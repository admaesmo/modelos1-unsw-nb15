"""Flujo completo de entrenamiento: datos -> partición -> selección -> evaluación -> guardado."""
import datetime
import platform
from pathlib import Path

import numpy as np
import sklearn
from sklearn.model_selection import StratifiedKFold, cross_val_score

from . import config, data, evaluation, pipeline, versioning
from .errors import VersionExistenteError


def seleccionar_estimador(X_train, y_train, seed: int, cv_folds: int) -> tuple[str, dict]:
    """Compara los estimadores por F1 con validación cruzada estratificada SOLO sobre train.

    El pipeline completo (preprocesamiento + modelo) se reajusta dentro de cada fold,
    por lo que no hay fuga de información entre folds.
    """
    cv = StratifiedKFold(n_splits=cv_folds, shuffle=True, random_state=seed)
    resultados = {}
    for nombre in config.ESTIMADORES_DISPONIBLES:
        pipe = pipeline.construir_pipeline(pipeline.crear_estimador(nombre, seed))
        scores = cross_val_score(pipe, X_train, y_train, cv=cv, scoring=config.METRICA, n_jobs=1)
        resultados[nombre] = {"media": float(scores.mean()), "std": float(scores.std())}
    mejor = max(resultados, key=lambda k: resultados[k]["media"])
    return mejor, resultados


def entrenar(data_path, target: str, output_dir, version: str, seed: int = config.SEED,
             test_size: float = config.TEST_SIZE, estimador: str = "auto",
             cv_folds: int = config.CV_FOLDS, log=print) -> dict:
    """Entrena y guarda una versión nueva. Devuelve rutas, métricas y metadatos."""
    version = versioning.validar_version(version)
    if (Path(output_dir) / version).exists():  # falla antes de gastar tiempo entrenando
        raise VersionExistenteError(
            f"La versión '{version}' ya existe en {Path(output_dir) / version}. "
            "Elija otro identificador (--version).")

    log(f"[1/5] Leyendo datos: {data_path}")
    df = data.leer_csv(data_path)
    X, y, info_datos = data.preparar_entrenamiento(df, target)
    log(f"      {info_datos['filas_usadas']:,} filas usadas "
        f"({info_datos['duplicados_eliminados']:,} duplicados eliminados)")

    log(f"[2/5] Separando train/test (test={test_size}, estratificado, semilla={seed})")
    X_train, X_test, y_train, y_test = data.separar(X, y, test_size, seed)

    cv_resultados = None
    if estimador == "auto":
        log(f"[3/5] Seleccionando modelo por validación cruzada ({cv_folds} folds) sobre train")
        estimador, cv_resultados = seleccionar_estimador(X_train, y_train, seed, cv_folds)
        for k, v in cv_resultados.items():
            log(f"      {k:>14}: F1 CV = {v['media']:.4f} ± {v['std']:.4f}")
    else:
        log(f"[3/5] Estimador fijado por argumento: {estimador}")
    log(f"      Modelo seleccionado: {estimador}")

    log("[4/5] Entrenando y evaluando sobre test (datos no usados para ajustar)")
    est = pipeline.crear_estimador(estimador, seed)
    modelo = pipeline.construir_pipeline(est).fit(X_train, y_train)
    metricas_modelo = evaluation.calcular_metricas(y_test, modelo.predict(X_test))
    base = pipeline.crear_baseline(seed).fit(X_train, y_train)
    metricas_base = evaluation.calcular_metricas(y_test, base.predict(X_test))
    log(f"      {estimador}: F1={metricas_modelo['f1']:.4f}  | baseline: F1={metricas_base['f1']:.4f}")

    log("[5/5] Guardando versión")
    metricas = {
        "metrica_principal": f"{config.METRICA} (clase 1 = ataque)",
        "modelo": metricas_modelo,
        "baseline": metricas_base,
        "mejora_f1_sobre_baseline": metricas_modelo["f1"] - metricas_base["f1"],
        "validacion_cruzada_f1_train": cv_resultados,
    }
    metadata = {
        "version": version,
        "fecha_creacion": datetime.datetime.now().astimezone().isoformat(timespec="seconds"),
        "tipo_problema": "clasificacion_binaria",
        "variable_objetivo": target,
        "clases": config.CLASES,
        "algoritmo": estimador,
        "parametros_modelo": {k: repr(v) for k, v in est.get_params().items()},
        "semilla": seed,
        "nota_reproducibilidad": (
            "Random Forest usa remuestreo aleatorio; con la misma semilla, datos y versiones "
            "de librerías los resultados son consistentes (puede haber diferencias numéricas "
            "mínimas entre sistemas)."),
        "columnas_excluidas": config.COLUMNAS_EXCLUIR,
        "columnas_entrada": {
            **{c: {"tipo": "numerica", "dtype": str(X[c].dtype)} for c in config.COLS_NUMERICAS},
            **{c: {"tipo": "categorica", "dtype": str(X[c].dtype),
                   "categorias_train": sorted(X_train[c].dropna().astype(str).unique().tolist())}
               for c in config.COLS_CATEGORICAS},
        },
        "orden_columnas": config.COLS_ENTRADA,
        "tratamiento_nulos": {"numericas": "mediana (aprendida en train)",
                              "categoricas": "moda (aprendida en train)"},
        "categorias_no_vistas": "se codifican con ceros (OneHotEncoder handle_unknown='ignore')",
        "datos": {"archivo": Path(data_path).name, **info_datos},
        "particion": {"estrategia": "train_test_split estratificado por el objetivo",
                      "test_size": test_size, "n_train": int(len(X_train)),
                      "n_test": int(len(X_test)), "metrica_evaluacion": config.METRICA},
        "entorno": {"python": platform.python_version(), "sklearn": sklearn.__version__,
                    "numpy": np.__version__, "dependencias": "fase-2/requirements.txt"},
        "commit_codigo": versioning.hash_commit(),
    }
    destino = versioning.crear_directorio_version(output_dir, version)
    rutas = versioning.guardar_version(destino, modelo, metricas, metadata)
    for nombre, ruta in rutas.items():
        log(f"      {nombre:>8}: {ruta}")
    return {"rutas": rutas, "metricas": metricas, "metadata": metadata}
