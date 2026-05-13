from dataclasses import dataclass, field
from typing import List, Tuple

import cv2
import numpy as np

from app.services.ocr_core import SUPPORTED_FORMATS


@dataclass
class PlateRegion:
    bbox: Tuple[int, int, int, int]
    confidence: float
    crop: np.ndarray


@dataclass
class PlateDetectionResult:
    ruta_original: str
    regions: List[PlateRegion] = field(default_factory=list)
    debug_steps: List[Tuple[str, np.ndarray]] = field(default_factory=list)
    summary_text: List[str] = field(default_factory=list)

    @property
    def best_region(self) -> PlateRegion | None:
        if not self.regions:
            return None
        return self.regions[0]


def _resize_for_processing(image: np.ndarray, max_width: int = 900) -> Tuple[np.ndarray, float]:
    height, width = image.shape[:2]
    if width <= max_width:
        return image.copy(), 1.0

    scale = max_width / float(width)
    resized = cv2.resize(image, (max_width, int(height * scale)), interpolation=cv2.INTER_AREA)
    return resized, scale


def _normalize_to_uint8(image: np.ndarray) -> np.ndarray:
    image = image.astype("float32")
    min_value = float(image.min())
    max_value = float(image.max())
    if max_value - min_value < 1e-6:
        return np.zeros(image.shape, dtype=np.uint8)
    normalized = 255 * (image - min_value) / (max_value - min_value)
    return normalized.astype(np.uint8)


def _clip_bbox(x: int, y: int, w: int, h: int, image_shape) -> Tuple[int, int, int, int]:
    image_h, image_w = image_shape[:2]
    x1 = max(0, x)
    y1 = max(0, y)
    x2 = min(image_w, x + w)
    y2 = min(image_h, y + h)
    return x1, y1, max(0, x2 - x1), max(0, y2 - y1)


def _expand_bbox(
    x: int,
    y: int,
    w: int,
    h: int,
    image_shape,
    margin_x: float = 0.08,
    margin_y: float = 0.18,
) -> Tuple[int, int, int, int]:
    pad_x = int(w * margin_x)
    pad_y = int(h * margin_y)
    return _clip_bbox(x - pad_x, y - pad_y, w + 2 * pad_x, h + 2 * pad_y, image_shape)


def _candidate_score(
    bbox: Tuple[int, int, int, int],
    contour_area: float,
    image_area: int,
    edges: np.ndarray,
) -> float:
    x, y, w, h = bbox
    if w <= 0 or h <= 0:
        return 0.0

    aspect_ratio = w / float(h)
    bbox_area = w * h
    area_ratio = bbox_area / float(image_area)
    rectangularity = contour_area / float(bbox_area)
    roi_edges = edges[y : y + h, x : x + w]
    edge_density = cv2.countNonZero(roi_edges) / float(bbox_area)
    image_h = edges.shape[0]
    center_y = (y + h / 2.0) / float(image_h)

    aspect_score = max(0.0, 1.0 - abs(aspect_ratio - 4.0) / 3.0)
    area_score = min(1.0, area_ratio / 0.04)
    rectangle_score = min(1.0, rectangularity)
    edge_score = min(1.0, edge_density / 0.28)
    vertical_score = max(0.0, 1.0 - abs(center_y - 0.58) / 0.58)

    score = (
        0.32 * aspect_score
        + 0.20 * area_score
        + 0.20 * rectangle_score
        + 0.16 * edge_score
        + 0.12 * vertical_score
    )
    if y <= 2:
        score *= 0.72
    return score


def _build_summary(regions: List[PlateRegion]) -> List[str]:
    lines = [
        "=" * 50,
        "DETECCION CLASICA DE PLACA",
        "=" * 50,
    ]

    if not regions:
        lines.append("No se encontro una region candidata de placa.")
        lines.append("Prueba con una imagen mas iluminada o con la placa mas visible.")
        return lines

    best = regions[0]
    x, y, w, h = best.bbox
    lines.append(f"Candidatos encontrados: {len(regions)}")
    lines.append(f"Mejor bbox: x={x}, y={y}, w={w}, h={h}")
    lines.append(f"Confianza heuristica: {best.confidence:.2%}")
    lines.append("")
    lines.append("Metodo: gris, contraste, blackhat, gradiente horizontal, umbral y contornos.")
    return lines


