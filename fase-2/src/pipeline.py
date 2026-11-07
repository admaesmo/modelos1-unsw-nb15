"""Construcción del Pipeline (preprocesamiento + modelo) sin fuga de información."""
from sklearn.compose import ColumnTransformer
from sklearn.dummy import DummyClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from .config import COLS_CATEGORICAS, COLS_NUMERICAS, ESTIMADORES_DISPONIBLES
from .errors import AppError


def crear_estimador(nombre: str, seed: int):
    if nombre == "logreg":
        return LogisticRegression(max_iter=2000, random_state=seed)
    if nombre == "random_forest":
        # Profundidad acotada para que el artefacto sea compacto (< 50 MB)
        return RandomForestClassifier(n_estimators=100, max_depth=20, min_samples_leaf=2,
                                      n_jobs=-1, random_state=seed)
    raise AppError(f"Estimador desconocido '{nombre}'. Opciones: {ESTIMADORES_DISPONIBLES}")


def crear_baseline(seed: int):
    return DummyClassifier(strategy="most_frequent", random_state=seed)


def construir_pipeline(estimador) -> Pipeline:
    """Un único objeto: imputación + escalado + one-hot + modelo. Se ajusta solo con train."""
    preprocesador = ColumnTransformer([
        ("num", Pipeline([
            ("imputar", SimpleImputer(strategy="median")),
            ("escalar", StandardScaler()),
        ]), COLS_NUMERICAS),
        ("cat", Pipeline([
            ("imputar", SimpleImputer(strategy="most_frequent")),
            ("onehot", OneHotEncoder(handle_unknown="ignore")),
        ]), COLS_CATEGORICAS),
    ])
    return Pipeline([("prep", preprocesador), ("modelo", estimador)])
