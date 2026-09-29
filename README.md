# Detección de intrusiones en red con Machine Learning (UNSW-NB15)

Proyecto semestral de **Modelos y Simulación de Sistemas I**, Universidad de Antioquia, 2026-2, Grupo B.

## Equipo

| Integrante | Usuario GitHub | Rama de trabajo (fase 1) | Responsabilidad |
|---|---|---|---|
| Felipe Cetina | [@Reginork](https://github.com/Reginork) | `feature/entorno-y-verificacion` | Entorno, dependencias, datos y script de verificación |
| Bryan Medrano | [@bryanmedrano](https://github.com/bryanmedrano) | `feature/eda-y-limpieza` | EDA, limpieza y separación train/test (notebook, secciones 1-5) |
| Adrian | [@admaesmo](https://github.com/admaesmo) | `feature/pipeline-y-modelo` | Pipeline, entrenamiento, evaluación y modelo guardado (notebook, secciones 6-10) |

---

## 1. Propósito del proyecto

Las redes de una organización reciben a diario miles de conexiones, y una pequeña fracción de ellas son ataques: escaneos de puertos, denegación de servicio, explotación de vulnerabilidades, puertas traseras, etc. Revisarlas manualmente no es viable. Un **sistema de detección de intrusiones (IDS)** basado en Machine Learning aprende, a partir de ejemplos etiquetados, a distinguir el tráfico normal del malicioso.

**Pregunta a responder:** dado un flujo de tráfico de red descrito por sus características (duración, bytes, paquetes, protocolo, servicio, estado de la conexión, TTL…), ¿se trata de tráfico **normal (0)** o de un **ataque (1)**?

- **Tipo de problema:** clasificación binaria supervisada.
- **Variable objetivo:** `label`.

Siguiendo el enfoque del curso, el objetivo **no es obtener el modelo más preciso**. Se trata de llevar el modelo desde un notebook hasta un producto reproducible, contenerizado, expuesto como API REST y monitoreado:

| Fase | Contenido | Entrega |
|---|---|---|
| **1. Modelo predictivo** | EDA, limpieza, preprocesamiento, entrenamiento, evaluación y modelo serializado | 30/sep/2026 |
| 2. Scripts y Docker | `train.py`, `predict.py`, versionamiento del modelo, Dockerfile, pytest | 31/oct/2026 |
| 3. API REST | `GET /health`, `POST /predict`, `POST /train`, validación de entradas, tests, cliente | 22/nov/2026 |
| 4. Monitoreo | Registro de predicciones, métricas de uso y drift, política de reentrenamiento | 22/nov/2026 |

El proyecto es acumulativo: cada fase vive en su propia carpeta (`fase-1/` … `fase-4/`) y las anteriores se conservan.

---

## 2. Dataset: UNSW-NB15

### Origen

UNSW-NB15 fue creado por el **Australian Centre for Cyber Security (ACCS)** de la UNSW Canberra. Se generó con la herramienta IXIA PerfectStorm, que mezcla tráfico normal real con ataques sintéticos modernos. Sobre el tráfico capturado se extrajeron características con las herramientas Argus y Bro-IDS.

- Página oficial: https://research.unsw.edu.au/projects/unsw-nb15-dataset
- Kaggle: https://www.kaggle.com/datasets/mrwellsdavid/unsw-nb15
- **Archivo usado:** `UNSW_NB15_training-set.csv`, la partición curada que publican los autores.

> Los datos **no se suben al repositorio**. Cada integrante descarga el CSV y lo coloca en `data/raw/UNSW_NB15_training-set.csv`.

### Estructura

Cada **fila** es un flujo de red y cada **columna**, una característica de ese flujo. El archivo tiene **45 columnas**:

| Grupo | Columnas | Descripción |
|---|---|---|
| Identificador | `id` | Número de fila. **Se excluye.** |
| Básicas del flujo | `dur`, `proto`, `service`, `state`, `spkts`, `dpkts`, `sbytes`, `dbytes`, `rate` | Duración, protocolo, servicio, estado de la conexión, paquetes y bytes en cada sentido |
| Tiempo de vida y carga | `sttl`, `dttl`, `sload`, `dload`, `sloss`, `dloss` | TTL de origen y destino, bits por segundo, paquetes retransmitidos |
| Temporización | `sinpkt`, `dinpkt`, `sjit`, `djit`, `tcprtt`, `synack`, `ackdat` | Tiempo entre paquetes, jitter y tiempos del saludo TCP |
| TCP | `swin`, `dwin`, `stcpb`, `dtcpb` | Ventana TCP y números de secuencia base |
| Contenido | `smean`, `dmean`, `trans_depth`, `response_body_len` | Tamaño medio de paquete, profundidad de la transacción HTTP y tamaño de la respuesta |
| Conexiones recientes | `ct_srv_src`, `ct_state_ttl`, `ct_dst_ltm`, `ct_src_dport_ltm`, `ct_dst_sport_ltm`, `ct_dst_src_ltm`, `ct_src_ltm`, `ct_srv_dst`, `ct_ftp_cmd`, `ct_flw_http_mthd` | Conteos de conexiones con el mismo origen, destino o servicio en las últimas 100 conexiones |
| Indicadores | `is_ftp_login`, `is_sm_ips_ports` | Sesión FTP con login; mismas IP y puertos de origen y destino |
| Tipo de ataque | `attack_cat` | Normal, Fuzzers, Analysis, Backdoor, DoS, Exploits, Generic, Reconnaissance, Shellcode, Worms. **Se excluye.** |
| **Objetivo** | `label` | **0 = normal, 1 = ataque** |

Resultan **42 variables predictoras**: 39 numéricas y 3 categóricas (`proto`, `service`, `state`).

### Cumplimiento de los requisitos del curso

| Requisito | Valor en UNSW-NB15 | Estado |
|---|---|---|
| Clasificación o regresión con objetivo definido | Clasificación binaria sobre `label` | ✅ |
| ≥ 1.000 observaciones | ~175.000 flujos | ✅ |
| ≥ 5 variables predictoras | 42 | ✅ |
| Variables numéricas y/o categóricas | 39 numéricas y 3 categóricas | ✅ |
| No es serie de tiempo | Cada flujo es una observación independiente (corte transversal) | ✅ |
| Alguna predictora con 0,1 %-2 % de nulos | _[completar con la salida de `scripts/verificar_dataset.py`]_ | _[pendiente]_ |
| Procesable en un computador personal | CSV de unas decenas de MB | ✅ |

Los conteos exactos se obtienen con el script de verificación (ver sección 5).

---

## 3. Trabajo realizado en la Fase 1

Todo el trabajo de la fase 1 está en `fase-1/fase1_modelo.ipynb`, que se ejecuta de principio a fin con *Restart & Run All*.

### 3.1 Verificación del dataset

Antes de modelar se ejecuta `scripts/verificar_dataset.py`, que comprueba automáticamente los requisitos del curso:

- número de filas y de predictoras;
- tipo de cada columna;
- porcentaje de nulos por columna, **separando los NaN reales de marcadores de texto** como `"-"`, `"?"` o `""`;
- si alguna predictora tiene entre 0,1 % y 2 % de nulos;
- número de clases y su distribución;
- columnas sospechosas de fuga de información.

### 3.2 Análisis exploratorio (EDA)

- **Dimensiones y tipos:** conteo de filas, columnas, tipos de dato y filas duplicadas.
- **Distribución del objetivo:** proporción de tráfico normal frente a ataques, y desglose por tipo de ataque (`attack_cat`), que se usa solo para entender el problema.
- **Estadísticas descriptivas** de las 39 variables numéricas. Muchas (bytes, carga, duración) tienen **distribuciones muy sesgadas**, con la mayoría de valores cerca de cero y colas largas. Por eso se visualizan en escala `log1p`.
- **Variables categóricas:** número de categorías de `proto`, `service` y `state`, y proporción de ataques por categoría. `proto` tiene muchas categorías poco frecuentes.
- **Correlaciones:** las 15 variables numéricas más correlacionadas con el objetivo, con un mapa de calor para detectar redundancia entre ellas (por ejemplo, entre paquetes y bytes).

_[Completar con los hallazgos concretos tras ejecutar el notebook.]_

### 3.3 Limpieza y decisiones sobre los datos

| Situación | Decisión | Justificación |
|---|---|---|
| Columna `id` | Excluida | Es un identificador de fila y no aporta información predictiva |
| Columna `attack_cat` | Excluida | Se deriva directamente del objetivo: si es "Normal", `label = 0`. Usarla sería **fuga de información** |
| `service = "-"` | Se conserva como categoría | En UNSW-NB15 significa "servicio no identificado", un valor legítimo y no un dato faltante |
| NaN en variables numéricas | Imputación por **mediana** | Robusta frente a los valores extremos de las variables sesgadas |
| NaN en variables categóricas | Imputación por **moda** | Estrategia simple y estándar para categorías |
| Escalas muy distintas | `StandardScaler` | Necesario para modelos sensibles a la escala, como la regresión logística |
| Variables categóricas | `OneHotEncoder(handle_unknown="ignore")` | Una categoría nueva en producción no rompe el modelo |

Las columnas de entrada del modelo se definen **una sola vez** al inicio del notebook (`COLS_NUMERICAS` y `COLS_CATEGORICAS`). Esas listas son el contrato de entrada que reutilizarán `predict.py` (fase 2) y la validación de la API (fase 3).

### 3.4 Separación en entrenamiento y prueba

- **80 % entrenamiento / 20 % prueba**, con `train_test_split`.
- **Estratificada** por `label`, para que ambas particiones conserven la misma proporción de ataques.
- `random_state = 42`, para que la separación sea reproducible.
- La separación se hace **antes de cualquier transformación**. Imputadores, escalador y codificador se ajustan solo con los datos de entrenamiento.

### 3.5 Prevención de fuga de información (data leakage)

Todo el preprocesamiento y el modelo están encapsulados en **un único `sklearn.pipeline.Pipeline`**:

```
Pipeline
├── ColumnTransformer
│   ├── numéricas   → SimpleImputer(median) → StandardScaler
│   └── categóricas → SimpleImputer(most_frequent) → OneHotEncoder
└── Estimador (LogisticRegression / RandomForestClassifier)
```

Con este diseño:

- nunca se hace `fit` con datos de prueba;
- en la validación cruzada, cada fold ajusta su propio preprocesamiento;
- el modelo guardado incluye el preprocesamiento, así que en producción basta con `modelo.predict(datos_crudos)`.

### 3.6 Modelos iniciales

| Modelo | Por qué probarlo | Estado |
|---|---|---|
| **Regresión logística** | Línea base lineal, rápida e interpretable | Implementado |
| **Random Forest** | Captura relaciones no lineales e interacciones, es robusto a escalas y valores extremos, y aporta importancia de variables | Implementado (profundidad limitada para que el modelo pese poco) |
| Árbol de decisión | Muy interpretable; útil para explicar las reglas que separan ataques de tráfico normal | Candidato |
| HistGradientBoosting | Suele ser el más preciso en datos tabulares y es rápido con muchas filas | Candidato |
| K-vecinos más cercanos | Punto de comparación basado en distancias | Candidato (costoso con ~175.000 filas) |

**Selección del modelo:** se hace con **validación cruzada estratificada (3 folds) sobre el conjunto de entrenamiento**, usando F1. El conjunto de prueba **no participa en la selección**; solo se usa una vez, para la evaluación final.

### 3.7 Evaluación

La métrica principal es el **F1 de la clase ataque**, porque importan los dos tipos de error:

- **falso negativo:** un ataque no detectado, el error más costoso;
- **falso positivo:** una falsa alarma, que desgasta al equipo de seguridad.

Sobre el conjunto de prueba se reportan precision, recall, F1, el reporte de clasificación y la matriz de confusión.

| Modelo | F1 (CV en entrenamiento) | Precision (prueba) | Recall (prueba) | F1 (prueba) |
|---|---|---|---|---|
| Regresión logística | _[completar]_ | — | — | — |
| Random Forest | _[completar]_ | — | — | — |
| **Seleccionado:** _[completar]_ | | _[completar]_ | _[completar]_ | _[completar]_ |

### 3.8 Modelo guardado

El Pipeline completo se serializa con `joblib` en `fase-1/models/`, con versión y fecha en el nombre:

- `modelo_v1_<fecha>.joblib`: preprocesamiento y modelo, comprimido.
- `metadatos_v1_<fecha>.json`: versión, fecha, estimador y parámetros, columnas de entrada con su tipo y las categorías vistas en entrenamiento, métricas de CV y de prueba, y versiones de Python y de las librerías.

La última celda del notebook recarga el modelo guardado y predice sobre 3 filas de prueba para comprobar que funciona.

---

## 4. Estructura del repositorio

La estructura se irá completando mediante Pull Requests de los integrantes:

```
.
├── README.md
├── requirements.txt          # dependencias con versiones fijadas
├── .gitignore
├── .github/
│   └── pull_request_template.md
├── data/
│   ├── raw/                  # el CSV va aquí (no se sube)
│   └── README.md             # cómo obtener el dataset
├── scripts/
│   └── verificar_dataset.py  # verifica los requisitos del curso
├── fase-1/
│   ├── README.md
│   ├── fase1_modelo.ipynb
│   └── models/               # Pipeline serializado + metadatos JSON
├── fase-2/
├── fase-3/
└── fase-4/
```

---

## 5. Cómo ejecutar

Se requiere Python 3.11 o superior.

```bash
git clone https://github.com/admaesmo/modelos1-unsw-nb15.git
cd modelos1-unsw-nb15

python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# 1. Colocar el CSV en data/raw/ y verificar los requisitos
python scripts/verificar_dataset.py data/raw/UNSW_NB15_training-set.csv label

# 2. Ejecutar el notebook de la fase 1
cd fase-1
jupyter notebook fase1_modelo.ipynb   # Kernel → Restart & Run All
```

---

## 6. Versionamiento

El proyecto versiona tres cosas: el código, las entregas y el modelo.

### Código: Gitflow simplificado

| Rama | Contenido | Cómo recibe cambios |
|---|---|---|
| `main` | Solo versiones **entregadas** al profesor | Únicamente por PR desde `develop`, al cerrar cada entrega |
| `develop` | Rama de **integración** (rama por defecto del repo) | Únicamente por PR desde ramas `feature/*` |
| `feature/<tarea>` | Trabajo de **un integrante** en una tarea concreta | Commits directos de su autor |

`main` y `develop` están **protegidas** en GitHub: no admiten `push` directo, requieren un Pull Request con **al menos 1 aprobación** de otro integrante y no se pueden borrar ni reescribir con `push --force`.

```
main      ●───────────────────────────────● entrega-1
           \                             /
develop     ●─────●──────────●──────────●
                   \        / \        /
feature/...         ●──●───●   ●──●───●
```

### Entregas: etiquetas (tags)

Al fusionar `develop` en `main` para una entrega, se crea una etiqueta que fija exactamente lo entregado:

| Tag | Entrega | Fecha |
|---|---|---|
| `entrega-1` | Fase 1 | 30/sep/2026 |
| `entrega-2` | Fase 2 | 31/oct/2026 |
| `entrega-3` | Fases 3 y 4 | 22/nov/2026 |

### Modelo: versión, fecha y metadatos

Cada modelo entrenado se guarda como `modelo_<version>_<fecha>.joblib` y va acompañado de `metadatos_<version>_<fecha>.json`. El JSON guarda el estimador, sus parámetros, las columnas de entrada, las métricas y las versiones de las librerías.

- Se sube la versión (`v1` → `v2`) cuando cambian las columnas de entrada, el preprocesamiento o el tipo de estimador.
- Reentrenar con los mismos ajustes conserva la versión y cambia la fecha.
- Las versiones anteriores no se borran: permiten comparar modelos y volver atrás (se usará en las fases 2 y 4).

---

## 7. Cómo contribuir

### 7.1 Preparación, una sola vez por integrante

1. Acepta la invitación al repositorio (llega por correo o en *github.com → Notifications*).
2. Configura una llave SSH en tu equipo y regístrala en https://github.com/settings/keys.
3. Clona el repositorio y configura tu identidad. Tus commits deben salir a **tu nombre**, porque el trabajo colaborativo se evalúa por autoría:

```bash
git clone https://github.com/admaesmo/modelos1-unsw-nb15.git
cd modelos1-unsw-nb15
git config user.name "Tu Nombre"
git config user.email "tu-correo-de-github@ejemplo.com"

python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 7.2 Trabajar en tu rama

Tu rama de la fase 1 ya existe en GitHub (ver la tabla del equipo). Tráela y trabaja en ella:

```bash
git fetch origin
git switch feature/<tu-rama>     # ej. git switch feature/eda-y-limpieza
git merge origin/develop         # trae lo último de develop antes de empezar
```

Haz commits **pequeños, frecuentes y descritos en español**, que digan qué cambió:

```bash
git status                       # revisa qué archivos cambiaron
git add fase-1/fase1_modelo.ipynb
git commit -m "Agrega análisis de nulos y distribución del objetivo"
git push                         # la primera vez: git push -u origin feature/<tu-rama>
```

Para tareas posteriores, crea una rama nueva desde `develop` actualizado:

```bash
git switch develop
git pull
git switch -c feature/<nueva-tarea>
```

### 7.3 Abrir el Pull Request

1. En GitHub aparecerá el botón **Compare & pull request** junto a tu rama.
2. Verifica que el destino sea **`base: develop`** ← `compare: feature/<tu-rama>`.
3. Completa la plantilla (qué cambia, cómo probarlo y el checklist).
4. En *Reviewers*, asigna a un compañero.

### 7.4 Revisar el PR de un compañero

1. Abre la pestaña *Files changed* y lee los cambios.
2. Para probarlo localmente: `git fetch origin && git switch feature/<rama-del-compañero>`.
3. Termina con *Review changes* → **Approve**, o **Request changes** con comentarios concretos.
4. Con la aprobación, el autor pulsa **Merge pull request**. La rama se borra automáticamente en GitHub.

### 7.5 Si `develop` avanzó mientras trabajabas

```bash
git fetch origin
git merge origin/develop         # en tu rama feature
# si hay conflictos: edítalos, luego git add <archivo> && git commit
git push
```

### 7.6 Cerrar una entrega

Cuando `develop` tenga todo lo de la fase y funcione desde un clon limpio:

1. Abran un PR de **`develop` → `main`** titulado "Entrega N — Fase N" y apruébenlo.
2. Tras el merge, creen la etiqueta:

```bash
git switch main
git pull
git tag -a entrega-1 -m "Entrega 1: fase 1 - modelo predictivo"
git push origin entrega-1
```

### 7.7 Reglas del equipo

- Nunca commitear directamente en `main` ni en `develop`: GitHub lo bloquea.
- Cada integrante abre **al menos un Pull Request por entrega**.
- **Un notebook lo edita una sola persona a la vez.** Los `.ipynb` son JSON y sus conflictos son muy difíciles de resolver. Pasen el turno fusionando el PR.
- Limpien las salidas del notebook antes de commitear (*Edit → Clear All Outputs*).
- Nunca subir datos (`data/raw/`), entornos (`.venv/`) ni credenciales (`.env`).
- Usen siempre `git add <archivo>`, no `git add .`, para no subir archivos por accidente.
