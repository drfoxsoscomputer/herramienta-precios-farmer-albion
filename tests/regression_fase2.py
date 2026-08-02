# Regression battery for menus.py (Fase 2 selector) — run from repo cwd
import io
import os
import sys
import types

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import menus
from rich.text import Text

_limpiar_real = menus.limpiar_pantalla  # guardar la real antes de que seccion 4 la parchee

# ── 1. limpiar_pantalla (fallback ANSI en sandbox) ──
buf = io.StringIO()
fake = types.SimpleNamespace(getvalue=buf.getvalue)
menus.console = type(menus.console)(
    file=buf, force_terminal=True, width=120, height=50
)
menus.limpiar_pantalla()
out = buf.getvalue()
buf.seek(0); buf.truncate(0)
assert out == "\x1b[2J\x1b[H", repr(out)
print("PASS limpiar_pantalla borra completo (\\x1b[2J\\x1b[H)")

# ── 2. _mover_cursor: wrap-around (40 casos) ─────────────────────
def check(cursor, tecla, filas, n, esperado, caso):
    got = menus._mover_cursor(cursor, tecla, filas, n)
    assert got == esperado, f"{caso}: {cursor} {tecla} filas={filas} n={n} -> {got}, esperado {esperado}"

# 1 columna (filas=5, n=5)
check(0, "up", 5, 5, 4, "col unica: primero->ultimo")
check(4, "down", 5, 5, 0, "col unica: ultimo->primero")
check(2, "up", 5, 5, 1, "col unica up normal")
check(2, "down", 5, 5, 3, "col unica down normal")
# 2 columnas (filas=19, n=38, menu pesca)
check(0, "up", 19, 38, 37, "pesca primero->ultimo")
check(37, "down", 19, 38, 0, "pesca ultimo->primero")
check(18, "up", 19, 38, 17, "fondo col0 up -> fila 17 col0")
check(19, "up", 19, 38, 37, "tope col1 up -> fondo col1")
check(18, "down", 19, 38, 0, "fondo col0 down -> tope col0")
check(37, "down", 19, 38, 0, "fondo col1 down -> tope col0")
check(5, "left", 19, 38, 24, "col0 left -> col1 misma fila (wrap)")
check(24, "left", 19, 38, 5, "col1 left -> col0 misma fila")
check(5, "right", 19, 38, 24, "col0 right -> col1 misma fila")
check(24, "right", 19, 38, 5, "col1 right -> col0 misma fila (wrap)")
# columna parcial (filas=4, n=7 -> col0=4 items, col1=3 items)
check(0, "up", 4, 7, 6, "parcial primero->ultimo")
check(6, "down", 4, 7, 0, "parcial ultimo->primero")
check(0, "right", 4, 7, 4, "parcial col0->col1")
check(4, "left", 4, 7, 0, "parcial col1->col0")
check(3, "down", 4, 7, 0, "parcial fondo col0 -> tope col0")
check(6, "down", 4, 7, 0, "parcial fondo col1 -> tope col0")
check(3, "right", 4, 7, 6, "parcial fila col0 (fila 3) -> ultimo")
check(2, "right", 4, 7, 6, "parcial fila 2 -> ultimo item (6)")
# 2 columnas cuadradas (filas=3, n=6)
check(0, "up", 3, 6, 5, "cuadrada primero->ultimo")
check(5, "down", 3, 6, 0, "cuadrada ultimo->primero")
check(0, "right", 3, 6, 3, "cuadrada col0->col1")
check(3, "left", 3, 6, 0, "cuadrada col1->col0")
check(2, "right", 3, 6, 5, "cuadrada fila 2 -> col1 fila 2")
# 3 columnas (filas=2, n=6)
check(0, "left", 2, 6, 4, "triple col0 left -> col2")
check(4, "right", 2, 6, 0, "triple col2 right -> col0")
check(0, "up", 2, 6, 5, "triple primero->ultimo")
check(5, "down", 2, 6, 0, "triple ultimo->primero")
check(4, "up", 2, 6, 5, "triple fila0 col2 up -> fila1 col2")
check(5, "up", 2, 6, 4, "triple fila1 col2 up -> fila0 col2")
# 1 columna: left/right no-op
check(2, "left", 5, 5, 2, "col unica left no-op")
check(2, "right", 5, 5, 2, "col unica right no-op")
print("PASS _mover_cursor 42 casos wrap-around")

# ── 3. _menu_seleccion con _leer_tecla mockeado ──────────────────
def run_sel(teclas, opciones, filas=None, numeros=None, es_raiz=False):
    seq = list(teclas)
    menus._leer_tecla = lambda espera=0: (seq.pop(0) if seq else "esc")
    return menus._menu_seleccion(opciones, titulo="T", filas=filas,
                                 numeros=numeros, es_raiz=es_raiz)

