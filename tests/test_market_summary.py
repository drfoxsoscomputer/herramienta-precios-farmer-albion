# Tests de market_summary — run from repo cwd
# market_summary es FUNCION PURA: recibe precios + item (+ config) y
# devuelve un dict. Ningun escenario toca la red (sin peticiones extra).
import json
import os
import sys
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from formatting import market_summary

CONFIG_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "albion_config.json")
with open(CONFIG_PATH, "r", encoding="utf-8") as f:
    CONFIG = json.load(f)

CITIES = ["Thetford", "Lymhurst", "Fort Sterling", "Bridgewatch", "Martlock"]
SHARK = "T8_FISH_SALTWATER_ALL_BOSS_SHARK"

CLAVES = ("min_venta", "max_venta", "min_ciudad", "max_ciudad",
          "es_ingrediente", "recetas", "sin_datos")


# ── 1. pez con datos: min/max visibles + contrato de claves ────
precios_pez = {"T4_FISH_FRESHWATER_ALL_COMMON": {"Thetford": 1200, "Lymhurst": 900, "Fort Sterling": 0}}
r = market_summary(precios_pez, "T4_FISH_FRESHWATER_ALL_COMMON")
for clave in CLAVES:
    assert clave in r, f"falta clave '{clave}' en: {sorted(r)}"
assert r["min_venta"] == 900 and r["max_venta"] == 1200, f"min/max: {r}"
assert r["min_ciudad"] == "Lymhurst" and r["max_ciudad"] == "Thetford", f"ciudades: {r}"
assert r["sin_datos"] is False, f"sin_datos: {r}"
print("PASS pez con datos: min/max visibles, ciudades min/max, sin_datos False, contrato de claves")

# ── 2. tiburon sin ventas: sin_datos True ─────────────────────
precios_shark = {SHARK: {c: 0 for c in CITIES}}
r = market_summary(precios_shark, SHARK)
assert r["sin_datos"] is True, f"tiburon sin_datos: {r}"
assert r["min_venta"] == 0 and r["max_venta"] == 0, f"tiburon precios: {r}"
assert r["min_ciudad"] == "" and r["max_ciudad"] == "", f"tiburon ciudades: {r}"
print("PASS tiburon sin ventas: sin_datos True (UI muestra 'Sin datos de venta'), ciudades vacias")

# ── 3. ingrediente si/no (recetas de insumos_pesca) ────────────
recetas_config = CONFIG["insumos_pesca"]["items"]
r = market_summary({}, "T1_FISHCHOPS", recetas_config)
assert r["es_ingrediente"] is True and set(r["recetas"]) == {"Salsa básica", "Salsa elegante", "Salsa especial"}, r
r = market_summary({}, SHARK, recetas_config)
assert r["es_ingrediente"] is False and r["recetas"] == [], r
r = market_summary({}, SHARK)  # sin config -> no se evalua
assert r["es_ingrediente"] is False and r["recetas"] == [], r
print("PASS ingrediente si/no: T1_FISHCHOPS en 3 salsas; tiburon no")

# ── 4. sin red: market_summary nunca toca la red ───────────────
def boom(*a, **k):
    raise AssertionError("market_summary no debe tocar la red")

original = urllib.request.urlopen
urllib.request.urlopen = boom
try:
    r = market_summary(precios_pez, "T4_FISH_FRESHWATER_ALL_COMMON")
finally:
    urllib.request.urlopen = original
assert r["max_venta"] == 1200, f"max sin red: {r}"
print("PASS sin red: market_summary es funcion pura (no usa urllib)")

# ── 5. integridad del config: 'uso' solo en peces raros ────────
for nombre, info in CONFIG["pescados"].items():
    if nombre.startswith("_"):
        continue
    tipo = info.get("tipo", "comun")
    if tipo == "raro":
        assert "uso" in info and info["uso"], f"pez raro sin 'uso' (o vacio): {nombre}"
    else:
        assert not info.get("uso"), f"pez comun con 'uso': {nombre}"
print("PASS integridad config: 'uso' presente y no vacio en los 22 raros; ausente en los comunes")

# ── 6. tiburon T8 -> trofeo oficial ────────────────────────────
shark_info = next(v for k, v in CONFIG["pescados"].items()
                  if not k.startswith("_") and v.get("id") == SHARK)
assert shark_info["uso"] == "Trofeo de tiburón", f"uso tiburon: {shark_info.get('uso')!r}"
print("PASS tiburon T8: 'uso' == 'Trofeo de tiburón'")

# ── 7. desempate por volumen: empate en min/max gana mayor volumen ──
# Tres ciudades a $100 (empate total); sin volumen se toma el 1er match
# del dict. Con volumen, la de mayor venta gana el desempate.
empate = {"T4_DIRT": {"Thetford": 100, "Lymhurst": 100, "Fort Sterling": 100}}
r_sin = market_summary(empate, "T4_DIRT")
assert r_sin["min_ciudad"] == "Thetford" and r_sin["max_ciudad"] == "Thetford", r_sin
vol = {"Thetford": 10, "Lymhurst": 900, "Fort Sterling": 50}
r = market_summary(empate, "T4_DIRT", volumen=vol)
assert r["min_ciudad"] == "Lymhurst", f"desempate min: {r}"
assert r["max_ciudad"] == "Lymhurst", f"desempate max: {r}"
print("PASS desempate por volumen: entre empate de 3, gana la de mayor volumen")

print("\nTODOS LOS TESTS DE MARKET_SUMMARY PASARON")
