# menus.py
# ─── Toda la interfaz de usuario (menus, tablas, paneles) ────
# No toca la red directamente: pide precios a api.py y formatea
# con formatting.py. El reinicio usa sys.argv[0] (el script que
# el usuario ejecuto), NO __file__, porque este archivo no es el
# punto de entrada.

import io
import os
import subprocess
import sys
import time
import msvcrt

from rich.console import Console, Group
from rich.control import Control
from rich.segment import Segment
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich import box

from constants import CITIES, COLORES_TIER, REF_MAP, ENCH_NOMBRES, ENCH_COLORS
from api import get_prices, get_history
from formatting import (format_price, _formatear_historial, color_precio, color_item,
                        valores_positivos, mejor_ciudad, pct, color_signo, market_summary)
from textos import RESENAS_MENU, RESENAS_DETALLE, LEYENDA_TIERS, RESENAS_OPCIONES_PRINCIPAL, RESUMEN

console = Console()


def _resena(texto, dim=True, c=None):
    """Muestra una resena de ayuda. dim=True -> gris tenue;
    dim=False -> texto con sus propios colores (leyenda de tiers).
    c=None usa la consola global; pasando `c` se puede renderizar
    a un buffer (para el diferenciador de lineas)."""
    if texto:
        c = c or console
        if dim:
            c.print(f"  [dim]{texto}[/]")
        else:
            c.print(f"  {texto}")
        c.print()


def _panel_resumen(resumen, mostrar_ingrediente=False):
    """Panel informativo con los datos de market_summary.

    Solo datos objetivos (min/max, ingrediente, diferencia refinado - crudo).
    NUNCA recomienda acciones: el usuario decide.
    mostrar_ingrediente=False oculta la linea de ingrediente (ej: recursos,
    que no participan de salsas).
    """
    lineas = []
    if resumen.get("sin_datos"):
        lineas.append(f"  [dim]{RESUMEN['sin_datos']}[/]")
    else:
        min_ciudad = resumen.get("min_ciudad") or ""
        max_ciudad = resumen.get("max_ciudad") or ""
        min_txt = f" ({min_ciudad})" if min_ciudad else ""
        max_txt = f" ({max_ciudad})" if max_ciudad else ""
        lineas.append(f"  {RESUMEN['venta_min']}:  [bold]${format_price(resumen['min_venta'])}[/]{min_txt}")
        lineas.append(f"  {RESUMEN['venta_max']}:  [bold]${format_price(resumen['max_venta'])}[/]{max_txt}")
    if mostrar_ingrediente:
        if resumen.get("es_ingrediente") and resumen.get("recetas"):
            lineas.append(f"  {RESUMEN['ingrediente']}:  [bold]{', '.join(resumen['recetas'])}[/]")
        else:
            lineas.append(f"  [dim]{RESUMEN['no_ingrediente']}[/]")
    if resumen.get("diferencia_refinado") is not None:
        diff = resumen["diferencia_refinado"]
        signo = "+" if diff >= 0 else ""
        lineas.append(f"  {RESUMEN['diferencia']}:  [bold]{signo}{diff:,}[/]")
    if not lineas:
        lineas.append("  [dim]Sin datos de mercado[/]")
    console.print(Panel(
        "\n".join(lineas),
        title=f"[bold]{RESUMEN['titulo']}[/]",
        border_style="green",
        box=box.ROUNDED,
        title_align="left",
    ))


class _RawControl(Control):
    """Control cuyo segment emite exactamente `text` (ANSI crudo).

    Rich solo expone enums (HOME, CLEAR...) y no tiene "erase-down" (\\x1b[J),
    asi que para emitir secuencias crudas hay que construir el segment a mano.
    """

    def __init__(self, text: str) -> None:
        self.segment = Segment(text, None)


# ─── Consola Windows (API nativa, sin ANSI) ────────────────────
if os.name == "nt":
    import ctypes

    class _COORD(ctypes.Structure):
        _fields_ = [("X", ctypes.c_short), ("Y", ctypes.c_short)]

    class _SMALL_RECT(ctypes.Structure):
        _fields_ = [("Left", ctypes.c_short), ("Top", ctypes.c_short),
                    ("Right", ctypes.c_short), ("Bottom", ctypes.c_short)]

    class _CONSOLE_SCREEN_BUFFER_INFO(ctypes.Structure):
        _fields_ = [("dwSize", _COORD), ("dwCursorPosition", _COORD),
                    ("wAttributes", ctypes.c_ushort), ("srWindow", _SMALL_RECT),
                    ("dwMaximumWindowSize", _COORD)]

    _kernel32 = ctypes.windll.kernel32
    _STD_OUTPUT_HANDLE = -11  # STD_OUTPUT_HANDLE
else:
    _kernel32 = None


def _consola_handle():
    """Devuelve el handle de salida de la consola real, o None si no hay."""
    if _kernel32 is None:
        return None
    try:
        h = _kernel32.GetStdHandle(_STD_OUTPUT_HANDLE)
        return h if h != -1 else None
    except Exception:
        return None


def limpiar_pantalla():
    """Limpia la consola completa (API nativa de Windows, sin ANSI).

    Se usa al ENTRAR a una pantalla (menu o detalle). FillConsoleOutputCharacterW
    + SetConsoleCursorPosition es lo que hace `cls` por debajo y funciona en
    consolas legacy (cmd.exe) donde los codigos ANSI no se interpretan solos.
    En Unix/redireccion (sin consola real) cae al ANSI de Rich.
    """
    h = _consola_handle()
    if h is not None:
        try:
            csbi = _CONSOLE_SCREEN_BUFFER_INFO()
            if _kernel32.GetConsoleScreenBufferInfo(h, ctypes.byref(csbi)):
                n = csbi.dwSize.X * csbi.dwSize.Y
                written = ctypes.c_ulong()
                origen = _COORD(0, 0)
                _kernel32.FillConsoleOutputCharacterW(h, ord(" "), n, origen, ctypes.byref(written))
                _kernel32.FillConsoleOutputAttribute(h, csbi.wAttributes, n, origen, ctypes.byref(written))
                if _kernel32.SetConsoleCursorPosition(h, origen):
                    return
        except Exception:
            pass
    console.control(_RawControl("\x1b[2J\x1b[H"))


