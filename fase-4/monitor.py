"""Registro persistente de las solicitudes a POST /predict (fase 4).

Una fila por intento, incluidas las rechazadas por validación:
    fecha_hora,estado_http,version,prediccion
En un error la predicción queda vacía y, si no se usó el modelo, también la versión.
El archivo se abre en modo "agregar", así que el historial se conserva entre ejecuciones.
Ubicación: variable LOG_PATH (por defecto fase-4/registro/registro_solicitudes.csv).
"""
import csv
import datetime
import os
import threading
from pathlib import Path

CAMPOS = ["fecha_hora", "estado_http", "version", "prediccion"]
_lock = threading.Lock()


def ruta_registro() -> Path:
    return Path(os.environ.get("LOG_PATH", Path(__file__).resolve().parent / "registro"
                               / "registro_solicitudes.csv"))


def registrar_evento(estado_http: int, version: str = "", prediccion: str = "") -> None:
    ruta = ruta_registro()
    with _lock:
        ruta.parent.mkdir(parents=True, exist_ok=True)
        nuevo = not ruta.exists() or ruta.stat().st_size == 0
        with open(ruta, "a", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            if nuevo:
                w.writerow(CAMPOS)  # encabezado solo al crear el archivo
            w.writerow([datetime.datetime.now().isoformat(timespec="seconds"), estado_http,
                        version, prediccion])
