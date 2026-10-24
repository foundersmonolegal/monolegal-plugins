"""Reglas de forma que comparten la página de revisión y la publicación en el MCP de casos.

Uso como comando: python3 validacion.py <propuesta.json o confirmado.json>
Imprime {"ok": ..., "errores": [...]} y sale con 0 si es válido o 1 si no.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

AUTORES = ("Abogado", "Cliente", "Juzgado", "Contraparte", "Administracion")
FECHA = re.compile(r"^\d{4}-\d{2}-\d{2}$")
FECHA_HORA_ZONA = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}(?::\d{2})?(?:Z|[+-]\d{2}:\d{2})$")


def _fecha_correcta(valor) -> bool:
    return isinstance(valor, str) and bool(FECHA.match(valor) or FECHA_HORA_ZONA.match(valor))


def _texto(valor) -> bool:
    return isinstance(valor, str) and bool(valor.strip())


TIPOS_EVIDENCIA = ("resolucion", "escrito", "whatsapp", "documento", "correo")


def validar_propuesta(propuesta: dict) -> list[str]:
    """Problemas de la propuesta que genera Claude: el contenido más el resumen y las evidencias de la revisión."""
    errores = validar_contenido(propuesta)
    if not _texto(propuesta.get("resumen")):
        errores.append("resumen está vacío: hace falta un párrafo que cuente el caso al abogado")
    if propuesta.get("correosLeidos") not in (None, "") and not (isinstance(propuesta.get("correosLeidos"), int) and propuesta["correosLeidos"] >= 0):
        errores.append("correosLeidos debe ser un número entero, 0 si no hay correo")
    evidencias = propuesta.get("evidencias")
    if not isinstance(evidencias, list) or not evidencias:
        errores.append("evidencias debe tener al menos una fuente")
        evidencias = []
    for i, evidencia in enumerate(evidencias):
        if evidencia.get("tipo") not in TIPOS_EVIDENCIA:
            errores.append(f"evidencias[{i}].tipo debe ser uno de {', '.join(TIPOS_EVIDENCIA)}")
        if not _texto(evidencia.get("fuente")) or not _texto(evidencia.get("aporta")):
            errores.append(f"evidencias[{i}] necesita fuente y aporta")
        if evidencia.get("fecha") not in (None, "") and not _fecha_correcta(evidencia.get("fecha")):
            errores.append(f"evidencias[{i}].fecha debe ser AAAA-MM-DD o vacía")
    return errores


def validar_contenido(propuesta: dict) -> list[str]:
    """Problemas de lo que se publica: vale para la propuesta y para la revisión confirmada."""
    errores = []
    caso = propuesta.get("caso") or {}
    for campo in ("nombre", "nombreCliente"):
        if not _texto(caso.get(campo)):
            errores.append(f"caso.{campo} está vacío")

    fases = propuesta.get("fases")
    if not isinstance(fases, list) or not fases or not all(_texto(f) for f in fases):
        errores.append("fases debe ser una lista de textos no vacía")
        fases = []
    if propuesta.get("faseActual") not in fases:
        errores.append("faseActual debe ser exactamente una de las fases")

    paso = propuesta.get("siguientePaso") or {}
    if not _texto(paso.get("descripcion")):
        errores.append("siguientePaso.descripcion está vacío")
    if paso.get("responsable") not in AUTORES:
        errores.append(f"siguientePaso.responsable debe ser uno de {', '.join(AUTORES)}")
    if paso.get("fechaLimite") not in (None, "") and not _fecha_correcta(paso.get("fechaLimite")):
        errores.append("siguientePaso.fechaLimite debe ser AAAA-MM-DD o vacía")

    actuaciones = propuesta.get("actuaciones")
    if not isinstance(actuaciones, list) or not actuaciones:
        errores.append("actuaciones debe tener al menos una actuación")
        actuaciones = []
    ids = [a.get("id") for a in actuaciones]
    if len(set(ids)) != len(ids) or not all(_texto(i) for i in ids):
        errores.append("cada actuación necesita un id único")
    for i, actuacion in enumerate(actuaciones):
        if not _fecha_correcta(actuacion.get("fecha")):
            errores.append(f"actuaciones[{i}].fecha debe ser AAAA-MM-DD o fecha y hora con zona")
        if actuacion.get("autor") not in AUTORES:
            errores.append(f"actuaciones[{i}].autor debe ser uno de {', '.join(AUTORES)}")
        if not _texto(actuacion.get("descripcion")):
            errores.append(f"actuaciones[{i}].descripcion está vacía")
    return errores


def main(argumentos: list[str] | None = None) -> int:
    argumentos = sys.argv[1:] if argumentos is None else argumentos
    if len(argumentos) != 1:
        print(__doc__, file=sys.stderr)
        return 2
    documento = json.loads(Path(argumentos[0]).read_text(encoding="utf-8"))
    errores = validar_contenido(documento) if documento.get("_tipo") == "revision-confirmada" else validar_propuesta(documento)
    print(json.dumps({"ok": not errores, "errores": errores}, ensure_ascii=False, indent=1))
    return 0 if not errores else 1


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main())
