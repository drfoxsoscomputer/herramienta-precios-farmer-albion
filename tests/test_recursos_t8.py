# Tests de los 10 items T8 en albion_config.json — run from repo cwd
# Valida la estructura de T8 contra el esquema real de T4/T6:
# {crudo, refinado, nombre, refinado_nombre} (NO izquierda/derecha).
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

CONFIG_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "albion_config.json")

with open(CONFIG_PATH, "r", encoding="utf-8") as f:
    CONFIG = json.load(f)

RECURSOS = CONFIG["recursos"]

# Pares T8 esperados (crudo/refinado) segun la tarea 2.1
PARES_T8 = {
    "fibra": ("T8_FIBER", "T8_CLOTH"),
    "madera": ("T8_WOOD", "T8_PLANKS"),
    "cuero": ("T8_HIDE", "T8_LEATHER"),
    "mineral": ("T8_ORE", "T8_METALBAR"),
    "piedra": ("T8_ROCK", "T8_STONEBLOCK"),
}

CLAVES_REQUERIDAS = {"crudo", "refinado", "nombre", "refinado_nombre"}

# ── 1. los 5 recursos tienen tier T8 ──────────────────────────
assert set(PARES_T8) <= set(RECURSOS), f"faltan recursos: {set(PARES_T8) - set(RECURSOS)}"
for rec in PARES_T8:
    assert "T8" in RECURSOS[rec]["tiers"], f"{rec}: falta el tier T8"
print("PASS: los 5 recursos tienen tier T8")

# ── 2. cada T8 tiene las 4 claves requeridas (exactas) ────────
for rec in PARES_T8:
    t8 = RECURSOS[rec]["tiers"]["T8"]
    assert set(t8.keys()) == CLAVES_REQUERIDAS, (
        f"{rec}: T8 claves {set(t8.keys())} != {CLAVES_REQUERIDAS}")
print("PASS estructura: cada T8 tiene las 4 claves (crudo/refinado/nombre/refinado_nombre)")

# ── 3. ids con prefijo T8_ ────────────────────────────────────
for rec in PARES_T8:
    t8 = RECURSOS[rec]["tiers"]["T8"]
    assert t8["crudo"].startswith("T8_"), f"{rec}: crudo {t8['crudo']} no empieza con T8_"
    assert t8["refinado"].startswith("T8_"), f"{rec}: refinado {t8['refinado']} no empieza con T8_"
print("PASS ids: crudo y refinado usan prefijo T8_")

# ── 4. pares exactos crudo/refinado ───────────────────────────
for rec, (crudo_esp, refinado_esp) in PARES_T8.items():
    t8 = RECURSOS[rec]["tiers"]["T8"]
    assert t8["crudo"] == crudo_esp, f"{rec}: crudo {t8['crudo']} != {crudo_esp}"
    assert t8["refinado"] == refinado_esp, f"{rec}: refinado {t8['refinado']} != {refinado_esp}"
print("PASS pares: FIBER/CLOTH, WOOD/PLANKS, HIDE/LEATHER, ORE/METALBAR, ROCK/STONEBLOCK")

# ── 5. simetria contra el esquema T4/T6 existente ─────────────
for rec in PARES_T8:
    tiers = RECURSOS[rec]["tiers"]
    t8 = tiers["T8"]
    for ref_tier in ("T4", "T6"):
        assert ref_tier in tiers, f"{rec}: falta {ref_tier} de referencia"
        ref = tiers[ref_tier]
        # mismo set de claves
        assert set(ref.keys()) == set(t8.keys()), (
            f"{rec}: esquema {ref_tier} {set(ref.keys())} != T8 {set(t8.keys())}")
        # mismo sufijo tras el prefijo de tier (T4_FIBER -> T8_FIBER)
        for campo in ("crudo", "refinado"):
            suf_ref = ref[campo].split("_", 1)[1]
            suf_t8 = t8[campo].split("_", 1)[1]
            assert suf_ref == suf_t8, (
                f"{rec}: {campo} {ref_tier}={ref[campo]} vs T8={t8[campo]} "
                f"(sufijo {suf_ref} != {suf_t8})")
print("PASS simetria: esquema T8 identico a T4/T6 (claves y sufijos de ids)")

# ── 6. nombre y refinado_nombre no vacios ─────────────────────
for rec in PARES_T8:
    t8 = RECURSOS[rec]["tiers"]["T8"]
    assert t8["nombre"].strip(), f"{rec}: nombre vacio"
    assert t8["refinado_nombre"].strip(), f"{rec}: refinado_nombre vacio"
print("PASS nombres: nombre y refinado_nombre no vacios")

print("\nTODOS LOS TESTS DE T8 PASARON")
