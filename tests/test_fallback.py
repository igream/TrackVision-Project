import argparse
from pathlib import Path

import cv2
import numpy as np


def inspect_full_image_fallback(image_path: Path) -> None:
    image = cv2.imread(str(image_path))
    if image is None:
        raise ValueError(f"No se pudo cargar la imagen: {image_path}")

    height, width = image.shape[:2]
    location = np.array([[[0, 0]], [[0, height - 1]], [[width - 1, height - 1]], [[width - 1, 0]]], dtype=np.int32)

    mask = np.zeros(image.shape[:2], np.uint8)
    cv2.drawContours(mask, [location], 0, 255, -1)

    y, x = np.where(mask == 255)
    topx, topy = np.min(x), np.min(y)
    bottomx, bottomy = np.max(x), np.max(y)
    cropped_color = image[topy : bottomy + 1, topx : bottomx + 1]

    print("Original shape:", image.shape)
    print("Cropped shape:", cropped_color.shape)


def main() -> None:
    parser = argparse.ArgumentParser(description="Inspect the full-image crop fallback used by OCR.")
    parser.add_argument(
        "--image",
        type=Path,
        default=Path("datasets/car_plate_detection/images/Cars0.png"),
        help="Image to inspect.",
    )
    args = parser.parse_args()
    inspect_full_image_fallback(args.image)


if __name__ == "__main__":
    main()
