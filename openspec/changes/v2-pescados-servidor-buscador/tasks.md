# Tasks: v2-pescados-servidor-buscador

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | ~1.000–1.100 (BASE ~370 migradas, A ~35, B ~310, C ~210, E ~165) |
| 400-line budget risk | High |
| Chained PRs recommended | Yes |
| Suggested split | PR 1 (BASE) → PR 2 (A+B) → PR 3 (C) → PR 4 (E) |
| Delivery strategy | force-chained |
| Chain strategy | pending |

Decision needed before apply: Yes
Chained PRs recommended: Yes
Chain strategy: pending
400-line budget risk: High

### Suggested Work Units

| Unit | Goal | Likely PR | Notes |
|------|------|-----------|-------|
| 1 | BASE: tests migrados a `tests/` | PR 1 | standalone; incluye ajuste de `test_command` en `openspec/config.yaml` |
| 2 | A: T8 en recursos + B: market_summary | PR 2 | base = PR 1; A y B independientes entre sí, agrupados por tamaño |
| 3 | C: buscador global | PR 3 | base = PR 2; depende de `normalizar()` y del detalle con market_summary |
| 4 | E: selección de servidor | PR 4 | base = PR 3; reutiliza `servidor` en api (parámetro ya añadido en B) |

Nota de alcance: FASE D (historial extendido + favoritos) queda FUERA de este cambio (fase futura separada). Sin SQLite, sin IA, sin pytest, sin nuevas dependencias. Buscador = plan B (catálogo local + tabla de mapeo; el endpoint de búsqueda NO se valida). Cache sin invalidación al cambiar servidor (la URL incluye el subdominio).

## Phase BASE: Migración de tests

- [x] 1.1 Crear carpeta `tests/` en la raíz con `tests/__init__.py` vacío (namespace de paquete).
  - Archivos: `tests/__init__.py` · Criterio: existe `tests/` y el paquete importa · Dep: ninguna
- [x] 1.2 Migrar `regression_fase2.py` de Temp a `tests/` y reemplazar `sys.path.insert(0, r"C:\Users\DrFox\albion")` por path relativo a la raíz (o import relativo).
  - Archivos: `tests/regression_fase2.py` · Criterio: `python -X utf8 tests/regression_fase2.py` desde la raíz pasa las 12 secciones · Dep: 1.1
- [x] 1.3 Migrar `test_api_cache.py` de Temp a `tests/` con el mismo ajuste de imports.
  - Archivos: `tests/test_api_cache.py` · Criterio: `python -X utf8 tests/test_api_cache.py` pasa los 4 tests · Dep: 1.1
- [x] 1.4 Actualizar `test_command` en `openspec/config.yaml` de Temp a `tests/` (para que apply/verify corran desde el repo).
  - Archivos: `openspec/config.yaml` · Criterio: el comando apunta a `tests/`, ambos tests pasan en una ejecución encadenada · Dep: 1.2, 1.3
- [x] 1.5 Verificar que las baterías originales en Temp quedan sin cambios (rollback seguro) y documentar el comando de ejecución en `ESTADO.md`.
  - Archivos: `ESTADO.md` · Criterio: se puede restaurar Temp si algo falla · Dep: 1.4

## Phase A: Recursos T8 en albion_config.json

- [x] 2.1 Agregar los 10 items T8 (5 pares crudo+refinado) a `recursos.*.tiers` de `albion_config.json` siguiendo el esquema REAL `{crudo, refinado, nombre, refinado_nombre}` (NO la terminología izquierda/derecha de la spec): T8_FIBER/T8_CLOTH, T8_WOOD/T8_PLANKS, T8_HIDE/T8_LEATHER, T8_ORE/T8_METALBAR, T8_ROCK/T8_STONEBLOCK; nombres reales en español verificados contra la convención T2-T7 existente.
  - Archivos: `albion_config.json` · Criterio: JSON válido (`json.load` sin error); cada tier T8 tiene las 4 claves; `ver_recurso` muestra T8 crudo y refinado separados (T4+ ya se separa por código) · Dep: ninguna
