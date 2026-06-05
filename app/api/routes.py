import base64
import datetime
import json
import os
import tempfile
from pathlib import Path

import cv2
import numpy as np
from fastapi import APIRouter, Request, Depends, HTTPException, Form, UploadFile, File, status
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, FileResponse, Response
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.database import get_db
from app.core.security import clear_session_cookie, get_password_hash, set_session_cookie, verify_password
from app.db.models import User, Detection
from app.services.ocr_core import process_plate_image
from app.services.plate_detector import detect_plate_regions
from app.services.storage import save_detection_result
from app.services.vehicle_detector import detect_largest_vehicle_region

router = APIRouter()

BASE_DIR = Path(__file__).resolve().parent.parent.parent
TEMPLATE_DIR = BASE_DIR / "app" / "templates"
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
DETECTION_REASONS = {
    "web_process": "Procesado en web",
    "possible_collision": "Posible choque",
    "circuit_button": "Activacion del boton del circuito",
}

templates = Jinja2Templates(directory=str(TEMPLATE_DIR))

def _image_to_data_url(image) -> str:
    ok, buffer = cv2.imencode(".png", image)
    if not ok:
        raise ValueError("No se pudo preparar una imagen de resultado para la web.")
    encoded = base64.b64encode(buffer).decode("ascii")
    return f"data:image/png;base64,{encoded}"


def _image_to_png_bytes(image) -> bytes | None:
    if image is None:
        return None
    ok, buffer = cv2.imencode(".png", image)
    if not ok:
        return None
    return buffer.tobytes()


def _uploaded_bytes_to_png_bytes(image_bytes: bytes) -> bytes:
    image_array = np.frombuffer(image_bytes, dtype=np.uint8)
    image = cv2.imdecode(image_array, cv2.IMREAD_COLOR)
    if image is None:
        return image_bytes
    png_bytes = _image_to_png_bytes(image)
    return png_bytes or image_bytes


def _write_temp_image(image, suffix: str = ".png") -> str:
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as temp_file:
        temp_path = temp_file.name
    if not cv2.imwrite(temp_path, image):
        raise ValueError("No se pudo preparar el recorte temporal para procesamiento.")
    return temp_path


def _bbox_to_text(bbox) -> str | None:
    if not bbox:
        return None
    return ",".join(str(int(value)) for value in bbox)


def _bbox_to_list(value: str | None):
    if not value:
        return None
    try:
        return [int(part) for part in value.split(",")]
    except ValueError:
        return None


def _parse_report(value: str | None):
    if not value:
        return None
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return None


def _normalize_reason(reason: str | None) -> str:
    value = (reason or "web_process").strip()
    if value not in DETECTION_REASONS:
        raise HTTPException(status_code=400, detail="Motivo de deteccion no soportado")
    return value


def _reason_label(reason: str | None) -> str:
    return DETECTION_REASONS.get(reason or "web_process", DETECTION_REASONS["web_process"])


def _ocr_report(result):
    return {
        "plate": result.texto_matricula or "No detectada",
        "confidence": result.promedio_confianza,
        "type": result.tipo,
        "allTexts": [
            {"text": text, "confidence": confidence}
            for text, confidence in result.todos_los_textos
        ],
        "plateParts": [
            {"text": item.texto, "confidence": item.confianza}
            for item in result.matricula_partes
        ],
        "summary": result.resumen_texto,
    }


def _steps_to_payload(steps):
    return [{"title": title, "image": _image_to_data_url(image)} for title, image in steps]


def _is_detected(detection: Detection) -> bool:
    text = (detection.plate_text or "").lower()
    if text.startswith("no detect"):
        return False
    return bool(detection.confidence and detection.confidence > 0)


def _detection_list_item(detection: Detection):
    return {
        "id": detection.id,
        "timestamp": detection.timestamp.isoformat() if detection.timestamp else None,
        "mode": detection.mode,
        "reason": detection.reason or "web_process",
        "reasonLabel": _reason_label(detection.reason),
        "plate": detection.plate_text or "No detectada",
        "confidence": detection.confidence or 0.0,
        "filename": detection.original_filename,
        "hasOriginal": detection.original_image_blob is not None,
        "hasVehicleCrop": detection.vehicle_crop_blob is not None,
        "hasPlateCrop": detection.plate_crop_blob is not None,
        "detected": _is_detected(detection),
    }


