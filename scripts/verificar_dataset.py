"""Verifica si un CSV cumple los requisitos del proyecto de Modelos I.

Uso:
    python scripts/verificar_dataset.py data/raw/UNSW_NB15_training-set.csv label

Requisitos revisados:
    1. Filas >= 1.000
    2. Variables predictoras (sin el objetivo) >= 5
    3. Tipo de cada columna (numérica / categórica)
    4. Porcentaje de nulos: NaN reales y marcadores ("-", "?", "", "NA") por separado
    5. Al menos una predictora con 0,1 %-2 % de NaN reales (obligatorio)
    6. Número de clases y distribución del objetivo
    7. Columnas sospechosas de fuga de información o que deben excluirse
"""

import argparse
import sys

import pandas as pd

MIN_FILAS = 1_000
MIN_PREDICTORAS = 5
NULOS_MIN_PCT = 0.1
NULOS_MAX_PCT = 2.0
MARCADORES_NULO = ["-", "?", "", "NA"]

# Nombres que suelen indicar identificadores, tiempo o variables derivadas del objetivo
PATRONES_ID = ("id", "_id", "index", "uuid")
PATRONES_TIEMPO = ("time", "date", "fecha", "timestamp", "stime", "ltime")
# Columnas conocidas que se derivan del objetivo en datasets concretos
DERIVADAS_OBJETIVO = {"label": ["attack_cat"], "attack_cat": ["label"]}


def estado(ok: bool) -> str:
    return "CUMPLE" if ok else "NO CUMPLE"


def titulo(texto: str) -> None:
    print(f"\n{'=' * 70}\n{texto}\n{'=' * 70}")


def contar_marcadores(serie: pd.Series) -> float:
    """Porcentaje de celdas que son marcadores de nulo (tras quitar espacios)."""
    if pd.api.types.is_numeric_dtype(serie):
        return 0.0
    texto = serie.dropna().astype(str).str.strip()
    return texto.isin(MARCADORES_NULO).sum() / len(serie) * 100


