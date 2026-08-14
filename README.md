# Albion Helper

Herramienta de consultas de mercado para Albion Online: web local + consola, para consultar precios mientras jugás.

## 🎯 ¿Para qué sirve?

Consultar precios y datos del mercado de Albion Online desde tu PC o tu celular (red local o internet vía túnel), sin instalar nada. Filosofía del proyecto: **solo datos, sin recomendaciones de ganancia**.

## 🚀 ¿Cómo correr?

### Web (recomendada)

```bash
python -X utf8 flask_app.py
```

El servidor se inicia en el puerto **8081**:

- `http://localhost:8081` — tu PC
- `http://192.168.0.111:8081` — tu IP en la red local (para el celular en la misma red)
- `http://127.0.0.1:8081` — conexión local

Para verlo desde el celular: abrí la página de Config en la web, escaneá el QR local con la cámara, o ingresá la URL de la IP.

### Consola (original)

```bash
python -X utf8 albion_helper.py
```

Controlada con flechas del teclado. Mismo motor de datos que la web.

## 📱 Acceso desde internet (túnel)

Si el celular no está en la misma red (ej. estás en la red del ONU y la PC en el router), la IP local no llega. Solución: túnel Cloudflare (gratis, sin cuenta).

```bash
cloudflared.exe tunnel --url http://localhost:8081 --no-autoupdate
```

La URL `*.trycloudflare.com` que aparece es la dirección pública; el QR de internet en la página de Config la muestra. **La URL cambia en cada reinicio** del túnel.

## 📋 Secciones

### Inicio
Dashboard con 3 tarjetas: Pesca, Recursos y Salsas. El buscador vive en el header (siempre visible).

### Pesca
Lista de peces con su tier (color) y detalle con precios por ciudad, volumen 7 días y resumen de mercado.

### Recursos
Listado por tier, crudo vs refinado, encantamientos `.1-.4` desde T4.

### Salsas
Precios de las 5 salsas, recetas (ingredientes y cantidades), volumen semanal.

### Buscar
Búsqueda global sobre el catálogo local (ignora acentos, tokens AND). Resultados en vivo mientras escribís; detalle por tipo: arma (5 paneles por encantamiento), diario (vacío/lleno), simple (5 calidades).

### Config
URL local + internet con sus QR para abrir la web en el celular o compartirla.

## 📦 Arquitectura del proyecto

- `flask_app.py` — Web oficial (Flask + HTMX + Tailwind), puerto 8081
- `templates/` — Plantillas Jinja de todas las páginas
- `albion_helper.py` — Entry point de la consola (Rich)
- `menus.py` — UI de la consola: menús, detalles, buscador
- `api.py` — `get_prices` / `get_history_raw` con cache 60s y backoff ante 429
- `formatting.py` — Formato de precios, historial, resumen de mercado
- `catalogo.py` + `catalog.json` — Catálogo local para el buscador global (23 MB, regenerable)
- `colores_web.py` — Adaptador de colores Rich → CSS
- `constants.py`, `textos.py`, `utilidades.py` — Constantes, copy en español, helpers compartidos
- `albion_config.json` — Datos: pescados, recursos, salsas con recetas
- `requirements.txt` — Dependencias
- `version.txt` — Versión actual (para actualizaciones)

## 🛠️ Instalación

```bash
pip install -r requirements.txt
```

## 🛡️ Licencias y créditos

- Datos del juego: **Albion Online** de Sandbox Interactive (proyecto no oficial de fans)
- Datos de mercado: API pública del juego (`albion-online-data.com`)
- Interfaz web: Flask + Tailwind (CDN) + HTMX
- Consola: Rich
