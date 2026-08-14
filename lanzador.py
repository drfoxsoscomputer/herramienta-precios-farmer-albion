# lanzador.py — Lanzador desktop de Albion Helper (tkinter + pystray)
# ─────────────────────────────────────────────────────────────────
# Ventana que supervisa el server web (Flask en 8081), controla el
# tunel Cloudflare (cloudflared), muestra el QR, abre el navegador,
# ejecuta la consola, busca actualizaciones y minimiza a la bandeja.
# Primer arranque: wizard (elegir carpeta + acceso directo + navegador/PWA).
#
# Regla de oro: los procesos hijos (Flask, cloudflared) viven mientras
# esta ventana esta abierta. Se cierran solos al salir del lanzador.

import os
import re
import sys
import json
import socket
import subprocess
import threading
import webbrowser
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from PIL import Image

import qrcode
import requests

try:
    import pystray
    HAS_PYSTRAY = True
except Exception:
    HAS_PYSTRAY = False

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
VERSION_FILE = os.path.join(BASE_DIR, "version.txt")
CONFIG_LAUNCHER = os.path.join(BASE_DIR, "lanzador_config.json")
TUN_URL_FILE = os.path.join(BASE_DIR, "tun_url.txt")
CLOUDFLARED = os.path.join(BASE_DIR, "cloudflared.exe")
REPO = "drfoxsoscomputer/herramienta-precios-farmer-albion"
PORT = 8081
HOST = "0.0.0.0"


# ─── Utilidades ─────────────────────────────────────────────────
def leer_version():
    try:
        with open(VERSION_FILE, "r", encoding="utf-8") as f:
            return f.read().strip()
    except Exception:
        return "0.0.0"


def guardar_version(texto):
    with open(VERSION_FILE, "w", encoding="utf-8") as f:
        f.write(texto.strip())