def _escribir_fila(fila, texto):
    """Escribe UNA linea del frame en su fila (0-based) sin tocar el resto.

    ANSI puro: mueve el cursor a la fila, escribe el texto (que ya trae sus
    colores ANSI del render en buffer) y borra hasta el final de la linea.
    Asi la navegacion no re-dibuja todo el frame: solo las filas que cambiaron.
    """
    console.control(_RawControl(f"\x1b[{fila + 1};1H{texto}\x1b[K"))
    try:
        console.file.flush()
    except Exception:
        pass


def _repintar_diff(lineas, prev):
    """Reescribe SOLO las lineas que cambiaron entre el frame anterior y el nuevo.

    En un menu, por tecla cambian 1-3 filas (la del cursor y la descripcion):
    el resto del frame queda intacto -> cero parpadeo.
    """
    max_ln = max(len(lineas), len(prev))
    for i in range(max_ln):
        nueva = lineas[i] if i < len(lineas) else ""
        vieja = prev[i] if i < len(prev) else ""
        if nueva != vieja:
            _escribir_fila(i, nueva)


def _leer_tecla(espera=0):
    """Lee una tecla sin Enter. Windows: msvcrt.getwch(); Unix: terminal raw.
    espera > 0: modo no bloqueante — devuelve None si no hay tecla en `espera` segundos."""
    if os.name == "nt":
        import msvcrt
        if espera > 0 and not msvcrt.kbhit():
            return None
        ch = msvcrt.getwch()
        if ch in ("\x00", "\xe0"):  # teclas especiales (flechas)
            ch2 = msvcrt.getwch()
            if ch2 == "H":
                return "up"
            elif ch2 == "P":
                return "down"
            elif ch2 == "K":
                return "left"
            elif ch2 == "M":
                return "right"
            else:
                return ""
        elif ch == "\r":
            return "enter"
        elif ch == "\x1b":
            return "esc"
        else:
            return ch
    else:
        # Unix terminal raw (fallback, no probado en este proyecto)
        import tty, termios, select
        fd = sys.stdin.fileno()
        old = termios.tcgetattr(fd)
        tty.setraw(fd)
        try:
            if espera > 0:
                r, _, _ = select.select([sys.stdin], [], [], espera)
                if not r:
                    return None
            ch = sys.stdin.read(1)
            if ch == "\x1b":
                nxt = sys.stdin.read(1)
                if nxt == "[":
                    seq = sys.stdin.read(1)
                    if seq == "A":
                        return "up"
                    elif seq == "B":
                        return "down"
                    elif seq == "D":
                        return "left"
                    elif seq == "C":
                        return "right"
                elif nxt == "O":
                    seq = sys.stdin.read(1)
                    if seq == "H":
                        return "up"
                    elif seq == "P":
                        return "down"
                    elif seq == "K":
                        return "left"
                    elif seq == "M":
                        return "right"
                return "esc"
            elif ch == "\r":
                return "enter"
            else:
                return ch
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old)


def _mover_cursor(cursor, tecla, filas, n):
    """Pura columna-major grid math, con wrap-around (cyclico)."""
    ncol = (n + filas - 1) // filas
    fila, col = cursor % filas, cursor // filas

    if tecla == "up":
        if fila > 0:
            return cursor - 1
        if cursor == 0:
            return n - 1  # primero -> ultimo
        cand = col * filas + (filas - 1)  # tope de columna -> fondo de la misma
        return cand if cand < n else n - 1
    elif tecla == "down":
        if cursor == n - 1:
            return 0  # ultimo -> primero
        if fila < filas - 1:
            return cursor + 1
        return col * filas  # fondo de columna -> tope de la misma
    elif tecla == "left":
        if col > 0:
            return cursor - filas
        cand = (ncol - 1) * filas + fila  # col 0 -> ultima columna
        return cand if cand < n else n - 1
    elif tecla == "right":
        if col < ncol - 1:
            cand = (col + 1) * filas + fila
            if cand < n:
                return cand
            return n - 1  # columna parcial: ultimo item
        return fila  # ultima columna -> col 0, misma fila
    else:
        return cursor


