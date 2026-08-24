# generar_splash.py — Genera splash.png estilo logo Albion (obra original).
# ─────────────────────────────────────────────────────────────────
# ESTRICTO (pedido del usuario 2026-08-24): fondo NEGRO PLANO opaco
# y SOLO tres elementos — el título "Albion" en Pirata One blanca
# (tipografía libre, licencia SIL OFL que viaja en
# static/fonts/PirataOne-OFL.txt), la espada roja de geometría propia
# y "HELPER" en Cinzel espaciado. SIN gradiente, SIN iluminación,
# SIN sombras, SIN versión. No se copia ningún asset ni arte de
# Sandbox Interactive; el proyecto es un fan-tool no oficial.
#
# Uso:  python -X utf8 generar_splash.py

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

BASE = Path(__file__).parent
FUENTE_GOTICA = BASE / "static" / "fonts" / "PirataOne-Regular.ttf"
FUENTE_CAPS = BASE / "static" / "fonts" / "Cinzel-VF.ttf"
FUENTE_FALLBACK = "C:/Windows/Fonts/georgia.ttf"
SALIDA = BASE / "splash.png"

ROJO = (208, 44, 44)            # espada
ROJO_OSCURO = (143, 29, 29)     # fuller y filos de la espada
BLANCO = (244, 242, 238)        # título
BLANCO_SUAVE = (226, 223, 217)  # sufijo

ESCALA = 2                    # dibuja al doble y reduce (nitidez)
ANCHO, ALTO = 640 * ESCALA, 400 * ESCALA
TITULO = "Albion"
SUBTITULO = "HELPER"


def _pegar(canvas, color, mascara):
    """Pega color RGBA sobre canvas con `mascara` L como alfa."""
    canvas.paste(color, (0, 0), mascara)


def _fuente_gotica(tamano):
    try:
        return ImageFont.truetype(str(FUENTE_GOTICA), tamano)
    except Exception:
        return ImageFont.truetype(FUENTE_FALLBACK, tamano)


def _fuente_caps(tamano, peso=400):
    try:
        f = ImageFont.truetype(str(FUENTE_CAPS), tamano)
        f.set_variation_by_axes([peso])
        return f
    except Exception:
        return ImageFont.truetype(FUENTE_FALLBACK, tamano)


def _espada(canvas):
    """Espada roja vertical, geometría propia: pomo, empuñadura,
    guarda y hoja ahusada con fuller. Queda DETRÁS del título."""
    cx = ANCHO // 2
    capa = Image.new("RGBA", (ANCHO, ALTO), (0, 0, 0, 0))
    d = ImageDraw.Draw(capa)

    d.ellipse([cx - 24, 126, cx + 24, 174], fill=(*ROJO, 255))     # pomo
    d.rounded_rectangle([cx - 12, 168, cx + 12, 244], radius=10,
                        fill=(*ROJO, 255))                         # empuñadura
    d.rounded_rectangle([cx - 84, 244, cx + 84, 274], radius=12,
                        fill=(*ROJO, 255))                         # guarda
    d.polygon([(cx - 30, 274), (cx + 30, 274), (cx + 16, 620),
               (cx, 690), (cx - 16, 620)], fill=(*ROJO, 255))      # hoja
    d.line([cx, 290, cx, 600], fill=(*ROJO_OSCURO, 255), width=8)  # fuller
    d.line([(cx - 30, 274), (cx - 16, 620)],
           fill=(*ROJO_OSCURO, 255), width=4)                      # filo izq
    d.line([(cx + 30, 274), (cx + 16, 620)],
           fill=(*ROJO_OSCURO, 255), width=4)                      # filo der

    canvas.alpha_composite(capa)


def _texto_blanco(canvas, texto, fuente, centro):
    """Texto blanco nítido vía máscara, sin sombra ni efectos."""
    mascara = Image.new("L", canvas.size, 0)
    ImageDraw.Draw(mascara).text(centro, texto, font=fuente, fill=255,
                                 anchor="mm")
    if mascara.getbbox() is None:
        return
    _pegar(canvas, (*BLANCO, 255), mascara)


def _texto_espaciado(canvas, ancho_total, texto, fuente, centro_y, espacio,
                     color):
    """Mayúsculas con tracking manual, centrado; vía máscara (alfa)."""
    mascara = Image.new("L", (ANCHO, ALTO), 0)
    d = ImageDraw.Draw(mascara)
    anchos = [d.textlength(c, font=fuente) for c in texto]
    total = sum(anchos) + espacio * (len(texto) - 1)
    x = (ancho_total - total) / 2
    for c, a in zip(texto, anchos):
        d.text((x, centro_y), c, font=fuente, fill=255, anchor="lm")
        x += a + espacio
    _pegar(canvas, color, mascara)


def main():
    # 1) Fondo negro puro plano (0,0,0), opaco. Nada más.
    canvas = Image.new("RGBA", (ANCHO, ALTO), (0, 0, 0, 255))

    # 2) Espada roja (detrás del título).
    _espada(canvas)

    # 3) Título blackletter blanco, auto-ajustado al ancho.
    probe = ImageDraw.Draw(canvas)
    tam = 230
    fuente = _fuente_gotica(tam)
    while probe.textlength(TITULO, font=fuente) > ANCHO - 160 and tam > 90:
        tam -= 8
        fuente = _fuente_gotica(tam)
    _texto_blanco(canvas, TITULO, fuente, (ANCHO // 2, 420))

    # 4) Sufijo espaciado en Cinzel.
    _texto_espaciado(canvas, ANCHO, SUBTITULO, _fuente_caps(46, peso=600),
                     586, 44, (*BLANCO_SUAVE, 255))

    # 5) Reducción final y guardado.
    canvas = canvas.resize((ANCHO // ESCALA, ALTO // ESCALA),
                           Image.Resampling.LANCZOS)
    canvas.save(SALIDA)
    print(f"splash generado: {SALIDA} ({canvas.size[0]}x{canvas.size[1]}) "
          f"modo={canvas.mode}")


if __name__ == "__main__":
    main()