def _detection_detail(detection: Detection):
    return {
        **_detection_list_item(detection),
        "savedDir": detection.saved_dir,
        "summary": detection.summary_text.splitlines() if detection.summary_text else [],
        "vehicleBbox": _bbox_to_list(detection.vehicle_bbox),
        "plateBbox": _bbox_to_list(detection.plate_bbox),
        "report": _parse_report(detection.report_json),
        "images": {
            "original": f"/api/detections/{detection.id}/image/original" if detection.original_image_blob else None,
            "vehicleCrop": f"/api/detections/{detection.id}/image/vehicle_crop" if detection.vehicle_crop_blob else None,
            "plateCrop": f"/api/detections/{detection.id}/image/plate_crop" if detection.plate_crop_blob else None,
        },
    }

@router.get("/", response_class=HTMLResponse)
async def index(request: Request, current_user: User = Depends(get_current_user)):
    if not current_user:
        return RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)
    return templates.TemplateResponse(request=request, name="index.html", context={"current_user": current_user})

@router.get("/login", response_class=HTMLResponse)
async def login_form(request: Request, current_user: User = Depends(get_current_user)):
    if current_user:
        return RedirectResponse(url="/", status_code=status.HTTP_302_FOUND)
    return templates.TemplateResponse(request=request, name="login.html")

@router.post("/login", response_class=HTMLResponse)
async def login(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.username == username).first()
    if not user or not verify_password(password, user.password_hash):
        return templates.TemplateResponse(request=request, name="login.html", context={"error": "Usuario o contraseña incorrectos"})
    
    response = RedirectResponse(url="/", status_code=status.HTTP_302_FOUND)
    set_session_cookie(response, user.id)
    return response

@router.get("/register", response_class=HTMLResponse)
async def register_form(request: Request, current_user: User = Depends(get_current_user)):
    if current_user:
        return RedirectResponse(url="/", status_code=status.HTTP_302_FOUND)
    return templates.TemplateResponse(request=request, name="register.html")

@router.post("/register", response_class=HTMLResponse)
async def register(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.username == username).first()
    if user:
        return templates.TemplateResponse(request=request, name="register.html", context={"error": "El usuario ya existe"})
    
    hashed_password = get_password_hash(password)
    new_user = User(username=username, password_hash=hashed_password)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    response = RedirectResponse(url="/", status_code=status.HTTP_302_FOUND)
    set_session_cookie(response, new_user.id)
    return response

@router.get("/logout")
async def logout():
    response = RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)
    clear_session_cookie(response)
    return response

@router.get("/assets/logo")
async def serve_logo():
    logo_path = next((p for p in LOGO_PATHS if p.exists()), None)
    if not logo_path:
        raise HTTPException(status_code=404, detail="Not found")
    return FileResponse(logo_path)

@router.get("/assets/favicon")
async def serve_favicon():
    favicon_path = next((p for p in FAVICON_PATHS if p.exists()), None)
    if not favicon_path:
        raise HTTPException(status_code=404, detail="Not found")
    return FileResponse(favicon_path)

@router.get("/assets/uaemex")
async def serve_uaemex():
    uaemex_path = next((p for p in UAEMEX_PATHS if p.exists()), None)
    if not uaemex_path:
        raise HTTPException(status_code=404, detail="Not found")
    return FileResponse(uaemex_path)

@router.get("/samples/{filename:path}")
async def serve_samples(filename: str):
    file_path = IMG_DIR / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Not found")
    return FileResponse(file_path)


