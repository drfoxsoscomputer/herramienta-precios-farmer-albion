# textos.py
# ─── Textos de ayuda (copy en espanol) ─────────────────────────
# Solo contenido, cero logica. Cada resena explica que se ve en
# esa pantalla y como usarla. Se muestran en gris tenue.
# Separar el copy de la logica permite editarlo sin tocar codigo.

# ─── Resenas de los menus (debajo del recuadro) ────────────────
RESENAS_MENU = {
    "principal": (
        "Elige una seccion. Cada una muestra el mercado de un rubro: "
        "precios por ciudad, la mejor ciudad para vender o comprar, "
        "y el volumen de los ultimos 7 dias."
    ),
    "pesca": (
        "Elige un pez. Veras su precio por ciudad, el volumen de los "
        "ultimos 7 dias, el dia de mayor venta y si es ingrediente de "
        "alguna salsa."
    ),
    "recursos": (
        "Elige un tier. Los tiers bajos (T2/T3) muestran crudo y refinado "
        "juntos; los altos (T4+) los separan, con sus encantamientos "
        ".1 a .4."
    ),
    "insumos": (
        "Elige una salsa. Veras su analisis de rentabilidad: receta, "
        "costo de insumos, ganancia al fabricarla, y si conviene fabricar "
        "o vender los insumos por separado."
    ),
}

# ─── Resenas de las pantallas de detalle (bajo el titulo) ──────
RESENAS_DETALLE = {
    "pez": (
        "Verde = mejor precio de esa ciudad, rojo = el peor, N/D = sin "
        "datos. Abajo, el resumen de mercado muestra datos objetivos."
    ),
    "recurso": (
        "Tiers bajos: comprar barato es bueno (verde). Tiers altos: vender "
        "caro es bueno (verde); rojo = el precio contrario. .1 a .4 son "
        "encantamientos. N/D = sin datos."
    ),
    "insumo": (
        "Se compra cada insumo al precio minimo y se vende en la ciudad "
        "que paga mas. Compara fabricar la salsa vs vender los insumos "
        "por separado."
    ),
}

# ─── Resumen de mercado (datos objetivos, sin recomendaciones) ─
RESUMEN = {
    "titulo": "Resumen de mercado",
    "venta_min": "Venta min",
    "venta_max": "Venta max",
    "volumen": "Volumen 7 dias",
    "dia_mayor": "Dia de mayor venta",
    "ingrediente": "Es ingrediente de",
    "no_ingrediente": "No es ingrediente de ninguna salsa",
    "diferencia": "Diferencia refinado - crudo",
    "sin_datos": "Sin datos de venta",
}

# ─── Leyenda de colores por tier (con su color real) ───────────
# Los nombres de color deben coincidir con COLORES_TIER (constants.py).
LEYENDA_TIERS = (
    "[grey58]T1 gris[/]  |  [white]T2 blanco[/]  |  [green]T3 verde[/]  |  "
    "[cyan]T4 cian[/]  |  [magenta]T5 magenta[/]  |  [dark_orange]T6 naranja[/]  |  "
    "[red]T7 rojo[/]  |  [yellow]T8 amarillo[/]"
)

# ─── Resenas de las opciones del menu principal ─────────────────
RESENAS_OPCIONES_PRINCIPAL = {
    1: "Pesca de peces comunes; precios por ciudad, entero vs picado, mejor ciudad para vender.",
    2: "Fibra: precio del recurso, verde = barato, rojo = caro. Tiers bajos: comprar barato.",
    3: "Madera: precio del recurso, verde = barato, rojo = caro. Tiers bajos: comprar barato.",
    4: "Cuero: precio del recurso, verde = barato, rojo = caro. Tiers bajos: comprar barato.",
    5: "Mineral: precio del recurso, verde = barato, rojo = caro. Tiers bajos: comprar barato.",
    6: "Piedra: precio del recurso, verde = barato, rojo = caro. Tiers bajos: comprar barato.",
    7: "Salsas de pescado: analisis de rentabilidad, receta, costo de insumos.",
}
