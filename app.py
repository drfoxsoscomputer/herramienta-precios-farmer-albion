# app.py — Entry point del executable portátil.
# ─────────────────────────────────────────────────────────────
# Flujo (todo dentro de la MISMA ventana, nunca abre el navegador):
#   1) Levanta Flask (hilo daemon) y abre UNA ventana chica (launcher)
#      que pregunta qué hacer: Abrir la app / Solo servidor / Consola.
#   2) "Abrir la app"   -> maximiza la misma ventana y carga la PWA completa.
#      "Solo servidor"  -> oculta la ventana, muestra UNA ventana aparte con
#                          SOLO los QRs (/qr-solo, sin menú) y queda en bandeja.
#      "Consola"        -> lanza AlbionHelperConsole.exe (terminal visible) y
#                          SALE de todo: sin server, sin ventana, sin bandeja.
#   3) Al cerrar la ventana de la app, pregunta SIEMPRE:
#        - Sí      -> cerrar por completo (detiene el TÚNEL, apaga server
#                     y sale: cero procesos huérfanos, garantizado también
#                     con Job Object ante crash/Task Manager)
#        - No      -> minimizar a la bandeja (el server sigue activo)
#        - Cancelar-> seguir con la ventana
#   Bandeja (junto al reloj): volver a abrir, ver QR (ventana de solo-QR),
#   túnel on/off, salir.
#   El menú de la bandeja muestra el estado real del túnel (check + texto) y el
#   anillo del ícono cambia de color (verde = túnel activo).
#
#   Modo --server (headless): abre la ventana de SOLO QRs + bandeja.
#   Equivalente a elegir "Solo servidor".

import ctypes
import os
import socket
import subprocess
import sys
import threading
import time
import urllib.request

import webview

import flask_app

PORT = flask_app.PORT
HOST = flask_app.HOST

APP_URL = f"http://127.0.0.1:{PORT}/"
CONFIG_URL = f"http://127.0.0.1:{PORT}/config"
QR_SOLO_URL = f"http://127.0.0.1:{PORT}/qr-solo"

# Estado global compartido entre el hilo del webview, el de la bandeja y el main.
_window = None                # ventana webview principal (launcher / app / config)
_qr_window = None             # ventana de solo-QR (creada oculta desde el inicio)
_tray = None                  # icono pystray
_cerrar_programatico = False  # True = el cierre lo dispara el código (no preguntar)
_relevo_hecho = False         # True = la ventana principal ya se mostró tras cargar

_MUTEX = "AlbionHelper_InstanciaUnica"
_kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)


# ─── Cierre real: hijos mueren con el proceso ──────────────────
class _JOB_BASIC_LIMIT(ctypes.Structure):
    _fields_ = [
        ("PerProcessUserTimeLimit", ctypes.c_int64),
        ("PerJobUserTimeLimit", ctypes.c_int64),
        ("LimitFlags", ctypes.c_uint32),
        ("MinimumWorkingSetSize", ctypes.c_size_t),
        ("MaximumWorkingSetSize", ctypes.c_size_t),
        ("ActiveProcessLimit", ctypes.c_uint32),
        ("Affinity", ctypes.c_size_t),
        ("PriorityClass", ctypes.c_uint32),
        ("SchedulingClass", ctypes.c_uint32),
    ]


class _IO_COUNTERS(ctypes.Structure):
    _fields_ = [(nombre, ctypes.c_uint64) for nombre in (
        "ReadOperationCount", "WriteOperationCount", "OtherOperationCount",
        "ReadTransferCount", "WriteTransferCount", "OtherTransferCount")]


class _JOB_EXT_LIMIT(ctypes.Structure):
    _fields_ = [
        ("BasicLimitInformation", _JOB_BASIC_LIMIT),
        ("IoInfo", _IO_COUNTERS),
        ("ProcessMemoryLimit", ctypes.c_size_t),
        ("JobMemoryLimit", ctypes.c_size_t),
        ("PeakProcessMemoryUsed", ctypes.c_size_t),
        ("PeakJobMemoryUsed", ctypes.c_size_t),
    ]


_job_handle = None


