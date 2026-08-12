# estilo.py
# ─── Tema visual de la web (paleta dorada Albion) ──────────────
# Solo estilos: la paleta Quasar de NiceGUI + CSS global (fondo,
# tarjetas, tablas, tipografia). Cero logica de datos.

from nicegui import ui

# ─── Paleta dorada Albion ──────────────────────────────────────
# primary: dorado del juego. dark: fondo oscuro de la app.
# Se aplican como variables Quasar (--q-*) dentro del CSS shared;
# NO usar ui.colors(): crea UI global que choca con @ui.page en
# NiceGUI 3.x ("ui.page cannot be used when UI is defined in the
# global scope").
PALETA_CSS = """
:root {
    --q-primary: #c9a227;
    --q-secondary: #8b6f1e;
    --q-accent: #e6c45c;
    --q-positive: #2ecc71;
    --q-negative: #e74c3c;
    --q-info: #5b8dc9;
    --q-warning: #f39c12;
    --q-dark: #1a1a1e;
    --q-dark-page: #121216;
}
"""

CSS_GLOBAL = """
body { font-family: 'Segoe UI', system-ui, sans-serif; }

/* Fondo con gradiente sutil para que no sea un negro plano */
.q-page-container {
    background: linear-gradient(180deg, #121216 0%, #16161c 100%);
    min-height: 100vh;
}

/* Tarjetas redondeadas con hover suave */
.alb-card {
    border-radius: 14px;
    border: 1px solid #2a2a33;
    background: #1d1d24;
    transition: transform .12s ease, border-color .12s ease, box-shadow .12s ease;
}
.alb-card:hover {
    transform: translateY(-2px);
    border-color: #c9a227;
    box-shadow: 0 6px 18px rgba(201, 162, 39, .15);
}
.alb-card-static { border-radius: 14px; border: 1px solid #2a2a33; background: #1d1d24; }

/* Tabla de precios */
.alb-table { width: 100%; border-collapse: collapse; font-size: 14px; }
.alb-table th {
    text-align: left;
    padding: 8px 12px;
    background: #23232c;
    color: #e6c45c;
    font-weight: 600;
    border-bottom: 2px solid #c9a227;
}
.alb-table td { padding: 8px 12px; border-bottom: 1px solid #26262e; }
.alb-table tr:nth-child(even) td { background: #1a1a20; }
.alb-table tr:hover td { background: #24242d; }
.alb-table .num { text-align: right; }
.alb-table .dim { color: #666677; }
"""


def aplicar_tema():
    """Aplica paleta + CSS global a TODAS las paginas (shared=True).

    Llamar a nivel de modulo (en webui.py), no dentro de main().
    """
    ui.add_css(PALETA_CSS + CSS_GLOBAL, shared=True)
