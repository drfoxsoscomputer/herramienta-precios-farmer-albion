# Tests de market_summary (Fase B) — run from repo cwd
# market_summary es FUNCION PURA: recibe precios + historial + item y
# devuelve un dict. Ningun escenario toca la red (sin peticiones extra).
import json
import os
import sys
import urllib.request
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from formatting import market_summary, DIAS_ESP

CONFIG_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "albion_config.json")
with open(CONFIG_PATH, "r", encoding="utf-8") as f:
    CONFIG = json.load(f)

CITIES = ["Thetford", "Lymhurst", "Fort Sterling", "Bridgewatch", "Martlock"]
SHARK = "T8_FISH_SALTWATER_ALL_BOSS_SHARK"


def dia_esp(ts):
    """Nombre espanol del dia de un timestamp (misma logica que market_summary)."""
    return DIAS_ESP[datetime.fromisoformat(ts).strftime("%A")]


def entry(location, data):
    """Un entry crudo como los que devuelve get_history_raw."""
    return {"item_id": "X", "location": location, "data": data}


def punto(ts, cnt):
    return {"timestamp": ts, "item_count": cnt, "avg_price": 100}


# ── 1. pez con datos: min/max visibles ─────────────────────────
precios_pez = {"T4_FISH_FRESHWATER_ALL_COMMON": {"Thetford": 1200, "Lymhurst": 900, "Fort Sterling": 0}}
hist = [entry("Thetford", [punto("2026-07-25T16:00:00", 10)]),
        entry("Lymhurst", [punto("2026-07-25T18:00:00", 5)])]
r = market_summary(precios_pez, hist, "T4_FISH_FRESHWATER_ALL_COMMON")
assert r["min_venta"] == 900 and r["max_venta"] == 1200, f"min/max: {r}"
assert r["min_ciudad"] == "Lymhurst" and r["max_ciudad"] == "Thetford", f"ciudades: {r}"
assert r["volumen_total"] == 15, f"volumen: {r}"
assert r["sin_datos"] is False, f"sin_datos: {r}"
print("PASS pez con datos: min/max/volumen visibles, ciudades min/max, sin_datos False")

# ── 2. tiburon sin ventas: sin_datos True ─────────────────────
precios_shark = {SHARK: {c: 0 for c in CITIES}}
r = market_summary(precios_shark, [], SHARK)
assert r["sin_datos"] is True, f"tiburon sin_datos: {r}"
assert r["min_venta"] == 0 and r["max_venta"] == 0, f"tiburon precios: {r}"
assert r["min_ciudad"] == "" and r["max_ciudad"] == "", f"tiburon ciudades: {r}"
assert r["volumen_total"] == 0, f"tiburon volumen: {r}"
print("PASS tiburon sin ventas: sin_datos True (UI muestra 'Sin datos de venta'), ciudades vacias")

# ── 3. dia de mayor venta con historial completo (7 dias) ──────
dias7 = ["2026-07-20T12:00:00", "2026-07-21T12:00:00", "2026-07-22T12:00:00",
         "2026-07-23T12:00:00", "2026-07-24T12:00:00", "2026-07-25T12:00:00",
         "2026-07-26T12:00:00"]  # lun..dom
hist7 = [entry(c, [punto(ts, 100)]) for c, ts in zip(CITIES * 2, dias7)]
hist7 += [entry("Fort Sterling", [punto("2026-07-22T16:00:00", 400),
                                  punto("2026-07-22T18:00:00", 100)])]  # miercoles domina
r = market_summary(precios_pez, hist7, "T4_FISH_FRESHWATER_ALL_COMMON")
assert r["dia_mayor_venta"] == dia_esp("2026-07-22T12:00:00"), f"dia mayor: {r}"
assert r["volumen_dia"] == 600, f"volumen dia: {r}"
assert r["volumen_total"] == 1200, f"volumen total: {r}"
print(f"PASS dia mayor venta 7d: {r['dia_mayor_venta']} ({r['volumen_dia']} uds)")

# ── 4. historial incompleto (3 dias): solo dias reales ─────────
dias3 = ["2026-07-25T12:00:00", "2026-07-26T12:00:00", "2026-07-27T12:00:00"]  # sab..lun
nombres3 = {dia_esp(t) for t in dias3}
hist3 = [entry(c, [punto(ts, 100 if i == 0 else (200 if i == 1 else 50))])
         for i, (c, ts) in enumerate(zip(CITIES, dias3))]
r = market_summary(precios_pez, hist3, "T4_FISH_FRESHWATER_ALL_COMMON")
assert r["dia_mayor_venta"] in nombres3, f"dia {r['dia_mayor_venta']} no esta entre {nombres3}"
assert r["dia_mayor_venta"] == dia_esp("2026-07-26T12:00:00"), f"dia mayor 3d: {r}"
assert r["volumen_dia"] == 200, f"volumen dia 3d: {r}"
print("PASS historial 3 dias: solo dias con datos (domingo lidera)")

# ── 5. ingrediente si/no (recetas de insumos_pesca) ────────────
recetas_config = CONFIG["insumos_pesca"]["items"]
r = market_summary({}, [], "T1_FISHCHOPS", recetas_config)
assert r["es_ingrediente"] is True and set(r["recetas"]) == {"Salsa básica", "Salsa elegante", "Salsa especial"}, r
r = market_summary({}, [], SHARK, recetas_config)
assert r["es_ingrediente"] is False and r["recetas"] == [], r
r = market_summary({}, [], SHARK)  # sin config -> no se evalua
assert r["es_ingrediente"] is False and r["recetas"] == [], r
print("PASS ingrediente si/no: T1_FISHCHOPS en 3 salsas; tiburon no")

# ── 6. diferencia refinado - crudo (solo recursos con par) ─────
precios_par = {"T8_FIBER": {"Thetford": 500, "Lymhurst": 600},
               "T8_CLOTH": {"Thetford": 800, "Lymhurst": 700}}
r = market_summary(precios_par, [], "T8_CLOTH")
assert r["diferencia_refinado"] == 200, f"diferencia: {r}"  # 800 - 600
precios_sin_par = {SHARK: {"Thetford": 1}, "T1_FISHCHOPS": {"Thetford": 2}}
r = market_summary(precios_sin_par, [], SHARK)
assert r["diferencia_refinado"] is None, f"sin par: {r}"
print("PASS diferencia refinado - crudo: 200 con par; None sin par")

# ── 7. formato: historial crudo de get_history_raw sin red ─────
# Consume el shape de get_history_raw (data[] con timestamp e item_count)
# y NUNCA toca la red: si llamara a urllib, este fake lo detectaria.
def boom(*a, **k):
    raise AssertionError("market_summary no debe tocar la red")

original = urllib.request.urlopen
urllib.request.urlopen = boom
try:
    r = market_summary(precios_pez, hist, "T4_FISH_FRESHWATER_ALL_COMMON")
finally:
    urllib.request.urlopen = original
assert r["volumen_total"] == 15, f"volumen sin red: {r}"
print("PASS formato: consume data[].timestamp/item_count sin peticiones extra")

print("\nTODOS LOS TESTS DE MARKET_SUMMARY PASARON")
