# ESTADO — Albion Helper

> Una pagina que cualquier sesion futura lee primero. Si esto no esta
> actualizado, es un bug mio, no del usuario.

## Que es
Helper de consola (Python + Rich) para Albion Online: consulta precios de
mercado de la API albion-online-data.com y recomienda donde vender
(entero vs picado) por ciudad.

## Como correr
```
python albion_helper.py
```
Windows, consola compatible con VT (Windows Terminal / cmd de Win10+).

## Estructura
- `albion_helper.py` — entry point (llama a menus.menu_principal)
- `menus.py` — toda la UI: selector con flechas, menus, detalles, colores por tier
- `constants.py` — ciudades, REF_MAP, COLORES_TIER, etc.
- `api.py` — get_prices/get_history con cache 60s y backoff ante 429
- `formatting.py` — helpers puros de formato (precios, colores, historial)
- `textos.py` — reseñas de ayuda (RESENAS_MENU, RESENAS_DETALLE, LEYENDA_TIERS)
- `albion_config.json` — datos: pescados (38), recursos (fibra/madera/cuero/mineral/piedra), salsas con recetas
- `openspec/config.yaml` — config SDD (contexto, strict_tdd: false, comando de tests, reglas por fase)
- `openspec/specs/` + `openspec/changes/archive/` — estructura SDD (fuente de verdad, versionada en git)
- `ESTADO.md` — este archivo (memoria viva del proyecto)

