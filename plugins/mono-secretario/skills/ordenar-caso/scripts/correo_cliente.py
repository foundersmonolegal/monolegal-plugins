"""Devuelve el correo o el teléfono real de una clave [EMAIL_n] o [TEL_n] de la tabla de datos personales del caso.

Uso:
    python3 correo_cliente.py <carpeta del caso> [--clave "[EMAIL_n]" | "[TEL_n]"]

Claude trabaja solo con claves y nunca envía [EMAIL_n] ni [TEL_n] al MCP. Cuando decide con los hechos anonimizados
qué clave es la del cliente, este script le da el valor real de esa clave y de ninguna otra:
- sin --clave imprime {"ok": true, "claves": ["[EMAIL_1]", ..., "[TEL_1]", ...]}, solo las claves de correo y de
  teléfono, sin valores;
- con --clave "[EMAIL_n]" imprime {"ok": true, "clave": "[EMAIL_1]", "email": "ana@ejemplo.com"}, recortado y en
  minúsculas;
- con --clave "[TEL_n]" imprime {"ok": true, "clave": "[TEL_1]", "telefono": "+34 612 34 56 78"}, recortado;
- cualquier otra clave ([CLIENTE], [DNI_1], [IBAN_1]...) se rechaza sin revelar nada.
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
CLAVE_TELEFONO = re.compile(r"\[TEL_(\d+)\]")
# Tipos de clave que se pueden revelar, en el orden en que se listan: (patrón, campo de la respuesta, normalización).
TIPOS_REVELABLES = (
    (CLAVE_EMAIL, "email", lambda valor: valor.strip().lower()),
    (CLAVE_TELEFONO, "telefono", lambda valor: valor.strip()),
)


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
        return _error(f"Falta la tabla {TABLA.as_posix()} del caso: pregunta el correo o el teléfono al abogado.")

    if clave is None:
        return {"ok": True, "claves": _claves_revelables(datos)}

    tipo = next(((campo, normalizar) for patron, campo, normalizar in TIPOS_REVELABLES if patron.fullmatch(clave)), None)
    if tipo is None:
        return _error("Solo se revelan claves de correo o de teléfono con la forma [EMAIL_n] o [TEL_n].")
    campo, normalizar = tipo
    if clave not in datos:
        return _error(f"La clave {clave} no está en la tabla del caso: pregunta el dato al abogado.")
    valor = datos[clave]
    if not isinstance(valor, str) or not valor.strip():
        return _error(f"La clave {clave} no tiene un valor guardado: pregunta el dato al abogado.")
    return {"ok": True, "clave": clave, campo: normalizar(valor)}


def _claves_revelables(datos: dict) -> list[str]:
    claves = []
    for patron, _, _ in TIPOS_REVELABLES:
        del_tipo = [k for k in datos if patron.fullmatch(k)]
        del_tipo.sort(key=lambda k: int(patron.fullmatch(k).group(1)))
        claves.extend(del_tipo)
    return claves


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
