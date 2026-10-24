"""Genera la página de revisión del caso a partir de propuesta.json.

Uso:
    python3 generar_revision.py <propuesta.json> <revision.html> [--fuentes fuentes.json] [--datos datos_personales.json]
    python3 generar_revision.py <confirmado.json> <guardado.html> --guardado <casoId> [--datos datos_personales.json]

Con --guardado genera, a partir de la revisión confirmada, la confirmación "Guardado en la memoria del mono" con la
vista previa del móvil de su cliente (assets/vista-cliente.html).

Valida la propuesta (validacion.py) e incrusta en assets/revision.html la propuesta, las cifras de
lo que se ha leído (de fuentes.json) y la tabla de datos personales (de datos_personales.json), para
que la página le muestre los nombres reales solo al abogado y los vuelva a ocultar al copiar.
Códigos de salida: 0 correcto, 1 propuesta inválida (imprime los problemas), 2 uso incorrecto.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))  # los módulos hermanos, también con python -I

from validacion import validar_contenido, validar_propuesta

MARCADOR = "/*__DATOS_PAGINA__*/null"


def plantilla(nombre: str = "revision.html") -> str:
    aqui = Path(__file__).resolve().parent
    for candidato in (aqui / nombre, aqui.parent / "assets" / nombre):
        if candidato.is_file():
            return candidato.read_text(encoding="utf-8")
    raise FileNotFoundError(f"No encuentro assets/{nombre}")


def incrustar(pagina: dict, html: str) -> str:
    """Inserta los datos como JSON dentro de un <script>; '</' se escapa para que ningún texto cierre la etiqueta."""
    datos = json.dumps(pagina, ensure_ascii=False).replace("</", "<\\/")
    if MARCADOR not in html:
        raise ValueError("La plantilla no tiene el marcador de datos")
    return html.replace(MARCADOR, datos)


def _leer_json(ruta: str | None) -> dict:
    return json.loads(Path(ruta).read_text(encoding="utf-8")) if ruta and Path(ruta).is_file() else {}


def main(argumentos: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("propuesta")
    parser.add_argument("revision")
    parser.add_argument("--fuentes")
    parser.add_argument("--datos")
    parser.add_argument("--guardado", metavar="CASO_ID")
    try:
        args = parser.parse_args(argumentos)
    except SystemExit:
        return 2
    propuesta = json.loads(Path(args.propuesta).read_text(encoding="utf-8"))
    errores = validar_contenido(propuesta) if args.guardado else validar_propuesta(propuesta)
    if errores:
        print(json.dumps({"ok": False, "errores": errores}, ensure_ascii=False, indent=1))
        return 1
    pagina = {
        "propuesta": propuesta,
        "lectura": _leer_json(args.fuentes).get("lectura", {}),
        "datos": _leer_json(args.datos).get("datos", {}),
    }
    if args.guardado:
        pagina["guardado"] = {"casoId": args.guardado, "en": dt.date.today().isoformat()}
    html = plantilla("vista-cliente.html" if args.guardado else "revision.html")
    Path(args.revision).write_text(incrustar(pagina, html), encoding="utf-8")
    print(json.dumps({"ok": True, "revision": args.revision}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main())
