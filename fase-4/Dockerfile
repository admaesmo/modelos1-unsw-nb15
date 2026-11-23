# Se construye con la RAÍZ del repositorio como contexto (reutiliza fase-2/src y fase-3/api.py):
#   docker build -f fase-4/Dockerfile -t modelos-fase4:1.0 .
FROM python:3.13.7-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    FASE2_DIR=/app/fase-2 \
    FASE3_DIR=/app/fase-3 \
    MODELS_DIR=/app/models \
    DATA_PATH=/app/data/UNSW_NB15_training-set.csv \
    LOG_PATH=/app/registro/registro_solicitudes.csv \
    MODEL_VERSION=v1

WORKDIR /app/fase-4

COPY fase-4/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY fase-2/src /app/fase-2/src
COPY fase-3/api.py /app/fase-3/api.py
COPY fase-4/api.py fase-4/monitor.py fase-4/reporte_monitoreo.py ./
COPY fase-4/tests ./tests

# El registro vive en /app/registro: monte esa carpeta para que persista.
EXPOSE 8000
CMD ["uvicorn", "api:app", "--host", "0.0.0.0", "--port", "8000"]