def _hijos_mueren_conmigo():
    """Job Object con KILL_ON_JOB_CLOSE asignado a ESTE proceso.

    Todo hijo que se lance después (cloudflared) hereda el job: si este
    proceso muere de CUALQUIER forma (cierre normal, crash, Task Manager,
    apagado de Windows), el SO cierra el handle del job y mata a los hijos.
    Así el 'cierre real' deja de depender solo del código de limpieza.
    """
    global _job_handle
    try:
        # Prototipos explícitos: sin ellos ctypes trunca los HANDLE de
        # 64 bits (GetCurrentProcess() devuelve -1 y quedaba inválido).
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel32.CreateJobObjectW.restype = ctypes.c_void_p
        kernel32.CreateJobObjectW.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
        kernel32.SetInformationJobObject.argtypes = [
            ctypes.c_void_p, ctypes.c_int, ctypes.c_void_p, ctypes.c_uint32]
        kernel32.GetCurrentProcess.restype = ctypes.c_void_p
        kernel32.GetCurrentProcess.argtypes = []
        kernel32.AssignProcessToJobObject.argtypes = [
            ctypes.c_void_p, ctypes.c_void_p]

        hjob = kernel32.CreateJobObjectW(None, None)
        if not hjob:
            return
        info = _JOB_EXT_LIMIT()
        # KILL_ON_JOB_CLOSE | BREAKAWAY_OK: los hijos heredan el job y mueren
        # con nosotros (cloudflared), pero quien pida explícitamente escapar
        # (CREATE_BREAKAWAY_FROM_JOB, ej. la consola) queda vivo.
        # Valores de winnt.h: KILL_ON_JOB_CLOSE=0x2000, BREAKAWAY_OK=0x800.
        info.BasicLimitInformation.LimitFlags = 0x00002000 | 0x00000800
        if not kernel32.SetInformationJobObject(
                hjob, 9,  # JobObjectExtendedLimitInformation
                ctypes.byref(info), ctypes.sizeof(info)):
            return
        if not kernel32.AssignProcessToJobObject(
                hjob, kernel32.GetCurrentProcess()):
            return
        _job_handle = hjob  # vivo mientras vivamos; al morir, el SO lo cierra
    except Exception:
        pass


# ─── Splash / instancia única ────────────────────────────────
def _instancia_duplicada():
    """True si ya hay OTRA instancia corriendo (mutex de Windows)."""
    ERROR_ALREADY_EXISTS = 183
    _kernel32.CreateMutexW(None, False, _MUTEX)
    return ctypes.get_last_error() == ERROR_ALREADY_EXISTS


def _log_splash(mensaje):
    """Bitácora del relevo splash->contenido (diagnóstico temporal)."""
    try:
        print("[splash] " + mensaje, file=sys.stderr, flush=True)
    except Exception:
        pass


def _cerrar_splash(*_args):
    """Cierra el splash de PyInstaller (no-op en dev o sin --splash).

    Se engancha al evento shown de cada ventana: cuando la primera
    ventana real aparece, el splash deja de tener razón de ser.
    """
    try:
        import pyi_splash  # modulo solo presente en el exe compilado con --splash
        pyi_splash.close()
        _log_splash("pyi_splash.close ok")
    except Exception as exc:
        _log_splash("cerrar_splash fallo: " + repr(exc))


def _relevo_contenido():
    """Muestra la ventana principal recién cuando el contenido está pintado.

    La ventana nace OCULTA: mientras carga, en pantalla solo existe el
    splash de PyInstaller (el telón cubre TODO el escenario, no un dedo).
    Cuando la página avisa por api.splash_listo(), se muestra la ventana
    y en el mismo golpe cae el splash: nunca hay ventana vacía ni
    asomando detrás del arte. Idempotente: launcher y qr-solo pueden
    avisar; gana el primero. También lo usa el timer de seguridad de 15s.
    """
    global _relevo_hecho
    if _relevo_hecho:
        return
    _relevo_hecho = True
    try:
        if _window is not None:
            _window.show()
            _log_splash("ventana principal mostrada")
    except Exception as exc:
        _log_splash("mostrar ventana fallo: " + repr(exc))
    _cerrar_splash()

