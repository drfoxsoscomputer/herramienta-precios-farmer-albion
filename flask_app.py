# flask_app.py — Web (Flask + HTMX + Tailwind) de Albion Helper
# ─────────────────────────────────────────────────────────────
# Web oficial del proyecto. Reutiliza la logica de datos:
#   api.py        -> get_prices / get_history_raw (cache 60s interna)
#   formatting.py -> format_price, antiguedad, market_summary, resumen_ciudad
#   utilidades.py -> info_tier, _volumen_por_ciudad, _fecha_fresca
#   colores_web   -> criterio verde/rojo y colores por tier en CSS
#   textos.py     -> TODO el copy en espanol
#
# Filosofia del proyecto: SOLO datos, sin recomendaciones de ganancia.
# La web usa el mismo universo de ciudades que la consola (CITIES).

import io
import json
import os
import re
import socket
import subprocess
import sys
import time
from urllib.parse import quote

from flask import Flask, abort, render_template, request, send_file

from api import get_prices, get_history_raw
from formatting import antiguedad, format_price, market_summary, resumen_ciudad
from utilidades import _fecha_fresca, _volumen_por_ciudad, info_tier
import colores_web
from constants import CITIES
from textos import (CALIDADES, PARES_RECURSO, RESENAS_DETALLE, RESENAS_MENU,
                    RESENAS_OPCIONES_PRINCIPAL)
import catalogo

