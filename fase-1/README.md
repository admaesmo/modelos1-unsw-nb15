# Fase 1 — Modelo predictivo

**Entrega:** 30 de septiembre de 2026 (5 % de la nota).

## Problema

Clasificación binaria de flujos de tráfico de red: **normal (0)** o **ataque (1)**. Una red recibe miles de conexiones por minuto y solo una fracción son ataques; revisarlas manualmente no es viable a esa escala. Detectar intrusiones de forma automática permite priorizar la atención del equipo de seguridad y reaccionar antes de que un ataque tenga éxito.

## Qué hace el modelo

El modelo recibe un **flujo de red** (una conexión) descrito por sus 42 variables — protocolo, servicio, estado de la conexión, bytes y paquetes enviados/recibidos, duración, TTL, tiempos entre paquetes, contadores de conexiones recientes, etc. — y responde con dos cosas:

1. una **clase**: `0` (tráfico normal) o `1` (ataque);
2. una **probabilidad** de que ese flujo sea un ataque (entre 0 y 1), útil para priorizar alertas en vez de tratarlas todas por igual.

Internamente, el flujo de datos es siempre el mismo, tanto al entrenar como al predecir sobre datos nuevos (ver sección 9 del notebook):

```
flujo de red (42 variables crudas)
        │
        ▼
 preprocesamiento (dentro del Pipeline)
   - numéricas   → imputar mediana → escalar (StandardScaler)
   - categóricas → imputar moda    → one-hot (OneHotEncoder)
        │
        ▼
 clasificador (Random Forest, ver sección "Resultados")
        │
        ▼
 clase (0/1) + probabilidad de ataque
```

Como el preprocesamiento vive dentro del mismo `Pipeline` que el clasificador, para predecir sobre un flujo nuevo basta con pasarle las 42 variables en crudo: el propio modelo se encarga de imputar, escalar y codificar exactamente igual que lo hizo con los datos de entrenamiento.

## Dataset

El dataset fu descargado de Kaggle en la sigueinte direccion 
https://www.kaggle.com/datasets/mrwellsdavid/unsw-nb15
- **Objetivo:** `label`.
- **Predictoras:** 42 (39 numéricas y 3 categóricas: `proto`, `service`, `state`).
- **Excluidas:** `id` (identificador) y `attack_cat` (se deriva del objetivo; usarla sería fuga de información).

## Metodología

1. **EDA:** dimensiones, tipos, nulos (separando NaN reales de marcadores como `"-"`), distribución del objetivo, estadísticas descriptivas y gráficas.
2. **Split train/test (80/20)** estratificado y con `random_state = 42`, **antes de cualquier transformación**.
3. **Un único `Pipeline`** de scikit-learn:
   - numéricas: `SimpleImputer(median)` + `StandardScaler`;
   - categóricas: `SimpleImputer(most_frequent)` + `OneHotEncoder(handle_unknown="ignore")`;
   - estimador: `LogisticRegression` o `RandomForestClassifier`.
4. **Selección del modelo** (lo hacemos en el notebook, sección 6.1): se comparan los dos estimadores del Pipeline (regresión logística y Random Forest) con **validación cruzada estratificada de 3 folds**, calculada **únicamente sobre el conjunto de train** — el test nunca interviene en esta comparación, para que su métrica final sea una estimación honesta y no esté sesgada por haberse usado para elegir el modelo.

   > **¿Qué es la validación cruzada estratificada?** En vez de entrenar una sola vez y medir sobre una única partición (lo que dependería de la suerte de esa partición), el conjunto de train se divide en **3 partes  de tamaño similar**. El modelo se entrena 3 veces: en cada vuelta, usa 2 de las partes para entrenar y mide el F1 sobre la parte restante, rotando cuál parte queda afuera cada vez. Al final se promedian los 3 F1 obtenidos (por eso el resultado se reporta como media ± desviación estándar). Es **estratificada** porque cada una de las 3 partes conserva la misma proporción de ataques y de tráfico normal que el conjunto completo (63,4 %/36,6 %); sin esto, alguna parte podría quedar con muy pocos ataques por azar y distorsionar la comparación entre modelos.

   La métrica de comparación es el **F1 de la clase "ataque"**, porque el objetivo está moderadamente desbalanceado (63,4 % normal / 36,6 % ataque) e importan tanto los falsos negativos (ataques no detectados) como los falsos positivos (falsas alarmas). El modelo con mayor F1 promedio en CV se reentrena con todo el conjunto de train (sección 6.2) y es el que pasa a la evaluación final del punto 5.
5. **Evaluación final en test:** precision, recall, F1, reporte de clasificación y matriz de confusión.
6. **Serialización** del Pipeline completo con `joblib` y de un JSON de metadatos.

Como todas las transformaciones se ajustan dentro del Pipeline, nunca se hace `fit` con datos de test: no hay fuga de información.

## Cómo ejecutar el notebook

Desde la raíz del repositorio:

```bash
source .venv/bin/activate        # entorno creado según el README principal
python scripts/verificar_dataset.py data/raw/UNSW_NB15_training-set.csv label
cd fase-1
jupyter notebook fase1_modelo.ipynb
```

En Jupyter, usa **Kernel → Restart & Run All**. El notebook lee el CSV desde `../data/raw/` por defecto. Para usar otra ruta, define la variable de entorno `DATA_PATH` antes de abrir Jupyter.

**En Google Colab:** abre el notebook y ejecuta todo. Si el CSV no está disponible, la celda de carga pide subirlo.

## Modelo generado

El notebook guarda en `fase-1/models/`:

| Archivo | Contenido |
|---|---|
| `modelo_v1_<fecha>.joblib` | Pipeline completo (preprocesamiento + modelo), comprimido |
| `metadatos_v1_<fecha>.json` | Versión, fecha, estimador, columnas de entrada con su tipo y categorías vistas, métricas de CV y test, versiones de librerías |

Uso del modelo guardado:

```python
import joblib, pandas as pd
modelo = joblib.load("fase-1/models/modelo_v1_<fecha>.joblib")
modelo.predict(df_nuevo)  # df_nuevo con las columnas de "orden_columnas" del JSON
```

## Resultados

| Modelo | F1 (CV en train) | Precision (test) | Recall (test) | F1 (test) |
|---|---|---|---|---|
| Regresión logística | 0,848 ± 0,006 | — | — | — |
| Random Forest | 0,936 ± 0,004 | — | — | — |
| **Seleccionado: Random Forest** | | 0,957 | 0,932 | 0,945 |
