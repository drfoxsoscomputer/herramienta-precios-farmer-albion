# Resumen de Mercado Specification

## Purpose
Reemplazar la recomendación "picar/entero" con un resumen informativo que muestra datos objetivos sobre cada item: precio de venta mínimo/máximo, volumen de ventas, día de mayor venta (datos de 7 días), e ingredientes de receta. La herramienta NO decide qué hacer con el material del usuario.

## Requirements

### Requirement: market_summary muestra precio de venta mínimo/máximo

El sistema SHOULD mostrar el precio de venta mínimo y máximo para cada item en el resumen.

#### Scenario: Resumen de precio para pescado con datos de ventas

- GIVEN que un pescado tiene datos de precios en la API
- WHEN el usuario ve el detalle del pescado con market_summary
- THEN el usuario ve sell_price_min y sell_price_max mostrados

#### Scenario: Resumen de precio para tiburón sin ventas

- GIVEN que T8_FISH_SALTWATER_ALL_BOSS_SHARK tiene sell_price_min = 0 y sell_price_max = 0
- WHEN el usuario ve el detalle del tiburón con market_summary
- THEN el usuario ve "sin datos de venta" en lugar de 0

### Requirement: market_summary muestra volumen de ventas

El sistema SHOULD calcular y mostrar el volumen total de ventas en el resumen.

#### Scenario: Volumen para pescado con ventas múltiples

- GIVEN que hay múltiples registros de ventas en el historial para un item
- WHEN el usuario visualiza el detalle del item con market_summary
- THEN el usuario ve el total de item_count sumado

### Requirement: market_summary muestra día de mayor venta

El sistema SHOULD agrupar el historial por día de la semana y mostrar el día con más ventas.

#### Scenario: Día de mayor venta con historial completo

- GIVEN que el historial contiene al menos 7 días de datos
- WHEN el usuario ve el detalle del item con market_summary
- THEN el usuario ve "martes" u otro día de la semana como el día más vendido

#### Scenario: Día de mayor venta con historial incompleto

- GIVEN que el historial solo tiene 3 días de datos
- WHEN el usuario visualiza el detalle del item con market_summary
- THEN el usuario ve solo los días disponibles (ejemplo: lunes, miércoles, viernes)

### Requirement: market_summary muestra ingredientes de receta

El sistema SHOULD cruzar referencias con recetas del albion_config.json e indicar si el item es ingrediente.

#### Scenario: Ingrediente de pescado

- GIVEN que un pescado es ingrediente de una receta
- WHEN el usuario ve el detalle del pescado con market_summary
- THEN el usuario ve "es ingrediente de [receta]"

#### Scenario: No es ingrediente

- GIVEN que un item no es usado en ninguna receta del config
- WHEN el usuario visualiza el detalle del item con market_summary
- THEN el usuario ve "no es ingrediente"

### Requirement: market_summary reutiliza datos del historial

El sistema SHOULD usar el mismo historial que la API proporciona (item_count + timestamp cada ~2h) para cálculos.

#### Scenario: Formato histórico consistente

- GIVEN que get_history ya devuelve item_count por item con timestamp
- WHEN el usuario solicita market_summary
- THEN el usuario recibe cálculos sin peticiones adicionales a la API

## Casos Borde

### Tiburón sin ventas

- GIVEN que T8_FISH_SALTWATER_ALL_BOSS_SHARK tiene sell_price_min = 0 y sell_price_max = 0
- WHEN el usuario ve el detalle del tiburón con market_summary
- THEN el usuario ve "sin datos de venta" sin error en la aplicación

### Histórico < 7 días

- GIVEN que el historial solo tiene 2-3 días de datos
- WHEN el usuario visualiza el día de mayor venta
- THEN el usuario ve solo los días disponibles con datos

### Búsqueda con acentos

- GIVEN que el usuario busca un item con acento (ejemplo: ñ)
- WHEN el usuario usa el buscador global
- THEN el usuario encuentra el item (la búsqueda ignora acentos)