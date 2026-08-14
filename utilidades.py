# utilidades.py — Helpers compartidos entre consola y web
# Single source of truth: info_tier, _volumen_por_ciudad, _fecha_fresca.
# Antes estaban definidos duplicados en menus.py. Ahora un solo lugar.

from constants import CITIES, COLORES_TIER


def info_tier(item_id):
    """(tier_str, color_rich) del item_id — misma lógica que menus.info_tier."""
    tier = item_id.split("_")[0][1:]  # "T4_FISH..." -> "4"
    color = COLORES_TIER.get(tier, "white")
    return tier, color


def _volumen_por_ciudad(hist):
    """{ciudad: volumen} del historial 7d crudo."""
    if not hist:
        return {}
    result = {}
    for entry in hist:
        city = entry.get("location")
        vol = sum(p.get("item_count", 0) for p in (entry.get("data") or []))
        if vol > 0:
            result[city] = vol
    return result


def _fecha_fresca(fechas, items, ciudad):
    """Timestamp ISO más reciente entre `items` para `ciudad`."""
    candidatos = []
    for item in items:
        candidatos.extend(fechas.get(item, {}).get(ciudad, []))
    return max(candidatos) if candidatos else None