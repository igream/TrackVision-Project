import base64
import cgi
import json
import mimetypes
import os
import posixpath
import tempfile
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Dict
from urllib.parse import unquote, urlparse

import cv2

from config.backend import WEB_HOST, WEB_PORT
from ocr_core import process_plate_image
from plate_detector import detect_plate_regions
from storage import save_detection_result


BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"
TEMPLATE_DIR = BASE_DIR / "templates"
IMG_DIR = BASE_DIR / "img"
LOGO_PATHS = (
    BASE_DIR / "src" / "LogoInApp.png",
    BASE_DIR / "src" / "LogoInApp.PNG",
)
FAVICON_PATHS = (
    BASE_DIR / "src" / "LogoOutApp.png",
    BASE_DIR / "src" / "LogoOutApp.PNG",
)
UAEMEX_PATHS = (
    BASE_DIR / "src" / "LogoUAEMex.png",
    BASE_DIR / "src" / "LogoUAEMex.PNG",
)
SUPPORTED_UPLOAD_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".tif", ".webp"}


def _json_response(payload: Dict[str, Any], status: HTTPStatus = HTTPStatus.OK) -> bytes:
    return json.dumps(payload, ensure_ascii=False).encode("utf-8")


def _image_to_data_url(image) -> str:
    ok, buffer = cv2.imencode(".png", image)
    if not ok:
        raise ValueError("No se pudo preparar una imagen de resultado para la web.")
    encoded = base64.b64encode(buffer).decode("ascii")
    return f"data:image/png;base64,{encoded}"


class OCRWebHandler(SimpleHTTPRequestHandler):
    server_version = "OCRPlacasWeb/1.0"

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        path = parsed.path

        if path in {"/", "/index.html"}:
            self._send_file(TEMPLATE_DIR / "index.html", "text/html; charset=utf-8")
            return

        if path == "/assets/logo":
            logo_path = next((candidate for candidate in LOGO_PATHS if candidate.exists()), None)
            if logo_path is None:
                self.send_error(HTTPStatus.NOT_FOUND, "Logo no encontrado")
                return
            self._send_file(logo_path, "image/png")
            return

        if path == "/assets/favicon":
            favicon_path = next((candidate for candidate in FAVICON_PATHS if candidate.exists()), None)
            if favicon_path is None:
                self.send_error(HTTPStatus.NOT_FOUND, "Icono no encontrado")
                return
            self._send_file(favicon_path, "image/png")
            return

        if path == "/assets/uaemex":
            uaemex_path = next((candidate for candidate in UAEMEX_PATHS if candidate.exists()), None)
            if uaemex_path is None:
                self.send_error(HTTPStatus.NOT_FOUND, "Logo UAEMex no encontrado")
                return
            self._send_file(uaemex_path, "image/png")
            return

        if path.startswith("/static/"):
            self._send_safe_static_file(STATIC_DIR, path.removeprefix("/static/"))
            return

        if path.startswith("/samples/"):
            self._send_safe_static_file(IMG_DIR, path.removeprefix("/samples/"))
            return

        self.send_error(HTTPStatus.NOT_FOUND, "Ruta no encontrada")

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path not in {"/api/process", "/api/detect"}:
            self.send_error(HTTPStatus.NOT_FOUND, "Ruta no encontrada")
            return

        try:
            if parsed.path == "/api/detect":
                payload = self._handle_detect_request()
            else:
                payload = self._handle_process_request()
            self._send_json(payload)
        except Exception as error:
            self._send_json({"ok": False, "error": str(error)}, HTTPStatus.BAD_REQUEST)

    def _save_upload_to_temp(self) -> tuple[str, str]:
        content_type = self.headers.get("Content-Type", "")
        if not content_type.startswith("multipart/form-data"):
            raise ValueError("La peticion debe incluir una imagen en formulario multipart.")

        form = cgi.FieldStorage(
            fp=self.rfile,
            headers=self.headers,
            environ={
                "REQUEST_METHOD": "POST",
                "CONTENT_TYPE": content_type,
            },
        )

        if "plate_image" not in form:
            raise ValueError("Seleccione una imagen antes de procesar.")

        upload = form["plate_image"]
        filename = Path(upload.filename or "").name
        extension = Path(filename).suffix.lower()
        if extension not in SUPPORTED_UPLOAD_EXTENSIONS:
            raise ValueError(f"Formato '{extension or 'sin extension'}' no soportado.")

        with tempfile.NamedTemporaryFile(suffix=extension, delete=False) as temp_file:
            temp_path = temp_file.name
            temp_file.write(upload.file.read())

        return temp_path, filename

    def _handle_process_request(self) -> Dict[str, Any]:
        temp_path, filename = self._save_upload_to_temp()

        try:
            result = process_plate_image(temp_path)
            result.ruta_original = filename
            saved_dir = save_detection_result(result)
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)

        stages = [
            {
                "title": title,
                "image": _image_to_data_url(image),
            }
            for title, image in result.etapas
        ]

        return {
            "ok": True,
            "plate": result.texto_matricula or "No detectada",
            "confidence": result.promedio_confianza,
            "type": result.tipo,
            "savedDir": saved_dir,
            "summary": result.resumen_texto,
            "stages": stages,
        }

    def _handle_detect_request(self) -> Dict[str, Any]:
        temp_path, _ = self._save_upload_to_temp()

        try:
            result = detect_plate_regions(temp_path)
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)

        stages = [
            {
                "title": title,
                "image": _image_to_data_url(image),
            }
            for title, image in result.debug_steps
        ]

        best = result.best_region
        return {
            "ok": True,
            "plate": "Placa detectada" if best else "No detectada",
            "confidence": best.confidence if best else 0.0,
            "type": "Deteccion PDI",
            "savedDir": "Sin guardado automatico",
            "summary": result.summary_text,
            "stages": stages,
            "bbox": best.bbox if best else None,
        }

    def _send_json(self, payload: Dict[str, Any], status: HTTPStatus = HTTPStatus.OK) -> None:
        body = _json_response(payload, status)
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_file(self, path: Path, content_type: str | None = None) -> None:
        if not path.exists() or not path.is_file():
            self.send_error(HTTPStatus.NOT_FOUND, "Archivo no encontrado")
            return

        body = path.read_bytes()
        guessed_type = content_type or mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", guessed_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_safe_static_file(self, root: Path, requested_path: str) -> None:
        normalized = posixpath.normpath(unquote(requested_path)).lstrip("/")
        target = (root / normalized).resolve()
        root_resolved = root.resolve()

        if root_resolved not in target.parents and target != root_resolved:
            self.send_error(HTTPStatus.FORBIDDEN, "Ruta no permitida")
            return

        self._send_file(target)


def run_server(host: str = WEB_HOST, port: int = WEB_PORT) -> None:
    server = ThreadingHTTPServer((host, port), OCRWebHandler)
    print(f"OCR Placas web disponible en http://{host}:{port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nServidor detenido.")
    finally:
        server.server_close()


if __name__ == "__main__":
    run_server()
