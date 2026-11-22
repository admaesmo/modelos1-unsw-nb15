"""API REST del detector de ataques (Fase 3).

Rutas:  GET /health · POST /predict · POST /train
Reutiliza la lógica de la fase 2 (fase-2/src): validación, Pipeline guardado, entrenamiento
y versionamiento. No duplica ninguna transformación.

Configuración por variables de entorno (todas opcionales):
    MODEL_VERSION  versión usada por /predict            (por defecto: v1)
    MODELS_DIR     carpeta con las versiones del modelo  (por defecto: ../fase-2/models)
    DATA_PATH      CSV etiquetado que usa /train         (por defecto: ../data/raw/UNSW_NB15_training-set.csv)
    TARGET, SEED   variable objetivo y semilla de /train (por defecto: label, 42)
    FASE2_DIR      ubicación de fase-2 (en Docker: /app/fase-2)

Arranque (desde fase-3):  uvicorn api:app --host 0.0.0.0 --port 8000
"""
import os
import re
import sys
import threading
from pathlib import Path

import pandas as pd
from fastapi import Body, FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

AQUI = Path(__file__).resolve().parent
FASE2 = Path(os.environ.get("FASE2_DIR", AQUI.parent / "fase-2"))
sys.path.insert(0, str(FASE2))

from src import config, data, training, versioning  # noqa: E402
from src.errors import AppError, DatosInvalidosError, ModeloNoEncontradoError, VersionExistenteError  # noqa: E402

_cache: dict = {}
_lock_cache = threading.Lock()
_lock_train = threading.Lock()


# --- Configuración (se lee en cada solicitud: permite cambiar de versión y probar fácilmente) ---
def models_dir() -> Path:
    return Path(os.environ.get("MODELS_DIR", FASE2 / "models"))


def version_activa() -> str:
    return os.environ.get("MODEL_VERSION", "v1")


def data_path() -> Path:
    return Path(os.environ.get("DATA_PATH", AQUI.parent / "data" / "raw" / "UNSW_NB15_training-set.csv"))


def cargar_modelo(version: str):
    """Carga (y guarda en memoria) la versión pedida. Lanza ModeloNoEncontradoError si no existe."""
    ruta = models_dir() / versioning.validar_version(version) / config.NOMBRE_MODELO
    if not ruta.is_file():
        raise ModeloNoEncontradoError(f"El modelo de la versión '{version}' no está disponible en {ruta.parent}")
    clave = (str(ruta), ruta.stat().st_mtime_ns)
    with _lock_cache:
        if clave not in _cache:
            _cache.clear()
            _cache[clave] = versioning.cargar_version(ruta)
        return _cache[clave]


def siguiente_version() -> str:
    """Primer identificador vN libre (v1, v2, v3…); ignora carpetas con otros nombres."""
    existentes = [int(m.group(1)) for p in models_dir().glob("v*")
                  if (m := re.fullmatch(r"v(\d+)", p.name))] if models_dir().exists() else []
    return f"v{max(existentes, default=0) + 1}"


def crear_app(registrar=None) -> FastAPI:
    """Crea la aplicación. `registrar(estado_http, version, prediccion)` es opcional (fase 4)."""
    app = FastAPI(title="API detector de ataques UNSW-NB15", version="1.0")

    def _registrar(estado: int, version: str = "", prediccion: str = ""):
        if registrar is not None:
            try:
                registrar(estado, version, prediccion)
            except Exception:  # el monitoreo nunca debe tumbar la API
                pass

    def _error(estado: int, mensaje: str, es_predict: bool = False):
        if es_predict:
            _registrar(estado)
        return JSONResponse(status_code=estado, content={"detail": mensaje})

    @app.exception_handler(RequestValidationError)
    async def _validacion(request: Request, exc: RequestValidationError):
        """Cuerpo que no es un JSON objeto, etc. También se registra si es /predict."""
        mensaje = "; ".join(f"{'.'.join(str(x) for x in e['loc'])}: {e['msg']}" for e in exc.errors())
        return _error(422, f"Solicitud inválida: {mensaje}", es_predict=request.url.path == "/predict")

    @app.get("/health")
    def health():
        try:
            cargar_modelo(version_activa())
            disponible = True
        except AppError:
            disponible = False
        return {"status": "ok", "version_activa": version_activa(), "modelo_disponible": disponible}

    @app.post("/predict")
    def predict(registro: dict = Body(...)):
        try:
            pipeline, meta = cargar_modelo(version_activa())
        except AppError as e:
            return _error(503, str(e), es_predict=True)
        try:
            X = data.validar_entrada_prediccion(pd.DataFrame([registro]), meta["orden_columnas"])
        except DatosInvalidosError as e:
            return _error(422, str(e), es_predict=True)
        except Exception as e:  # valores anidados u otros tipos imposibles de tabular
            return _error(422, f"Registro inválido: {e}", es_predict=True)
        try:
            clase = int(pipeline.predict(X)[0])
            prob = float(pipeline.predict_proba(X)[0, 1])
        except Exception as e:
            _registrar(500, meta["version"])
            return JSONResponse(status_code=500, content={"detail": f"El modelo no pudo predecir: {e}"})
        etiqueta = meta.get("clases", config.CLASES)[str(clase)]
        _registrar(200, meta["version"], etiqueta)
        return {"prediccion": etiqueta, "clase": clase, "prob_ataque": round(prob, 6),
                "version": meta["version"]}

    @app.post("/train")
    def train(opciones: dict | None = Body(default=None)):
        """Entrena una versión NUEVA (nunca sobrescribe). El cuerpo puede ir vacío;
        opcionalmente {"seed": int, "estimator": "auto"|"logreg"|"random_forest"}."""
        opciones = opciones or {}
        seed = opciones.get("seed", int(os.environ.get("SEED", config.SEED)))
        estimador = opciones.get("estimator", "auto")
        if not isinstance(seed, int) or isinstance(seed, bool):
            return _error(422, "seed debe ser un entero")
        if estimador not in ["auto"] + config.ESTIMADORES_DISPONIBLES:
            return _error(422, f"estimator debe ser uno de {['auto'] + config.ESTIMADORES_DISPONIBLES}")
        if not data_path().is_file():
            return _error(503, f"Datos de entrenamiento no disponibles en {data_path()}. "
                               "Monte la carpeta de datos (ver README).")
        with _lock_train:  # evita que dos entrenamientos simultáneos elijan el mismo identificador
            version = siguiente_version()
            try:
                res = training.entrenar(data_path(), os.environ.get("TARGET", config.TARGET),
                                        models_dir(), version, seed=seed, estimador=estimador,
                                        log=lambda *a, **k: None)
            except VersionExistenteError as e:
                return _error(409, str(e))
            except AppError as e:
                return _error(422, str(e))
        m = res["metricas"]["modelo"]
        return JSONResponse(status_code=201, content={
            "version": version,
            "algoritmo": res["metadata"]["algoritmo"],
            "metricas": {k: round(m[k], 4) for k in ("precision", "recall", "f1")},
            "ruta": str(res["rutas"]["modelo"].parent),
            "version_activa": version_activa(),
            "nota": "La nueva versión NO se activa sola: /predict sigue usando la versión activa "
                    "hasta que cambie MODEL_VERSION.",
        })

    return app


app = crear_app()