# ─── Servidor ─────────────────────────────────────────────────
def _wait_for_server(timeout=30):
    """Bloquea hasta que Flask responde en el puerto."""
    start = time.time()
    while time.time() - start < timeout:
        try:
            s = socket.create_connection(("127.0.0.1", PORT), timeout=1)
            s.close()
            return True
        except OSError:
            time.sleep(0.5)
    return False


def _run_flask():
    """Corre Flask en un hilo daemon; muere cuando el proceso sale."""
    flask_app.app.run(host=HOST, port=PORT, threaded=True, debug=False)


def _shutdown_server():
    """Apaga Flask de forma suave por la ruta /shutdown."""
    try:
        urllib.request.urlopen(
            f"http://127.0.0.1:{PORT}/shutdown", timeout=3)
    except Exception:
        pass


def _apagar_todo():
    """Cierre REAL en un solo lugar: túnel -> bandeja -> server -> proceso.

    Único funnel de salida: lo llama main() cuando webview.start() retorna
    (cierre por la X con 'Sí', Salir de la bandeja, modo --server) y también
    ante excepciones del arranque (finally). Sin esto, cloudflared quedaba
    huérfano sirviendo la URL pública tras cerrar la app.
    """
    try:
        flask_app.detener_tunel_func()
    except Exception:
        pass
    global _tray
    if _tray is not None:
        try:
            _tray.stop()
        except Exception:
            pass
        _tray = None
    _shutdown_server()
    time.sleep(1)
    os._exit(0)


# ─── Diálogo de cierre ────────────────────────────────────────
def _on_closing(window=None):
    """Se dispara al apretar la X de la ventana (evento cancelable).

    Devuelve False para CANCELAR el cierre; None/True lo permite.
    """
    global _cerrar_programatico
    if _cerrar_programatico:
        return  # cierre disparado por el código: permitir sin preguntar

    MB_YESNOCANCEL = 0x00000003
    MB_ICONQUESTION = 0x00000020
    MB_DEFBUTTON3 = 0x00001000
    MB_SETFOREGROUND = 0x00010000
    res = ctypes.windll.user32.MessageBoxW(
        0,
        "¿Qué querés hacer?\n\n"
        "Sí      -> Cerrar por completo (apaga el servidor)\n"
        "No      -> Minimizar a la bandeja (el servidor sigue activo)\n"
        "Cancelar -> Seguir con la ventana",
        "Albion Helper",
        MB_YESNOCANCEL | MB_ICONQUESTION | MB_DEFBUTTON3 | MB_SETFOREGROUND,
    )
    IDYES = 6
    IDNO = 7
    if res == IDYES:
        # Cerrar por completo: hay que destruir AMBAS ventanas (principal y QR)
        # para que webview.start() retorne y main() apague el server.
        _cerrar_programatico = True
        if _qr_window is not None:
            try:
                _qr_window.destroy()
            except Exception:
                pass
        return  # permite el cierre -> webview.start() retorna -> apaga todo
    if res == IDNO:
        _crear_bandeja()
        # Ocultar la ventana DESPUÉS de que el handler termine (estamos en el hilo GUI).
        threading.Timer(0.3, lambda: _window.hide() if _window else None).start()
        return False  # cancela el cierre: la ventana no se destruye, queda viva
    return False  # Cancelar: sigue con la ventana


# ─── Bandeja ──────────────────────────────────────────────────
def _img_bandeja(anillo="#c9a227"):
    """Ícono 64x64: cuadrado oscuro + anillo de color (amarillo = túnel off)."""
    from PIL import Image, ImageDraw
    img = Image.new("RGB", (64, 64), "#1a1410")
    draw = ImageDraw.Draw(img)
    draw.ellipse([6, 6, 58, 58], fill=anillo)
    draw.ellipse([22, 22, 42, 42], fill="#1a1410")
    return img


def _actualizar_icono_bandeja():
    """Cambia el color del anillo según el estado real del túnel."""
    global _tray
    if _tray is None:
        return
    try:
        color = "#2ecc71" if flask_app.cloudflared_activo() else "#c9a227"
        _tray.icon = _img_bandeja(color)
    except Exception:
        pass


