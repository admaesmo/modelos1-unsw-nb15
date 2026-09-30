# Fase 1 — Modelo predictivo

**Entrega:** 30 de septiembre de 2026 (5 % de la nota).

## Problema

Clasificación binaria de flujos de tráfico de red: **normal (0)** o **ataque (1)**. Una red recibe miles de conexiones por minuto y solo una fracción son ataques; revisarlas manualmente no es viable a esa escala. Detectar intrusiones de forma automática permite priorizar la atención del equipo de seguridad y reaccionar antes de que un ataque tenga éxito.

## Dataset

UNSW-NB15, archivo `UNSW_NB15_training-set.csv`. Las instrucciones de descarga están en [../data/README.md](../data/README.md).

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
4. **Selección del modelo** con validación cruzada estratificada (3 folds) **solo sobre train**, usando F1.
5. **Evaluación final en test:** precision, recall, F1, reporte de clasificación y matriz de confusión.
6. **Serialización** del Pipeline completo con `joblib` y de un JSON de metadatos.

Como todas las transformaciones se ajustan dentro del Pipeline, nunca se hace `fit` con datos de test: no hay fuga de información.

## Cómo ejecutar el notebook

Desde la raíz del repositorio:

```bash
source .venv/bin/activate                  # entorno creado según el README principal
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