def _menu_seleccion(opciones, titulo="", filas=None, texto_bajo="", numeros=None, es_raiz=False):
    """Selector numerado con flechas.

    opciones: lista de (label, desc) — label con markup Rich, desc resena
    contextual de la opcion (puede ser "").
    filas None -> una sola columna. Con filas se usa grid column-major
    (item = columna * filas + fila), igual que el reparto de la lista.
    numeros: lista opcional con la etiqueta a mostrar por opcion (ej:
    ["1","2","R"]). Por defecto numera 1..n. Solo responden los DIGITOS
    que se muestran como etiqueta; un digito no visible se ignora (evita
    atajos ocultos que parecen bugs). Con numeros no hay acumulacion de
    digitos multiples.
    Devuelve int (indice 0-based), "R" (reiniciar) o None (esc/q = cancelar).
    es_raiz=True -> el hint dice "Esc salir"; False -> "Esc volver".
    """
    n = len(opciones)
    if filas is None:
        filas = n
    filas = max(1, min(filas, n))
    ncol = (n + filas - 1) // filas
    ncolw = max(len(str(n)), 2)
    cursor = 0
    digitos = ""  # acumula numeros de 2 digitos (ej: "34")
    # Con numeros custom solo responden los DIGITOS visibles como etiqueta;
    # un digito no mostrado (ej: 8/9/0 sin etiqueta) se ignora: evita atajos
    # ocultos que parecen bugs. Sin numeros, la numeracion es posicional 1..n.
    atajos_digitos = None
    if numeros is not None:
        atajos_digitos = {etiq: i for i, etiq in enumerate(numeros) if etiq.isdigit()}

    # Color y texto plano de cada label, computados UNA vez (no cambian).
    # El numero [ x] lleva el MISMO color que el texto de su opcion.
    _labels = []
    for label, _ in opciones:
        t = console.render_str(label)
        segs = list(t.render(console))
        col = None
        if segs:
            st = segs[0].style
            col = st.color.name if (st and st.color) else None
        _labels.append((col, t.plain))

    def render_grid(c=None):
        c = c or console
        celdas = [[""] * ncol for _ in range(filas)]
        cursor_celda = None  # (r, c_, contenido_plain_sin_pad, bg) de la seleccion
        for r in range(filas):
            for c_ in range(ncol):
                idx = c_ * filas + r
                if idx >= n:
                    break
                label, _ = opciones[idx]
                etiqueta = str(idx + 1 if numeros is None else numeros[idx])
                col, plain = _labels[idx]
                numero = (f"[{col}][{etiqueta:>{ncolw}}][/]" if col
                          else f"[{etiqueta:>{ncolw}}]")
                if idx == cursor:
                    # barra de seleccion: numero y texto en NEGRO sobre CYAN
                    # (estilo de la fase de navegacion por flechas).
                    cursor_celda = (r, c_, f"  [{etiqueta:>{ncolw}}] {plain}", "cyan")
                else:
                    celdas[r][c_] = f"  {numero} {label}"
        # alinear cada columna a su ancho maximo (incluyendo la seleccion)
        anchos = {}
        for c_ in range(ncol):
            w_list = ([len(cursor_celda[2])] if (cursor_celda and cursor_celda[1] == c_) else [])
            w_list += [len(Text.from_markup(celdas[r][c_]).plain)
                       for r in range(filas) if celdas[r][c_]]
            anchos[c_] = max(w_list) if w_list else 0
        for c_ in range(ncol):
            for r in range(filas):
                if celdas[r][c_]:
                    celdas[r][c_] += " " * (anchos[c_] - len(Text.from_markup(celdas[r][c_]).plain))
        if cursor_celda is not None:
            r, c_, contenido, bg = cursor_celda
            # el padding va DENTRO de la barra para que el fondo cubra todo
            celdas[r][c_] = f"[black on {bg}]{contenido.ljust(anchos[c_])}[/]"
        for r in range(filas):
            fila_txt = [celdas[r][c_] for c_ in range(ncol) if celdas[r][c_]]
            c.print("    ".join(fila_txt))

    def footer(c=None):
        c = c or console
        # La linea de descripcion SIEMPRE se reserva (aunque este vacia)
        # para que la pantalla no cambie de altura al navegar.
        _, desc = opciones[cursor]
        c.print(f"  [dim]{desc}[/]" if desc else "")
        if texto_bajo:
            if isinstance(texto_bajo, str):
                _resena(texto_bajo, dim=True, c=c)
            else:
                for item in texto_bajo:
                    if isinstance(item, tuple):
                        txt, dim = item
                        _resena(txt, dim=dim, c=c)
                    else:
                        _resena(item, dim=True, c=c)
        col_hint = "Izq/Der columna · " if ncol > 1 else ""
        esc_tecla, esc_accion = ("Esc", "salir") if es_raiz else ("Esc", "volver")
        c.print(f"  [dim]{col_hint}Arriba/Abajo mover · [yellow]Enter[/] elegir · [yellow]{esc_tecla}[/] {esc_accion} · [yellow]R[/] recargar")

    primera = True
    lineas_prev = None
    while True:
        # ── Renderizar el frame completo en un buffer (misma logica visual) ──
        ancho = console.width if console.width else 120
        alto = console.height if console.height else 50
        buf = io.StringIO()
        # highlight=False: Rich NO pinta los numeros en bold-cyan (repr.number).
        # color_system="truecolor": si se detecta "windows"/"standard" (16 colores,
        # como hace Rich sobre un buffer StringIO) los colores 8-bit (dark_orange,
        # grey58) degradan a amarillo/gris apagado. Windows 10+ soporta VT 24-bit,
        # asi que forzamos truecolor para que T6 se vea naranja de verdad.
        fc = Console(file=buf, force_terminal=True, width=ancho, height=alto,
                     highlight=False, color_system="truecolor")
        fc.print(titulo)
        fc.print()
        render_grid(fc)
        fc.print()
        footer(fc)
        lineas = buf.getvalue().split("\n")
        while lineas and lineas[-1] == "":
            lineas.pop()

        if primera or lineas_prev is None or len(lineas) > alto:
            # primer frame (o frame mas alto que la terminal): redibujo completo
            limpiar_pantalla()
            console.control(_RawControl("\n".join(lineas) + "\n"))
            try:
                console.file.flush()
            except Exception:
                pass
            primera = False
        else:
            # navegacion: reescribir solo las filas que cambiaron (sin parpadeo)
            _repintar_diff(lineas, lineas_prev)
        lineas_prev = lineas

        tecla = _leer_tecla()
        if tecla is None:
            continue
        elif tecla == "esc" or tecla.lower() == "q":
            return None
        elif tecla == "enter":
            if digitos:
                num = int(digitos)
                digitos = ""
                if 1 <= num <= n:
                    return num - 1
            else:
                return cursor
        elif tecla in ("up", "down", "left", "right"):
            digitos = ""
            cursor = _mover_cursor(cursor, tecla, filas, n)
        elif tecla.upper() == "R":
            return "R"
        elif tecla.isdigit():
            if atajos_digitos is not None:
                # solo responden los digitos que se VEN como etiqueta
                if tecla in atajos_digitos:
                    return atajos_digitos[tecla]
                continue  # digito no visible -> ignorado (no parecer bug)
            if tecla == "0":
                continue  # 0 nunca es item valido; se ignora sin consumir la siguiente tecla
            # numero directo; con n>9 acumula digitos (ej: "34") con timeout
            if n > 9:
                digitos += tecla
                while len(digitos) < len(str(n)):
                    t2 = _leer_tecla(espera=0.6)
                    if t2 is None or not t2.isdigit():
                        break
                    digitos += t2
                if 1 <= int(digitos) <= n:
                    return int(digitos) - 1
                digitos = ""
            else:
                return int(tecla) - 1
        # otras teclas: ignorar y re-render


# ─── Colores por Tier ─────────────────────────────────────────
def info_tier(item_id):
    """Extrae el tier del item_id y devuelve (tier_str, color_rich)."""
    tier = item_id.split("_")[0][1:]  # "T4_FISH..." → "4"
    color = COLORES_TIER.get(tier, "white")
    return tier, color


# ─── Reinicio ─────────────────────────────────────────────────
def reiniciar():
    """Relanza la app completa (recarga albion_config.json en frio).

    Usa sys.argv[0] (el script que el usuario ejecuto), NO __file__,
    porque este archivo no es el punto de entrada. El proceso hijo
    hereda la consola del padre, asi que no se abre una ventana nueva.
    """
    subprocess.Popen([sys.executable, sys.argv[0]])
    sys.exit(0)


def _pausa_volver():
    """Pantallas de detalle: espera UNA tecla sin prompt de texto.
    Esc/Enter -> vuelve al listado; R -> recarga la app; el resto se ignora."""
    while True:
        tecla = _leer_tecla()
        if tecla in ("esc", "enter"):
            return
        if tecla is not None and tecla.upper() == "R":
            reiniciar()


def _confirmar_salida():
    """Raiz: pide confirmacion antes de salir. Enter confirma, Esc cancela."""
    while True:
        tecla = _leer_tecla()
        if tecla == "enter":
            return True
        if tecla == "esc":
            return False


