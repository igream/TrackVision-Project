from dataclasses import dataclass, field
from typing import List, Tuple

import cv2
import numpy as np

from app.services.ocr_core import SUPPORTED_FORMATS


@dataclass
class VehicleRegion:
    bbox: Tuple[int, int, int, int]
    confidence: float
    crop: np.ndarray


@dataclass
class VehicleDetectionResult:
    ruta_original: str
    regions: List[VehicleRegion] = field(default_factory=list)
    debug_steps: List[Tuple[str, np.ndarray]] = field(default_factory=list)
    summary_text: List[str] = field(default_factory=list)

    @property
    def best_region(self) -> VehicleRegion | None:
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
    margin_x: float = 0.10,
    margin_y: float = 0.16,
) -> Tuple[int, int, int, int]:
    pad_x = int(w * margin_x)
    pad_y = int(h * margin_y)
    return _clip_bbox(x - pad_x, y - pad_y, w + 2 * pad_x, h + 2 * pad_y, image_shape)


def _vehicle_score(
    bbox: Tuple[int, int, int, int],
    contour_area: float,
    image_area: int,
    edges: np.ndarray,
) -> float:
    x, y, w, h = bbox
    if w <= 0 or h <= 0:
        return 0.0

    bbox_area = w * h
    aspect_ratio = w / float(h)
    area_ratio = bbox_area / float(image_area)
    rectangularity = min(1.0, contour_area / float(bbox_area))
    roi_edges = edges[y : y + h, x : x + w]
    edge_density = cv2.countNonZero(roi_edges) / float(bbox_area)
    image_h = edges.shape[0]
    center_y = (y + h / 2.0) / float(image_h)

    aspect_score = max(0.0, 1.0 - abs(aspect_ratio - 2.15) / 2.15)
    area_score = min(1.0, area_ratio / 0.42)
    fill_score = rectangularity
    texture_score = min(1.0, edge_density / 0.15)
    vertical_score = max(0.0, 1.0 - abs(center_y - 0.58) / 0.58)

    score = (
        0.34 * area_score
        + 0.24 * aspect_score
        + 0.18 * fill_score
        + 0.14 * texture_score
        + 0.10 * vertical_score
    )

    if area_ratio > 0.92:
        score *= 0.75
    if y <= 1 and h < image_h * 0.45:
        score *= 0.72
    return score


def _build_summary(regions: List[VehicleRegion], used_crop: bool) -> List[str]:
    lines = [
        "=" * 50,
        "DETECCION CLASICA DE VEHICULO",
        "=" * 50,
    ]

    if not regions:
        lines.append("No se encontro un carro principal confiable.")
        lines.append("Se uso la imagen completa como respaldo.")
        return lines

    best = regions[0]
    x, y, w, h = best.bbox
    lines.append(f"Candidatos encontrados: {len(regions)}")
    lines.append(f"Mejor bbox carro: x={x}, y={y}, w={w}, h={h}")
    lines.append(f"Confianza heuristica: {best.confidence:.2%}")
    lines.append(f"Entrada para placa/OCR: {'recorte del carro' if used_crop else 'imagen completa'}")
    lines.append("")
    lines.append("Metodo: gris, CLAHE, suavizado, Canny, cierre morfologico y contornos.")
    return lines


def detect_largest_vehicle_region(image_path: str, max_candidates: int = 4) -> VehicleDetectionResult:
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
    blurred = cv2.GaussianBlur(contrast, (5, 5), 0)
    edges = cv2.Canny(blurred, 45, 135)

    width = processed.shape[1]
    close_w = max(35, int(width * 0.08))
    close_h = max(13, int(close_w * 0.38))
    close_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (close_w, close_h))
    fill_kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (9, 9))
    mask = cv2.morphologyEx(edges, cv2.MORPH_CLOSE, close_kernel, iterations=2)
    mask = cv2.dilate(mask, fill_kernel, iterations=2)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, fill_kernel, iterations=2)

    contours, _ = cv2.findContours(mask.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    image_area = processed.shape[0] * processed.shape[1]

    candidates = []
    for contour in contours:
        x, y, w, h = cv2.boundingRect(contour)
        x, y, w, h = _clip_bbox(x, y, w, h, processed.shape)
        if w == 0 or h == 0:
            continue

        bbox_area = w * h
        area_ratio = bbox_area / float(image_area)
        aspect_ratio = w / float(h)
        if area_ratio < 0.08:
            continue
        if not 0.85 <= aspect_ratio <= 5.4:
            continue
        if w < processed.shape[1] * 0.20 or h < processed.shape[0] * 0.16:
            continue

        contour_area = cv2.contourArea(contour)
        score = _vehicle_score((x, y, w, h), contour_area, image_area, edges)
        if score < 0.26:
            continue
        candidates.append((score, (x, y, w, h)))

    candidates.sort(key=lambda item: item[0], reverse=True)

    annotated = processed.copy()
    regions = []
    for index, (score, bbox) in enumerate(candidates[:max_candidates], start=1):
        x, y, w, h = _expand_bbox(*bbox, processed.shape)
        cv2.rectangle(annotated, (x, y), (x + w, y + h), (255, 130, 0), 2)
        cv2.putText(
            annotated,
            f"{index}: {score:.2f}",
            (x, max(18, y - 8)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.55,
            (255, 80, 0),
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
        regions.append(VehicleRegion(bbox=(ox, oy, ow, oh), confidence=score, crop=crop))

    best_view = image.copy()
    if regions:
        x, y, w, h = regions[0].bbox
        cv2.rectangle(best_view, (x, y), (x + w, y + h), (255, 130, 0), 3)

    debug_steps = [
        ("1 - Original", image),
        ("2 - Bordes vehiculo", edges),
        ("3 - Mascara vehiculo", mask),
        ("4 - Carro principal", best_view),
    ]
    if regions:
        debug_steps.append(("5 - Recorte carro", regions[0].crop))

    used_crop = bool(regions)
    return VehicleDetectionResult(
        ruta_original=image_path,
        regions=regions,
        debug_steps=debug_steps,
        summary_text=_build_summary(regions, used_crop),
    )
