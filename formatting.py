# formatting.py
# ─── Funciones de formateo y color ────────────────────────────
# Funciones PURAS: todo lo que necesitan entra por parametros.
# No tocan la red, no leen config, no imprimen por si solas.

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