def ip_lan():
    """IP local de la LAN (mismo truco que flask_app.py)."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            s.connect(("8.8.8.8", 80))
            return s.getsockname()[0]
        finally:
            s.close()
    except OSError:
        return "127.0.0.1"


def url_local():
    return f"http://{ip_lan()}:{PORT}/"


def leer_tun_url():
    try:
        with open(TUN_URL_FILE, "r", encoding="utf-8") as f:
            return f.read().strip()
    except Exception:
        return ""


def server_activo():
    """True si Flask responde en el puerto."""
    try:
        s = socket.create_connection(("127.0.0.1", PORT), timeout=1.5)
        s.close()
        return True
    except OSError:
        return False


def cloudflared_activo():
    """True si hay un proceso cloudflared corriendo."""
    try:
        out = subprocess.run(
                ["tasklist", "/FI", "IMAGENAME eq cloudflared.exe"],
                capture_output=True, text=True, encoding="utf-8",
                errors="replace", timeout=10,
                creationflags=subprocess.CREATE_NO_WINDOW,
            ).stdout
        return "cloudflared.exe" in out
    except Exception:
        return False


# ─── Control de procesos ────────────────────────────────────────
class Servicios:
    """Posee los procesos Flask y cloudflared. Al salir, los termina."""

    def __init__(self):
        self.flask_proc = None
        self.cloud_proc = None
        self._lock = threading.Lock()

    def _cmd_flask(self):
        """Comando para levantar el server: en dev python flask_app.py,
        empaquetado el MISMO exe con --server."""
        if getattr(sys, "frozen", False):
            return [sys.executable, "--server"]
        return [sys.executable, "-X", "utf8", "flask_app.py"]

    def iniciar_flask(self):
        """Lanza Flask desacoplado (puede quedar como proceso independiente)."""
        with self._lock:
            if server_activo():
                return True
            try:
                args = self._cmd_flask()
                self.flask_proc = subprocess.Popen(
                    args,
                    cwd=BASE_DIR,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    creationflags=subprocess.CREATE_NO_WINDOW,
                )
                return True
            except Exception:
                return False

    def detener_flask(self):
        with self._lock:
            if self.flask_proc:
                try:
                    self.flask_proc.terminate()
                except Exception:
                    pass
                self.flask_proc = None
            # proceso independiente (si quedo huérfano tras mi sesión):
            self._matar_puerto(PORT)

    def iniciar_tunel(self):
        """Lanza cloudflared desacoplado apuntando a localhost:PORT.

        Redirige su salida a tun.log para poder leer la URL trycloudflare
        nueva (cambia en cada reinicio).
        """
        with self._lock:
            if cloudflared_activo():
                return True
            if not os.path.exists(CLOUDFLARED):
                return False
            try:
                log = open(os.path.join(BASE_DIR, "tun.log"), "w", encoding="utf-8")
                args = [CLOUDFLARED, "tunnel", "--url", f"http://localhost:{PORT}",
                        "--no-autoupdate"]
                self.cloud_proc = subprocess.Popen(
                    args,
                    cwd=BASE_DIR,
                    stdout=log,
                    stderr=subprocess.STDOUT,
                    creationflags=subprocess.CREATE_NO_WINDOW,
                )
                return True
            except Exception:
                return False

    def detener_tunel(self):
        with self._lock:
            if self.cloud_proc:
                try:
                    self.cloud_proc.terminate()
                except Exception:
                    pass
                self.cloud_proc = None
            subprocess.run(["taskkill", "/F", "/IM", "cloudflared.exe"],
                           capture_output=True, timeout=10,
                           creationflags=subprocess.CREATE_NO_WINDOW)

    def _matar_puerto(self, port):
        """Mata el proceso que ocupa `port` (para no dejar server huerfano)."""
        try:
            out = subprocess.run(
                ["netstat", "-ano"], capture_output=True, text=True,
                encoding="utf-8", errors="replace", timeout=15,
                creationflags=subprocess.CREATE_NO_WINDOW,
            ).stdout
            pids = set()
            for linea in out.splitlines():
                if f":{port}" in linea and "LISTENING" in linea:
                    partes = linea.split()
                    if partes:
                        pids.add(partes[-1])
            for pid in pids:
                subprocess.run(["taskkill", "/F", "/PID", pid],
                               capture_output=True, timeout=10,
                               creationflags=subprocess.CREATE_NO_WINDOW)
        except Exception:
            pass

    def detener_todo(self):
        self.detener_flask()
        self.detener_tunel()


# ─── QR ─────────────────────────────────────────────────────────
def generar_qr(url, size=220):
    """Devuelve una Image PIL con el QR de `url`."""
    img = qrcode.make(url)  # type: ignore[attr-defined]
    img = img.resize((size, size), Image.Resampling.NEAREST)  # type: ignore[attr-defined]
    return img


# ─── Actualizaciones ────────────────────────────────────────────
def buscar_actualizaciones():
    """Compara version local vs ultima release de GitHub.

    Devuelve (disponible: bool, version_remota: str, url_descarga: str).
    """
    local = leer_version()
    try:
        r = requests.get(
            f"https://api.github.com/repos/{REPO}/releases/latest",
            timeout=10,
        )
        if r.status_code != 200:
            return False, "", ""
        data = r.json()
        remota = data.get("tag_name", "").lstrip("v")
        if not remota:
            return False, "", ""
        url = ""
        for asset in data.get("assets", []):
            if asset.get("name", "").endswith(".zip"):
                url = asset.get("browser_download_url", "")
                break
        if not url:
            url = data.get("zipball_url", "")
        return _version_mayor(remota, local), remota, url
    except Exception:
        return False, "", ""


def _version_mayor(a, b):
    """True si la version a > b (comparacion semantica simple)."""
    pa = [int(x) for x in re.findall(r"\d+", a)][:3]
    pb = [int(x) for x in re.findall(r"\d+", b)][:3]
    pa += [0] * (3 - len(pa))
    pb += [0] * (3 - len(pb))
    return tuple(pa) > tuple(pb)


# ─── Wizard primer arranque ─────────────────────────────────────
def primer_arranque(parent):
    """Si no hay config del lanzador, muestra el wizard de bienvenida.

    Pasos: elegir carpeta (por defecto la actual) + crear acceso directo
    (escritorio / inicio / ambos / ninguno) + abrir en navegador o PWA.
    """
    if os.path.exists(CONFIG_LAUNCHER):
        return

    cfg = {"carpeta": BASE_DIR, "acceso": "ninguno", "abrir": "navegador"}

    win = tk.Toplevel(parent)
    win.title("Albion Helper — Primer arranque")
    win.geometry("560x420")
    win.resizable(False, False)
    win.grab_set()
    win.transient(parent)

    tk.Label(win, text="¡Bienvenido a Albion Helper!",
             font=("Segoe UI", 16, "bold")).pack(pady=(18, 4))
    tk.Label(win, text="Elige dónde guardar el programa y cómo deseas usarlo.",
             font=("Segoe UI", 10)).pack(pady=(0, 14))

    # Carpeta
    frame_dir = ttk.LabelFrame(win, text="  Carpeta de instalación  ")
    frame_dir.pack(fill="x", padx=20, pady=6)
    var_dir = tk.StringVar(value=cfg["carpeta"])
    tk.Entry(frame_dir, textvariable=var_dir, width=52).pack(side="left", padx=8, pady=8)
    ttk.Button(frame_dir, text="Examinar...",
               command=lambda: var_dir.set(filedialog.askdirectory(
                   initialdir=cfg["carpeta"]))).pack(side="left", padx=4)

    # Acceso directo
    frame_acc = ttk.LabelFrame(win, text="  Acceso directo  ")
    frame_acc.pack(fill="x", padx=20, pady=6)
    var_acc = tk.StringVar(value="ninguno")
    for valor, label in [("escritorio", "Escritorio"),
                         ("inicio", "Menú Inicio"),
                         ("ambos", "Ambos"),
                         ("ninguno", "No crear")]:
        ttk.Radiobutton(frame_acc, text=label, value=valor,
                        variable=var_acc).pack(anchor="w", padx=10)

    # Abrir en navegador o PWA
    frame_abr = ttk.LabelFrame(win, text="  Al iniciar el servidor  ")
    frame_abr.pack(fill="x", padx=20, pady=6)
    var_abr = tk.StringVar(value="navegador")
    ttk.Radiobutton(frame_abr, text="Abrir en el navegador",
                    value="navegador", variable=var_abr).pack(anchor="w", padx=10)
    ttk.Radiobutton(frame_abr, text="Instalar como app (PWA)",
                    value="pwa", variable=var_abr).pack(anchor="w", padx=10)
    ttk.Radiobutton(frame_abr, text="No abrir nada",
                    value="nada", variable=var_abr).pack(anchor="w", padx=10)

    def finalizar():
        cfg["carpeta"] = var_dir.get().strip() or BASE_DIR
        cfg["acceso"] = var_acc.get()
        cfg["abrir"] = var_abr.get()
        with open(CONFIG_LAUNCHER, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=2)
        win.destroy()

    ttk.Button(win, text="Listo", command=finalizar).pack(pady=14)


def crear_acceso_directo(acc):
    """Crea accesos directos segun la eleccion del wizard."""
    if not acc or acc == "ninguno":
        return

    vbs = os.path.join(os.environ.get("TEMP", BASE_DIR), "albion_lnk.vbs")
    targets = []
    # En PyInstaller (--onedir) el exe es el target; en dev, python + script.
    if getattr(sys, "frozen", False):
        exe = sys.executable
        args = ""
    else:
        exe = sys.executable
        args = os.path.join(BASE_DIR, "lanzador.py")
    if acc in ("escritorio", "ambos"):
        targets.append(os.path.join(os.path.expanduser("~"), "Desktop"))
    if acc in ("inicio", "ambos"):
        targets.append(os.path.join(os.environ.get("APPDATA", ""),
                                    "Microsoft", "Windows", "Start Menu",
                                    "Programs"))
    for carpeta in targets:
        lnk = os.path.join(carpeta, "Albion Helper.lnk")
        with open(vbs, "w", encoding="utf-8") as f:
            f.write(f"""
