# Fase 3 — API REST

**Entrega:** 22 de noviembre de 2026 · **Código evaluado:** etiqueta de Git `entrega-3` (ver [sección 11](#11-versión-entregada)).

## Integrantes

- Adrian ([@admaesmo](https://github.com/admaesmo))
- Felipe Cetina ([@Reginork](https://github.com/Reginork))
- Bryan Medrano ([@bryanmedrano](https://github.com/bryanmedrano))

## 1. Qué hace esta fase

Expone por HTTP el modelo de la [Fase 2](../fase-2/README.md) (detector de ataques en tráfico de red, UNSW-NB15). Se conservan `fase-1/` y `fase-2/`; la API **reutiliza** el código de `fase-2/src` (validación, Pipeline guardado, entrenamiento y versionamiento) sin duplicar ninguna transformación. Framework: **FastAPI**.

| Ruta | Qué hace |
|---|---|
| `GET /health` | HTTP 200 y `{"status": "ok", ...}`: la API está en ejecución |
| `POST /predict` | Recibe un registro JSON con las 42 variables predictoras; carga la versión configurada y devuelve la etiqueta (`normal`/`ataque`) y la versión usada |
| `POST /train` | Entrena con los datos y la configuración de la fase 2, guarda una **versión nueva** (modelo, métricas y metadatos) y devuelve su identificador (HTTP 201). Las versiones anteriores se conservan |

Documentación interactiva automática (Swagger): `http://localhost:8000/docs`.

## 2. Configuración (variables de entorno, todas opcionales)

| Variable | Por defecto | Para qué |
|---|---|---|
| `MODEL_VERSION` | `v1` | **Versión que usa `/predict`**. Es la forma de elegir (o volver a) una versión disponible |
| `MODELS_DIR` | `../fase-2/models` | Carpeta con las versiones (`v1/`, `v2/`, …) |
| `DATA_PATH` | `../data/raw/UNSW_NB15_training-set.csv` | CSV etiquetado que usa `/train` |
| `TARGET`, `SEED` | `label`, `42` | Variable objetivo y semilla de `/train` |

Versiones disponibles en el repositorio: `v1`, `v2`, `v-docker` y `v3` (esta última creada al probar `/train`). Para predecir con otra: `MODEL_VERSION=v2 uvicorn api:app …`. **Una versión recién entrenada no se activa sola**: `/predict` sigue usando la configurada hasta que se cambie `MODEL_VERSION`.

## 3. Entorno local

Python **3.13** (probado con 3.13.7). Terminal: **Bash (Linux)**.

```bash
# desde la raíz del repositorio
python3 -m venv .venv && source .venv/bin/activate
pip install -r fase-3/requirements.txt
cd fase-3
uvicorn api:app --host 0.0.0.0 --port 8000
```

Los datos para `/train` se obtienen como en la fase 2 (`data/raw/UNSW_NB15_training-set.csv`, ver [`data/README.md`](../data/README.md)); no se suben a GitHub.

## 4. Docker (demostración local)

La imagen reutiliza `fase-2/src`, por eso se construye **desde la raíz del repositorio** (el contexto es la raíz; el Dockerfile está en `fase-3/`). Python 3.13.7, puerto **8000**, servidor en `0.0.0.0`.

```bash
# desde la RAÍZ del repositorio
docker build -f fase-3/Dockerfile -t modelos-fase3:1.0 .

docker run -d --name api-fase3 --user "$(id -u):$(id -g)" \
  -p 8000:8000 \
  -v "$PWD/data/raw:/app/data:ro" \
  -v "$PWD/fase-2/models:/app/models" \
  modelos-fase3:1.0
```

| Montaje | Uso |
|---|---|
| `data/raw` → `/app/data` (solo lectura) | Datos para `/train` |
| `fase-2/models` → `/app/models` | Versiones del modelo: `/predict` las lee y `/train` guarda aquí las nuevas, así que persisten aunque el contenedor se elimine |

Detener: `docker rm -f api-fase3`. En PowerShell hay que adaptar `$PWD` → `${PWD}`, las barras y la continuación de línea (`` ` ``).

## 5. Cliente de prueba y ejemplo

[`cliente_prueba.py`](cliente_prueba.py) (solo biblioteca estándar) envía el registro de [`ejemplo_solicitud.json`](ejemplo_solicitud.json), una fila real del CSV de ejemplo de la fase 2:

```bash
python cliente_prueba.py                 # GET /health y POST /predict
python cliente_prueba.py --quitar dur    # quita una variable: la API debe rechazarla
python cliente_prueba.py --train         # además llama a POST /train (~20 s–2 min)
```

Equivalente con `curl`:

```bash
curl http://localhost:8000/health
curl -X POST http://localhost:8000/predict -H "Content-Type: application/json" -d @ejemplo_solicitud.json
curl -X POST http://localhost:8000/train -H "Content-Type: application/json" -d '{}'
```

**Solicitud** `POST /predict` (fragmento; el archivo completo tiene las 42 variables, `null` para un dato faltante):

```json
{"dur": 0.361938, "spkts": 10, "dpkts": 6, "sbytes": 568, "...": "...", "proto": "tcp", "service": "-", "state": "FIN"}
```

**Respuesta** (HTTP 200, ejecutada en Docker):

```json
{"prediccion": "ataque", "clase": 1, "prob_ataque": 0.79573, "version": "v1"}
```

**`/health`** → `{"status": "ok", "version_activa": "v1", "modelo_disponible": true}`

**`/train`** (HTTP 201, ejecutada en Docker con los datos completos):

```json
{"version": "v3", "algoritmo": "random_forest",
 "metricas": {"precision": 0.9574, "recall": 0.9324, "f1": 0.9447},
 "ruta": "/app/models/v3", "version_activa": "v1",
 "nota": "La nueva versión NO se activa sola: /predict sigue usando la versión activa hasta que cambie MODEL_VERSION."}
```

El cuerpo de `/train` puede ir vacío; opcionalmente `{"seed": 7, "estimator": "random_forest"}`. El identificador es el primer `vN` libre, así que nunca sobrescribe una versión.

## 6. Validación y errores

| Situación | Respuesta |
|---|---|
| Falta una variable | **422** `{"detail": "Faltan columnas requeridas: ['dur']"}` (nombra la variable) |
| Tipo incompatible (texto en una variable numérica) | **422** con la variable afectada |
| Cuerpo que no es un objeto JSON / JSON inválido | **422** `Solicitud inválida: …` |
| Valor `null` | Se acepta: se aplica la regla guardada en la fase 2 (mediana si es numérica, moda si es categórica) |
| Categoría no vista en el entrenamiento | Se acepta (se codifica con ceros) |
| Variables adicionales | Se ignoran |
| Modelo de `MODEL_VERSION` no disponible | **503** con el mensaje `El modelo de la versión 'vX' no está disponible…` |
| `/train` sin los datos montados | **503** indicando la ruta esperada |
| `/train` con parámetros inválidos | **422** |

La predicción funciona sin la variable objetivo (`label`).

## 7. Pruebas

```bash
python -m pytest        # desde fase-3 (~3 s; sin red ni datos reales)
docker run --rm modelos-fase3:1.0 python -m pytest -q     # dentro de la imagen
```

Entrenan un modelo pequeño con datos sintéticos en un directorio temporal (no tocan `fase-2/models`). 8 pruebas en `tests/test_api.py`:

| Prueba | Verifica |
|---|---|
| **`/health` responde 200** (exigida) | Código 200 y estado `ok` |
| **Entrada válida** (exigida) | 200, etiqueta, clase, probabilidad y versión `v1` |
| **Campo obligatorio ausente** (exigida) | 422 y el mensaje nombra la variable |
| Nulos | Un nulo numérico y uno categórico se procesan (200) |
| Tipo incompatible | 422 nombrando la variable |
| Cuerpo que no es un objeto | 422 |
| Modelo no disponible | 503 y `modelo_disponible: false` en `/health` |
| `/train` | 201, versión nueva (`v2`, luego `v3`), la anterior se conserva y no se activa sola |

`/train` también se comprobó manualmente con los datos completos (sección 5): creó `v3` con F1 = 0,9447.

## 8. Estructura

```
fase-3/
├── api.py                  # API FastAPI (rutas, validación, errores)
├── cliente_prueba.py       # cliente de prueba (stdlib)
├── ejemplo_solicitud.json  # registro real del proyecto para probar
├── requirements.txt  Dockerfile
├── tests/                  # conftest.py, test_api.py
└── README.md
```

## 9. Limitaciones

- `/train` es **síncrono** (la petición espera entre ~20 s y unos minutos según el equipo) y no tiene autenticación: es una demostración local, no un despliegue.
- La API carga la versión activa en memoria al primera solicitud; si cambia `MODEL_VERSION`, se carga la nueva en la solicitud siguiente (sin reiniciar).
- Las limitaciones del modelo son las de la [fase 2](../fase-2/README.md#11-resultados-modelo-base-y-limitaciones).

## 10. Fuentes

Documentación de FastAPI, Starlette y Uvicorn; material del curso y Especificación Técnica de las fases 3 y 4. No se adaptó código externo.

## 11. Versión entregada

El código de la Entrega 3 corresponde a la etiqueta de Git **`entrega-3`** sobre `main` (distinta de las versiones de modelo en `models/`).