@router.post("/api/vehicle")
async def handle_vehicle_request(
    mode: str = Form(...),
    reason: str | None = Form(None),
    plate_image: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if not current_user:
        return JSONResponse({"ok": False, "error": "No autenticado"}, status_code=401)
    reason_value = _normalize_reason(reason)

    filename = plate_image.filename
    extension = Path(filename).suffix.lower()
    if extension not in SUPPORTED_UPLOAD_EXTENSIONS:
        return JSONResponse({"ok": False, "error": f"Formato '{extension}' no soportado."}, status_code=400)

    image_bytes = await plate_image.read()

    with tempfile.NamedTemporaryFile(suffix=extension, delete=False) as temp_file:
        temp_path = temp_file.name
        temp_file.write(image_bytes)

    try:
        result = detect_largest_vehicle_region(temp_path)
        best = result.best_region
        stages = _steps_to_payload(result.debug_steps)

        detection = Detection(
            user_id=current_user.id,
            mode='vehicle',
            reason=reason_value,
            plate_text="Carro detectado" if best else "No detectado",
            confidence=best.confidence if best else 0.0,
            original_filename=filename,
            saved_dir="Sin guardado automatico",
            summary_text="\n".join(result.summary_text),
            original_image_blob=_uploaded_bytes_to_png_bytes(image_bytes),
            vehicle_crop_blob=_image_to_png_bytes(best.crop) if best else None,
            vehicle_bbox=_bbox_to_text(best.bbox) if best else None,
            report_json=json.dumps({
                "vehicle": {
                    "detected": bool(best),
                    "confidence": best.confidence if best else 0.0,
                    "bbox": best.bbox if best else None,
                },
                "summary": result.summary_text,
            }),
        )
        db.add(detection)
        db.commit()

    except Exception as e:
        return JSONResponse({"ok": False, "error": str(e)}, status_code=400)
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)

    best = result.best_region

    return {
        "ok": True,
        "plate": "Carro detectado" if best else "No detectado",
        "confidence": best.confidence if best else 0.0,
        "type": "Deteccion de carro",
        "reason": reason_value,
        "reasonLabel": _reason_label(reason_value),
        "savedDir": "Sin guardado automatico",
        "summary": result.summary_text,
        "stages": stages,
        "bbox": best.bbox if best else None,
        "vehicleCrop": _image_to_data_url(best.crop) if best else None,
    }

