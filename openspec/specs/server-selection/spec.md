# Selección de Servidor Specification

## Purpose
Parametrizar API_BASE y HISTORY_BASE (actualmente hardcodeado west en constants.py) con una opción UI que mapea America/Europa/Asia a west/east/asia. Esto permite al usuario cambiar entre servidores para obtener precios más precisos según su región.

## Requirements

### Requirement: UI muestra selector de servidor

El sistema MUST agregar un selector de servidor en el menú principal con tres opciones: America, Europa, Asia.

#### Scenario: menú principal muestra servidor seleccionado actualmente

- GIVEN que el servidor actual es west
- WHEN el usuario abre el menú principal
- THEN el usuario ve "Servidor: America (west)" en la parte inferior del menú

#### Scenario: cambio de servidor via menú

- GIVEN que el usuario ve el menú principal
- WHEN el usuario selecciona "Servidor" y luego cambia a "Europa"
- THEN el usuario ve "Servidor: Europa (east)" y los precios se actualizan desde el servidor east

### Requirement: mapeo de UI a technical_id de servidor

El sistema SHOULD mapear las opciones de UI America/Europa/Asia a technical_ids west/east/asia.

#### Scenario: opción America mapea a west

- GIVEN que el usuario selecciona "America"
- WHEN el usuario confirma el cambio
- THEN API_BASE = "https://west.albion-online-data.com" y HISTORY_BASE = "https://west.albion-online-data.com/api/v2/history"

#### Scenario: opción Europa mapea a east

- GIVEN que el usuario selecciona "Europa"
- WHEN el usuario confirma el cambio
- THEN API_BASE = "https://east.albion-online-data.com" y HISTORY_BASE = "https://east.albion-online-data.com/api/v2/history"

### Requirement: cambio de servidor actualiza cache

El sistema SHOULD invalidar la cache de precios cuando el servidor cambia.

#### Scenario: cache se limpia al cambiar servidor

- GIVEN que hay datos de cache para el servidor west
- WHEN el usuario cambia a servidor asia
- THEN el usuario ve una nueva petición a asia (sin datos de west)

### Requirement: server selection se guarda en app state

El sistema SHOULD mantener el servidor seleccionado entre sesiones.

#### Scenario: sesión conserva servidor seleccionado

- GIVEN que el usuario cambia servidor a Asia
- WHEN el usuario cierra y reabre la aplicación
- THEN el usuario ve "Servidor: Asia (asia)" sin necesidad de cambiar

## Casos Borde

### Límites del servidor (solo west/east/asia)

- GIVEN que el usuario intenta seleccionar un servidor no válido
- WHEN el usuario elige una opción inválida
- THEN el usuario ve un mensaje de error "servidor no válido"

### Falla de servidor mientras se navega menú

- GIVEN que el usuario está viendo la opción de servidor
- WHEN el usuario presiona Entrar sin servidor seleccionado
- THEN el usuario vuelve al menú sin cambios

### Cache se invalida correctamente

- GIVEN que el usuario ve el resumen de un item con servidor west
- WHEN el usuario cambia servidor a Europa
- THEN el usuario ve nueva petición a east (cache old no usada)

### Resiliencia ante endpoint no disponible

- GIVEN que el usuario selecciona un servidor inactivo
- WHEN el usuario ve el detalle de un item
- THEN el usuario ve un mensaje de error y una sugerencia de cambio a otro servidor