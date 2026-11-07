"""Versionamiento por carpetas: models/<version>/{modelo.joblib, metrics.json, metadata.json}."""
import json
import re
import subprocess
from pathlib import Path

import joblib

from .config import NOMBRE_METADATA, NOMBRE_METRICAS, NOMBRE_MODELO
from .errors import AppError, ModeloNoEncontradoError, VersionExistenteError

_VERSION_VALIDA = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")


def validar_version(version: str) -> str:
    if not _VERSION_VALIDA.match(version or ""):
        raise AppError(f"Identificador de versión inválido: {version!r} "
                       "(use letras, números, '.', '_' o '-'; p. ej. v1)")
    return version


def crear_directorio_version(output_dir, version: str) -> Path:
    """Crea la carpeta de la versión. Nunca sobrescribe una existente."""
    destino = Path(output_dir) / validar_version(version)
    try:
        destino.mkdir(parents=True, exist_ok=False)
    except FileExistsError:
        raise VersionExistenteError(
            f"La versión '{version}' ya existe en {destino}. "
            "Elija otro identificador (--version) o elimine la carpeta manualmente.") from None
    return destino


def hash_commit() -> str:
    """Hash del commit del código, o 'desconocido' si no hay Git (p. ej. en Docker)."""
    try:
        r = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True,
                           timeout=5, cwd=Path(__file__).parent)
        if r.returncode == 0:
            sucio = subprocess.run(["git", "status", "--porcelain"], capture_output=True,
                                   text=True, timeout=5, cwd=Path(__file__).parent).stdout.strip()
            return r.stdout.strip() + ("+cambios-sin-commit" if sucio else "")
    except (OSError, subprocess.SubprocessError):
        pass
    return "desconocido"


def guardar_version(directorio: Path, pipeline, metricas: dict, metadata: dict) -> dict:
    rutas = {"modelo": directorio / NOMBRE_MODELO,
             "metricas": directorio / NOMBRE_METRICAS,
             "metadata": directorio / NOMBRE_METADATA}
    joblib.dump(pipeline, rutas["modelo"], compress=3)
    for clave, contenido in (("metricas", metricas), ("metadata", metadata)):
        with open(rutas[clave], "w", encoding="utf-8") as f:
            json.dump(contenido, f, indent=2, ensure_ascii=False)
    return rutas


def resolver_ruta_modelo(ruta) -> Path:
    """Acepta la ruta al .joblib o a la carpeta de la versión."""
    ruta = Path(ruta)
    if ruta.is_dir():
        ruta = ruta / NOMBRE_MODELO
    if not ruta.is_file():
        raise ModeloNoEncontradoError(f"No se encontró el modelo: {ruta}")
    return ruta


def cargar_version(ruta):
    """Devuelve (pipeline, metadata) de una versión guardada."""
    ruta_modelo = resolver_ruta_modelo(ruta)
    try:
        pipeline = joblib.load(ruta_modelo)
    except Exception as e:
        raise ModeloNoEncontradoError(f"No se pudo leer el modelo {ruta_modelo}: {e}") from e
    ruta_meta = ruta_modelo.parent / NOMBRE_METADATA
    if not ruta_meta.is_file():
        raise ModeloNoEncontradoError(f"Falta {NOMBRE_METADATA} junto al modelo: {ruta_meta}")
    with open(ruta_meta, encoding="utf-8") as f:
        return pipeline, json.load(f)
