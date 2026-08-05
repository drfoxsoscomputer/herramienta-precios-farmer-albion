# formatting.py
# ─── Funciones de formateo y color ────────────────────────────
# Funciones PURAS: todo lo que necesitan entra por parametros.
# No tocan la red, no leen config, no imprimen por si solas.

from datetime import datetime, timezone


def format_price(val):
    if val is None or val == 0:
        return "N/D"
    return f"{val:,}"


def antiguedad(iso, ahora=None):
    """Convierte un timestamp ISO 8601 a texto relativo en espanol.

    "2026-08-02T12:20:00" -> "hace 10 s" / "hace 5 min" / "hace 3 h" /
    "hace 2 d" (singular: "hace 1 min", "hace 1 h", "hace 1 d").
    Devuelve "" si el timestamp falta, es None o no se puede interpretar;
    la UI muestra un guion en esos casos. `ahora` es opcional y sirve
    para pruebas deterministicas; si no se pasa, usa la hora actual UTC.
    Los timestamps naive (como los de la API de Albion) se tratan como UTC.
    """
    if not iso:
        return ""
    if isinstance(iso, datetime):
        fecha = iso
    else:
        try:
            fecha = datetime.fromisoformat(str(iso))
        except (ValueError, TypeError):
            return ""
    if fecha.tzinfo is None:
        fecha = fecha.replace(tzinfo=timezone.utc)
    # Centinela de la API de Albion en ciudades sin ventas: "0001-01-01T00:00:00".
    # No es un dato real; devolvemos "" (la UI muestra el guion).
    if fecha.year < 2000:
        return ""
    ahora = ahora or datetime.now(timezone.utc)
    if ahora.tzinfo is None:
        ahora = ahora.replace(tzinfo=timezone.utc)
    seg = max(0, int((ahora - fecha).total_seconds()))
    if seg < 60:
        return f"hace {seg} s"
    if seg < 3600:
        return f"hace {seg // 60} min"
    if seg < 86400:
        return f"hace {seg // 3600} h"
    return f"hace {seg // 86400} d"


def _formatear_historial(hist_data, label, unidad="uds"):
    """Arma lineas de historial por ciudad para un item.

    hist_data: lista CRUDA de get_history_raw — entries con data[] de
    {timestamp, item_count, avg_price} por ciudad. De cada ciudad se muestra
    volumen total, promedio ponderado y el resumen (rango + cambio %) via
    resumen_ciudad. El Total queda alineado con el ancho dinamico del volumen.
    """
    if not hist_data:
        return []
    por_ciudad = {}
    for entry in hist_data:
        if not isinstance(entry, dict):
            continue
        city = entry.get("location")
        pts = [p for p in (entry.get("data") or []) if isinstance(p, dict)]
        vol = sum(p.get("item_count", 0) for p in pts)
        if vol == 0:
            continue
        por_ciudad[city] = (vol, resumen_ciudad(pts))
    if not por_ciudad:
        return []
    lines = [f"  [bold]{label}[/]:"]
    total_vol = sum(v for v, _ in por_ciudad.values())
    # Ancho dinamico de la columna de volumen: se adapta a la cifra mas larga
    # (incluido el Total) para que "uds" y el promedio queden alineados siempre.
    ancho_vol = max([len(f"{v:,}") for v, _ in por_ciudad.values()] + [len(f"{total_vol:,}")])
    for city in sorted(por_ciudad, key=lambda c: por_ciudad[c][0], reverse=True):
        vol, res = por_ciudad[city]
        extra = ""
        if res:
            signo = "+" if res["cambio_pct"] >= 0 else ""
            extra = (f" · rango {res['rango_min']:,}-{res['rango_max']:,}"
                     f" · {signo}{res['cambio_pct']:.1f}%")
        lines.append(f"    {city:15s} {vol:>{ancho_vol},} {unidad}  (promedio ${res['promedio']:,}{extra})")
    avg = round(sum(res["promedio"] * v for v, res in por_ciudad.values()) / total_vol)
    lines.append(f"    {'Total':15s} {total_vol:>{ancho_vol},} {unidad}  (promedio ${avg:,})")
    return lines


def resumen_ciudad(serie):
    """Resumen por ciudad de una serie de historial CRUDA.

    serie: data[] de un entry de get_history_raw, una lista de dicts
    {timestamp, item_count, avg_price} (orden cronologico de la API).

    Devuelve dict:
      promedio   -> media ponderada por item_count de avg_price
      rango_min  -> menor avg_price de la serie
      rango_max  -> mayor avg_price de la serie
      cambio_pct -> variacion % del ULTIMO precio (el mas reciente) contra
                    el promedio ponderado (precio actual vs promedio)

    None si no hay datos (serie vacia, None o sin puntos con item_count > 0).
    """
    if not serie:
        return None
    pts = [p for p in serie if isinstance(p, dict) and (p.get("item_count") or 0) > 0]
    if not pts:
        return None
    total = sum(p["item_count"] for p in pts)
    if total <= 0:
        return None
    try:
        pts = sorted(pts, key=lambda p: p.get("timestamp", ""))
    except TypeError:
        pass
    promedio = round(sum(p["avg_price"] * p["item_count"] for p in pts) / total)
    precios = [p["avg_price"] for p in pts]
    actual = pts[-1]["avg_price"]
    cambio_pct = (actual - promedio) / promedio * 100 if promedio else 0.0
    return {
        "promedio": promedio,
        "rango_min": min(precios),
        "rango_max": max(precios),
        "cambio_pct": cambio_pct,
    }


