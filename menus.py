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
from api import get_prices, get_history_raw
from formatting import (format_price, _formatear_historial, color_precio, color_item,
                        market_summary, antiguedad)
from textos import (RESENAS_MENU, RESENAS_DETALLE, LEYENDA_TIERS, RESENAS_OPCIONES_PRINCIPAL,
                    RESUMEN, PARES_RECURSO, CALIDADES)
import catalogo

console = Console()


def _volumen_por_ciudad(hist):
    """{ciudad: volumen} del historial 7d (para desempatar min/max en
    market_summary). `hist` es la lista CRUDA de get_history_raw: entries
    con data[] de {timestamp, item_count, avg_price} por ciudad."""
    if not hist:
        return {}
    result = {}
    for entry in hist:
        city = entry.get("location")
        vol = sum(p.get("item_count", 0) for p in (entry.get("data") or []))
        if vol > 0:
            result[city] = vol
    return result


def _fecha_fresca(fechas, items, ciudad):
    """Timestamp ISO mas reciente entre `items` para `ciudad`.

    fechas: {item_id: {ciudad: [timestamps...]}} con los sell_price_min_date
    y sell_price_max_date de la API (los arma el mapeo de cada detalle).
    Devuelve None si ningun item tiene timestamp para esa ciudad (fila sin
    datos -> la columna "Actualizado" muestra un guion).
    """
    candidatos = []
    for item in items:
        candidatos.extend(fechas.get(item, {}).get(ciudad, []))
    return max(candidatos) if candidatos else None


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