opts = [(f"O{i}", f"desc {i}") for i in range(1, 39)]
assert run_sel(["enter"], opts, filas=19) == 0, "enter en primer item -> 0"
assert run_sel(["down", "enter"], opts, filas=19) == 1, "down -> item 1"
assert run_sel(["up", "enter"], opts, filas=19) == 37, "up desde 0 -> ultimo (wrap)"
assert run_sel(["right", "enter"], opts, filas=19) == 19, "right col0 -> col1"
assert run_sel(["right", "up", "enter"], opts, filas=19) == 37, "col1 tope up -> ultimo"
assert run_sel(["1", "9"], opts, filas=19) == 18, "1+9 (enter multi) -> 18" 
assert run_sel(["3", "4", "enter"], opts, filas=19) == 33, "3+4 -> 33"
assert run_sel(["2", "enter"], opts, filas=19) == 1, "2 -> item 1"
assert run_sel(["0", "enter"], opts, filas=19) == 0, "0 en submenu se ignora; enter selecciona"
assert run_sel(["0"], opts, filas=19, es_raiz=True) is None, "0 sin etiqueta se ignora incluso en raiz"
assert run_sel(["R"], opts, filas=19) == "R", "R -> reiniciar"
assert run_sel(["esc"], opts, filas=19) is None, "esc -> cancelar"
assert run_sel(["q"], opts, filas=19) is None, "q -> cancelar"
opts9 = [(f"O{i}", "") for i in range(1, 10)]
assert run_sel(["9"], opts9, filas=5) == 8, "9 items: digito directo -> 8"
assert run_sel(["0"], opts9, filas=5) is None, "0 en menu chico se ignora (no idx -1)"
assert run_sel(["x", "enter"], opts9, filas=5) == 0, "tecla invalida ignorada"
# numeros personalizados (raiz): solo responden los digitos VISIBLES
opts8 = [(f"O{i}", "") for i in range(1, 9)]
numeros_raiz = [str(i) for i in range(1, 8)] + ["R"]
assert run_sel(["R"], opts8, filas=5, numeros=numeros_raiz) == "R", "R visible -> reiniciar"
assert run_sel(["1"], opts8, filas=5, numeros=numeros_raiz) == 0, "digito visible 1 -> idx 0"
assert run_sel(["7"], opts8, filas=5, numeros=numeros_raiz) == 6, "digito visible 7 -> idx 6"
assert run_sel(["8"], opts8, filas=5, numeros=numeros_raiz) is None, "8 sin etiqueta se ignora (no select Reiniciar)"
assert run_sel(["0"], opts8, filas=5, numeros=numeros_raiz) is None, "0 sin etiqueta se ignora"
# render sin duplicar numeros: capturar grid y verificar una sola etiqueta por item
def render_captura(teclas, opciones, filas=None, numeros=None):
    buf = io.StringIO()
    menus.console = type(menus.console)(file=buf, force_terminal=True, width=120, height=50)
    seq = list(teclas)
    menus._leer_tecla = lambda espera=0: (seq.pop(0) if seq else "esc")
    try:
        menus._menu_seleccion(opciones, titulo="T", filas=filas, numeros=numeros)
    except SystemExit:
        pass
    # extraer plain text sin ANSI
    from rich.console import Console as _C
    c2 = _C(file=io.StringIO(), force_terminal=False)
    from rich.text import Text
    t = Text.from_ansi(buf.getvalue())
    return t.plain

txt = render_captura(["enter"], opts8, filas=5, numeros=numeros_raiz)
assert "[ 1] O1" in txt and "[ 1] [1] O1" not in txt, "sin numeros duplicados"
assert "[ R] O8" in txt and "[R] [R] O8" not in txt, "R sin duplicar"
assert "[ 0]" not in txt, "no hay etiqueta 0 en la raiz"
print("PASS _menu_seleccion 17 casos (numeros custom + render sin duplicar)")

# ── 4. E2E: menu_principal recorre todas las secciones ───────────
def fake_prices(ids, *a, **k):
    out = []
    for i in ids:
        out.append({"item_id": i, "city": "Caerleon", "sell_price_min": 100, "quality": 1})
    return out

menus.get_prices = fake_prices
menus.get_history = lambda *a, **k: []
menus.ver_detalle_pez = lambda *a, **k: None
menus._ver_detalle_recurso = lambda *a, **k: None
menus.menu_insumos_pesca = lambda *a, **k: None
menus.menu_pesca = lambda *a, **k: None
menus.ver_recurso = lambda *a, **k: None

