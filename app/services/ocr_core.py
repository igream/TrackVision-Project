import os
import re
import tempfile
from dataclasses import dataclass, field
from datetime import datetime
from functools import lru_cache
from threading import Lock
from typing import List, Optional, Tuple

import cv2
import imutils
import numpy as np
from paddleocr import PaddleOCR

from app.core.config_backend import (
    APPROX_CONTOUR_EPSILON,
    BILATERAL_FILTER_SIGMA_COLOR,
    BILATERAL_FILTER_SIGMA_SPACE,
    BILATERAL_FILTER_SIZE,
    BORDER_PADDING,
    BORDER_TYPE,
    CANNY_THRESHOLD_HIGH,
    CANNY_THRESHOLD_LOW,
    MAX_CONTOURS_TO_CHECK,
    OCR_ENABLE_MKLDNN,
    OCR_DEVICE,
    OCR_LANG,
    OCR_USE_ANGLE_CLS,
    REQUIRED_POLYGON_POINTS,
    VALID_THRESHOLD,
)

SUPPORTED_FORMATS = {'.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.tif', '.webp'}
_OCR_PREDICT_LOCK = Lock()

@dataclass
class PlateCandidate:
    texto: str
    confianza: float
    caja: Optional[np.ndarray] = None

@dataclass
class DetectionResult:
    ruta_original: str
    etapas: List[Tuple[str, np.ndarray]] = field(default_factory=list)
    todos_los_textos: List[Tuple[str, float]] = field(default_factory=list)
    matricula_partes: List[PlateCandidate] = field(default_factory=list)
    texto_real: Optional[str] = None
    resumen_texto: List[str] = field(default_factory=list)
    fecha: str = field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d"))
    hora: str = field(default_factory=lambda: datetime.now().strftime("%H-%M-%S"))

    @property
    def promedio_confianza(self) -> float:
        if not self.matricula_partes:
            return 0.0
        return float(np.mean([c.confianza for c in self.matricula_partes]))

    @property
    def texto_matricula(self) -> str:
        return ''.join([c.texto for c in self.matricula_partes])

    @property
    def tipo(self) -> str:
        return "Validas" if self.promedio_confianza > VALID_THRESHOLD else "Fallos"


@lru_cache(maxsize=1)
def get_ocr_engine() -> PaddleOCR:
    return PaddleOCR(
        use_angle_cls=OCR_USE_ANGLE_CLS,
        lang=OCR_LANG,
        device=OCR_DEVICE,
        enable_mkldnn=OCR_ENABLE_MKLDNN,
    )


def calcular_cer(referencia: str, hipotesis: str) -> float:
    ref = referencia.upper().replace(" ", "")
    hip = hipotesis.upper().replace(" ", "")

    if len(ref) == 0:
        return 0.0 if len(hip) == 0 else 1.0

    d = np.zeros((len(ref) + 1, len(hip) + 1), dtype=int)
    for i in range(len(ref) + 1):
        d[i][0] = i
    for j in range(len(hip) + 1):
        d[0][j] = j

    for i in range(1, len(ref) + 1):
        for j in range(1, len(hip) + 1):
            costo = 0 if ref[i - 1] == hip[j - 1] else 1
            d[i][j] = min(
                d[i - 1][j] + 1,
                d[i][j - 1] + 1,
                d[i - 1][j - 1] + costo
            )

    return d[len(ref)][len(hip)] / len(ref)


def es_alfanumerica_mixta(texto: str) -> bool:
    limpio = re.sub(r'[^A-Z0-9]', '', texto.upper())
    tiene_letra = any(c.isalpha() for c in limpio)
    tiene_numero = any(c.isdigit() for c in limpio)
    return tiene_letra and tiene_numero and len(limpio) >= 3


def es_texto_matricula(texto: str) -> bool:
    texto_limpio = re.sub(r'[^A-Z0-9\-]', '', texto.upper())
    return len(texto_limpio) >= 2


