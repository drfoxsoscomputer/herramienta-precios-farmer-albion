# Migración de Tests Specification

## Purpose
Mover las baterías de tests de Temp a tests/ en el repo, ajustando imports y verificando que corren desde el repo raíz. Esto completa la BASE (capacidad esencial) de la propuesta.

## Requirements

### Requirement: tests/ directory existe

El sistema MUST crear la carpeta tests/ en la raíz del repo si no existe.

#### Scenario: tests/ directory creado

- GIVEN que el repo no tiene carpeta tests/
- WHEN el usuario ejecuta la migración
- THEN el usuario ve la carpeta tests/ creada en la raíz del repo

### Requirement: regression_fase2.py migrado a tests/

El sistema MUST mover regression_fase2.py de Temp a tests/ y ajustar imports.

#### Scenario: archivos movidos con imports actualizados

- GIVEN que regression_fase2.py en Temp tiene imports relativos
- WHEN el usuario ejecuta migración completa
- THEN el usuario ve regression_fase2.py en tests/ con imports ajustados

#### Scenario: test_api_cache.py migrado a tests/

- GIVEN que test_api_cache.py en Temp ejecuta pruebas de cache
- WHEN el usuario ejecuta migración completa
- THEN el usuario ve test_api_cache.py en tests/ con imports corregidos

### Requirement: tests corren desde repo raíz

El sistema MUST verificar que ambas baterías de tests se ejecutan desde el directorio raíz del repo.

#### Scenario: ejecución de tests desde repo raíz

- GIVEN que los dos archivos de tests están en tests/
- WHEN el usuario ejecuta "python -X utf8 tests/regression_fase2.py"
- THEN el usuario ve todos los tests que pasan (12 secciones)

#### Scenario: ejecución de tests desde tests/

- GIVEN que los dos archivos de tests están en tests/
- WHEN el usuario ejecuta "python -X utf8 tests/test_api_cache.py"
- THEN el usuario ve todos los tests de cache que pasan (4 tests)

### Requirement: archivos de tests importan correctamente desde tests/

El sistema MUST ajustar imports para que funcionen desde tests/.

#### Scenario: __init__.py para namespace tests

- GIVEN que los dos archivos de tests necesitan ser importados como módulos
- WHEN el usuario ejecuta migración
- THEN el usuario ve tests/__init__.py creado vacío

#### Scenario: imports relativos corregidos

- GIVEN que regression_fase2.py importó "albion_helper"
- WHEN el usuario ejecuta migración
- THEN el usuario ve regression_fase2.py importando "from ..albion_helper import *" o similar

## Comportamiento

### Ejecución de Tests

- El sistema DEBE usar el comando exacto: "python -X utf8 tests/regression_fase2.py"
- El sistema DEBE usar el comando exacto: "python -X utf8 tests/test_api_cache.py"
- Los tests deben ejecutarse exitosamente desde el directorio raíz del repo

### Verificación Post-Migración

- Después de cada migración exitosa, el sistema DEBE verificar que los tests corren exitosamente desde tests/
- Si un test falla, el sistema DEBE restaurar el original en Temp y mostrar error

## Casos Borde

### Tests fallan después de migración

- GIVEN que regression_fase2.py falla después de mover
- WHEN el usuario verifica la migración
- THEN el usuario ve error de import y recupera los archivos originales de Temp

### Tests pasan desde raiz pero fallan desde tests/

- GIVEN que los tests dependen de un working directory en particular
- WHEN el usuario ejecuta tests desde tests/ (subdirectorio)
- THEN el usuario ve fallos e intenta ejecutar desde raiz

### Importación cíclica después de migración

- GIVEN que los tests importan entre sí
- WHEN el usuario ejecuta migración
- THEN el usuario ve errores de importación cíclica

### Múltiples ejecuciones de migración

- GIVEN que los tests se mueven una vez
- WHEN el usuario ejecuta migración dos veces
- THEN el usuario ve que los archivos ya están en tests/ (no se mueven otra vez)