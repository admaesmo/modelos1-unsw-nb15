# Imagen con versión de Python explícita (no usar latest). Debe coincidir con el README.
FROM python:3.13.7-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Dependencias primero: aprovecha la caché de capas si solo cambia el código
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Código de la aplicación (los datos, modelos y salidas se montan como volúmenes)
COPY train.py predict.py ./
COPY src ./src
COPY tests ./tests

# Sin ENTRYPOINT: el comando (train.py, predict.py o pytest) se indica en docker run.
# El modelo NO se entrena durante docker build.
CMD ["python", "train.py", "--help"]