# menu_principal: 1..7 cada seccion (los submenus mockeados vuelven solos),
# luego esc -> confirmacion -> enter confirma y sale.
teclas = ["1", "2", "3", "4", "5", "6", "7", "esc", "enter"]
menus._leer_tecla = lambda espera=0: (teclas.pop(0) if teclas else "esc")
menus.limpiar_pantalla = lambda: None
menus.reiniciar = lambda: (_ for _ in ()).throw(SystemExit("reiniciar"))
menus.menu_principal({"pescados": {}})
print("PASS E2E menu_principal secciones 1-7 + salida con confirmacion")

# Esc en la raiz -> confirmacion -> Esc cancela (no sale); R recarga
teclas = ["esc", "esc", "R"]
menus._leer_tecla = lambda espera=0: (teclas.pop(0) if teclas else "esc")
try:
    menus.menu_principal({"pescados": {}})
    raise AssertionError("debia recargar (SystemExit) tras esc-esc-R")
except SystemExit as e:
    assert str(e) == "reiniciar", f"esperaba reiniciar, got {e}"
print("PASS E2E Esc en raiz cancela la salida; R recarga")

# menu_insumos_pesca: 0 en el selector de salsas se IGNORA (sin crash,
# sin volver); Esc vuelve.
cfg_salsas = {"insumos_pesca": {"items": {
    "Salsa de pescado T1": {"id": "SAUCE_FISH_LEVEL1", "receta": {"T1_FISHCHOPS": 2, "T1_SEAWEED": 1}},
    "Salsa de pescado T2": {"id": "SAUCE_FISH_LEVEL2", "receta": {"T1_FISHCHOPS": 2, "T1_SEAWEED": 2}},
    "Salsa de pescado T3": {"id": "SAUCE_FISH_LEVEL3", "receta": {"T1_FISHCHOPS": 2, "T1_SEAWEED": 3}},
}}}
teclas = ["0", "esc"]
menus._leer_tecla = lambda espera=0: (teclas.pop(0) if teclas else "esc")
menus.menu_insumos_pesca(cfg_salsas)
print("PASS menu_insumos_pesca: 0 ignorado en selector de salsas (sin TypeError)")

# ── 5. _pausa_volver: Esc/Enter vuelven, R recarga, invalida se ignora ──
def run_pausa(teclas):
    seq = list(teclas)
    menus._leer_tecla = lambda espera=0: (seq.pop(0) if seq else "esc")
    try:
        menus._pausa_volver()
        return "return"
    except SystemExit:
        return "reiniciar"

assert run_pausa(["esc"]) == "return", "esc -> volver"
assert run_pausa(["enter"]) == "return", "enter -> volver"
assert run_pausa(["x", "esc"]) == "return", "invalida ignorada, esc vuelve"
assert run_pausa(["R"]) == "reiniciar", "R -> reiniciar"
assert run_pausa(["r"]) == "reiniciar", "r minuscula -> reiniciar"
print("PASS _pausa_volver 5 casos")

# ── 6. _confirmar_salida: Enter confirma, Esc cancela, otra se ignora ──
def run_confirma(teclas):
    seq = list(teclas)
    menus._leer_tecla = lambda espera=0: (seq.pop(0) if seq else "esc")
    return menus._confirmar_salida()

assert run_confirma(["enter"]) is True, "enter -> salir"
assert run_confirma(["esc"]) is False, "esc -> cancelar"
assert run_confirma(["x", "enter"]) is True, "invalida ignorada, enter confirma"
assert run_confirma(["x", "esc"]) is False, "invalida ignorada, esc cancela"
print("PASS _confirmar_salida 4 casos")

# ── 7. hint del selector: raiz dice salir, submenu dice volver ──
def render_hint(es_raiz):
    buf = io.StringIO()
    menus.console = type(menus.console)(file=buf, force_terminal=True, width=120, height=50)
    seq = ["esc"]
    menus._leer_tecla = lambda espera=0: (seq.pop(0) if seq else "esc")
    menus._menu_seleccion([("A", "")], titulo="T", es_raiz=es_raiz)
    from rich.text import Text
    return Text.from_ansi(buf.getvalue()).plain

txt_root = render_hint(True)
txt_sub = render_hint(False)
assert "Esc salir" in txt_root and "Esc volver" not in txt_root, "raiz: hint Esc salir"
assert "Esc volver" in txt_sub and "Esc salir" not in txt_sub, "submenu: hint Esc volver"
assert "0/R atajos" not in txt_root and "0/R atajos" not in txt_sub, "sin atajos viejos"
print("PASS hint raiz/submenu")

