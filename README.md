# OCR Placas

Aplicacion web para detectar y leer matriculas vehiculares a partir de imagenes. El flujo usa OpenCV para localizar la placa, PaddleOCR para leer el texto y una interfaz responsive para cargar imagenes, revisar las etapas del procesamiento y consultar el resultado.

## Estado actual

- Interfaz web local para computadora y celular.
- Carga de imagenes desde el navegador.
- Carrusel con las etapas del procesamiento: original, bordes, contorno, recorte y texto OCR.
- Resumen de textos detectados, matricula final y confianza media.
- Guardado automatico de resultados en `Detecciones/`.
- Interfaz anterior de escritorio disponible como modo opcional.

## Estructura principal

- `app.py`: punto de entrada principal. Inicia la version web por defecto.
- `web_app.py`: servidor HTTP local y endpoint `/api/process`.
- `templates/index.html`: estructura de la interfaz web.
- `static/app.css`: estilos responsive en blanco y azul rey.
- `static/app.js`: logica del frontend, carga de imagenes y carrusel.
- `ocr_core.py`: procesamiento de imagenes y lectura OCR.
- `storage.py`: guardado de resultados.
- `gui.py`: interfaz anterior de escritorio con Tkinter.
- `config/backend.py`: parametros del servidor, OCR, procesamiento y guardado.
- `config/frontend.py`: configuracion visual de la interfaz de escritorio.
- `src/LogoInApp.PNG`: logo de la aplicacion.

## Requisitos

- Python 3.10
- Windows, macOS o Linux
- Dependencias de `requirements.txt`

## Instalacion

Clona o copia el proyecto y entra a la carpeta raiz:

```powershell
cd "ruta\al\proyecto"
```

Crea y activa un entorno virtual:

```powershell
py -3.10 -m venv .venv310
.\.venv310\Scripts\Activate.ps1
```

En macOS o Linux:

```bash
python3.10 -m venv .venv310
source .venv310/bin/activate
```

Instala dependencias:

```powershell
python -m pip install --upgrade pip
pip install -r requirements.txt
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

## Configuracion

El proyecto evita rutas absolutas del equipo local. Los valores principales se calculan desde la carpeta del proyecto o se pueden cambiar con variables de entorno.

Variables disponibles:

- `OCR_WEB_HOST`: host por defecto del servidor web. Valor inicial: `127.0.0.1`.
- `OCR_WEB_PORT`: puerto por defecto del servidor web. Valor inicial: `8000`.
- `OCR_SAVE_BASE_DIR`: carpeta donde se guardan los resultados. Valor inicial: `Detecciones/` dentro del proyecto.

Ejemplo en PowerShell:

```powershell
$env:OCR_WEB_PORT = "8080"
$env:OCR_SAVE_BASE_DIR = ".\Resultados"
python app.py
```

Ejemplo en bash:

```bash
export OCR_WEB_PORT=8080
export OCR_SAVE_BASE_DIR="$HOME/OCR_Resultados"
python app.py
```

## Uso de escritorio

La interfaz anterior con Tkinter sigue disponible:

```powershell
python app.py --desktop
```

## Resultados generados

Cada procesamiento guarda informacion en la carpeta configurada por `OCR_SAVE_BASE_DIR`. Si no se configura, se usa:

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

`Detecciones/` esta en `.gitignore` porque contiene archivos generados y puede incluir datos de pruebas.

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
python -m py_compile app.py web_app.py gui.py ocr_core.py storage.py config\backend.py config\frontend.py
```

En macOS o Linux:

```bash
python -m py_compile app.py web_app.py gui.py ocr_core.py storage.py config/backend.py config/frontend.py
```

Para validar que la web responde, ejecuta la app y abre:

```text
http://127.0.0.1:8000
```

## Compartir el proyecto

Antes de compartir o subir el proyecto:

- No incluyas entornos virtuales como `.venv/`, `.venv310/`, `venv/` o `ENV/`.
- No incluyas `__pycache__/`, logs ni archivos temporales.
- No incluyas `Detecciones/` salvo que quieras compartir resultados de prueba.
- Conserva el logo con el nombre `src/LogoInApp.PNG`, respetando mayusculas y minusculas para compatibilidad con Linux.
- Si cambias rutas de salida o puerto, documentalo mediante variables de entorno, no con rutas absolutas dentro del codigo.

## Nota de produccion

El servidor actual usa la libreria estandar de Python y es suficiente para pruebas locales o demostraciones. Para produccion conviene migrar el backend a FastAPI o Flask y servir el frontend con un servidor web dedicado.
