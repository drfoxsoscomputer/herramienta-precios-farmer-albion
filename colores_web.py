# colores_web.py
# ─── Adaptador de colores Rich -> CSS para la web ─────────────
# Las funciones de formatting.py (color_precio, color_item) devuelven
# markup Rich ([green]...[/]) que no sirve en el navegador. Este modulo
# traduce la paleta del proyecto (COLORES_TIER / ENCH_COLORS) a colores
# CSS y reimplementa el criterio verde/rojo como color web puro.

from constants import COLORES_TIER, ENCH_COLORS
from formatting import format_price

# ─── Traduccion de la paleta Rich a CSS ────────────────────────
# Rich usa nombres ANSI/256; el navegador necesita hex o nombres web.
# grey58 -> #555555 (gris medio), dark_orange -> orange, el resto ya
# son nombres web validos.
RICH_A_CSS = {
    "grey58": "#555555",
    "white": "#ffffff",
    "green": "green",
    "cyan": "cyan",
    "magenta": "magenta",
    "dark_orange": "orange",
    "red": "red",
    "yellow": "yellow",
    "blue": "blue",
}


def tier_a_css(tier):
    """Color CSS de un tier (str '1'..'8'). Fallback blanco."""
    return RICH_A_CSS.get(COLORES_TIER.get(tier, "white"), "#ffffff")


def ench_a_css(nivel):
    """Color CSS de un nivel de encantamiento (1..4). Fallback blanco."""
    color = ENCH_COLORS[nivel] if 0 <= nivel < len(ENCH_COLORS) else ""
    return RICH_A_CSS.get(color, "#ffffff")


def precio_web_color(valor, mejor, peor):
    """Criterio verde/rojo de color_precio (formatting.py) como CSS.

    Devuelve "green" si es el mayor precio, "red" si es el menor y None
    en el medio (sin color). El caso N/D (valor 0) tambien es None: el
    texto lo maneja la UI. Orden de chequeo igual que en consola: el
    mayor gana si todos empatan.
    """
    if valor == 0:
        return None
    if valor == mejor:
        return "green"
    if valor == peor:
        return "red"
    return None


def precio_web(valor, mejor, peor):
    """(texto, color_css) de una celda de precio, listo para la UI web.

    Texto: "$1,234" formateado o "N/D" si no hay dato. Color: None
    cuando no aplica verde/rojo.
    """
    if valor == 0:
        return "N/D", None
    return f"${format_price(valor)}", precio_web_color(valor, mejor, peor)
