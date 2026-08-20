# app.py — Entry point del executable portátil.
# ─────────────────────────────────────────────────────────────
# Flujo (todo dentro de la MISMA ventana, nunca abre el navegador):
#   1) Levanta Flask (hilo daemon) y abre UNA ventana chica (launcher)
#      que pregunta qué hacer: Abrir la app / Solo servidor / Consola.
#   2) "Abrir la app"   -> maximiza la misma ventana y carga la PWA completa.
#      "Solo servidor"  -> maximiza la ventana y carga /config (QR del túnel),
#                          queda en la bandeja.
#      "Consola"        -> oculta la ventana, abre AlbionHelperConsole.exe
#                          (terminal visible) y queda en la bandeja.
#   3) Al cerrar la ventana de la app, pregunta SIEMPRE:
#        - Sí      -> cerrar por completo (apaga server y sale)
#        - No      -> minimizar a la bandeja (el server sigue activo)
#        - Cancelar-> seguir con la ventana
#   Bandeja (junto al reloj): volver a abrir, ver QR/config, túnel on/off, salir.
#   El menú de la bandeja muestra el estado real del túnel (check + texto) y el
#   anillo del ícono cambia de color (verde = túnel activo).
#
#   Modo --server (headless): crea la ventana directamente en /config (QR) y
#   deja la bandeja activa. Equivalente a elegir "Solo servidor".

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

# Estado global compartido entre el hilo del webview, el de la bandeja y el main.
_window = None                # ventana webview actual (None si fue destruida)
_tray = None                  # icono pystray
_cerrar_programatico = False  # True = el cierre lo dispara el código (no preguntar)

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


# ─── Diálogo de cierre ────────────────────────────────────────
def _on_closing(window=None):
    """Se dispara al apretar la X de la ventana (evento cancelable).

    Devuelve False para CANCELAR el cierre; None/True lo permite.
    """
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
    return "Túnel: Activo" if _tunel_activo() else "Túnel: Inactivo"


def _mostrar_ventana(url):
    """Muestra (crea si hace falta) la ventana y carga la URL indicada."""
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


def _tray_abrir(icon=None, item=None):
    _mostrar_ventana(APP_URL)


def _tray_qr(icon=None, item=None):
    _mostrar_ventana(CONFIG_URL)


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
    if _window is not None:
        try:
            _window.destroy()
        except Exception:
            pass
    if _tray is not None:
        try:
            _tray.stop()
        except Exception:
            pass
    _shutdown_server()
    time.sleep(1)
    os._exit(0)


# ─── API expuesta a la página del launcher (pywebview.api.*) ──
class LauncherApi:
    def abrir_app(self):
        """Maximiza la ventana y carga la PWA completa."""
        if _window is None:
            return
        _window.maximize()
        _window.load_url(APP_URL)

    def solo_servidor(self):
        """Maximiza la ventana en /config (QR del túnel) y queda en bandeja."""
        _mostrar_ventana(CONFIG_URL)
        _crear_bandeja()

    def abrir_consola(self):
        """Oculta la ventana, abre la consola y queda en bandeja."""
        if _window is not None:
            try:
                _window.hide()
            except Exception:
                pass
        _crear_bandeja()
        _lanzar_consola()


def _lanzar_consola():
    """Abre AlbionHelperConsole.exe (o python albion_helper.py en dev)."""
    try:
        if getattr(sys, "frozen", False):
            consola = os.path.join(os.path.dirname(sys.executable),
                                   "AlbionHelperConsole.exe")
            if os.path.exists(consola):
                subprocess.Popen([consola])
                return
        subprocess.Popen([sys.executable, "-X", "utf8", "albion_helper.py"])
    except Exception:
        pass


# ─── Ventana ──────────────────────────────────────────────────
def _crear_ventana(url=None):
    """Crea la ventana webview (launcher chico por defecto) y engancha el cierre."""
    global _window
    _window = webview.create_window(
        "Albion Helper",
        url or f"http://127.0.0.1:{PORT}/launcher",
        width=420,
        height=560,
        resizable=True,
        text_select=True,
        js_api=LauncherApi(),
    )
    if _window is not None:
        _window.events.closing += _on_closing


# ─── Modos ────────────────────────────────────────────────────
def main():
    # 1) Levantar Flask en hilo separado (daemon: se apaga con el proceso)
    threading.Thread(target=_run_flask, daemon=True).start()

    # 2) Esperar a que el server esté listo
    if not _wait_for_server():
        print("No se pudo iniciar el servidor a tiempo.", file=sys.stderr)
        sys.exit(1)

    # 3) Modo --server (headless): ventana directa en /config (QR) + bandeja,
    #    equivalente a elegir "Solo servidor". Nunca abre el navegador.
    if "--server" in sys.argv:
        _crear_bandeja()
        _crear_ventana(CONFIG_URL)
        webview.start()
        _shutdown_server()
        time.sleep(1)
        return

    # 4) Ventana launcher (pregunta qué abrir)
    _crear_ventana()

    # 5) Event loop de webview (bloqueante). Retorna cuando la ventana se cierra
    #    por completo (la ventana nunca se destruye en "solo"/"consola": solo se
    #    oculta o se recarga en otra URL, así que acá siempre es cierre real).
    webview.start()

    # 6) Cierre por completo
    _shutdown_server()
    time.sleep(1)


if __name__ == "__main__":
    main()