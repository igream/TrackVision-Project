# Detección de Placas Vehiculares

Aplicación para la detección y lectura de matrículas vehiculares (ALPR) utilizando Procesamiento Digital de Imágenes (PDI) y Reconocimiento Óptico de Caracteres (OCR).

## Características

* **Backend:** Implementado con [FastAPI](https://fastapi.tiangolo.com/), proporcionando soporte para operaciones asíncronas y concurrencia.
* **Autenticación:** Sistema de registro y acceso de usuarios, utilizando la biblioteca `bcrypt` para el cifrado de contraseñas.
* **Captura de Imagen:** Permite cargar archivos desde el almacenamiento local o capturar fotografías desde una cámara conectada al dispositivo.
* **Persistencia de Datos:** Utiliza `SQLite` y `SQLAlchemy` para almacenar los resultados y metadatos. Las imágenes originales se almacenan en la base de datos en formato BLOB.
* **Flujo de Detección:**
  * **Detección PDI:** Proceso algorítmico clásico que aísla contornos que coinciden con las proporciones de una placa vehicular.
  * **Lectura OCR:** Extracción de texto mediante el modelo de red neuronal `PaddleOCR`.

---

## Requisitos

- **Python 3.10+**
- Windows, macOS o Linux

---

## Instalación

1. Clonar o descargar el repositorio y abrir una terminal en la raíz del proyecto.
   ```powershell
   cd "ruta\al\proyecto"
   ```

2. Crear y activar un entorno virtual.
   **En Windows:**
   ```powershell
   py -3.10 -m venv .venv310
   .\.venv310\Scripts\Activate.ps1
   ```
   **En macOS o Linux:**
   ```bash
   python3.10 -m venv .venv310
   source .venv310/bin/activate
   ```

3. Actualizar `pip` e instalar las dependencias listadas.
   ```powershell
   python -m pip install --upgrade pip
   pip install -r requirements.txt
   ```

---

## Ejecución

El punto de entrada del servidor es `run.py`. Para iniciar la aplicación web:

```powershell
python run.py
```

El servidor iniciará en el puerto 8000 por defecto. Para acceder a la aplicación, abrir un navegador web en la siguiente dirección:

```text
http://127.0.0.1:8000
```

*(Para especificar una dirección IP o puerto distinto, utilizar las banderas correspondientes: `python run.py --host 0.0.0.0 --port 8080`)*

---

## Uso

1. **Autenticación:**
   - Es necesario iniciar sesión con un usuario registrado para acceder al procesamiento.

2. **Carga de Imagen:**
   - **Desde el dispositivo:** Seleccionar la pestaña "Cargar Imagen" para elegir un archivo local (.jpg, .png, etc.).
   - **Desde la cámara:** Seleccionar la pestaña "Tomar Foto" para habilitar la captura web.

3. **Procesamiento:**
   - **Detectar placa:** Aplica transformaciones de PDI para ubicar el área de la placa y realizar el recorte. Permite enviar este recorte a lectura OCR posteriormente.
   - **Leer texto OCR:** Extrae el texto alfanumérico directamente de la imagen suministrada.

4. **Resultados:**
   Las imágenes del proceso y los textos detectados se muestran en la interfaz en un carrusel. El resumen del resultado y la imagen original se almacenan automáticamente en la base de datos.

---

## Estructura del Proyecto

El proyecto sigue una arquitectura modular en directorios:

* `run.py`: Punto de entrada de la aplicación.
* `app/`: Directorio principal del código fuente de la aplicación.
  * `app/main.py`: Inicialización de FastAPI y montaje de rutas.
  * `app/api/`: Definición de endpoints (`routes.py`) e inyecciones de dependencias (`deps.py`).
  * `app/core/`: Configuraciones del sistema y lógicas de seguridad (`security.py`).
  * `app/db/`: Configuración del motor de base de datos (`database.py`) y modelos ORM (`models.py`).
  * `app/services/`: Lógica de visión por computadora (`plate_detector.py`), OCR (`ocr_core.py`) y manipulación de archivos (`storage.py`).
  * `app/desktop/`: Interfaz gráfica heredada de escritorio.
  * `app/templates/` y `app/static/`: Archivos para la interfaz web (HTML, CSS, Vanilla JS).
* `tests/`: Scripts de validación, simulaciones de subida y evaluación masiva.
* `database.db`: Archivo de la base de datos SQLite (se genera automáticamente en el primer inicio).

---

## Variables de Entorno

El comportamiento del servidor y las rutas locales pueden ser modificadas mediante variables de entorno antes de la ejecución:

```powershell
$env:OCR_WEB_PORT = "8080"
$env:OCR_SAVE_BASE_DIR = ".\ResultadosAlternativos"
python run.py
```

## Dependencias Principales
* **FastAPI + Uvicorn:** Infraestructura del servidor web.
* **SQLAlchemy + bcrypt:** Manejo de base de datos relacional y cifrado.
* **OpenCV + PaddleOCR:** Procesamiento digital de imágenes y extracción de características ópticas.
