"""Prepara las llamadas al MCP de casos (Mono Virtual) a partir de la revisión confirmada.

Uso:
    python3 preparar_publicacion.py <confirmado.json> --cliente "<nombre del cliente>" [--contrato v2|v1]

Imprime {"ok": true, "crear_caso": {...}, "registrar_actuaciones": {...}, "actualizar_estado_caso": {...}, "avisos": [...]}.
- Fechas: un día suelto (AAAA-MM-DD) se envía a las 12:00 con la zona de Madrid (+01:00 o +02:00).
- Código de cliente: "CLI-" y 6 caracteres sacados del nombre; el mismo cliente da siempre el mismo código.
- Contrato v2 (MCP actualizado): autores Juzgado, Contraparte y Administracion y siguiente paso propio.
  Contrato v1 (MCP anterior): esos tres se envían como Abogado y el siguiente paso solo viaja como pendiente.
- El siguiente paso con fecha límite también se envía como pendiente, que es lo que muestra hoy la app.
Códigos de salida: 0 correcto, 1 hay que corregir la revisión (imprime los problemas), 2 uso incorrecto.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))  # los módulos hermanos, también con python -I

from privacidad import normalizar
from validacion import validar_contenido

CLAVE_DATO_PERSONAL = re.compile(r"\[(?:CLIENTE|ABOGADO|[A-Z]+_\d+)\]")
# Una clave del nombre del caso con lo que la une al resto: "de [CLIENTE]", "[CLIENTE] - ", "y [PERSONA_1]".
CLAVE_EN_NOMBRE = re.compile(r"\s*(?:\b(?:de|del|para|a|y|con)\s+)?" + CLAVE_DATO_PERSONAL.pattern + r"\s*(?:[-–—·,:]\s*)?")
AUTORES_V1 = {"Juzgado": "Abogado", "Contraparte": "Abogado", "Administracion": "Abogado"}


def _ultimo_domingo(anio: int, mes: int) -> dt.date:
    dia = dt.date(anio, mes + 1, 1) - dt.timedelta(days=1)
    return dia - dt.timedelta(days=(dia.weekday() + 1) % 7)


def zona_madrid(fecha: dt.date) -> str:
    """Horario de verano de la UE: del último domingo de marzo al último domingo de octubre (a mediodía)."""
    verano = _ultimo_domingo(fecha.year, 3) <= fecha < _ultimo_domingo(fecha.year, 10)
    return "+02:00" if verano else "+01:00"


def fecha_con_zona(valor: str | None) -> str | None:
    if not valor:
        return None
    if re.match(r"^\d{4}-\d{2}-\d{2}$", valor):
        dia = dt.date.fromisoformat(valor)
        return f"{valor}T12:00:00{zona_madrid(dia)}"
    return valor


def codigo_cliente(nombre: str) -> str:
    return "CLI-" + hashlib.sha256(normalizar(nombre).encode("utf-8")).hexdigest()[:6].upper()


def preparar(confirmado: dict, cliente: str, contrato: str = "v2") -> tuple[dict, list[str]]:
    """Devuelve (llamadas, problemas). Si hay problemas, no se debe publicar."""
    problemas = validar_contenido(confirmado)
    avisos: list[str] = []
    paso = confirmado.get("siguientePaso") or {}

    textos = [("siguientePaso.descripcion", paso.get("descripcion"))]
    textos += [(f"actuaciones[{i}].descripcion", a.get("descripcion")) for i, a in enumerate(confirmado.get("actuaciones") or [])]
    for campo, texto in textos:
        if texto and CLAVE_DATO_PERSONAL.search(texto):
            problemas.append(f"{campo} lleva claves de datos personales ({', '.join(sorted(set(CLAVE_DATO_PERSONAL.findall(texto))))}): "
                             "reescríbelo para el cliente, en segunda persona y sin nombres")
    if problemas:
        return {}, problemas

    caso = confirmado["caso"]
    # El cliente ve el nombre del caso en su app: va sin su nombre (ya sabe que el caso es suyo) ni otros datos personales.
    if set(CLAVE_DATO_PERSONAL.findall(caso["nombre"])) - {"[CLIENTE]"}:
        avisos.append("Se han quitado del nombre del caso claves de datos personales distintas del cliente.")
    nombre_caso = re.sub(r"\s+", " ", CLAVE_EN_NOMBRE.sub(" ", caso["nombre"])).strip(" -–—·,:") or "Caso"

    actuaciones = []
    for actuacion in confirmado["actuaciones"]:
        autor = actuacion["autor"]
        if contrato == "v1" and autor in AUTORES_V1:
            autor = AUTORES_V1[autor]
        actuaciones.append({"fecha": fecha_con_zona(actuacion["fecha"]), "descripcion": actuacion["descripcion"].strip(), "autor": autor})
    if contrato == "v1" and any(a["autor"] in AUTORES_V1 for a in confirmado["actuaciones"]):
        avisos.append("Contrato v1: las actuaciones del juzgado, la contraparte o la Administración se envían con autor Abogado.")

    fecha_limite = fecha_con_zona(paso.get("fechaLimite"))
    pendientes = [{"descripcion": paso["descripcion"].strip(), "fechaLimite": fecha_limite}] if fecha_limite else []
    estado = {"fases": confirmado["fases"], "faseActual": confirmado["faseActual"], "pendientes": pendientes}
    if contrato == "v2":
        estado["siguientePaso"] = {"descripcion": paso["descripcion"].strip(), "responsable": paso["responsable"], "fechaLimite": fecha_limite}
    else:
        if not fecha_limite:
            avisos.append("Contrato v1: el siguiente paso no tiene fecha límite, así que no se puede enviar como pendiente.")
        if paso.get("responsable") in AUTORES_V1:
            avisos.append("Contrato v1: el responsable del siguiente paso no viaja; el MCP anterior no lo admite.")

    llamadas = {
        "crear_caso": {"nombre": nombre_caso, "codigoCliente": codigo_cliente(cliente), "nombreCliente": cliente.strip()},
        "registrar_actuaciones": {"actuaciones": actuaciones},
        "actualizar_estado_caso": estado,
    }
    return llamadas, avisos


def main(argumentos: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("confirmado")
    parser.add_argument("--cliente", required=True)
    parser.add_argument("--contrato", choices=("v2", "v1"), default="v2")
    try:
        args = parser.parse_args(argumentos)
    except SystemExit:
        return 2
    confirmado = json.loads(Path(args.confirmado).read_text(encoding="utf-8"))
    llamadas, mensajes = preparar(confirmado, args.cliente, args.contrato)
    if not llamadas:
        print(json.dumps({"ok": False, "errores": mensajes}, ensure_ascii=False, indent=1))
        return 1
    print(json.dumps({"ok": True, "contrato": args.contrato, **llamadas, "avisos": mensajes}, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main())
