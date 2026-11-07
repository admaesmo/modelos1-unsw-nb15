"""Predicción por lotes con una versión guardada (no reentrena ni reajusta nada)."""
from pathlib import Path

import pandas as pd

from . import data, versioning
from .errors import AppError


def predecir_csv(model_path, input_path, output_path, con_probabilidad: bool = False,
                 log=print) -> pd.DataFrame:
    """Lee el CSV de entrada, predice una vez por fila (orden original) y escribe el CSV.

    El archivo de salida solo se crea si todo el proceso termina bien.
    """
    pipeline, meta = versioning.cargar_version(model_path)
    df = data.leer_csv(input_path)
    X = data.validar_entrada_prediccion(df, meta["orden_columnas"])

    try:
        pred = pipeline.predict(X)
        proba = pipeline.predict_proba(X)[:, 1] if con_probabilidad else None
    except Exception as e:
        raise AppError(f"El modelo no pudo predecir con estos datos: {e}") from e

    etiquetas = meta.get("clases", {"0": "normal", "1": "ataque"})
    salida = pd.DataFrame(index=df.index)
    if "id" in df.columns:  # identificador opcional para relacionar filas
        salida["id"] = df["id"]
    salida["prediccion"] = pred.astype(int)
    salida["etiqueta"] = [etiquetas[str(int(p))] for p in pred]
    if proba is not None:
        salida["prob_ataque"] = proba.round(6)
    assert len(salida) == len(df)

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    salida.to_csv(output_path, index=False)
    log(f"Versión usada: {meta['version']} ({meta['algoritmo']})")
    log(f"{len(salida)} predicciones -> {output_path} "
        f"(1 = ataque: {int((salida['prediccion'] == 1).sum())}, "
        f"0 = normal: {int((salida['prediccion'] == 0).sum())})")
    return salida
