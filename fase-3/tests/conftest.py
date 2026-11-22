"""Pruebas de la API con un modelo pequeño entrenado sobre datos sintéticos (sin red ni datos reales)."""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

FASE3 = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(FASE3))
import api  # noqa: E402  (agrega fase-2 al path)

from src.config import COLS_CATEGORICAS, COLS_ENTRADA, COLS_NUMERICAS, TARGET  # noqa: E402
from src.training import entrenar  # noqa: E402


def datos_sinteticos(n: int = 300, seed: int = 0) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    df = pd.DataFrame({c: rng.normal(size=n).round(4) for c in COLS_NUMERICAS})
    df["sbytes"] = rng.integers(0, 5000, n)
    df["proto"] = rng.choice(["tcp", "udp", "icmp"], n)
    df["service"] = rng.choice(["-", "http", "dns"], n)
    df["state"] = rng.choice(["FIN", "INT", "CON"], n)
    df[TARGET] = ((df["sbytes"] > 2500) | (df["proto"] == "udp")).astype(int)
    return df


@pytest.fixture
def registro_valido():
    """Un registro JSON con todas las variables predictoras (valores nativos de Python)."""
    fila = datos_sinteticos(5, seed=3)[COLS_ENTRADA].iloc[0]
    return {c: (v.item() if hasattr(v, "item") else v) for c, v in fila.items()}


@pytest.fixture
def entorno(tmp_path, monkeypatch):
    """Modelo v1 pequeño en una carpeta temporal; no toca fase-2/models."""
    csv = tmp_path / "datos.csv"
    datos_sinteticos().to_csv(csv, index=False)
    entrenar(csv, TARGET, tmp_path / "models", "v1", seed=42, estimador="logreg", log=lambda *a: None)
    monkeypatch.setenv("MODELS_DIR", str(tmp_path / "models"))
    monkeypatch.setenv("MODEL_VERSION", "v1")
    monkeypatch.setenv("DATA_PATH", str(csv))
    api._cache.clear()
    return tmp_path


@pytest.fixture
def cliente(entorno):
    from fastapi.testclient import TestClient
    return TestClient(api.crear_app())
