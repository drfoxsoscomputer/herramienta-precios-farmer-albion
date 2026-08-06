# Tests del buscador global (catalogo.py) — run from repo cwd
# Sin red: el indice se construye con un fixture LOCAL que replica la
# estructura de items.json de ao-bin-dumps; nunca se descarga catalog.json.
import io
import os
import sys
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import catalogo

# ── Fixture local: replica {UniqueName, LocalizedNames} de items.json ──
FIXTURE = [
    {"UniqueName": "T4_FISH_FRESHWATER_ALL_COMMON", "LocalizedNames": {"ES-ES": "Pez común de agua dulce"}},
    {"UniqueName": "T8_FISH_SALTWATER_ALL_BOSS_SHARK", "LocalizedNames": {"ES-ES": "Tiburón"}},
    {"UniqueName": "T4_2H_BOW", "LocalizedNames": {"ES-ES": "Arco de combate"}},
    {"UniqueName": "T4_2H_BOW@1", "LocalizedNames": {"ES-ES": "Arco de combate"}},
    {"UniqueName": "T4_2H_BOW@2", "LocalizedNames": {"ES-ES": "Arco de combate"}},
    {"UniqueName": "T4_2H_BOW@3", "LocalizedNames": {"ES-ES": "Arco de combate"}},
    {"UniqueName": "T4_2H_BOW@4", "LocalizedNames": {"ES-ES": "Arco de combate"}},
    {"UniqueName": "T4_JOURNAL_FISHERMAN", "LocalizedNames": {"ES-ES": "Diario de pescador"}},
    {"UniqueName": "T4_JOURNAL_FISHERMAN_EMPTY", "LocalizedNames": {"ES-ES": "Diario de pescador (vacío)"}},
    {"UniqueName": "T4_JOURNAL_FISHERMAN_FULL", "LocalizedNames": {"ES-ES": "Diario de pescador (parcialmente lleno)"}},
    {"UniqueName": "T4_JOURNAL_TROPHY_FISHING", "LocalizedNames": {"ES-ES": "Diario de trofeos del pescador novato (Parcialmente lleno)"}},
    {"UniqueName": "T5_BAG", "LocalizedNames": {"EN-US": "Bag"}},
]
catalogo._cat = catalogo._indexar(FIXTURE)

# ── 1. normalizar: minusculas + sin acentos (tildes y ñ) ─────
assert catalogo.normalizar("Tiburón Árbol") == "tiburon arbol", catalogo.normalizar("Tiburón Árbol")
assert catalogo.normalizar("ÑOÑO") == "nono", catalogo.normalizar("ÑOÑO")
assert catalogo.normalizar("  Pez  ") == "pez", "strip de espacios"
assert catalogo.normalizar(None) == "", "None -> ''"
print("PASS normalizar: minusculas + NFD sin marcas (tildes y ñ), None -> ''")

# ── 2. dedupe: @1..@4 agrupados al base, un solo resultado ──
res = catalogo.buscar("arco")
assert len(res) == 1, f"deberia agrupar las 5 variantes, got {len(res)}"
assert res[0]["id_base"] == "T4_2H_BOW" and res[0]["tipo"] == "arma", res[0]
print("PASS dedupe: T4_2H_BOW@1..@4 -> un solo resultado (base, tipo arma)")

# ── 3. deteccion de tipo: _JOURNAL -> diario, con @ -> arma, resto -> simple ──
por_id = {i["id_base"]: i["tipo"] for i in catalogo._cat}
assert por_id["T4_2H_BOW"] == "arma", por_id
assert por_id["T4_JOURNAL_FISHERMAN"] == "diario", por_id
assert por_id["T4_FISH_FRESHWATER_ALL_COMMON"] == "simple", por_id
print("PASS tipo: _JOURNAL -> diario, con @ -> arma, resto -> simple")

