# tema.py — TEMA ALBION GLASS: fuente única de la paleta en Python.
# ─────────────────────────────────────────────────────────────
# Espejo de static/css/tema.css y static/js/tema.js: si cambiás un
# valor acá, cambialo también allá (y viceversa).
# La estética está inspirada en la UI del juego pero es obra propia:
# colores puros (sin copyright) + técnicas de vidrio y metal.

ORO_BRILLO = "#f5d576"
ORO_CLARO = "#e8b84a"
ORO = "#c9a256"
AMBAR = "#e8a545"
BRONCE = "#8a6a3a"
BRONCE_HONDO = "#5a4020"

FONDO = "#1a1410"
PANEL = "#241c16"
BORDE = "#3a2a24"

PLATA_CLARA = "#f4f4f5"
PLATA = "#a1a1aa"
PLATA_HONDA = "#52525b"


def rgb(hexa):
    """'#rrggbb' -> (r, g, b), el formato que PIL entiende."""
    return tuple(int(hexa[i:i + 2], 16) for i in (1, 3, 5))
