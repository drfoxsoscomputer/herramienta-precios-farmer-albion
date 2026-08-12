# webui.py — Pantallas web (NiceGUI) de Albion Helper
# ─────────────────────────────────────────────────────────────
# Capa de presentacion web que REUTILIZA la logica de datos:
#   api.py        -> get_prices / get_history_raw (cache 60s interna)
#   formatting.py -> format_price, antiguedad, market_summary, resumen_ciudad
#   textos.py     -> TODO el copy en espanol
#   constants.py  -> CITIES, COLORES_TIER
#   colores_web   -> adaptador Rich -> CSS (nuevo)
#
# NO importa menus.py: las helpers pequenas que alli viven
# (_fecha_fresca, _volumen_por_ciudad, info_tier) se reimplementan
# aqui con la misma logica. El config se inyecta desde app.py con
# set_config() para evitar imports circulares.

from urllib.parse import quote

from nicegui import run, ui

from constants import CITIES, COLORES_TIER
from api import get_prices, get_history_raw
from formatting import antiguedad, format_price, market_summary, resumen_ciudad
from textos import (PARES_RECURSO, RESENAS_DETALLE, RESENAS_MENU,
                    RESENAS_OPCIONES_PRINCIPAL, RESUMEN)
import colores_web
import estilo

# ─── Tema visual (dorado Albion) ───────────────────────────────
# Se aplica a nivel de MODULO, no dentro de main(): NiceGUI 3.x no
# permite UI global en el script principal junto con @ui.page.
estilo.aplicar_tema()

# ─── Config inyectado por app.py ──────────────────────────────
_CONFIG = {}
_IP_LAN = ""
_PORT = 8080


def set_config(config, ip_lan="", port=8080):
    """Inyecta el config cargado por app.py y los datos de la LAN."""
    global _CONFIG, _IP_LAN, _PORT
    _CONFIG = config or {}
    _IP_LAN = ip_lan or ""
    _PORT = port


def get_config():
    """Getter del config (las paginas lo usan en tiempo de render)."""
    return _CONFIG


# ─── Helpers de datos (reimplementacion fiel de menus.py) ─────
def info_tier(item_id):
    """(tier_str, color_rich) del item_id — misma logica que menus.info_tier."""
    tier = item_id.split("_")[0][1:]  # "T4_FISH..." -> "4"
    color = COLORES_TIER.get(tier, "white")
    return tier, color


def _volumen_por_ciudad(hist):
    """{ciudad: volumen} del historial 7d crudo (menus._volumen_por_ciudad)."""
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
    """Timestamp ISO mas reciente entre `items` para `ciudad` (menus._fecha_fresca)."""
    candidatos = []
    for item in items:
        candidatos.extend(fechas.get(item, {}).get(ciudad, []))
    return max(candidatos) if candidatos else None


