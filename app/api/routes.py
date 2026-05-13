import base64
import os
import tempfile
from pathlib import Path

import cv2
from fastapi import APIRouter, Request, Depends, HTTPException, Form, UploadFile, File, status
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, FileResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.database import get_db
from app.core.security import clear_session_cookie, get_password_hash, set_session_cookie, verify_password
from app.db.models import User, Detection
from app.services.ocr_core import process_plate_image
from app.services.plate_detector import detect_plate_regions
from app.services.storage import save_detection_result

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

templates = Jinja2Templates(directory=str(TEMPLATE_DIR))

def _image_to_data_url(image) -> str:
    ok, buffer = cv2.imencode(".png", image)
    if not ok:
        raise ValueError("No se pudo preparar una imagen de resultado para la web.")
    encoded = base64.b64encode(buffer).decode("ascii")
    return f"data:image/png;base64,{encoded}"

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

@router.post("/api/process")
async def handle_process_request(
    mode: str = Form(...),
    plate_image: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if not current_user:
        return JSONResponse({"ok": False, "error": "No autenticado"}, status_code=401)
        
    filename = plate_image.filename
    extension = Path(filename).suffix.lower()
    if extension not in SUPPORTED_UPLOAD_EXTENSIONS:
        return JSONResponse({"ok": False, "error": f"Formato '{extension}' no soportado."}, status_code=400)

    image_bytes = await plate_image.read()

    with tempfile.NamedTemporaryFile(suffix=extension, delete=False) as temp_file:
        temp_path = temp_file.name
        temp_file.write(image_bytes)

    try:
        result = process_plate_image(temp_path)
        result.ruta_original = filename
        saved_dir = save_detection_result(result)
        
        # Guardar en DB con BLOB
        detection = Detection(
            user_id=current_user.id,
            mode='ocr',
            plate_text=result.texto_matricula or "No detectada",
            confidence=result.promedio_confianza,
            original_filename=filename,
            saved_dir=saved_dir,
            summary_text="\n".join(result.resumen_texto),
            original_image_blob=image_bytes
        )
        db.add(detection)
        db.commit()
        
    except Exception as e:
        return JSONResponse({"ok": False, "error": str(e)}, status_code=400)
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)

    stages = [{"title": t, "image": _image_to_data_url(i)} for t, i in result.etapas]

    return {
        "ok": True,
        "plate": result.texto_matricula or "No detectada",
        "confidence": result.promedio_confianza,
        "type": result.tipo,
        "savedDir": saved_dir,
        "summary": result.resumen_texto,
        "stages": stages,
    }


@router.post("/api/detect")
async def handle_detect_request(
    mode: str = Form(...),
    plate_image: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if not current_user:
        return JSONResponse({"ok": False, "error": "No autenticado"}, status_code=401)
        
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
        
        # Guardar en DB con BLOB
        detection = Detection(
            user_id=current_user.id,
            mode='detect',
            plate_text="Placa detectada" if best else "No detectada",
            confidence=best.confidence if best else 0.0,
            original_filename=filename,
            saved_dir="Sin guardado automatico",
            summary_text="\n".join(result.summary_text) if isinstance(result.summary_text, list) else str(result.summary_text),
            original_image_blob=image_bytes
        )
        db.add(detection)
        db.commit()
        
    except Exception as e:
        return JSONResponse({"ok": False, "error": str(e)}, status_code=400)
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)

    stages = [{"title": t, "image": _image_to_data_url(i)} for t, i in result.debug_steps]
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
        "crop": _image_to_data_url(best.crop) if best else None,
    }
