import argparse
from pathlib import Path

import requests


def upload_file(session: requests.Session, url: str, path: Path) -> None:
    with path.open("rb") as file_obj:
        files = {"plate_image": (path.name, file_obj)}
        data = {"mode": "ocr"}
        response = session.post(url, files=files, data=data, timeout=120)

    print(f"Process {path.name}: {response.status_code}")
    if response.status_code != 200:
        print(response.text)


def main() -> None:
    parser = argparse.ArgumentParser(description="Upload sample plate images to a running local server.")
    parser.add_argument("--base-url", default="http://127.0.0.1:8000", help="Running OCR Placas server URL.")
    parser.add_argument("--username", default="testuser99")
    parser.add_argument("--password", default="password123")
    parser.add_argument("--limit", type=int, default=10)
    parser.add_argument(
        "--images-dir",
        type=Path,
        default=Path("datasets/car_plate_detection/images"),
        help="Directory containing sample images.",
    )
    args = parser.parse_args()

    session = requests.Session()
    credentials = {"username": args.username, "password": args.password}
    session.post(f"{args.base_url}/register", data=credentials, timeout=30)
    session.post(f"{args.base_url}/login", data=credentials, timeout=30)

    for image_path in sorted(args.images_dir.glob("*.png"))[: args.limit]:
        upload_file(session, f"{args.base_url}/api/process", image_path)


if __name__ == "__main__":
    main()
