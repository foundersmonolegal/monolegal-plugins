"""Registra cuánto tarda cada ejecución del plugin y prepara su telemetría para el MCP.

Uso:
    python3 registro.py <carpeta del caso> marcar <hito>
    python3 registro.py <carpeta del caso> ejecucion [--caso-id ID] [--resultado publicado|sin_publicar|error]

Hitos, en orden: inicio, identificado, propuesta, confirmado, publicado. "inicio" abre una ejecución nueva.
"ejecucion" imprime los datos para la tool registrar_ejecucion (tiempos, cifras de lo leído y si el abogado
cambió la fase o el siguiente paso), sin datos personales, y los guarda en .monolegal/registro.json.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
from pathlib import Path

VERSION_PLUGIN = "0.5.0"
TRAMOS = [("identificar", "inicio", "identificado"), ("lectura_y_propuesta", "identificado", "propuesta"),
          ("revision_abogado", "propuesta", "confirmado"), ("publicacion", "confirmado", "publicado")]


def _leer(ruta: Path) -> dict:
    try:
        return json.loads(ruta.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def ahora() -> str:
    return dt.datetime.now().astimezone().isoformat(timespec="seconds")


def marcar(trabajo: Path, hito: str, instante: str | None = None) -> dict:
    registro = _leer(trabajo / "registro.json")
    actual = registro.get("actual")
    if hito == "inicio" or not actual:
        if actual:
            registro.setdefault("anteriores", []).append(actual)
        actual = {"hitos": {}}
    actual["hitos"][hito] = instante or ahora()
    registro["actual"] = actual
    (trabajo / "registro.json").write_text(json.dumps(registro, ensure_ascii=False, indent=1), encoding="utf-8")
    return actual


def ejecucion(trabajo: Path, caso_id: str | None, resultado: str) -> dict:
    registro = _leer(trabajo / "registro.json")
    hitos = (registro.get("actual") or {}).get("hitos", {})
    instantes = {h: dt.datetime.fromisoformat(v) for h, v in hitos.items()}
    duraciones = {nombre: int((instantes[fin] - instantes[ini]).total_seconds())
                  for nombre, ini, fin in TRAMOS if ini in instantes and fin in instantes}
    ordenados = sorted(instantes.values())
    if len(ordenados) >= 2:
        duraciones["total"] = int((ordenados[-1] - ordenados[0]).total_seconds())

    lectura = _leer(trabajo / "fuentes.json").get("lectura", {})
    propuesta = _leer(trabajo / "propuesta.json")
    cambios = _leer(trabajo / "confirmado.json").get("cambios", {})
    datos = {
        "casoId": caso_id,
        "versionPlugin": VERSION_PLUGIN,
        "iniciadaEn": hitos.get("inicio"),
        "finalizadaEn": max(hitos.values()) if hitos else None,
        "duracionesSegundos": duraciones,
        "fuentes": {
            "documentos": lectura.get("documentos", 0),
            "descartados": lectura.get("descartados", 0),
            "mensajesWhatsapp": lectura.get("mensajes_whatsapp", 0),
            "hilosCorreo": propuesta.get("correosLeidos") or 0,
        },
        "resultado": resultado,
        "faseModificada": cambios.get("faseModificada"),
        "siguientePasoModificado": cambios.get("siguientePasoModificado"),
    }
    if registro.get("actual") is not None:
        registro["actual"]["ejecucion"] = datos
        (trabajo / "registro.json").write_text(json.dumps(registro, ensure_ascii=False, indent=1), encoding="utf-8")
    return datos


def main(argumentos: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("carpeta")
    sub = parser.add_subparsers(dest="orden", required=True)
    sub_marcar = sub.add_parser("marcar")
    sub_marcar.add_argument("hito", choices=["inicio", "identificado", "propuesta", "confirmado", "publicado"])
    sub_ejecucion = sub.add_parser("ejecucion")
    sub_ejecucion.add_argument("--caso-id")
    sub_ejecucion.add_argument("--resultado", choices=["publicado", "sin_publicar", "error"], default="publicado")
    try:
        args = parser.parse_args(argumentos)
    except SystemExit:
        return 2
    trabajo = Path(args.carpeta) / ".monolegal"
    trabajo.mkdir(parents=True, exist_ok=True)
    if args.orden == "marcar":
        marcar(trabajo, args.hito)
        return 0
    print(json.dumps(ejecucion(trabajo, args.caso_id, args.resultado), ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main())
