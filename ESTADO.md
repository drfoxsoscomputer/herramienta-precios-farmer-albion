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
- `ESTADO.md` — este archivo (memoria viva del proyecto)

## Estado actual
- Protocolo de continuidad global activo (AGENTS.md global): ESTADO.md + CodeGraph + responsabilidad de subagentes
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
- [ ] Probar la herramienta en la practica con pescados (usuario)
- [ ] Continuar con recursos: fibra, madera, cuero, mineral (usuario probara)
- [ ] Plan de 8 fases "helper entendible": fases 0-2 hechas; detalle de fases 3-8 NO quedo registrado — reconstruir con el usuario
- [ ] `logo_test.jpg` sin trackear (decisión del usuario: commit o borrar)

## Decisiones recientes
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
- Bateria en `C:\Users\DrFox\AppData\Local\Temp\opencode\regression_fase2.py` (12 secciones: limpiar_pantalla, _mover_cursor, _menu_seleccion, E2E menu_principal, pausa, confirmar, hints, diferenciador, colores T6 truecolor)
- API: `C:\Users\DrFox\AppData\Local\Temp\opencode\test_api_cache.py` (4 tests: cache TTL, 429 backoff)
- Correr: `python -X utf8 regression_fase2.py && python -X utf8 test_api_cache.py` desde `C:\Users\DrFox\albion`
