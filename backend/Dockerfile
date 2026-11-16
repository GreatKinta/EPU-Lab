FROM python:3.12-slim AS base
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY requirements.lock .
RUN --mount=type=cache,target=/root/.cache/pip pip install -r requirements.lock
COPY . .
RUN useradd --create-home labchain && mkdir -p /data/uploads /data/ocr && chown -R labchain:labchain /data /app
USER labchain
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

FROM base AS ocr
USER root
RUN --mount=type=cache,target=/root/.cache/pip pip install torch==2.15.0+cpu torchvision==0.29.2+cpu --index-url https://download.pytorch.org/whl/cpu && pip install -r requirements-ocr.lock
ENV EASYOCR_MODULE_PATH=/data/ocr
USER labchain
