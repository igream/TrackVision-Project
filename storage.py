import os
import re
from typing import Optional

from config.backend import SAVE_BASE_DIR
from ocr_core import DetectionResult


def _sanitize_filename(value: str) -> str:
    return re.sub(r'[^a-zA-Z0-9_-]', '_', value)


def save_detection_result(result: DetectionResult, base_dir: Optional[str] = None) -> str:
    base_dir = base_dir or SAVE_BASE_DIR
    carpeta_hora = os.path.join(base_dir, result.tipo, result.fecha, result.hora)
    os.makedirs(carpeta_hora, exist_ok=True)

    info_path = os.path.join(carpeta_hora, "informacion.txt")
    with open(info_path, "w", encoding="utf-8") as archivo:
        archivo.write(f"Fecha: {result.fecha}\n")
        archivo.write(f"Hora: {result.hora}\n")
        archivo.write(f"Tipo: {result.tipo}\n")
        archivo.write(f"Ruta original: {result.ruta_original}\n")
        archivo.write(f"Confianza media: {result.promedio_confianza:.2%}\n")
        archivo.write("\n")

        if result.matricula_partes:
            archivo.write(f"Matrícula final: {result.texto_matricula}\n")
            archivo.write("Fragmentos detectados:\n")
            for candidato in result.matricula_partes:
                archivo.write(f"  - {candidato.texto} (confianza: {candidato.confianza:.2%})\n")
        else:
            archivo.write("Matrícula final: No se pudo aislar una matrícula válida.\n")

        archivo.write("\nTextos detectados:\n")
        for texto, confianza in result.todos_los_textos:
            archivo.write(f"  - {texto} (confianza: {confianza:.2%})\n")

        archivo.write("\nResumen completo:\n")
        for linea in result.resumen_texto:
            archivo.write(linea + "\n")

    for indice, (titulo, imagen) in enumerate(result.etapas, start=1):
        safe_title = _sanitize_filename(titulo.replace(" ", "_"))
        nombre = f"{indice:02d}_{safe_title}.png"
        ruta_img = os.path.join(carpeta_hora, nombre)
        cv2_image = imagen
        try:
            import cv2
            cv2.imwrite(ruta_img, cv2_image)
        except Exception:
            # Si falla la guardada con OpenCV, ignora la imagen.
            pass

    return carpeta_hora
