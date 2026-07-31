"""Wep Scraper — entrada de la app: levanta FastAPI y (en local) abre el navegador."""

import logging
import os
import threading
import webbrowser
from pathlib import Path

import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

DATA_DIR = Path(os.getenv("DATA_DIR", BASE_DIR / "data"))
DATA_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    handlers=[
        logging.FileHandler(DATA_DIR / "wep.log", encoding="utf-8"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger("wep.app")

from backend import db  # noqa: E402  (después de configurar logging)
from backend.api import router as api_router  # noqa: E402
from backend.auth import BasicAuthMiddleware  # noqa: E402

app = FastAPI(title="Wep Scraper")
app.add_middleware(BasicAuthMiddleware)

db.init_db()

app.include_router(api_router)


@app.exception_handler(Exception)
async def manejar_excepcion_no_controlada(request: Request, exc: Exception):
    logger.exception("Error no controlado en %s %s", request.method, request.url.path)
    return JSONResponse(status_code=500, content={"detail": "Error interno. Revisá data/wep.log para más detalle."})


FRONTEND_DIR = BASE_DIR / "frontend"
app.mount("/static", StaticFiles(directory=FRONTEND_DIR / "static"), name="static")


@app.get("/")
def index():
    return FileResponse(FRONTEND_DIR / "index.html")


HOST = os.getenv("HOST", "127.0.0.1")
PORT = int(os.getenv("PORT", "8000"))
# Railway (y la mayoría de los hosts) setean esta variable; en la máquina del
# usuario no existe, así que ahí sí abrimos el navegador automáticamente.
ES_DEPLOY_REMOTO = bool(os.getenv("RAILWAY_ENVIRONMENT") or os.getenv("PORT"))


def _abrir_navegador():
    webbrowser.open(f"http://localhost:{PORT}")


if __name__ == "__main__":
    if not ES_DEPLOY_REMOTO:
        threading.Timer(1.0, _abrir_navegador).start()
    logger.info("Iniciando Wep Scraper en %s:%s (deploy remoto: %s)", HOST, PORT, ES_DEPLOY_REMOTO)
    uvicorn.run(app, host=HOST, port=PORT, log_level="info")
