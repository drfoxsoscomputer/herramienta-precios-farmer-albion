# app.py — Entry point del executable portátil.
# Al ejecutarse: levanta el servidor Flask y abre una ventana tipo app (pywebview)
# maximizada apuntando a http://127.0.0.1:8081/. Cuando se cierra la ventana,
# el servidor se apaga y el proceso termina.

import socket
import sys
import threading
import time
import urllib.request

import webview

import flask_app

PORT = flask_app.PORT
HOST = flask_app.HOST


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


def main():
    # 1) Levantar Flask en hilo separado (daemon: se apaga con el proceso)
    threading.Thread(target=_run_flask, daemon=True).start()

    # 2) Esperar a que el server esté listo
    if not _wait_for_server():
        print("No se pudo iniciar el servidor a tiempo.", file=sys.stderr)
        sys.exit(1)

    # 3) Ventana tipo app maximizada apuntando a la PWA local.
    #    webview usa WebView2 (Edge runtime); el manifest display:standalone
    #    se respeta dentro de la ventana.
    webview.create_window(
        "Albion Helper",
        f"http://127.0.0.1:{PORT}/",
        maximized=True,   # abre maximizada, como pediste
        resizable=True,
        text_select=True, # permite seleccionar texto en la ventana
    )

    # 4) Event loop de webview (bloqueante). Retorna al cerrar la ventana.
    webview.start()

    # 5) Ventana cerrada → apagar server y salir.
    _shutdown_server()
    time.sleep(1)


if __name__ == "__main__":
    main()