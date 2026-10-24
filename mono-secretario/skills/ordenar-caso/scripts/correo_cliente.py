"""Devuelve el correo real de una clave [EMAIL_n] de la tabla de datos personales del caso.

Uso:
    python3 correo_cliente.py <carpeta del caso> [--clave "[EMAIL_n]"]

Claude trabaja solo con claves y nunca envía [EMAIL_n] al MCP. Cuando decide con los hechos anonimizados
qué clave es la del cliente, este script le da el valor real de esa clave y de ninguna otra:
- sin --clave imprime {"ok": true, "claves": ["[EMAIL_1]", ...]}, solo las claves de correo y sin valores;
- con --clave imprime {"ok": true, "clave": "[EMAIL_1]", "email": "ana@ejemplo.com"}, recortado y en minúsculas;
- cualquier otra clave ([CLIENTE], [DNI_1], [TEL_1]...) se rechaza sin revelar nada.
La salida es siempre JSON en una línea. Los errores llevan {"ok": false, "error": "..."}.
Códigos de salida: 0 correcto, 1 error, 2 uso incorrecto.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

TABLA = Path(".monolegal") / "datos_personales.json"
CLAVE_EMAIL = re.compile(r"\[EMAIL_(\d+)\]")


def _error(mensaje: str) -> dict:
    return {"ok": False, "error": mensaje}


def _leer_tabla(carpeta_caso: Path) -> dict | None:
    try:
        datos = json.loads((carpeta_caso / TABLA).read_text(encoding="utf-8")).get("datos")
    except (OSError, ValueError, AttributeError):
        return None
    return datos if isinstance(datos, dict) else None


def resolver(carpeta_caso: Path, clave: str | None) -> dict:
    datos = _leer_tabla(Path(carpeta_caso))
    if datos is None:
        return _error(f"Falta la tabla {TABLA.as_posix()} del caso: pregunta el correo al abogado.")

    if clave is None:
        claves = [k for k in datos if CLAVE_EMAIL.fullmatch(k)]
        claves.sort(key=lambda k: int(CLAVE_EMAIL.fullmatch(k).group(1)))
        return {"ok": True, "claves": claves}

    if not CLAVE_EMAIL.fullmatch(clave):
        return _error("Solo se revelan claves de correo con la forma [EMAIL_n].")
    if clave not in datos:
        return _error(f"La clave {clave} no está en la tabla del caso: pregunta el correo al abogado.")
    valor = datos[clave]
    if not isinstance(valor, str) or not valor.strip():
        return _error(f"La clave {clave} no tiene un correo guardado: pregunta el correo al abogado.")
    return {"ok": True, "clave": clave, "email": valor.strip().lower()}


def main(argumentos: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("carpeta")
    parser.add_argument("--clave")
    try:
        args = parser.parse_args(argumentos)
    except SystemExit:
        return 2
    resultado = resolver(Path(args.carpeta), args.clave)
    print(json.dumps(resultado, ensure_ascii=False))
    return 0 if resultado["ok"] else 1


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main())
