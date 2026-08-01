# Proposal: v2-pescados-servidor-buscador

## Intent
Implementar el cambio v2 del helper: añadir los recursos T8 que faltan (fibra, madera, cuero, mineral, piedra), reemplazar la recomendación "picar/entero" por un resumen informativo con datos objetivos (precio min/max, volumen, día de mayor venta, uso como ingrediente), añadir un buscador global que encuentra cualquier item por palabra parcial ignorando acentos, parametrizar la selección de servidor (America/Europa/Asia), y migrar las baterías de tests al repo.

## Scope

### In Scope
- Agregar fibra T8, madera T8, cuero T8, mineral T8, piedra T8 a albion_config.json (10 items: crudo+refinado). Los pescados ya tienen T8.
- Reemplazar la recomendación "picar/entero" por un RESUMEN INFORMATIVO por item: precio min/max de venta, volumen de venta, día de mayor venta (agrupando historial 7d por día de la semana), y si es ingrediente de alguna receta del config (dato, NO orden). La herramienta no decide qué hacer con el material del usuario.
- Agregar buscador global desde el menu principal: búsqueda por palabra parcial, ignorar acentos, listar selección con selector existente
- Parametrizar servidor API (west/east/asia) con opción UI America/Europa/Asia
- Migrar baterías de tests: regression_fase2.py y test_api_cache.py de Temp a tests/ en repo (imports ajustados, correr desde repo)

### Out of Scope
- FASE D (historial de precios extendido + favoritos) en una fase separada; detalle solo en propuesta
- Base de datos SQLite / snapshots históricos: la API ya da 7d; BD es fase futura si se necesitan tendencias de más de 7 días (decisión tomada con el usuario, NO incluir ahora)
- Añadir nuevas funcionalidades de UI más allá del buscador y selector de servidor
- Instalar nuevas dependencias (pytest, otros paquetes)

## Capabilities

### New Capabilities
- `resource-t8`: Agregar los 10 items de recursos T8 crudo+refinado (T8_FIBER/T8_CLOTH, T8_WOOD/T8_PLANKS, T8_HIDE/T8_LEATHER, T8_ORE/T8_METALBAR, T8_ROCK/T8_STONEBLOCK)
- `market-summary`: Resumen informativo por item — precio min/max (sell_price_min/max de la API), volumen, día de mayor venta (agrupación historial 7d), uso como ingrediente (recetas del config). Sin recomendaciones de acción. LÓGICA GENÉRICA: aplica a pescados, recursos (crudo y refinado) e insumos/salsas. En recursos también muestra la diferencia refinado vs crudo como dato. Una sola función market_summary(precios, historial, item) reusada por todos los detalles.
- `global-search`: Buscador global que encuentra cualquier item por palabra parcial (ignorar acentos)
- `server-selection`: Opción UI para elegir servidor API America/Europa/Asia
- `test-migration`: Migrar pruebas desde Temp a tests/ (completar BASE)

### Modified Capabilities
- `prices-api`: Parametrizar servidor API (API_BASE/HISTORY_BASE configurable; hoy hardcodeado a west)
- `price-recommendation`: Reemplazada por `market-summary` (resumen informativo en vez de recomendación picar/entero)

