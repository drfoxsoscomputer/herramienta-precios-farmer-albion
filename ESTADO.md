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

## Repo GitHub (publico)
- https://github.com/drfoxsoscomputer/herramienta-precios-farmer-albion
- Nombre elegido con skill de copywriting: "La Herramienta de Precios del Farmer en Albion" (herramienta + precios + farmer + Albion)
- README en espanol con disclaimer de marca (proyecto no oficial de fans; "Albion Online" es marca de Sandbox Interactive)

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
- **SDD v2 — WORK UNIT 2 COMPLETADO (2026-08-01, slice apply 2, PR 2)**: fase A (10 items T8 en albion_config.json + tests/test_recursos_t8.py) y fase B (get_history_raw en api.py, market_summary pura en formatting.py, resumen "Resumen de mercado" en los 3 detalles de menus.py, copy neutral en textos.py, tests/test_market_summary.py). El bloque de recomendacion picar/entero fue ELIMINADO. `test_command` ahora corre las 4 baterias; 340 lineas de diff (dentro del presupuesto ~345)
- **SDD v2 — FIX UI (2026-08-01)**: barra de seleccion restaurada a CYAN (estilo de la fase de flechas, memoria #150) — el commit 6281f4f (00:07) la habia cambiado a color-del-tier/blanco; items no seleccionados sin dim; reseña del detalle de pez sin la frase "sin recomendaciones" (texto de mas); `_COLORES_OSCUROS` eliminado (codigo muerto); test regression_fase2.py seccion 8 actualizado al contrato cyan (4 baterias PASS)
- **SDD v2 — FIX POST-VERIFICACION coherencia (2026-08-01)**: coherencia total "sin recomendaciones" + ciudades en el resumen de mercado. `color_item(val, todos)` sin es_bajo (verde = mayor precio, rojo = menor, dato neutro); `market_summary` agrega `min_ciudad`/`max_ciudad` (primer match por ciudad); panel "Observacion" -> "Precio mayor por ciudad" (siempre modo max, sin "comprar/vender"); panel salsas sin veredicto CONVIENE/VENDER INSUMOS (solo numeros); _panel_resumen muestra la ciudad: "Venta min: $X (Ciudad)"; 5 reseñas reescritas en textos.py (incluye RESENAS_MENU["insumos"] que el plan no listaba pero violaba el grep de copy); `es_bajo`/`tier_num` eliminados de _ver_detalle_recurso; tests ciudad min/max en escenarios 1-2. 4/4 baterias PASS + checks de contrato OK
- Contexto persistido en Engram: `sdd-init/albion` (#153), `sdd/albion/testing-capabilities` (#154), `skill-registry` (#155)
- CodeGraph indexado en `.codegraph/` (6 archivos, 105 nodos) — regenerar con `codegraph update` tras cambios estructurales
- Selector con flechas + numeros en todos los menus (grid 2 columnas en pesca/recursos)
- Navegacion unificada: flechas mover, Enter elegir, R recargar (global), Esc volver (raiz: confirmacion para salir)
- Render SIN parpadeo: diferenciador de lineas (reescribe solo filas cambiadas, ANSI puro)
- Seleccion con barra CYAN + texto negro (estilo fase de flechas; el commit 6281f4f lo habia cambiado a color-del-tier/blanco y fue revertido)
- Numero [ x] con el color de su label (ya no amarillo fijo)
- Truecolor forzado en el frame (T6 = naranja 208 real, no amarillo degradado)
- Item "Reiniciar" eliminado de la raiz (R ya recarga desde cualquier pantalla)
- Cache 60s en api.py contra rate limit 429; backoff 2s/4s
- **SDD v2 — SLICE APPLY 3 (2026-08-01)**: market_summary SIN historial (firma `market_summary(precios, item, recetas_config=None)`); eliminados volumen_total/dia_mayor_venta/volumen_dia del calculo, del dict de retorno y del panel de resumen (dato descartado por el usuario); panel de recursos ahora "Precio mayor y menor por ciudad" (mayor + menor fusionados por linea con su ciudad via `mejor_ciudad(vals, "min")`); copy de textos.py sin "dia de mayor venta"; tests/test_market_summary.py actualizado al nuevo contrato (5 escenarios); `get_history_raw` ya no se importa ni se usa en menus.py (sigue en api.py, sin callers)
- **SDD v2 — CAMPO "uso" DETALLE DE PESCA (2026-08-01)**: campo `uso` (nombre oficial ES del plato/trofeo) agregado SOLO a los 22 peces raros de albion_config.json y albion_config.full.json (los comunes NO llevan "uso"; las claves "_Tn" son separadores y se ignoran); `RESUMEN['uso'] = 'Se usa en'` en textos.py; `_panel_resumen` gana el parametro `uso=""` (si es truthy agrega la linea DESPUES del bloque ingrediente y ANTES de diferencia_refinado; la docstring documenta que uso="" oculta la linea); `ver_detalle_pez` lee `uso = config.get("pescados", {}).get(nombre, {}).get("uso", "")` y llama `_panel_resumen(resumen, uso=uso)` SIN mostrar_ingrediente (la linea "Es ingrediente de" era falsa en peces: el pez entero no participa de salsas); `ver_detalle_insumo` INTACTA (sigue con mostrar_ingrediente=True, salsas). tests/test_market_summary.py: +2 secciones (6: integridad config raro->uso presente, comun->uso ausente; 7: Tiburón T8 -> "Trofeo de tiburón" con tilde). 4/4 baterias PASS
- **ELIMINADA GANANCIA DE REFINAR (2026-08-01)**: borrado TODO el calculo de ganancia de refinar (era recomendacion velada, no dato de mercado): `_SUFIJOS_REFINADO`, `_diferencia_refinado()` y la clave `diferencia_refinado` del retorno/docstring de `market_summary` en formatting.py; el bloque de diferencia en `_panel_resumen` y la columna "Dif" de la tabla de recurso refinado en menus.py; `RESUMEN["diferencia"]` en textos.py; seccion 4 de tests/test_market_summary.py (renumeradas 5->4, 6->5, 7->6). Contrato market_summary queda: min_venta, max_venta, min_ciudad, max_ciudad, es_ingrediente, recetas, sin_datos. `color_signo` INTACTO (sigue en salsas). 4/4 baterias PASS (26 checks)
- **UI SALSAS: separacion + extra con signo/color (2026-08-01)**: `Group` de menu_insumos_pesca separa tabla / grid / volumen con `Text("")` (la info ya no queda pegada); el "extra" de cada salsa usa `{extra:+,}` y `{pct_extra:+.1f}` con `color_signo(extra)` (verde $+103 / rojo $-103 / amarillo 0). 4/4 baterias PASS
- **UI CONSISTENCIA headers + footer + sin extra (2026-08-01)**: (1) 4 headers unificados al mismo estilo `Panel(<reseña>, title="<seccion>", border_style="cyan", box=box.ROUNDED, expand=True)` — nombre de seccion sobre el borde, reseña ADENTRO (menu_principal "Albion Helper", menu_pesca "Pesca" con LEYENDA_TIERS dentro, ver_recurso "Recurso" con nombre del recurso en negrita + reseña + LEYENDA_TIERS dentro, menu_insumos_pesca "Salsas de pescado"); (2) footer del selector reescrito: descripcion del item suelta + linea en blanco + caja con SOLO el hint (Panel cyan ROUNDED expand, col_hint + flechas + Enter + Esc salir/volver + R), identico en todas las pantallas; (3) ELIMINADO el "extra" del grid de salsas (comparacion de rentabilidad = recomendacion velada): fuera carne_max_vta/alga_max_vta/alga_px/carne_px y valor_insumos/extra/pct_extra; la 3a columna del grid es solo `[bold]{ciudad_venta}[/] ${mejor_venta:,}`; el DETALLE de cada salsa CONSERVA su analisis (ver_detalle_insumo intacta); (4) volumen por ciudad dice "uds" ("Martlock: 50,912 uds"); (5) limpieza: parametro muerto `texto_bajo` eliminado de `_menu_seleccion` (firma + 4 call sites + helper run_sel del test). 4/4 baterias PASS (26 checks) + smoke render de los 4 headers OK
- **UI PARES CRUDO/REFINADO (2026-08-01)**: menu principal (opciones 2-6) y encabezado de ver_recurso muestran cada recurso como par "crudo/refinado" (Fibra/Tela, Troncos/Tablas, Piel/Cuero, Mineral/Barra, Piedra/Bloque) via `PARES_RECURSO` en textos.py (claves = claves de config, con fallback a nombre_recurso). El encabezado de ver_recurso ya NO repite el nombre adentro: el par va sobre el borde (title) y el body queda reseña + LEYENDA_TIERS (misma anatomia que los otros 3 headers unificados). Sin cambios de logica ni de formatting.py. 4/4 baterias PASS + smoke render de los 5 headers OK
- **UI SALSAS: layout "listado arriba" (2026-08-01)**: menu_insumos_pesca ahora usa `_menu_seleccion` con el nuevo parametro `titulo_abajo`: el panel "Salsas de pescado" va ARRIBA (titulo), el listado [1][2][3] va inmediatamente despues, la descripcion/receta de la salsa seleccionada (dinamica) va ENTRE el listado y los datos, y el bloque inferior (tabla de mercado + grid recetas + volumen 7d) va DESPUES (titulo_abajo); el footer queda solo con la caja de hint. Con `titulo_abajo` activo, `footer(con_desc=False)` no imprime la descripcion abajo. Sin `titulo_abajo` (default) el resto de menus mantiene el comportamiento historico (desc en footer). 4/4 baterias PASS + smoke render navegando (receta cambia arriba)
- **UI DETALLES UNIFICADOS (2026-08-01)**: los 3 detalles (ver_detalle_pez, _ver_detalle_recurso, ver_detalle_insumo) pasan al estilo de header/footer de los menus: header = Panel(nombre del item en el borde, reseña adentro, cyan ROUNDED expand) + footer = nuevo helper `_hint_detalle()` (Panel "Esc volver · R recargar", cyan ROUNDED expand) que reemplaza los 6 hints sueltos "[Esc] Volver · [R] Recargar". El tag "T6 Comun — 8 trozos al picar" va como primera linea del cuerpo del panel de pez. El caso "sin datos" de menu_insumos_pesca tambien pasa a Panel + hint. 4/4 baterias PASS + smoke render de los 3 headers OK
- **UI HEADER CON COLOR DE PALETA (2026-08-02)**: el header de las 3 pantallas de detalle ahora se dibuja con el COMPONENTE UNICO `_panel_detalle(nombre, color, contenido)` (menus.py, junto a `_hint_detalle`) y usa el MISMO color de la paleta con que el item se lista en el menu: pez -> `info_tier()` (COLORES_TIER), recurso -> `COLORES_TIER[tier_num]` (antes `[bold cyan]` FIJO), salsa -> `ENCH_COLORS[nivel]` (antes `[bold cyan]` FIJO). El titulo y el tag "T4 Comun" van SIN negrita y el tag FUERA del `[dim]` (la negrita en terminales de 16 colores aclaraba el color: `\x1b[1;36m` vs `\x1b[36m` puro del menu). Renders ANSI verificados: pez T4=36, T8=33, recurso T5=35, salsa L2=34 — IDENTICOS al menu. 4/4 baterias PASS. Cambiar la paleta en constants.py propaga el color a menu Y detalle.
- **ENCANTAMIENTOS SOLO T4+ (2026-08-02)**: en `_ver_detalle_recurso`, los encantamientos `.1-.4` (T{tier}_LEVEL{i}@{i}) existen en Albion desde T4; T2/T3 NO tienen versiones encantadas. Nuevo flag `has_ench = int(tier_key[1:]) >= 4`: si es False se omiten las columnas `.1 .2 .3 .4` de ambas tablas (crudo/refinado), no se consultan los ids `_LEVEL*` a la API y el panel "Precio mayor y menor por ciudad" no lista niveles 1-4. Verificado con renders: T2 (Algodon) tabla solo `Ciudad | Algodon`; T4 (Cañamo) muestra `.1-.4` con datos. 4/4 baterias PASS.
- **TABLA RECURSO UNIFICADA (2026-08-02)**: el detalle de recurso en modo "todo" ya NO dibuja dos tablas apiladas (una para el crudo y otra para el refinado, con la columna `Ciudad` duplicada). Ahora es UNA sola tabla: columna `Ciudad` unica + columnas del crudo (con sus encantamientos) + columnas del refinado (con sus encantamientos), segun `modo` y `has_ench`. Verificado con renders: T2 -> `Ciudad | Algodon | Tela simple`; T4 -> `Ciudad | Cañamo | .1..4 | Tela fina | .1..4` (una fila por ciudad). 4/4 baterias PASS.
- **VOLUMEN 7 DIAS: ancho dinamico (2026-08-02)**: en `_formatear_historial` (formatting.py) la columna de volumen deja el ancho fijo `>8,` y pasa a ancho DINAMICO (`ancho_vol` = max de los volumenes incl. el Total) para que "uds" y el promedio queden SIEMPRE alineados, aun con totals de 9+ caracteres (ej. `1,715,202`). Antes el fijo `>8` desplazaba el " uds" cuando el numero superaba 8 digitos -> el Total quedaba desalineado. Verificado: pos de "uds" = 30 en todas las filas (ciudades + Total). 4/4 baterias PASS.
- **PANELES ENCOGIDOS (2026-08-02)**: los cuadros que se estiraban a todo el ancho de la pantalla ahora se encajan a su contenido con `expand=False` (4 paneles "Volumen 7 dias": pez, recurso, salsas y detalle de salsa; el "Resumen de mercado"). El resumen de mercado de un recurso en modo "todo" muestra crudo Y refinado juntos en una grid alineada [item | venta min | venta max] via `nombre_principal` + `items_extra` de `_panel_resumen` (los modos clásico/refinado de recursos y los resums de peces/salsas siguen con las filas clasicas "Venta min:/max:"). 4/4 baterias PASS + smoke renders T2/T3 sin ench y T4 con ench OK.
- **ELIMINADO PANEL DUPLICADO + DESEMPATE POR VOLUMEN (2026-08-02)**: borrado el panel "Precio mayor y menor por ciudad" (duplicaba el "Resumen de mercado" con otro orden, confundía al usuario mostrando ciudades distintas ante empate). Queda UN SOLO resumen. `market_summary` gana el parametro `volumen={ciudad: volumen}`: cuando varias ciudades empatan en el precio minimo (o maximo), la de MAYOR volumen de venta 7d desempata (si ninguna tiene dato, queda la primer match del dict). Helper `_volumen_por_ciudad(hist)` en menus.py extrae {ciudad: volumen} del historial; se pasa en recursos (todo/crudo/refinado), pez (entero) y salsas. Eliminada `_linea_mayor_menor` (muerto). Verificado: 3 ciudades a $120 -> el resumen muestra Lymhurst (40,000 uds) en vez de aleatoria. 4/4 baterias PASS + test 7 (desempate por volumen) en test_market_summary.py.

## Pendientes / ToDo
- [ ] CAMBIO SDD v2 (acordado con el usuario, preflight: interactive/both/force-chained/400):
  - [x] BASE: baterias de tests migradas de Temp a `tests/` (PR 1) — slice apply 1 completado y verificado (12 + 4 PASS)
  - [x] A: T8 en los 5 recursos (fibra/madera/cuero/mineral/piedra x crudo+refinado = 10 items) — slice apply 2 (PR 2), tests/test_recursos_t8.py PASS
  - [x] B: market_summary — resumen informativo sin recomendaciones (min/max, volumen, dia mayor venta, ingrediente, diferencia refinado) — slice apply 2 (PR 2), tests/test_market_summary.py PASS
  - [ ] C: buscador global desde menu principal (ignora acentos, busca en API, listado seleccionable)
  - [ ] D: historial de precios (get_history existe sin uso) + favoritos — definir en detalle al llegar
  - [ ] E: cambio de servidor (west=America / east=Europa / asia=Asia; hoy fijo en constants.py)
  - Estado: propuesta sdd-propose LANZADA y ABORTADA por el usuario ("seguimos luego").
  - Retomar: relanzar sdd-propose con el prompt guardado en Engram topic `sdd/albion-v2/propose-prompt` (#157); estado en `sdd/albion-v2/estado-sesion` (#156).
- [x] Propuesta aprobada (reencuadrada: resumen informativo en vez de recomendacion, sin SQLite/IA)
- [x] Specs creadas (5: test-migration, resource-t8, market-summary, global-search, server-selection) en openspec/specs/
- [x] Diseño técnico materializado por el orquestador (design.md) — el sub-agente sdd-design fallo 2x (reporte vacio)
- [x] CAUSA RAIZ arreglada: agentes sdd-* usaban modelo north-mini-code-free (reportes vacios) → cambiados a deepseek-v4-flash-free en ~/.config/opencode/opencode.json (PENDIENTE: reiniciar opencode para aplicar)
- [x] Work unit 2 (A: T8 + B: market_summary) COMPLETADO y VERIFICADO (2026-08-01): 10 items T8 en albion_config.json, get_history_raw en api.py, market_summary pura en formatting.py, bloque de recomendacion picar/entero ELIMINADO de menus.py, tests nuevos (test_recursos_t8.py 6 PASS, test_market_summary.py 7 PASS); 4/4 baterias verdes
- [x] Nombres T8 verificados contra base de datos del juego (albioncore/albiondatabase): corregidos 5 (Cáñamo fantasma/Tela barroca, Cuero fortificado, Mármol/Bloque de mármol); 5 correctos desde el aplicador (madera blanca, adamantium, piel resistente)
- [ ] Probar la herramienta en la practica con pescados (usuario)
- [ ] Continuar con recursos: fibra, madera, cuero, mineral (usuario probara)
- [ ] `logo_test.jpg` sin trackear (decisión del usuario: commit o borrar)
- [x] Repo creado en GitHub publico (2026-08-01): herramienta-precios-farmer-albion
- [x] Skills de marketing instalados (copywriting + product-marketing desde coreyhaines31/marketingskills) — registro actualizado

## Decisiones recientes
- Volumen 7 dias: columna de volumen con ancho dinamico en _formatear_historial (formatting.py) para que el Total (aun de 9+ digitos) quede alineado con las ciudades (2026-08-02)
- Tabla de recurso unificada: el detalle (modo "todo") junta crudo y refinado en UNA tabla con columna `Ciudad` unica (antes dos tablas apiladas con Ciudad duplicada) (2026-08-02)
- Encantamientos `.1-.4` solo desde T4 en recursos: T2/T3 no tienen versiones encantadas en Albion, el detalle las omite (flag `has_ench` en _ver_detalle_recurso) (2026-08-02)
- Header de detalle con color de paleta: componente unico `_panel_detalle(nombre, color, contenido)`; los 3 detalles usan el color del tier/encantamiento del item (sin negrita, tag fuera del dim) para coincidir exactamente con el color del listado del menu (2026-08-02)
- Detalles unificados: header Panel (nombre en borde + reseña adentro) y footer caja de hint via `_hint_detalle()` en los 3 detalles + caso sin-datos de salsas (2026-08-01)
- Salsas: layout "listado arriba" (opcion 2 elegida por el usuario como UX): panel header -> listado [1][2][3] -> receta de la seleccionada (dinamica) -> datos (tabla/grid/volumen) -> hint. Nuevo parametro `titulo_abajo` en `_menu_seleccion` (2026-08-01)
- Headers/footers unificados: nombre de seccion SOBRE el borde + reseña ADENTRO del panel; footer SOLO con el hint en caja, descripcion del item suelta (2026-08-01)
- ELIMINADO el "extra" del menu de salsas: era comparacion de rentabilidad (recomendacion velada, contradice "solo datos"); el DETALLE de cada salsa conserva el analisis completo (2026-08-01)
- Volumen 7 dias por ciudad rotulado "uds" (ej: "Martlock: 50,912 uds") (2026-08-01)
- market_summary SIN historial: el usuario descarto volumen_total / dia_mayor_venta / volumen_dia ("dato pasado, no sirve"); el resumen queda solo con min/max por ciudad, ingrediente y diferencia refinado; el volumen 7d SIGUE visible en los paneles de historial por ciudad del detalle; `sin_datos` ahora es `max_venta == 0` (2026-08-01)
- FIX post-verificacion: la app NO recomienda comprar/vender (el usuario decide segun su rol); los colores verde/rojo son solo posicion del precio (mayor/menor) y el resumen de mercado muestra la ciudad de cada extremo (2026-08-01)
- NOMBRE DEL REPO: "La Herramienta de Precios del Farmer en Albion" (slug: herramienta-precios-farmer-albion) — formula que el usuario aprobo: [que es herramienta] + [para que precios] + [para quien farmer] + [juego Albion]; espanol, no ingles (2026-08-01)
- Skills de marketing instalados en .agents/skills: copywriting + product-marketing (coreyhaines31/marketingskills, MIT) — metodo: git clone + copia (npx skills add quedo en modo interactivo) (2026-08-01)
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
- T8: `tests/test_recursos_t8.py` (6 checks: tier T8 en 5 recursos, 4 claves, prefijo T8_, pares, simetria T4/T6, nombres)
- Market summary: `tests/test_market_summary.py` (6 secciones: pez con datos + contrato de claves, tiburon sin ventas, ingrediente si/no, sin peticiones extra, integridad config "uso" raro/comun, tiburon T8 -> "Trofeo de tiburón")
- Correr desde la raiz: `python -X utf8 tests/regression_fase2.py && python -X utf8 tests/test_api_cache.py && python -X utf8 tests/test_recursos_t8.py && python -X utf8 tests/test_market_summary.py`
- Origenes intactos en `C:\Users\DrFox\AppData\Local\Temp\opencode\` (rollback seguro: los originales no se tocaron; los nuevos archivos en tests/ son copias con el import de sys.path relativo a la raiz)
