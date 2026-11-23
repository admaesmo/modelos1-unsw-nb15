"""Lee el registro de la API y muestra dos métricas de operación.

    python reporte_monitoreo.py [--registro registro/registro_solicitudes.csv]

- total de solicitudes a /predict
- porcentaje de solicitudes fallidas (respuestas HTTP 4xx o 5xx)
Describe el funcionamiento del servicio, no la calidad predictiva (eso requeriría los
resultados reales). Con el registro vacío o inexistente muestra total 0 y "sin solicitudes".
"""
import argparse
import csv
import sys
from collections import Counter
from pathlib import Path

from monitor import ruta_registro


def calcular(ruta) -> dict:
    ruta = Path(ruta)
    filas = []
    if ruta.is_file():
        with open(ruta, newline="", encoding="utf-8") as f:
            filas = list(csv.DictReader(f))
    total = len(filas)
    fallidas = sum(1 for r in filas if 400 <= int(r["estado_http"]) <= 599)
    return {
        "total": total,
        "fallidas": fallidas,
        "porcentaje_fallidas": (fallidas / total * 100) if total else None,
        "por_version": dict(Counter(r["version"] for r in filas if r["version"])),
    }


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Métricas de operación de la API a partir del registro.")
    p.add_argument("--registro", default=str(ruta_registro()),
                   help="CSV del registro (por defecto: LOG_PATH o registro/registro_solicitudes.csv)")
    m = calcular(p.parse_args(argv).registro)
    print(f"Total de solicitudes: {m['total']}")
    if m["porcentaje_fallidas"] is None:
        print("Porcentaje de solicitudes fallidas: sin solicitudes")
    else:
        pct = f"{m['porcentaje_fallidas']:.1f}".replace(".", ",")
        print(f"Porcentaje de solicitudes fallidas (HTTP 4xx/5xx): {pct} % ({m['fallidas']} de {m['total']})")
    for version, n in sorted(m["por_version"].items()):
        print(f"  predicciones con la versión {version}: {n}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
