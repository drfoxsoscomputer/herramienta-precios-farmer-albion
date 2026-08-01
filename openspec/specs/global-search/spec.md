# Buscador Global Specification

## Purpose
Agregar un buscador global desde el menú principal que encuentra cualquier item por palabra parcial, ignora acentos, y muestra una lista seleccionable con el selector existente. Debe tener un fallback cuando el endpoint de búsqueda no está disponible.

## Requirements

### Requirement: buscador global desde menú principal

El sistema MUST agregar una opción "Buscar" en el menú principal que abre un buscador con búsqueda por palabra parcial.

#### Scenario: Buscador global funciona con endpoint disponible

- GIVEN que el endpoint de búsqueda está disponible
- WHEN el usuario selecciona "Buscar" en el menú principal
- THEN el usuario ve un campo de entrada y puede buscar items

#### Scenario: buscador global con fallback cuando endpoint no está disponible

- GIVEN que el endpoint de búsqueda está inaccesible (404/429)
- WHEN el usuario selecciona "Buscar" en el menú principal
- THEN el usuario ve un mensaje "búsqueda no disponible temporalmente" y se usa el catálogo del config como alternativa

### Requirement: búsqueda por palabra parcial

El sistema SHOULD permitir al usuario ingresar una palabra parcial para encontrar items.

#### Scenario: búsqueda parcial encuentra pescados

- GIVEN que la palabra parcial "pez" está en el nombre del item
- WHEN el usuario escribe "pez" en el buscador
- THEN el usuario ve todos los items que contienen "pez" (pez común, pez espada, etc.)

#### Scenario: búsqueda exacta encuentra single item

- GIVEN que se busca "tiburón T8"
- WHEN el usuario ingresa esa frase exacta
- THEN el usuario ve solo T8_FISH_SALTWATER_ALL_BOSS_SHARK

### Requirement: ignorar acentos en búsqueda

El sistema SHOULD normalizar texto de búsqueda e ignorar acentos al buscar items.

#### Scenario: búsqueda sin acentos encuentra items con acentos

- GIVEN que se escribe "pez" sin la letra con acento
- WHEN el usuario busca con "pez"
- THEN el usuario encuentra items como "pez común" que tiene acento en español

### Requirement: mapeo español->technical_id

El sistema SHOULD mapear el nombre español del item al technical_id para resultados precisos.

#### Scenario: mapeo de tiburón español a technical_id

- GIVEN que el usuario escribe "tiburón"
- WHEN el usuario busca "tiburón"
- THEN el usuario ve T8_FISH_SALTWATER_ALL_BOSS_SHARK en resultados

### Requirement: resultados seleccionables con selector existente

El sistema MUST mostrar resultados de búsqueda usando el selector existente para navegación.

#### Scenario: navegación por flechas en resultados de búsqueda

- GIVEN que la búsqueda retorna 10+ items
- WHEN el usuario presiona ↑↓ en el buscador
- THEN el usuario puede navegar por la lista de resultados seleccionables

#### Scenario: selección de item en buscador

- GIVEN que el usuario ve resultados de búsqueda
- WHEN el usuario presiona Enter en un item
- THEN el usuario ve el detalle del item seleccionado con market_summary

## Casos Borde

### Rate limit 429 del endpoint de búsqueda

- GIVEN que la API de búsqueda retorna 429 Too Many Requests
- WHEN el usuario realiza una búsqueda
- THEN el usuario ve un mensaje de error amigable y espera antes de reintentar

### Fallback a catálogo del config

- GIVEN que el endpoint de búsqueda no está disponible
- WHEN el usuario intenta buscar
- THEN el usuario ve "búsqueda deshabilitada temporalmente" y una lista de los 100 items del config filtrados localmente

### Imagen del tiburón sin ventas

- GIVEN que T8_FISH_SALTWATER_ALL_BOSS_SHARK tiene precio 0
- WHEN el usuario ve el detalle del tiburón después de una búsqueda
- THEN el usuario ve "sin datos de venta" en el market_summary

### Configuración del servidor afecta búsqueda

- GIVEN que el usuario cambia el servidor API (America/Europa/Asia)
- WHEN el usuario realiza una búsqueda
- THEN el usuario obtiene resultados de búsqueda desde el endpoint del servidor seleccionado