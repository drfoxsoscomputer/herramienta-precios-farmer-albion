# catalogo.py
# ─── Buscador global: catalogo local de items de Albion ───────
# Descarga UNA vez el catalogo oficial de items (ao-data/ao-bin-dumps)
# a catalog.json (junto a la app) y busca por nombre ES-ES + UniqueName
# normalizados (minusculas + sin acentos). Si la descarga falla, avisa y
# devuelve vacio: nunca crashea.
#
# Funciones puras (normalizar, _indexar, buscar) testeadas en
# tests/test_catalogo.py con fixtures locales, sin red.

import json
import os
import ssl
import sys
import unicodedata
import urllib.request

from rich.console import Console

console = Console()

URL_ITEMS = "https://raw.githubusercontent.com/ao-data/ao-bin-dumps/master/formatted/items.json"
ARCHIVO_CATALOGO = "catalog.json"
MAX_RESULTADOS = 15

# Indice en memoria: se construye una sola vez por sesion (lazy).
_cat = None


def normalizar(texto):
    """Minusculas + sin acentos (NFD y sin marcas diacriticas).

    'Tiburón Árbol' -> 'tiburon arbol'. Funciona para tildes y ñ.
    None o vacio -> "" (la UI lo usa para no crashear con consulta nula).
    """
    if texto is None:
        return ""
    nfd = unicodedata.normalize("NFD", str(texto))
    sin_marcas = "".join(c for c in nfd if unicodedata.category(c) != "Mn")
    return sin_marcas.lower().strip()


def _limpiar_nombre(nombre):
    """Quita el sufijo ' (parcialmente lleno)' del final (diarios)."""
    sufijo = " (parcialmente lleno)"
    if nombre and nombre.lower().endswith(sufijo):
        return nombre[: -len(sufijo)]
    return nombre


def _ruta_catalogo():
    """catalog.json vive junto a la app (junto al exe en portable, junto a
    este archivo en desarrollo)."""
    if getattr(sys, "frozen", False):
        base = os.path.dirname(sys.executable)
    else:
        base = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base, ARCHIVO_CATALOGO)


def _aviso_descarga(error):
    console.print(f"\n[red][!] No se pudo descargar el catalogo de items: {error}[/]")
    console.print("[dim]La proxima vez que busques se reintenta solo.[/]\n")


def _descargar_catalogo():
    """Descarga items.json -> catalog.json si no existe. Ruta o None si falla."""
    ruta = _ruta_catalogo()
    if os.path.exists(ruta):
        return ruta
    console.print("[dim]Descargando catalogo de items (primera vez, ~23 MB)...[/]")
    try:
        req = urllib.request.Request(URL_ITEMS, headers={"User-Agent": "Mozilla/5.0"})
        context = ssl._create_unverified_context()
        with urllib.request.urlopen(req, timeout=120, context=context) as r:
            data = r.read()
        with open(ruta, "wb") as f:
            f.write(data)
        # Validar que sea JSON parseable antes de confiar en el archivo.
        with open(ruta, "r", encoding="utf-8") as f:
            json.load(f)
        return ruta
    except Exception as e:
        try:
            if os.path.exists(ruta):
                os.remove(ruta)
        except OSError:
            pass
        _aviso_descarga(e)
        return None


def _indexar(data):
    """Construye el indice de busqueda desde la lista cruda de items.json.

    Cada entry: {'UniqueName': 'T4_2H_BOW', 'LocalizedNames': {'ES-ES': ...}}.
    Agrupa en UN solo resultado (el base):
      - variantes de encantamiento @1..@4 (armas/armaduras/herramientas)
      - diarios: _EMPTY / _FULL se agrupan al journal base, que es lo que se
        lista; el detalle consulta {base}_EMPTY y {base}_FULL
    Detecta el tipo de cada item:
      - '_JOURNAL' en el id        -> 'diario' (se consulta _EMPTY/_FULL)
      - tiene variantes con @      -> 'arma' (se consulta base y @1..@4)
      - resto                      -> 'simple' (solo el base)
    Devuelve lista de dicts {nombre, id_base, tipo, busqueda}.
    """
    variantes = set()
    diarios = set()
    for entry in data:
        if not isinstance(entry, dict):
            continue
        un = entry.get("UniqueName", "")
        if "@" in un:
            variantes.add(un.split("@", 1)[0])
        elif "_JOURNAL" in un:
            base_d = un
            for suf in ("_EMPTY", "_FULL"):
                if un.endswith(suf):
                    base_d = un[: -len(suf)]
                    break
            diarios.add(base_d)

    items = {}
    for entry in data:
        if not isinstance(entry, dict):
            continue
        un = entry.get("UniqueName", "")
        if not un:
            continue
        base = un.split("@", 1)[0]
        if base in items:
            continue
        # Saltar las variantes _EMPTY/_FULL de los diarios: el journal base es
        # el unico que se lista; el detalle consulta {base}_EMPTY/{base}_FULL.
        if any(un.endswith(s) for s in ("_EMPTY", "_FULL")):
            base_d = un
            for suf in ("_EMPTY", "_FULL"):
                if un.endswith(suf):
                    base_d = un[: -len(suf)]
                    break
            if base_d in diarios:
                continue
        nombres = entry.get("LocalizedNames") or {}
        nombre = _limpiar_nombre(nombres.get("ES-ES") or nombres.get("EN-US") or un)
        if base in diarios:
            tipo = "diario"
        elif base in variantes:
            tipo = "arma"
        else:
            tipo = "simple"
        items[base] = {
            "nombre": nombre,
            "id_base": base,
            "tipo": tipo,
            "busqueda": f"{normalizar(nombre)} {normalizar(base)}",
        }
    return list(items.values())


def _cargar_catalogo():
    """Carga (y cachea) el indice completo. [] si no hay catalogo."""
    global _cat
    if _cat is not None:
        return _cat
    ruta = _descargar_catalogo()
    if not ruta:
        _cat = []
        return _cat
    try:
        with open(ruta, "r", encoding="utf-8") as f:
            data = json.load(f)
        _cat = _indexar(data)
    except Exception as e:
        _aviso_descarga(e)
        _cat = []
    return _cat


def buscar(consulta):
    """Busca items por tokens AND contra nombre ES-ES + UniqueName normalizados.

    Devuelve hasta MAX_RESULTADOS dicts {nombre, id_base, tipo}. Consulta
    vacia -> [] (la UI muestra el mensaje de ayuda). Sin catalogo -> [].
    """
    tokens = [t for t in normalizar(consulta).split() if t]
    if not tokens:
        return []
    resultados = []
    for item in _cargar_catalogo():
        if all(t in item["busqueda"] for t in tokens):
            resultados.append(item)
    return resultados[:MAX_RESULTADOS]
