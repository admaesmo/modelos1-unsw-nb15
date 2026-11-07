"""Entrena el modelo y guarda una versión nueva en <output-dir>/<version>/.

Ejemplo (desde fase-2, en una sola línea):
    python train.py --data data/datos.csv --target label --output-dir models --version v1 --seed 42
"""
import argparse
import sys

from src import config
from src.errors import AppError
from src.training import entrenar


def parse_args(argv=None):
    p = argparse.ArgumentParser(
        description="Entrena el modelo (Pipeline sin fuga de información) y guarda una versión "
                    "con modelo.joblib, metrics.json y metadata.json.")
    p.add_argument("--data", required=True, help="Ruta al CSV con datos etiquetados")
    p.add_argument("--target", default=config.TARGET,
                   help=f"Nombre de la variable objetivo (por defecto: {config.TARGET})")
    p.add_argument("--output-dir", default="models", help="Directorio de salida (por defecto: models)")
    p.add_argument("--version", required=True,
                   help="Identificador de la versión, p. ej. v1. Si ya existe, el proceso falla")
    p.add_argument("--seed", type=int, default=config.SEED, help="Semilla aleatoria (por defecto: 42)")
    p.add_argument("--test-size", type=float, default=config.TEST_SIZE,
                   help="Proporción de datos para prueba (por defecto: 0.2)")
    p.add_argument("--estimator", default="auto", choices=["auto"] + config.ESTIMADORES_DISPONIBLES,
                   help="'auto' elige por validación cruzada; o fije uno (por defecto: auto)")
    p.add_argument("--cv-folds", type=int, default=config.CV_FOLDS,
                   help="Folds de la validación cruzada (por defecto: 3)")
    return p.parse_args(argv)


def main(argv=None) -> int:
    args = parse_args(argv)
    try:
        entrenar(args.data, args.target, args.output_dir, args.version, args.seed,
                 args.test_size, args.estimator, args.cv_folds)
    except AppError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