# ─── Menu Principal ───────────────────────────────────────────
def menu_principal(config):
    nombres = ["Pesca", "Fibra", "Madera", "Cuero", "Mineral", "Piedra", "Salsas de pescado"]
    while True:
        panel = Panel(
            "[dim]Elige una seccion con los numeros (1-7) o con las flechas + Enter.[/]",
            title="[bold cyan]Albion Helper[/]",
            subtitle="[cyan]Consulta de mercado[/]",
            border_style="cyan",
            box=box.HEAVY,
        )
        opciones = []
        for i, nombre in enumerate(nombres, start=1):
            opciones.append((nombre, RESENAS_OPCIONES_PRINCIPAL[i]))

        # Reiniciar NO es un item del menu: la tecla R ya recarga desde
        # cualquier pantalla (lo dice el hint), un item visible seria duplicar.
        idx = _menu_seleccion(opciones, titulo=panel, texto_bajo=RESENAS_MENU["principal"],
                              es_raiz=True)

        if idx == "R":
            reiniciar()
        elif idx is None:
            console.print("\n[bold yellow]¿Salir? [Enter] Confirmar · [Esc] Cancelar[/]")
            if _confirmar_salida():
                console.print("\n[bold green]Que la plata te sobre![/]")
                break
        elif 0 <= idx <= 6:
            seccion = idx + 1
            if seccion == 1:
                menu_pesca(config)
            elif seccion == 2:
                ver_recurso(config, "fibra")
            elif seccion == 3:
                ver_recurso(config, "madera")
            elif seccion == 4:
                ver_recurso(config, "cuero")
            elif seccion == 5:
                ver_recurso(config, "mineral")
            elif seccion == 6:
                ver_recurso(config, "piedra")
            elif seccion == 7:
                menu_insumos_pesca(config)


# ─── Pesca ────────────────────────────────────────────────────
def menu_pesca(config):
    raw = config["pescados"]
    peces = []
    for nombre, info in raw.items():
        if nombre.startswith("_"):
            continue
        peces.append((nombre, info["id"], info["trozos"], info.get("tipo", "comun")))

    titulo = Panel(f"[bold]Seleccione un pez para ver detalle[/]", border_style="blue", box=box.ROUNDED)
    while True:
        opciones = []
        for nombre, item_id, _, _ in peces:
            _, color = info_tier(item_id)
            opciones.append((f"[{color}]{nombre}[/]", ""))
        idx = _menu_seleccion(opciones, titulo=titulo, filas=(len(peces) + 1) // 2,
                              texto_bajo=[RESENAS_MENU["pesca"], (LEYENDA_TIERS, False)])
        if idx is None:
            return
        elif idx == "R":
            reiniciar()
        else:
            nombre, item_id, trozos, tipo = peces[idx]
            ver_detalle_pez(nombre, item_id, trozos, tipo, config)

def ver_detalle_pez(nombre, item_id, trozos, tipo, config=None):
    limpiar_pantalla()
    tier, color = info_tier(item_id)
    tipo_txt = "Raro" if tipo == "raro" else "Comun"
    tag = f"[bold {color}]T{tier} {tipo_txt}[/]"
    console.print(f"\n[bold cyan]>>> {nombre}[/]")
    console.print(f"[dim]{tag}  —  {trozos} trozos al picar[/]")
    console.print()
    _resena(RESENAS_DETALLE["pez"])

    raw_data = get_prices([item_id, "T1_FISHCHOPS"])
    if not raw_data:
        console.print("  [yellow][Esc][/] Volver · [yellow][R][/] Recargar")
        _pausa_volver()
        return

    prices = {}
    for entry in raw_data:
        # Solo precios de calidad normal (1): el helper compara el item base.
        if entry.get("quality", 1) != 1:
            continue
        item = entry["item_id"]
        city = entry["city"]
        if item not in prices:
            prices[item] = {}
        prices[item][city] = entry.get("sell_price_min", 0)

    fish_prices = prices.get(item_id, {})
    chops_prices = prices.get("T1_FISHCHOPS", {})

    # ─── Recopilar precios por ciudad ──────────────────────────
    precios = {}  # city -> (entero, picado)
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

    tbl = Table(box=box.ROUNDED)
    tbl.add_column("Ciudad", style="cyan")
    tbl.add_column("Entero", justify="right")
    tbl.add_column("Picado", justify="right")
    for city in CITIES:
        e, p = precios[city]
        tbl.add_row(city, color_precio(e, max_entero, min_entero), color_precio(p, max_picado, min_picado))
    console.print(tbl)

    # ─── Historial 7d (si disponible) ───────────────────────────
    console.print()
    console.print("[dim]Consultando historial de mercado...[/]")
    hist_entero = get_history(item_id)
    time.sleep(0.5)
    hist_trozos = get_history("T1_FISHCHOPS")

    vol_entero_total = sum(h["volumen"] for h in hist_entero.values())
    vol_trozos_total = sum(h["volumen"] for h in hist_trozos.values())

    if vol_entero_total > 0 or vol_trozos_total > 0:
        hist_parts = []
        if vol_entero_total > 0:
            hist_parts += _formatear_historial(hist_entero, "Entero")
        if vol_trozos_total > 0:
            hist_parts += _formatear_historial(hist_trozos, "Picado", "trozos")
        console.print(Panel(
            "\n".join(hist_parts),
            title="[bold]Volumen 7 dias[/]",
            border_style="cyan",
            box=box.ROUNDED,
            title_align="left",
        ))

    # ─── Resumen de mercado (informativo, sin recomendaciones) ──
    recetas_config = None
    if config:
        recetas_config = config.get("insumos_pesca", {}).get("items", {})
    resumen = market_summary(prices, item_id, recetas_config)
    console.print()
    _panel_resumen(resumen, mostrar_ingrediente=recetas_config is not None)
    console.print("  [yellow][Esc][/] Volver · [yellow][R][/] Recargar")
    _pausa_volver()