def detect_plate_regions(image_path: str, max_candidates: int = 5) -> PlateDetectionResult:
    extension = "." + image_path.rsplit(".", 1)[-1].lower() if "." in image_path else ""
    if extension not in SUPPORTED_FORMATS:
        raise ValueError(f"Formato '{extension or 'sin extension'}' no soportado.")

    image = cv2.imread(image_path)
    if image is None:
        raise ValueError("No se pudo cargar la imagen.")

    processed, scale = _resize_for_processing(image)
    gray = cv2.cvtColor(processed, cv2.COLOR_BGR2GRAY)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    contrast = clahe.apply(gray)
    blurred = cv2.bilateralFilter(contrast, 9, 75, 75)

    rect_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (25, 7))
    square_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
    blackhat = cv2.morphologyEx(blurred, cv2.MORPH_BLACKHAT, rect_kernel)

    grad_x = cv2.Sobel(blackhat, ddepth=cv2.CV_32F, dx=1, dy=0, ksize=3)
    grad_x = _normalize_to_uint8(np.absolute(grad_x))
    grad_x = cv2.GaussianBlur(grad_x, (5, 5), 0)
    grad_x = cv2.morphologyEx(grad_x, cv2.MORPH_CLOSE, rect_kernel)

    _, thresh = cv2.threshold(grad_x, 0, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)
    thresh = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, rect_kernel)
    thresh = cv2.erode(thresh, square_kernel, iterations=1)
    thresh = cv2.dilate(thresh, square_kernel, iterations=1)

    edges = cv2.Canny(blurred, 80, 180)
    contours, _ = cv2.findContours(thresh.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    image_area = processed.shape[0] * processed.shape[1]

    candidates = []
    for contour in contours:
        x, y, w, h = cv2.boundingRect(contour)
        x, y, w, h = _clip_bbox(x, y, w, h, processed.shape)
        if w == 0 or h == 0:
            continue
        if w < 45 or h < 16:
            continue

        aspect_ratio = w / float(h)
        area = w * h
        area_ratio = area / float(image_area)
        if not 2.0 <= aspect_ratio <= 6.5:
            continue
        if not 0.002 <= area_ratio <= 0.18:
            continue

        contour_area = cv2.contourArea(contour)
        score = _candidate_score((x, y, w, h), contour_area, image_area, edges)
        if score < 0.18:
            continue

        candidates.append((score, (x, y, w, h)))

    candidates.sort(key=lambda item: item[0], reverse=True)

    annotated = processed.copy()
    regions = []
    for index, (score, bbox) in enumerate(candidates[:max_candidates], start=1):
        x, y, w, h = _expand_bbox(*bbox, processed.shape)
        cv2.rectangle(annotated, (x, y), (x + w, y + h), (0, 180, 255), 2)
        cv2.putText(
            annotated,
            f"{index}: {score:.2f}",
            (x, max(18, y - 8)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.55,
            (0, 80, 255),
            2,
        )

        original_bbox = (
            int(x / scale),
            int(y / scale),
            int(w / scale),
            int(h / scale),
        )
        ox, oy, ow, oh = _clip_bbox(*original_bbox, image.shape)
        crop = image[oy : oy + oh, ox : ox + ow]
        regions.append(PlateRegion(bbox=(ox, oy, ow, oh), confidence=score, crop=crop))

    best_view = image.copy()
    if regions:
        x, y, w, h = regions[0].bbox
        cv2.rectangle(best_view, (x, y), (x + w, y + h), (0, 220, 0), 3)

    debug_steps = [
        ("1 - Original", image),
        ("2 - Escala de grises", gray),
        ("3 - Contraste CLAHE", contrast),
        ("4 - Blackhat", blackhat),
        ("5 - Gradiente horizontal", grad_x),
        ("6 - Mascara morfologica", thresh),
        ("7 - Candidatos", annotated),
        ("8 - Mejor deteccion", best_view),
    ]
    if regions:
        debug_steps.append(("9 - Recorte de placa", regions[0].crop))

    return PlateDetectionResult(
        ruta_original=image_path,
        regions=regions,
        debug_steps=debug_steps,
        summary_text=_build_summary(regions),
    )