# ── 8. Diferenciador: navegar NO re-dibuja el frame completo ──
# (seccion 4 parchea limpiar_pantalla para el E2E; restaurar la REAL aqui)

def run_diff(teclas, opciones, titulo="TITULO_X", filas=None):
    buf = io.StringIO()
    menus.console = type(menus.console)(file=buf, force_terminal=True, width=120, height=50)
    menus.limpiar_pantalla = _limpiar_real  # restaurar: el diff necesita el clear real
    seq = list(teclas)
    menus._leer_tecla = lambda espera=0: (seq.pop(0) if seq else "esc")
    menus._menu_seleccion(opciones, titulo=titulo, filas=filas)
    return buf.getvalue()

# al bajar, el titulo NO se re-imprime y solo hay UN clear inicial
raw = run_diff(["down", "esc"], [("Uno", "d1"), ("Dos", "d2")], filas=2)
txt = Text.from_ansi(raw).plain
assert raw.count("\x1b[2J") == 1, "un solo clear (primer frame)"
assert txt.count("TITULO_X") == 1, "el titulo no se re-imprime al navegar"
assert txt.count("d1") == 1 and txt.count("d2") == 1, "descripciones: una vez cada una"
# la barra de seleccion SIEMPRE es cyan (fase de flechas): black-on-cyan
grid_fila0 = raw.split("\n")[2]  # fila 0: "Uno" (seleccionada en el primer frame)
grid_fila1 = raw.split("\n")[3]  # fila 1: "Dos" (NO seleccionada)
assert "\x1b[30;46m" in grid_fila0, "seleccion: barra black-on-cyan"
assert "\x1b[2m" not in grid_fila1, "opcion NO seleccionada: sin dim"
assert "\x1b[30;47m" not in raw, "ya NO hay barra de fondo blanco"
# el segundo frame mueve el cursor: reescribe SOLO las filas del grid
raw2 = run_diff(["down", "esc"], [("Uno", ""), ("Dos", "")], filas=2)
assert "\x1b[4;1H" in raw2, "el segundo frame reescribe la fila del nuevo cursor"
assert "\x1b[3;1H" in raw2, "y la fila anterior (el cursor se movio)"
assert "\x1b[2;1H" not in raw2, "el titulo NUNCA se re-escribe (sin redibujo completo)"
assert "\x1b[30;46m" in raw2, "la barra cyan sigue presente tras navegar"
# con label de tier cyan: la barra SIGUE siendo black-on-cyan (no cambia)
raw3 = run_diff(["esc"], [("[cyan]Azul[/]", ""), ("Dos", "")], filas=2)
assert "\x1b[30;46m" in raw3, "barra siempre cyan aunque el label sea cyan"
# tier oscuro (grey58): la barra NO cae a blanco, sigue cyan
raw4 = run_diff(["esc"], [("[grey58]Gris[/]", ""), ("Dos", "")], filas=2)
assert "\x1b[30;46m" in raw4 and "\x1b[30;47m" not in raw4, "grey58 -> barra cyan, no blanco"
# el [x] no seleccionado lleva el MISMO color que el texto (verde), nunca amarillo
raw5 = run_diff(["esc"], [("[green]A[/]", ""), ("[green]B[/]", "")], filas=2)
lineas5 = raw5.split("\n")  # linea 3 = fila del grid con la opcion NO seleccionada
assert "\x1b[30;46m" in raw5, "barra de seleccion cyan (aunque el label sea verde)"
assert "\x1b[32m" in lineas5[3], "el [x] no seleccionado lleva el color del label (verde)"
assert "\x1b[2;33m" not in lineas5[3], "el [x] de la fila NO seleccionada ya no es amarillo"
# T6 (dark_orange) en truecolor: el LABEL se ve naranja 208, la BARRA sigue cyan
raw6 = run_diff(["down", "esc"], [("[dark_orange]Naranja[/]", ""), ("Dos", "")], filas=2)
# la reescritura de la fila 0 (cursor salio de Naranja) va tras \x1b[3;1H, hasta \x1b[K
r0 = raw6.split("\x1b[3;1H", 1)[1].split("\x1b[K", 1)[0]
assert "\x1b[38;5;208m" in r0, "label T6 no seleccionado = naranja 208, no amarillo"
assert "\x1b[2;33m" not in r0, "T6 en el grid ya NO degrada a amarillo"
raw7 = run_diff(["esc"], [("[dark_orange]Naranja[/]", ""), ("Dos", "")], filas=2)
assert "\x1b[30;46m" in raw7, "barra T6 seleccionada = black-on-cyan (no naranja ni blanco)"
print("PASS diferenciador: solo filas cambiadas se re-escriben (sin parpadeo)")

print("\nTODOS LOS TESTS PASARON")