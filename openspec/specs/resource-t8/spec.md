# Recursos T8 Specification

## Purpose
Agregar los 10 items de recursos T8 (crudo+refinado) a albion_config.json: fibra/madera/cuero/mineral/piedra (5 pares crudo/refinado). Esto completa el inventario T8 para que el helper muestre todos los niveles de recursos en Albion Online.

## Requirements

### Requirement: T8_FIBER añadido a albion_config.json

El sistema MUST agregar una entrada T8_FIBER (fibra cruda) a albion_config.json, junto con su versión refinada T8_CLOTH (tela).

#### Scenario: Verificación de T8_FIBER/T8_CLOTH en el inventario

- GIVEN que albion_config.json existe con datos de pescados T8
- WHEN un usuario carga el inventario desde albion_config.json
- THEN el usuario puede ver T8_FIBER en tier 8 (derecha: fibra) y T8_CLOTH (izquierda: tela) en la UI

### Requirement: T8_WOOD añadido a albion_config.json

El sistema MUST agregar una entrada T8_WOOD (madera) a albion_config.json, junto con su versión refinada T8_PLANKS (tablas).

#### Scenario: Verificación de T8_WOOD/T8_PLANKS en el inventario

- GIVEN el archivo albion_config.json
- WHEN el usuario visualiza recursos de tier 8 en el menú principal
- THEN el usuario puede seleccionar T8_WOOD (madera) y T8_PLANKS (tablas)

### Requirement: T8_HIDE añadido a albion_config.json

El sistema MUST agregar una entrada T8_HIDE (cuero) a albion_config.json, junto con su versión refinada T8_LEATHER (cuero procesado).

#### Scenario: Verificación de T8_HIDE/T8_LEATHER en el inventario

- GIVEN albion_config.json con pescados T8
- WHEN un usuario abre la sección de recursos
- THEN el usuario ve T8_HIDE (cuero) e T8_LEATHER (cuero procesado) listados

### Requirement: T8_ORE añadido a albion_config.json

El sistema MUST agregar una entrada T8_ORE (mineral) a albion_config.json, junto con su versión refinada T8_METALBAR (barra metálica).

#### Scenario: Verificación de T8_ORE/T8_METALBAR en el inventario

- GIVEN el archivo de configuración del helper
- WHEN el usuario recorre el menú de recursos T8
- THEN el usuario selecciona T8_ORE (mineral) y T8_METALBAR (barra metálica)

### Requirement: T8_ROCK añadido a albion_config.json

El sistema MUST agregar una entrada T8_ROCK (piedra) a albion_config.json, junto con su versión refinada T8_STONEBLOCK (bloque de piedra).

#### Scenario: Verificación de T8_ROCK/T8_STONEBLOCK en el inventario

- GIVEN albion_config.json actualizado con pescados T8
- WHEN un usuario busca un recurso T8 específico
- THEN el usuario puede encontrar T8_ROCK (piedra) y T8_STONEBLOCK (bloque de piedra)

## Comportamiento

Todos los 10 items T8 (5 crudos + 5 refinados) deben seguir el mismo esquema de datos que los items T4/T6 existentes en albion_config.json, incluyendo:
- Identificador técnico (ejemplo: T8_FIBER)
- Etapa (T8)
- Etiqueta derecha (ejemplo: fibra)
- Etiqueta izquierda (ejemplo: tela)
- Receta (opcional, vacía para recursos que no se refinan)
- ID de icono (opcional)
- Comentarios (opcional)