# En PyInstaller (exe portable) los datos viven junto al exe; en desarrollo,
# junto a este archivo. sys.frozen True solo cuando corre empaquetado.
if getattr(sys, "frozen", False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

CONFIG_FILE = os.path.join(BASE_DIR, "albion_config.json")

CLOUDFLARED = os.path.join(BASE_DIR, "cloudflared.exe")
if not os.path.exists(CLOUDFLARED):
    # Fallback dev: build.py usa el cloudflared.exe de TEMP; en el exe
    # empaquetado siempre vive junto al ejecutable.
    _cf_temp = os.path.join(os.environ.get("TEMP", ""), "cloudflared.exe")
    if _cf_temp and os.path.exists(_cf_temp):
        CLOUDFLARED = _cf_temp
TUN_URL_FILE = os.path.join(BASE_DIR, "tun_url.txt")
TUN_LOG_FILE = os.path.join(BASE_DIR, "tun.log")

HOST = "0.0.0.0"
PORT = 8081

app = Flask(
    __name__,
    template_folder=os.path.join(BASE_DIR, "templates"),
    static_folder=os.path.join(BASE_DIR, "static"),
)


# ─── PWA ───────────────────────────────────────────────────────
@app.get("/manifest.json")
def pwa_manifest():
    return send_file(os.path.join(BASE_DIR, "static", "manifest.json"),
                     mimetype="application/manifest+json")


@app.get("/sw.js")
def pwa_sw():
    return send_file(os.path.join(BASE_DIR, "static", "sw.js"),
                     mimetype="application/javascript")


# ─── Config ────────────────────────────────────────────────────
def load_config():
    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def ip_lan():
    """IP local de la LAN: el celular entra a la web."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            s.connect(("8.8.8.8", 80))
            return s.getsockname()[0]
        finally:
            s.close()
    except OSError:
        return "127.0.0.1"


# ─── Helpers de datos (puros para Jinja) ────────────────
def _historial_tabla(hist_data, label, unidad="uds"):
    """Volumen 7d como tabla estructurada para Jinja.

    Devuelve dict: {label, filas: [{ciudad, volumen, promedio, rango_min,
    rango_max, cambio_pct}], total: {volumen, promedio}} o None sin datos.
    """
    if not hist_data:
        return None
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
        return None
    filas = []
    for city in sorted(por_ciudad, key=lambda c: por_ciudad[c][0], reverse=True):
        vol, res = por_ciudad[city]
        filas.append({
            "ciudad": city,
            "volumen": vol,
            "promedio": res["promedio"] if res else 0,
            "rango_min": res["rango_min"] if res else 0,
            "rango_max": res["rango_max"] if res else 0,
            "cambio_pct": res["cambio_pct"] if res else None,
        })
    total_vol = sum(f["volumen"] for f in filas)
    total_avg = round(sum(f["promedio"] * f["volumen"] for f in filas) / total_vol) \
        if total_vol else 0
    return {
        "label": label,
        "unidad": unidad,
        "filas": filas,
        "total": {"volumen": total_vol, "promedio": total_avg},
    }


def _datos_pez(nombre, item_id, trozos, tipo, config):
    """Datos de detalle de pez para la plantilla (misma logica que ver_detalle_pez)."""
    raw_data = get_prices([item_id, "T1_FISHCHOPS"])
    prices = {}
    fechas = {}
    for entry in raw_data or []:
        if entry.get("quality", 1) != 1:
            continue
        item = entry["item_id"]
        city = entry["city"]
        prices.setdefault(item, {})[city] = entry.get("sell_price_min", 0)
        fechas.setdefault(item, {}).setdefault(city, [])
        if entry.get("sell_price_min", 0) > 0 and entry.get("sell_price_min_date"):
            fechas[item][city].append(entry["sell_price_min_date"])
        if entry.get("sell_price_max", 0) > 0 and entry.get("sell_price_max_date"):
            fechas[item][city].append(entry["sell_price_max_date"])

    fish_prices = prices.get(item_id, {})
    chops_prices = prices.get("T1_FISHCHOPS", {})

    precios = {}
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
        texto_e, color_e = colores_web.precio_web(e, max_entero, min_entero)
        texto_p, color_p = colores_web.precio_web(p, max_picado, min_picado)
        filas.append({
            "ciudad": city,
            "entero_txt": texto_e, "entero_color": color_e,
            "fresca_entero": fresca_entero or "—",
            "picado_txt": texto_p, "picado_color": color_p,
            "fresca_picado": fresca_picado or "—",
        })

    hist_entero = get_history_raw(item_id)
    hist_trozos = get_history_raw("T1_FISHCHOPS")

    volumen = []
    tabla_entero = _historial_tabla(hist_entero, "Entero")
    tabla_trozos = _historial_tabla(hist_trozos, "Picado", "trozos")
    if tabla_entero:
        volumen.append(tabla_entero)
    if tabla_trozos:
        volumen.append(tabla_trozos)

    recetas_config = None
    if config:
        recetas_config = config.get("insumos_pesca", {}).get("items", {})
    resumen = market_summary(prices, item_id, recetas_config,
                             volumen=_volumen_por_ciudad(hist_entero))
    uso = ""
    if config:
        uso = config.get("pescados", {}).get(nombre, {}).get("uso", "")

    return {"filas": filas, "volumen": volumen, "resumen": resumen, "uso": uso}


def _datos_recurso(nombre, tier_key, tier_data, modo="todo"):
    """Misma logica de datos que _datos_recurso (ver_detalle_recurso de menus.py)."""
    crudo_id = tier_data["crudo"]
    refinado_id = tier_data["refinado"]
    nombre_real = tier_data.get("nombre", f"{nombre} {tier_key}")
    ref_label = refinado_id.split("_", 1)[1].title()
    ref_nombre = tier_data.get("refinado_nombre", ref_label)

    has_ench = int(tier_key[1:]) >= 4
    ench_ids = [f"{crudo_id}_LEVEL{i}@{i}" for i in range(1, 5)] if has_ench else []
    ref_ench_ids = [f"{refinado_id}_LEVEL{i}@{i}" for i in range(1, 5)] if has_ench else []

    if modo == "crudo":
        item_ids = [crudo_id] + ench_ids
    elif modo == "refinado":
        item_ids = [refinado_id] + ref_ench_ids
    else:
        item_ids = [crudo_id] + ench_ids + [refinado_id] + ref_ench_ids

    raw_data = get_prices(item_ids)
    prices_map = {}
    fechas = {}
    for entry in raw_data or []:
        if entry.get("quality", 1) != 1:
            continue
        iid = entry["item_id"]
        ciudad = entry["city"]
        prices_map.setdefault(iid, {})[ciudad] = entry.get("sell_price_min", 0)
        fechas.setdefault(iid, {}).setdefault(ciudad, [])
        if entry.get("sell_price_min", 0) > 0 and entry.get("sell_price_min_date"):
            fechas[iid][ciudad].append(entry["sell_price_min_date"])
        if entry.get("sell_price_max", 0) > 0 and entry.get("sell_price_max_date"):
            fechas[iid][ciudad].append(entry["sell_price_max_date"])

    mostrar_crudo = modo in ("crudo", "todo")
    mostrar_ref = modo in ("refinado", "todo")

    columnas_precio = []
    if mostrar_crudo:
        columnas_precio.append((crudo_id, nombre_real))
        if has_ench:
            for i in range(4):
                columnas_precio.append((ench_ids[i], f".{i + 1}"))
    if mostrar_ref:
        columnas_precio.append((refinado_id, ref_nombre))
        if has_ench:
            for i in range(4):
                columnas_precio.append((ref_ench_ids[i], f".{i + 1}"))

    vals_por_item = {}
    for iid, _ in columnas_precio:
        vals = [prices_map.get(iid, {}).get(c, 0) for c in CITIES
                if prices_map.get(iid, {}).get(c, 0) > 0]
        vals_por_item[iid] = vals

    headers = ["Ciudad"]
    for _, etiq in columnas_precio:
        headers.append(etiq)
        headers.append("Actualizado")

    filas = []
    for city in CITIES:
        celdas = []
        for iid, _ in columnas_precio:
            val = prices_map.get(iid, {}).get(city, 0)
            vals = vals_por_item[iid]
            txt, color = colores_web.precio_web(val, max(vals, default=0), min(vals, default=0))
            celdas.append({"txt": txt, "color": color, "es_fresca": False})
            fresca = antiguedad(_fecha_fresca(fechas, [iid], city)) or "—"
            celdas.append({"txt": fresca, "color": None, "es_fresca": True})
        filas.append({"ciudad": city, "celdas": celdas})

    volumen = []
    hist_crudo = None
    hist_ref = None
    if mostrar_crudo:
        hist_crudo = get_history_raw(crudo_id)
        tabla = _historial_tabla(hist_crudo, nombre_real)
        if tabla:
            volumen.append(tabla)
    if mostrar_ref:
        hist_ref = get_history_raw(refinado_id)
        tabla = _historial_tabla(hist_ref, ref_nombre)
        if tabla:
            volumen.append(tabla)

    if modo == "todo":
        res_crudo = market_summary(prices_map, crudo_id, volumen=_volumen_por_ciudad(hist_crudo))
        res_ref = market_summary(prices_map, refinado_id, volumen=_volumen_por_ciudad(hist_ref))
        resumen = {"modo": "todo", "crudo": (nombre_real, res_crudo),
                   "refinado": (ref_nombre, res_ref)}
    else:
        item_vista = refinado_id if modo == "refinado" else crudo_id
        hist_vista = hist_ref if modo == "refinado" else hist_crudo
        resumen = {"modo": "unico",
                   "resumen": market_summary(prices_map, item_vista,
                                             volumen=_volumen_por_ciudad(hist_vista))}

    return {"headers": headers, "filas": filas, "volumen": volumen, "resumen": resumen}


def _acortar_nombre(nombre):
    """Abrevia nombres para columnas: 'Carne de pescado' -> 'Carne', 'Algas' -> 'Alga'."""
    if nombre.startswith("Carne de"):
        return "Carne"
    if nombre.endswith("s") and len(nombre) > 3:
        return nombre[:-1]
    return nombre


def _calidades_con_datos(precios_item):
    """Calidades (1-5) con al menos un precio > 0 en el dict de precios."""
    return [cal for cal in range(1, 6)
            if any(v > 0 for v in (precios_item.get(cal) or {}).values())]


def _id_a_nombre(config):
    """Mapa: item_id -> nombre espanol desde pescados e insumos."""
    m = {}
    for seccion_key in ("pescados", "insumos_pesca"):
        seccion = config.get(seccion_key, {})
        if seccion_key == "insumos_pesca":
            seccion = seccion.get("items", {})
        for nom, data in seccion.items():
            if isinstance(data, dict) and "id" in data:
                m[data["id"]] = nom
    return m


def _datos_salsa(nombre, item_id, receta, config):
    """Misma logica de datos que ver_detalle_insumo (menus.py)."""
    fetch_ids = [item_id] + (list(receta.keys()) if receta else [])
    raw_data = get_prices(fetch_ids)

    precios_grp = {}
    fechas = {}
    for entry in raw_data or []:
        if entry.get("quality", 1) != 1:
            continue
        iid = entry["item_id"]
        ciudad = entry["city"]
        precios_grp.setdefault(iid, {})[ciudad] = entry.get("sell_price_min", 0)
        fechas.setdefault(iid, {}).setdefault(ciudad, [])
        if entry.get("sell_price_min", 0) > 0 and entry.get("sell_price_min_date"):
            fechas[iid][ciudad].append(entry["sell_price_min_date"])
        if entry.get("sell_price_max", 0) > 0 and entry.get("sell_price_max_date"):
            fechas[iid][ciudad].append(entry["sell_price_max_date"])

    id_to_nombre = _id_a_nombre(config)
    salsa_prices = precios_grp.get(item_id, {})

    # ─── Columnas: Ciudad | [ingredientes] | Venta | Actualizado ──
    cols_info = []  # [(titulo, dict_ciudad->precio)]
    items_fila = [item_id]
    if receta:
        for ing_id in sorted(receta.keys(), key=lambda i: id_to_nombre.get(i, i)):
            items_fila.append(ing_id)
            col_title = _acortar_nombre(id_to_nombre.get(ing_id, ing_id))
            cols_info.append((col_title, precios_grp.get(ing_id, {})))
    cols_info.append(("Venta", salsa_prices))

    headers = ["Ciudad"] + [t for t, _ in cols_info] + ["Actualizado"]

    filas = []
    for city in CITIES:
        celdas = []
        for _, data in cols_info:
            val = data.get(city, 0)
            col_vals = [v for v in data.values() if v > 0]
            if val == 0:
                txt, color = "N/D", None
            elif not col_vals:
                txt, color = f"${format_price(val)}", None
            else:
                txt, color = f"${format_price(val)}", None
                if val == max(col_vals):
                    color = colores_web.RICH_A_CSS.get("green", "#2ecc71")
                elif val == min(col_vals):
                    color = colores_web.RICH_A_CSS.get("red", "#e74c3c")
            celdas.append({"txt": txt, "color": color, "es_fresca": False})
        fresca = antiguedad(_fecha_fresca(fechas, items_fila, city)) or "—"
        celdas.append({"txt": fresca, "color": None, "es_fresca": True})
        filas.append({"ciudad": city, "celdas": celdas})

    # ─── Receta (dato neutro) ────────────────────────────────────
    receta_txt = ""
    if receta:
        receta_txt = " + ".join(
            f"{cantidad} x {id_to_nombre.get(ing_id, ing_id)}"
            for ing_id, cantidad in receta.items())

    # ─── Historial 7d + Resumen ──────────────────────────────────
    hist = get_history_raw(item_id)
    volumen = []
    tabla = _historial_tabla(hist, nombre)
    if tabla:
        volumen.append(tabla)

    recetas_config = config.get("insumos_pesca", {}).get("items", {})
    resumen = market_summary(precios_grp, item_id, recetas_config,
                             volumen=_volumen_por_ciudad(hist))

    return {"headers": headers, "filas": filas, "receta": receta_txt,
            "volumen": volumen, "resumen": resumen}


def _col_calidades(iid, precios):
    """Columnas (item_id, CALIDADES[cal-1], cal) para un item, con datos."""
    calidades = _calidades_con_datos(precios.get(iid, {})) or [1]
    return [(iid, CALIDADES[cal - 1], cal) for cal in calidades]


def _tabla_buscado(columnas, precios, fechas):
    """Tabla Ciudad | (calidad | Actualizado) — replica _tabla_calidades menus.py."""
    headers = ["Ciudad"]
    for _, etiq, _ in columnas:
        headers.append(etiq)
        headers.append("Actualizado")
    filas = []
    for city in CITIES:
        celdas = []
        for iid, _, calidad in columnas:
            px = precios.get(iid, {}).get(calidad, {}).get(city, 0)
            vals = [v for v in precios.get(iid, {}).get(calidad, {}).values() if v > 0]
            if px == 0 or not vals:
                txt, color = "—", None
            else:
                txt = f"${format_price(px)}"
                if px == max(vals):
                    color = colores_web.RICH_A_CSS.get("green", "#2ecc71")
                elif px == min(vals):
                    color = colores_web.RICH_A_CSS.get("red", "#e74c3c")
                else:
                    color = None
            celdas.append({"txt": txt, "color": color, "es_fresca": False})
            ts = fechas.get(iid, {}).get(calidad, {}).get(city, [])
            celdas.append({"txt": antiguedad(max(ts)) if ts else "—",
                           "color": None, "es_fresca": True})
        filas.append({"ciudad": city, "celdas": celdas})
    return {"headers": headers, "filas": filas}


def _datos_buscado(item):
    """Misma logica de datos que ver_detalle_buscado (menus.py).

    item: dict {nombre, id_base, tipo} de catalogo.buscar.
    Devuelve dict: {tipo, id_base, paneles: [{etiqueta, headers, filas}]}.
      - simple: un panel sin etiqueta con las calidades con datos.
      - arma:   un panel por encantamiento (Base, .1..4).
      - diario: un panel sin etiqueta con columnas Vacio/Lleno.
    """
    id_base = item["id_base"]
    tipo = item["tipo"]

    if tipo == "diario":
        base = id_base
        for suf in ("_EMPTY", "_FULL"):
            if base.endswith(suf):
                base = base[: -len(suf)]
                break
        ids = [f"{base}_EMPTY", f"{base}_FULL"]
    elif tipo == "arma":
        ids = [id_base] + [f"{id_base}@{i}" for i in range(1, 5)]
    else:
        ids = [id_base]

    raw_data = get_prices(ids)

    precios = {}  # item_id -> calidad -> {ciudad: precio}
    fechas = {}   # item_id -> calidad -> ciudad -> [timestamps ISO]
    for entry in raw_data or []:
        iid = entry.get("item_id", "")
        if iid not in ids:
            continue
        ciudad = entry.get("city", "")
        calidad = entry.get("quality", 1)
        precio = entry.get("sell_price_min", 0)
        precios.setdefault(iid, {}).setdefault(calidad, {})[ciudad] = precio
        fechas.setdefault(iid, {}).setdefault(calidad, {}).setdefault(ciudad, [])
        if precio > 0 and entry.get("sell_price_min_date"):
            fechas[iid][calidad][ciudad].append(entry["sell_price_min_date"])
        if entry.get("sell_price_max", 0) > 0 and entry.get("sell_price_max_date"):
            fechas[iid][calidad][ciudad].append(entry["sell_price_max_date"])

    paneles = []
    if tipo == "diario":
        columnas = [(ids[0], "Vacío", 1), (ids[1], "Lleno", 1)]
        paneles.append({"etiqueta": "", **_tabla_buscado(columnas, precios, fechas)})
    elif tipo == "arma":
        for etiq, iid in [("Base", id_base)] + [(f".{i}", f"{id_base}@{i}")
                                                for i in range(1, 5)]:
            columnas = _col_calidades(iid, precios)
            paneles.append({"etiqueta": etiq, **_tabla_buscado(columnas, precios, fechas)})
    else:
        columnas = _col_calidades(id_base, precios)
        paneles.append({"etiqueta": "", **_tabla_buscado(columnas, precios, fechas)})

    return {"tipo": tipo, "id_base": id_base, "paneles": paneles}


def _buscar_items(q):
    """Resultados de catalogo.buscar(q) enriquecidos para la plantilla.

    Cada item: {nombre, id_base, tipo, tier, color, icono}.
    """
    items = []
    for r in catalogo.buscar(q):
        try:
            tier, _ = info_tier(r["id_base"])
            color = colores_web.tier_a_css(tier)
        except Exception:
            tier, color = "?", "#ffffff"
        items.append({
            "nombre": r["nombre"],
            "id_base": r["id_base"],
            "tipo": r["tipo"],
            "tier": tier,
            "color": color,
            "icono": f"https://render.albiononline.com/v1/item/{r['id_base']}.png",
        })
    return items


# ─── Contexto comun para las plantillas ────────────────────────
def _menu_activo(ruta):
    """Ruta del menu que se marca activo ('inicio'|'pesca'|'recursos'|...)."""
    if ruta == "/":
        return "inicio"
    if ruta.startswith("/pesca"):
        return "pesca"
    if ruta.startswith("/recursos"):
        return "recursos"
    if ruta.startswith("/salsas"):
        return "salsas"
    if ruta.startswith("/buscar"):
        return "buscar"
    if ruta.startswith("/config"):
        return "config"
    return ""


def _contexto(ruta):
    """Datos que TODAS las plantillas usan (menu, url de la web)."""
    return {
        "menu_activo": _menu_activo(ruta),
        "ip_lan": ip_lan(),
        "port": PORT,
    }


# ─── Rutas ─────────────────────────────────────────────────────
@app.get("/")
def inicio():
    nombres = (["Pesca", "Recursos", "Salsas"])
    secciones = []
    iconos = ["fish", "mountain", "pot"]
    rutas = ["/pesca", "/recursos/fibra", "/salsas"]
    for i, (nombre, ruta) in enumerate(zip(nombres, rutas), start=1):
        secciones.append({
            "nombre": nombre,
            "ruta": ruta,
            "icono": iconos[i - 1],
            "resena": RESENAS_OPCIONES_PRINCIPAL[i],
        })
    return render_template("index.html", **_contexto("/"), secciones=secciones)


@app.get("/pesca")
def pesca():
    config = load_config()
    peces = []
    for nombre, info in (config.get("pescados") or {}).items():
        if nombre.startswith("_"):
            continue
        item_id = info["id"]
        tier, color = info_tier(item_id)
        peces.append({
            "nombre": nombre,
            "item_id": item_id,
            "trozos": info["trozos"],
            "tipo": info.get("tipo", "comun"),
            "tier": tier,
            "color": colores_web.tier_a_css(tier),
            "icono": f"https://render.albiononline.com/v1/item/{item_id}.png",
        })
    return render_template("pesca.html", **_contexto("/pesca"), peces=peces,
                           resena=RESENAS_MENU["pesca"])


@app.get("/pesca/<nombre>")
def pesca_detalle(nombre):
    config = load_config()
    info = (config.get("pescados") or {}).get(nombre)
    if not info:
        abort(404)
    item_id = info["id"]
    trozos = info["trozos"]
    tipo = info.get("tipo", "comun")
    tier, color = info_tier(item_id)
    datos = _datos_pez(nombre, item_id, trozos, tipo, config)
    return render_template(
        "pesca_detalle.html",
        **_contexto(f"/pesca/{quote(nombre)}"),
        nombre=nombre, item_id=item_id, tier=tier, color=colores_web.tier_a_css(tier),
        tipo_txt="Raro" if tipo == "raro" else "Comun",
        trozos=trozos, resena=RESENAS_DETALLE["pez"], datos=datos,
        icono=f"https://render.albiononline.com/v1/item/{item_id}.png",
    )


@app.get("/pesca/<nombre>/tabla")
def pesca_detalle_tabla(nombre):
    """Fragmento HTMX: solo la tabla + volumen + resumen del pez.

    La pagina de detalle la incluye con hx-get y polling (refresca sola
    cada 30 s sin recargar la pagina). Misma logica de datos que /pesca/<nombre>.
    """
    config = load_config()
    info = (config.get("pescados") or {}).get(nombre)
    if not info:
        abort(404)
    item_id = info["id"]
    trozos = info["trozos"]
    tipo = info.get("tipo", "comun")
    datos = _datos_pez(nombre, item_id, trozos, tipo, config)
    return render_template("_pesca_tabla.html", datos=datos)


@app.get("/recursos/<tipo>")
def recursos(tipo):
    config = load_config()
    info = (config.get("recursos") or {}).get(tipo)
    nombre = (info or {}).get("nombre", tipo.upper())
    par = PARES_RECURSO.get(tipo, nombre)
    tiers = (info or {}).get("tiers") or {}
    tiers_ordenados = sorted(tiers.keys(), key=lambda t: int(t[1:]))

    menu_items = []
    for tk in tiers_ordenados:
        td = tiers[tk]
        tier_num = int(tk[1:])
        if tier_num <= 3:
            nombre_item = td.get("nombre", f"{nombre} {tk}")
            menu_items.append({"label": f"{nombre_item} {tk}", "tier_key": tk, "modo": "todo"})
        else:
            crudo_name = td.get("nombre", f"{nombre} {tk}")
            ref_label = td["refinado"].split("_", 1)[1].title()
            ref_name = td.get("refinado_nombre", ref_label)
            menu_items.append({"label": f"{crudo_name} {tk}", "tier_key": tk, "modo": "crudo"})
            menu_items.append({"label": f"{ref_name} {tk}", "tier_key": tk, "modo": "refinado"})

    for item in menu_items:
        item["color"] = colores_web.tier_a_css(item["tier_key"][1:])
        item["icono"] = f"https://render.albiononline.com/v1/item/{item['tier_key']}_{tipo.upper()}.png"

    return render_template("recursos.html", **_contexto(f"/recursos/{tipo}"),
                           par=par, tipo=tipo, resena=RESENAS_MENU["recursos"],
                           menu_items=menu_items)


@app.get("/recursos/<tipo>/<tier_key>/<modo>")
def recursos_detalle(tipo, tier_key, modo):
    config = load_config()
    info = (config.get("recursos") or {}).get(tipo)
    tier_data = (info or {}).get("tiers") or {}
    td = tier_data.get(tier_key)
    if not info or not td:
        abort(404)
    nombre = info.get("nombre", tipo.upper())
    par = PARES_RECURSO.get(tipo, nombre)
    crudo_id = td["crudo"]
    refinado_id = td["refinado"]
    nombre_real = td.get("nombre", f"{nombre} {tier_key}")
    ref_label = refinado_id.split("_", 1)[1].title()
    ref_nombre = td.get("refinado_nombre", ref_label)
    if modo == "crudo":
        titulo_item = nombre_real
    elif modo == "refinado":
        titulo_item = ref_nombre
    else:
        titulo_item = f"{nombre_real} -> {ref_nombre}"
    color = colores_web.tier_a_css(tier_key[1:])
    datos = _datos_recurso(nombre, tier_key, td, modo)
    return render_template(
        "recursos_detalle.html",
        **_contexto(f"/recursos/{tipo}/{tier_key}/{modo}"),
        par=par, titulo=f"{titulo_item} {tier_key}", color=color,
        resena=RESENAS_DETALLE["recurso"], datos=datos, volver=f"/recursos/{tipo}",
    )


@app.get("/config")
def config():
    """Pantalla de configuracion: URL de la LAN + QR para el celular."""
    activo = cloudflared_activo()
    tunel_url = ""
    if activo:
        tun_file = os.path.join(BASE_DIR, "tun_url.txt")
        if os.path.exists(tun_file):
            with open(tun_file, "r", encoding="utf-8") as f:
                tunel_url = f.read().strip()
    return render_template("config.html", **_contexto("/config"),
                           tunel_url=tunel_url)


@app.get("/launcher")
def launcher():
    """Pantalla de inicio chica (ventana de escritorio): elige que abrir."""
    version = "0.0.0"
    try:
        with open(os.path.join(BASE_DIR, "version.txt"), "r", encoding="utf-8") as f:
            version = f.read().strip()
    except Exception:
        pass
    return render_template("launcher.html", **_contexto("/launcher"),
                           version=version)


@app.get("/qr-solo")
def qr_solo():
    """Ventana aparte con SOLO los QRs (local + túnel), sin menu ni config."""
    activo = cloudflared_activo()
    tunel_url = ""
    if activo:
        tun_file = os.path.join(BASE_DIR, "tun_url.txt")
        if os.path.exists(tun_file):
            with open(tun_file, "r", encoding="utf-8") as f:
                tunel_url = f.read().strip()
    url_local = f"http://{ip_lan()}:{PORT}/"
    return render_template("qr_solo.html", **_contexto("/qr-solo"),
                           url_local=url_local, tunel_url=tunel_url)


@app.get("/qr")
def qr():
    """QR en SVG del URL indicado (default: URL de la LAN). Generado al vuelo."""
    import qrcode
    import qrcode.image.svg

    url = request.args.get("url") or f"http://{ip_lan()}:{PORT}/"
    img = qrcode.make(url, image_factory=qrcode.image.svg.SvgPathImage,
                      box_size=6, border=2)
    buf = io.BytesIO()
    img.save(buf)
    buf.seek(0)
    return send_file(buf, mimetype="image/svg+xml")


@app.get("/salsas")
def salsas():
    config = load_config()
    items = (config.get("insumos_pesca") or {}).get("items") or {}
    salsas_lista = []
    for nombre, info in items.items():
        if "Salsa" not in nombre:
            continue
        item_id = info["id"]
        nivel = int(item_id.split("_LEVEL")[-1]) if "_LEVEL" in item_id else 0
        receta = info.get("receta") or {}
        cant_carne = receta.get("T1_FISHCHOPS", 0)
        cant_alga = receta.get("T1_SEAWEED", 0)
        salsas_lista.append({
            "nombre": nombre,
            "item_id": item_id,
            "nivel": nivel,
            "color": colores_web.ench_a_css(nivel),
            "receta": f"{cant_carne} Carne + {cant_alga} Alga",
            "icono": f"https://render.albiononline.com/v1/item/{item_id}.png",
        })
    return render_template("salsas.html", **_contexto("/salsas"),
                           salsas=salsas_lista, resena=RESENAS_MENU["insumos"])


@app.get("/salsas/<nombre>")
def salsa_detalle(nombre):
    config = load_config()
    items = (config.get("insumos_pesca") or {}).get("items") or {}
    info = items.get(nombre)
    if not info or "Salsa" not in nombre:
        abort(404)
    item_id = info["id"]
    nivel = int(item_id.split("_LEVEL")[-1]) if "_LEVEL" in item_id else 0
    receta = info.get("receta") or {}
    datos = _datos_salsa(nombre, item_id, receta, config)
    return render_template(
        "salsa_detalle.html",
        **_contexto(f"/salsas/{quote(nombre)}"),
        nombre=nombre, item_id=item_id,
        color=colores_web.ench_a_css(nivel), nivel=nivel,
        resena=RESENAS_DETALLE["insumo"], datos=datos,
        icono=f"https://render.albiononline.com/v1/item/{item_id}.png",
    )


@app.get("/salsas/<nombre>/tabla")
def salsa_detalle_tabla(nombre):
    """Fragmento HTMX: tabla + receta + volumen + resumen de la salsa."""
    config = load_config()
    items = (config.get("insumos_pesca") or {}).get("items") or {}
    info = items.get(nombre)
    if not info or "Salsa" not in nombre:
        abort(404)
    receta = info.get("receta") or {}
    datos = _datos_salsa(nombre, info["id"], receta, config)
    return render_template("_salsa_tabla.html", datos=datos)


@app.get("/buscar")
def buscar():
    """Pagina del buscador global: campo + resultados en vivo via HTMX."""
    q = request.args.get("q", "")
    return render_template("buscar.html", **_contexto("/buscar"), q=q,
                           resena=RESENAS_MENU["buscar"])


@app.get("/buscar/tabla")
def buscar_tabla():
    """Fragmento HTMX con los resultados de la consulta (hasta 15)."""
    q = request.args.get("q", "")
    items = _buscar_items(q)
    return render_template("_buscar_resultados.html", items=items, q=q)


@app.get("/buscar/item/<path:id_base>")
def buscar_detalle(id_base):
    """Detalle de un item del catalogo (arma/diario/simple), replica menus.py."""
    item = None
    for cand in catalogo.buscar(id_base.replace("_", " ")):
        if cand["id_base"] == id_base:
            item = cand
            break
    if not item:
        abort(404)
    try:
        tier, _ = info_tier(id_base)
        color = colores_web.tier_a_css(tier)
    except Exception:
        tier, color = "?", "#ffffff"
    etiqueta_tipo = {"diario": "Diario", "arma": "Arma", "simple": "Item"}.get(
        item["tipo"], "Item")
    resena = RESENAS_DETALLE[
        "buscado_diario" if item["tipo"] == "diario"
        else ("buscado_arma" if item["tipo"] == "arma" else "buscado")]
    datos = _datos_buscado(item)
    return render_template(
        "buscar_detalle.html",
        **_contexto(f"/buscar/item/{quote(id_base)}"),
        nombre=item["nombre"], id_base=id_base, tier=tier, color=color,
        etiqueta_tipo=etiqueta_tipo, resena=resena, datos=datos,
        icono=f"https://render.albiononline.com/v1/item/{id_base}.png",
    )


# ─── Control de túnel Cloudflare ────────────────────────────────────────
def cloudflared_activo():
    """True si hay un proceso cloudflared corriendo."""
    try:
        out = subprocess.run(
                ["tasklist", "/FI", "IMAGENAME eq cloudflared.exe"],
                capture_output=True, text=True, encoding="utf-8",
                errors="replace", timeout=10,
                creationflags=subprocess.CREATE_NO_WINDOW,
            ).stdout
        return "cloudflared.exe" in out
    except Exception:
        return False


def iniciar_tunel_func():
    """Lanza cloudflared apuntando a localhost:PORT y guarda la URL."""
    if cloudflared_activo():
        return False, "Tunel ya activo"
    if not os.path.exists(CLOUDFLARED):
        return False, "cloudflared.exe no encontrado"
    try:
        with open(TUN_LOG_FILE, "w", encoding="utf-8") as log:
            args = [CLOUDFLARED, "tunnel", "--url", f"http://localhost:{PORT}",
                    "--no-autoupdate"]
            subprocess.Popen(
                args,
                cwd=BASE_DIR,
                stdout=log,
                stderr=subprocess.STDOUT,
                creationflags=subprocess.CREATE_NO_WINDOW,
            )
        # Esperar hasta ~15s a que cloudflared publique su URL en el log
        url = ""
        for _ in range(15):
            time.sleep(1)
            if os.path.exists(TUN_LOG_FILE):
                with open(TUN_LOG_FILE, "r", encoding="utf-8",
                          errors="ignore") as lf:
                    texto = lf.read()
                m = re.search(r"https://[a-z0-9-]+\.trycloudflare\.com", texto)
                if m:
                    url = m.group(0)
                    break
        # Guardar URL en tun_url.txt (vacía si no llegó a conectarse)
        with open(TUN_URL_FILE, "w", encoding="utf-8") as f:
            f.write(url)
        if not url:
            return False, "El tunel no publico una URL a tiempo"
        return True, "Tunel iniciado"
    except Exception as e:
        # Si falla, limpiar archivo de log vacío
        try:
            with open(TUN_LOG_FILE, "w", encoding="utf-8") as f:
                f.write("")
        except Exception:
            pass
        return False, str(e)


def detener_tunel_func():
    """Detiene el proceso cloudflared y limpia archivos."""
    try:
        if cloudflared_activo():
            subprocess.run(["taskkill", "/F", "/IM", "cloudflared.exe"],
                          capture_output=True, timeout=10,
                          creationflags=subprocess.CREATE_NO_WINDOW)
        # Limpiar URL guardada
        try:
            with open(TUN_URL_FILE, "w", encoding="utf-8") as f:
                f.write("")
        except Exception:
            pass
        return True, "Tunel detenido"
    except Exception as e:
        return False, str(e)


@app.post("/tunel/start")
def tunel_start():
    """EndPoint para iniciar el tunel desde la web."""
    ok, msg = iniciar_tunel_func()
    if ok:
        # Leer URL del archivo tras iniciar
        url = ""
        if os.path.exists(TUN_URL_FILE):
            with open(TUN_URL_FILE, "r", encoding="utf-8") as f:
                url = f.read().strip()
        return _({"status": "ok", "url": url, "message": msg})
    return _({"status": "error", "message": msg}), 500


@app.post("/tunel/stop")
def tunel_stop():
    """EndPoint para detener el tunel desde la web."""
    ok, msg = detener_tunel_func()
    if ok:
        return _({"status": "ok", "message": msg})
    return _({"status": "error", "message": msg}), 500


@app.get("/status")
def status():
    """Retorna el estado real del tunel (basado en el proceso, no en el archivo)."""
    activo = cloudflared_activo()
    url = ""
    if activo and os.path.exists(TUN_URL_FILE):
        with open(TUN_URL_FILE, "r", encoding="utf-8") as f:
            url = f.read().strip()
    return _({"status": "ok", "tunel_activo": activo, "url": url})


def _apagar_flask():
    """Cierra el proceso por completo (server + ventana) con un pequeño retardo."""
    time.sleep(0.5)
    os._exit(0)


@app.get("/shutdown")
def shutdown():
    """Apaga el servidor Flask (usado por la ventana al cerrarse)."""
    import threading
    threading.Thread(target=_apagar_flask, daemon=True).start()
    return _({"status": "ok"})


def _(obj):
    """Helper para serializar a JSON-friendly dict."""
    return obj


# ─── Arranque ──────────────────────────────────────────────────
if __name__ == "__main__":
    print(f"Albion Helper web (Flask) en http://{ip_lan()}:{PORT}/")
    app.run(host=HOST, port=PORT, threaded=True, debug=False)