def _crear_bandeja():
    """Icono junto al reloj (pystray). Idempotente."""
    global _tray
    if _tray is not None:
        return
    try:
        import pystray
    except Exception:
        return
    _tray = pystray.Icon(
        "albion_helper",
        _img_bandeja(),
        "Albion Helper",
        pystray.Menu(
            pystray.MenuItem("Abrir Albion Helper", _tray_abrir, default=True),
            pystray.MenuItem("Ver QR / Configuración", _tray_qr),
            pystray.MenuItem(_label_tunel, _tray_tunel,
                             checked=_tunel_activo),
            pystray.MenuItem("Salir", _tray_salir),
        ),
    )
    threading.Thread(target=_tray.run, daemon=True).start()
    _actualizar_icono_bandeja()


def _tunel_activo(item=None):
    try:
        return flask_app.cloudflared_activo()
    except Exception:
        return False


def _label_tunel(item=None):
    return "Internet: Disponible" if _tunel_activo() else "Internet: No disponible"


def _mostrar_ventana(url):
    """Muestra (crea si hace falta) la ventana PRINCIPAL y carga la URL."""
    global _window
    try:
        if _window is None:
            _crear_ventana(url)
            return
        _window.show()
        _window.restore()
        _window.maximize()
        _window.load_url(url)
    except Exception:
        pass


def _mostrar_ventana_qr():
    """Muestra (crea si hace falta) la ventana de SOLO QRs."""
    global _qr_window
    try:
        if _qr_window is None:
            _crear_ventana_qr()
        w = _qr_window
        if w is None:
            return
        w.show()
        w.restore()
        w.load_url(QR_SOLO_URL)
    except Exception:
        pass


def _tray_abrir(icon=None, item=None):
    _mostrar_ventana(APP_URL)


def _tray_qr(icon=None, item=None):
    _mostrar_ventana_qr()


def _tray_tunel(icon=None, item=None):
    try:
        if flask_app.cloudflared_activo():
            flask_app.detener_tunel_func()
        else:
            flask_app.iniciar_tunel_func()
    except Exception:
        pass
    _actualizar_icono_bandeja()


def _tray_salir(icon=None, item=None):
    global _cerrar_programatico
    _cerrar_programatico = True
    for w in (_window, _qr_window):
        if w is not None:
            try:
                w.destroy()
            except Exception:
                pass
    # El resto (túnel, bandeja, server, proceso) lo hace _apagar_todo()
    # cuando webview.start() retorne por la destrucción de las ventanas.


# ─── API expuesta a la página del launcher (pywebview.api.*) ──
class LauncherApi:
    def splash_listo(self):
        """La página avisa que ya está pintada: recién ahí muere el splash.

        Antes el splash se cerraba con events.shown (ventana EXISTE), lo que
        dejaba al usuario mirando una ventana vacía mientras la página
        terminaba de cargar. El relevo ahora es contenido listo -> cortina.
        """
        _log_splash("js llamo splash_listo")
        _relevo_contenido()

    def abrir_app(self):
        """Maximiza la ventana y carga la PWA completa."""
        if _window is None:
            return
        _window.maximize()
        _window.load_url(APP_URL)

    def solo_servidor(self):
        """Oculta la ventana principal, muestra la de SOLO QRs y queda en bandeja."""
        if _window is not None:
            try:
                _window.hide()
            except Exception:
                pass
        _mostrar_ventana_qr()
        _crear_bandeja()

    def abrir_consola(self):
        """Abre la consola y CIERRA todo lo demás (server, ventanas, bandeja)."""
        _lanzar_consola()
        _tray_salir()


def _popen_consola(cmd):
    """Lanza la consola FUERA del Job Object (BREAKAWAY).

    El proceso vive en un job KILL_ON_JOB_CLOSE para que cloudflared muera
    con la app; la consola debe SOBREVIVIR al cierre del launcher, así que
    pide CREATE_BREAKAWAY_FROM_JOB (requiere BREAKAWAY_OK en el job, seteado
    en _hijos_mueren_conmigo). Fallback sin flags si el entorno no permite
    el escape.
    """
    breakaway = getattr(subprocess, "CREATE_BREAKAWAY_FROM_JOB", 0x01000000)
    nueva_consola = getattr(subprocess, "CREATE_NEW_CONSOLE", 0x00000010)
    try:
        return subprocess.Popen(cmd,
                                creationflags=breakaway | nueva_consola)
    except OSError:
        return subprocess.Popen(cmd)