@router.post("/api/process")
async def handle_process_request(
    mode: str = Form(...),
    reason: str | None = Form(None),
    plate_image: UploadFile = File(...),
    original_image: UploadFile | None = File(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if not current_user:
        return JSONResponse({"ok": False, "error": "No autenticado"}, status_code=401)
    reason_value = _normalize_reason(reason)
        
    filename = plate_image.filename
    extension = Path(filename).suffix.lower()
    if extension not in SUPPORTED_UPLOAD_EXTENSIONS:
        return JSONResponse({"ok": False, "error": f"Formato '{extension}' no soportado."}, status_code=400)

    image_bytes = await plate_image.read()
    original_image_bytes = await original_image.read() if original_image else image_bytes

    with tempfile.NamedTemporaryFile(suffix=extension, delete=False) as temp_file:
        temp_path = temp_file.name
        temp_file.write(image_bytes)

    try:
        result = process_plate_image(temp_path)
        result.ruta_original = filename
        saved_dir = save_detection_result(result)
        report = _ocr_report(result)
        ocr_plate_crop = result.etapas[3][1] if len(result.etapas) > 3 else None
        stages = _steps_to_payload(result.etapas)
        
        # Guardar en DB con BLOB
        detection = Detection(
            user_id=current_user.id,
            mode='ocr',
            reason=reason_value,
            plate_text=result.texto_matricula or "No detectada",
            confidence=result.promedio_confianza,
            original_filename=filename,
            saved_dir=saved_dir,
            summary_text="\n".join(result.resumen_texto),
            original_image_blob=_uploaded_bytes_to_png_bytes(original_image_bytes),
            plate_crop_blob=_image_to_png_bytes(ocr_plate_crop) or _uploaded_bytes_to_png_bytes(image_bytes),
            report_json=json.dumps(report),
        )
        db.add(detection)
        db.commit()
        
    except Exception as e:
        return JSONResponse({"ok": False, "error": str(e)}, status_code=400)
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)

    return {
        "ok": True,
        "plate": result.texto_matricula or "No detectada",
        "confidence": result.promedio_confianza,
        "type": result.tipo,
        "reason": reason_value,
        "reasonLabel": _reason_label(reason_value),
        "savedDir": saved_dir,
        "summary": result.resumen_texto,
        "stages": stages,
        "report": report,
        "plateCrop": _image_to_data_url(ocr_plate_crop) if ocr_plate_crop is not None else None,
    }


@router.post("/api/detect")
async def handle_detect_request(
    mode: str = Form(...),
    reason: str | None = Form(None),
    plate_image: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if not current_user:
        return JSONResponse({"ok": False, "error": "No autenticado"}, status_code=401)
    reason_value = _normalize_reason(reason)
        
    filename = plate_image.filename
    extension = Path(filename).suffix.lower()
    if extension not in SUPPORTED_UPLOAD_EXTENSIONS:
        return JSONResponse({"ok": False, "error": f"Formato '{extension}' no soportado."}, status_code=400)

    image_bytes = await plate_image.read()

    with tempfile.NamedTemporaryFile(suffix=extension, delete=False) as temp_file:
        temp_path = temp_file.name
        temp_file.write(image_bytes)

    try:
        result = detect_plate_regions(temp_path)
        best = result.best_region
        stages = _steps_to_payload(result.debug_steps)
        
        # Guardar en DB con BLOB
        detection = Detection(
            user_id=current_user.id,
            mode='detect',
            reason=reason_value,
            plate_text="Placa detectada" if best else "No detectada",
            confidence=best.confidence if best else 0.0,
            original_filename=filename,
            saved_dir="Sin guardado automatico",
            summary_text="\n".join(result.summary_text) if isinstance(result.summary_text, list) else str(result.summary_text),
            original_image_blob=_uploaded_bytes_to_png_bytes(image_bytes),
            plate_crop_blob=_image_to_png_bytes(best.crop) if best else None,
            plate_bbox=_bbox_to_text(best.bbox) if best else None,
            report_json=json.dumps({
                "plate": {
                    "detected": bool(best),
                    "confidence": best.confidence if best else 0.0,
                    "bbox": best.bbox if best else None,
                },
                "summary": result.summary_text,
            }),
        )
        db.add(detection)
        db.commit()
        
    except Exception as e:
        return JSONResponse({"ok": False, "error": str(e)}, status_code=400)
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)

    best = result.best_region

    return {
        "ok": True,
        "plate": "Placa detectada" if best else "No detectada",
        "confidence": best.confidence if best else 0.0,
        "type": "Deteccion PDI",
        "reason": reason_value,
        "reasonLabel": _reason_label(reason_value),
        "savedDir": "Sin guardado automatico",
        "summary": result.summary_text,
        "stages": stages,
        "bbox": best.bbox if best else None,
        "crop": _image_to_data_url(best.crop) if best else None,
        "plateCrop": _image_to_data_url(best.crop) if best else None,
    }


@router.get("/api/detections")
async def list_detections(
    mode: str | None = None,
    reason: str | None = None,
    status_filter: str | None = None,
    q: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if not current_user:
        return JSONResponse({"ok": False, "error": "No autenticado"}, status_code=401)

    query = db.query(Detection).filter(Detection.user_id == current_user.id)

    if mode in {"vehicle", "detect", "ocr"}:
        query = query.filter(Detection.mode == mode)

    if reason in DETECTION_REASONS:
        if reason == "web_process":
            query = query.filter((Detection.reason == reason) | (Detection.reason.is_(None)))
        else:
            query = query.filter(Detection.reason == reason)

    if q:
        pattern = f"%{q.strip()}%"
        query = query.filter(
            (Detection.plate_text.ilike(pattern))
            | (Detection.original_filename.ilike(pattern))
        )

    if date_from:
        try:
            start = datetime.datetime.fromisoformat(date_from)
            query = query.filter(Detection.timestamp >= start)
        except ValueError:
            pass

    if date_to:
        try:
            end = datetime.datetime.fromisoformat(date_to) + datetime.timedelta(days=1)
            query = query.filter(Detection.timestamp < end)
        except ValueError:
            pass

    detections = query.order_by(Detection.timestamp.desc()).limit(100).all()
    if status_filter == "detected":
        detections = [item for item in detections if _is_detected(item)]
    elif status_filter == "not_detected":
        detections = [item for item in detections if not _is_detected(item)]
    return {"ok": True, "detections": [_detection_list_item(item) for item in detections]}


@router.get("/api/detections/{detection_id}")
async def get_detection_detail(
    detection_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if not current_user:
        return JSONResponse({"ok": False, "error": "No autenticado"}, status_code=401)

    detection = (
        db.query(Detection)
        .filter(Detection.id == detection_id, Detection.user_id == current_user.id)
        .first()
    )
    if not detection:
        raise HTTPException(status_code=404, detail="Deteccion no encontrada")
    return {"ok": True, "detection": _detection_detail(detection)}


@router.get("/api/detections/{detection_id}/image/{kind}")
async def get_detection_image(
    detection_id: int,
    kind: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if not current_user:
        return JSONResponse({"ok": False, "error": "No autenticado"}, status_code=401)

    detection = (
        db.query(Detection)
        .filter(Detection.id == detection_id, Detection.user_id == current_user.id)
        .first()
    )
    if not detection:
        raise HTTPException(status_code=404, detail="Deteccion no encontrada")

    blobs = {
        "original": detection.original_image_blob,
        "vehicle_crop": detection.vehicle_crop_blob,
        "plate_crop": detection.plate_crop_blob,
    }
    image_blob = blobs.get(kind)
    if not image_blob:
        raise HTTPException(status_code=404, detail="Imagen no disponible")

    return Response(content=image_blob, media_type="image/png")
