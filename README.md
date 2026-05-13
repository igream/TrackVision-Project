# OCR Placas

Proyecto de lectura de matrículas con PaddleOCR.

## Entorno portátil

Cada desarrollador debe crear su propio entorno virtual local y no compartir la carpeta del venv.

### Requisitos

- Python 3.10

### Instalación

```powershell
cd "c:\Users\Fer\Desktop\OCR Placas"
py -3.10 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### Uso web

```powershell
python app.py
```

Abre `http://127.0.0.1:8000` en el navegador.

Para conservar la interfaz anterior de escritorio:

```powershell
python app.py --desktop
```

### Notas

- No incluyas `.venv/` ni `.venv310/` en el control de versiones.
- Si trabajas en otro equipo, simplemente recrea el entorno virtual y ejecuta `pip install -r requirements.txt`.
