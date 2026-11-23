"""Pruebas del registro y del reporte. Ejecutar desde fase-4:  python -m pytest"""
import csv
import json

from monitor import CAMPOS, ruta_registro
from reporte_monitoreo import calcular, main


def filas():
    with open(ruta_registro(), newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def ensayo(cliente, registro_valido):
    """El ensayo de la especificación: dos entradas válidas y una con una variable ausente."""
    assert cliente.post("/predict", json=registro_valido).status_code == 200
    assert cliente.post("/predict", json=registro_valido).status_code == 200
    incompleto = {k: v for k, v in registro_valido.items() if k != "dur"}
    assert cliente.post("/predict", json=incompleto).status_code == 422


def test_cada_intento_genera_una_sola_fila(cliente, registro_valido):
    ensayo(cliente, registro_valido)
    f = filas()
    assert len(f) == 3                                      # el rechazo también se registra
    assert list(f[0].keys()) == CAMPOS
    assert [r["estado_http"] for r in f] == ["200", "200", "422"]
    assert f[0]["version"] == "v1" and f[0]["prediccion"] in ("normal", "ataque")
    assert f[2]["version"] == "" and f[2]["prediccion"] == ""   # error: sin versión ni predicción
    assert "T" in f[0]["fecha_hora"]                        # fecha y hora ISO


def test_cuerpo_invalido_tambien_se_registra(cliente):
    r = cliente.post("/predict", content=json.dumps([1, 2]), headers={"Content-Type": "application/json"})
    assert r.status_code == 422
    assert [x["estado_http"] for x in filas()] == ["422"]


def test_modelo_no_disponible_se_registra_como_503(cliente, registro_valido, monkeypatch):
    monkeypatch.setenv("MODEL_VERSION", "v99")
    assert cliente.post("/predict", json=registro_valido).status_code == 503
    assert [x["estado_http"] for x in filas()] == ["503"]


def test_el_registro_se_conserva_entre_ejecuciones(entorno, registro_valido):
    from fastapi.testclient import TestClient
    for _ in range(2):  # dos "arranques" distintos de la API sobre el mismo archivo
        TestClient(api_app()).post("/predict", json=registro_valido)
    f = filas()
    assert len(f) == 2
    ruta = ruta_registro()
    assert ruta.read_text(encoding="utf-8").count("fecha_hora") == 1  # un solo encabezado


def api_app():
    import api
    return api.api_fase3.crear_app(registrar=api.registrar_evento)


def test_reporte_3_solicitudes_33_por_ciento(cliente, registro_valido, capsys):
    ensayo(cliente, registro_valido)
    m = calcular(ruta_registro())
    assert (m["total"], m["fallidas"]) == (3, 1)
    assert round(m["porcentaje_fallidas"], 1) == 33.3
    main(["--registro", str(ruta_registro())])
    salida = capsys.readouterr().out
    assert "Total de solicitudes: 3" in salida and "33,3 %" in salida


def test_reporte_con_registro_vacio(tmp_path, capsys):
    vacio = tmp_path / "vacio.csv"
    vacio.write_text("fecha_hora,estado_http,version,prediccion\n", encoding="utf-8")
    for ruta in (vacio, tmp_path / "no_existe.csv"):
        m = calcular(ruta)
        assert m["total"] == 0 and m["porcentaje_fallidas"] is None
    main(["--registro", str(vacio)])
    salida = capsys.readouterr().out
    assert "Total de solicitudes: 0" in salida and "sin solicitudes" in salida
