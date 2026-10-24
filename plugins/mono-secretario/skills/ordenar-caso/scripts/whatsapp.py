"""Lee exportaciones de chats de WhatsApp (Android e iPhone, .txt o .zip).

Formatos reconocidos (fecha día/mes/año, como en España):
    Android: 18/10/26, 14:05 - María López: mensaje
    iPhone:  [18/10/26, 14:05:12] María López: mensaje
Las líneas sin fecha continúan el mensaje anterior; las líneas de sistema (cifrado,
cambios de grupo) se ignoran.
"""
from __future__ import annotations

import datetime as dt
import re
import zipfile
from pathlib import Path

INICIO = r"^[‎‏﻿]*\[?(?P<d>\d{1,2})/(?P<m>\d{1,2})/(?P<a>\d{2,4}),?\s+(?P<h>\d{1,2}):(?P<min>\d{2})(?::\d{2})?(?:\s*(?P<ampm>[ap]\.?\s?m\.?))?\]?\s*(?:-\s*)?"
MENSAJE = re.compile(INICIO + r"(?P<autor>[^:\n]{1,60}):\s(?P<texto>.*)$", re.IGNORECASE)
SISTEMA = re.compile(INICIO, re.IGNORECASE)
NOMBRE_ARCHIVO = re.compile(r"(?:Chat de WhatsApp con|WhatsApp Chat with|WhatsApp Chat -|Chat de WhatsApp -)\s*(?P<nombre>.+?)(?:\.txt|\.zip)?$", re.IGNORECASE)
AUDIO = re.compile(r"audio omitido|audio omitted|-AUDIO-|PTT-\d|\.opus\b", re.IGNORECASE)
MULTIMEDIA = re.compile(r"omitid[oa]|omitted|archivo adjunto|<adjunto:|attached", re.IGNORECASE)


def _fecha(coincidencia: re.Match) -> dt.datetime | None:
    anio = int(coincidencia.group("a"))
    anio += 2000 if anio < 100 else 0
    hora = int(coincidencia.group("h"))
    ampm = (coincidencia.group("ampm") or "").lower().replace(".", "").replace(" ", "")
    if ampm == "pm" and hora < 12:
        hora += 12
    elif ampm == "am" and hora == 12:
        hora = 0
    try:
        return dt.datetime(anio, int(coincidencia.group("m")), int(coincidencia.group("d")), hora, int(coincidencia.group("min")))
    except ValueError:
        return None


def parece_exportacion(texto: str) -> bool:
    lineas = [l for l in texto.splitlines()[:30] if l.strip()]
    return sum(bool(MENSAJE.match(l)) for l in lineas) >= 2


def parsear(texto: str) -> list[dict]:
    mensajes: list[dict] = []
    for linea in texto.splitlines():
        coincidencia = MENSAJE.match(linea)
        if coincidencia and _fecha(coincidencia):
            mensajes.append({"fecha": _fecha(coincidencia), "autor": coincidencia.group("autor").strip(" ‎"), "texto": coincidencia.group("texto").strip("‎")})
        elif SISTEMA.match(linea) and _fecha(SISTEMA.match(linea)):
            continue
        elif mensajes and linea.strip():
            mensajes[-1]["texto"] += "\n" + linea
    return mensajes


def leer(ruta: Path) -> tuple[str, str] | None:
    """Devuelve (nombre del chat, texto) si el archivo es una exportación de WhatsApp."""
    if ruta.suffix.lower() == ".txt":
        texto = ruta.read_text(encoding="utf-8", errors="replace")
        return (_nombre_chat(ruta.name), texto) if parece_exportacion(texto) else None
    if ruta.suffix.lower() == ".zip":
        try:
            with zipfile.ZipFile(ruta) as zip_:
                candidatos = [n for n in zip_.namelist() if n.lower().endswith(".txt")]
                for nombre in sorted(candidatos, key=lambda n: (not n.endswith("_chat.txt"), len(n))):
                    texto = zip_.read(nombre).decode("utf-8", errors="replace")
                    if parece_exportacion(texto):
                        return _nombre_chat(ruta.name) or _nombre_chat(Path(nombre).name), texto
        except zipfile.BadZipFile:
            return None
    return None


def _nombre_chat(nombre_archivo: str) -> str | None:
    coincidencia = NOMBRE_ARCHIVO.search(nombre_archivo)
    return coincidencia.group("nombre").strip() if coincidencia else None


def analizar(ruta: Path, relativa: str, cliente: str | None, coincide, ultimos: int) -> dict | None:
    """Resume una exportación: participantes, quién es el cliente y los últimos mensajes.

    `coincide(cliente, nombre)` decide si un nombre de participante es el del cliente.
    """
    leido = leer(ruta)
    if not leido:
        return None
    nombre_chat, texto = leido
    mensajes = parsear(texto)
    if not mensajes:
        return None
    participantes = sorted({m["autor"] for m in mensajes})
    referencia = cliente or nombre_chat
    del_cliente = [p for p in participantes if referencia and (coincide(referencia, p) or (nombre_chat and coincide(nombre_chat, p)))]
    if not del_cliente and nombre_chat in participantes:
        del_cliente = [nombre_chat]

    def rol(autor: str) -> str:
        if autor in del_cliente:
            return "Cliente"
        return "Abogado" if len(participantes) <= 2 else "Otro"

    recientes = mensajes[-ultimos:]
    return {
        "ruta": relativa,
        "chat_con": nombre_chat,
        "participantes": [{"nombre": p, "rol": rol(p)} for p in participantes],
        "cliente_identificado": bool(del_cliente),
        "mensajes": len(mensajes),
        "desde": mensajes[0]["fecha"].date().isoformat(),
        "hasta": mensajes[-1]["fecha"].date().isoformat(),
        "audios": sum(bool(AUDIO.search(m["texto"])) for m in mensajes),
        "multimedia": sum(bool(MULTIMEDIA.search(m["texto"])) for m in mensajes),
        "ultimos": [{"fecha": m["fecha"].isoformat(timespec="minutes"), "autor": m["autor"], "rol": rol(m["autor"]), "texto": m["texto"]} for m in recientes],
    }
