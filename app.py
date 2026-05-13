import argparse

from config.backend import WEB_HOST, WEB_PORT


def iniciar_aplicacion_desktop() -> None:
    from gui import OCRApp

    app = OCRApp()
    app.run()


def iniciar_aplicacion_web(host: str, port: int) -> None:
    from web_app import run_server

    run_server(host=host, port=port)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="OCR Placas")
    parser.add_argument("--desktop", action="store_true", help="Abrir la interfaz anterior de escritorio.")
    parser.add_argument("--host", default=WEB_HOST, help="Host para la app web.")
    parser.add_argument("--port", default=WEB_PORT, type=int, help="Puerto para la app web.")
    args = parser.parse_args()

    if args.desktop:
        iniciar_aplicacion_desktop()
    else:
        iniciar_aplicacion_web(args.host, args.port)
