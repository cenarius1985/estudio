# Backend api+worker de Estudio Doctorado (misma imagen, distinto comando).
# Tesseract (spa+eng) para OCR de imágenes y páginas de PDF escaneadas.
FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    TESSDATA_PREFIX=/usr/share/tesseract-ocr/5/tessdata

RUN apt-get update \
 && apt-get install -y --no-install-recommends \
      tesseract-ocr tesseract-ocr-spa tesseract-ocr-eng \
      libgomp1 libglib2.0-0 curl \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY estudio ./estudio

RUN useradd --create-home --shell /bin/bash estudio \
 && chown -R estudio:estudio /app \
 # Los volúmenes modelos/cargas heredan ownership de estos directorios al
 # crearse por primera vez (comportamiento de Docker); sin esto quedan de
 # root y fastembed no puede descargar el modelo (Errno 13).
 && mkdir -p /data/modelos /data/cargas \
 && chown estudio:estudio /data/modelos /data/cargas
USER estudio

EXPOSE 8000
CMD ["uvicorn", "estudio.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