def color_precio(valor, mejor_valor, peor_valor):
    """Colorea el precio de un pez: verde el mejor, rojo el peor."""
    if valor == 0:
        return f"[dim]N/D[/]"
    if valor == mejor_valor:
        return f"[bold green]${format_price(valor)}[/]"
    if valor == peor_valor:
        return f"[red]${format_price(valor)}[/]"
    return f"${format_price(valor)}"


def color_item(val, todos):
    """Colorea el precio de un recurso segun su posicion: verde el mayor,
    rojo el menor (dato neutro, sin recomendar comprar/vender)."""
    if val == 0:
        return f"[dim]N/D[/]"
    if not todos:
        return f"${format_price(val)}"
    if val == max(todos):
        return f"[bold green]${format_price(val)}[/]"
    if val == min(todos):
        return f"[red]${format_price(val)}[/]"
    return f"${format_price(val)}"


def valores_positivos(precios):
    """Valores > 0 de un dict {ciudad: precio}."""
    return [v for v in precios.values() if v > 0]


def mejor_ciudad(precios, modo="max"):
    """Devuelve (ciudad, precio) del mejor valor de un dict {ciudad: precio}.

    modo="max" -> la ciudad que paga mas (para VENDER).
    modo="min" -> la ciudad mas barata (para COMPRAR).
    Si no hay datos positivos devuelve ("", 0).
    """
    vals = valores_positivos(precios)
    if not vals:
        return ("", 0)
    precio = max(vals) if modo == "max" else min(vals)
    ciudad = [c for c, v in precios.items() if v == precio][0]
    return (ciudad, precio)


def pct(parte, base):
    """Porcentaje de parte/base. 0 si base es 0 (evita division por cero)."""
    return (parte / base * 100) if base > 0 else 0


def color_signo(valor):
    """Color segun el signo: 'green' si > 0, 'red' si < 0, 'yellow' si es 0."""
    if valor > 0:
        return "green"
    if valor < 0:
        return "red"
    return "yellow"


# ─── Resumen de mercado (Fase B) ───────────────────────────────

def market_summary(precios, item, recetas_config=None, volumen=None):
    """Resumen informativo de mercado (FUNCION PURA: sin red, sin imprimir).

    Devuelve datos objetivos para que la UI formatee (NO recomienda acciones):
      min_venta / max_venta   -> precio de venta minimo/maximo del item
                                 entre las ciudades con datos
      min_ciudad / max_ciudad -> ciudad donde se da cada extremo ("" si
                                 no hay datos). Si varias ciudades empatan en
                                 el extremo, gana la de MAYOR volumen de venta
                                 (desempate por movimiento real).
      es_ingrediente / recetas-> si el item es ingrediente de alguna salsa
      sin_datos               -> True si no hay precio de venta

    precios: {item_id: {ciudad: sell_price_min}} (lo que ya arma la UI).
    item: item id en vista (str).
    recetas_config: dict de insumos_pesca.items (nombre -> {id, receta}).
    volumen: {ciudad: volumen} del historial 7d (desempate). Opcional.
    """
    # ── Precios del item en vista ──
    p_item = precios.get(item, {}) if isinstance(precios, dict) else {}
    vals = [v for v in p_item.values() if v > 0]
    min_venta = min(vals) if vals else 0
    max_venta = max(vals) if vals else 0

    def _desempate(ciudades):
        """De una lista de ciudades con el MISMO precio, devuelve la de mayor
        volumen (movimiento real). Perden las que no tienen dato de volumen."""
        if not ciudades:
            return ""
        if len(ciudades) == 1:
            return ciudades[0]
        vol = volumen or {}
        return max(ciudades, key=lambda c: (
            vol.get(c, 0) if isinstance(vol.get(c), (int, float)) else 0, c))

    min_ciudad = _desempate([c for c, v in p_item.items() if v == min_venta]) if vals else ""
    max_ciudad = _desempate([c for c, v in p_item.items() if v == max_venta]) if vals else ""

    # ── Ingrediente: el item aparece como clave en alguna receta ──
    es_ingrediente = False
    recetas = []
    if recetas_config:
        for nombre, data in recetas_config.items():
            if isinstance(data, dict):
                receta = data.get("receta")
                if isinstance(receta, dict) and item in receta:
                    es_ingrediente = True
                    recetas.append(nombre)

    sin_datos = (max_venta == 0)

    return {
        "min_venta": min_venta,
        "max_venta": max_venta,
        "min_ciudad": min_ciudad,
        "max_ciudad": max_ciudad,
        "es_ingrediente": es_ingrediente,
        "recetas": recetas,
        "sin_datos": sin_datos,
    }