# ─── Recursos ─────────────────────────────────────────────────
def ver_recurso(config, tipo):
    info = config["recursos"].get(tipo)
    if not info:
        console.print(f"\n[red][!] Tipo de recurso '{tipo}' no encontrado.[/]")
        return

    nombre_recurso = info.get("nombre", tipo.upper())
    tiers = info["tiers"]
    tiers_ordenados = sorted(tiers.keys(), key=lambda t: int(t[1:]))

    # Menu: T2/T3 = una entrada cada uno; T4+ = crudo + refinado separados
    menu_items = []
    for tk in tiers_ordenados:
        td = tiers[tk]
        tier_num = int(tk[1:])
        if tier_num <= 3:
            nombre_item = td.get("nombre", f"{nombre_recurso} {tk}")
            menu_items.append({"label": f"{nombre_item} {tk}", "tier_key": tk, "modo": "todo"})
        else:
            crudo_name = td.get("nombre", f"{nombre_recurso} {tk}")
            ref_label = td["refinado"].split("_", 1)[1].title()
            ref_esp = REF_MAP.get(ref_label, ref_label)
            ref_name = td.get("refinado_nombre", ref_esp)
            menu_items.append({"label": f"{crudo_name} {tk}", "tier_key": tk, "modo": "crudo"})
            menu_items.append({"label": f"{ref_name} {tk}", "tier_key": tk, "modo": "refinado"})

    titulo = Panel(f"[bold]{nombre_recurso}[/]", border_style="blue", box=box.ROUNDED)
    while True:
        opciones = []
        for item in menu_items:
            tier_num = item["tier_key"][1:]
            color = COLORES_TIER.get(tier_num, "white")
            opciones.append((f"[{color}]{item['label']}[/]", ""))
        idx = _menu_seleccion(opciones, titulo=titulo, filas=(len(menu_items) + 1) // 2,
                              texto_bajo=[RESENAS_MENU["recursos"], (LEYENDA_TIERS, False)])
        if idx is None:
            return
        elif idx == "R":
            reiniciar()
        else:
            item = menu_items[idx]
            _ver_detalle_recurso(nombre_recurso, item["tier_key"], tiers[item["tier_key"]], modo=item["modo"])

def _linea_mayor_menor(nombre_mk, vals):
    """Una linea del panel de observacion: precio MAYOR y MENOR de una
    variante, cada uno con su ciudad (datos objetivos, sin recomendaciones).

    nombre_mk: nombre ya formateado (color de tier o de encantamiento).
    vals: {ciudad: precio} con solo valores > 0 (debe estar no vacio).
    Si mayor y menor caen en la misma ciudad, muestra una sola entrada.
    """
    c_max, p_max = mejor_ciudad(vals)
    c_min, p_min = mejor_ciudad(vals, "min")
    if c_max == c_min:
        return f"  {nombre_mk}: [bold]{c_max}[/] ${p_max:,} (mayor)"
    return (f"  {nombre_mk}: [bold]{c_max}[/] ${p_max:,} (mayor)"
            f" · [bold]{c_min}[/] ${p_min:,} (menor)")


