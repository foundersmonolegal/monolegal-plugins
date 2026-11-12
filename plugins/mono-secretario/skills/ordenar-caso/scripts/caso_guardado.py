"""Recuerda en la carpeta del caso el Id con el que se guardó en el MCP de casos.

Uso:
    python3 caso_guardado.py escribir <carpeta del caso> <Id del caso>
    python3 caso_guardado.py leer <carpeta del caso>

El archivo .monolegal/caso.json no lleva datos personales: solo el Id, cuándo se guardó y la versión del plugin.
ordenar-caso lo escribe al guardar el caso; actualizar-caso lo lee para saber qué caso actualizar sin preguntar.

Códigos de salida: 0 correcto, 1 el Id está vacío (no se escribe nada), 3 la carpeta no recuerda ningún caso,
2 uso incorrecto.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))  # los módulos hermanos, también con python -I

from registro import VERSION_PLUGIN, ahora

ARCHIVO = Path(".monolegal") / "caso.json"
SIN_CASO_RECORDADO = 3


def escribir(carpeta: Path, caso_id: str) -> Path:
    if not isinstance(caso_id, str) or not caso_id.strip():
        raise ValueError("El Id del caso está vacío: no hay nada que recordar.")
    ruta = Path(carpeta) / ARCHIVO
    ruta.parent.mkdir(parents=True, exist_ok=True)
    datos = {"casoId": caso_id.strip(), "guardado": ahora(), "versionPlugin": VERSION_PLUGIN}
    ruta.write_text(json.dumps(datos, ensure_ascii=False, indent=1), encoding="utf-8")
    return ruta


def leer(carpeta: Path) -> str | None:
    """El Id recordado, o None si no hay archivo, está corrupto o no trae un Id (todo eso es «sin caso recordado»)."""
    try:
        datos = json.loads((Path(carpeta) / ARCHIVO).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    caso_id = datos.get("casoId") if isinstance(datos, dict) else None
    return caso_id.strip() if isinstance(caso_id, str) and caso_id.strip() else None


def main(argumentos: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ordenes = parser.add_subparsers(dest="orden", required=True)
    orden_escribir = ordenes.add_parser("escribir")
    orden_escribir.add_argument("carpeta")
    orden_escribir.add_argument("caso_id")
    orden_leer = ordenes.add_parser("leer")
    orden_leer.add_argument("carpeta")
    try:
        args = parser.parse_args(argumentos)
    except SystemExit:
        return 2

    if args.orden == "escribir":
        try:
            ruta = escribir(Path(args.carpeta), args.caso_id)
        except ValueError as error:
            print(json.dumps({"error": str(error)}, ensure_ascii=False))
            return 1
        print(json.dumps({"ruta": str(ruta)}, ensure_ascii=False))
        return 0

    caso_id = leer(Path(args.carpeta))
    print(json.dumps({"casoId": caso_id}, ensure_ascii=False))
    return 0 if caso_id else SIN_CASO_RECORDADO


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main())
