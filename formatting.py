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
    # Ancho dinamico de la columna de volumen: se adapta a la cifra mas larga
    # (incluido el Total) para que "uds" y el promedio queden alineados siempre.
    ancho_vol = max([len(f"{d['volumen']:,}") for d in hist_data.values()] + [len(f"{total_vol:,}")])
    for city in sorted(hist_data, key=lambda c: hist_data[c]["volumen"], reverse=True):
        d = hist_data[city]
        lines.append(f"    {city:15s} {d['volumen']:>{ancho_vol},} {unidad}  (promedio ${d['avg_price']:,})")
    avg = round(sum(h["avg_price"] * h["volumen"] for h in hist_data.values()) / total_vol)
    lines.append(f"    {'Total':15s} {total_vol:>{ancho_vol},} {unidad}  (promedio ${avg:,})")
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