def area_caja(caja: np.ndarray) -> float:
    puntos = np.array(caja, dtype=np.float32)
    x = puntos[:, 0]
    y = puntos[:, 1]
    return 0.5 * abs(np.dot(x, np.roll(y, 1)) - np.dot(y, np.roll(x, 1)))


def seleccionar_matricula(candidatos: List[PlateCandidate]) -> List[PlateCandidate]:
    if not candidatos:
        return []

    mixtos = [
        candidato
        for candidato in candidatos
        if es_alfanumerica_mixta(candidato.texto)
    ]
    if mixtos:
        return mixtos

    areas = [area_caja(c.caja) if c.caja is not None else 0 for c in candidatos]
    idx_max = int(np.argmax(areas))
    return [candidatos[idx_max]]


def generar_resumen_texto(
    todos_los_textos: List[Tuple[str, float]],
    matricula_partes: List[PlateCandidate],
    texto_real: Optional[str] = None
) -> List[str]:
    resumen_texto = []
    resumen_texto.append("=" * 50)
    resumen_texto.append("        TODOS LOS TEXTOS DETECTADOS        ")
    resumen_texto.append("=" * 50)

    for texto, confianza in todos_los_textos:
        resumen_texto.append(f"  '{texto.strip()}' (confianza: {confianza:.2%})")

    resumen_texto.append("\n" + "=" * 50)
    resumen_texto.append("        MATRÍCULA DETECTADA        ")
    resumen_texto.append("=" * 50)

    if not matricula_partes:
        resumen_texto.append("  No se pudo aislar el número de matrícula.")
        return resumen_texto

    for candidato in matricula_partes:
        resumen_texto.append(f"  Fragmento : {candidato.texto}  (confianza: {candidato.confianza:.2%})")

    texto_matricula = ''.join([c.texto for c in matricula_partes])
    confianza_promedio = float(np.mean([c.confianza for c in matricula_partes]))

    resumen_texto.append(f"\n  MATRÍCULA FINAL : {texto_matricula}")
    resumen_texto.append(f"  Confianza media : {confianza_promedio:.2%}")

    if texto_real:
        cer = calcular_cer(texto_real, texto_matricula)
        resumen_texto.append("\n" + "=" * 50)
        resumen_texto.append("            MÉTRICAS CER            ")
        resumen_texto.append("=" * 50)
        resumen_texto.append(f"  Texto real      : {texto_real.upper()}")
        resumen_texto.append(f"  Texto OCR       : {texto_matricula}")
        resumen_texto.append(f"  CER             : {cer:.2%}")
        resumen_texto.append(f"  Precisión       : {(1 - cer):.2%}")

        if cer == 0.0:
            nivel = "PERFECTO - Reconocimiento exacto"
        elif cer <= 0.10:
            nivel = "EXCELENTE - Error menor al 10%"
        elif cer <= 0.30:
            nivel = "BUENO     - Error menor al 30%"
        elif cer <= 0.50:
            nivel = "REGULAR   - Error del 30-50%"
        else:
            nivel = "DEFICIENTE - Error mayor al 50%"
        resumen_texto.append(f"  Calidad         : {nivel}")

    return resumen_texto