def _ver_detalle_recurso(nombre, tier_key, tier_data, modo="todo"):
    limpiar_pantalla()
    crudo_id = tier_data["crudo"]
    refinado_id = tier_data["refinado"]
    nombre_real = tier_data.get("nombre", f"{nombre} {tier_key}")
    ref_label = refinado_id.split("_", 1)[1].title()
    ref_esp = REF_MAP.get(ref_label, ref_label)
    ref_nombre = tier_data.get("refinado_nombre", ref_esp)

    # Titulo segun modo
    if modo == "crudo":
        titulo_item = nombre_real
    elif modo == "refinado":
        titulo_item = ref_nombre
    else:
        titulo_item = f"{nombre_real} -> {ref_nombre}"
    console.print(f"\n[bold cyan]>>> {titulo_item} {tier_key}[/]")
    console.print()
    _resena(RESENAS_DETALLE["recurso"])

    # IDs de items encantados
    ench_ids = [f"{crudo_id}_LEVEL{i}@{i}" for i in range(1, 5)]
    ref_ench_ids = [f"{refinado_id}_LEVEL{i}@{i}" for i in range(1, 5)]

    # Buscar precios (solo lo necesario segun modo)
    if modo == "crudo":
        item_ids = [crudo_id] + ench_ids
    elif modo == "refinado":
        item_ids = [crudo_id, refinado_id] + ref_ench_ids
    else:
        item_ids = [crudo_id] + ench_ids + [refinado_id] + ref_ench_ids

    raw_data = get_prices(item_ids)
    if not raw_data:
        console.print("  [yellow][Esc][/] Volver · [yellow][R][/] Recargar")
        _pausa_volver()
        return

    prices_map = {}
    for entry in raw_data:
        # Solo precios de calidad normal (1): el helper compara el item base.
        if entry.get("quality", 1) != 1:
            continue
        prices_map.setdefault(entry["item_id"], {})[entry["city"]] = entry.get("sell_price_min", 0)

    # ═══════════════ TABLA ═══════════════
    if modo == "crudo" or modo == "todo":
        planos = {c: prices_map.get(crudo_id, {}).get(c, 0) for c in CITIES if prices_map.get(crudo_id, {}).get(c, 0) > 0}
        tbl = Table(box=box.ROUNDED)
        tbl.add_column("Ciudad", style="cyan")
        tbl.add_column(nombre_real, justify="right")
        for e in (".1", ".2", ".3", ".4"):
            tbl.add_column(e, justify="right")

        for city in CITIES:
            row = [city]
            plano = prices_map.get(crudo_id, {}).get(city, 0)
            row.append(color_item(plano, planos.values()))
            for i in range(4):
                eid = ench_ids[i]
                val = prices_map.get(eid, {}).get(city, 0)
                vals = [prices_map.get(ench_ids[i], {}).get(c, 0) for c in CITIES if prices_map.get(ench_ids[i], {}).get(c, 0) > 0]
                row.append(color_item(val, vals))
            tbl.add_row(*row)
        console.print(tbl)

    if modo == "refinado" or modo == "todo":
        if modo != "crudo":
            console.print()
        refs = {c: prices_map.get(refinado_id, {}).get(c, 0) for c in CITIES if prices_map.get(refinado_id, {}).get(c, 0) > 0}
        tbl = Table(box=box.ROUNDED)
        tbl.add_column("Ciudad", style="cyan")
        tbl.add_column(ref_nombre, justify="right")
        for e in (".1", ".2", ".3", ".4"):
            tbl.add_column(e, justify="right")
        tbl.add_column("Dif", justify="right")

        for city in CITIES:
            row = [city]
            ref = prices_map.get(refinado_id, {}).get(city, 0)
            row.append(color_item(ref, refs.values()))
            for i in range(4):
                eid = ref_ench_ids[i]
                val = prices_map.get(eid, {}).get(city, 0)
                vals = [prices_map.get(ref_ench_ids[i], {}).get(c, 0) for c in CITIES if prices_map.get(ref_ench_ids[i], {}).get(c, 0) > 0]
                row.append(color_item(val, vals))
            # Dif: ref base vs plano base (solo si tenemos ambos datos)
            diff = ""
            plano_p = prices_map.get(crudo_id, {}).get(city, 0)
            if ref > 0 and plano_p > 0:
                gan = ref - plano_p
                diff = f"[{color_signo(gan)}]{gan:+,}[/]"
            row.append(diff)
            tbl.add_row(*row)
        console.print(tbl)

    # ═══════════════ HISTORIAL 7 DIAS ═══════════════
    console.print()
    console.print("[dim]Consultando historial de mercado...[/]")
    hist_parts = []
    if modo == "crudo" or modo == "todo":
        hist_crudo = get_history(crudo_id)
        if sum(h["volumen"] for h in hist_crudo.values()) > 0:
            hist_parts += _formatear_historial(hist_crudo, nombre_real)
        time.sleep(0.5)
    if modo == "refinado" or modo == "todo":
        hist_ref = get_history(refinado_id)
        if sum(h["volumen"] for h in hist_ref.values()) > 0:
            hist_parts += _formatear_historial(hist_ref, ref_nombre)
    if hist_parts:
        console.print(Panel(
            "\n".join(hist_parts),
            title="[bold]Volumen 7 dias[/]",
            border_style="cyan",
            box=box.ROUNDED,
            title_align="left",
        ))

    # ═══════════════ PANEL DE OBSERVACION ═══════════════
    console.print()

    lineas = []
    # Nivel 0
    if modo == "crudo" or modo == "todo":
        crudo_vals = {c: prices_map.get(crudo_id, {}).get(c, 0) for c in CITIES if prices_map.get(crudo_id, {}).get(c, 0) > 0}
        if crudo_vals:
            lineas.append(_linea_mayor_menor(nombre_real, crudo_vals))
    if modo == "refinado" or modo == "todo":
        ref_vals = {c: prices_map.get(refinado_id, {}).get(c, 0) for c in CITIES if prices_map.get(refinado_id, {}).get(c, 0) > 0}
        if ref_vals:
            lineas.append(_linea_mayor_menor(ref_nombre, ref_vals))

    # Niveles 1-4
    for i in range(4):
        mostrar_crudo = (modo == "crudo" or modo == "todo")
        mostrar_ref = (modo == "refinado" or modo == "todo")

        ench_vals = {}
        ref_ench_vals = {}
        if mostrar_crudo:
            ench_vals = {c: prices_map.get(ench_ids[i], {}).get(c, 0) for c in CITIES if prices_map.get(ench_ids[i], {}).get(c, 0) > 0}
        if mostrar_ref:
            ref_ench_vals = {c: prices_map.get(ref_ench_ids[i], {}).get(c, 0) for c in CITIES if prices_map.get(ref_ench_ids[i], {}).get(c, 0) > 0}

        if not ench_vals and not ref_ench_vals:
            continue

        enc_nombre = ENCH_NOMBRES[i + 1]
        enc_color = ENCH_COLORS[i + 1]
        lineas.append("")
        if ench_vals:
            lineas.append(_linea_mayor_menor(f"[{enc_color}]{nombre_real} {enc_nombre}[/]", ench_vals))
        if ref_ench_vals:
            lineas.append(_linea_mayor_menor(f"[{enc_color}]{ref_nombre} {enc_nombre}[/]", ref_ench_vals))

    if not lineas:
        txt = "  [dim]Sin datos de precios.[/]"
    else:
        txt = "\n".join(lineas).rstrip()

    console.print(Panel(txt, title="[bold]Precio mayor y menor por ciudad[/]", border_style="green", box=box.HEAVY, title_align="left"))

    # ─── Resumen de mercado (informativo, sin recomendaciones) ──
    # En modo crudo no hay par crudo/refinado en precios ->
    # diferencia_refinado queda en None (no se muestra).
    item_vista = refinado_id if modo == "refinado" else crudo_id
    resumen = market_summary(prices_map, item_vista)
    console.print()
    _panel_resumen(resumen)
    console.print("  [yellow][Esc][/] Volver · [yellow][R][/] Recargar")
    _pausa_volver()