def _lineas_historial(hist_data, label, unidad="uds"):
    """Equivalente web de formatting._formatear_historial.

    Devuelve lista de strings PLANOS (sin markup Rich): volumen por
    ciudad con promedio, rango y cambio %, mas el Total alineado.
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
    lines = [f"{label}:"]
    total_vol = sum(v for v, _ in por_ciudad.values())
    for city in sorted(por_ciudad, key=lambda c: por_ciudad[c][0], reverse=True):
        vol, res = por_ciudad[city]
        extra = ""
        if res:
            signo = "+" if res["cambio_pct"] >= 0 else ""
            extra = (f" · rango {res['rango_min']:,}-{res['rango_max']:,}"
                     f" · {signo}{res['cambio_pct']:.1f}%")
        promedio = res["promedio"] if res else 0
        lines.append(f"  {city}: {vol:,} {unidad} (promedio ${promedio:,}{extra})")
    avg = round(sum(res["promedio"] * v for v, res in por_ciudad.values()) / total_vol) \
        if por_ciudad else 0
    lines.append(f"  Total: {total_vol:,} {unidad} (promedio ${avg:,})")
    return lines


def _datos_pez(nombre, item_id, trozos, tipo, config):
    """Replica EXACTA de la logica de datos de ver_detalle_pez (menus.py).

    Devuelve un dict con todo lo que la pagina necesita para renderizar:
      filas    -> [{ciudad, entero:(txt,color), fresca_entero,
                    picado:(txt,color), fresca_picado}]
      volumen  -> [(label, [lineas...])] por seccion con datos
      resumen  -> dict de market_summary
      uso      -> campo "uso" del config (plato/trofeo)
    """
    raw_data = get_prices([item_id, "T1_FISHCHOPS"])
    prices = {}
    fechas = {}  # item_id -> ciudad -> [timestamps min/max de la API]
    for entry in raw_data or []:
        # Solo precios de calidad normal (1): el helper compara el item base.
        if entry.get("quality", 1) != 1:
            continue
        item = entry["item_id"]
        city = entry["city"]
        prices.setdefault(item, {})[city] = entry.get("sell_price_min", 0)
        # Timestamps en paralelo para la columna "Actualizado". Solo cuando
        # la fila tiene precio real: la API manda "0001-01-01T00:00:00" como
        # centinela en ciudades sin ventas (fila N/D -> columna con guion).
        fechas.setdefault(item, {}).setdefault(city, [])
        if entry.get("sell_price_min", 0) > 0 and entry.get("sell_price_min_date"):
            fechas[item][city].append(entry["sell_price_min_date"])
        if entry.get("sell_price_max", 0) > 0 and entry.get("sell_price_max_date"):
            fechas[item][city].append(entry["sell_price_max_date"])

    fish_prices = prices.get(item_id, {})
    chops_prices = prices.get("T1_FISHCHOPS", {})

    # ─── Recopilar precios por ciudad ──────────────────────────
    precios = {}  # city -> (entero, picado)
    for city in CITIES:
        entero = fish_prices.get(city, 0)
        cho_price = chops_prices.get(city, 0)
        picado = cho_price * trozos if cho_price else 0
        precios[city] = (entero, picado)

    enteros = [precios[c][0] for c in CITIES if precios[c][0] > 0]
    picados = [precios[c][1] for c in CITIES if precios[c][1] > 0]
    max_entero = max(enteros) if enteros else 0
    min_entero = min(enteros) if enteros else 0
    max_picado = max(picados) if picados else 0
    min_picado = min(picados) if picados else 0

    filas = []
    for city in CITIES:
        e, p = precios[city]
        fresca_entero = antiguedad(_fecha_fresca(fechas, [item_id], city))
        fresca_picado = antiguedad(_fecha_fresca(fechas, ["T1_FISHCHOPS"], city))
        filas.append({
            "ciudad": city,
            "entero": colores_web.precio_web(e, max_entero, min_entero),
            "fresca_entero": fresca_entero or "—",
            "picado": colores_web.precio_web(p, max_picado, min_picado),
            "fresca_picado": fresca_picado or "—",
        })

    # ─── Historial 7d (si disponible) ───────────────────────────
    hist_entero = get_history_raw(item_id)
    hist_trozos = get_history_raw("T1_FISHCHOPS")

    vol_entero_total = sum(_volumen_por_ciudad(hist_entero).values())
    vol_trozos_total = sum(_volumen_por_ciudad(hist_trozos).values())

    volumen = []
    if vol_entero_total > 0 or vol_trozos_total > 0:
        if vol_entero_total > 0:
            volumen.append(("Entero", _lineas_historial(hist_entero, "Entero")))
        if vol_trozos_total > 0:
            volumen.append(("Picado", _lineas_historial(hist_trozos, "Picado", "trozos")))

    # ─── Resumen de mercado (informativo, sin recomendaciones) ──
    recetas_config = None
    if config:
        recetas_config = config.get("insumos_pesca", {}).get("items", {})
    resumen = market_summary(prices, item_id, recetas_config,
                             volumen=_volumen_por_ciudad(hist_entero))
    uso = ""
    if config:
        uso = config.get("pescados", {}).get(nombre, {}).get("uso", "")

    return {
        "filas": filas,
        "volumen": volumen,
        "resumen": resumen,
        "uso": uso,
    }


# ─── Barra superior persistente ───────────────────────────────
def _barra_superior():
    """Header fijo: logo dorado + Recargar (recarga la pagina actual) + Inicio."""
    ui.dark_mode().enable()
    with ui.header().classes("bg-primary text-white").style(
            "background: linear-gradient(90deg,#1a1a1e,#23232c);"
            "border-bottom:2px solid #c9a227;"):
        with ui.row().classes("items-center w-full px-4 py-2"):
            ui.icon("sports_esports").classes("text-2xl").style("color:#c9a227")
            ui.label("Albion Helper").classes("text-h6 font-bold").style("color:#e6c45c")
            ui.space()
            ui.button("Recargar", icon="refresh", on_click=ui.navigate.reload) \
                .props("flat dense color=white").style("color:#e6c45c")
            ui.button("Inicio", icon="home", on_click=lambda: ui.navigate.to("/")) \
                .props("flat dense color=white").style("color:#e6c45c")


def _marco():
    """Contenedor comun: columna centrada con ancho maximo legible."""
    return ui.column().classes("w-full max-w-3xl mx-auto px-4 py-4 gap-2")


# ─── Pagina de inicio: hero + grilla de secciones ───────────────
# Iconos por seccion (Material Icons, disponibles en Quasar).
_ICONOS_SECCION = {
    1: "water", 2: "eco", 3: "forest", 4: "checkroom",
    5: "diamond", 6: "terrain", 7: "set_meal", 8: "search",
}


@ui.page("/")
def pagina_inicio():
    _barra_superior()
    nombres = (["Pesca"]
               + [PARES_RECURSO[k] for k in ("fibra", "madera", "cuero", "mineral", "piedra")]
               + ["Salsas de pescado", "Buscar"])
    rutas = {1: "/pesca",
             2: "/recursos/fibra", 3: "/recursos/madera", 4: "/recursos/cuero",
             5: "/recursos/mineral", 6: "/recursos/piedra",
             7: "/salsas", 8: "/buscar"}
    with _marco():
        # Hero
        with ui.column().classes("items-center w-full gap-1 py-6"):
            ui.label("Albion Helper").classes("text-h3 font-bold").style("color:#e6c45c")
            ui.label(RESENAS_MENU["principal"]).classes("text-grey-5 text-center")
            if _IP_LAN:
                ui.badge(f"Celular: http://{_IP_LAN}:{_PORT}") \
                    .props("outline") \
                    .style("background:#1d1d24;color:#c9a227;border:1px solid #c9a227;"
                           "font-size:13px;padding:6px 12px;border-radius:20px")
        ui.separator()
        # Grilla responsive de tarjetas
        with ui.grid(columns=1).classes("w-full gap-4 sm:grid-cols-2 lg:grid-cols-4"):
            for i, nombre in enumerate(nombres, start=1):
                with ui.card().classes("alb-card w-full cursor-pointer") \
                        .on("click", lambda r=rutas[i]: ui.navigate.to(r)):
                    with ui.row().classes("items-center gap-3 no-wrap"):
                        ui.icon(_ICONOS_SECCION[i]).classes("text-4xl").style("color:#c9a227")
                        with ui.column().classes("gap-0 min-w-0"):
                            ui.label(nombre).classes("text-h6 font-bold")
                            ui.label(RESENAS_OPCIONES_PRINCIPAL[i]) \
                                .classes("text-body2 text-grey-6")


# ─── Pesca: listado de peces con color de tier ─────────────────
@ui.page("/pesca")
def pagina_pesca():
    _barra_superior()
    config = get_config()
    peces = []
    for nombre, info in (config.get("pescados") or {}).items():
        if nombre.startswith("_"):
            continue
        peces.append((nombre, info["id"], info["trozos"], info.get("tipo", "comun")))
    with _marco():
        ui.label("Pesca").classes("text-h4").style("color:#e6c45c")
        ui.label(RESENAS_MENU["pesca"]).classes("text-grey-6")
        ui.separator()
        for nombre, item_id, _trozos, _tipo in peces:
            tier, _color = info_tier(item_id)
            css = colores_web.tier_a_css(tier)
            with ui.card().classes("alb-card w-full cursor-pointer") \
                    .on("click", lambda n=nombre: ui.navigate.to(f"/pesca/{quote(n)}")):
                with ui.row().classes("items-center gap-3"):
                    ui.label("").classes("self-stretch") \
                        .style(f"width:4px;border-radius:4px;background:{css}")
                    ui.label(nombre).style(f"color: {css}; font-weight: 600; font-size:16px")
                    ui.space()
                    ui.badge(f"T{tier}").props("outline").style(
                        f"color:{css};border:1px solid {css};background:#1d1d24;"
                        f"font-size:12px;padding:2px 10px;border-radius:12px")


# ─── Detalle de pez: replica web de ver_detalle_pez ────────────
@ui.page("/pesca/{nombre}")
async def pagina_detalle_pez(nombre):
    _barra_superior()
    config = get_config()
    info = (config.get("pescados") or {}).get(nombre)
    if not info:
        with _marco():
            ui.label(f"Pez '{nombre}' no encontrado en el config.").classes("text-red")
        return
    item_id = info["id"]
    trozos = info["trozos"]
    tipo = info.get("tipo", "comun")

    tier, color = info_tier(item_id)
    css = colores_web.tier_a_css(tier)
    tipo_txt = "Raro" if tipo == "raro" else "Comun"

    with _marco():
        ui.button("← Volver a pesca", icon="arrow_back",
                  on_click=lambda: ui.navigate.to("/pesca")).props("flat dense")
        # Header: nombre con color de tier + tag + reseña (equiv. _panel_detalle)
        ui.label(nombre).classes("text-h4 font-bold").style(f"color: {css}")
        ui.label(f"T{tier} {tipo_txt} — {trozos} trozos al picar") \
            .classes("text-subtitle1 text-grey-4")
        ui.label(RESENAS_DETALLE["pez"]).classes("text-grey-6")
        ui.separator()

        # Carga con spinner: las llamadas de red pueden tardar varios segundos.
        with ui.column().classes("items-center gap-2 py-8"):
            ui.spinner(size="lg").style("color:#c9a227")
            ui.label("Consultando mercado...").classes("text-grey-6")
        await ui.context.client.connected()

        datos = await run.io_bound(_datos_pez, nombre, item_id, trozos, tipo, config)

        _render_tabla_precios(datos["filas"])
        if datos["volumen"]:
            _panel_volumen(datos["volumen"])
        _panel_resumen(datos["resumen"], uso=datos["uso"])


# ─── Placeholders Fase 2 ───────────────────────────────────────
@ui.page("/recursos/{tipo}")
def pagina_recurso(tipo):
    _barra_superior()
    config = get_config()
    info = (config.get("recursos") or {}).get(tipo)
    nombre = (info or {}).get("nombre", tipo.upper())
    par = PARES_RECURSO.get(tipo, nombre)
    _placeholder(par, RESENAS_MENU["recursos"])


@ui.page("/salsas")
def pagina_salsas():
    _barra_superior()
    _placeholder("Salsas de pescado", RESENAS_MENU["insumos"])


@ui.page("/buscar")
def pagina_buscar():
    _barra_superior()
    _placeholder("Buscar", RESENAS_MENU["buscar"])


def _placeholder(titulo, resena):
    """Pantalla de proxima fase: titulo + resena + aviso."""
    with _marco():
        ui.label(titulo).classes("text-h4").style("color:#e6c45c")
        ui.label("Proximamente (Fase 2)").classes("text-grey-6 text-h6")
        if resena:
            ui.label(resena).classes("text-grey-7")


# ─── Componentes de render ─────────────────────────────────────
def _render_tabla_precios(filas):
    """Tabla Ciudad | Entero | Actualizado | Picado | Actualizado.

    Los precios llevan color inline (verde mayor / rojo menor), el
    "Actualizado" relativo y "—" cuando la fila no tiene datos.
    """
    celdas = []
    for f in filas:
        texto_e, color_e = f["entero"]
        texto_p, color_p = f["picado"]
        style_e = f"color:{color_e};font-weight:600" if color_e else ""
        style_p = f"color:{color_p};font-weight:600" if color_p else ""
        celdas.append(
            f'<tr>'
            f'<td>{f["ciudad"]}</td>'
            f'<td class="num" style="{style_e}">{texto_e}</td>'
            f'<td class="num dim">{f["fresca_entero"]}</td>'
            f'<td class="num" style="{style_p}">{texto_p}</td>'
            f'<td class="num dim">{f["fresca_picado"]}</td>'
            f'</tr>')
    html = (
        '<table class="alb-table">'
        '<thead><tr>'
        '<th>Ciudad</th>'
        '<th class="num">Entero</th>'
        '<th class="num">Actualizado</th>'
        '<th class="num">Picado</th>'
        '<th class="num">Actualizado</th>'
        '</tr></thead><tbody>'
        + "".join(celdas) +
        '</tbody></table>'
    )
    ui.html(html).classes("w-full")


def _panel_volumen(secciones):
    """Panel 'Volumen 7 dias' (equiv. al Panel Rich de ver_detalle_pez)."""
    with ui.card().classes("alb-card-static w-full"):
        with ui.row().classes("items-center gap-2"):
            ui.icon("bar_chart").style("color:#c9a227")
            ui.label("Volumen 7 dias").classes("text-h6").style("color:#e6c45c")
        for _label, lineas in secciones:
            for linea in lineas:
                ui.label(linea).classes("font-mono text-body2")


def _panel_resumen(resumen, uso=""):
    """Panel 'Resumen de mercado' (equiv. a _panel_resumen de menus.py)."""
    with ui.card().classes("alb-card-static w-full"):
        with ui.row().classes("items-center gap-2"):
            ui.icon("insights").style("color:#c9a227")
            ui.label(RESUMEN["titulo"]).classes("text-h6").style("color:#e6c45c")
        if resumen.get("sin_datos"):
            ui.label(RESUMEN["sin_datos"]).classes("text-grey-6")
        else:
            min_txt = f" ({resumen['min_ciudad']})" if resumen.get("min_ciudad") else ""
            max_txt = f" ({resumen['max_ciudad']})" if resumen.get("max_ciudad") else ""
            ui.label(f"{RESUMEN['venta_min']}:  ${format_price(resumen['min_venta'])}{min_txt}") \
                .classes("text-bold").style("color:#2ecc71")
            ui.label(f"{RESUMEN['venta_max']}:  ${format_price(resumen['max_venta'])}{max_txt}") \
                .classes("text-bold").style("color:#e74c3c")
        if uso:
            ui.label(f"{RESUMEN['uso']}: {uso}").classes("text-body2")
