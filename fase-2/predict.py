"""Genera predicciones con una versión guardada del modelo (no reentrena).

Ejemplo (desde fase-2, en una sola línea):
    python predict.py --model models/v1/modelo.joblib --input data/ejemplo_prediccion.csv --output outputs/predicciones.csv
"""
import argparse
import sys

from src.errors import AppError
from src.prediction import predecir_csv


def parse_args(argv=None):
    p = argparse.ArgumentParser(
        description="Predice con una versión guardada. Salida: columnas 'prediccion' "
                    "(0 = normal, 1 = ataque) y 'etiqueta', una fila por fila de entrada, "
                    "en el mismo orden. Las columnas extra del CSV se ignoran.")
    p.add_argument("--model", required=True,
                   help="Ruta a modelo.joblib o a la carpeta de la versión (p. ej. models/v1)")
    p.add_argument("--input", required=True, help="CSV con las variables de entrada (sin objetivo)")
    p.add_argument("--output", required=True, help="CSV de salida con las predicciones")
    p.add_argument("--proba", action="store_true", help="Añade la columna prob_ataque (opcional)")
    return p.parse_args(argv)


def main(argv=None) -> int:
    args = parse_args(argv)
    try:
        predecir_csv(args.model, args.input, args.output, args.proba)
    except AppError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
