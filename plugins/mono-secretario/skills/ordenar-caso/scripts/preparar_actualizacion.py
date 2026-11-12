"""Prepara la llamada a actualizar_caso del MCP de casos a partir de la propuesta que confirmó el abogado.

Uso:
    python3 preparar_actualizacion.py <propuesta.json> --fases "<fase>" [--fases "<fase>" ...]

propuesta.json: {"casoId": "...", "actuaciones": [{"fecha", "autor", "descripcion"}], "faseActual": "...",
"siguientePaso": {"descripcion", "responsable", "fechaLimite"}}. Actuaciones, fase y siguiente paso son opcionales,
pero tiene que haber al menos uno. --fases son las fases del caso guardado (la fase nueva debe ser una de ellas).

Imprime {"ok": true, "actualizar_caso": {...}} con solo lo que cambia (sin fase ni siguiente paso si no cambian).
- Fechas: un día suelto (AAAA-MM-DD) se envía a las 12:00 con la zona de Madrid, como en preparar_publicacion.py.
- La fecha límite del siguiente paso solo viaja si la fijó el abogado: nunca se calcula ni se inventa.
Códigos de salida: 0 correcto, 1 hay que corregir la propuesta (imprime los problemas), 2 uso incorrecto.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))  # los módulos hermanos, también con python -I

from preparar_publicacion import CLAVE_DATO_PERSONAL, fecha_con_zona
from validacion import validar_actuacion, validar_siguiente_paso

SIN_CAMBIOS = "no hay nada que actualizar: la propuesta no trae actuaciones, fase ni siguiente paso"


def _claves_de_datos_personales(campo: str, texto) -> list[str]:
    claves = sorted(set(CLAVE_DATO_PERSONAL.findall(texto))) if isinstance(texto, str) else []
    if not claves:
        return []
    return [f"{campo} lleva claves de datos personales ({', '.join(claves)}): reescríbelo para el cliente, en segunda persona y sin nombres"]


def preparar(propuesta: dict, fases_del_caso: list[str]) -> tuple[dict, list[str]]:
    """Devuelve (argumentos de actualizar_caso, problemas). Si hay problemas, no se debe llamar a la tool."""
    problemas: list[str] = []
    caso_id = propuesta.get("casoId")
    if not (isinstance(caso_id, str) and caso_id.strip()):
        problemas.append("casoId está vacío: hace falta el Id del caso guardado")

    actuaciones = propuesta.get("actuaciones") or []
    fase = propuesta.get("faseActual")
    paso = propuesta.get("siguientePaso")
    if not actuaciones and not fase and not paso:
        problemas.append(SIN_CAMBIOS)

    for i, actuacion in enumerate(actuaciones):
        problemas += validar_actuacion(actuacion, i)
        problemas += _claves_de_datos_personales(f"actuaciones[{i}].descripcion", actuacion.get("descripcion"))
    if fase and fase not in fases_del_caso:
        problemas.append(f"faseActual '{fase}' no está entre las fases del caso: {', '.join(fases_del_caso)}")
    if paso:
        problemas += validar_siguiente_paso(paso)
        problemas += _claves_de_datos_personales("siguientePaso.descripcion", paso.get("descripcion"))
    if problemas:
        return {}, problemas

    argumentos: dict = {"casoId": caso_id.strip()}
    if actuaciones:
        argumentos["actuaciones"] = [
            {"fecha": fecha_con_zona(a["fecha"]), "descripcion": a["descripcion"].strip(), "autor": a["autor"]} for a in actuaciones]
    if fase:
        argumentos["faseActual"] = fase
    if paso:
        argumentos["siguientePaso"] = {"descripcion": paso["descripcion"].strip(), "responsable": paso["responsable"]}
        if paso.get("fechaLimite"):
            argumentos["siguientePaso"]["fechaLimite"] = fecha_con_zona(paso["fechaLimite"])
    return argumentos, []


def main(argumentos: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("propuesta")
    parser.add_argument("--fases", action="append", default=[])
    try:
        args = parser.parse_args(argumentos)
    except SystemExit:
        return 2
    try:
        propuesta = json.loads(Path(args.propuesta).read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        print(json.dumps({"ok": False, "errores": [f"No se pudo leer la propuesta: {error}"]}, ensure_ascii=False, indent=1))
        return 1

    llamada, problemas = preparar(propuesta, args.fases)
    if problemas:
        print(json.dumps({"ok": False, "errores": problemas}, ensure_ascii=False, indent=1))
        return 1
    print(json.dumps({"ok": True, "actualizar_caso": llamada}, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main())