# ── 4. diarios agrupados: _EMPTY/_FULL NO aparecen, solo el journal base ──
res = catalogo.buscar("diario")
bases = [r["id_base"] for r in res]
assert bases == ["T4_JOURNAL_FISHERMAN", "T4_JOURNAL_TROPHY_FISHING"], f"los diarios se agrupan al base, got {bases}"
assert res[0]["tipo"] == "diario", res[0]
assert res[0]["nombre"] == "Diario de pescador", res[0]["nombre"]
# La variante _FULL con sufijo ' (parcialmente lleno)' no contamina el listado
assert all("parcialmente lleno" not in r["nombre"] for r in res), res
print("PASS diarios: _EMPTY/_FULL agrupados, una sola entrada (nombre sin '(parcialmente lleno)')")

# ── 4b. diarios con sufijo en mayuscula: el limpiado es case-insensitive ──
res = catalogo.buscar("trofeos")
assert len(res) == 1, f"deberia encontrar solo el diario de trofeos, got {len(res)}"
assert res[0]["id_base"] == "T4_JOURNAL_TROPHY_FISHING", res
assert res[0]["nombre"] == "Diario de trofeos del pescador novato", res[0]["nombre"]
assert all("parcialmente lleno" not in r["nombre"].lower() for r in res), res
print("PASS diarios: ' (Parcialmente lleno)' con P mayuscula tambien se limpia")

# ── 5. tokens AND contra nombre ES-ES y UniqueName normalizados ──
res = catalogo.buscar("tiburon")  # sin tilde encuentra "Tiburón"
assert [r["id_base"] for r in res] == ["T8_FISH_SALTWATER_ALL_BOSS_SHARK"], res
res = catalogo.buscar("pez común")  # 2 tokens en el nombre
assert any(r["id_base"] == "T4_FISH_FRESHWATER_ALL_COMMON" for r in res), res
res = catalogo.buscar("T4 2H")  # tokens contra UniqueName normalizado
assert any(r["id_base"] == "T4_2H_BOW" for r in res), res
res = catalogo.buscar("tiburon pez")  # AND: ningun item tiene ambos tokens
assert res == [], res
print("PASS AND tokens: parcial ES-ES sin acentos, UniqueName, consulta de 2 tokens")

# ── 6. limite de resultados: maximo 15 ────────────────────────
muchos = [{"UniqueName": f"T4_SWORD{i:02d}", "LocalizedNames": {"ES-ES": f"Espada {i}"}} for i in range(40)]
catalogo._cat = catalogo._indexar(FIXTURE + muchos)
res = catalogo.buscar("espada")
assert 0 < len(res) <= 15, f"max 15 resultados, got {len(res)}"
print("PASS limite: buscar devuelve maximo 15 resultados")

# ── 7. sin resultados ni descarga: consulta vacia y catalogo vacio ──
catalogo._cat = catalogo._indexar(FIXTURE)
assert catalogo.buscar("") == [], "consulta vacia -> []"
catalogo._cat = []
assert catalogo.buscar("arco") == [], "catalogo vacio -> [] sin error"
print("PASS sin datos: consulta vacia -> [] y catalogo vacio -> [] sin error")

# ── 8. sin red: con indice en memoria NO se descarga nada ─────
catalogo._cat = catalogo._indexar(FIXTURE)

def boom(*a, **k):
    raise AssertionError("buscar no debe tocar la red con indice en memoria")

original = urllib.request.urlopen
urllib.request.urlopen = boom
try:
    res = catalogo.buscar("tiburon")
finally:
    urllib.request.urlopen = original
assert len(res) == 1 and res[0]["id_base"] == "T8_FISH_SALTWATER_ALL_BOSS_SHARK", res
print("PASS sin red: fixtures locales, buscar nunca descarga catalog.json")

# ── 9. descarga fallida -> error amigable, no crash, None ─────
import tempfile
catalogo._ruta_catalogo = lambda: os.path.join(tempfile.gettempdir(), "catalog_test_inexistente.json")
buf = io.StringIO()
catalogo.console = type(catalogo.console)(file=buf, force_terminal=False)

def boom_red(*a, **k):
    raise OSError("sin conexion")

catalogo.urllib.request.urlopen = boom_red
ruta = catalogo._descargar_catalogo()
assert ruta is None, "descarga fallida -> None"
assert "No se pudo descargar" in buf.getvalue(), buf.getvalue()
print("PASS descarga fallida: None + aviso amigable, sin crash")

print("\nTODOS LOS TESTS DE CATALOGO PASARON")
