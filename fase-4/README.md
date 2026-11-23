# Fase 4 — Monitoreo

**Entrega:** 22 de noviembre de 2026 · **Código evaluado:** etiqueta de Git `entrega-3` (ver [sección 9](#9-versión-entregada)).

## Integrantes

- Adrian ([@admaesmo](https://github.com/admaesmo))
- Felipe Cetina ([@Reginork](https://github.com/Reginork))
- Bryan Medrano ([@bryanmedrano](https://github.com/bryanmedrano))

## 1. Qué hace esta fase

Se conserva `fase-3/` (la API) y se añade lo necesario para **registrar cómo se usa** y saber **qué versión predice**. No se duplica la API: [`api.py`](api.py) carga `fase-3/api.py` y le conecta el registro de [`monitor.py`](monitor.py).

| Archivo | Función |
|---|---|
| [`monitor.py`](monitor.py) | Registra cada llamada a `POST /predict` en un CSV persistente |
| [`api.py`](api.py) | La API de la fase 3 con el registro habilitado |
| [`reporte_monitoreo.py`](reporte_monitoreo.py) | Lee el registro y muestra el total de solicitudes y el % de fallidas |
| [`muestra_registro.csv`](muestra_registro.csv) | Muestra del registro usado en el reporte |
| `tests/` | 6 pruebas del registro y del reporte |

## 2. Registro de solicitudes

Una fila por **cada intento** a `/predict`, incluidos los rechazados por validación (un campo ausente, un tipo incompatible, un cuerpo que no es JSON) y los fallos de servicio (503):

```
fecha_hora,estado_http,version,prediccion
```

- Predicción válida: se guarda la versión que produjo la respuesta y la etiqueta.
- Error: `prediccion` queda vacía y, si no se usó el modelo, también `version`.
- El archivo se abre en modo *agregar*: **el historial se conserva entre ejecuciones** (el encabezado se escribe solo al crear el archivo).
- La hora se guarda como la del servidor; dentro de Docker es UTC (por eso en el ejemplo aparece 05:18 aunque en Colombia eran las 00:18).

**Ubicación:** variable `LOG_PATH`; por defecto `fase-4/registro/registro_solicitudes.csv` (local) y `/app/registro/registro_solicitudes.csv` (Docker, carpeta montada). La carpeta `registro/` está en `.gitignore`; la muestra entregada es `muestra_registro.csv`.

## 3. Cómo ejecutarlo

Python 3.13 y Bash, igual que las fases anteriores.

**Local** (desde `fase-4`, con el entorno de `fase-3/requirements.txt` o `fase-4/requirements.txt` instalado):

```bash
cd fase-4
MODEL_VERSION=v1 uvicorn api:app --host 0.0.0.0 --port 8000     # registro en fase-4/registro/
```

**Docker** (desde la **raíz** del repositorio; el contexto es la raíz porque se reutiliza `fase-2/src` y `fase-3/api.py`):

```bash
docker build -f fase-4/Dockerfile -t modelos-fase4:1.0 .
mkdir -p fase-4/registro
docker run -d --name api-fase4 --user "$(id -u):$(id -g)" -p 8000:8000 \
  -e MODEL_VERSION=v1 \
  -v "$PWD/fase-2/models:/app/models:ro" \
  -v "$PWD/fase-4/registro:/app/registro" \
  modelos-fase4:1.0
```

El registro persistente queda en `fase-4/registro/registro_solicitudes.csv` aunque el contenedor se elimine (verificado: tras `docker restart` el total siguió acumulando). Para `/train` desde esta imagen hay que montar también los datos (`-v "$PWD/data/raw:/app/data:ro"`) y los modelos sin `:ro`. Detener: `docker rm -f api-fase4`.

**Cliente y reporte:**

```bash
cd fase-4
python ../fase-3/cliente_prueba.py                  # predicción válida
python ../fase-3/cliente_prueba.py --quitar dur     # predicción con una variable ausente (se rechaza)
python reporte_monitoreo.py                         # total y % de fallidas
python reporte_monitoreo.py --registro muestra_registro.csv    # sobre la muestra entregada
```

## 4. Métricas de operación

[`reporte_monitoreo.py`](reporte_monitoreo.py) muestra:

1. **Total de solicitudes** a `/predict`.
2. **Porcentaje de solicitudes fallidas**: respuestas HTTP 4xx o 5xx sobre el total. Con el registro vacío o inexistente muestra `Total: 0` y `sin solicitudes`.

Estas métricas describen el **funcionamiento del servicio**. Medir la calidad predictiva requeriría conocer los resultados reales de cada flujo.

## 5. Pruebas

```bash
python -m pytest        # desde fase-4 (~2 s)
docker run --rm modelos-fase4:1.0 python -m pytest -q       # dentro de la imagen
```

| Prueba | Verifica |
|---|---|
| Una fila por intento | Dos válidas + una inválida → exactamente 3 filas (200, 200, 422); en el error versión y predicción vacías |
| Cuerpo inválido | Un JSON que no es un objeto también se registra (422) |
| Modelo no disponible | Se registra como 503 |
| Persistencia | Dos arranques de la API sobre el mismo archivo acumulan filas y un solo encabezado |
| Reporte 3 solicitudes | Total 3 y 33,3 % de fallos |
| Registro vacío | Total 0 y «sin solicitudes» |

## 6. Versiones y política de reentrenamiento

**Versiones guardadas** (en `fase-2/models/`, accesibles desde la API montándolas en `/app/models`):

| Identificador | Cómo se creó | Algoritmo | F1 (ataque) en test |
|---|---|---|---|
| **`v1`** — *versión activa* | `train.py --version v1 --seed 42` (fase 2) | Random Forest | 0,9447 |
| `v2` | `train.py --version v2 --seed 7` (fase 2) | Random Forest | 0,9403 |
| `v3` | `POST /train` (fase 3, desde Docker) | Random Forest | 0,9447 |

(`v-docker` es la versión entrenada en Docker en la fase 2.)

**Qué versión usa la API:** la que indique `MODEL_VERSION` (por defecto `v1`); cada fila del registro guarda la versión que respondió. **Para volver a la anterior** basta reiniciar con `MODEL_VERSION=v1` (local: `MODEL_VERSION=v1 uvicorn api:app …`; Docker: `-e MODEL_VERSION=v1`). Ninguna versión se sobrescribe, por lo que el regreso no requiere reentrenar.

**Política de reentrenamiento**

> El modelo se revisará cuando el equipo reúna **500 flujos nuevos con su etiqueta real** (normal o ataque, confirmada por el analista de seguridad), o cuando aparezca un tipo de ataque que el modelo no detecte. **Adrian** ejecutará `POST /train` para generar una versión candidata. Se comparará la candidata con la versión activa usando la **misma métrica de la fase 2 (F1 de la clase ataque)** sobre esos casos reservados, que no se usan para entrenar, y la candidata se activará (cambiando `MODEL_VERSION`) **solo si supera a la activa**; si no mejora, se conserva la activa.

Un campo ausente o mal formado (HTTP 422) **no** activa esta política: se corrige en quien envía los datos.

## 7. Reporte

**Solicitudes enviadas** (API en Docker con `MODEL_VERSION=v1`, registro vacío al inicio, [`muestra_registro.csv`](muestra_registro.csv)):

| # | Solicitud | Respuesta |
|---|---|---|
| 1 | `POST /predict` con el registro completo de [`fase-3/ejemplo_solicitud.json`](../fase-3/ejemplo_solicitud.json) | 200 · `ataque` · versión `v1` |
| 2 | La misma solicitud válida | 200 · `ataque` · versión `v1` |
| 3 | La misma solicitud **sin la variable `dur`** | 422 · `Faltan columnas requeridas: ['dur']` |

**Registro generado:**

```
fecha_hora,estado_http,version,prediccion
2026-11-22T05:18:10,200,v1,ataque
2026-11-22T05:18:10,200,v1,ataque
2026-11-22T05:18:10,422,,
```

**Indicadores** (`python reporte_monitoreo.py --registro muestra_registro.csv`):

```
Total de solicitudes: 3
Porcentaje de solicitudes fallidas (HTTP 4xx/5xx): 33,3 % (1 de 3)
  predicciones con la versión v1: 2
```

**Interpretación.** La API procesó dos registros con `v1` y rechazó el tercero porque le faltaba la variable `dur`. La tasa de fallos fue 1/3 (33,3 %). El rechazo fue el resultado esperado de la prueba de validación: la API respondió 422 con un mensaje que nombra la variable, y el intento quedó registrado sin versión ni predicción.

## 8. Estructura

```
fase-4/
├── api.py  monitor.py  reporte_monitoreo.py
├── muestra_registro.csv       # muestra del registro usado en el reporte
├── requirements.txt  Dockerfile
├── tests/                     # conftest.py, test_monitoreo.py
├── registro/                  # registro persistente (ignorado por Git)
└── README.md
```

**Limitaciones:** el registro es un CSV de un solo proceso (suficiente para esta entrega; con varios procesos habría que usar una base de datos); no hay tableros ni reentrenamiento automático (opcionales según la especificación); el porcentaje de fallos mide el servicio, no la calidad del modelo.

## 9. Versión entregada

El código de las fases 3 y 4 corresponde a la etiqueta de Git **`entrega-3`** sobre `main`. Es distinta de los identificadores de versión del modelo (`v1`, `v2`, `v3`).

Fuentes: documentación de FastAPI y Uvicorn; material del curso y Especificación Técnica de las fases 3 y 4. No se adaptó código externo.
