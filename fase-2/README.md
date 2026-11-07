# Fase 2 — Scripts y Docker

**Entrega:** 31 de octubre de 2026 (15 % de la nota) · **Código evaluado:** etiqueta de Git `entrega-2` (ver [sección 12](#12-versión-entregada)).

## Integrantes

- Adrian ([@admaesmo](https://github.com/admaesmo))
- Felipe Cetina ([@Reginork](https://github.com/Reginork))
- Bryan Medrano ([@bryanmedrano](https://github.com/bryanmedrano))

## 1. Problema y relación con la Fase 1

Clasificación binaria de flujos de red del dataset **UNSW-NB15**: `0` = tráfico normal, `1` = ataque (variable objetivo `label`). La [Fase 1](../fase-1/README.md) resolvió el problema en un notebook; esta fase lo convierte en una aplicación que se ejecuta por línea de comandos y dentro de Docker, sin abrir el notebook:

- `train.py` entrena y guarda una **versión** del modelo (`models/<versión>/`).
- `predict.py` carga una versión guardada y genera predicciones sobre un CSV nuevo.

## 2. Cambios respecto a la Fase 1

La retroalimentación de la Fase 1 no pidió modificaciones, por lo que **el problema, los datos, el preprocesamiento y el modelo se conservan**. Con la semilla 42, `train.py` reproduce exactamente las métricas del notebook (F1 = 0,9447). Lo nuevo es la organización:

| Fase 1 (notebook) | Fase 2 |
|---|---|
| Todo el código en celdas | Lógica reutilizable en `src/`; `train.py` y `predict.py` solo leen argumentos |
| Un modelo, nombre con fecha | Versiones por carpeta (`models/v1/`, `models/v2/`…); un identificador repetido **no se sobrescribe** |
| Columnas definidas en el notebook | Contrato único en `src/config.py`, reutilizado al entrenar y al predecir |
| Sin validación al predecir | `predict.py` valida columnas y tipos, y falla con código ≠ 0 si algo está mal |
| — | Dockerfile, `requirements.txt` y pruebas con pytest |

El preprocesamiento sigue dentro de un único `Pipeline` (imputación + escalado + one-hot) ajustado **solo con train**, sin fuga de información. La validación cruzada se reajusta dentro de cada fold.

## 3. Entorno local

Requiere **Python 3.13** (probado con 3.13.7; la imagen Docker usa 3.13.7). Terminal usada: **Bash (Linux)**.

```bash
# desde la raíz del repositorio
python3 -m venv .venv
source .venv/bin/activate
pip install -r fase-2/requirements.txt
cd fase-2          # todos los comandos siguientes se ejecutan desde fase-2
```

## 4. Datos

El dataset **no se sube a GitHub**. Descárgalo según [`data/README.md`](../data/README.md) (Kaggle o página oficial de UNSW) y deja el archivo en:

```
data/raw/UNSW_NB15_training-set.csv      # desde la raíz del repositorio
```

Para entrenar se usa ese archivo completo (53.952 filas útiles tras quitar 28.380 duplicados). Para predecir, el repositorio incluye [`data/ejemplo_prediccion.csv`](data/ejemplo_prediccion.csv): 10 filas **sin** la variable objetivo y con un nulo en `dur` y otro en `service` para mostrar su tratamiento.

### Esquema del CSV de predicción

42 columnas de entrada (el orden en el CSV no importa):

- **Numéricas (39):** `dur, spkts, dpkts, sbytes, dbytes, rate, sttl, dttl, sload, dload, sloss, dloss, sinpkt, dinpkt, sjit, djit, swin, stcpb, dtcpb, dwin, tcprtt, synack, ackdat, smean, dmean, trans_depth, response_body_len, ct_srv_src, ct_state_ttl, ct_dst_ltm, ct_src_dport_ltm, ct_dst_sport_ltm, ct_dst_src_ltm, is_ftp_login, ct_ftp_cmd, ct_flw_http_mthd, ct_src_ltm, ct_srv_dst, is_sm_ips_ports`
- **Categóricas (3):** `proto`, `service`, `state`.

Reglas al predecir:

| Situación | Qué ocurre |
|---|---|
| Falta una columna requerida | Error claro y código de salida 1; no se crea el CSV de salida |
| Texto no numérico en una columna numérica | Error claro y código de salida 1 |
| Celda nula | Se imputa con lo aprendido en train (mediana si es numérica, moda si es categórica) |
| Categoría no vista en el entrenamiento | Se codifica con ceros (no falla ni se descarta la fila) |
| Columnas adicionales (incluida `label`, `id`, `attack_cat`) | Se ignoran |
| Orden de las columnas del CSV | Irrelevante: se reordena según el esquema del entrenamiento |

## 5. Entrenar

```bash
python train.py --data ../data/raw/UNSW_NB15_training-set.csv --target label --output-dir models --version v1 --seed 42
```

Consultar todas las opciones: `python train.py --help`

| Argumento | Descripción |
|---|---|
| `--data` (obligatorio) | CSV con datos etiquetados |
| `--version` (obligatorio) | Identificador de la versión (`v1`, `v2`…). Si ya existe, **falla** sin tocar nada |
| `--target` | Variable objetivo (por defecto `label`) |
| `--output-dir` | Directorio de salida (por defecto `models`) |
| `--seed` | Semilla aleatoria (por defecto 42) |
| `--test-size` | Proporción de prueba (por defecto 0,2, partición estratificada) |
| `--estimator` | `auto` (por defecto: elige por validación cruzada entre `logreg` y `random_forest`), `logreg` o `random_forest` |
| `--cv-folds` | Folds de la validación cruzada (por defecto 3) |

Al terminar imprime un resumen y las rutas de los archivos generados (~20 s).

## 6. Predecir

```bash
python predict.py --model models/v1/modelo.joblib --input data/ejemplo_prediccion.csv --output outputs/predicciones.csv
```

Consultar opciones: `python predict.py --help`. `--model` acepta el `.joblib` o la carpeta de la versión (`--model models/v2`). Con `--proba` se añade la columna opcional `prob_ataque`.

**Salida** (una fila por fila de entrada, en el mismo orden): `prediccion` (`0` = normal, `1` = ataque) y `etiqueta` (`normal`/`ataque`); si el CSV de entrada trae una columna `id`, se copia para relacionar resultados.

## 7. Dónde queda cada cosa

```
fase-2/
├── train.py  predict.py           # puntos de entrada (solo argumentos)
├── src/                           # lógica compartida (config, data, pipeline, training, prediction, versioning…)
├── tests/                         # pruebas con pytest
├── data/ejemplo_prediccion.csv    # CSV de ejemplo sin variable objetivo
├── models/
│   ├── v1/  v2/  v-docker/        # cada versión: modelo.joblib, metrics.json, metadata.json
├── outputs/                       # predicciones (se crea al ejecutar; ignorado por Git)
├── requirements.txt  Dockerfile  .dockerignore
```

Cada versión contiene: `modelo.joblib` (Pipeline completo: preprocesamiento + modelo), `metrics.json` (métricas del modelo y del modelo base sobre test) y `metadata.json` (versión, fecha, algoritmo y parámetros, semilla, columnas y tipos, datos usados, partición, versión de Python/librerías, hash del commit).

## 8. Versionamiento

Los modelos se versionan por carpetas dentro de `models/`. Versiones entregadas (mismo algoritmo, distinta semilla):

| Versión | Comando | Algoritmo | Semilla | F1 test |
|---|---|---|---|---|
| `v1` | `--version v1 --seed 42` | Random Forest | 42 | 0,9447 |
| `v2` | `--version v2 --seed 7 --estimator random_forest` | Random Forest | 7 | 0,9403 |
| `v-docker` | entrenada dentro de Docker (sección 9) | Random Forest | 42 | 0,9447 |

Repetir un identificador produce `ERROR: La versión 'v1' ya existe…` con código de salida 1. Los artefactos (4 MB cada uno) se guardan en el repositorio. Para elegir versión al predecir basta cambiar `--model`.

## 9. Docker

Imagen basada en `python:3.13.7-slim`, directorio de trabajo `/app`, sin `ENTRYPOINT` y **sin entrenar durante el build**. Los datos y modelos se montan como carpetas, así que lo generado persiste aunque el contenedor se elimine. Terminal: **Bash**; el `--user` evita que los archivos generados queden como propiedad de root. En PowerShell hay que adaptar las rutas (`${PWD}` en lugar de `$PWD`) y la continuación de línea (`` ` `` en lugar de `\`).

```bash
# desde fase-2
docker build -t modelos-fase2:1.0 .
mkdir -p models outputs

# Entrenar (datos en solo lectura; el modelo queda en ./models/v-docker)
docker run --rm --user "$(id -u):$(id -g)" \
  -v "$PWD/../data/raw:/app/data:ro" \
  -v "$PWD/models:/app/models" \
  modelos-fase2:1.0 python train.py \
  --data data/UNSW_NB15_training-set.csv --target label \
  --output-dir models --version v-docker --seed 42

# Predecir (la predicción queda en ./outputs/predicciones.csv)
docker run --rm --user "$(id -u):$(id -g)" \
  -v "$PWD/data:/app/data:ro" \
  -v "$PWD/models:/app/models:ro" \
  -v "$PWD/outputs:/app/outputs" \
  modelos-fase2:1.0 python predict.py \
  --model models/v-docker/modelo.joblib \
  --input data/ejemplo_prediccion.csv \
  --output outputs/predicciones.csv
```

Verificado manualmente: la imagen se construye, ambos scripts corren dentro del contenedor, el F1 de `v-docker` es idéntico al de `v1` (0,9447) y los resultados persisten en el equipo anfitrión.

## 10. Pruebas

```bash
python -m pytest            # desde fase-2 (~5 s, sin red, sin tocar models/)
```

También dentro de la imagen: `docker run --rm modelos-fase2:1.0 python -m pytest -q`.

Usan datos sintéticos pequeños y directorios temporales (`tmp_path`). 10 pruebas en `tests/test_aplicacion.py`:

| Comportamiento | Qué comprueban |
|---|---|
| Entrenamiento y almacenamiento | Se generan modelo cargable, métricas y metadatos; el modelo supera al modelo base |
| Carga y predicción | Una predicción por fila, mismo orden, coincide con el modelo guardado (tolerancia numérica en probabilidades) |
| Orden de columnas y columnas extra | No cambian el resultado |
| Valores faltantes | Nulos y categorías nuevas se procesan sin error |
| Entrada inválida | Columna ausente o texto en columna numérica → error claro; la CLI sale con código ≠ 0 y no crea salida |
| Versionamiento | Una segunda versión conserva la primera y ambas cargan; un identificador repetido no sobrescribe (archivos idénticos byte a byte) |
| Sin fuga | El objetivo y `id`/`attack_cat` no son variables de entrada |

## 11. Resultados, modelo base y limitaciones

Evaluación sobre el 20 % de prueba (10.791 filas, estratificada, nunca usado para ajustar ni seleccionar):

| | Precision | Recall | F1 (ataque) |
|---|---|---|---|
| **Random Forest (`v1`)** | 0,957 | 0,932 | **0,945** |
| Modelo base (siempre "normal") | 0,000 | 0,000 | 0,000 |

La selección entre regresión logística (F1 CV 0,848) y Random Forest (F1 CV 0,936) se hace con validación cruzada solo sobre train. El modelo base alcanza 63 % de *accuracy* pero F1 = 0: nunca detecta un ataque, por eso se usa F1 y no *accuracy*.

**Limitaciones conocidas**

- **Datos:** el dataset no tiene nulos reales en el rango 0,1–2 % exigido por el curso (aprobado por el profesor y documentado en la Fase 1). La imputación se probó con nulos sintéticos en las pruebas.
- **Duplicados:** se eliminan antes de partir (34,5 % del dataset); las métricas son sobre datos únicos y no representan una distribución real de tráfico.
- **Generalización:** el modelo se entrenó con una sola partición de UNSW-NB15; con tráfico de otra red o de otra época puede rendir peor.
- **Reproducibilidad:** Random Forest es aleatorio; con la misma semilla, datos y versiones de librerías el resultado es consistente (se verificó que coincide entre local y Docker), pero puede variar mínimamente entre sistemas.
- **Trazabilidad:** `metadata.json` de `v1` y `v2` registra el commit base `58e9c37…` con la marca `+cambios-sin-commit`, porque se generaron antes de versionar el código de esta fase. `v-docker` indica `desconocido` porque la imagen no incluye Git. Vuelve a entrenar si necesitas un hash exacto.
- **Categorías nuevas:** una categoría no vista se trata como "sin información" (ceros), lo que puede reducir la calidad de la predicción de esa fila.

## 12. Versión entregada

El código de la Entrega 2 corresponde a la etiqueta de Git **`entrega-2`** sobre `main`. Este identificador es distinto de las versiones de modelo de `models/`.

## 13. Fuentes

- Dataset UNSW-NB15: Moustafa, N. y Slay, J. (2015), *UNSW-NB15: a comprehensive data set for network intrusion detection systems*, UNSW Canberra.
- Documentación de scikit-learn (`Pipeline`, `ColumnTransformer`, `OneHotEncoder`, `StratifiedKFold`) y de Docker.
- Material del curso Modelos 1 y Especificación Técnica de la Fase 2. No se adaptó código externo.