Set WshShell = WScript.CreateObject("WScript.Shell")
Set oShortcut = WshShell.CreateShortcut("{lnk}")
oShortcut.TargetPath = "{exe}"
oShortcut.Arguments = "{args}"
oShortcut.WorkingDirectory = "{BASE_DIR}"
oShortcut.IconLocation = "{exe},0"
oShortcut.Save
""")
        try:
            subprocess.run(["wscript.exe", vbs], capture_output=True,
                           timeout=15,
                           creationflags=subprocess.CREATE_NO_WINDOW)
        except Exception:
            pass


# ─── Ventana principal ──────────────────────────────────────────
class LanzadorApp:
    def __init__(self, root):
        self.root = root
        self.svc = Servicios()
        self.tun_url = leer_tun_url()
        self.tray = None
        self.root.title("Albion Helper")
        self.root.geometry("480x460")
        self.root.resizable(False, False)
        self._build_ui()
        self._pintar_estado()
        # wizard + acceso directo (solo primera vez)
        primer_arranque(self.root)
        try:
            cfg = json.load(open(CONFIG_LAUNCHER, encoding="utf-8"))
            crear_acceso_directo(cfg.get("acceso", "ninguno"))
        except Exception:
            pass
        self.root.after(3000, self._chequear_tunel)

    # UI
    def _build_ui(self):
        tk.Label(self.root, text="Albion Helper",
                 font=("Segoe UI", 18, "bold")).pack(pady=(18, 2))
        tk.Label(self.root, text=f"Versión {leer_version()} · Puerto {PORT}",
                 font=("Segoe UI", 9), fg="#666").pack(pady=(0, 12))

        # Estado
        self.lbl_estado = tk.Label(self.root, text="", font=("Segoe UI", 12, "bold"))
        self.lbl_estado.pack(pady=4)
        self.lbl_url = tk.Label(self.root, text="", font=("Segoe UI", 9), fg="#444")
        self.lbl_url.pack(pady=2)

        # Botones
        frame = ttk.Frame(self.root)
        frame.pack(pady=14, padx=30, fill="x")
        self.btn_web = ttk.Button(frame, text="Iniciar servidor web",
                                  command=self.toggle_web)
        self.btn_web.pack(fill="x", pady=3)
        self.btn_nav = ttk.Button(frame, text="Abrir en el navegador",
                                  command=self.abrir_navegador)
        self.btn_nav.pack(fill="x", pady=3)
        self.btn_qr = ttk.Button(frame, text="Ver QR",
                                 command=self.ver_qr)
        self.btn_qr.pack(fill="x", pady=3)
        self.btn_tun = ttk.Button(frame, text="Activar Cloudflare",
                                  command=self.toggle_tunel)
        self.btn_tun.pack(fill="x", pady=3)
        self.btn_cons = ttk.Button(frame, text="Ejecutar consola",
                                   command=self.abrir_consola)
        self.btn_cons.pack(fill="x", pady=3)
        self.btn_upd = ttk.Button(frame, text="Buscar actualizaciones",
                                  command=self.buscar_upd)
        self.btn_upd.pack(fill="x", pady=3)

        ttk.Button(self.root, text="Minimizar a la bandeja",
                   command=self.minimizar_a_bandeja).pack(pady=(6, 2))
        ttk.Button(self.root, text="Salir", command=self.salir).pack(pady=2)

    # Estado
    def _pintar_estado(self):
        web = server_activo()
        tun = cloudflared_activo()
        if web:
            self.lbl_estado.config(text="● Servidor web ACTIVO",
                                   fg="#1e7d32")
            self.btn_web.config(text="Detener servidor web")
        else:
            self.lbl_estado.config(text="○ Servidor web DETENIDO",
                                   fg="#b23b3b")
            self.btn_web.config(text="Iniciar servidor web")
        if tun:
            self.btn_tun.config(text="Desactivar Cloudflare")
            self.tun_url = leer_tun_url()
            self.lbl_url.config(text=f"Internet: {self.tun_url or 'activo (sin URL)'}")
        else:
            self.btn_tun.config(text="Activar Cloudflare")
            self.lbl_url.config(text=f"Local: {url_local()}")
        self.root.after(3000, self._pintar_estado)

    def _chequear_tunel(self):
        if server_activo():
            self.tun_url = leer_tun_url() or self.tun_url
        self.root.after(5000, self._chequear_tunel)

    # Acciones
    def toggle_web(self):
        if server_activo():
            self.svc.detener_flask()
        else:
            ok = self.svc.iniciar_flask()
            if not ok:
                messagebox.showerror("Error", "No se pudo iniciar el servidor web.")
        self._pintar_estado()

    def abrir_navegador(self):
        cfg = self._cargar_cfg()
        if cfg.get("abrir") == "pwa":
            self.abrir_pwa()
        else:
            url = self.tun_url or url_local()
            webbrowser.open(url)

    def abrir_pwa(self):
        """Abrir la web para que el navegador ofrezca 'Instalar app' (PWA)."""
        url = self.tun_url or url_local()
        webbrowser.open(url)
        messagebox.showinfo(
            "Instalar como app",
            "En el navegador busca el ícono de instalar (en la barra de "
            "direcciones o en el menú). Albion Helper se instalará como app "
            "y tendrá su propia ventana.",
        )

    def ver_qr(self):
        qr_win = tk.Toplevel(self.root)
        qr_win.title("QR de acceso")
        qr_win.resizable(False, False)
        url = self.tun_url or url_local()
        img = generar_qr(url)
        img_tk = _pil_a_tk(img)
        tk.Label(qr_win, image=img_tk).pack(padx=10, pady=(10, 2))
        tk.Label(qr_win, text=url, font=("Segoe UI", 9), fg="#444").pack(pady=(0, 8))
        qr_win.img = img_tk  # type: ignore[attr-defined]  # evitar GC

    def toggle_tunel(self):
        if cloudflared_activo():
            self.svc.detener_tunel()
        else:
            ok = self.svc.iniciar_tunel()
            if not ok:
                messagebox.showerror(
                    "Error",
                    "No se encontró cloudflared.exe junto al programa. "
                    "Descárgalo a la carpeta del proyecto.",
                )
        self._pintar_estado()
        if cloudflared_activo():
            threading.Thread(target=self._capturar_tun_url, daemon=True).start()

    def _capturar_tun_url(self):
        """Busca la URL trycloudflare en tun.log (salida de cloudflared).

        La URL cambia en cada reinicio; se guarda en tun_url.txt para que
        /config y el QR la usen.
        """
        import time
        time.sleep(8)
        try:
            url = self._url_desde_tunel()
            if url:
                with open(TUN_URL_FILE, "w", encoding="utf-8") as f:
                    f.write(url)
                self.tun_url = url
        except Exception:
            pass

    def _url_desde_tunel(self):
        """Lee la URL del tunel desde tun.log (patron trycloudflare.com)."""
        try:
            with open(os.path.join(BASE_DIR, "tun.log"), "r", encoding="utf-8",
                      errors="ignore") as f:
                texto = f.read()
            m = re.search(r"https://[a-z0-9-]+\.trycloudflare\.com", texto)
            return m.group(0) if m else ""
        except Exception:
            return ""

    def abrir_consola(self):
        """Lanza la consola: en dev python albion_helper.py, empaquetado el
        exe de consola que vive junto al lanzador."""
        if getattr(sys, "frozen", False):
            consola_exe = os.path.join(os.path.dirname(sys.executable),
                                       "AlbionHelperConsole.exe")
            if os.path.exists(consola_exe):
                subprocess.Popen([consola_exe], cwd=BASE_DIR)
                return
        subprocess.Popen(
            [sys.executable, "-X", "utf8", "albion_helper.py"],
            cwd=BASE_DIR,
        )

    def buscar_upd(self):
        disponible, remota, url = buscar_actualizaciones()
        if disponible:
            r = messagebox.askyesno(
                "Actualización disponible",
                f"Hay una versión nueva: v{remota} "
                f"(tu versión: v{leer_version()}).\n¿Descargar ahora?",
            )
            if r and url:
                self._descargar(url)
        else:
            messagebox.showinfo(
                "Actualizaciones",
                f"Estás al día (v{leer_version()}).",
            )

    def _descargar(self, url):
        destino = os.path.join(BASE_DIR, "actualizaciones")
        os.makedirs(destino, exist_ok=True)
        nombre = url.split("/")[-1] or f"albion-helper-v{leer_version()}.zip"
        ruta = os.path.join(destino, nombre)
        try:
            r = requests.get(url, timeout=120)
            r.raise_for_status()
            with open(ruta, "wb") as f:
                f.write(r.content)
        except Exception as e:
            messagebox.showerror("Error al descargar",
                                 "No se pudo descargar la actualización:\n" + str(e))
            return
        messagebox.showinfo(
            "Descarga completa",
            f"Se descargó {nombre}\nen:\n{destino}\n\n"
            "Descomprímelo y reemplaza la carpeta del programa para "
            "actualizar. La URL de internet (Cloudflare) se regenera sola.",
        )

    # Bandeja
    def minimizar_a_bandeja(self):
        if not HAS_PYSTRAY:
            messagebox.showinfo("Bandeja", "pystray no está disponible.")
            return
        self.root.withdraw()
        if self.tray is None:
            self._crear_tray()

    def _crear_tray(self):
        if not HAS_PYSTRAY:
            return
        import pystray
        img = Image.new("RGB", (64, 64), "#c9a227")
        menu = pystray.Menu(
            pystray.MenuItem("Abrir Albion Helper", self._abrir_desde_tray),
            pystray.MenuItem("Iniciar/Detener web", self._tray_toggle_web),
            pystray.MenuItem("Salir", self._tray_salir),
        )
        self.tray = pystray.Icon("albion_helper", img, "Albion Helper", menu)
        threading.Thread(target=self.tray.run, daemon=True).start()

    def _abrir_desde_tray(self, icon=None, item=None):
        self.root.after(0, self.root.deiconify)

    def _tray_toggle_web(self, icon=None, item=None):
        self.root.after(0, self.toggle_web)

    def _tray_salir(self, icon=None, item=None):
        self.root.after(0, self.salir)

    # Helpers
    def _cargar_cfg(self):
        try:
            return json.load(open(CONFIG_LAUNCHER, encoding="utf-8"))
        except Exception:
            return {}

    def salir(self):
        self.svc.detener_todo()
        if self.tray:
            try:
                self.tray.stop()
            except Exception:
                pass
        self.root.destroy()


def _pil_a_tk(img):
    import io
    from tkinter import PhotoImage
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return PhotoImage(data=buf.read())


def main():
    # Modos del exe portable (cuando PyInstaller empaqueta lanzador.py):
    #   lanzador.exe            -> GUI
    #   lanzador.exe --server   -> levanta Flask (lo lanza el propio lanzador)
    #   lanzador.exe --consola  -> consola original
    if "--server" in sys.argv:
        import flask_app
        print(f"Albion Helper web (Flask) en http://{flask_app.ip_lan()}:{flask_app.PORT}/")
        flask_app.app.run(host=flask_app.HOST, port=flask_app.PORT,
                          threaded=True, debug=False)
        return
    root = tk.Tk()
    app = LanzadorApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()