# albion_helper.py — PUNTO DE ENTRADA
# ─────────────────────────────────────────────────────────────
# Este archivo solo: carga config, maximiza la ventana y arranca
# el menu. Toda la logica vive en los modulos:
#   constants.py  -> datos fijos
#   api.py        -> acceso a la red
#   formatting.py -> formateo y colores (funciones puras)
#   menus.py      -> interfaz de usuario

import ctypes
import json
import os
import sys

from rich.console import Console

from menus import menu_principal

# ─── Maximizar ventana ───────────────────────────────────────
try:
    kernel32 = ctypes.windll.kernel32
    user32 = ctypes.windll.user32
    hwnd = kernel32.GetConsoleWindow()
    if hwnd:
        user32.ShowWindow(hwnd, 3)  # SW_MAXIMIZE = 3
except Exception:
    pass

# ─── Config ───────────────────────────────────────────────────
if getattr(sys, "frozen", False):
    _BASE = os.path.dirname(sys.executable)
else:
    _BASE = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(_BASE, "albion_config.json")

console = Console()


def load_config():
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        console.print(f"[red]Error cargando configuracion: {e}[/]")
        sys.exit(1)


# ─── Entry ────────────────────────────────────────────────────
def main():
    config = load_config()
    menu_principal(config)


if __name__ == "__main__":
    main()
