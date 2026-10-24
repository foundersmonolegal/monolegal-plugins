"""Sustituye los datos personales por claves antes de que ningún texto salga del equipo.

Reemplaza por claves como [CLIENTE], [PERSONA_1], [DNI_1], [TEL_1], [EMAIL_1],
[IBAN_1] o [DIRECCION_1]:
- las personas conocidas (cliente, partes de las cabeceras, participantes de WhatsApp)
  y sus nombres y apellidos sueltos cuando van en mayúscula;
- las personas tras un tratamiento (D., Dña., Don, Doña, Sr., Sra.);
- los datos con formato fijo: DNI/NIE, teléfonos, correos, IBAN y direcciones.
Las empresas y organismos no son datos personales y se dejan.

La tabla clave → valor se guarda en .monolegal/datos_personales.json y no sale del equipo.
Es una medida de mínimos: un nombre que no aparece en ninguno de esos sitios puede escaparse.
"""
from __future__ import annotations

import re
import unicodedata
from collections import Counter

VARIANTES = {"a": "aáàäâ", "e": "eéèëê", "i": "iíìïî", "o": "oóòöô", "u": "uúùüû", "n": "nñ", "c": "cç"}
CONECTORES = {"de", "del", "la", "las", "los", "y", "i", "e"}
NO_NOMBRE = {"juzgado", "tribunal", "seccion", "plaza", "procurador", "procuradora", "letrado", "letrada", "abogado", "abogada",
             "demandante", "demandado", "demandada", "parte", "actora", "juez", "jueza", "magistrado", "magistrada", "fiscal",
             "secretario", "secretaria", "administracion", "justicia", "presidente", "presidenta", "ponente", "perito", "perita",
             "notario", "notaria", "registrador", "registradora", "cliente", "senor", "senora", "don", "dona"}
