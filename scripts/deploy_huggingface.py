import argparse
import os
import secrets
import shutil
import tempfile
from pathlib import Path

from huggingface_hub import HfApi, create_repo


ROOT = Path(__file__).resolve().parent.parent
HF_README = ROOT / "deploy" / "huggingface" / "README.md"
INCLUDE_PATHS = [
    "Dockerfile",
    ".dockerignore",
    "requirements.txt",
    "run.py",
    "app",
    "img",
    "src",
]
IGNORE_DIRS = {"__pycache__", "Detecciones"}
IGNORE_SUFFIXES = {".pyc", ".pyo", ".pyd"}


def should_skip(path: Path) -> bool:
    return any(part in IGNORE_DIRS for part in path.parts) or path.suffix in IGNORE_SUFFIXES


def copy_item(source: Path, destination: Path) -> None:
    if source.is_dir():
        for child in source.rglob("*"):
            relative = child.relative_to(source)
            target = destination / relative
            if should_skip(relative):
                continue
            if child.is_dir():
                target.mkdir(parents=True, exist_ok=True)
            else:
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(child, target)
    else:
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)


def build_stage(stage_dir: Path) -> None:
    if not HF_README.exists():
        raise FileNotFoundError(f"No existe el README de Hugging Face: {HF_README}")

    for relative_path in INCLUDE_PATHS:
        source = ROOT / relative_path
        if not source.exists():
            raise FileNotFoundError(f"No existe el archivo requerido: {source}")
        copy_item(source, stage_dir / relative_path)

    shutil.copy2(HF_README, stage_dir / "README.md")


def configure_space(api: HfApi, repo_id: str, session_secret: str | None) -> None:
    variables = {
        "OCR_WEB_HOST": "0.0.0.0",
        "OCR_WEB_PORT": "7860",
        "OCR_SAVE_BASE_DIR": "/tmp/Detecciones",
        "OCR_SESSION_SECURE": "true",
    }
    for key, value in variables.items():
        api.add_space_variable(repo_id=repo_id, key=key, value=value)

    api.add_space_secret(
        repo_id=repo_id,
        key="OCR_SESSION_SECRET",
        value=session_secret or secrets.token_urlsafe(48),
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Despliega TrackVision en Hugging Face Spaces.")
    parser.add_argument("--repo-id", default=os.getenv("HF_SPACE_ID", "igream/TrackVision-Project"))
    parser.add_argument("--create", action="store_true", help="Crea el Space si no existe.")
    parser.add_argument("--private", action="store_true", help="Crea el Space como privado al usar --create.")
    parser.add_argument("--configure", action="store_true", help="Configura variables de entorno del Space.")
    parser.add_argument(
        "--session-secret",
        default=os.getenv("OCR_SESSION_SECRET"),
        help="Secreto de sesión para Hugging Face. También puede venir de OCR_SESSION_SECRET.",
    )
    parser.add_argument("--commit-message", default="Deploy TrackVision Docker Space")
    args = parser.parse_args()

    api = HfApi()
    if args.create:
        create_repo(
            repo_id=args.repo_id,
            repo_type="space",
            space_sdk="docker",
            private=args.private,
            exist_ok=True,
        )

    if args.configure:
        configure_space(api, args.repo_id, args.session_secret)

    with tempfile.TemporaryDirectory(prefix="trackvision-hf-") as temp_dir:
        stage_dir = Path(temp_dir)
        build_stage(stage_dir)
        api.upload_folder(
            repo_id=args.repo_id,
            repo_type="space",
            folder_path=stage_dir,
            path_in_repo=".",
            commit_message=args.commit_message,
        )

    print(f"Despliegue enviado a https://huggingface.co/spaces/{args.repo_id}")


if __name__ == "__main__":
    main()