# ─── Salsas de pescado ────────────────────────────────────────
def menu_insumos_pesca(config):
    info = config.get("insumos_pesca")
    if not info:
        console.print("\n[red][!] Seccion no encontrada.[/]")
        return

    salsas = [(nombre, d["id"], d.get("receta", {}))
              for nombre, d in info["items"].items() if "Salsa" in nombre]

    salsa_ids = [s[1] for s in salsas]
    fetch_ids = ["T1_FISHCHOPS", "T1_SEAWEED"] + salsa_ids
    raw_data = get_prices(fetch_ids)

    if not raw_data:
        limpiar_pantalla()
        console.print("\n[bold cyan]>>> Salsas de pescado[/]\n")
        console.print("  [red][!] Sin datos de mercado[/]")
        console.print("\n  [yellow][Esc][/] Volver · [yellow][R][/] Recargar")
        _pausa_volver()
        return

    # Agrupar por item_id
    precios_grp = {}
    for entry in raw_data:
        # Solo precios de calidad normal (1): el helper compara el item base.
        if entry.get("quality", 1) != 1:
            continue
        precios_grp.setdefault(entry["item_id"], {})[entry["city"]] = entry.get("sell_price_min", 0)

    alga_px = precios_grp.get("T1_SEAWEED", {})
    carne_px = precios_grp.get("T1_FISHCHOPS", {})

    # Mejores precios ingredientes para extra (comprar no aplica: usamos venta)
    _, carne_max_vta = mejor_ciudad(carne_px)
    _, alga_max_vta = mejor_ciudad(alga_px)

    # Tabla combinada
    tbl = Table(box=box.ROUNDED)
    tbl.add_column("Ciudad", style="cyan")
    for nombre, sid, _ in salsas:
        nivel = int(sid.split("_LEVEL")[-1])
        color = ENCH_COLORS[nivel]
        nombre_corto = nombre.replace("Salsa ", "")
        tbl.add_column(f"[{color}]{nombre_corto}[/]", justify="right")

    for city in CITIES:
        row = [city]
        for _, sid, _ in salsas:
            prices = precios_grp.get(sid, {})
            val = prices.get(city, 0)
            col_vals = [v for v in prices.values() if v > 0]
            if val == 0:
                row.append("[dim]N/D[/]")
            elif not col_vals:
                row.append(f"${format_price(val)}")
            else:
                if val == max(col_vals):
                    row.append(f"[bold green]${format_price(val)}[/]")
                elif val == min(col_vals):
                    row.append(f"[red]${format_price(val)}[/]")
                else:
                    row.append(f"${format_price(val)}")
        tbl.add_row(*row)

    # Info por salsa en grid: salsa | receta | ciudad + precio + extra
    grid = Table.grid(padding=(0, 3))
    grid.add_column(no_wrap=True)
    grid.add_column(no_wrap=True)
    grid.add_column(no_wrap=True)
    for nombre, sid, receta in salsas:
        nivel = int(sid.split("_LEVEL")[-1])
        color = ENCH_COLORS[nivel]
        nombre_corto = nombre.replace("Salsa ", "")

        salsa_px = precios_grp.get(sid, {})
        salsa_vals = valores_positivos(salsa_px)
        if not salsa_vals:
            continue

        ciudad_venta, mejor_venta = mejor_ciudad(salsa_px)

        cant_carne = receta.get("T1_FISHCHOPS", 0)
        cant_alga = receta.get("T1_SEAWEED", 0)

        valor_insumos = carne_max_vta * cant_carne + alga_max_vta * cant_alga
        extra = mejor_venta - valor_insumos if valor_insumos > 0 else 0
        pct_extra = pct(extra, valor_insumos)

        grid.add_row(
            f"[{color}]{nombre_corto}[/]",
            f"{cant_carne} Carne + {cant_alga} Alga",
            f"[bold]{ciudad_venta}[/] ${mejor_venta:,}  (extra +${extra:,}, {pct_extra:.1f}%)",
        )

    # ── Volumen 7 dias en grid: salsa | total | top ciudad ──
    console.print("[dim]Consultando historial...[/]")
    hist_data = get_history(salsa_ids)
    vol_grid = Table.grid(padding=(0, 3))
    vol_grid.add_column(no_wrap=True)
    vol_grid.add_column(no_wrap=True)
    vol_grid.add_column(no_wrap=True)
    hay_vol = False
    for nombre, sid, _ in salsas:
        hist = hist_data.get(sid, {})
        vol_total = sum(h["volumen"] for h in hist.values())
        if vol_total > 0:
            hay_vol = True
            nivel = int(sid.split("_LEVEL")[-1])
            color = ENCH_COLORS[nivel]
            nombre_corto = nombre.replace("Salsa ", "")
            top = sorted(hist, key=lambda c: hist[c]["volumen"], reverse=True)[0]
            vol_grid.add_row(
                f"[{color}]{nombre_corto}[/]",
                f"[bold]{vol_total:,}[/] uds",
                f"{top}: {hist[top]['volumen']:,}",
            )
    vol_panel = (Panel(vol_grid, title="[bold]Volumen 7 dias[/]", border_style="cyan",
                       box=box.ROUNDED, title_align="left") if hay_vol
                 else Text("  [dim]Sin datos de historial[/]"))

    # Selector: la vista de mercado es el titulo; las salsas, las opciones
    while True:
        opciones = []
        for nombre, sid, receta in salsas:
            nivel = int(sid.split("_LEVEL")[-1])
            color = ENCH_COLORS[nivel]
            cant_carne = receta.get("T1_FISHCHOPS", 0)
            cant_alga = receta.get("T1_SEAWEED", 0)
            opciones.append((f"[{color}]{nombre}[/]", f"{cant_carne} Carne + {cant_alga} Alga"))

        titulo = Group(
            Panel("[bold cyan]Salsas de pescado[/]", border_style="cyan"),
            tbl,
            grid,
            vol_panel,
        )

        idx = _menu_seleccion(opciones, titulo=titulo, texto_bajo=RESENAS_MENU["insumos"])

        if idx is None:
            return
        elif idx == "R":
            reiniciar()
        else:
            nombre, sid, _ = salsas[idx]
            ver_detalle_insumo(nombre, sid, config)


def _acortar_nombre(nombre):
    """Abrevia nombres para columnas: 'Carne de pescado' -> 'Carne', 'Algas' -> 'Alga'."""
    if nombre.startswith("Carne de"):
        return "Carne"
    if nombre.endswith("s") and len(nombre) > 3:
        return nombre[:-1]
    return nombre


def _id_a_nombre(config):
    """Construye mapa: item_id -> nombre español desde pescados e insumos."""
    m = {}
    for seccion_key in ("pescados", "insumos_pesca"):
        seccion = config.get(seccion_key, {})
        if seccion_key == "insumos_pesca":
            seccion = seccion.get("items", {})
        for nom, data in seccion.items():
            if isinstance(data, dict) and "id" in data:
                m[data["id"]] = nom
    return m


def _tabla_insumos(filas):
    """Tabla de insumos: Recurso | Cant. | Ciudad | Precio c/u | Total."""
    t = Table(box=box.ROUNDED, show_edge=False, padding=(0, 1))
    t.add_column("Recurso", style="cyan")
    t.add_column("Cant.", justify="right")
    t.add_column("Ciudad")
    t.add_column("Precio c/u", justify="right")
    t.add_column("Total", justify="right")
    for rec, cant, ciudad, pu, total in filas:
        if total > 0:
            t.add_row(rec, str(cant), f"[bold]{ciudad}[/]", f"${pu:,}", f"[bold green]${total:,}[/]")
        else:
            t.add_row(rec, str(cant), "[dim]N/D[/]", "[dim]N/D[/]", "[dim]sin datos[/]")
    return t


