"""Lectura, validación y partición de datos."""
from pathlib import Path

import pandas as pd
from sklearn.model_selection import train_test_split

from .config import COLS_ENTRADA, COLS_NUMERICAS, COLS_CATEGORICAS, TARGET
from .errors import DatosInvalidosError


def leer_csv(ruta) -> pd.DataFrame:
    ruta = Path(ruta)
    if not ruta.is_file():
        raise DatosInvalidosError(f"No existe el archivo CSV: {ruta}")
    try:
        df = pd.read_csv(ruta, low_memory=False)
    except Exception as e:  # CSV corrupto, vacío, binario...
        raise DatosInvalidosError(f"No se pudo leer {ruta} como CSV: {e}") from e
    if df.empty:
        raise DatosInvalidosError(f"El archivo {ruta} no tiene filas")
    return df


def validar_columnas(df: pd.DataFrame, columnas) -> None:
    faltan = [c for c in columnas if c not in df.columns]
    if faltan:
        raise DatosInvalidosError(f"Faltan columnas requeridas: {faltan}")


def preparar_entrenamiento(df: pd.DataFrame, target: str = TARGET):
    """Valida el CSV etiquetado, elimina duplicados (como en la fase 1) y devuelve X, y."""
    validar_columnas(df, COLS_ENTRADA + [target])
    if df[target].isna().any():
        raise DatosInvalidosError(f"La variable objetivo '{target}' tiene valores nulos")
    n_antes = len(df)
    df = df.drop_duplicates(subset=COLS_ENTRADA + [target]).reset_index(drop=True)
    X = df[COLS_ENTRADA]
    y = df[target]
    if y.nunique() < 2:
        raise DatosInvalidosError("El objetivo debe tener al menos dos clases")
    return X, y, {"filas_leidas": n_antes, "duplicados_eliminados": n_antes - len(df),
                  "filas_usadas": len(df)}


def separar(X, y, test_size: float, seed: int):
    """Partición estratificada ANTES de ajustar cualquier transformación."""
    if not 0 < test_size < 1:
        raise DatosInvalidosError("test_size debe estar entre 0 y 1 (exclusivos)")
    return train_test_split(X, y, test_size=test_size, stratify=y, random_state=seed)


def validar_entrada_prediccion(df: pd.DataFrame, orden_columnas=None) -> pd.DataFrame:
    """Valida un CSV de predicción y lo deja con el esquema del entrenamiento.

    - Columnas adicionales (incluido el objetivo): se ignoran.
    - Orden de columnas del CSV: irrelevante; se reordena según el esquema.
    - Columna requerida ausente: error.
    - Numéricas con texto no convertible: error (un nulo NO es error; se imputa).
    - Categorías nuevas: las codifica en ceros el OneHotEncoder (handle_unknown="ignore").
    """
    orden = list(orden_columnas or COLS_ENTRADA)
    validar_columnas(df, orden)
    X = df[orden].copy()
    for col in [c for c in orden if c in COLS_NUMERICAS]:
        convertida = pd.to_numeric(X[col], errors="coerce")
        malas = convertida.isna() & X[col].notna()
        if malas.any():
            ejemplo = X.loc[malas, col].iloc[0]
            raise DatosInvalidosError(
                f"La columna numérica '{col}' tiene valores no numéricos "
                f"(p. ej. {ejemplo!r} en la fila {int(malas.idxmax())})")
        X[col] = convertida
    for col in [c for c in orden if c in COLS_CATEGORICAS]:
        X[col] = X[col].astype("object").where(X[col].notna(), None)
    return X
