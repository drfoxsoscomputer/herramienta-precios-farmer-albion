# generar_splash.py — Genera splash.png estilo banner Albion (obra original).
# ─────────────────────────────────────────────────────────────────
# Dibuja con PIL un splash de arranque inspirado en la estética del
# juego (oro/bronce sobre fondo oscuro) usando SOLO elementos propios:
# gradientes, polígonos simples y la fuente libre Cinzel (SIL OFL).
# No se copia ningún asset de Sandbox Interactive.
#
# Uso:  python -X utf8 generar_splash.py

from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont

BASE = Path(__file__).parent
FUENTE_VF = BASE / "static" / "fonts" / "Cinzel-VF.ttf"
FUENTE_FALLBACK = "C:/Windows/Fonts/georgia.ttf"
SALIDA = BASE / "splash.png"

# Paleta propia alineada al tema web del proyecto.
FONDO_ARRIBA = (36, 28, 22)    # #241c16
FONDO_ABAJO = (18, 13, 10)     # #120d0a
BRILLO = (96, 66, 30)          # resplandor cálido tras el banner
PLACA_ARRIBA = (74, 56, 38)    # #4a3826
PLACA_MEDIO = (46, 33, 21)     # #2e2115
PLACA_ABAJO = (31, 21, 13)     # #1f150d
BORDE = (138, 106, 58)         # #8a6a3a
FILO = (201, 162, 86)          # #c9a256
ORO_CLARO = (247, 224, 138)    # #f7e08a
ORO = (232, 184, 74)           # #e8b84a
ORO_OSCURO = (185, 138, 62)    # #b98a3e
TEXTO_SUAVE = (154, 138, 112)  # #9a8a70
SOMBRA = (8, 5, 3)

ESCALA = 2                    # dibuja al doble y reduce (nitidez)
ANCHO, ALTO = 640 * ESCALA, 400 * ESCALA
TITULO = "ALBION HELPER"


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


def _texto_oro(canvas, texto, fuente, centro, dy_sombra=10):
    """Texto con gradiente de oro + sombra cálida, centrado en `centro`."""
    mascara = Image.new("L", canvas.size, 0)
    ImageDraw.Draw(mascara).text(centro, texto, font=fuente,
                                 fill=255, anchor="mm")
    caja = mascara.getbbox()
    if caja is None:
        return
    x0, y0, x1, y1 = caja
    grad = _gradiente_vertical(
        x1 - x0, y1 - y0,
        [(0.0, ORO_CLARO), (0.45, ORO), (1.0, ORO_OSCURO)])
    sombra = ImageChops.offset(mascara, 0, dy_sombra)
    sombra = sombra.filter(ImageFilter.GaussianBlur(6))
    canvas.paste(SOMBRA, (0, 0), sombra)
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
    # 1) Fondo con gradiente vertical + resplandor cálido central.
    canvas = _gradiente_vertical(ANCHO, ALTO,
                                 [(0.0, FONDO_ARRIBA), (1.0, FONDO_ABAJO)])
    brillo = Image.new("L", (ANCHO, ALTO), 0)
    ImageDraw.Draw(brillo).ellipse(
        [ANCHO * 0.12, ALTO * 0.22, ANCHO * 0.88, ALTO * 0.78], fill=110)
    brillo = brillo.filter(ImageFilter.GaussianBlur(120))
    canvas.paste(BRILLO, (0, 0), brillo)

    # 2) Viñeta: bordes más oscuros.
    vineta = Image.new("L", (ANCHO, ALTO), 95)
    ImageDraw.Draw(vineta).ellipse(
        [-ANCHO * 0.25, -ALTO * 0.35, ANCHO * 1.25, ALTO * 1.35], fill=0)
    vineta = vineta.filter(ImageFilter.GaussianBlur(150))
    canvas.paste((0, 0, 0), (0, 0), vineta)

    # 3) Placa metálica (banner horizontal con esquinas biseladas).
    bx0, by0, bx1, by1 = 140, 300, ANCHO - 140, 500
    cha = 34
    poly = _poligono_banner(bx0, by0, bx1, by1, cha)
    placa_mask = Image.new("L", (ANCHO, ALTO), 0)
    ImageDraw.Draw(placa_mask).polygon(poly, fill=255)
    caja_placa = (bx0, by0, bx1, by1)
    grad_placa = _gradiente_vertical(
        bx1 - bx0, by1 - by0,
        [(0.0, PLACA_ARRIBA), (0.5, PLACA_MEDIO), (1.0, PLACA_ABAJO)])
    canvas.paste(grad_placa, (bx0, by0), placa_mask.crop(caja_placa))

    draw = ImageDraw.Draw(canvas)
    draw.polygon(poly, outline=BORDE, width=4 * ESCALA // 2)
    # filo superior iluminado (sensación metálica)
    draw.line([bx0 + cha, by0 + 3, bx1 - cha, by0 + 3], fill=FILO,
              width=ESCALA)
    # remaches en las cuatro esquinas
    _remache(draw, bx0 + cha // 2, by0 + cha // 2)
    _remache(draw, bx1 - cha // 2, by0 + cha // 2)
    _remache(draw, bx0 + cha // 2, by1 - cha // 2)
    _remache(draw, bx1 - cha // 2, by1 - cha // 2)

    # 4) Título en Cinzel con auto-ajuste al ancho de la placa.
    tam = 100
    fuente_titulo = _fuente(tam, peso=700)
    while (draw.textlength(TITULO, font=fuente_titulo) > (bx1 - bx0) - 120
           and tam > 40):
        tam -= 4
        fuente_titulo = _fuente(tam, peso=700)
    _texto_oro(canvas, TITULO, fuente_titulo, (ANCHO // 2, 382))

    # 5) Ornamento y subtítulo.
    _ornamento(draw, ANCHO // 2, 452)
    _texto_espaciado(draw, ANCHO, "CARGANDO", _fuente(30, peso=400),
                     600, 14 * ESCALA // 2, TEXTO_SUAVE)

    # 6) Versión (si existe version.txt) abajo a la derecha.
    try:
        version = (BASE / "version.txt").read_text(encoding="utf-8").strip()
    except Exception:
        version = ""
    if version:
        draw.text((ANCHO - 40, ALTO - 36), f"v{version}",
                  font=_fuente(24, peso=400), fill=TEXTO_SUAVE, anchor="rm")

    # 7) Reducción final y guardado.
    canvas = canvas.resize((ANCHO // ESCALA, ALTO // ESCALA),
                           Image.Resampling.LANCZOS)
    canvas.save(SALIDA)
    print(f"splash generado: {SALIDA} ({canvas.size[0]}x{canvas.size[1]})")


if __name__ == "__main__":
    main()
