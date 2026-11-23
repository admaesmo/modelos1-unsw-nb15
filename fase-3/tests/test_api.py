"""Pruebas de la API. Ejecutar desde fase-3:  python -m pytest"""
import json


# --- Las tres pruebas exigidas -----------------------------------------------------------
def test_health_responde_200(cliente):
    r = cliente.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_entrada_valida_devuelve_prediccion_y_version(cliente, registro_valido):
    r = cliente.post("/predict", json=registro_valido)
    assert r.status_code == 200
    cuerpo = r.json()
    assert cuerpo["version"] == "v1"
    assert cuerpo["prediccion"] in ("normal", "ataque")
    assert cuerpo["clase"] in (0, 1)
    assert 0 <= cuerpo["prob_ataque"] <= 1


def test_campo_obligatorio_ausente_se_rechaza(cliente, registro_valido):
    del registro_valido["dur"]
    r = cliente.post("/predict", json=registro_valido)
    assert r.status_code in (400, 422)
    assert "dur" in r.json()["detail"]  # el mensaje identifica la variable que falta


# --- Pruebas adicionales -----------------------------------------------------------------
def test_valor_nulo_se_imputa_con_la_regla_guardada(cliente, registro_valido):
    registro_valido["dur"] = None
    registro_valido["service"] = None
    assert cliente.post("/predict", json=registro_valido).status_code == 200


def test_tipo_incompatible_se_rechaza(cliente, registro_valido):
    registro_valido["sbytes"] = "no-es-un-numero"
    r = cliente.post("/predict", json=registro_valido)
    assert r.status_code == 422 and "sbytes" in r.json()["detail"]


def test_cuerpo_que_no_es_un_objeto_se_rechaza(cliente):
    r = cliente.post("/predict", content=json.dumps([1, 2, 3]),
                     headers={"Content-Type": "application/json"})
    assert r.status_code == 422


def test_modelo_no_disponible_devuelve_503(cliente, registro_valido, monkeypatch):
    monkeypatch.setenv("MODEL_VERSION", "v99")
    r = cliente.post("/predict", json=registro_valido)
    assert r.status_code == 503 and "v99" in r.json()["detail"]
    assert cliente.get("/health").json()["modelo_disponible"] is False


def test_train_crea_version_nueva_y_conserva_la_anterior(cliente, entorno):
    r = cliente.post("/train", json={"estimator": "logreg"})
    assert r.status_code == 201
    assert r.json()["version"] == "v2"
    assert (entorno / "models" / "v1" / "modelo.joblib").is_file()   # la anterior se conserva
    assert (entorno / "models" / "v2" / "modelo.joblib").is_file()
    assert r.json()["version_activa"] == "v1"                         # no se activa sola
    r2 = cliente.post("/train", json={"estimator": "logreg"})
    assert r2.json()["version"] == "v3"                               # nunca repite identificador
