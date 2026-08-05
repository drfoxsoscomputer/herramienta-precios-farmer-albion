# textos.py
# ─── Textos de ayuda (copy en espanol) ─────────────────────────
# Solo contenido, cero logica. Cada resena explica que se ve en
# esa pantalla y como usarla. Se muestran en gris tenue.
# Separar el copy de la logica permite editarlo sin tocar codigo.

# ─── Resenas de los menus (debajo del recuadro) ────────────────
RESENAS_MENU = {
    "principal": (
        "Elige una seccion. Cada una muestra el mercado de un rubro: "
        "precio por ciudad y el volumen de los ultimos 7 dias."
    ),
    "pesca": (
        "Elige un pez. Veras su precio por ciudad, el volumen de los "
        "ultimos 7 dias y si es ingrediente de alguna salsa."
    ),
    "recursos": (
        "Elige un tier. Los tiers bajos (T2/T3) muestran crudo y refinado "
        "juntos; los altos (T4+) los separan, con sus encantamientos "
        ".1 a .4."
    ),
    "insumos": (
        "Elige una salsa. Veras su receta, el precio de venta por ciudad "
        "y el volumen de los ultimos 7 dias."
    ),
    "buscar": (
        "Escribe un termino (puede ser parcial y sin acentos) para filtrar "
        "todo el catalogo de items: pesca, recursos, armas, diarios..."
    ),
}

# ─── Resenas de las pantallas de detalle (bajo el titulo) ──────
RESENAS_DETALLE = {
    "pez": (
        "Verde = el mayor precio de esa ciudad, rojo = el menor, N/D = sin "
        "datos. Abajo, el resumen de mercado."
    ),
    "recurso": (
        "Verde = el mayor precio de esa ciudad, rojo = el menor. .1 a .4 "
        "son encantamientos. N/D = sin datos."
    ),
    "insumo": (
        "Receta de la salsa y su mercado por ciudad: precio de venta y "
        "volumen de los ultimos 7 dias."
    ),
    "buscado": (
        "Precios por ciudad y calidad. Verde = el mayor precio de esa "
        "columna, rojo = el menor, — = sin datos. En armas, cada "
        "encantamiento (.1 a .4) es un panel aparte."
    ),
}

# ─── Calidades de items (buscador global) ─────────────────────
CALIDADES = ["Normal", "Bueno", "Notable", "Sobresaliente", "Obra maestra"]

# ─── Resumen de mercado ─
RESUMEN = {
    "titulo": "Resumen de mercado",
    "venta_min": "Venta min",
    "venta_max": "Venta max",
    "uso": "Se usa en",
    "ingrediente": "Es ingrediente de",
    "no_ingrediente": "No es ingrediente de ninguna salsa",
    "sin_datos": "Sin datos de venta",
}

# ─── Leyenda de colores por tier (con su color real) ───────────
# Los nombres de color deben coincidir con COLORES_TIER (constants.py).
LEYENDA_TIERS = (
    "[grey58]T1 gris[/]  |  [white]T2 blanco[/]  |  [green]T3 verde[/]  |  "
    "[cyan]T4 cian[/]  |  [magenta]T5 magenta[/]  |  [dark_orange]T6 naranja[/]  |  "
    "[red]T7 rojo[/]  |  [yellow]T8 amarillo[/]"
)

# ─── Pares crudo/refinado de cada recurso (etiquetas de menu) ──
# El menu principal y el encabezado de cada recurso muestran el par
# "crudo/refinado" en vez del nombre solo. Claves = claves de config.
PARES_RECURSO = {
    "fibra": "Fibra/Tela",
    "madera": "Troncos/Tablas",
    "cuero": "Piel/Cuero",
    "mineral": "Mineral/Barra",
    "piedra": "Piedra/Bloque",
}

# ─── Resenas de las opciones del menu principal ─────────────────
RESENAS_OPCIONES_PRINCIPAL = {
    1: "Pesca de peces comunes; precios por ciudad, entero y picado, volumen de los ultimos 7 dias.",
    2: "Fibra: precio del recurso por ciudad, verde = mayor precio, rojo = menor.",
    3: "Madera: precio del recurso por ciudad, verde = mayor precio, rojo = menor.",
    4: "Cuero: precio del recurso por ciudad, verde = mayor precio, rojo = menor.",
    5: "Mineral: precio del recurso por ciudad, verde = mayor precio, rojo = menor.",
    6: "Piedra: precio del recurso por ciudad, verde = mayor precio, rojo = menor.",
    7: "Salsas de pescado: analisis de rentabilidad, receta, costo de insumos.",
    8: "Buscar: escribe un termino y encuentra cualquier item del catalogo por nombre (pesca, recursos, armas, diarios...).",
}
