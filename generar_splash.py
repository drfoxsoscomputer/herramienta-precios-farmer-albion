# generar_splash.py — Genera splash.png estilo banner Albion (obra original).
# ─────────────────────────────────────────────────────────────────
# Splash de arranque "glass": fondo con bokeh cálido desenfocado,
# placa metálica con glow, título en Cinzel con gradiente de oro y
# bloom. Todo dibujado con PIL usando la paleta de tema.py; no se
# copia ningún asset del juego.
#
# Uso:  python -X utf8 generar_splash.py

import random
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont

import tema

BASE = Path(__file__).parent
FUENTE_VF = BASE / "static" / "fonts" / "Cinzel-VF.ttf"
FUENTE_FALLBACK = "C:/Windows/Fonts/georgia.ttf"
SALIDA = BASE / "splash.png"

# ── Paleta canónica (tema.py) ──
ORO_BRILLO = tema.rgb(tema.ORO_BRILLO)
ORO = tema.rgb(tema.ORO_CLARO)
FILO = tema.rgb(tema.ORO)
BORDE = tema.rgb(tema.BRONCE)
PANEL = tema.rgb(tema.PANEL)

# ── Derivados artísticos del splash (mezclas propias sobre el tema) ──
FONDO_ARRIBA = PANEL                       # arranca del panel
FONDO_ABAJO = (18, 13, 10)                 # cae a un marrón casi negro
BRILLO = (96, 66, 30)                      # resplandor cálido central
PLACA_ARRIBA = (74, 56, 38)                # metal: brillo arriba
PLACA_MEDIO = (46, 33, 21)
PLACA_ABAJO = (31, 21, 13)                 # ...sombra abajo
TEXTO_SUAVE = (154, 138, 112)
SOMBRA = (8, 5, 3)
BOKEH_COLORES = [tema.rgb(tema.AMBAR), (185, 128, 58),
                 BORDE, (122, 92, 49)]

ESCALA = 2                    # dibuja al doble y reduce (nitidez)
ANCHO, ALTO = 640 * ESCALA, 400 * ESCALA
TITULO = "ALBION HELPER"
RNG = random.Random(7)        # semilla fija: mismo splash en cada build


def _lerp(c1, c2, t):
    return tuple(round(a + (b - a) * t) for a, b in zip(c1, c2))


def _gradiente_vertical(ancho, alto, paradas):
    """Imagen RGB con gradiente vertical; paradas = [(pos 0..1, color), ...]."""
    col = Image.new("RGB", (1, alto))
    fila = []
    for y in range(alto):
        t = y / max(alto - 1, 1)
        color = paradas[-1][1]
        for i in range(len(paradas) - 1):
            p0, c0 = paradas[i]
            p1, c1 = paradas[i + 1]
            if p0 <= t <= p1:
                color = _lerp(c0, c1, (t - p0) / max(p1 - p0, 1e-6))
                break
        fila.append(color)
    col.putdata(fila)
    return col.resize((ancho, alto))


def _fuente(tamano, peso=700):
    """Cinzel variable (peso ajustable); fallback Georgia si no está."""
    try:
        f = ImageFont.truetype(str(FUENTE_VF), tamano)
        f.set_variation_by_axes([peso])
        return f
    except Exception:
        return ImageFont.truetype(FUENTE_FALLBACK, tamano)


def _poligono_banner(x0, y0, x1, y1, cha):
    """Rectángulo con esquinas biseladas (placa metálica)."""
    return [(x0 + cha, y0), (x1 - cha, y0), (x1, y0 + cha),
            (x1, y1 - cha), (x1 - cha, y1), (x0 + cha, y1),
            (x0, y1 - cha), (x0, y0 + cha)]


def _pegar(canvas, color, mascara):
    """Pega `color` sólido sobre canvas con `mascara` L como alfa."""
    canvas.paste(color, (0, 0), mascara)