EMPRESA = re.compile(
    r"(?:\b(?:S\.?\s?L\.?(?:U|P|L)?|S\.?\s?A\.?U?|S\.?\s?C\.?V?|C\.?\s?B\.?|S\.?\s?COOP\.?)\.?\s*$)"
    r"|\b(?:AYUNTAMIENTO|AJUNTAMENT|CONSELLER[IÍ]A|GENERALITAT|MINISTERIO|TESORER[IÍ]A|INSTITUTO|INSTITUT|BANCO|CAIXA|CAJA|"
    r"FOGASA|ASOCIACI[OÓ]N|FUNDACI[OÓ]N|COMUNIDAD DE PROPIETARIOS|MINISTERIO FISCAL|ABOGAC[IÍ]A DEL ESTADO|SEGURIDAD SOCIAL|"
    r"MUTUA|ASEGURADORA|SEGUROS|DIPUTACI[OÓ]N|UNIVERSIDAD|SINDICATO)\b",
    re.IGNORECASE,
)
PALABRA_MAYUSCULA = r"(?:[A-ZÁÉÍÓÚÀÈÒÑÇ][a-záéíóúàèòñçü'·-]+|[A-ZÁÉÍÓÚÀÈÒÑÇ]{2,})"
TRATAMIENTO = re.compile(
    r"\b(?:D\.ª|Dña\.|Dña|D\.|Don|Doña|Sr\.|Sra\.|Srta\.)\s+"
    rf"({PALABRA_MAYUSCULA}(?:\s+(?:de\s+|del\s+|de\s+la\s+|i\s+|y\s+)?{PALABRA_MAYUSCULA}){{0,3}})"
)
TELEFONO_SOLO = re.compile(r"^(?:(?:\+|00)\d{2}[\s.-]?)?\d(?:[\s.-]?\d){7,12}$")
PATRONES = [
    ("EMAIL", re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")),
    ("IBAN", re.compile(r"\bES\d{2}(?:[\s-]?\d{4}){5}\b", re.IGNORECASE)),
    ("DNI", re.compile(r"(?<![A-Za-z0-9])(?:\d{8}|[XYZxyz][-\s]?\d{7})[-\s]?[A-HJ-NP-TV-Za-hj-np-tv-z](?![A-Za-z0-9])")),
    ("TEL", re.compile(r"(?<![\d])(?:(?:\+|00)34[\s.-]?)?[6789](?:[\s.-]?\d){8}(?![\d])")),
    ("DIRECCION", re.compile(
        r"\b(?:C/|Calle|Avda\.?|Avenida|Av\.|Plaza|Pza\.|Paseo|Camino|Carrer|Ronda|Partida|Traves[ií]a)\s+"
        r"(?!(?:n\.?[º°o]|n[úu]m|n[úu]mero)\b)[A-Za-zÁÉÍÓÚÀÈÒÑÇáéíóúàèòñç'·.\s]{2,50}?,?\s*(?:n[º°o]\.?\s*)?\d{1,4}\b",
        re.IGNORECASE)),
]


def normalizar(texto: str) -> str:
    sin_tildes = "".join(c for c in unicodedata.normalize("NFKD", texto) if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", re.sub(r"[^\w\s]", " ", sin_tildes)).strip().lower()


def _clase(caracter: str, mayuscula: bool | None) -> str:
    """Clase de caracteres con las variantes con tilde; mayuscula=None admite ambas."""
    if caracter not in VARIANTES:
        letra = re.escape(caracter)
        if mayuscula is None:
            return f"[{letra}{re.escape(caracter.upper())}]" if caracter.isalpha() else letra
        return re.escape(caracter.upper()) if mayuscula else letra
    variantes = VARIANTES[caracter]
    if mayuscula is None:
        return "[" + variantes + variantes.upper() + "]"
    return "[" + (variantes.upper() if mayuscula else variantes) + "]"


def patron_nombre_completo(valor: str) -> re.Pattern:
    """El nombre entero, sin distinguir mayúsculas ni tildes y con espacios variables."""
    partes = [r"[\s.,]+" if c == " " else _clase(c, None) for c in normalizar(valor)]
    return re.compile(r"(?<!\w)" + "".join(partes) + r"(?!\w)")


def patron_palabra_nombre(palabra: str) -> re.Pattern:
    """Un nombre o apellido suelto solo si va en mayúscula inicial o todo en mayúsculas ("Prueba", "PRUEBA", no "prueba")."""
    base = normalizar(palabra)
    capitalizada = _clase(base[0], True) + "".join(_clase(c, False) for c in base[1:])
    mayusculas = "".join(_clase(c, True) for c in base)
    return re.compile(r"(?<!\w)(?:" + capitalizada + "|" + mayusculas + r")(?!\w)")


def es_empresa(nombre: str) -> bool:
    return bool(EMPRESA.search(nombre))


class Anonimizador:
    def __init__(self, cliente: str | None = None):
        self.datos: dict[str, str] = {}          # clave -> valor original
        self._por_valor: dict[str, str] = {}     # valor normalizado -> clave
        self._contador: Counter = Counter()
        self._personas: list[tuple[re.Pattern, str]] = []
        self._sueltos: list[tuple[re.Pattern, str]] = []
        if cliente:
            self.registrar_persona(cliente, "CLIENTE")

    def _clave(self, tipo: str, valor: str, fija: str | None = None) -> str:
        normalizado = normalizar(valor) if tipo == "PERSONA" else re.sub(r"[\s.-]", "", valor.lower())
        if normalizado in self._por_valor:
            return self._por_valor[normalizado]
        if fija:
            clave = f"[{fija}]"
        else:
            self._contador[tipo] += 1
            clave = f"[{tipo}_{self._contador[tipo]}]"
        self._por_valor[normalizado] = clave
        self.datos.setdefault(clave, valor.strip())  # una clave fija (CLIENTE) conserva su primer valor
        return clave

    def registrar_persona(self, nombre: str, fija: str | None = None) -> str | None:
        """Registra una persona física y devuelve su clave; None si es una empresa o no parece un nombre."""
        nombre = re.sub(r"\s+", " ", nombre).strip(" .,:;")
        if TELEFONO_SOLO.match(nombre):
            return self._clave("TEL", nombre)
        significativas = [p for p in normalizar(nombre).split() if p not in CONECTORES and len(p) > 1]
        if (not significativas or es_empresa(nombre) or significativas[0] in NO_NOMBRE
                or all(p in NO_NOMBRE for p in significativas) or any(c.isdigit() for c in nombre)):
            return None
        nueva = normalizar(nombre) not in self._por_valor
        clave = self._clave("PERSONA", nombre, fija)
        if nueva:
            self._personas.append((patron_nombre_completo(nombre), clave))
            self._personas.sort(key=lambda par: -len(par[0].pattern))
            self._sueltos += [(patron_palabra_nombre(p), clave) for p in significativas if len(p) >= 4 and p not in NO_NOMBRE]
        return clave

    def _sustituir_personas(self, texto: str) -> str:
        for patron, clave in self._personas:
            texto = patron.sub(clave, texto)
        return texto

    def _clave_tras_tratamiento(self, nombre: str) -> str:
        """'Sra. López': si es un nombre o apellido suelto ya conocido, conserva la clave de esa persona."""
        conocida = next((clave for patron, clave in self._sueltos if patron.fullmatch(nombre)), None)
        return conocida or self.registrar_persona(nombre) or nombre

    def anonimizar(self, texto: str) -> str:
        if not texto:
            return texto
        for tipo, patron in PATRONES:
            texto = patron.sub(lambda m, t=tipo: self._clave(t, m.group(0)), texto)
        texto = self._sustituir_personas(texto)
        texto = TRATAMIENTO.sub(lambda m: m.group(0).replace(m.group(1), self._clave_tras_tratamiento(m.group(1))), texto)
        texto = self._sustituir_personas(texto)
        for patron, clave in self._sueltos:
            texto = patron.sub(clave, texto)
        return texto

    def anonimizar_estructura(self, valor, excluir: frozenset = frozenset()):
        """Aplica anonimizar() a todos los textos de un dict o lista, salvo a las claves excluidas."""
        if isinstance(valor, str):
            return self.anonimizar(valor)
        if isinstance(valor, list):
            return [self.anonimizar_estructura(v, excluir) for v in valor]
        if isinstance(valor, dict):
            return {k: (v if k in excluir else self.anonimizar_estructura(v, excluir)) for k, v in valor.items()}
        return valor
