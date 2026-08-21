# build.py — Empaquetado portable de Albion Helper (PyInstaller onedir)
# ─────────────────────────────────────────────────────────────────
# Genera dos exes en dist/AlbionHelper/ (todo portable, sin instalar nada):
#   AlbionHelper.exe         -> lanzador GUI + modo --server (web Flask)
#   AlbionHelperConsole.exe  -> consola original (con ventana de terminal)
# Datos editables junto al exe: templates/, static/, albion_config.json,
# catalog.json, version.txt, cloudflared.exe.
#
# Uso:  python -X utf8 build.py

import os
import shutil
import subprocess
import sys
import time

BASE = os.path.dirname(os.path.abspath(__file__))
DIST = os.path.join(BASE, "dist", "AlbionHelper")
PYTHON = sys.executable

# Archivos/dirs que van JUNTO al exe (BASE_DIR portable los lee ahi).
DATOS = [
    "templates", "static",
    "albion_config.json", "catalog.json", "version.txt",
]

# cloudflared.exe es opcional (tunel); si existe en TEMP lo copiamos.
CLOUDFLARED_TEMP = os.path.join(os.environ.get("TEMP", ""), "cloudflared.exe")


def run_pyinstaller(entry, name, console, hidden_imports=None, splash=None):
    """Corre PyInstaller onedir para `entry` -> dist/<name>/<name>.exe."""
    cmd = [
        PYTHON, "-m", "PyInstaller",
        "--noconfirm", "--onedir", "--clean",
        "--name", name,
        "--distpath", os.path.join(BASE, "dist"),
        "--workpath", os.path.join(BASE, "build"),
        "--specpath", os.path.join(BASE, "build"),
    ]
    if not console:
        cmd.append("--windowed")
    if splash:
        # Splash de arranque (ventana nativa mientras se carga el exe).
        cmd += ["--splash", splash]
    for h in (hidden_imports or []):
        cmd.append("--hidden-import")
        cmd.append(h)
    cmd.append(entry)
    print(f"\n=== PyInstaller: {name} ===")
    # El antivirus (Defender) a veces bloquea un DLL recién copiado durante
    # el COLLECT; reintentar suele bastar porque el Analysis queda cacheado.
    for intento in range(1, 4):
        resultado = subprocess.run(cmd, cwd=BASE)
        if resultado.returncode == 0:
            return
        print(f"intento {intento} fallo (exit {resultado.returncode}); "
              + ("reintento..." if intento < 3 else "abandonamos."))
        time.sleep(6)
    raise SystemExit(f"PyInstaller falló para {name} tras 3 intentos")


def main():
    splash = os.path.join(BASE, "splash.png")

    # 1) Entry point de la app PWA (Flask + ventana webview launcher + bandeja)
    run_pyinstaller(os.path.join(BASE, "app.py"), "AlbionHelper", console=False,
                    hidden_imports=["webview", "pystray", "PIL"],
                    splash=splash if os.path.exists(splash) else None)

    # 2) Consola (con terminal) — usa albion_helper.py original
    run_pyinstaller(os.path.join(BASE, "albion_helper.py"), "AlbionHelperConsole",
                    console=True)

    # 3) Mover la consola dentro de la carpeta del lanzador
    consola_dir = os.path.join(BASE, "dist", "AlbionHelperConsole")
    os.makedirs(DIST, exist_ok=True)
    shutil.move(os.path.join(consola_dir, "AlbionHelperConsole.exe"),
                os.path.join(DIST, "AlbionHelperConsole.exe"))
    shutil.rmtree(consola_dir, ignore_errors=True)

    # 4) Copiar datos editables junto al exe
    for item in DATOS:
        src = os.path.join(BASE, item)
        if os.path.exists(src):
            dst = os.path.join(DIST, item)
            if os.path.isdir(src):
                shutil.copytree(src, dst, dirs_exist_ok=True)
            else:
                shutil.copy2(src, dst)
            print(f"copiado: {item}")

    # 5) cloudflared.exe opcional (para el tunel)
    if os.path.exists(CLOUDFLARED_TEMP):
        shutil.copy2(CLOUDFLARED_TEMP, os.path.join(DIST, "cloudflared.exe"))
        print("copiado: cloudflared.exe")
    else:
        print("AVISO: cloudflared.exe no encontrado en TEMP — el tunel no funcionara.")

    print(f"\nListo. Carpeta portable: {DIST}")


if __name__ == "__main__":
    main()