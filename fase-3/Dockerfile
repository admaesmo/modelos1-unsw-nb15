# Se construye con la RAÍZ del repositorio como contexto (reutiliza fase-2/src):
#   docker build -f fase-3/Dockerfile -t modelos-fase3:1.0 .
FROM python:3.13.7-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    FASE2_DIR=/app/fase-2 \
    MODELS_DIR=/app/models \
    DATA_PATH=/app/data/UNSW_NB15_training-set.csv \
    MODEL_VERSION=v1

WORKDIR /app

COPY fase-3/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Lógica compartida de la fase 2, API y pruebas. Datos y modelos se montan como volúmenes.
COPY fase-2/src ./fase-2/src
COPY fase-3/api.py fase-3/cliente_prueba.py fase-3/ejemplo_solicitud.json ./
COPY fase-3/tests ./tests

EXPOSE 8000
# El servidor escucha en 0.0.0.0 para ser accesible desde fuera del contenedor.
CMD ["uvicorn", "api:app", "--host", "0.0.0.0", "--port", "8000"]