def columnas_sospechosas(df: pd.DataFrame, objetivo: str) -> list[tuple[str, str]]:
    sospechosas = []
    for col in df.columns:
        if col == objetivo:
            continue
        nombre = col.lower()
        if nombre in PATRONES_ID or nombre.endswith("_id"):
            sospechosas.append((col, "parece un identificador"))
        elif any(p in nombre for p in PATRONES_TIEMPO):
            sospechosas.append((col, "parece una columna de tiempo"))
        elif col in DERIVADAS_OBJETIVO.get(objetivo, []):
            sospechosas.append((col, f"se deriva del objetivo '{objetivo}' (fuga)"))
        elif not pd.api.types.is_float_dtype(df[col]) and df[col].nunique() == len(df):
            # Los floats continuos suelen ser únicos por fila sin ser identificadores
            sospechosas.append((col, "valor único por fila (posible identificador)"))
        elif df[col].nunique(dropna=False) <= 1:
            sospechosas.append((col, "constante, no aporta información"))
    return sospechosas


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("csv", help="Ruta del archivo CSV")
    parser.add_argument("objetivo", help="Nombre de la columna objetivo")
    args = parser.parse_args()

    try:
        # keep_default_na=True: pandas ya convierte "" y "NA" en NaN; "-" y "?" quedan como texto
        df = pd.read_csv(args.csv, low_memory=False)
    except FileNotFoundError:
        print(f"ERROR: no existe el archivo {args.csv}")
        return 2

    if args.objetivo not in df.columns:
        print(f"ERROR: la columna objetivo '{args.objetivo}' no está en el CSV.")
        print("Columnas disponibles:", ", ".join(df.columns))
        return 2

    predictoras = [c for c in df.columns if c != args.objetivo]

    titulo(f"Dataset: {args.csv}")

    # 1 y 2. Tamaño
    ok_filas = len(df) >= MIN_FILAS
    ok_predictoras = len(predictoras) >= MIN_PREDICTORAS
    print(f"1. Filas: {len(df):,}  (mínimo {MIN_FILAS:,}) -> {estado(ok_filas)}")
    print(f"2. Predictoras: {len(predictoras)}  (mínimo {MIN_PREDICTORAS}) -> {estado(ok_predictoras)}")

    # 3. Tipos
    numericas = [c for c in predictoras if pd.api.types.is_numeric_dtype(df[c])]
    categoricas = [c for c in predictoras if c not in numericas]
    titulo("3. Tipos de datos")
    print(f"Numéricas ({len(numericas)}): {', '.join(numericas)}")
    print(f"Categóricas ({len(categoricas)}): {', '.join(categoricas)}")

    # 4. Nulos
    titulo("4. Nulos por columna (solo columnas con algún nulo o marcador)")
    resumen = pd.DataFrame({
        "tipo": ["numérica" if c in numericas else "categórica" for c in predictoras],
        "NaN_%": [df[c].isna().mean() * 100 for c in predictoras],
        "marcador_%": [contar_marcadores(df[c]) for c in predictoras],
    }, index=predictoras)
    con_nulos = resumen[(resumen["NaN_%"] > 0) | (resumen["marcador_%"] > 0)]
    if con_nulos.empty:
        print("Ninguna predictora tiene NaN ni marcadores de nulo.")
    else:
        print(con_nulos.round(3).to_string())
    print(f"\nMarcadores considerados: {MARCADORES_NULO}")
    print("Ojo: un '-' puede ser una categoría legítima (p. ej. 'servicio no identificado').")

    # 5. Requisito de nulos
    en_rango_nan = resumen[resumen["NaN_%"].between(NULOS_MIN_PCT, NULOS_MAX_PCT)]
    en_rango_marcador = resumen[resumen["marcador_%"].between(NULOS_MIN_PCT, NULOS_MAX_PCT)]
    ok_nulos = not en_rango_nan.empty
    titulo(f"5. Requisito de nulos ({NULOS_MIN_PCT} %-{NULOS_MAX_PCT} % en alguna predictora)")
    if ok_nulos:
        print(f"Con NaN reales en rango: {', '.join(en_rango_nan.index)}")
    elif not en_rango_marcador.empty:
        print("Ninguna predictora tiene NaN reales en rango, pero estas tienen marcadores en rango:")
        print(f"  {', '.join(en_rango_marcador.index)}")
        print("  Solo cuentan si el marcador realmente significa 'dato faltante'. Consultar al profesor.")
    else:
        print("Ninguna predictora tiene NaN reales ni marcadores en el rango exigido.")
    print(f"-> {estado(ok_nulos)}")

    # 6. Objetivo
    titulo(f"6. Distribución del objetivo '{args.objetivo}'")
    conteo = df[args.objetivo].value_counts(dropna=False)
    distribucion = pd.DataFrame({"n": conteo, "%": (conteo / len(df) * 100).round(2)})
    print(f"Clases: {len(conteo)}")
    print(distribucion.to_string())
    ratio = conteo.max() / conteo.min()
    if ratio > 3:
        print(f"Aviso: desbalance (clase mayoritaria / minoritaria = {ratio:.1f}). Usar split estratificado y F1/recall.")

    # 7. Columnas a excluir
    titulo("7. Columnas sospechosas de fuga o que deben excluirse")
    sospechosas = columnas_sospechosas(df, args.objetivo)
    if sospechosas:
        for col, motivo in sospechosas:
            print(f"- {col}: {motivo}")
    else:
        print("No se detectaron columnas sospechosas por nombre o contenido.")

    # Resumen
    cumple_todo = ok_filas and ok_predictoras and ok_nulos
    titulo(f"RESULTADO GLOBAL: {estado(cumple_todo)}")
    print(f"Filas: {estado(ok_filas)} | Predictoras: {estado(ok_predictoras)} | Nulos 0,1-2 %: {estado(ok_nulos)}")
    return 0 if cumple_todo else 1


if __name__ == "__main__":
    sys.exit(main())
