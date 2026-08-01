# formatting.py
# ─── Funciones de formateo y color ────────────────────────────
# Funciones PURAS: todo lo que necesitan entra por parametros.
# No tocan la red, no leen config, no imprimen por si solas.

from datetime import datetime

# Nombre de dia (strftime %A) -> espanol (sin acentos, convencion del proyecto)
DIAS_ESP = {
    "Monday": "lunes", "Tuesday": "martes", "Wednesday": "miercoles",
    "Thursday": "jueves", "Friday": "viernes", "Saturday": "sabado",
    "Sunday": "domingo",
}

# Sufijos de item_id que identifican un producto REFINADO de recurso.
# Con esto market_summary detecta el par crudo/refinado del mismo tier.
_SUFIJOS_REFINADO = frozenset({"CLOTH", "PLANKS", "LEATHER", "METALBAR", "STONEBLOCK"})

def format_price(val):
    if val is None or val == 0:
        return "N/D"
    return f"{val:,}"


def _formatear_historial(hist_data, label, unidad="uds"):
    """Arma lineas de historial por ciudad para un item."""
    if not hist_data:
        return []
    lines = [f"  [bold]{label}[/]:"]
    total_vol = sum(h["volumen"] for h in hist_data.values())
    for city in sorted(hist_data, key=lambda c: hist_data[c]["volumen"], reverse=True):
        d = hist_data[city]
        lines.append(f"    {city:15s} {d['volumen']:>8,} {unidad}  (promedio ${d['avg_price']:,})")
    avg = round(sum(h["avg_price"] * h["volumen"] for h in hist_data.values()) / total_vol)
    lines.append(f"    {'Total':15s} {total_vol:>8,} {unidad}  (promedio ${avg:,})")
    return lines


def color_precio(valor, mejor_valor, peor_valor):
    """Colorea el precio de un pez: verde el mejor, rojo el peor."""
    if valor == 0:
        return f"[dim]N/D[/]"
    if valor == mejor_valor:
        return f"[bold green]${format_price(valor)}[/]"
    if valor == peor_valor:
        return f"[red]${format_price(valor)}[/]"
    return f"${format_price(valor)}"


def color_item(val, todos, es_bajo):
    """Colorea el precio de un recurso segun su posicion en la lista.

    es_bajo=True  -> tiers bajos (T2/T3): barato es bueno (verde).
    es_bajo=False -> tiers altos (T4+): caro es bueno (verde).
    """
    if val == 0:
        return f"[dim]N/D[/]"
    if not todos:
        return f"${format_price(val)}"
    if es_bajo:
        if val == min(todos):
            return f"[bold green]${format_price(val)}[/]"
        if val == max(todos):
            return f"[red]${format_price(val)}[/]"
    else:
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

def _diferencia_refinado(precios):
    """Precio refinado - crudo como dato (None si no hay par claro).

    Busca en precios dos items BASE (sin encantamientos .1-.4) del mismo
    tier donde uno es refinado (sufijo en _SUFIJOS_REFINADO) y el otro no.
    Devuelve (mejor precio refinado) - (mejor precio crudo), o None.
    """
    base = {}
    for iid, ciudades in (precios or {}).items():
        if "_LEVEL" in iid or "@" in iid:
            continue  # encantamientos no cuentan como par
        base.setdefault(iid.split("_", 1)[0], []).append(iid)
    for tier, ids in base.items():
        if len(ids) != 2:
            continue
        crudo = [i for i in ids if i.rsplit("_", 1)[-1] not in _SUFIJOS_REFINADO]
        refinado = [i for i in ids if i.rsplit("_", 1)[-1] in _SUFIJOS_REFINADO]
        if len(crudo) == 1 and len(refinado) == 1:
            best_c = max((v for v in precios[crudo[0]].values() if v > 0), default=0)
            best_r = max((v for v in precios[refinado[0]].values() if v > 0), default=0)
            if best_c > 0 and best_r > 0:
                return best_r - best_c
    return None


def market_summary(precios, historial, item, recetas_config=None):
    """Resumen informativo de mercado (FUNCION PURA: sin red, sin imprimir).

    Devuelve datos objetivos para que la UI formatee (NO recomienda acciones):
      min_venta / max_venta   -> precio de venta minimo/maximo del item
                                 entre las ciudades con datos
      volumen_total           -> suma de item_count del historial
      dia_mayor_venta         -> dia de la semana con mas ventas (espanol)
      volumen_dia             -> item_count sumado ese dia
      es_ingrediente / recetas-> si el item es ingrediente de alguna salsa
      diferencia_refinado     -> precio refinado - crudo (solo recursos)
      sin_datos               -> True si no hay precio ni volumen

    precios: {item_id: {ciudad: sell_price_min}} (lo que ya arma la UI).
    historial: entries crudos de get_history_raw (data[] con timestamp).
    item: item_id en vista (str).
    recetas_config: dict de insumos_pesca.items (nombre -> {id, receta}).
    """
    # ── Precios del item en vista ──
    p_item = precios.get(item, {}) if isinstance(precios, dict) else {}
    vals = [v for v in p_item.values() if v > 0]
    min_venta = min(vals) if vals else 0
    max_venta = max(vals) if vals else 0

    # ── Historial: volumen total + dia de mayor venta ──
    volumen_total = 0
    por_dia = {}
    for entry in historial or []:
        for h in entry.get("data", []) or []:
            cnt = h.get("item_count", 0) or 0
            volumen_total += cnt
            ts = h.get("timestamp")
            if not ts or cnt <= 0:
                continue
            try:
                dia = datetime.fromisoformat(ts).strftime("%A")
            except ValueError:
                continue
            dia_esp = DIAS_ESP.get(dia, dia)
            por_dia[dia_esp] = por_dia.get(dia_esp, 0) + cnt
    if por_dia:
        dia_mayor_venta = max(por_dia, key=por_dia.get)
        volumen_dia = por_dia[dia_mayor_venta]
    else:
        dia_mayor_venta = ""
        volumen_dia = 0

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

    # ── Diferencia refinado - crudo (solo si precios trae el par) ──
    diferencia_refinado = _diferencia_refinado(precios)

    sin_datos = (max_venta == 0 and volumen_total == 0)

    return {
        "min_venta": min_venta,
        "max_venta": max_venta,
        "volumen_total": volumen_total,
        "dia_mayor_venta": dia_mayor_venta,
        "volumen_dia": volumen_dia,
        "es_ingrediente": es_ingrediente,
        "recetas": recetas,
        "diferencia_refinado": diferencia_refinado,
        "sin_datos": sin_datos,
    }