## Approach
1. Migrar baterías de tests de Temp a tests/ y confirmar que corren desde el repo
2. Revisar albion_config.json y añadir 10 items T8 (nombres exactos de la API validados contra T8_FIBER/T8_CLOTH, T8_ROCK/T8_STONEBLOCK etc.)
3. Implementar `market-summary` en el detalle de items: usar sell_price_min/max + buy_price_min/max (ya disponibles en get_prices), volumen y agrupación por día (get_history ya trae item_count + timestamp cada ~2h), y cruce con recetas del config (insumos_pesca.items[*].receta)
4. Integrar buscador en menu_principal: endpoint de búsqueda de albion-online-data (VALIDAR ruta exacta en exploración — los probes dieron 404/429), mapear nombre español -> technical_id (ej. tiburon -> T8_FISH_SALTWATER_ALL_BOSS_SHARK), retornar lista seleccionable con selector existente
5. Parametrizar API_BASE/HISTORY_BASE desde variable de servidor: eliminar hardcode west en constants.py; exponer opción America/Europa/Asia mapeando a west/east/asia
6. Documentar decisiones del resumen con ejemplos y casos borde

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `constants.py` | Modified | Hacer API_BASE y HISTORY_BASE configurables; eliminar hardcode west |
| `api.py` | Modified | Agregar soporte de servidor (parámetro de conexión); exponer sell_price_min/max |
| `albion_config.json` | Modified | Agregar 10 items T8 (crudo+refinado) para fibra/madera/cuero/mineral/piedra |
| `menus.py` | Modified | Resumen informativo en detalles + buscador global + selector de servidor |
| `formatting.py` | Modified | Formateo del resumen (min/max, % volumen, día de mayor venta) |
| `textos.py` | Modified | Textos del resumen, buscador y selector de servidor |
| `tests/` | New | Migrar baterías de tests de Temp, adaptar imports, verificar que corren |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Endpoint de búsqueda no encontrado (probes dieron 404/429) | High | Explorar la ruta correcta de albion-online-data; fallback: buscar solo en catálogo del config + mapeo manual de items populares |
| Traducción nombre español -> technical_id | Medium | Validar mapeo con la API; probar con varios items; mantener tabla de traducción en textos.py si no hay endpoint |
| Rate limit 429 de API de búsqueda | Medium | Reusar cache 60s existente; backoff 2s/4s; limitar peticiones de búsqueda |
| Items sin ventas (ej. tiburón T8 = todo 0) | Medium | El resumen debe mostrar "sin datos de venta" con elegancia, no romper |
| Volumen por día con menos de 7d de datos | Low | Mostrar solo días con datos reales |
| Breaking migration de tests | High | Correr baterías actuales primero para confirmar base, migrar paso a paso |

## Rollback Plan
1. Revertir cambios en albion_config.json (eliminar los 10 items T8)
2. Revertir cambios en constants.py (restablecer API_BASE/HISTORY_BASE a west hardcoded)
3. Revertir menú principal (quitar buscador, resumen y opción de servidor)
4. Revertir api.py (quitar soporte de servidor)
5. Eliminar carpeta tests/ (si creada) y restaurar baterías originales en Temp
6. Correr scripts de regresión para confirmar estado previo

## Dependencies
- API albion-online-data.com: endpoints de precios e historial ya devuelven sell_price_min/max y timestamp por hora (VERIFICADO con probes: T4_FISH_FRESHWATER_ALL_COMMON tiene sell 1001/1022 y historial con item_count + timestamp cada ~2h)
- Endpoint de búsqueda para buscador global (PENDIENTE DE VALIDAR ruta exacta)
- NO requiere base de datos (SQLite) ni IA: agregaciones simples con los datos que la API ya entrega (decisión tomada con el usuario)

## Success Criteria
- [ ] Todas las baterías de tests corren desde tests/ (no desde Temp)
- [ ] albion_config.json incluye 10 items T8 (crudo+refinado) con estructura válida
- [ ] El detalle de un pescado muestra resumen informativo: precio min/max, volumen, día de mayor venta, ingrediente de receta (probar con pez T4 común que tiene datos)
- [ ] El detalle de un pescado sin ventas (ej. tiburón T8) muestra "sin datos de venta" sin romper
- [ ] Buscador global retorna resultados para palabra parcial sin acentos; seleccionable con selector existente
- [ ] UI muestra selector de servidor (America/Europa/Asia) y los precios cambian según selección
- [ ] Las APIs de precios e historial funcionan con servidor seleccionado (probar cambio west/east)
