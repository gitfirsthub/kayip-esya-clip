FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

# venv'deki torch sürümüyle aynı olmalı
ARG TORCH_VERSION=2.14.1

WORKDIR /srv

RUN pip install --index-url https://download.pytorch.org/whl/cpu "torch==${TORCH_VERSION}"

COPY requirements.txt .
RUN pip install -r requirements.txt

# Model katmanı: yalnızca betiğe bağlı, uygulama kodu değişince yeniden inmez
ENV MODEL_CACHE_DIR=/models \
    FACE_MODEL_PATH=/models/face_detection_yunet_2023mar.onnx \
    DATA_DIR=/data
COPY scripts/download_models.py scripts/download_models.py
RUN python scripts/download_models.py

ENV HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1

RUN useradd --create-home --uid 10001 appuser \
    && mkdir -p /data \
    && chown -R appuser:appuser /data

COPY app app
USER appuser

EXPOSE 8000
HEALTHCHECK --interval=10s --timeout=5s --start-period=120s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=3)"

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