- [x] 2.2 Crear `tests/test_recursos_t8.py` que valide la estructura de los 10 items T8 (claves requeridas, ids con prefijo T8_, simetría crudo/refinado) contra el esquema de los items T4/T6 existentes.
  - Archivos: `tests/test_recursos_t8.py`, `albion_config.json` · Criterio: pasa con `python -X utf8 tests/test_recursos_t8.py` desde la raíz · Dep: 2.1, 1.1

## Phase B: market_summary (resumen informativo)

- [x] 3.1 En `api.py`, agregar `get_history_raw(item_id, servidor="west")` que devuelva los entries crudos (timestamp + item_count por ciudad) sin agregar; NO modificar `get_history` (el código actual descarta los timestamps).
  - Archivos: `api.py` · Criterio: devuelve lista de dicts con `data[].timestamp` e `item_count`; `get_history` existente intacto (test_api_cache pasa) · Dep: 1.3
- [x] 3.2 En `formatting.py`, agregar `market_summary(precios, historial, item, recetas_config=None)` → dict estructurado: `min_venta/max_venta`, `volumen_total`, `dia_mayor_venta` + `volumen_dia` (agrupar por `strftime("%A")`, solo días con datos), `es_ingrediente` + `recetas` (item_id como clave en `insumos_pesca.items[*].receta`), `diferencia_refinado` (solo recursos), `sin_datos`.
  - Archivos: `formatting.py` · Criterio: función pura sin red/impresión; tiburón (todo 0) → `sin_datos=True`; historial de 3 días → solo esos días · Dep: 3.1
- [x] 3.3 En `menus.py`, reemplazar el bloque de recomendación picar/entero de `ver_detalle_pez` (líneas 627-692) por la sección "Resumen de mercado" usando `market_summary` (sin recomendaciones de acción).
  - Archivos: `menus.py` · Criterio: pez con datos muestra min/max/volumen/día/ingrediente; tiburón muestra "sin datos de venta" sin romper · Dep: 3.2
- [x] 3.4 En `menus.py`, integrar el resumen en `_ver_detalle_recurso` (modo crudo/refinado, con `diferencia_refinado` como dato) y en `ver_detalle_insumo`.
  - Archivos: `menus.py` · Criterio: el detalle de recurso e insumo muestran el resumen debajo del panel existente · Dep: 3.2
- [x] 3.5 En `textos.py`, actualizar `RESENAS_MENU["pesca"]` y `RESENAS_DETALLE["pez"]`: ya no "entero vs picado", sí resumen informativo (datos objetivos, sin recomendación).
  - Archivos: `textos.py` · Criterio: copy en español neutro sin verbos de recomendación · Dep: 3.3
- [x] 3.6 Crear `tests/test_market_summary.py` con los escenarios de la spec: pez con datos (min/max visibles), tiburón sin ventas ("sin datos de venta"), día de mayor venta con 7d y con 3d (solo días reales), ingrediente sí/no, formato sin peticiones extra a la API.
  - Archivos: `tests/test_market_summary.py` · Criterio: pasa con `python -X utf8 tests/test_market_summary.py` · Dep: 3.2

## Phase C: Buscador global

- [ ] 4.1 En `formatting.py`, agregar `normalizar(texto)` con `unicodedata.normalize("NFD", ...)` + filtro de marcas `Mn` + lowercase (ignora tildes y ñ).
  - Archivos: `formatting.py` · Criterio: `normalizar("tiburón") == normalizar("tiburon")` · Dep: ninguna
- [ ] 4.2 En `textos.py`, agregar `MAPA_BUSQUEDA` (nombre español → technical_id) para items populares no cubiertos por el catálogo (ej. "tiburón" → `T8_FISH_SALTWATER_ALL_BOSS_SHARK`, journals).
  - Archivos: `textos.py` · Criterio: el mapeo cubre al menos los items populares de la spec · Dep: ninguna
