"""Pruebas básicas de la aplicación (train.py, predict.py y src/). Ejecutar: python -m pytest"""
import json
import subprocess
import sys

import joblib
import numpy as np
import pandas as pd
import pytest

from conftest import RAIZ, generar_datos
from src import data, versioning
from src.config import COLS_ENTRADA, TARGET
from src.errors import DatosInvalidosError, VersionExistenteError
from src.prediction import predecir_csv


# 1. Entrenamiento y almacenamiento -------------------------------------------------------
def test_entrenamiento_genera_artefactos_cargables(entrenar_modelo):
    res = entrenar_modelo("v1")
    for clave in ("modelo", "metricas", "metadata"):
        assert res["rutas"][clave].is_file()
    modelo = joblib.load(res["rutas"]["modelo"])
    assert hasattr(modelo, "predict")
    metricas = json.loads(res["rutas"]["metricas"].read_text(encoding="utf-8"))
    assert 0 <= metricas["modelo"]["f1"] <= 1
    assert metricas["modelo"]["f1"] > metricas["baseline"]["f1"]  # supera al modelo base
    meta = json.loads(res["rutas"]["metadata"].read_text(encoding="utf-8"))
    assert meta["version"] == "v1" and meta["semilla"] == 42
    assert meta["orden_columnas"] == COLS_ENTRADA
    assert meta["variable_objetivo"] == TARGET


# 2. Carga y predicción --------------------------------------------------------------------
def test_prediccion_una_por_fila_y_coincide_con_el_modelo_guardado(entrenar_modelo, csv_entrada,
                                                                    tmp_path):
    res = entrenar_modelo("v1")
    salida = tmp_path / "out" / "pred.csv"
    predecir_csv(res["rutas"]["modelo"], csv_entrada, salida, con_probabilidad=True,
                 log=lambda *a, **k: None)
    pred = pd.read_csv(salida)
    entrada = pd.read_csv(csv_entrada)
    assert len(pred) == len(entrada)  # una predicción por fila, sin eliminar ninguna
    modelo = joblib.load(res["rutas"]["modelo"])
    esperado = modelo.predict(entrada[COLS_ENTRADA])
    assert (pred["prediccion"].to_numpy() == esperado).all()  # mismo orden
    np.testing.assert_allclose(pred["prob_ataque"], modelo.predict_proba(entrada[COLS_ENTRADA])[:, 1],
                               atol=1e-5)
    assert set(pred["etiqueta"]) <= {"normal", "ataque"}


def test_prediccion_no_depende_del_orden_de_columnas_ni_de_columnas_extra(entrenar_modelo,
                                                                          csv_entrada, tmp_path):
    res = entrenar_modelo("v1")
    base = pd.read_csv(csv_entrada)
    alterado = base[list(reversed(COLS_ENTRADA))].copy()
    alterado["columna_extra"] = 1
    alterado[TARGET] = 0  # el objetivo, si viene, se ignora
    ruta = tmp_path / "alterado.csv"
    alterado.to_csv(ruta, index=False)
    p1 = predecir_csv(res["rutas"]["modelo"], csv_entrada, tmp_path / "a.csv", log=lambda *a: None)
    p2 = predecir_csv(res["rutas"]["modelo"], ruta, tmp_path / "b.csv", log=lambda *a: None)
    assert (p1["prediccion"].to_numpy() == p2["prediccion"].to_numpy()).all()


# 3. Valores faltantes ---------------------------------------------------------------------
def test_nulos_y_categorias_nuevas_se_procesan(entrenar_modelo, csv_entrada, tmp_path):
    res = entrenar_modelo("v1")
    df = pd.read_csv(csv_entrada)
    df.loc[0, "dur"] = np.nan          # nulo numérico -> mediana de train
    df.loc[1, "service"] = np.nan      # nulo categórico -> moda de train
    df.loc[2, "proto"] = "protocolo_nuevo"  # categoría no vista -> ceros en el one-hot
    ruta = tmp_path / "con_nulos.csv"
    df.to_csv(ruta, index=False)
    pred = predecir_csv(res["rutas"]["modelo"], ruta, tmp_path / "p.csv", log=lambda *a: None)
    assert len(pred) == len(df)
    assert pred["prediccion"].isin([0, 1]).all()


# 4. Entrada inválida ----------------------------------------------------------------------
def test_columna_ausente_produce_error_claro(entrenar_modelo, csv_entrada, tmp_path):
    res = entrenar_modelo("v1")
    ruta = tmp_path / "sin_dur.csv"
    pd.read_csv(csv_entrada).drop(columns="dur").to_csv(ruta, index=False)
    salida = tmp_path / "pred.csv"
    with pytest.raises(DatosInvalidosError, match="dur"):
        predecir_csv(res["rutas"]["modelo"], ruta, salida, log=lambda *a: None)
    assert not salida.exists()  # no se genera un archivo que aparente resultados válidos


def test_linea_de_comandos_sale_con_codigo_distinto_de_cero(entrenar_modelo, csv_entrada, tmp_path):
    res = entrenar_modelo("v1")
    ruta = tmp_path / "sin_dur.csv"
    pd.read_csv(csv_entrada).drop(columns="dur").to_csv(ruta, index=False)
    salida = tmp_path / "pred.csv"
    r = subprocess.run([sys.executable, "predict.py", "--model", str(res["rutas"]["modelo"]),
                        "--input", str(ruta), "--output", str(salida)],
                       cwd=RAIZ, capture_output=True, text=True)
    assert r.returncode != 0
    assert "dur" in r.stderr and not salida.exists()
    r = subprocess.run([sys.executable, "predict.py", "--model", str(tmp_path / "no_existe.joblib"),
                        "--input", str(csv_entrada), "--output", str(salida)],
                       cwd=RAIZ, capture_output=True, text=True)
    assert r.returncode != 0 and "ERROR" in r.stderr


def test_valor_no_numerico_en_columna_numerica_falla():
    df = generar_datos(5)[COLS_ENTRADA].astype({"dur": object})
    df.loc[2, "dur"] = "abc"
    with pytest.raises(DatosInvalidosError, match="dur"):
        data.validar_entrada_prediccion(df)


# 5. Versionamiento ------------------------------------------------------------------------
def test_segunda_version_conserva_la_primera_y_ambas_cargan(entrenar_modelo):
    r1 = entrenar_modelo("v1", seed=1)
    r2 = entrenar_modelo("v2", seed=2)
    assert r1["rutas"]["modelo"].parent != r2["rutas"]["modelo"].parent
    for r in (r1, r2):
        modelo, meta = versioning.cargar_version(r["rutas"]["modelo"].parent)  # carga por carpeta
        assert hasattr(modelo, "predict")
    assert versioning.cargar_version(r1["rutas"]["modelo"])[1]["semilla"] == 1
    assert versioning.cargar_version(r2["rutas"]["modelo"])[1]["semilla"] == 2


def test_identificador_repetido_no_sobrescribe(entrenar_modelo):
    r1 = entrenar_modelo("v1")
    antes = {k: p.read_bytes() for k, p in r1["rutas"].items()}
    with pytest.raises(VersionExistenteError):
        entrenar_modelo("v1", seed=99)
    despues = {k: p.read_bytes() for k, p in r1["rutas"].items()}
    assert antes == despues


# Sin fuga: el objetivo y las columnas excluidas no pueden ser entradas ---------------------
def test_el_modelo_no_usa_el_objetivo_ni_columnas_excluidas():
    assert TARGET not in COLS_ENTRADA
    assert "attack_cat" not in COLS_ENTRADA and "id" not in COLS_ENTRADA
