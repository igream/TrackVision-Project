import argparse
import xml.etree.ElementTree as ET
from pathlib import Path

from app.services.plate_detector import detect_plate_regions


def _read_ground_truth(xml_path: Path) -> tuple[int, int, int, int]:
    root = ET.parse(xml_path).getroot()
    box = root.find(".//bndbox")
    if box is None:
        raise ValueError(f"No bndbox found in {xml_path}")

    xmin = int(box.findtext("xmin", "0"))
    ymin = int(box.findtext("ymin", "0"))
    xmax = int(box.findtext("xmax", "0"))
    ymax = int(box.findtext("ymax", "0"))
    return xmin, ymin, xmax - xmin, ymax - ymin


def _iou(box_a: tuple[int, int, int, int], box_b: tuple[int, int, int, int]) -> float:
    ax, ay, aw, ah = box_a
    bx, by, bw, bh = box_b
    ax2 = ax + aw
    ay2 = ay + ah
    bx2 = bx + bw
    by2 = by + bh

    inter_x1 = max(ax, bx)
    inter_y1 = max(ay, by)
    inter_x2 = min(ax2, bx2)
    inter_y2 = min(ay2, by2)
    inter_w = max(0, inter_x2 - inter_x1)
    inter_h = max(0, inter_y2 - inter_y1)
    intersection = inter_w * inter_h

    union = aw * ah + bw * bh - intersection
    if union <= 0:
        return 0.0
    return intersection / union


def evaluate(dataset_dir: Path, limit: int | None, threshold: float) -> None:
    images_dir = dataset_dir / "images"
    annotations_dir = dataset_dir / "annotations"
    image_paths = sorted(images_dir.glob("*.png"))
    if limit:
        image_paths = image_paths[:limit]

    total = 0
    detected = 0
    matched = 0
    iou_sum = 0.0

    for image_path in image_paths:
        xml_path = annotations_dir / f"{image_path.stem}.xml"
        if not xml_path.exists():
            continue

        total += 1
        ground_truth = _read_ground_truth(xml_path)
        result = detect_plate_regions(str(image_path))
        best = result.best_region
        if best is None:
            print(f"{image_path.name}: no detection")
            continue

        detected += 1
        score = _iou(best.bbox, ground_truth)
        iou_sum += score
        if score >= threshold:
            matched += 1

        print(
            f"{image_path.name}: iou={score:.3f} "
            f"confidence={best.confidence:.3f} bbox={best.bbox}"
        )

    mean_iou = iou_sum / detected if detected else 0.0
    detection_rate = detected / total if total else 0.0
    match_rate = matched / total if total else 0.0

    print("")
    print("=" * 50)
    print(f"Images evaluated : {total}")
    print(f"Detected         : {detected} ({detection_rate:.2%})")
    print(f"IoU >= {threshold:.2f}     : {matched} ({match_rate:.2%})")
    print(f"Mean IoU         : {mean_iou:.3f}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate classic plate detector.")
    parser.add_argument(
        "--dataset",
        default="datasets/car_plate_detection",
        type=Path,
        help="Dataset directory with images/ and annotations/ folders.",
    )
    parser.add_argument("--limit", type=int, default=25, help="Maximum images to evaluate.")
    parser.add_argument("--threshold", type=float, default=0.5, help="IoU threshold for success.")
    args = parser.parse_args()

    evaluate(args.dataset, args.limit, args.threshold)


if __name__ == "__main__":
    main()
