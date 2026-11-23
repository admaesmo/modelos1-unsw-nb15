"""API de la fase 4: la misma API de la fase 3 + registro de cada solicitud a /predict.

No duplica código: carga fase-3/api.py y le conecta el registro de monitor.py.
Arranque (desde fase-4):  uvicorn api:app --host 0.0.0.0 --port 8000
"""
import importlib.util
import os
import sys
from pathlib import Path

AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI))
RUTA_FASE3 = Path(os.environ.get("FASE3_DIR", AQUI.parent / "fase-3")) / "api.py"

_spec = importlib.util.spec_from_file_location("api_fase3", RUTA_FASE3)
api_fase3 = importlib.util.module_from_spec(_spec)
sys.modules["api_fase3"] = api_fase3
_spec.loader.exec_module(api_fase3)

from monitor import registrar_evento  # noqa: E402

app = api_fase3.crear_app(registrar=registrar_evento)
