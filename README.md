# OCR Placas

Aplicacion web para detectar placas vehiculares y leer su texto mediante procesamiento digital de imagenes y OCR.

## Requisitos

- Python 3.10
- Windows, macOS o Linux
- Un entorno virtual local

## Instalacion

1. Entrar a la carpeta del proyecto.

```powershell
cd "ruta\al\proyecto"
```

2. Crear y activar el entorno virtual.

```powershell
py -3.10 -m venv .venv310
.\.venv310\Scripts\Activate.ps1
```

En macOS o Linux:

```bash
python3.10 -m venv .venv310
source .venv310/bin/activate
```

3. Instalar dependencias.

```powershell
python -m pip install --upgrade pip
pip install -r requirements.txt
```

## Ejecucion

Iniciar la version web:

```powershell
python app.py
```

Abrir en el navegador:

```text
http://127.0.0.1:8000
```

Tambien es posible cambiar host y puerto:

```powershell
python app.py --host 0.0.0.0 --port 8000
```

Para usar la interfaz anterior de escritorio:

```powershell
python app.py --desktop
```

## Flujo de uso

1. Cargar una imagen del vehiculo.
2. Elegir el modo:
   - `Detectar placa`: localiza la region de la placa con PDI clasico.
   - `Leer texto OCR`: procesa una placa y extrae el texto.
3. Ejecutar el analisis.
4. Revisar el carrusel de etapas y el resumen en pantalla.

## Configuracion

Los valores principales se pueden ajustar con variables de entorno.

- `OCR_WEB_HOST`: host por defecto del servidor web.
- `OCR_WEB_PORT`: puerto por defecto del servidor web.
- `OCR_SAVE_BASE_DIR`: carpeta donde se guardan los resultados.

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

## Estructura del proyecto

- `app.py`: punto de entrada principal.
- `web_app.py`: servidor web local y endpoints `api/process` y `api/detect`.
- `plate_detector.py`: detector clasico de placas con PDI.
- `evaluate_plate_detector.py`: evaluacion del detector contra el dataset local.
- `ocr_core.py`: pipeline de OCR y postprocesamiento.
- `storage.py`: guardado de resultados.
- `templates/index.html`: vista principal.
- `static/app.css`: estilos.
- `static/app.js`: interaccion del frontend.
- `config/backend.py`: configuracion de OCR, servidor y guardado.
- `config/frontend.py`: configuracion visual de la interfaz de escritorio.

## Resultados generados

Los resultados se guardan en la carpeta definida por `OCR_SAVE_BASE_DIR`. Si no se define, se usa `Detecciones/` dentro del proyecto.

Cada ejecucion puede generar:

- `informacion.txt`
- imagen original
- bordes o mascara de procesamiento
- contornos o region detectada
- recorte de placa
- imagen con texto OCR

## Formatos soportados

- `.jpg`
- `.jpeg`
- `.png`
- `.bmp`
- `.tiff`
- `.tif`
- `.webp`

## Evaluacion del detector

Si el dataset esta disponible en `datasets/car_plate_detection/`, la deteccion clasica puede evaluarse con:

```powershell
python evaluate_plate_detector.py --limit 50
```

Para evaluar mas imagenes, aumentar el limite o usar `--limit 0` para intentar todo el dataset.

## Verificacion rapida

Compilar los archivos principales:

```powershell
python -m py_compile app.py web_app.py gui.py ocr_core.py storage.py plate_detector.py evaluate_plate_detector.py config\backend.py config\frontend.py
```

Abrir la aplicacion web y comprobar que responde en:

```text
http://127.0.0.1:8000
```

## Notas

- `Detecciones/` y `datasets/` estan ignorados para evitar subir archivos generados o conjuntos de datos grandes.
- El logo debe conservarse en `src/LogoInApp.PNG`.
- El backend actual usa la biblioteca estandar de Python y es suficiente para pruebas y desarrollo local.
