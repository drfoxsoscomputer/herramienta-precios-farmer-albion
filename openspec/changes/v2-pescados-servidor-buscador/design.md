# Design: v2-pescados-servidor-buscador

## Resumen
Diseño técnico del cambio v2 del helper Albion: T8 en recursos, resumen informativo de mercado (market_summary), buscador global, selección de servidor y migración de tests. Documento anclado al código real (constants.py, api.py, formatting.py, menus.py, textos.py, albion_config.json).

## Decisiones de diseño clave

### 1. Parametrización del servidor (Fase E)
- **Decisión**: función `get_server_base()` en api.py + parámetro de servidor en las llamadas, en lugar de variables globales mutables.
- **Justificación**: evita estado global mutable (más fácil de testear, sin efectos colaterales entre llamadas). La URL completa ya incluye el subdominio (west/east/asia), así que el cache de URLs se separa automáticamente por servidor.
- **Detalle**:
  - constants.py: mantener `API_BASE_TEMPLATE` y `HISTORY_BASE_TEMPLATE` con `{servidor}` en el subdominio: `https://{servidor}.albion-online-data.com/api/v2/stats/prices/{items}.json?locations=...`
  - api.py: `get_server_base(servidor)` devuelve el template formateado; `get_prices(item_ids, servidor="west")` y `get_history(item_ids, servidor="west")` reciben el servidor y construyen la URL.
  - Mapeo UI: `SERVIDORES = {"America": "west", "Europa": "east", "Asia": "asia"}` en constants.py.
  - Persistencia: `albion_config.json` gana campo `selected_server` (default `"west"`). Se guarda al cambiar.
  - UI: nueva opción "Servidor" en menu_principal → submenú con las 3 opciones → al confirmar, actualiza selected_server y reinicia el frame actual (los datos se refrescan al navegar).

### 2. Cache ante cambio de servidor (Fase E)
- **Decisión**: NO se necesita invalidación explícita.
- **Justificación**: el cache actual en api.py es `dict[url] -> (timestamp, data)` y la URL incluye el subdominio del servidor. Al cambiar de servidor, las URLs son distintas → no hay colisión. Datos viejos de west expiran por TTL 60s naturalmente.
- **Verificación**: confirmado leyendo `_cache_get`/`_cache_put` en api.py (líneas 26-34) — la clave es la URL completa.

### 3. market_summary (Fase B) — resumen informativo
- **Decisión**: función pura en formatting.py que devuelve DATOS ESTRUCTURADOS (dict), no texto formateado. La UI (menus.py) formatea.
- **Firma**: `market_summary(precios, historial, item)` → dict con:
  - `min_venta`, `max_venta` (de sell_price_min/max del mejor item por ciudad)
  - `volumen_total` (suma de item_count del historial)
  - `dia_mayor_venta` (str nombre de día) + `volumen_dia`
  - `es_ingrediente` (bool) + `recetas` (lista de nombres de salsa)
  - `diferencia_refinado` (solo recursos: precio refinado - crudo como dato)
  - `sin_datos` (bool) si todo es 0 → la UI muestra "sin datos de venta"
- **Agrupación por día**: los timestamps del historial (`2026-07-25T16:00:00`) → `datetime.fromisoformat` → `strftime("%A")` → sumar item_count por día de la semana. Mostrar SOLO días con datos reales.
- **Ingrediente**: cruzar el item_id del pescado contra `insumos_pesca.items[*].receta` del config (recetas anidadas). El config ya tiene esta estructura.
- **Integración**: en ver_detalle (pescados), _ver_detalle_recurso (recursos crudo/refinado) y detalle de insumos. El resumen se imprime debajo del panel existente, sin romper el layout.
- **Justificación filosofía**: NO recomendar acciones (no "vendé entero/picado"); solo datos objetivos. El usuario decide.

### 4. Normalización de acentos (Fase C)
- **Decisión**: `unicodedata.normalize("NFD", texto)` + quitar marcas diacríticas (`''.join(c for c in nfd if unicodedata.category(c) != 'Mn')`) + lowercase. Función `normalizar(texto)` en formatting.py.
- **Justificación**: cero dependencias nuevas (módulo estándar), funciona para tildes y ñ.
- **Uso**: tanto el término buscado como los nombres del catálogo se normalizan antes de comparar.

