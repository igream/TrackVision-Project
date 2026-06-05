import argparse
import base64
import os
import sys
from getpass import getpass
from pathlib import Path

import requests


DEFAULT_BASE_URL = os.getenv("TRACKVISION_BASE_URL", "http://127.0.0.1:8000")
IMG_DIR = Path(__file__).resolve().parents[2] / "img"
EVENTS = {
    "button": {
        "label": "Activacion del boton del circuito",
        "reason": "circuit_button",
    },
    "impact": {
        "label": "Posible choque",
        "reason": "possible_collision",
    },
}


def login(session: requests.Session, base_url: str, username: str, password: str) -> bool:
    response = session.post(
        f"{base_url}/login",
        data={"username": username, "password": password},
        timeout=30,
        allow_redirects=False,
    )
    if response.status_code in {302, 303}:
        return True
    if response.status_code == 200:
        return False
    if response.status_code == 404:
        return False
    if response.status_code >= 500:
        raise RuntimeError(f"No se pudo iniciar sesion: HTTP {response.status_code} {response.text[:200]}")
    return False


def register_user(session: requests.Session, base_url: str, username: str, password: str) -> bool:
    response = session.post(
        f"{base_url}/register",
        data={"username": username, "password": password},
        timeout=30,
        allow_redirects=False,
    )
    return response.status_code in {302, 303}


def parse_response(response: requests.Response, step_name: str) -> dict:
    try:
        payload = response.json()
    except ValueError:
        payload = {"ok": False, "error": response.text}

    if not response.ok or not payload.get("ok"):
        raise RuntimeError(f"{step_name} fallido: HTTP {response.status_code} {payload}")
    return payload


def data_url_to_bytes(data_url: str, field_name: str) -> tuple[bytes, str]:
    if not data_url:
        raise RuntimeError(f"La respuesta no incluyo {field_name}; no se puede continuar el flujo.")
    if "," not in data_url:
        raise RuntimeError(f"{field_name} no tiene formato data URL valido.")
    header, encoded = data_url.split(",", 1)
    content_type = header.removeprefix("data:").split(";", 1)[0] or "image/png"
    return base64.b64decode(encoded), content_type


def post_image(
    session: requests.Session,
    base_url: str,
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
    response = session.post(
        f"{base_url}{endpoint}",
        data={"mode": mode, "reason": reason},
        files=files,
        timeout=120,
    )
    return parse_response(response, mode)


def send_full_pipeline(session: requests.Session, base_url: str, event: str, image_path: Path) -> list[dict]:
    config = EVENTS[event]
    reason = config["reason"]
    if not image_path.exists():
        raise FileNotFoundError(f"No existe la imagen de prueba: {image_path}")

    original_bytes = image_path.read_bytes()
    original_type = "image/png" if image_path.suffix.lower() == ".png" else "image/jpeg"

    vehicle = post_image(
        session,
        base_url,
        "/api/vehicle",
        "vehicle",
        reason,
        image_path.name,
        original_bytes,
        original_type,
    )
    vehicle_bytes, vehicle_type = data_url_to_bytes(vehicle.get("vehicleCrop"), "vehicleCrop")

    detect = post_image(
        session,
        base_url,
        "/api/detect",
        "detect",
        reason,
        "recorte_carro.png",
        vehicle_bytes,
        vehicle_type,
    )
    plate_bytes, plate_type = data_url_to_bytes(detect.get("plateCrop") or detect.get("crop"), "plateCrop")

    ocr = post_image(
        session,
        base_url,
        "/api/process",
        "ocr",
        reason,
        "recorte_placa.png",
        plate_bytes,
        plate_type,
        original=(image_path.name, original_bytes, original_type),
    )
    return [vehicle, detect, ocr]


def prompt_required(prompt: str, *, secret: bool = False) -> str:
    while True:
        value = getpass(prompt).strip() if secret and sys.stdin.isatty() else input(prompt).strip()
        if value:
            return value
        print("El valor no puede estar vacio.")


def prompt_choice(prompt: str, options: list[str]) -> int:
    while True:
        raw_value = input(prompt).strip()
        try:
            value = int(raw_value)
        except ValueError:
            print("Escribe un numero valido.")
            continue
        if 1 <= value <= len(options):
            return value - 1
        print(f"Elige una opcion entre 1 y {len(options)}.")


def authenticate(session: requests.Session, base_url: str) -> tuple[str, str]:
    print("\nCredenciales de TrackVision")
    username = prompt_required("Usuario: ")
    password = prompt_required("Contrasena: ", secret=True)

    if login(session, base_url, username, password):
        print("Sesion iniciada correctamente.")
        return username, password

    print("No se pudo iniciar sesion. El usuario puede no existir o la contrasena es incorrecta.")
    create = input("Deseas registrar este usuario ahora? [s/N]: ").strip().lower()
    if create not in {"s", "si", "y", "yes"}:
        raise RuntimeError("Autenticacion cancelada. Registra el usuario en la web o revisa la contrasena.")

    if not register_user(session, base_url, username, password):
        raise RuntimeError("No se pudo registrar el usuario. Puede que ya exista con otra contrasena.")
    print("Usuario registrado correctamente.")
    return username, password


def select_event() -> str:
    keys = ["button", "impact"]
    print("\nCaso a registrar")
    for index, key in enumerate(keys, start=1):
        print(f"{index}. {EVENTS[key]['label']}")
    return keys[prompt_choice("Selecciona un caso: ", keys)]


def sample_images(limit: int = 10) -> list[Path]:
    extensions = {".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".tif", ".webp"}
    images = [path for path in sorted(IMG_DIR.iterdir()) if path.suffix.lower() in extensions]
    return images[:limit]


def select_image() -> Path:
    images = sample_images()
    if not images:
        raise FileNotFoundError(f"No hay imagenes de prueba en {IMG_DIR}.")

    print("\nImagenes de prueba disponibles")
    for index, image_path in enumerate(images, start=1):
        print(f"{index}. {image_path.name}")
    return images[prompt_choice("Selecciona una imagen: ", [image.name for image in images])]


def main() -> None:
    parser = argparse.ArgumentParser(description="Emula eventos del circuito TrackVision sin Raspberry Pi.")
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL, help="URL base de TrackVision.")
    args = parser.parse_args()

    base_url = args.base_url.rstrip("/")
    session = requests.Session()
    print("Emulador de circuito TrackVision")
    print(f"Servidor: {base_url}")

    try:
        authenticate(session, base_url)
        event = select_event()
        image_path = select_image()
        print(f"\nProcesando {image_path.name} como {EVENTS[event]['label']}...")
        results = send_full_pipeline(session, base_url, event, image_path)
    except requests.RequestException as exc:
        raise SystemExit(f"Error de red al conectar con TrackVision: {exc}") from exc
    except Exception as exc:
        raise SystemExit(str(exc)) from exc

    print("\nFlujo completo enviado correctamente")
    for title, result in zip(["Carro", "Placa", "OCR"], results):
        print(f"{title}: {result.get('plate')} ({round((result.get('confidence') or 0) * 100)}%)")
    print(f"Motivo: {results[-1].get('reasonLabel', results[-1].get('reason'))}")


if __name__ == "__main__":
    main()
