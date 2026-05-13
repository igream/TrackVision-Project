import argparse


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
    parser.add_argument("--host", default="127.0.0.1", help="Host para la app web.")
    parser.add_argument("--port", default=8000, type=int, help="Puerto para la app web.")
    args = parser.parse_args()

    if args.desktop:
        iniciar_aplicacion_desktop()
    else:
        iniciar_aplicacion_web(args.host, args.port)
