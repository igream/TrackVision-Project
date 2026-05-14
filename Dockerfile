FROM python:3.10-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    OCR_WEB_HOST=0.0.0.0 \
    OCR_WEB_PORT=7860 \
    OCR_SAVE_BASE_DIR=/tmp/Detecciones \
    OCR_SESSION_SECURE=true \
    HF_HOME=/tmp/.huggingface \
    PADDLE_HOME=/tmp/.paddle

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        libgl1 \
        libglib2.0-0 \
        libgomp1 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN python -m pip install --upgrade pip \
    && pip install -r requirements.txt

COPY app ./app
COPY img ./img
COPY src ./src
COPY run.py README.md ./

RUN mkdir -p /tmp/Detecciones /tmp/.huggingface /tmp/.paddle

EXPOSE 7860

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "7860", "--workers", "1"]