def _lanzar_consola():
    """Abre AlbionHelperConsole.exe (o python albion_helper.py en dev)."""
    try:
        if getattr(sys, "frozen", False):
            consola = os.path.join(os.path.dirname(sys.executable),
                                   "AlbionHelperConsole.exe")
            if os.path.exists(consola):
                _popen_consola([consola])
                return
            # Consola ausente en la carpeta portable: avisar en vez de
            # lanzarnos a nosotros mismos con argumentos de .py.
            ctypes.windll.user32.MessageBoxW(
                0,
                "No se encontró AlbionHelperConsole.exe junto al ejecutable.\n"
                "Usá la carpeta portable completa.",
                "Albion Helper",
                0x00000040,  # MB_ICONINFORMATION
            )
            return
        _popen_consola([sys.executable, "-X", "utf8", "albion_helper.py"])
    except Exception:
        pass


# ─── Ventanas ─────────────────────────────────────────────────
def _centrado_xy(ancho, alto):
    """Coordenadas para que una ventana anchoxalto quede centrada en pantalla.

    pywebview sin x/y abre la esquina superior izquierda: el launcher
    debe entrar centrado desde el primer píxel (simetría pedida).
    OJO: WinForms vuelve a escalar x/y por el DPI del sistema (medido:
    pasamos 750 físico y abrió en 937 = 750*1.25), así que acá se
    calcula en unidades lógicas dividiendo la pantalla por la escala.
    """
    try:
        u = ctypes.windll.user32
        sx = u.GetSystemMetrics(0)  # SM_CXSCREEN (físico: proceso DPI-aware)
        sy = u.GetSystemMetrics(1)  # SM_CYSCREEN
        try:
            escala = u.GetDpiForSystem() / 96.0
        except Exception:
            escala = 1.0
        if escala <= 0:
            escala = 1.0
        lx = int(sx / escala)
        ly = int(sy / escala)
        if lx <= ancho or ly <= alto:
            return None
        return ((lx - ancho) // 2, (ly - alto) // 2)
    except Exception:
        return None


def _crear_ventana(url=None):
    """Crea la ventana webview principal (launcher chico por defecto) y engancha el cierre."""
    global _window
    xy = _centrado_xy(420, 560)
    _window = webview.create_window(
        "Albion Helper",
        url or f"http://127.0.0.1:{PORT}/launcher",
        width=420,
        height=560,
        x=xy[0] if xy else None,
        y=xy[1] if xy else None,
        resizable=True,
        text_select=True,
        hidden=True,  # nace oculta: se muestra sola cuando el contenido está pintado
        background_color="#1a1410",  # nunca blanca: ni antes del CSS ni en el revelado
        js_api=LauncherApi(),
    )
    if _window is not None:
        _window.events.closing += _on_closing
        # El splash NO se cierra con events.shown: la página llama a
        # api.splash_listo() cuando ya está pintada (con timer de seguridad
        # de 15s en main() por si el puente JS falla).


def _crear_ventana_qr():
    """Crea la ventana de SOLO QRs (oculta al inicio; se muestra con "Solo servidor")."""
    global _qr_window
    xy_qr = _centrado_xy(460, 640)
    _qr_window = webview.create_window(
        "Albion Helper · QR",
        QR_SOLO_URL,
        width=460,
        height=640,
        x=xy_qr[0] if xy_qr else None,
        y=xy_qr[1] if xy_qr else None,
        resizable=True,
        text_select=True,
        hidden=True,
        background_color="#1a1410",
    )
    if _qr_window is not None:
        _qr_window.events.closing += _on_qr_closing
        # Mismo criterio: el splash lo cierra la página (api.splash_listo).


def _on_qr_closing(window=None):
    """Al cerrar la ventana de QRs con la X: ocultarla a la bandeja, no cerrar."""
    if _cerrar_programatico:
        return  # cierre programático: permitir
    _crear_bandeja()
    threading.Timer(0.3, lambda: _qr_window.hide() if _qr_window else None).start()
    return False  # cancela el cierre: la ventana queda viva, oculta


def _webview2_disponible():
    """True si el runtime de WebView2 está instalado.

    Es el único requisito del portable a nivel sistema (Windows 10/11 lo
    traen de fábrica vía Evergreen). Si falta, la ventana webview queda
    vacía sin explicación: mejor detectarlo y avisar.
    """
    try:
        import winreg
    except Exception:
        return True  # fuera de Windows (dev): no bloquear
    GUID = ("Microsoft\\EdgeUpdate\\Clients\\"
            "{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}")
    for vista in (
            (winreg.HKEY_LOCAL_MACHINE, "SOFTWARE\\WOW6432Node\\" + GUID),
            (winreg.HKEY_LOCAL_MACHINE, "SOFTWARE\\" + GUID),
            (winreg.HKEY_CURRENT_USER, "SOFTWARE\\" + GUID),
    ):
        try:
            with winreg.OpenKey(vista[0], vista[1]):
                return True
        except OSError:
            continue
    return False


# ─── Modos ────────────────────────────────────────────────────
def main():
    # 0) Una sola instancia: si ya hay otra, avisar y salir.
    if _instancia_duplicada():
        _cerrar_splash()  # este proceso también abre splash: no dejarlo colgado
        ctypes.windll.user32.MessageBoxW(
            0,
            "Albion Helper ya está en ejecución.\n"
            "Buscá la ventana abierta o el ícono junto al reloj.",
            "Albion Helper",
            0x00000040,  # MB_ICONINFORMATION
        )
        return

    # 0.0) Requisito del sistema: WebView2 (ventana web). Sin él la app
    # abriría una ventana vacía; avisamos con instrucción clara.
    if not _webview2_disponible():
        _cerrar_splash()
        ctypes.windll.user32.MessageBoxW(
            0,
            "Albion Helper necesita el runtime 'Microsoft Edge WebView2'.\n\n"
            "Windows 10/11 suelen traerlo instalado. Instalalo desde\n"
            "Windows Update o descargando 'Evergreen Standalone Installer'\n"
            "del sitio oficial de Microsoft Edge WebView2.",
            "Albion Helper",
            0x00000030,  # MB_ICONWARNING
        )
        return

    # 0.1) Cierre real a nivel SO: todo hijo (cloudflared) muere con nosotros
    # aunque el proceso se termine por crash o desde el Task Manager.
    _hijos_mueren_conmigo()

    # Red de seguridad: si ninguna ventana llegara a mostrarse,
    # el splash nunca vive más de 15 segundos.
    _timer_splash = threading.Timer(15.0, _relevo_contenido)
    _timer_splash.daemon = True
    _timer_splash.start()

    # 1) Levantar Flask en hilo separado (daemon: se apaga con el proceso)
    threading.Thread(target=_run_flask, daemon=True).start()

    # 2) Esperar a que el server esté listo
    if not _wait_for_server():
        print("No se pudo iniciar el servidor a tiempo.", file=sys.stderr)
        sys.exit(1)

    try:
        # 3) Modo --server (headless): ventana de SOLO QRs + bandeja,
        #    equivalente a elegir "Solo servidor". Nunca abre el navegador.
        if "--server" in sys.argv:
            _crear_bandeja()
            _mostrar_ventana_qr()
        else:
            # 4) Ventana launcher (pregunta qué abrir) + ventana de QRs oculta
            _crear_ventana()
            _crear_ventana_qr()

        # 5) Event loop de webview (bloqueante). Retorna cuando TODAS las
        #    ventanas se cierran (la principal se oculta en "solo"/"consola",
        #    no se destruye; la de QRs también; el cierre por completo las
        #    destruye).
        webview.start()
    finally:
        # 6) Cierre por completo: túnel, bandeja, server y proceso.
        _apagar_todo()


if __name__ == "__main__":
    main()