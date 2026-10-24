"""Elige qué archivos de la carpeta del caso traer, sin abrirlos, a partir de su listado.

Uso:
    python3 seleccionar_fuentes.py elegir <listado.json> [--tanda 15]
    python3 seleccionar_fuentes.py fechas <carpeta de trabajo> <listado.json>

La carpeta del caso suele estar en Google Drive (unidad G: en Windows), que la terminal no puede montar.
Por eso se lista con la herramienta de archivos de la app y solo se traen los archivos necesarios:
traer la carpeta entera obligaría a Drive a descargarla completa.

listado.json: lista (o {"archivos": [...]}) de {"ruta": relativa a la carpeta del caso, "modificado": fecha ISO,
"bytes": tamaño, opcional}.

elegir: descarta archivos de sistema, formatos que no se leen, los demasiado grandes y las carpetas de
jurisprudencia, y ordena el resto: chats de WhatsApp, las resoluciones más recientes por su nombre
(«Auto», «Sentencia», LexNET...) y después todo lo demás por fecha. Imprime las tandas a traer, como mucho tres.
fechas: al traerlos, las copias pierden su fecha; les devuelve la original para que identificar_caso.py
ordene bien.

Códigos de salida: 0 correcto, 4 nada que leer, 2 uso incorrecto.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import sys
from pathlib import Path, PurePosixPath

sys.path.insert(0, str(Path(__file__).resolve().parent))  # los módulos hermanos, también con python -I

import whatsapp
from identificar_caso import EXTENSIONES_LEIBLES, Reglas, cargar_patrones, datos_lexnet, en_carpeta_jurisprudencia, fecha_en_nombre, normalizar

ARCHIVOS_DE_SISTEMA = {"desktop.ini", "thumbs.db", ".ds_store"}
MAX_CHATS = 4               # el abogado puede hablar con el cliente desde dos teléfonos
RESOLUCIONES_PRIORITARIAS = 5


def _ruta(valor: str) -> str:
    ruta = str(valor).replace("\\", "/").lstrip("/")
    return ruta[2:] if ruta.startswith("./") else ruta


def _fecha(valor: str | None) -> dt.datetime:
    """Fecha ISO, con o sin hora y con o sin zona, como hora local sin zona."""
    texto = str(valor or "").strip().replace(" ", "T").replace("Z", "+00:00")
    try:
        fecha = dt.datetime.fromisoformat(texto)
    except ValueError:
        return dt.datetime.min
    return fecha.astimezone().replace(tzinfo=None) if fecha.tzinfo else fecha


def _archivos(listado: list | dict) -> list[dict]:
    return listado.get("archivos", []) if isinstance(listado, dict) else listado


def _motivo_descarte(ruta: PurePosixPath, tamano: int, reglas: Reglas) -> str | None:
    nombre = ruta.name.lower()
    if nombre in ARCHIVOS_DE_SISTEMA or nombre.startswith("~$") or any(parte.startswith(".") for parte in ruta.parts):
        return "sistema"
    if en_carpeta_jurisprudencia(ruta, reglas):
        return "jurisprudencia"
    if ruta.suffix.lower() not in EXTENSIONES_LEIBLES and not _es_chat(ruta):
        return "formato"
    if tamano > reglas.limites["max_mb_por_archivo"] * 1024 * 1024:
        return "tamano"
    return None


def _es_chat(ruta: PurePosixPath) -> bool:
    return ruta.suffix.lower() in (".txt", ".zip") and (
        bool(whatsapp.NOMBRE_ARCHIVO.search(ruta.name)) or "whatsapp" in ruta.name.lower())


def _es_resolucion(ruta: PurePosixPath, reglas: Reglas) -> bool:
    palabras = set(normalizar(ruta.stem).split())
    return bool(datos_lexnet(ruta.name, reglas)) or any(clave in palabras for clave in reglas.nombres_resolucion)


def _fecha_estimada(ruta: PurePosixPath, modificado: dt.datetime, reglas: Reglas, hoy: dt.date) -> dt.datetime:
    lexnet = datos_lexnet(ruta.name, reglas)
    if lexnet:
        return lexnet["notificacion"]
    del_nombre = fecha_en_nombre(ruta.stem, reglas, hoy)
    return dt.datetime.combine(del_nombre, dt.time.min) if del_nombre else modificado


def elegir(listado: list | dict, tamano_tanda: int = 15, max_tandas: int = 3, hoy: dt.date | None = None) -> dict:
    hoy = hoy or dt.date.today()
    reglas = Reglas(cargar_patrones())
    archivos = _archivos(listado)
    descartados: dict[str, int] = {}
    candidatos = []
    for entrada in archivos:
        ruta = PurePosixPath(_ruta(entrada["ruta"]))
        motivo = _motivo_descarte(ruta, int(entrada.get("bytes") or 0), reglas)
        if motivo:
            descartados[motivo] = descartados.get(motivo, 0) + 1
            continue
        candidatos.append({"ruta": str(ruta), "fecha": _fecha_estimada(ruta, _fecha(entrada.get("modificado")), reglas, hoy),
                           "chat": _es_chat(ruta), "resolucion": _es_resolucion(ruta, reglas)})

    por_fecha = sorted(candidatos, key=lambda c: c["fecha"], reverse=True)
    chats = [c for c in por_fecha if c["chat"]][:MAX_CHATS]
    resoluciones = [c for c in por_fecha if c["resolucion"] and not c["chat"]][:RESOLUCIONES_PRIORITARIAS]
    primero = chats + resoluciones
    orden = [c["ruta"] for c in primero + [c for c in por_fecha if c not in primero]]
    tandas = [orden[i:i + tamano_tanda] for i in range(0, len(orden), tamano_tanda)][:max_tandas]
    return {"total": len(archivos), "candidatos": len(candidatos), "descartados": descartados,
            "whatsapp": [c["ruta"] for c in chats], "tandas": tandas}


def fijar_fechas(trabajo: Path, listado: list | dict) -> dict:
    ajustados = sin_copia = 0
    for entrada in _archivos(listado):
        copia = trabajo / _ruta(entrada["ruta"])
        if not copia.is_file():
            sin_copia += 1
            continue
        marca = _fecha(entrada.get("modificado")).timestamp()
        os.utime(copia, (marca, marca))
        ajustados += 1
    return {"ajustados": ajustados, "sin_copia": sin_copia}


def main(argumentos: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ordenes = parser.add_subparsers(dest="orden", required=True)
    orden_elegir = ordenes.add_parser("elegir")
    orden_elegir.add_argument("listado")
    orden_elegir.add_argument("--tanda", type=int, default=15)
    orden_fechas = ordenes.add_parser("fechas")
    orden_fechas.add_argument("trabajo")
    orden_fechas.add_argument("listado")
    try:
        args = parser.parse_args(argumentos)
    except SystemExit:
        return 2

    listado = json.loads(Path(args.listado).read_text(encoding="utf-8"))
    if args.orden == "fechas":
        print(json.dumps(fijar_fechas(Path(args.trabajo), listado), ensure_ascii=False))
        return 0
    resultado = elegir(listado, args.tanda)
    print(json.dumps(resultado, ensure_ascii=False, indent=1))
    return 0 if resultado["tandas"] else 4


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main())
