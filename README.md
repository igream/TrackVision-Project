# Detección de Placas Vehiculares

Aplicación para la detección y lectura de matrículas vehiculares (ALPR) utilizando Procesamiento Digital de Imágenes (PDI) y Reconocimiento Óptico de Caracteres (OCR).

## Características

* **Backend:** Implementado con [FastAPI](https://fastapi.tiangolo.com/), proporcionando soporte para operaciones asíncronas y concurrencia.
* **Autenticación:** Sistema de registro y acceso de usuarios, utilizando `bcrypt` para el cifrado de contraseñas y cookies de sesión firmadas.
* **Captura de Imagen:** Permite cargar archivos desde el almacenamiento local o capturar fotografías desde una cámara conectada al dispositivo.
* **Persistencia de Datos:** Utiliza SQLite y SQLAlchemy para almacenar resultados y metadatos. Las imágenes originales se almacenan en la base de datos en formato BLOB.
* **Flujo de Detección:**
  * **Detección PDI:** Proceso algorítmico clásico que aísla contornos que coinciden con las proporciones de una placa vehicular.
  * **Lectura OCR:** Extracción de texto mediante el modelo de red neuronal PaddleOCR.

---

## Requisitos

- Python 3.10+
- Windows, macOS o Linux

---

## Instalación

1. Clonar o descargar el repositorio y abrir una terminal en la raíz del proyecto.

   ```powershell
   cd "ruta\al\proyecto"
   ```

2. Crear y activar un entorno virtual.

   En Windows:

   ```powershell
   py -3.10 -m venv .venv310
   .\.venv310\Scripts\Activate.ps1
   ```

   En macOS o Linux:

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

El servidor iniciará en el puerto 8000 por defecto. Para acceder a la aplicación, abrir un navegador web en:

```text
http://127.0.0.1:8000
```

Para especificar una dirección IP o puerto distinto:

```powershell
python run.py --host 0.0.0.0 --port 8080
```

---

## Uso

1. **Autenticación:** Es necesario iniciar sesión con un usuario registrado para acceder al procesamiento.
2. **Carga de Imagen:** Seleccionar la pestaña "Subir archivo" para elegir una imagen local o "Tomar foto" para capturar desde cámara.
3. **Procesamiento:** Usar "Detectar placa" para ubicar y recortar una placa, o "Leer texto OCR" para extraer texto alfanumérico.
4. **Resultados:** Las imágenes del proceso y los textos detectados se muestran en la interfaz. El resumen y la imagen original se almacenan automáticamente.

---

## Estructura del Proyecto

* `run.py`: Punto de entrada de la aplicación.
* `app/`: Directorio principal del código fuente.
  * `app/main.py`: Inicialización de FastAPI y montaje de rutas.
  * `app/api/`: Endpoints e inyecciones de dependencias.
  * `app/core/`: Configuración del sistema y lógica de seguridad.
  * `app/db/`: Configuración del motor de base de datos y modelos ORM.
  * `app/services/`: Lógica de visión por computadora, OCR y almacenamiento.
  * `app/desktop/`: Interfaz gráfica heredada de escritorio.
  * `app/templates/` y `app/static/`: Interfaz web.
* `tests/`: Scripts de validación, simulación de subidas y evaluación masiva.
* `database.db`: Archivo SQLite generado automáticamente en el primer inicio.

---

## Variables de Entorno

El comportamiento del servidor, la sesión y las rutas locales pueden modificarse mediante variables de entorno:

```powershell
$env:OCR_WEB_PORT = "8080"
$env:OCR_SAVE_BASE_DIR = ".\app\Detecciones"
$env:OCR_SESSION_SECRET = "cambia-este-secreto-en-produccion"
$env:OCR_SESSION_SECURE = "true"
python run.py
```

## Dependencias Principales

* **FastAPI + Uvicorn:** Infraestructura del servidor web.
* **SQLAlchemy + bcrypt:** Manejo de base de datos relacional y cifrado.
* **OpenCV + PaddleOCR:** Procesamiento digital de imágenes y extracción de características ópticas.