def process_plate_image(ruta_imagen: str, texto_real: Optional[str] = None) -> DetectionResult:
    _, extension = os.path.splitext(ruta_imagen)
    if extension.lower() not in SUPPORTED_FORMATS:
        raise ValueError(f"Formato '{extension}' no soportado.")

    if not os.path.exists(ruta_imagen):
        raise FileNotFoundError(f"Archivo no encontrado: {ruta_imagen}")

    img = cv2.imread(ruta_imagen)
    if img is None:
        raise ValueError("No se pudo cargar la imagen.")

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    bfilter = cv2.bilateralFilter(
        gray,
        BILATERAL_FILTER_SIZE,
        BILATERAL_FILTER_SIGMA_COLOR,
        BILATERAL_FILTER_SIGMA_SPACE,
    )
    edged = cv2.Canny(bfilter, CANNY_THRESHOLD_LOW, CANNY_THRESHOLD_HIGH)

    keypoints = cv2.findContours(edged.copy(), cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
    contours = imutils.grab_contours(keypoints)
    contours = sorted(contours, key=cv2.contourArea, reverse=True)[:MAX_CONTOURS_TO_CHECK]

    location = None
    for contour in contours:
        peri = cv2.arcLength(contour, True)
        approx = cv2.approxPolyDP(contour, APPROX_CONTOUR_EPSILON * peri, True)
        if len(approx) == REQUIRED_POLYGON_POINTS:
            location = approx
            break

    if location is None:
        h, w = img.shape[:2]
        location = np.array([[[0, 0]], [[0, h - 1]], [[w - 1, h - 1]], [[w - 1, 0]]], dtype=np.int32)

    img_contorno = img.copy()
    cv2.drawContours(img_contorno, [location], 0, (0, 255, 0), 3)

    mask = np.zeros(gray.shape, np.uint8)
    cv2.drawContours(mask, [location], 0, 255, -1)
    (y, x) = np.where(mask == 255)
    (topx, topy) = (np.min(x), np.min(y))
    (bottomx, bottomy) = (np.max(x), np.max(y))

    cropped_color = img[topy:bottomy + 1, topx:bottomx + 1]
    border_type = cv2.BORDER_REFLECT if BORDER_TYPE == "reflect" else cv2.BORDER_CONSTANT
    cropped_padded = cv2.copyMakeBorder(
        cropped_color,
        BORDER_PADDING,
        BORDER_PADDING,
        BORDER_PADDING,
        BORDER_PADDING,
        border_type,
    )

    ocr = get_ocr_engine()

    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as archivo_temporal:
        ruta_temporal = archivo_temporal.name

    try:
        cv2.imwrite(ruta_temporal, cropped_padded)
        with _OCR_PREDICT_LOCK:
            resultados = list(ocr.predict(ruta_temporal))
    finally:
        if os.path.exists(ruta_temporal):
            os.remove(ruta_temporal)

    candidatos = []
    todos_los_textos = []
    img_ocr_filtrado = cropped_padded.copy()

    if resultados and resultados[0] is not None:
        for res in resultados:
            if res is None:
                continue
            textos = res.get('rec_texts', [])
            confianzas = res.get('rec_scores', [])
            cajas = res.get('dt_polys', [None] * len(textos))

            for texto, confianza, caja in zip(textos, confianzas, cajas):
                texto_limpio = re.sub(r'[^A-Z0-9\-]', '', texto.upper())
                todos_los_textos.append((texto, confianza))
                if es_texto_matricula(texto_limpio):
                    candidatos.append(PlateCandidate(texto=texto_limpio, confianza=confianza, caja=caja))

    matricula_partes = seleccionar_matricula(candidatos)
    matricula_partes.sort(
        key=lambda item: np.mean(np.array(item.caja, dtype=np.float32)[:, 0]) if item.caja is not None else 0
    )

    if matricula_partes:
        for candidato in matricula_partes:
            if candidato.caja is not None:
                try:
                    puntos = np.array(candidato.caja, dtype=np.int32)
                    cv2.polylines(img_ocr_filtrado, [puntos], isClosed=True, color=(0, 255, 0), thickness=2)
                    cv2.putText(
                        img_ocr_filtrado,
                        candidato.texto,
                        (puntos[0][0], puntos[0][1] - 8),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.7,
                        (0, 0, 255),
                        2,
                    )
                except Exception:
                    pass

    etapas = [
        ("1 - Original", img),
        ("2 - Bordes Canny", edged),
        ("3 - Contorno", img_contorno),
        ("4 - Recorte", cropped_padded),
        ("5 - Texto OCR", img_ocr_filtrado),
    ]

    resumen_texto = generar_resumen_texto(todos_los_textos, matricula_partes, texto_real)
    return DetectionResult(
        ruta_original=ruta_imagen,
        etapas=etapas,
        todos_los_textos=todos_los_textos,
        matricula_partes=matricula_partes,
        texto_real=texto_real,
        resumen_texto=resumen_texto,
    )