## Estado actual
- Protocolo de continuidad global activo (AGENTS.md global): ESTADO.md + CodeGraph + responsabilidad de subagentes
- **SDD inicializado (2026-08-01)**: modo hybrid (openspec + engram); strict_tdd: false (no hay pytest); artifact store "both"; PRs force-chained; review budget 400 líneas
- **SDD v2 — BASE COMPLETADA (2026-08-01, slice apply 1)**: baterias de tests migradas de Temp a `tests/` (regression_fase2.py 12 secciones + test_api_cache.py 4 tests); `test_command` en openspec/config.yaml (apply y verify) apunta a `tests/`; ambos PASS desde la raiz con `python -X utf8`
- Contexto persistido en Engram: `sdd-init/albion` (#153), `sdd/albion/testing-capabilities` (#154), `skill-registry` (#155)
- CodeGraph indexado en `.codegraph/` (6 archivos, 105 nodos) — regenerar con `codegraph update` tras cambios estructurales
- Selector con flechas + numeros en todos los menus (grid 2 columnas en pesca/recursos)
- Navegacion unificada: flechas mover, Enter elegir, R recargar (global), Esc volver (raiz: confirmacion para salir)
- Render SIN parpadeo: diferenciador de lineas (reescribe solo filas cambiadas, ANSI puro)
- Seleccion con barra del color del tier + texto negro (fallback blanco para colores oscuros)
- Numero [ x] con el color de su label (ya no amarillo fijo)
- Truecolor forzado en el frame (T6 = naranja 208 real, no amarillo degradado)
- Item "Reiniciar" eliminado de la raiz (R ya recarga desde cualquier pantalla)
- Cache 60s en api.py contra rate limit 429; backoff 2s/4s

## Pendientes / ToDo
- [ ] CAMBIO SDD v2 (acordado con el usuario, preflight: interactive/both/force-chained/400):
  - [x] BASE: baterias de tests migradas de Temp a `tests/` (PR 1) — slice apply 1 completado y verificado (12 + 4 PASS)
  - [ ] A: T8 en los 5 recursos (fibra/madera/cuero/mineral/piedra x crudo+refinado = 10 items)
  - [ ] B: regla ingredientes — no recomendar picar pescados clave (recetas del config + volumen)
  - [ ] C: buscador global desde menu principal (ignora acentos, busca en API, listado seleccionable)
  - [ ] D: historial de precios (get_history existe sin uso) + favoritos — definir en detalle al llegar
  - [ ] E: cambio de servidor (west=America / east=Europa / asia=Asia; hoy fijo en constants.py)
  - Estado: propuesta sdd-propose LANZADA y ABORTADA por el usuario ("seguimos luego").
  - Retomar: relanzar sdd-propose con el prompt guardado en Engram topic `sdd/albion-v2/propose-prompt` (#157); estado en `sdd/albion-v2/estado-sesion` (#156).
- [x] Propuesta aprobada (reencuadrada: resumen informativo en vez de recomendacion, sin SQLite/IA)
- [x] Specs creadas (5: test-migration, resource-t8, market-summary, global-search, server-selection) en openspec/specs/
- [x] Diseño técnico materializado por el orquestador (design.md) — el sub-agente sdd-design fallo 2x (reporte vacio)
- [x] CAUSA RAIZ arreglada: agentes sdd-* usaban modelo north-mini-code-free (reportes vacios) → cambiados a deepseek-v4-flash-free en ~/.config/opencode/opencode.json (PENDIENTE: reiniciar opencode para aplicar)
- [ ] Probar la herramienta en la practica con pescados (usuario)
- [ ] Continuar con recursos: fibra, madera, cuero, mineral (usuario probara)
- [ ] `logo_test.jpg` sin trackear (decisión del usuario: commit o borrar)

## Decisiones recientes
- CAUSA RAIZ sub-agentes: sdd-* de fases complejas usaban north-mini-code-free (reportes vacios) → deepseek-v4-flash-free (2026-08-01)
- Diseño v2: get_server_base() en api.py, cache sin invalidacion (URL incluye servidor), market_summary() en formatting.py devolviendo dict, normalizar() con unicodedata, buscador plan B catalogo local, selected_server en config (2026-08-01)
- BASE v2 (migracion de tests): sys.path absoluto de Temp reemplazado por path derivado de `__file__` (`os.path.dirname(os.path.dirname(os.path.abspath(__file__)))`) — los tests corren desde la raiz sin import relativo (no aplica `python -m`, solo script directo) (2026-08-01)
- CAMBIO v2 acordado: T8 recursos + regla ingredientes + buscador global (ignora acentos, API) + historial/favoritos + cambio de servidor (2026-08-01)
- API Albion tiene 3 servidores por subdominio: west (America), east (Europa), asia (Asia) — hoy fija a west (2026-08-01)
- SDD init hecho: openspec/ + Engram sdd-init/albion; sin pytest -> strict_tdd: false (2026-08-01)
- Protocolo anti-limbo global: ESTADO.md por proyecto + codegraph + verificar subagentes (2026-08-01)
- `.atl/` y `.codegraph/` en .gitignore (artefactos de tooling regenerables) (2026-08-01)
- Selector sin parpadeo: frame a buffer + reescribir solo filas cambiadas (2026-08-01)
- Barra de seleccion = color del tier, texto negro; oscuros -> blanco (2026-08-01)
- T6 dark_orange -> truecolor 208 (Rich degradaba a amarillo en 16 colores) (2026-08-01)
- Raiz sale solo con Esc; solo digitos visibles como atajo (2026-07-31)
- Navegacion unificada Esc/Enter/R; tecla 0 eliminada de submenus (2026-07-31)
- Despedida: "Que la plata te sobre!" (2026-07-31)
- Espanol neutro en la UI (usuario venezolano, no voseo) (2026-07-31)
- Cache 60s + backoff 429 en api.py (2026-07-31)

## Tests / verificacion
- Bateria en `tests/regression_fase2.py` (12 secciones: limpiar_pantalla, _mover_cursor, _menu_seleccion, E2E menu_principal, pausa, confirmar, hints, diferenciador, colores T6 truecolor)
- API: `tests/test_api_cache.py` (4 tests: cache TTL, 429 backoff)
- Correr desde la raiz: `python -X utf8 tests/regression_fase2.py && python -X utf8 tests/test_api_cache.py`
- Origenes intactos en `C:\Users\DrFox\AppData\Local\Temp\opencode\` (rollback seguro: los originales no se tocaron; los nuevos archivos en tests/ son copias con el import de sys.path relativo a la raiz)
