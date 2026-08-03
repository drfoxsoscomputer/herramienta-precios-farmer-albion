# Tests del formateador de antiguedad (columna "Actualizado") — run from repo cwd
# antiguedad es FUNCION PURA: ISO 8601 -> "hace X s/min/h/d" en espanol.
import os
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from formatting import antiguedad

# "ahora" fijo para que los casos sean deterministicos (UTC).
AHORA = datetime(2026, 8, 2, 12, 20, 0, tzinfo=timezone.utc)


def hace(iso, ahora=AHORA):
    return antiguedad(iso, ahora=ahora)


# ── 1. unidades: segundos / minutos / horas / dias ────────────
assert hace("2026-08-02T12:19:50") == "hace 10 s", hace("2026-08-02T12:19:50")
assert hace("2026-08-02T12:20:00") == "hace 0 s", hace("2026-08-02T12:20:00")
assert hace("2026-08-02T12:19:00") == "hace 1 min", hace("2026-08-02T12:19:00")
assert hace("2026-08-02T12:15:00") == "hace 5 min", hace("2026-08-02T12:15:00")
assert hace("2026-08-02T11:20:00") == "hace 1 h", hace("2026-08-02T11:20:00")
assert hace("2026-08-02T09:20:00") == "hace 3 h", hace("2026-08-02T09:20:00")
assert hace("2026-08-01T12:20:00") == "hace 1 d", hace("2026-08-01T12:20:00")
assert hace("2026-07-31T12:20:00") == "hace 2 d", hace("2026-07-31T12:20:00")
print("PASS unidades: s/min/h/d con singulares 'hace 1 min/h/d'")

# ── 2. bordes de cambio de unidad ─────────────────────────────
assert hace("2026-08-02T12:19:01") == "hace 59 s", hace("2026-08-02T12:19:01")  # 59 s
assert hace("2026-08-02T12:19:00") == "hace 1 min", hace("2026-08-02T12:19:00")  # 60 s -> min
assert hace("2026-08-02T11:21:00") == "hace 59 min", hace("2026-08-02T11:21:00")  # 59 min
assert hace("2026-08-02T11:20:00") == "hace 1 h", hace("2026-08-02T11:20:00")  # 60 min -> h
assert hace("2026-08-01T13:20:00") == "hace 23 h", hace("2026-08-01T13:20:00")  # 23 h
assert hace("2026-08-01T12:20:00") == "hace 1 d", hace("2026-08-01T12:20:00")  # 24 h exactas -> d
print("PASS bordes: 59 s/min/h quedan en la unidad inferior; 24 h pasan a dias")

# ── 3. timestamp futuro por desfase de reloj -> "hace 0 s" ────
assert hace("2026-08-02T12:20:30") == "hace 0 s", hace("2026-08-02T12:20:30")
print("PASS desfase: timestamp futuro no da negativo (clamp a 0 s)")

# ── 4. entradas invalidas -> "" ───────────────────────────────
assert antiguedad(None) == "", f"None -> '', got {antiguedad(None)!r}"
assert antiguedad("") == "", f"'' -> '', got {antiguedad('')!r}"
assert antiguedad("no-es-una-fecha") == "", f"texto -> '', got {antiguedad('no-es-una-fecha')!r}"
assert antiguedad(12345) == "", f"numero -> '', got {antiguedad(12345)!r}"
# Centinela de la API en ciudades sin ventas (anio 1): no es dato real.
assert antiguedad("0001-01-01T00:00:00") == "", "centinela anio 1 -> ''"
print("PASS invalidos: None/vacio/texto/numero/centinela -> ''")

# ── 5. formatos con zona horaria y objetos datetime ───────────
assert hace("2026-08-02T12:19:50+00:00") == "hace 10 s", hace("2026-08-02T12:19:50+00:00")
assert hace("2026-08-02T12:19:50Z") == "hace 10 s", hace("2026-08-02T12:19:50Z")
assert hace(datetime(2026, 8, 2, 12, 19, 50, tzinfo=timezone.utc)) == "hace 10 s", "datetime aware"
# naive -> tratado como UTC: mismo resultado que el aware
assert hace("2026-08-02T12:19:50", ahora=datetime(2026, 8, 2, 12, 20, 0)) == "hace 10 s", "ahora naive"
print("PASS formatos: offset +00:00, sufijo Z y datetime directo; naive = UTC")

# ── 6. la columna usa la fecha MAS reciente (min vs max) ──────
# _fecha_fresca elige el max de los timestamps; el formateador recibe
# solo el ISO elegido. Caso directo: elegir el mas nuevo de dos ISO.
fresca = max("2026-08-02T12:00:00", "2026-08-02T12:20:00")  # comparacion lexica (mismo formato)
assert hace(fresca) == "hace 0 s", f"fresca = max(min_date, max_date) -> {hace(fresca)}"
print("PASS frescura: max lexico de los ISO (mismo formato) elige la mas reciente")

print("\nTODOS LOS TESTS DE ANTIGUEDAD PASARON")
