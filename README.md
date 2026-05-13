# OCR Placas

Aplicacion para detectar y leer matriculas vehiculares a partir de imagenes. El flujo usa OpenCV para localizar la placa, PaddleOCR para leer el texto y una interfaz web responsive para cargar imagenes, revisar las etapas del procesamiento y consultar el resultado.

## Estado actual

- Interfaz web local con diseño responsive para computadora y celular.
- Carga de imagenes desde el navegador.
- Carrusel con las etapas del procesamiento: original, bordes, contorno, recorte y texto OCR.
- Resumen de textos detectados, matricula final y confianza media.
- Guardado automatico de resultados en la carpeta `Detecciones/`.
- Interfaz anterior de escritorio disponible de forma opcional.

## Estructura principal

- `app.py`: punto de entrada principal. Inicia la version web por defecto.
- `web_app.py`: servidor HTTP local y endpoint `/api/process`.
- `templates/index.html`: estructura de la interfaz web.
- `static/app.css`: estilos responsive en tonalidades blanco y azul rey.
- `static/app.js`: logica del frontend, carga de imagenes y carrusel.
- `ocr_core.py`: procesamiento de imagenes y lectura OCR.
- `storage.py`: guardado de resultados.
- `gui.py`: interfaz anterior de escritorio con Tkinter.
- `config/backend.py`: parametros de OCR y procesamiento.
- `config/frontend.py`: configuracion visual de la interfaz de escritorio.
- `src/LogoInApp.PNG`: logo de la aplicacion.

## Requisitos

- Python 3.10
- Windows, macOS o Linux
- Dependencias de `requirements.txt`

## Instalacion

Desde PowerShell:

```powershell
cd "c:\Users\Fer\Desktop\OCR Placas"
py -3.10 -m venv .venv310
.\.venv310\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

Si el entorno virtual ya existe, solo activalo:

```powershell
.\.venv310\Scripts\Activate.ps1
```

## Uso web

Ejecuta:

```powershell
python app.py
```

Luego abre en el navegador:

```text
http://127.0.0.1:8000
```

Tambien puedes indicar host y puerto:

```powershell
python app.py --host 0.0.0.0 --port 8000
```

Usa `0.0.0.0` si quieres probar desde otro dispositivo en la misma red. En ese caso entra desde el celular o computadora usando la IP local del equipo donde corre el servidor.

## Uso de escritorio

La interfaz anterior con Tkinter sigue disponible:

```powershell
python app.py --desktop
```

## Resultados generados

Cada procesamiento guarda informacion en:

```text
Detecciones/
```

La carpeta se organiza por tipo de resultado, fecha y hora. Incluye:

- `informacion.txt`
- imagen original
- bordes Canny
- contorno detectado
- recorte de la placa
- imagen con texto OCR

## Formatos soportados

- `.jpg`
- `.jpeg`
- `.png`
- `.bmp`
- `.tiff`
- `.tif`
- `.webp`

## Verificacion rapida

Para comprobar que los archivos Python cargan correctamente:

```powershell
python -m py_compile app.py web_app.py gui.py ocr_core.py storage.py
```

Para validar que la web responde, ejecuta la app y abre:

```text
http://127.0.0.1:8000
```

## Notas de desarrollo

- No subir carpetas de entorno virtual como `.venv/`, `.venv310/`, `venv/` o `ENV/`.
- No subir `__pycache__/` ni archivos temporales.
- Si se mueve el proyecto a Linux o a un despliegue web, conserva el nombre del logo respetando mayusculas y minusculas: `src/LogoInApp.PNG`.
- El servidor actual usa la libreria estandar de Python. Para produccion convendria migrar el backend a FastAPI o Flask y servir el frontend con un servidor web dedicado.