- [ ] 4.3 En `menus.py`, crear `_catalogo_busqueda(config)` → lista de (nombre, item_id, tipo) normalizada: pescados + recursos (crudo y refinado por tier) + insumos + `MAPA_BUSQUEDA`.
  - Archivos: `menus.py` · Criterio: cubre los ~100 items del config; nombres normalizados una sola vez · Dep: 4.1, 4.2
- [ ] 4.4 En `menus.py`, crear `_entrada_texto()`: buffer char a char con `_leer_tecla()` (Enter confirma, Esc cancela), consistente con el selector (sin `Prompt.ask`).
  - Archivos: `menus.py` · Criterio: devuelve el texto ingresado o None al cancelar; no mezcla estilos Rich · Dep: ninguna
- [ ] 4.5 En `menus.py`, agregar la opción "Buscar" en `menu_principal`: flujo `_entrada_texto` → `normalizar` → filtrar `_catalogo_busqueda` → `_menu_seleccion` → Enter abre el detalle con market_summary; sin resultados → mensaje informativo.
  - Archivos: `menus.py` · Criterio: "pez" lista los peces con "pez" en el nombre; búsqueda con acentos funciona; Enter en un resultado muestra el detalle · Dep: 4.3, 4.4, 3.3
- [ ] 4.6 Crear `tests/test_busqueda.py`: búsqueda parcial, búsqueda sin acentos, "tiburón" → shark, sin resultados → lista vacía sin error.
  - Archivos: `tests/test_busqueda.py` · Criterio: pasa con `python -X utf8 tests/test_busqueda.py` · Dep: 4.5

## Phase E: Selección de servidor

- [ ] 5.1 En `constants.py`, convertir `API_BASE`/`HISTORY_BASE` en `API_BASE_TEMPLATE`/`HISTORY_BASE_TEMPLATE` con `{servidor}` en el subdominio, y agregar `SERVIDORES = {"America": "west", "Europa": "east", "Asia": "asia"}` + default `"west"`.
  - Archivos: `constants.py` · Criterio: `API_BASE_TEMPLATE.format(servidor="west")` produce la URL actual · Dep: ninguna
- [ ] 5.2 En `api.py`, agregar `get_server_base(servidor)` y el parámetro `servidor="west"` en `get_prices`, `get_history` y `get_history_raw`; la clave de cache sigue siendo la URL completa (sin invalidación: subdominio distinto = URL distinta).
  - Archivos: `api.py` · Criterio: west y east producen URLs distintas → sin colisión de cache (spec: "se limpia al cambiar servidor" cumplido por diseño); `test_api_cache.py` sigue pasando · Dep: 5.1
- [ ] 5.3 Persistir `selected_server` (default `"west"`) en `albion_config.json` y agregar guardado del config al cambiar servidor (función de escritura en `albion_helper.py` o equivalente).
  - Archivos: `albion_config.json`, `albion_helper.py` · Criterio: al cambiar a Asia, cerrar y reabrir muestra "Servidor: Asia (asia)" · Dep: 5.2
- [ ] 5.4 En `menus.py`, agregar submenú "Servidor" en `menu_principal` (America/Europa/Asia) y la línea de estado "Servidor: America (west)" en el footer; al confirmar, guarda y refresca (los datos se recargan al navegar).
  - Archivos: `menus.py` · Criterio: la UI muestra el servidor actual; cambiar a Europa actualiza precios desde east; opción inválida → "servidor no válido" · Dep: 5.2, 5.3
- [ ] 5.5 Crear `tests/test_servidor.py`: mapeo UI→técnico, URLs distintas por servidor, cache separado por servidor, persistencia de `selected_server`.
  - Archivos: `tests/test_servidor.py` · Criterio: pasa con `python -X utf8 tests/test_servidor.py` · Dep: 5.2, 5.3
