# La Herramienta de Precios del Farmer en Albion

Herramienta CLI (Python + Rich) para consultar precios de mercado de Albion Online. Dirigida a **pescadores, refinadores, transportistas y farmers** que juegan en zona segura y quieren decidir dónde vender con datos, no con intuición.

> Proyecto no oficial de fans. No está afiliado, respaldado ni patrocinado por Sandbox Interactive GmbH. "Albion Online" es una marca registrada de Sandbox Interactive GmbH. Los datos de precios provienen de la API pública albion-online-data.com.

## Qué hace

- Consulta precios de venta de pescados, recursos e insumos en las ciudades del juego.
- Muestra precios mínimos/máximos, volumen y día de mayor venta (resumen informativo).
- Indica si un item es ingrediente de receta (ej. salsas).
- Buscador global que ignora tildes y mayúsculas.
- Selección de servidor: América (west), Europa (east), Asia (asia).

La herramienta **no recomienda qué vender**: te da los datos objetivos y vos decidís. Pensada para el farmer que lleva la cuenta de su plata.

## Cómo correr

```powershell
python -X utf8 albion_helper.py
```

Se requiere Python 3.8+ y `rich`. En Windows la consola usa la API nativa (funciona en cmd.exe legacy).

## Tests

```powershell
python -X utf8 tests/regression_fase2.py
python -X utf8 tests/test_api_cache.py
```

## Estructura

| Archivo | Rol |
|---------|-----|
| `albion_helper.py` | Punto de entrada |
| `menus.py` | Navegación e interfaz de consola |
| `formatting.py` | Formato, normalización de texto y resumen de mercado |
| `api.py` | Acceso a la API con cache y reintentos |
| `constants.py` | Constantes, tiers y servidores |
| `textos.py` | Textos de la interfaz y mapeo de búsqueda |
| `albion_config.json` | Catálogo de items (pescados, recursos, insumos) |
| `tests/` | Baterías de tests |

## Desarrollo con SDD

Este proyecto usa Spec-Driven Development. Los cambios se planifican en `openspec/` (propuestas, specs, diseño, tareas) antes de implementarse.

## Licencia

MIT — uso educativo y personal. Sin garantías; los precios son datos de mercado del juego y pueden variar.
