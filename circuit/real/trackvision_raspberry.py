import argparse
import base64
import math
import os
import subprocess
import tempfile
import time
from pathlib import Path

import requests


try:
    import RPi.GPIO as GPIO
except ImportError as exc:
    raise SystemExit("Instala RPi.GPIO en la Raspberry Pi antes de ejecutar este script.") from exc

try:
    from smbus2 import SMBus
except ImportError as exc:
    raise SystemExit("Instala smbus2 en la Raspberry Pi antes de ejecutar este script.") from exc


MPU6050_ADDRESS = 0x68
PWR_MGMT_1 = 0x6B
ACCEL_XOUT_H = 0x3B
ACCEL_SCALE = 16384.0

BUTTON_REASON = "circuit_button"
IMPACT_REASON = "possible_collision"
DEFAULT_BASE_URL = "https://igream-trackvision-project.hf.space"


class TrackVisionCircuit:
    def __init__(self, args: argparse.Namespace) -> None:
        self.base_url = args.base_url.rstrip("/")
        self.username = args.username
        self.password = args.password
        self.button_pin = args.button_pin
        self.led_pin = args.led_pin
        self.impact_threshold = args.impact_threshold
        self.cooldown_seconds = args.cooldown_seconds
        self.debounce_seconds = args.debounce_seconds
        self.poll_seconds = args.poll_seconds
        self.capture_command = args.capture_command
        self.session = requests.Session()
        self.bus = SMBus(args.i2c_bus)
        self.last_event_at = 0.0
        self.last_button_at = 0.0

    def setup(self) -> None:
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(self.button_pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        GPIO.setup(self.led_pin, GPIO.OUT)
        self.bus.write_byte_data(MPU6050_ADDRESS, PWR_MGMT_1, 0)
        self.login()
        self.set_led(True)

    def close(self) -> None:
        self.set_led(False)
        self.bus.close()
        GPIO.cleanup()

    def set_led(self, enabled: bool) -> None:
        GPIO.output(self.led_pin, GPIO.HIGH if enabled else GPIO.LOW)

    def blink(self, count: int, interval: float = 0.15) -> None:
        for _ in range(count):
            self.set_led(False)
            time.sleep(interval)
            self.set_led(True)
            time.sleep(interval)

    def login(self) -> None:
        response = self.session.post(
            f"{self.base_url}/login",
            data={"username": self.username, "password": self.password},
            timeout=30,
            allow_redirects=False,
        )
        if response.status_code not in {200, 302, 303}:
            raise RuntimeError(f"No se pudo iniciar sesion: HTTP {response.status_code}")

    def read_word(self, register: int) -> int:
        high = self.bus.read_byte_data(MPU6050_ADDRESS, register)
        low = self.bus.read_byte_data(MPU6050_ADDRESS, register + 1)
        value = (high << 8) + low
        if value >= 0x8000:
            value = -((65535 - value) + 1)
        return value

    def acceleration_magnitude(self) -> float:
        ax = self.read_word(ACCEL_XOUT_H) / ACCEL_SCALE
        ay = self.read_word(ACCEL_XOUT_H + 2) / ACCEL_SCALE
        az = self.read_word(ACCEL_XOUT_H + 4) / ACCEL_SCALE
        return math.sqrt((ax * ax) + (ay * ay) + (az * az))

    def button_pressed(self) -> bool:
        now = time.monotonic()
        if GPIO.input(self.button_pin) != GPIO.LOW:
            return False
        if now - self.last_button_at < self.debounce_seconds:
            return False
        self.last_button_at = now
        return True

    def event_allowed(self) -> bool:
        return time.monotonic() - self.last_event_at >= self.cooldown_seconds

    def capture_image(self) -> Path:
        temp_dir = Path(tempfile.gettempdir())
        image_path = temp_dir / f"trackvision_{int(time.time())}.jpg"
        command = self.capture_command.format(output=str(image_path))
        completed = subprocess.run(command, shell=True, check=False, capture_output=True, text=True)
        if completed.returncode != 0 or not image_path.exists():
            raise RuntimeError(f"Fallo la captura de camara: {completed.stderr.strip()}")
        return image_path

    def parse_response(self, response: requests.Response, step_name: str) -> dict:
        try:
            payload = response.json()
        except ValueError as exc:
            raise RuntimeError(f"{step_name} no devolvio JSON valido: {response.text[:200]}") from exc
        if not response.ok or not payload.get("ok"):
            raise RuntimeError(f"{step_name} fallido: HTTP {response.status_code} {payload}")
        return payload

    def data_url_to_bytes(self, data_url: str, field_name: str) -> tuple[bytes, str]:
        if not data_url:
            raise RuntimeError(f"La respuesta no incluyo {field_name}; no se puede continuar el flujo.")
        if "," not in data_url:
            raise RuntimeError(f"{field_name} no tiene formato data URL valido.")
        header, encoded = data_url.split(",", 1)
        content_type = header.removeprefix("data:").split(";", 1)[0] or "image/png"
        return base64.b64decode(encoded), content_type

    def post_image(
        self,
        endpoint: str,
        mode: str,
        reason: str,
        filename: str,
        image_bytes: bytes,
        content_type: str,
        original: tuple[str, bytes, str] | None = None,
    ) -> dict:
        files = {"plate_image": (filename, image_bytes, content_type)}
        if original:
            files["original_image"] = original
        response = self.session.post(
            f"{self.base_url}{endpoint}",
            data={"mode": mode, "reason": reason},
            files=files,
            timeout=120,
        )
        return self.parse_response(response, mode)

    def send_full_pipeline(self, image_path: Path, reason: str) -> list[dict]:
        original_bytes = image_path.read_bytes()
        original_type = "image/png" if image_path.suffix.lower() == ".png" else "image/jpeg"

        vehicle = self.post_image(
            "/api/vehicle",
            "vehicle",
            reason,
            image_path.name,
            original_bytes,
            original_type,
        )
        vehicle_bytes, vehicle_type = self.data_url_to_bytes(vehicle.get("vehicleCrop"), "vehicleCrop")

        detect = self.post_image(
            "/api/detect",
            "detect",
            reason,
            "recorte_carro.png",
            vehicle_bytes,
            vehicle_type,
        )
        plate_bytes, plate_type = self.data_url_to_bytes(detect.get("plateCrop") or detect.get("crop"), "plateCrop")

        ocr = self.post_image(
            "/api/process",
            "ocr",
            reason,
            "recorte_placa.png",
            plate_bytes,
            plate_type,
            original=(image_path.name, original_bytes, original_type),
        )
        return [vehicle, detect, ocr]

    def handle_event(self, reason: str) -> None:
        if not self.event_allowed():
            return
        self.last_event_at = time.monotonic()
        image_path = None
        try:
            self.blink(3, 0.08)
            image_path = self.capture_image()
            self.set_led(True)
            results = self.send_full_pipeline(image_path, reason)
            print(
                "Flujo enviado: "
                f"carro={results[0].get('plate')}, "
                f"placa={results[1].get('plate')}, "
                f"ocr={results[2].get('plate')}"
            )
            self.blink(2, 0.2)
        except Exception as exc:
            print(f"Error: {exc}")
            self.blink(6, 0.1)
        finally:
            if image_path and image_path.exists():
                image_path.unlink(missing_ok=True)
            self.set_led(True)

    def run(self) -> None:
        print("TrackVision Raspberry listo. Esperando boton o impacto.")
        while True:
            if self.button_pressed():
                self.handle_event(BUTTON_REASON)
                continue

            magnitude = self.acceleration_magnitude()
            if magnitude > self.impact_threshold:
                print(f"Impacto detectado: {magnitude:.2f} g")
                self.handle_event(IMPACT_REASON)

            time.sleep(self.poll_seconds)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Cliente real de circuito TrackVision para Raspberry Pi.")
    parser.add_argument("--base-url", default=os.getenv("TRACKVISION_BASE_URL", DEFAULT_BASE_URL))
    parser.add_argument("--username", default=os.getenv("TRACKVISION_USERNAME"))
    parser.add_argument("--password", default=os.getenv("TRACKVISION_PASSWORD"))
    parser.add_argument("--button-pin", type=int, default=int(os.getenv("TRACKVISION_BUTTON_PIN", "17")))
    parser.add_argument("--led-pin", type=int, default=int(os.getenv("TRACKVISION_LED_PIN", "27")))
    parser.add_argument("--i2c-bus", type=int, default=int(os.getenv("TRACKVISION_I2C_BUS", "1")))
    parser.add_argument("--impact-threshold", type=float, default=float(os.getenv("TRACKVISION_IMPACT_THRESHOLD", "2.4")))
    parser.add_argument("--cooldown-seconds", type=float, default=float(os.getenv("TRACKVISION_COOLDOWN_SECONDS", "5")))
    parser.add_argument("--debounce-seconds", type=float, default=float(os.getenv("TRACKVISION_DEBOUNCE_SECONDS", "0.5")))
    parser.add_argument("--poll-seconds", type=float, default=float(os.getenv("TRACKVISION_POLL_SECONDS", "0.1")))
    parser.add_argument(
        "--capture-command",
        default=os.getenv("TRACKVISION_CAPTURE_COMMAND", "libcamera-still -n -o {output} --timeout 1000"),
        help="Comando de captura. Debe incluir {output}.",
    )
    args = parser.parse_args()
    if not args.username or not args.password:
        raise SystemExit("Define TRACKVISION_USERNAME y TRACKVISION_PASSWORD, o usa --username y --password.")
    if "{output}" not in args.capture_command:
        raise SystemExit("--capture-command debe incluir {output}.")
    return args


def main() -> None:
    circuit = TrackVisionCircuit(parse_args())
    try:
        circuit.setup()
        circuit.run()
    finally:
        circuit.close()


if __name__ == "__main__":
    main()
