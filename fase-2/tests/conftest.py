"""Utilidades de prueba: datos sintéticos pequeños con el esquema real del proyecto."""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

RAIZ = Path(__file__).resolve().parent.parent  # carpeta fase-2
sys.path.insert(0, str(RAIZ))

from src.config import COLS_CATEGORICAS, COLS_ENTRADA, COLS_NUMERICAS, TARGET  # noqa: E402


def generar_datos(n: int = 300, seed: int = 0) -> pd.DataFrame:
    """Dataset sintético: el objetivo depende de sbytes y del protocolo (hay señal que aprender)."""
    rng = np.random.default_rng(seed)
    df = pd.DataFrame({c: rng.normal(size=n).round(4) for c in COLS_NUMERICAS})
    df["sbytes"] = rng.integers(0, 5000, n)
    df["proto"] = rng.choice(["tcp", "udp", "icmp"], n)
    df["service"] = rng.choice(["-", "http", "dns"], n)
    df["state"] = rng.choice(["FIN", "INT", "CON"], n)
    df[TARGET] = ((df["sbytes"] > 2500) | (df["proto"] == "udp")).astype(int)
    return df


@pytest.fixture
def csv_entrenamiento(tmp_path):
    ruta = tmp_path / "datos.csv"
    generar_datos().to_csv(ruta, index=False)
    return ruta


@pytest.fixture
def csv_entrada(tmp_path):
    """CSV de predicción: sin la variable objetivo."""
    ruta = tmp_path / "entrada.csv"
    generar_datos(20, seed=1)[COLS_ENTRADA].to_csv(ruta, index=False)
    return ruta


@pytest.fixture
def entrenar_modelo(csv_entrenamiento, tmp_path):
    """Devuelve una función que entrena una versión rápida en un directorio temporal."""
    from src.training import entrenar

    def _entrenar(version="v1", seed=42):
        return entrenar(csv_entrenamiento, TARGET, tmp_path / "models", version, seed=seed,
                        estimador="logreg", log=lambda *a, **k: None)
    return _entrenar
