"""Cliente de prueba: envía un registro real del proyecto a la API y muestra la respuesta.

Uso (con la API en marcha, desde fase-3):
    python cliente_prueba.py                       # GET /health y POST /predict con ejemplo_solicitud.json
    python cliente_prueba.py --quitar dur          # quita una variable: la API debe rechazarla (422)
    python cliente_prueba.py --train               # además llama a POST /train (tarda ~20 s)
Solo usa la biblioteca estándar.
"""
import argparse
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path

EJEMPLO = Path(__file__).with_name("ejemplo_solicitud.json")


def llamar(metodo: str, url: str, cuerpo=None, timeout=300):
    datos = None if cuerpo is None else json.dumps(cuerpo).encode("utf-8")
    req = urllib.request.Request(url, data=datos, method=metodo,
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read() or b"{}")


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--url", default="http://localhost:8000", help="URL base de la API")
    p.add_argument("--registro", default=str(EJEMPLO), help="JSON con las variables predictoras")
    p.add_argument("--quitar", action="append", default=[], metavar="VARIABLE",
                   help="elimina una variable del registro (para probar el rechazo)")
    p.add_argument("--train", action="store_true", help="llama también a POST /train")
    a = p.parse_args()

    registro = json.loads(Path(a.registro).read_text(encoding="utf-8"))
    for v in a.quitar:
        registro.pop(v, None)

    try:
        estado, cuerpo = llamar("GET", f"{a.url}/health")
        print(f"GET  /health  -> {estado} {json.dumps(cuerpo, ensure_ascii=False)}")
        estado, cuerpo = llamar("POST", f"{a.url}/predict", registro)
        print(f"POST /predict -> {estado} {json.dumps(cuerpo, ensure_ascii=False)}")
        if a.train:
            estado_t, cuerpo_t = llamar("POST", f"{a.url}/train", {})
            print(f"POST /train   -> {estado_t} {json.dumps(cuerpo_t, ensure_ascii=False)}")
    except urllib.error.URLError as e:
        print(f"No se pudo conectar con {a.url}: {e.reason}. ¿Está la API en marcha?", file=sys.stderr)
        return 1
    return 0 if estado < 400 else 2


if __name__ == "__main__":
    sys.exit(main())
