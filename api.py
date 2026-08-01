# api.py
# ─── Acceso a la API de Albion ────────────────────────────────
# Todo lo que toca la red vive aqui. El resto del programa
# llama a get_prices() / get_history() sin saber como se descarga.

import json
import ssl
import time
import urllib.request
import urllib.error

from constants import CITIES, API_BASE, HISTORY_BASE

from rich.console import Console

console = Console()

# ─── Cache en memoria (TTL 60s) ────────────────────────────────
# La API de Albion limita a 180 req/min. Cada detalle hace 3 llamadas
# en rafaga (precios + 2 historiales); cacheando la URL, navegar de
# nuevo al mismo pez no vuelve a golpear la red.
CACHE_TTL = 60
_cache = {}  # url -> (timestamp, data)


def _cache_get(url):
    item = _cache.get(url)
    if item and time.time() - item[0] < CACHE_TTL:
        return item[1]
    return None


def _cache_put(url, data):
    _cache[url] = (time.time(), data)


def _fetch_json(url, timeout):
    """Descarga JSON de una URL con cache + reintentos. Devuelve datos o None."""
    cached = _cache_get(url)
    if cached is not None:
        return cached

    for intento in range(3):
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            context = ssl._create_unverified_context()
            with urllib.request.urlopen(req, timeout=timeout, context=context) as r:
                data = json.loads(r.read().decode())
                _cache_put(url, data)
                return data
        except urllib.error.HTTPError as e:
            # 429 = rate limit de la API Albion (180 req/min):
            # esperamos (2s, 4s) y reintentamos, hasta 3 intentos totales.
            if e.code == 429 and intento < 2:
                time.sleep(2 * (intento + 1))
                continue
            console.print(f"\n[red][!] Error de red: {e.code} {e.reason}[/]")
            return None
        except urllib.error.URLError as e:
            console.print(f"\n[red][!] Error de red: {e.reason}[/]")
            console.print("[red][!] Verifica tu conexion o la API de Albion.[/]\n")
            return None
        except Exception as e:
            console.print(f"\n[red][!] Error inesperado: {e}[/]\n")
            return None
    return None


def get_prices(item_ids):
    """Precios actuales de venta por item. Devuelve lista de dicts."""
    items_str = ",".join(item_ids)
    url = API_BASE.format(items=items_str)
    data = _fetch_json(url, timeout=10)
    return data if data is not None else []


def get_history(item_ids):
    """Historial 7d de precios y volumen. Acepta un item_id o lista."""
    if isinstance(item_ids, str):
        item_ids = [item_ids]
    items_str = ",".join(item_ids)
    url = HISTORY_BASE.format(item=items_str)
    data = _fetch_json(url, timeout=15)
    if data is None:
        return {}

    if len(item_ids) == 1:
        # Modo original: dict {ciudad: {volumen, avg_price}}
        result = {}
        for entry in data:
            city = entry["location"]
            if city not in CITIES:
                continue
            total_vol = sum(h["item_count"] for h in entry["data"])
            if total_vol == 0:
                continue
            weighted_sum = sum(h["avg_price"] * h["item_count"] for h in entry["data"])
            avg_price = round(weighted_sum / total_vol)
            result[city] = {"volumen": total_vol, "avg_price": avg_price}
        return result
    else:
        # Modo multiple: dict {item_id: {ciudad: {volumen, avg_price}}}
        result = {}
        for entry in data:
            iid = entry.get("item_id", "")
            city = entry["location"]
            if city not in CITIES:
                continue
            total_vol = sum(h["item_count"] for h in entry["data"])
            if total_vol == 0:
                continue
            weighted_sum = sum(h["avg_price"] * h["item_count"] for h in entry["data"])
            avg_price = round(weighted_sum / total_vol)
            result.setdefault(iid, {})[city] = {"volumen": total_vol, "avg_price": avg_price}
        return result


def get_history_raw(item_id, servidor="west"):
    """Historial 7d CRUDO: entries con data[] de {timestamp, item_count, avg_price}.

    A diferencia de get_history (que agrega por ciudad y DESCARTA los
    timestamps), esto devuelve la lista cruda de la API, solo de las
    ciudades configuradas y sin sumar: market_summary necesita el detalle
    timestamp a timestamp para agrupar por dia de la semana.

    El parametro `servidor` queda aceptado para la fase de seleccion de
    servidor; hoy la URL base es fija (HISTORY_BASE, subdominio west).
    """
    if isinstance(item_id, str):
        item_id = [item_id]
    items_str = ",".join(item_id)
    url = HISTORY_BASE.format(item=items_str)
    data = _fetch_json(url, timeout=15)
    if data is None:
        return []
    # Mismo universo que get_history: solo ciudades configuradas.
    return [e for e in data if e.get("location") in CITIES]
