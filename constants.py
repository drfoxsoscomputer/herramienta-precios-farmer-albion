# constants.py
# ─── Datos fijos (constantes) ─────────────────────────────────
# Nada aqui cambia en tiempo de ejecucion. Separadas del codigo
# para que el script principal solo se preocupe por la logica.

# ─── Ciudades ─────────────────────────────────────────────────
CITIES = ["Thetford", "Lymhurst", "Fort Sterling", "Bridgewatch", "Martlock"]

# ─── URLs de la API ───────────────────────────────────────────
API_BASE = "https://west.albion-online-data.com/api/v2/stats/prices/{items}.json?locations=Thetford,Lymhurst,Fort%20Sterling,Bridgewatch,Martlock"
HISTORY_BASE = "https://west.albion-online-data.com/api/v2/stats/history/{item}.json?locations=Thetford,Lymhurst,Fort%20Sterling,Bridgewatch,Martlock"

# ─── Colores por Tier ─────────────────────────────────────────
COLORES_TIER = {
    "1": "grey58", "2": "white", "3": "green",
    "4": "cyan", "5": "magenta",
    "6": "dark_orange", "7": "red", "8": "yellow"
}

# ─── Traduccion de refinados ──────────────────────────────────
REF_MAP = {"Cloth": "Tela", "Planks": "Tablas", "Leather": "Cuero", "Metalbar": "Metal", "Stoneblock": "Piedra"}

# ─── Encantamientos ───────────────────────────────────────────
ENCH_NOMBRES = ["", "poco común", "raro", "excepcional", "primigenio"]
ENCH_COLORS = ["", "green", "blue", "magenta", "yellow"]
