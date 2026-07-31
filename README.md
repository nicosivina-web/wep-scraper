# Wep Scraper

Herramienta para armar bases de datos de negocios en cualquier país de LATAM por nicho, usando Google Places API (New) como fuente y enrichment propio (scraping liviano) para completar email, redes sociales y WhatsApp. Corre 100% local por defecto (no depende de servicios pagos más allá del free tier de Google Places), y opcionalmente se puede deployar a internet para que todo el equipo comparta la misma base de datos (ver [sección 6](#6-deploy-online-opcional-para-uso-compartido-en-equipo)).

## 1. Conseguir la API key de Google Places (gratis)

1. Entrá a [Google Cloud Console](https://console.cloud.google.com/) y creá un proyecto nuevo (o usá uno existente).
2. En el buscador superior escribí **"Places API (New)"** y activala (botón "Habilitar"/"Enable"). Ojo: es la API **nueva**, no la clásica "Places API" — tienen nombres parecidos pero son productos distintos.
3. Andá a **APIs y servicios → Credenciales → Crear credenciales → Clave de API**. Se genera tu API key.
4. **Restringí la key por seguridad**: abrí la key recién creada → en "Restricciones de la aplicación" elegí **"Direcciones IP"** y agregá la IP pública de la máquina donde vas a correr Wep Scraper (podés buscar "cuál es mi ip" en Google para obtenerla). Esto evita que alguien más use tu key si se filtra.
5. En "Restricciones de API" elegí **"Restringir clave"** y seleccioná únicamente **Places API (New)**.
6. Google da **USD 200 de crédito gratis por mes** para APIs de Places/Maps, que alcanza para varios miles de búsquedas mensuales de uso normal de agencia. Revisá tu consumo en **APIs y servicios → Panel**.

## 2. Instalación

Requiere Python 3.11 o superior.

```bash
python -m venv venv
venv\Scripts\activate        # en Windows
pip install -r requirements.txt
playwright install chromium
```

`playwright install chromium` descarga el navegador headless que se usa como fallback cuando un sitio necesita JavaScript para mostrar su contenido de contacto.

## 3. Configurar el `.env`

Copiá `.env.example` a `.env` y pegá tu API key:

```bash
copy .env.example .env
```

Editá `.env`:

```
GOOGLE_PLACES_API_KEY=tu-api-key-acá
```

Nunca compartas ni subas este archivo a ningún repositorio.

## 4. Correr la app

```bash
python app.py
```

Esto levanta el servidor local y abre automáticamente `http://localhost:8000` en tu navegador. La base de datos se crea sola en `data/wep.db` la primera vez que corrés la app — no requiere ninguna instalación ni configuración extra de base de datos.

## 5. Uso

1. **Buscar negocios**: elegí país, escribí el nicho (ej: "parrillas", "churrascarias", "taquerías") y la ciudad/zona, y tocá "Buscar negocios". Los resultados se agregan a la base, deduplicados automáticamente.
2. **Enriquecer pendientes**: tocá el botón en la barra lateral para completar email, WhatsApp, Instagram y Facebook de los leads que tienen sitio web. Se ve el progreso en tiempo real.
3. **Leads**: tabla principal con filtros por país, nicho, ciudad, con email, con IG, sin contactar, tags y búsqueda por nombre. Click en una fila abre el detalle y permite editar tags.
4. **Exportar**: exporta a CSV respetando los filtros aplicados, con selección de columnas.
5. **Búsquedas**: historial de todas las búsquedas realizadas; si repetís una búsqueda de menos de 7 días te avisa (podés repetirla igual).

## 6. Deploy online (opcional, para uso compartido en equipo)

Si varias personas de la agencia necesitan acceder a la misma base de leads desde distintos lugares, podés deployar Wep Scraper a internet en vez de correrlo solo en tu máquina. El proyecto ya viene listo para esto (`Dockerfile` incluido). La opción más simple es **[Railway](https://railway.app)**.

### Pasos con Railway

1. **Subí el proyecto a GitHub** (si no lo hiciste ya):
   ```bash
   git init
   git add .
   git commit -m "Wep Scraper"
   ```
   Creá un repo nuevo en GitHub y pusheá (`git remote add origin <url>` y `git push -u origin main`).

2. En [railway.app](https://railway.app), creá una cuenta, **"New Project" → "Deploy from GitHub repo"** y elegí tu repo. Railway detecta el `Dockerfile` automáticamente y lo usa para el build (no hace falta configurar nada más ahí).

3. **Agregá un Volumen persistente** (para que la base de datos no se borre en cada deploy): en el servicio, pestaña **"Settings" → "Volumes" → "Add Volume"**, con mount path `/data`. Sin esto, cada vez que redeployes perdés todos los leads guardados.

4. **Variables de entorno**: en la pestaña **"Variables"** del servicio, agregá:
   ```
   GOOGLE_PLACES_API_KEY=tu-api-key
   APP_USERNAME=un-usuario-que-elijas
   APP_PASSWORD=una-contraseña-que-elijas
   ```
   `APP_USERNAME`/`APP_PASSWORD` son **necesarias** para producción: sin ellas, la app queda abierta a cualquiera que tenga el link. Con ellas, el navegador va a pedir usuario y contraseña antes de dejar entrar (login HTTP básico).

5. Railway te da una URL pública (`algo.up.railway.app`). Esa es la que comparte todo el equipo — todos apuntan al mismo servidor y a la misma base de datos, así que los leads siempre están sincronizados entre todos sin hacer nada extra.

6. Si tu key de Google Places tiene restricción por IP (paso 4 de la sección 1), vas a tener que sacarle esa restricción o cambiarla a restricción por "referrer"/sin restricción de IP, porque la IP del servidor de Railway no es la tuya y va a cambiar. Como alternativa, dejá la key sin restricción de IP pero restringida solo a "Places API (New)" en "Restricciones de API".

### Actualizar el deploy

Cada vez que hagas `git push` a la rama conectada, Railway redeploya solo con los cambios nuevos — el volumen persistente hace que la base de datos y los leads ya cargados no se pierdan entre deploys.

## Nota legal — uso responsable de datos por país

Wep Scraper obtiene datos de negocios públicos vía Google Places API y, opcionalmente, enriquece con datos públicos visibles en los sitios web de esos negocios. Aun así, el uso de esta herramienta y de los datos obtenidos debe respetar la normativa de protección de datos personales de cada país donde se use. Algunas referencias:

- **Argentina**: Ley 25.326 de Protección de Datos Personales.
- **Brasil**: LGPD — Lei Geral de Proteção de Dados (Lei 13.709/2018).
- **México**: LFPDPPP — Ley Federal de Protección de Datos Personales en Posesión de los Particulares.
- **Chile**: Ley 19.628 sobre Protección de la Vida Privada.
- **Colombia**: Ley 1581 de 2012 de Protección de Datos Personales.
- **Uruguay**: Ley 18.331 de Protección de Datos Personales.

Recomendaciones para uso responsable:

- Incluí siempre una opción clara de **opt-out** en cualquier mensaje de outreach que envíes usando estos datos.
- No superes **1 solicitud cada 2 segundos** por sitio al enriquecer (la app ya respeta este límite por defecto).
- Respetá el `robots.txt` de cada sitio (la app lo hace automáticamente).
- No guardes ni proceses datos sensibles (salud, ideología, orientación sexual, etc.) — esta herramienta solo extrae datos de contacto comercial público (email, teléfono, redes).
- Esta nota es informativa, no constituye asesoramiento legal. Ante dudas sobre un caso de uso específico, consultá con un abogado especializado en protección de datos del país correspondiente.

## Estructura del proyecto

```
wep-scraper/
├── app.py                    # entrada: levanta FastAPI y (en local) abre el navegador
├── requirements.txt
├── Dockerfile                 # para deploy (Railway u otro host con Docker)
├── .env.example
├── data/                     # wep.db (SQLite) y wep.log se crean acá
├── backend/
│   ├── api.py                 # endpoints FastAPI
│   ├── db.py                  # esquema SQLite + migraciones
│   ├── auth.py                # login HTTP básico opcional (para deploy online)
│   ├── config/countries.py    # países LATAM soportados
│   ├── sources/google_places.py
│   ├── enrichers/              # extractors, website (httpx+BS4), website_js (Playwright), runner
│   └── exporters/csv_export.py
└── frontend/
    ├── index.html
    └── static/app.js
```

## Troubleshooting

- **"Falta GOOGLE_PLACES_API_KEY"**: revisá que el archivo `.env` exista en la raíz del proyecto y tenga la key cargada.
- **La búsqueda devuelve error 502**: normalmente es un problema con la API key (inválida, sin la API habilitada, o sin crédito). Revisá `data/wep.log` para el detalle exacto del error de Google.
- **El enrichment marca todo como "error"**: puede ser que los sitios web de esos leads estén caídos, bloqueen bots vía `robots.txt`, o tarden más de 15s en responder. Es esperable que no todos los sitios se puedan enriquecer.
- Cualquier error inesperado queda registrado en `data/wep.log` con el traceback completo.
