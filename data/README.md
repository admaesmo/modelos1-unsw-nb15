# Datos

Los datos **no se suben al repositorio** (`data/raw/` está en `.gitignore`). Cada integrante los descarga localmente.

## Dataset: UNSW-NB15

- **Origen:** Australian Centre for Cyber Security (ACCS), UNSW Canberra.
- **Página oficial:** https://research.unsw.edu.au/projects/unsw-nb15-dataset
- **Kaggle:** https://www.kaggle.com/datasets/mrwellsdavid/unsw-nb15
- **Archivo usado:** `UNSW_NB15_training-set.csv`, la partición curada de entrenamiento con 45 columnas (`id`, 42 variables de tráfico, `attack_cat` y `label`).

## Cómo obtenerlo

1. Descarga el dataset desde Kaggle (botón *Download*) o desde la página oficial.
2. Descomprime el archivo.
3. Copia `UNSW_NB15_training-set.csv` en esta carpeta:

```
data/raw/UNSW_NB15_training-set.csv
```

4. Desde la raíz del repositorio, verifica que cumple los requisitos del curso:

```bash
python scripts/verificar_dataset.py data/raw/UNSW_NB15_training-set.csv label
```

## Columnas relevantes

| Columna | Uso |
|---|---|
| `label` | Variable objetivo: 0 = normal, 1 = ataque |
| `proto`, `service`, `state` | Predictoras categóricas |
| Otras 39 columnas numéricas | Predictoras numéricas (ver `COLS_NUMERICAS` en el notebook de fase-1) |
| `id` | Excluida: identificador de fila |
| `attack_cat` | Excluida: tipo de ataque, se deriva del objetivo (fuga de información) |

En la columna `service`, el valor `"-"` significa "servicio no identificado". Se trata como una categoría y no como un dato faltante.
