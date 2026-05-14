---
title: TrackVision Project
emoji: 🚘
colorFrom: blue
colorTo: green
sdk: docker
app_port: 7860
pinned: false
---

# Detección de Placas Vehiculares

Aplicación para la detección y lectura de matrículas vehiculares (ALPR) utilizando Procesamiento Digital de Imágenes (PDI) y Reconocimiento Óptico de Caracteres (OCR).

## Demo En Línea

La versión pública del proyecto está desplegada en Hugging Face Spaces:

```text
https://igream-trackvision-project.hf.space
```

La aplicación permite registrarse, iniciar sesión, subir imágenes vehiculares, detectar regiones candidatas de placa y ejecutar OCR sobre la imagen o el recorte detectado.

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

## Ejecución Local

El punto de entrada del servidor es `run.py`. Para iniciar la aplicación web con la configuración local por defecto:

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

Si se definen variables de entorno para una ejecución local por HTTP, usar `OCR_SESSION_SECURE=false`; reservar `true` para despliegues HTTPS como Hugging Face Spaces.

---

## Despliegue En Hugging Face Spaces

Este repositorio está preparado para desplegarse como Docker Space gratuito en Hugging Face.

1. Crear un Space público con SDK `Docker`.
2. Subir este repositorio al Space o configurar el Space desde Git.
3. Definir estas variables de entorno y secretos en la configuración del Space:

   ```text
   OCR_WEB_HOST=0.0.0.0
   OCR_WEB_PORT=7860
   OCR_SAVE_BASE_DIR=/tmp/Detecciones
   OCR_SESSION_SECURE=true
   ```

   ```text
   OCR_SESSION_SECRET=<secreto-largo-generado-para-produccion>
   ```

4. Esperar a que termine el build y abrir la URL pública generada por Hugging Face. El formato habitual es:

   ```text
   https://<usuario>-<nombre-del-space>.hf.space
   ```

El contenedor usa el puerto `7860`, SQLite efímero y almacenamiento temporal en `/tmp/Detecciones`. El primer arranque puede tardar varios minutos mientras se construye la imagen, inicia el contenedor y se cargan los modelos de OCR. Si el Space se suspende por inactividad, volver a abrir la URL pública lo despierta automáticamente; también puede reiniciarse con:

```powershell
.\.venv310\Scripts\hf.exe spaces restart <usuario>/<nombre-del-space>
```

Para pausarlo manualmente:

```powershell
.\.venv310\Scripts\hf.exe spaces pause <usuario>/<nombre-del-space>
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
* `Dockerfile`: Imagen de despliegue para Hugging Face Spaces.
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
$env:OCR_SESSION_SECURE = "false"
python run.py
```

En despliegues HTTPS, como Hugging Face Spaces, usar `OCR_SESSION_SECURE=true`.

## Dependencias Principales

* **FastAPI + Uvicorn:** Infraestructura del servidor web.
* **SQLAlchemy + bcrypt:** Manejo de base de datos relacional y cifrado.
* **OpenCV Headless + PaddleOCR:** Procesamiento digital de imágenes y extracción de características ópticas.
