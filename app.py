# app.py — Entry point web (NiceGUI) de Albion Helper
# ─────────────────────────────────────────────────────────────
# Fase 1 de la migracion: las pantallas de consola (menus.py) pasan
# a una web local servida por NiceGUI. La logica de datos se reutiliza
# tal cual (api.py, formatting.py, textos.py): este archivo solo carga
# el config, detecta la IP de la LAN y arranca el servidor.
#
# Regla importante: ui.run() SOLO se ejecuta al correr este archivo
# como script (__main__). Importar app.py no debe arrancar el server.

import json
import os
import socket
import sys

# El directorio de este script va primero en sys.path para que los
# imports de modulos hermanos (webui, api, formatting...) funcionen
# sin importar desde donde se invoque el script.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "albion_config.json")

HOST = "0.0.0.0"
PORT = 8080


def load_config():
    """Carga albion_config.json (misma carpeta que este archivo)."""
    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def ip_lan():
    """Detecta la IP local de la LAN para que el celular abra la web.

    Truco clasico: abrir un socket UDP "conectado" a un destino externo
    no envia trafico, pero el SO elige la interfaz de salida y expone la
    IP local en getsockname(). Si no hay red, cae a localhost.
    """
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            s.connect(("8.8.8.8", 80))
            return s.getsockname()[0]
        finally:
            s.close()
    except OSError:
        return "127.0.0.1"


def main():
    """Carga config, inyecta en webui y arranca el servidor web."""
    config = load_config()
    ip = ip_lan()

    import webui
    webui.set_config(config, ip_lan=ip, port=PORT)

    from nicegui import ui
    ui.run(host=HOST, port=PORT, reload=False, show=True)


if __name__ == "__main__":
    main()
