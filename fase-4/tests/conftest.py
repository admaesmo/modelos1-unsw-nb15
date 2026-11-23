"""Pruebas del registro y del reporte, con un modelo pequeño sintético y un registro temporal."""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

FASE4 = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(FASE4))
import api  # noqa: E402  (carga fase-3/api.py y fase-2/src)

from src.config import COLS_ENTRADA, COLS_NUMERICAS, TARGET  # noqa: E402
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
    fila = datos_sinteticos(5, seed=3)[COLS_ENTRADA].iloc[0]
    return {c: (v.item() if hasattr(v, "item") else v) for c, v in fila.items()}


@pytest.fixture
def entorno(tmp_path, monkeypatch):
    csv = tmp_path / "datos.csv"
    datos_sinteticos().to_csv(csv, index=False)
    entrenar(csv, TARGET, tmp_path / "models", "v1", seed=42, estimador="logreg", log=lambda *a: None)
    monkeypatch.setenv("MODELS_DIR", str(tmp_path / "models"))
    monkeypatch.setenv("MODEL_VERSION", "v1")
    monkeypatch.setenv("LOG_PATH", str(tmp_path / "registro" / "registro_solicitudes.csv"))
    api.api_fase3._cache.clear()
    return tmp_path


@pytest.fixture
def cliente(entorno):
    from fastapi.testclient import TestClient
    return TestClient(api.app)