def _bokeh(canvas, cantidad=9):
    """Manchas cálidas desenfocadas: la 'escena' difusa detrás del vidrio."""
    for _ in range(cantidad):
        cx = RNG.uniform(0.02, 0.98) * ANCHO
        cy = RNG.uniform(-0.12, 0.72) * ALTO   # luz que viene de arriba
        r = RNG.uniform(90, 240) * ESCALA // 2 * 2
        color = RNG.choice(BOKEH_COLORES)
        intensidad = int(RNG.uniform(55, 110))
        mask = Image.new("L", (ANCHO, ALTO), 0)
        ImageDraw.Draw(mask).ellipse([cx - r, cy - r, cx + r, cy + r],
                                     fill=intensidad)
        mask = mask.filter(ImageFilter.GaussianBlur(r * 0.55))
        _pegar(canvas, color, mask)


def _texto_oro(canvas, texto, fuente, centro, dy_sombra=10):
    """Texto con bloom dorado + sombra cálida + gradiente nítido."""
    mascara = Image.new("L", canvas.size, 0)
    ImageDraw.Draw(mascara).text(centro, texto, font=fuente,
                                 fill=255, anchor="mm")
    caja = mascara.getbbox()
    if caja is None:
        return
    x0, y0, x1, y1 = caja

    # sombra oscura desplazada (profundidad)
    sombra = ImageChops.offset(mascara, 0, dy_sombra)
    sombra = sombra.filter(ImageFilter.GaussianBlur(6))
    _pegar(canvas, SOMBRA, sombra)

    # bloom: halo dorado suave detrás del trazo (glow glass)
    bloom = mascara.filter(ImageFilter.GaussianBlur(14))
    bloom = bloom.point(lambda v: int(v * 0.45))
    _pegar(canvas, ORO_BRILLO, bloom)

    # trazo nítido con gradiente metálico
    grad = _gradiente_vertical(
        x1 - x0, y1 - y0,
        [(0.0, ORO_BRILLO), (0.45, ORO), (1.0, (185, 138, 62))])
    canvas.paste(grad, (x0, y0), mascara.crop(caja))