def _panel_resumen(resumen, mostrar_ingrediente=False, uso="", items_extra=None, nombre_principal=""):
    """Panel informativo con los datos de market_summary.

    Solo datos objetivos (min/max, ingrediente). NUNCA recomienda acciones:
    el usuario decide.
    mostrar_ingrediente=False oculta la linea de ingrediente (ej: recursos,
    que no participan de salsas).
    uso="" oculta la linea de uso ("Se usa en ..."); pasar un nombre de plato
    o trofeo la muestra (ej: detalle de pez raro).
    nombre_principal: etiqueta del item principal. Si se pasa (no vacia), el
    resumen se arma en una grid alineada [item | venta min | venta max];
    si esta vacia, usa las filas clasicas "Venta min:" y "Venta max:".
    items_extra=[(etiqueta, resumen), ...]: agrega filas alineadas de otros
    items (ej: crudo Y refinado juntos) cuando se usa nombre_principal.
    """
    def _celdas_precio(res):
        min_ciudad = res.get("min_ciudad") or ""
        max_ciudad = res.get("max_ciudad") or ""
        min_txt = f" ({min_ciudad})" if min_ciudad else ""
        max_txt = f" ({max_ciudad})" if max_ciudad else ""
        return (f"[bold]${format_price(res['min_venta'])}[/]{min_txt}",
                f"[bold]${format_price(res['max_venta'])}[/]{max_txt}")

    extras = items_extra or []
    usar_grid = bool(nombre_principal) or bool(extras)

    if usar_grid:
        grid = Table.grid(padding=(0, 2))
        grid.add_column(no_wrap=True, max_width=22)
        grid.add_column(justify="left", max_width=26)
        grid.add_column(justify="left", max_width=26)
        if nombre_principal and not resumen.get("sin_datos"):
            mn, mx = _celdas_precio(resumen)
            grid.add_row(nombre_principal, mn, mx)
        for etiq, res in extras:
            if res.get("sin_datos"):
                grid.add_row(etiq, f"  [dim]{RESUMEN['sin_datos']}[/]", "")
            else:
                mn, mx = _celdas_precio(res)
                grid.add_row(etiq, mn, mx)
        cuerpo: list = [grid]
    else:
        cuerpo = []
        if resumen.get("sin_datos"):
            cuerpo.append(f"  [dim]{RESUMEN['sin_datos']}[/]")
        else:
            min_ciudad = resumen.get("min_ciudad") or ""
            max_ciudad = resumen.get("max_ciudad") or ""
            min_txt = f" ({min_ciudad})" if min_ciudad else ""
            max_txt = f" ({max_ciudad})" if max_ciudad else ""
            cuerpo.append(f"  {RESUMEN['venta_min']}:  [bold]${format_price(resumen['min_venta'])}[/]{min_txt}")
            cuerpo.append(f"  {RESUMEN['venta_max']}:  [bold]${format_price(resumen['max_venta'])}[/]{max_txt}")

    # Lineas de informacion extra (ingrediente / uso) fuera de la grid.
    extra_lineas = []
    if mostrar_ingrediente:
        if resumen.get("es_ingrediente") and resumen.get("recetas"):
            extra_lineas.append(f"  {RESUMEN['ingrediente']}:  [bold]{', '.join(resumen['recetas'])}[/]")
        else:
            extra_lineas.append(f"  [dim]{RESUMEN['no_ingrediente']}[/]")
    if uso:
        extra_lineas.append(f"  {RESUMEN['uso']}:  [bold]{uso}[/]")

    if usar_grid:
        cuerpo = Group(*cuerpo, *extra_lineas) if extra_lineas else cuerpo[0]
    else:
        cuerpo.extend(extra_lineas)
        cuerpo = "\n".join(cuerpo) if cuerpo else "  [dim]Sin datos de mercado[/]"

    console.print(Panel(
        cuerpo,
        title=f"[bold]{RESUMEN['titulo']}[/]",
        border_style="green",
        box=box.ROUNDED,
        title_align="left",
        expand=False,
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

    Consola legacy Windows (sin VT): API nativa. Con VT / Unix / redireccion:
    ANSI puro (mueve el cursor a la fila, escribe el texto que ya trae sus
    colores ANSI del render en buffer y borra hasta el final de la linea).
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
        if ch in ("\x00", "\xe0"):  # teclas especiales (flechas, F1-F12)
            ch2 = msvcrt.getwch()
            if ch2 == "H":
                return "up"
            elif ch2 == "P":
                return "down"
            elif ch2 == "K":
                return "left"
            elif ch2 == "M":
                return "right"
            elif ch2 == "?":  # F5 (scan-code de msvcrt: F1=";", F5="?", F6="@")
                return "f5"
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


def _menu_seleccion(opciones, titulo="", titulo_abajo="", filas=None, numeros=None, es_raiz=False):
    """Selector numerado con flechas.

    opciones: lista de (label, desc) — label con markup Rich, desc resena
    contextual de la opcion (puede ser "").
    titulo: bloque que se muestra ARRIBA del listado.
    titulo_abajo: bloque opcional que se muestra DESPUES del listado y de la
    descripcion de la opcion seleccionada (layout "listado arriba, datos abajo").
    Con titulo_abajo, la desc de la opcion seleccionada va entre el listado y
    el bloque; sin el, va en el footer (comportamiento historico).
    filas None -> una sola columna. Con filas se usa grid column-major
    (item = columna * filas + fila), igual que el reparto de la lista.
    numeros: lista opcional con la etiqueta a mostrar por opcion (ej:
    ["1","2","F5"]). Por defecto numera 1..n. Solo responden los DIGITOS
    que se muestran como etiqueta; un digito no visible se ignora (evita
    atajos ocultos que parecen bugs). Con numeros no hay acumulacion de
    digitos multiples.
    Devuelve int (indice 0-based), "f5" (reiniciar) o None (esc/q = cancelar).
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

    def footer(c=None, con_desc=True):
        c = c or console
        # La linea de descripcion SIEMPRE se reserva (aunque este vacia)
        # para que la pantalla no cambie de altura al navegar.
        if con_desc:
            _, desc = opciones[cursor]
            c.print(f"  [dim]{desc}[/]" if desc else "")
            c.print()
        col_hint = "Izq/Der columna · " if ncol > 1 else ""
        esc_tecla, esc_accion = ("Esc", "salir") if es_raiz else ("Esc", "volver")
        hint = (f"  [dim]{col_hint}Arriba/Abajo mover · [yellow]Enter[/] elegir"
                f" · [yellow]{esc_tecla}[/] {esc_accion} · [yellow]F5[/] recargar")
        c.print(Panel(hint, border_style="cyan", box=box.ROUNDED, expand=True))

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
        if titulo_abajo:
            # layout "listado arriba": la descripcion de la opcion seleccionada
            # va ENTRE el listado y el bloque de datos; el footer solo hint.
            _, desc = opciones[cursor]
            fc.print(f"  [dim]{desc}[/]" if desc else "")
            fc.print()
            fc.print(titulo_abajo)
            fc.print()
            footer(fc, con_desc=False)
        else:
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
        elif tecla == "f5":
            return "f5"
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
        if tecla == "f5":
            reiniciar()


def _panel_detalle(nombre, color, contenido):
    """Header unificado de las pantallas de detalle (componente unico).

    nombre: titular en el borde; color: color de la paleta del item (tier o
    encantamiento) — el MISMO con que se lista el item en el menu, sin negrita
    para que coincida en terminales de 16 colores. contenido: bloque interior
    (tag + resena). Compartido por pez, recurso e insumo.
    """
    console.print(Panel(
        contenido,
        title=f"[{color}]{nombre}[/]",
        border_style="cyan",
        box=box.ROUNDED,
        expand=True,
    ))
    console.print()


def _hint_detalle(c=None):
    """Caja de hint del footer de las pantallas de detalle.

    Mismo estilo que el footer del selector (Panel cyan ROUNDED expand),
    pero sin flechas/Enter: las pantallas de detalle solo vuelven o recargan.
    """
    c = c or console
    c.print(Panel(
        "  [dim][yellow]Esc[/] volver · [yellow]F5[/] recargar[/]",
        border_style="cyan",
        box=box.ROUNDED,
        expand=True,
    ))


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
    # 1 Pesca · 2-6 recursos como "crudo/refinado" (PARES_RECURSO) · 7 Salsas · 8 Buscar.
    # Los indices 1-7 NO cambian: el ruteo por `seccion` sigue intacto.
    nombres = (["Pesca"]
               + [PARES_RECURSO[k] for k in ("fibra", "madera", "cuero", "mineral", "piedra")]
               + ["Salsas de pescado", "Buscar"])
    while True:
        panel = Panel(
            f"  [dim]{RESENAS_MENU['principal']}[/]",
            title="[bold cyan]Albion Helper[/]",
            border_style="cyan",
            box=box.ROUNDED,
            expand=True,
        )
        opciones = []
        for i, nombre in enumerate(nombres, start=1):
            opciones.append((nombre, RESENAS_OPCIONES_PRINCIPAL[i]))

        # Reiniciar NO es un item del menu: la tecla R ya recarga desde
        # cualquier pantalla (lo dice el hint), un item visible seria duplicar.
        idx = _menu_seleccion(opciones, titulo=panel, es_raiz=True)

        if idx == "f5":
            reiniciar()
        elif idx is None:
            console.print("\n[bold yellow]¿Salir? [Enter] Confirmar · [Esc] Cancelar[/]")
            if _confirmar_salida():
                console.print("\n[bold green]Que la plata te sobre![/]")
                break
        elif idx == 7:
            menu_buscar(config)
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


# ─── Buscador global ──────────────────────────────────────────
def menu_buscar(config):
    """Buscador global: escritura en vivo con Backspace (reusa _leer_tecla).

    Cada tecla re-filtra el catalogo (normalizado, tokens AND). ↑/↓ mueven
    el cursor, Enter abre el detalle del item seleccionado, Esc vuelve
    (primero limpia la consulta si hay texto), R recarga la app.
    """
    texto = ""
    cursor = 0
    while True:
        resultados = catalogo.buscar(texto)
        cursor = min(cursor, max(0, len(resultados) - 1)) if resultados else 0

        # ── Render del frame completo en un buffer (misma tecnica del selector) ──
        titulo = Panel(
            f"  [dim]{RESENAS_MENU['buscar']}[/]",
            title="[bold cyan]Buscar[/]",
            border_style="cyan",
            box=box.ROUNDED,
            expand=True,
        )
        buf = io.StringIO()
        ancho = console.width if console.width else 120
        alto = console.height if console.height else 50
        fc = Console(file=buf, force_terminal=True, width=ancho, height=alto,
                     highlight=False, color_system="truecolor")
        fc.print(titulo)
        fc.print()
        fc.print(f"  [bold]Consulta:[/] {texto}\u258c")
        fc.print()
        if not texto:
            fc.print("  [dim]Escribe para buscar...[/]")
        elif not resultados:
            fc.print("  [dim]Sin resultados para tu consulta.[/]")
        else:
            for i, item in enumerate(resultados):
                nombre = item["nombre"].replace("[", "\\[").replace("]", "\\]")
                etiqueta = f"{i + 1:>2}"
                if i == cursor:
                    fc.print(f"  [black on cyan][ {etiqueta} ] {nombre}[/]")
                else:
                    fc.print(f"  [ {etiqueta} ] {nombre}")
            fc.print()
            fc.print(f"  [dim]{len(resultados)} resultado(s) · ↑/↓ mover · Enter abrir[/]")
        fc.print()
        fc.print(Panel(
            "  [dim]Escribir filtra · [yellow]↑/↓[/] mover · [yellow]Enter[/] abrir"
            " · [yellow]Esc[/] volver · [yellow]F5[/] recargar[/]",
            border_style="cyan",
            box=box.ROUNDED,
            expand=True,
        ))
        lineas = buf.getvalue().split("\n")
        while lineas and lineas[-1] == "":
            lineas.pop()
        limpiar_pantalla()
        console.control(_RawControl("\n".join(lineas) + "\n"))
        try:
            console.file.flush()
        except Exception:
            pass

        tecla = _leer_tecla()
        if tecla is None:
            continue
        if tecla == "esc":
            if texto:
                texto = ""
                cursor = 0
            else:
                return
        elif tecla == "enter":
            if resultados:
                ver_detalle_buscado(resultados[cursor], config)
        elif tecla in ("up", "down") and resultados:
            if tecla == "up":
                cursor = (cursor - 1) % len(resultados)
            else:
                cursor = (cursor + 1) % len(resultados)
        elif tecla == "f5":
            reiniciar()
        elif tecla in ("\x08", "\x7f"):  # Backspace
            if texto:
                texto = texto[:-1]
                cursor = 0
        elif len(tecla) == 1 and tecla.isprintable():
            texto += tecla
            cursor = 0


def _celda_calidad(val, vals):
    """Celda de precio por calidad: verde el mayor, rojo el menor, '—' sin datos."""
    if val == 0 or not vals:
        return "[dim]—[/]"
    if val == max(vals):
        return f"[bold green]${format_price(val)}[/]"
    if val == min(vals):
        return f"[red]${format_price(val)}[/]"
    return f"${format_price(val)}"


def _tabla_calidades(columnas, precios, fechas):
    """Tabla `Ciudad | (calidad | Act)` por item.

    columnas: [(item_id, etiqueta, calidad), ...] en orden de la tabla.
    precios:  {item_id: {calidad: {ciudad: precio}}}.
    fechas:   {item_id: {calidad: {ciudad: [timestamps ISO]}}}.
    Colores por calidad: verde el mayor de la columna, rojo el menor, '—'
    sin datos. La columna 'Act' muestra la frescura de cada celda.
    'Sobresaliente' se abrevia a 'Sobresal.' en el encabezado para que las 11
    columnas entren en 120 de ancho (la calidad interna sigue siendo 4).
    """
    ABREV = {"Sobresaliente": "Sobresal."}
    tbl = Table(box=box.ROUNDED)
    tbl.add_column("Ciudad", style="cyan")
    for _, etiq, _ in columnas:
        tbl.add_column(ABREV.get(etiq, etiq), justify="right")
        tbl.add_column("Act", justify="right")
    for city in CITIES:
        row = [city]
        for iid, _, calidad in columnas:
            px = precios.get(iid, {}).get(calidad, {})
            val = px.get(city, 0)
            vals = [v for v in px.values() if v > 0]
            row.append(_celda_calidad(val, vals))
            ts = fechas.get(iid, {}).get(calidad, {}).get(city, [])
            fresca = antiguedad(max(ts)) if ts else ""
            row.append(fresca or "[dim]—[/]")
        tbl.add_row(*row)
    return tbl


def ver_detalle_buscado(item, config):
    """Detalle de un item del buscador: UNA llamada get_prices, sin volumen,
    sin resumen. Segun el tipo detectado por el catalogo:
      - arma:   5 paneles apilados (base/.1/.2/.3/.4), cada uno con las 5
                calidades por ciudad (11 columnas).
      - diario: tabla Ciudad | Vacío | Lleno (consulta {base}_EMPTY/_FULL).
      - simple: un solo panel con las 5 calidades.
    """
    limpiar_pantalla()
    id_base = item["id_base"]
    tipo = item["tipo"]

    # Color del header: el del tier si se puede extraer; si no, blanco neutro.
    try:
        _, color = info_tier(id_base)
    except Exception:
        color = "white"

    _panel_detalle(
        item["nombre"], color,
        f"  [dim]{id_base}[/]\n\n  {RESENAS_DETALLE['buscado']}",
    )

    if tipo == "diario":
        base = id_base
        for suf in ("_EMPTY", "_FULL"):
            if base.endswith(suf):
                base = base[: -len(suf)]
                break
        ids = [f"{base}_EMPTY", f"{base}_FULL"]
    elif tipo == "arma":
        ids = [id_base] + [f"{id_base}@{i}" for i in range(1, 5)]
    else:
        ids = [id_base]

    raw_data = get_prices(ids)
    if not raw_data:
        _hint_detalle()
        _pausa_volver()
        return

    precios = {}  # item_id -> calidad -> {ciudad: precio}
    fechas = {}   # item_id -> calidad -> ciudad -> [timestamps ISO]
    for entry in raw_data:
        iid = entry.get("item_id", "")
        if iid not in ids:
            continue
        ciudad = entry.get("city", "")
        calidad = entry.get("quality", 1)
        precio = entry.get("sell_price_min", 0)
        precios.setdefault(iid, {}).setdefault(calidad, {})[ciudad] = precio
        fechas.setdefault(iid, {}).setdefault(calidad, {}).setdefault(ciudad, [])
        if precio > 0 and entry.get("sell_price_min_date"):
            fechas[iid][calidad][ciudad].append(entry["sell_price_min_date"])
        if entry.get("sell_price_max", 0) > 0 and entry.get("sell_price_max_date"):
            fechas[iid][calidad][ciudad].append(entry["sell_price_max_date"])

    if tipo == "diario":
        columnas = [(ids[0], "Vacío", 1), (ids[1], "Lleno", 1)]
        console.print(_tabla_calidades(columnas, precios, fechas))
    elif tipo == "arma":
        paneles = [("Base", id_base)] + [(f".{i}", f"{id_base}@{i}") for i in range(1, 5)]
        for etiq, iid in paneles:
            columnas = [(iid, cal, i + 1) for i, cal in enumerate(CALIDADES)]
            console.print(Panel(
                _tabla_calidades(columnas, precios, fechas),
                title=f"[bold]{etiq}[/]",
                border_style="cyan",
                box=box.ROUNDED,
                title_align="left",
                expand=False,
            ))
            console.print()
    else:
        columnas = [(id_base, cal, i + 1) for i, cal in enumerate(CALIDADES)]
        console.print(_tabla_calidades(columnas, precios, fechas))

    console.print()
    _hint_detalle()
    _pausa_volver()


# ─── Pesca ────────────────────────────────────────────────────
def menu_pesca(config):
    raw = config["pescados"]
    peces = []
    for nombre, info in raw.items():
        if nombre.startswith("_"):
            continue
        peces.append((nombre, info["id"], info["trozos"], info.get("tipo", "comun")))

    titulo = Panel(
        f"  [dim]{RESENAS_MENU['pesca']}[/]\n\n  {LEYENDA_TIERS}",
        title="[bold cyan]Pesca[/]",
        border_style="cyan",
        box=box.ROUNDED,
        expand=True,
    )
    while True:
        opciones = []
        for nombre, item_id, _, _ in peces:
            _, color = info_tier(item_id)
            opciones.append((f"[{color}]{nombre}[/]", ""))
        idx = _menu_seleccion(opciones, titulo=titulo, filas=(len(peces) + 1) // 2)
        if idx is None:
            return
        elif idx == "f5":
            reiniciar()
        else:
            nombre, item_id, trozos, tipo = peces[idx]
            ver_detalle_pez(nombre, item_id, trozos, tipo, config)

def ver_detalle_pez(nombre, item_id, trozos, tipo, config=None):
    limpiar_pantalla()
    tier, color = info_tier(item_id)
    tipo_txt = "Raro" if tipo == "raro" else "Comun"
    tag = f"[{color}]T{tier} {tipo_txt}[/]"
    # Header unificado: nombre en el borde con el color del tier, tag + reseña adentro.
    _panel_detalle(
        nombre, color,
        f"  {tag}  [dim]—  {trozos} trozos al picar[/]\n\n  {RESENAS_DETALLE['pez']}",
    )

    raw_data = get_prices([item_id, "T1_FISHCHOPS"])
    if not raw_data:
        _hint_detalle()
        _pausa_volver()
        return

    prices = {}
    fechas = {}  # item_id -> ciudad -> [timestamps min/max de la API]
    for entry in raw_data:
        # Solo precios de calidad normal (1): el helper compara el item base.
        if entry.get("quality", 1) != 1:
            continue
        item = entry["item_id"]
        city = entry["city"]
        if item not in prices:
            prices[item] = {}
        prices[item][city] = entry.get("sell_price_min", 0)
        # Los timestamps no entran en `prices` (contrato de market_summary):
        # van en paralelo para la columna "Actualizado". Solo cuando la fila
        # tiene precio real: la API manda "0001-01-01T00:00:00" como centinela
        # en ciudades sin ventas (fila N/D -> columna con guion).
        fechas.setdefault(item, {}).setdefault(city, [])
        if entry.get("sell_price_min", 0) > 0 and entry.get("sell_price_min_date"):
            fechas[item][city].append(entry["sell_price_min_date"])
        if entry.get("sell_price_max", 0) > 0 and entry.get("sell_price_max_date"):
            fechas[item][city].append(entry["sell_price_max_date"])

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
    tbl.add_column("Actualizado", justify="right")
    tbl.add_column("Picado", justify="right")
    tbl.add_column("Actualizado", justify="right")
    for city in CITIES:
        e, p = precios[city]
        fresca_entero = antiguedad(_fecha_fresca(fechas, [item_id], city))
        fresca_picado = antiguedad(_fecha_fresca(fechas, ["T1_FISHCHOPS"], city))
        tbl.add_row(city,
                    color_precio(e, max_entero, min_entero), fresca_entero or "[dim]—[/]",
                    color_precio(p, max_picado, min_picado), fresca_picado or "[dim]—[/]")
    console.print(tbl)

    # ─── Historial 7d (si disponible) ───────────────────────────
    console.print()
    console.print("[dim]Consultando historial de mercado...[/]")
    hist_entero = get_history_raw(item_id)
    time.sleep(0.5)
    hist_trozos = get_history_raw("T1_FISHCHOPS")

    vol_entero_total = sum(_volumen_por_ciudad(hist_entero).values())
    vol_trozos_total = sum(_volumen_por_ciudad(hist_trozos).values())

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
            expand=False,
        ))

    # ─── Resumen de mercado (informativo, sin recomendaciones) ──
    recetas_config = None
    if config:
        recetas_config = config.get("insumos_pesca", {}).get("items", {})
    resumen = market_summary(prices, item_id, recetas_config, volumen=_volumen_por_ciudad(hist_entero))
    uso = ""
    if config:
        uso = config.get("pescados", {}).get(nombre, {}).get("uso", "")
    console.print()
    _panel_resumen(resumen, uso=uso)
    console.print()
    _hint_detalle()
    _pausa_volver()


# ─── Recursos ─────────────────────────────────────────────────
def ver_recurso(config, tipo):
    info = config["recursos"].get(tipo)
    if not info:
        console.print(f"\n[red][!] Tipo de recurso '{tipo}' no encontrado.[/]")
        return

    nombre_recurso = info.get("nombre", tipo.upper())
    # El encabezado muestra el par "crudo/refinado" (ej: Fibra/Tela);
    # si el recurso no esta en PARES_RECURSO, cae al nombre simple.
    par_recurso = PARES_RECURSO.get(tipo, nombre_recurso)
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

    titulo = Panel(
        f"  [dim]{RESENAS_MENU['recursos']}[/]\n\n"
        f"  {LEYENDA_TIERS}",
        title=f"[bold cyan]{par_recurso}[/]",
        border_style="cyan",
        box=box.ROUNDED,
        expand=True,
    )
    while True:
        opciones = []
        for item in menu_items:
            tier_num = item["tier_key"][1:]
            color = COLORES_TIER.get(tier_num, "white")
            opciones.append((f"[{color}]{item['label']}[/]", ""))
        idx = _menu_seleccion(opciones, titulo=titulo, filas=(len(menu_items) + 1) // 2)
        if idx is None:
            return
        elif idx == "f5":
            reiniciar()
        else:
            item = menu_items[idx]
            _ver_detalle_recurso(nombre_recurso, item["tier_key"], tiers[item["tier_key"]], modo=item["modo"])

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
    # Header unificado: nombre en el borde con el color del tier, reseña adentro.
    color = COLORES_TIER.get(tier_key[1:], "white")
    _panel_detalle(
        f"{titulo_item} {tier_key}", color,
        f"  {RESENAS_DETALLE['recurso']}",
    )

    # Los encantamientos (.1-.4) existen desde T4 en Albion; T2/T3 no tienen
    # versiones encantadas, asi que se omiten (columnas, consultas y observacion).
    has_ench = int(tier_key[1:]) >= 4

    # IDs de items encantados (solo si el tier los tiene)
    ench_ids = [f"{crudo_id}_LEVEL{i}@{i}" for i in range(1, 5)] if has_ench else []
    ref_ench_ids = [f"{refinado_id}_LEVEL{i}@{i}" for i in range(1, 5)] if has_ench else []

    # Buscar precios (solo lo necesario segun modo)
    if modo == "crudo":
        item_ids = [crudo_id] + ench_ids
    elif modo == "refinado":
        item_ids = [crudo_id, refinado_id] + ref_ench_ids
    else:
        item_ids = [crudo_id] + ench_ids + [refinado_id] + ref_ench_ids

    raw_data = get_prices(item_ids)
    if not raw_data:
        _hint_detalle()
        _pausa_volver()
        return

    prices_map = {}
    fechas = {}  # item_id -> ciudad -> [timestamps min/max de la API]
    for entry in raw_data:
        # Solo precios de calidad normal (1): el helper compara el item base.
        if entry.get("quality", 1) != 1:
            continue
        iid = entry["item_id"]
        ciudad = entry["city"]
        prices_map.setdefault(iid, {})[ciudad] = entry.get("sell_price_min", 0)
        # Los timestamps no entran en `prices_map` (contrato de market_summary):
        # van en paralelo para la columna "Actualizado". Solo cuando la fila
        # tiene precio real: la API manda "0001-01-01T00:00:00" como centinela
        # en ciudades sin ventas (fila N/D -> columna con guion).
        fechas.setdefault(iid, {}).setdefault(ciudad, [])
        if entry.get("sell_price_min", 0) > 0 and entry.get("sell_price_min_date"):
            fechas[iid][ciudad].append(entry["sell_price_min_date"])
        if entry.get("sell_price_max", 0) > 0 and entry.get("sell_price_max_date"):
            fechas[iid][ciudad].append(entry["sell_price_max_date"])

    # ═══════════════ TABLA ═══════════════
    # Una sola tabla: columna Ciudad + columnas de crudo y/o refinado (+ encantamientos).
    mostrar_crudo = (modo == "crudo" or modo == "todo")
    mostrar_ref = (modo == "refinado" or modo == "todo")
    planos = {c: prices_map.get(crudo_id, {}).get(c, 0) for c in CITIES if prices_map.get(crudo_id, {}).get(c, 0) > 0} if mostrar_crudo else {}
    refs = {c: prices_map.get(refinado_id, {}).get(c, 0) for c in CITIES if prices_map.get(refinado_id, {}).get(c, 0) > 0} if mostrar_ref else {}

    tbl = Table(box=box.ROUNDED)
    tbl.add_column("Ciudad", style="cyan")
    if mostrar_crudo:
        tbl.add_column(nombre_real, justify="right")
        tbl.add_column("Actualizado", justify="right")
        if has_ench:
            for e in (".1", ".2", ".3", ".4"):
                tbl.add_column(e, justify="right")
                tbl.add_column("Actualizado", justify="right")
    if mostrar_ref:
        tbl.add_column(ref_nombre, justify="right")
        tbl.add_column("Actualizado", justify="right")
        if has_ench:
            for e in (".1", ".2", ".3", ".4"):
                tbl.add_column(e, justify="right")
                tbl.add_column("Actualizado", justify="right")

    for city in CITIES:
        row = [city]
        if mostrar_crudo:
            plano = prices_map.get(crudo_id, {}).get(city, 0)
            row.append(color_item(plano, planos.values()))
            fresca = antiguedad(_fecha_fresca(fechas, [crudo_id], city))
            row.append(fresca or "[dim]—[/]")
            if has_ench:
                for i in range(4):
                    eid = ench_ids[i]
                    val = prices_map.get(eid, {}).get(city, 0)
                    vals = [prices_map.get(ench_ids[i], {}).get(c, 0) for c in CITIES if prices_map.get(ench_ids[i], {}).get(c, 0) > 0]
                    row.append(color_item(val, vals))
                    fresca = antiguedad(_fecha_fresca(fechas, [eid], city))
                    row.append(fresca or "[dim]—[/]")
        if mostrar_ref:
            ref = prices_map.get(refinado_id, {}).get(city, 0)
            row.append(color_item(ref, refs.values()))
            fresca = antiguedad(_fecha_fresca(fechas, [refinado_id], city))
            row.append(fresca or "[dim]—[/]")
            if has_ench:
                for i in range(4):
                    eid = ref_ench_ids[i]
                    val = prices_map.get(eid, {}).get(city, 0)
                    vals = [prices_map.get(ref_ench_ids[i], {}).get(c, 0) for c in CITIES if prices_map.get(ref_ench_ids[i], {}).get(c, 0) > 0]
                    row.append(color_item(val, vals))
                    fresca = antiguedad(_fecha_fresca(fechas, [eid], city))
                    row.append(fresca or "[dim]—[/]")
        tbl.add_row(*row)
    console.print(tbl)

    # ═══════════════ HISTORIAL 7 DIAS ═══════════════
    console.print()
    console.print("[dim]Consultando historial de mercado...[/]")
    hist_parts = []
    if modo == "crudo" or modo == "todo":
        hist_crudo = get_history_raw(crudo_id)
        if sum(_volumen_por_ciudad(hist_crudo).values()) > 0:
            hist_parts += _formatear_historial(hist_crudo, nombre_real)
        time.sleep(0.5)
    if modo == "refinado" or modo == "todo":
        hist_ref = get_history_raw(refinado_id)
        if sum(_volumen_por_ciudad(hist_ref).values()) > 0:
            hist_parts += _formatear_historial(hist_ref, ref_nombre)
    if hist_parts:
        console.print(Panel(
            "\n".join(hist_parts),
            title="[bold]Volumen 7 dias[/]",
            border_style="cyan",
            box=box.ROUNDED,
            title_align="left",
            expand=False,
        ))

    # ═══════════════ RESUMEN DE MERCADO (informativo, sin recomendaciones) ══
    console.print()
    if modo == "todo":
        res_crudo = market_summary(prices_map, crudo_id, volumen=_volumen_por_ciudad(hist_crudo))
        res_ref = market_summary(prices_map, refinado_id, volumen=_volumen_por_ciudad(hist_ref))
        _panel_resumen(res_crudo, nombre_principal=nombre_real,
                       items_extra=[(ref_nombre, res_ref)])
    else:
        item_vista = refinado_id if modo == "refinado" else crudo_id
        hist_vista = hist_ref if modo == "refinado" else hist_crudo
        resumen = market_summary(prices_map, item_vista, volumen=_volumen_por_ciudad(hist_vista))
        _panel_resumen(resumen)
    console.print()
    _hint_detalle()
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
        console.print(Panel(
            "  [red][!] Sin datos de mercado[/]",
            title="[bold cyan]Salsas de pescado[/]",
            border_style="cyan",
            box=box.ROUNDED,
            expand=True,
        ))
        console.print()
        _hint_detalle()
        _pausa_volver()
        return

    # Agrupar por item_id
    precios_grp = {}
    fechas = {}  # item_id -> ciudad -> [timestamps min/max de la API]
    for entry in raw_data:
        # Solo precios de calidad normal (1): el helper compara el item base.
        if entry.get("quality", 1) != 1:
            continue
        iid = entry["item_id"]
        ciudad = entry["city"]
        precios_grp.setdefault(iid, {})[ciudad] = entry.get("sell_price_min", 0)
        # Timestamps en paralelo (la columna "Actualizado"); solo con precio
        # real: la API manda "0001-01-01T00:00:00" como centinela sin ventas.
        fechas.setdefault(iid, {}).setdefault(ciudad, [])
        if entry.get("sell_price_min", 0) > 0 and entry.get("sell_price_min_date"):
            fechas[iid][ciudad].append(entry["sell_price_min_date"])
        if entry.get("sell_price_max", 0) > 0 and entry.get("sell_price_max_date"):
            fechas[iid][ciudad].append(entry["sell_price_max_date"])

    # Tabla combinada
    tbl = Table(box=box.ROUNDED)
    tbl.add_column("Ciudad", style="cyan")
    for nombre, sid, _ in salsas:
        nivel = int(sid.split("_LEVEL")[-1])
        color = ENCH_COLORS[nivel]
        nombre_corto = nombre.replace("Salsa ", "")
        tbl.add_column(f"[{color}]{nombre_corto}[/]", justify="right")
        tbl.add_column("Actualizado", justify="right")

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
            fresca = antiguedad(_fecha_fresca(fechas, [sid], city))
            row.append(fresca or "[dim]—[/]")
        tbl.add_row(*row)

    # Info por salsa en grid: salsa | receta (dato neutro, sin precio ni ciudad)
    grid = Table.grid(padding=(0, 3))
    grid.add_column(no_wrap=True)
    grid.add_column(no_wrap=True)
    for nombre, sid, receta in salsas:
        nivel = int(sid.split("_LEVEL")[-1])
        color = ENCH_COLORS[nivel]
        nombre_corto = nombre.replace("Salsa ", "")

        cant_carne = receta.get("T1_FISHCHOPS", 0)
        cant_alga = receta.get("T1_SEAWEED", 0)

        grid.add_row(
            f"[{color}]{nombre_corto}[/]",
            f"{cant_carne} Carne + {cant_alga} Alga",
        )

    # Selector: layout "listado arriba" — el header va arriba, los datos
    # (tabla + recetas) van como bloque inferior.
    while True:
        opciones = []
        for nombre, sid, receta in salsas:
            nivel = int(sid.split("_LEVEL")[-1])
            color = ENCH_COLORS[nivel]
            cant_carne = receta.get("T1_FISHCHOPS", 0)
            cant_alga = receta.get("T1_SEAWEED", 0)
            opciones.append((f"[{color}]{nombre}[/]", f"{cant_carne} Carne + {cant_alga} Alga"))

        titulo = Group(
            Panel(
                f"  [dim]{RESENAS_MENU['insumos']}[/]",
                title="[bold cyan]Salsas de pescado[/]",
                border_style="cyan",
                box=box.ROUNDED,
                expand=True,
            ),
        )

        titulo_abajo = Group(
            Text(""),
            tbl,
            Text(""),
            grid,
            Text(""),
        )

        idx = _menu_seleccion(opciones, titulo=titulo, titulo_abajo=titulo_abajo)

        if idx is None:
            return
        elif idx == "f5":
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





def ver_detalle_insumo(nombre, item_id, config):
    limpiar_pantalla()
    # Header unificado: nombre en el borde con el color de encantamiento, reseña adentro.
    nivel = int(item_id.split("_LEVEL")[-1]) if "_LEVEL" in item_id else 0
    color = ENCH_COLORS[nivel] if 0 <= nivel < len(ENCH_COLORS) else "white"
    _panel_detalle(nombre, color, f"  {RESENAS_DETALLE['insumo']}")

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
        _hint_detalle()
        _pausa_volver()
        return

    # Agrupar precios por item_id
    precios_grp = {}
    fechas = {}  # item_id -> ciudad -> [timestamps min/max de la API]
    for entry in raw_data:
        # Solo precios de calidad normal (1): el helper compara el item base.
        if entry.get("quality", 1) != 1:
            continue
        iid = entry["item_id"]
        ciudad = entry["city"]
        precios_grp.setdefault(iid, {})[ciudad] = entry.get("sell_price_min", 0)
        # Los timestamps no entran en `precios_grp` (contrato de market_summary):
        # van en paralelo para la columna "Actualizado". Solo cuando la fila
        # tiene precio real: la API manda "0001-01-01T00:00:00" como centinela
        # en ciudades sin ventas (fila N/D -> columna con guion).
        fechas.setdefault(iid, {}).setdefault(ciudad, [])
        if entry.get("sell_price_min", 0) > 0 and entry.get("sell_price_min_date"):
            fechas[iid][ciudad].append(entry["sell_price_min_date"])
        if entry.get("sell_price_max", 0) > 0 and entry.get("sell_price_max_date"):
            fechas[iid][ciudad].append(entry["sell_price_max_date"])

    salsa_prices = precios_grp.get(item_id, {})

    # ── Tabla combinada: Ciudad | Alga | Carne | Venta | Actualizado ──
    tbl = Table(box=box.ROUNDED)
    tbl.add_column("Ciudad", style="cyan")

    cols_info = []  # [(titulo_columna, dict_precios_por_ciudad)]
    items_fila = [item_id]  # ids que alimentan la fila (para la frescura)
    if receta:
        for ing_id in sorted(receta.keys(), key=lambda i: id_to_nombre.get(i, i)):
            items_fila.append(ing_id)
            col_title = _acortar_nombre(id_to_nombre.get(ing_id, ing_id))
            cols_info.append((col_title, precios_grp.get(ing_id, {})))
    cols_info.append(("Venta", salsa_prices))

    for title, _ in cols_info:
        tbl.add_column(title, justify="right")
    tbl.add_column("Actualizado", justify="right")

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
        fresca = antiguedad(_fecha_fresca(fechas, items_fila, city))
        row.append(fresca or "[dim]—[/]")
        tbl.add_row(*row)
    console.print(tbl)

# ── Receta (dato neutro, sin recomendaciones) ──
    if receta:
        receta_parts = [f"{cantidad} × {id_to_nombre.get(ing_id, ing_id)}"
                        for ing_id, cantidad in receta.items()]
        console.print()
        console.print(Text.from_markup(f"  [bold]Receta:[/] {' + '.join(receta_parts)}"))

    # ── Historial 7d ──
    console.print()
    console.print("[dim]Consultando historial de mercado...[/]")
    hist = get_history_raw(item_id)
    vol_total = sum(_volumen_por_ciudad(hist).values())
    if vol_total > 0:
        hist_parts = _formatear_historial(hist, nombre)
        console.print(Panel(
            "\n".join(hist_parts),
            title="[bold]Volumen 7 dias[/]",
            border_style="cyan",
            box=box.ROUNDED,
            title_align="left",
            expand=False,
        ))

    # ── Resumen de mercado (informativo, sin recomendaciones) ──
    recetas_config = config.get("insumos_pesca", {}).get("items", {})
    resumen = market_summary(precios_grp, item_id, recetas_config, volumen=_volumen_por_ciudad(hist))
    console.print()
    _panel_resumen(resumen)

    console.print()
    _hint_detalle()
    _pausa_volver()