### 5. Buscador global (Fase C)
- **Decisión**: plan B por defecto (endpoint de búsqueda NO verificado — probes dieron 404/429): búsqueda sobre catálogo local + tabla manual de mapeo nombre-esp → technical_id en textos.py.
- **Flujo**:
  1. Opción "Buscar" en menu_principal.
  2. Entrada de texto: reutilizar `_leer_tecla()` char a char con buffer (consistente con el selector existente; sin Prompt.ask que mezcla estilos). Enter confirma, Esc cancela.
  3. `normalizar(consulta)` y comparar contra catálogo normalizado (pescados + recursos + insumos + tabla de mapeo en textos.py con items populares como journals).
  4. Resultados → `_menu_seleccion()` existente → Enter abre el detalle con market_summary.
- **Fallback**: si el endpoint de búsqueda se valida en el futuro, se agrega como fuente primaria manteniendo el catálogo local como respaldo ante 429/404.
- **Pregunta abierta**: validar endpoint real (probablemente `https://www.albion-online-data.com/api/v2/stats/search?item=...` o el CDN de items) — resuelto en implementación; el diseño NO depende de ello.

### 6. T8 en recursos (Fase A)
- **Decisión**: extender el esquema `tiers` de cada recurso en albion_config.json con clave `T8` siguiendo el esquema real existente: `{crudo, refinado, nombre, refinado_nombre}` (NO el "izquierda/derecha" que mencionó la spec — el esquema real es crudo/refinado).
- **Items**: T8_FIBER/T8_CLOTH, T8_WOOD/T8_PLANKS, T8_HIDE/T8_LEATHER, T8_ORE/T8_METALBAR, T8_ROCK/T8_STONEBLOCK.
- **Nombres**: verificar nombres reales en español del juego durante implementación (ej. T8 fibra = "algodón celestial", etc.) — mismo patrón que T2-T7.
- `COLORES_TIER` ya tiene "8": "yellow" → cero cambios de color necesarios.

### 7. Migración de tests (BASE)
- **Decisión**: crear `tests/` en la raíz, mover `regression_fase2.py` y `test_api_cache.py` desde Temp, ajustar imports (agregar `sys.path` hacia la raíz del proyecto o imports relativos), verificar con `python -X utf8 tests/regression_fase2.py` y `python -X utf8 tests/test_api_cache.py` desde la raíz.
- `tests/__init__.py` vacío si hace falta para imports de paquete.
- NO pytest (decisión del usuario: sin nuevas dependencias).

## Estructura de archivos afectados

| Archivo | Cambio |
|---------|--------|
| `constants.py` | Templates con `{servidor}`, `SERVIDORES`, `normalizar` (o en formatting), `selected_server` default |
| `api.py` | `get_server_base()`, parámetro `servidor` en get_prices/get_history |
| `formatting.py` | `normalizar()`, `market_summary()` |
| `textos.py` | Tabla mapeo nombre-esp → technical_id, textos del buscador y servidor |
| `albion_config.json` | T8 en 5 recursos + `selected_server` |
| `menus.py` | Opción Buscar, entrada de texto, opción Servidor, integración market_summary en detalles |
| `tests/` | Migración de baterías |

## Flujos

### Cambio de servidor
menu_principal → "Servidor" → selector (America/Europa/Asia) → guardar selected_server → frame se refresca → siguientes get_prices/get_history usan el subdominio nuevo.

### Búsqueda
menu_principal → "Buscar" → escribir texto (buffer char a char) → normalizar → filtrar catálogo → _menu_seleccion con resultados → Enter → detalle con market_summary.

### Resumen en detalle
ver_detalle(item) → get_prices + get_history (servidor activo) → market_summary() → imprimir sección "Resumen de mercado" con min/max, volumen, día de mayor venta, ingrediente (si aplica), sin recomendaciones.

## Riesgos técnicos
1. **Endpoint de búsqueda incierto** → plan B catálogo local cubre el requisito; endpoint es mejora futura.
2. **Nombres T8 en español** → verificar contra convención del juego durante implementación; el config es fácil de ajustar.
3. **Rate limit 429** → el cache 60s + backoff existente en api.py ya lo mitiga; el buscador local no hace llamadas extra.
4. **Items sin ventas** (tiburón) → `sin_datos=True` → "sin datos de venta" en UI.
5. **Historial < 7 días** → mostrar solo días con datos reales.

## Preguntas abiertas
- Endpoint de búsqueda exacto de albion-online-data (resuelto por plan B; mejora futura si se valida).
- Nombres reales en español de los 10 items T8 (se verifican en implementación contra la convención del juego).