def _ornamento(draw, cx, cy, mitad=170):
    """Línea — rombo — línea bajo el título."""
    draw.line([cx - mitad, cy, cx - 26, cy], fill=FILO, width=3 * ESCALA // 2)
    draw.line([cx + 26, cy, cx + mitad, cy], fill=FILO, width=3 * ESCALA // 2)
    r = 9 * ESCALA // 2
    draw.polygon([(cx, cy - r), (cx + r, cy), (cx, cy + r), (cx - r, cy)],
                 fill=ORO)


def _remache(draw, x, y, r=10):
    """Rombo dorado pequeño (esquinas del banner)."""
    r *= ESCALA // 2
    draw.polygon([(x, y - r), (x + r, y), (x, y + r), (x - r, y)], fill=ORO)


def _texto_espaciado(draw, ancho_total, texto, fuente, centro_y, espacio,
                     color):
    """Texto en mayúsculas con tracking manual, centrado."""
    anchos = [draw.textlength(c, font=fuente) for c in texto]
    total = sum(anchos) + espacio * (len(texto) - 1)
    x = (ancho_total - total) / 2
    for c, a in zip(texto, anchos):
        draw.text((x, centro_y), c, font=fuente, fill=color, anchor="lm")
        x += a + espacio


def main():
    # 1) Fondo con gradiente vertical + bokeh cálido desenfocado.
    canvas = _gradiente_vertical(ANCHO, ALTO,
                                 [(0.0, FONDO_ARRIBA), (1.0, FONDO_ABAJO)])
    _bokeh(canvas)

    # 2) Viñeta: bordes más oscuros.
    vineta = Image.new("L", (ANCHO, ALTO), 95)
    ImageDraw.Draw(vineta).ellipse(
        [-ANCHO * 0.25, -ALTO * 0.35, ANCHO * 1.25, ALTO * 1.35], fill=0)
    vineta = vineta.filter(ImageFilter.GaussianBlur(150))
    canvas.paste((0, 0, 0), (0, 0), vineta)

    # 3) Geometría de la placa.
    bx0, by0, bx1, by1 = 140, 300, ANCHO - 140, 500
    cha = 34
    poly = _poligono_banner(bx0, by0, bx1, by1, cha)
    placa_mask = Image.new("L", (ANCHO, ALTO), 0)
    ImageDraw.Draw(placa_mask).polygon(poly, fill=255)

    # 4) Glow alrededor de la placa: halo ancho tenue + núcleo cercano.
    for radio, alfa in ((80, 70), (26, 120)):
        glow = placa_mask.filter(ImageFilter.GaussianBlur(radio))
        glow = glow.point(lambda v, a=alfa: int(v * a / 255))
        _pegar(canvas, ORO, glow)

    # 5) Relleno metálico + bordes.
    caja_placa = (bx0, by0, bx1, by1)
    grad_placa = _gradiente_vertical(
        bx1 - bx0, by1 - by0,
        [(0.0, PLACA_ARRIBA), (0.5, PLACA_MEDIO), (1.0, PLACA_ABAJO)])
    canvas.paste(grad_placa, (bx0, by0), placa_mask.crop(caja_placa))

    draw = ImageDraw.Draw(canvas)
    draw.polygon(poly, outline=BORDE, width=4 * ESCALA // 2)
    draw.line([bx0 + cha, by0 + 3, bx1 - cha, by0 + 3], fill=FILO,
              width=ESCALA)

    # 6) Franja especular diagonal (reflejo de luz sobre el vidrio/metal).
    brillo_mask = Image.new("L", (ANCHO, ALTO), 0)
    ImageDraw.Draw(brillo_mask).polygon(
        [(bx0 + 60, by0), (bx0 + 260, by0),
         (bx0 + 150, by1), (bx0 - 50, by1)], fill=48)
    brillo_mask = brillo_mask.filter(ImageFilter.GaussianBlur(18))
    especular = ImageChops.multiply(brillo_mask, placa_mask)
    _pegar(canvas, (255, 244, 214), especular)

    # 7) Remaches en las cuatro esquinas.
    _remache(draw, bx0 + cha // 2, by0 + cha // 2)
    _remache(draw, bx1 - cha // 2, by0 + cha // 2)
    _remache(draw, bx0 + cha // 2, by1 - cha // 2)
    _remache(draw, bx1 - cha // 2, by1 - cha // 2)

    # 8) Título en Cinzel con auto-ajuste al ancho de la placa.
    tam = 100
    fuente_titulo = _fuente(tam, peso=700)
    while (draw.textlength(TITULO, font=fuente_titulo) > (bx1 - bx0) - 120
           and tam > 40):
        tam -= 4
        fuente_titulo = _fuente(tam, peso=700)
    _texto_oro(canvas, TITULO, fuente_titulo, (ANCHO // 2, 382))

    # 9) Ornamento y subtítulo.
    _ornamento(draw, ANCHO // 2, 452)
    _texto_espaciado(draw, ANCHO, "CARGANDO", _fuente(30, peso=400),
                     600, 14 * ESCALA // 2, TEXTO_SUAVE)

    # 10) Versión (si existe version.txt) abajo a la derecha.
    try:
        version = (BASE / "version.txt").read_text(encoding="utf-8").strip()
    except Exception:
        version = ""
    if version:
        draw.text((ANCHO - 40, ALTO - 36), f"v{version}",
                  font=_fuente(24, peso=400), fill=TEXTO_SUAVE, anchor="rm")

    # 11) Reducción final y guardado.
    canvas = canvas.resize((ANCHO // ESCALA, ALTO // ESCALA),
                           Image.Resampling.LANCZOS)
    canvas.save(SALIDA)
    print(f"splash generado: {SALIDA} ({canvas.size[0]}x{canvas.size[1]})")


if __name__ == "__main__":
    main()