def ver_detalle_insumo(nombre, item_id, config):
    limpiar_pantalla()
    console.print(f"\n[bold cyan]>>> {nombre}[/]")
    console.print()
    _resena(RESENAS_DETALLE["insumo"])

    id_to_nombre = _id_a_nombre(config)

    # Buscar receta en config
    receta = None
    for item_data in config.get("insumos_pesca", {}).get("items", {}).values():
        if isinstance(item_data, dict) and item_data.get("id") == item_id and "receta" in item_data:
            receta = item_data["receta"]
            break

    # IDs a consultar: salsa + ingredientes
    fetch_ids = [item_id]
    if receta:
        fetch_ids.extend(receta.keys())

    raw_data = get_prices(fetch_ids)
    if not raw_data:
        console.print("  [yellow][Esc][/] Volver · [yellow][R][/] Recargar")
        _pausa_volver()
        return

    # Agrupar precios por item_id
    precios_grp = {}
    for entry in raw_data:
        # Solo precios de calidad normal (1): el helper compara el item base.
        if entry.get("quality", 1) != 1:
            continue
        iid = entry["item_id"]
        precios_grp.setdefault(iid, {})[entry["city"]] = entry.get("sell_price_min", 0)

    salsa_prices = precios_grp.get(item_id, {})

    # ── Tabla combinada: Ciudad | Alga | Carne | Venta ──
    tbl = Table(box=box.ROUNDED)
    tbl.add_column("Ciudad", style="cyan")

    cols_info = []  # [(titulo_columna, dict_precios_por_ciudad)]
    if receta:
        for ing_id in sorted(receta.keys(), key=lambda i: id_to_nombre.get(i, i)):
            col_title = _acortar_nombre(id_to_nombre.get(ing_id, ing_id))
            cols_info.append((col_title, precios_grp.get(ing_id, {})))
    cols_info.append(("Venta", salsa_prices))

    for title, _ in cols_info:
        tbl.add_column(title, justify="right")

    for city in CITIES:
        row = [city]
        for _, data in cols_info:
            val = data.get(city, 0)
            col_vals = [v for v in data.values() if v > 0]
            if val == 0:
                row.append("[dim]N/D[/]")
            elif not col_vals:
                row.append(f"${format_price(val)}")
            else:
                if val == max(col_vals):
                    row.append(f"[bold green]${format_price(val)}[/]")
                elif val == min(col_vals):
                    row.append(f"[red]${format_price(val)}[/]")
                else:
                    row.append(f"${format_price(val)}")
        tbl.add_row(*row)
    console.print(tbl)

    # ── Panel de rentabilidad ──
    if receta and salsa_prices:
        salsa_vals = valores_positivos(salsa_prices)
        if salsa_vals:
            mejor_ciudad_venta, mejor_venta = mejor_ciudad(salsa_prices)

            contenido = []
            contenido.append(Text.from_markup(f"  [bold]{nombre}[/]"))

            # Receta dentro del panel: cantidad x ingrediente
            receta_parts = []
            for ing_id, cantidad in receta.items():
                ing_nombre = id_to_nombre.get(ing_id, ing_id)
                receta_parts.append(f"{cantidad} x {ing_nombre}")
            contenido.append(Text.from_markup(f"    [dim]Receta:[/] {' + '.join(receta_parts)}"))

            contenido.append(Text.from_markup(f"    Venta en [bold]{mejor_ciudad_venta}[/]: [green]${mejor_venta:,}[/]"))
            contenido.append(Text.from_markup(""))

            # ── Insumos (precio menor por ciudad) ──
            costo_total = 0
            filas_compra = []
            for ing_id, cantidad in receta.items():
                ing_nombre = id_to_nombre.get(ing_id, ing_id)
                ing_prices = precios_grp.get(ing_id, {})
                ing_vals = valores_positivos(ing_prices)
                if ing_vals:
                    ciudad_compra, precio_compra = mejor_ciudad(ing_prices, "min")
                    costo = precio_compra * cantidad
                    costo_total += costo
                    filas_compra.append((ing_nombre, cantidad, ciudad_compra, precio_compra, costo))
                else:
                    filas_compra.append((ing_nombre, cantidad, "N/D", 0, 0))

            contenido.append(Text.from_markup("  [bold]Insumos (precio menor por ciudad):[/]"))
            contenido.append(_tabla_insumos(filas_compra))
            contenido.append(Text.from_markup(f"    [bold]Costo total:[/]        [bold]${costo_total:,}[/]"))
            ganancia = mejor_venta - costo_total
            margen = pct(ganancia, costo_total)
            signo_ganancia = color_signo(ganancia)
            if ganancia >= 0:
                contenido.append(Text.from_markup(f"    [bold {signo_ganancia}]Ganancia:[/]         +${ganancia:,}  ({margen:.1f}%)"))
            else:
                contenido.append(Text.from_markup(f"    [bold {signo_ganancia}]Perdida:[/]          ${ganancia:,}  ({margen:.1f}%)"))

            # ── vs vender insumos por separado ──
            contenido.append(Text.from_markup(""))
            contenido.append(Text.from_markup("  [bold]vs vender insumos por separado:[/]"))
            valor_insumos = 0
            filas_venta = []
            for ing_id, cantidad in receta.items():
                ing_nombre = id_to_nombre.get(ing_id, ing_id)
                ing_prices = precios_grp.get(ing_id, {})
                ing_vals = valores_positivos(ing_prices)
                if ing_vals:
                    ciudad_vta, precio_vta = mejor_ciudad(ing_prices)
                    valor = precio_vta * cantidad
                    valor_insumos += valor
                    filas_venta.append((ing_nombre, cantidad, ciudad_vta, precio_vta, valor))
                else:
                    filas_venta.append((ing_nombre, cantidad, "N/D", 0, 0))
            contenido.append(_tabla_insumos(filas_venta))
            contenido.append(Text.from_markup(f"    [bold]Total:[/]              [bold]${valor_insumos:,}[/]"))

            # ── TOTAL por salsa ──
            contenido.append(Text.from_markup(""))
            contenido.append(Text.from_markup(
                f"  [bold cyan]TOTAL por salsa:[/]  costo [bold]${costo_total:,}[/]"
                f"  ->  venta [bold green]${mejor_venta:,}[/]"
                f"  ([bold {color_signo(ganancia)}]{ganancia:+,}[/])"
            ))

            console.print()
            console.print(Panel(
                Group(*contenido),
                title="[bold]Analisis de rentabilidad[/]",
                border_style="yellow",
                box=box.HEAVY,
                title_align="left",
            ))

    # ── Historial 7d ──
    console.print()
    console.print("[dim]Consultando historial de mercado...[/]")
    hist = get_history(item_id)
    vol_total = sum(h["volumen"] for h in hist.values())
    if vol_total > 0:
        hist_parts = _formatear_historial(hist, nombre)
        console.print(Panel(
            "\n".join(hist_parts),
            title="[bold]Volumen 7 dias[/]",
            border_style="cyan",
            box=box.ROUNDED,
            title_align="left",
        ))

    # ── Resumen de mercado (informativo, sin recomendaciones) ──
    recetas_config = config.get("insumos_pesca", {}).get("items", {})
    resumen = market_summary(precios_grp, item_id, recetas_config)
    console.print()
    _panel_resumen(resumen, mostrar_ingrediente=True)

    console.print()
    console.print("  [yellow][Esc][/] Volver · [yellow][R][/] Recargar")
    _pausa_volver()
