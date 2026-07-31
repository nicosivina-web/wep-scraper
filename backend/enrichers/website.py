"""Enrichment de leads: fetch de sitios web + extracción de contacto."""

import asyncio
import logging
from urllib import robotparser
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup

from backend.enrichers import extractors
from backend.enrichers import website_js

logger = logging.getLogger("wep.enrich")

USER_AGENT = "WepScraperBot/1.0 (+uso interno agencia; respeta robots.txt; contacto: agencia@local)"

RUTAS_POR_IDIOMA = {
    "es": ["", "/contacto", "/nosotros", "/about", "/quienes-somos"],
    "pt": ["", "/contato", "/sobre", "/quem-somos"],
}

DELAY_ENTRE_REQUESTS = 2.0
TIMEOUT_SEGUNDOS = 15.0
MIN_TEXTO_UTIL = 200  # caracteres de texto visible; por debajo, se intenta el fallback JS


class RobotsCache:
    def __init__(self):
        self._cache: dict[str, robotparser.RobotFileParser] = {}

    async def puede_acceder(self, client: httpx.AsyncClient, url: str) -> bool:
        parsed = urlparse(url)
        origin = f"{parsed.scheme}://{parsed.netloc}"
        rp = self._cache.get(origin)
        if rp is None:
            rp = robotparser.RobotFileParser()
            try:
                resp = await client.get(urljoin(origin, "/robots.txt"), timeout=10)
                if resp.status_code == 200:
                    rp.parse(resp.text.splitlines())
                else:
                    rp.parse([])
            except httpx.HTTPError:
                rp.parse([])  # si no se puede leer robots.txt, se asume permitido
            self._cache[origin] = rp
        try:
            return rp.can_fetch(USER_AGENT, url)
        except Exception:
            return True


_robots_cache = RobotsCache()


def _texto_visible(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()
    return soup.get_text(separator=" ", strip=True)


async def _fetch_pagina(client: httpx.AsyncClient, url: str) -> str | None:
    if not await _robots_cache.puede_acceder(client, url):
        logger.info("robots.txt bloquea %s", url)
        return None
    try:
        resp = await client.get(url, timeout=TIMEOUT_SEGUNDOS, follow_redirects=True)
        if resp.status_code >= 400:
            return None
        return resp.text
    except httpx.HTTPError as exc:
        logger.info("Error fetching %s: %s", url, exc)
        return None


async def enriquecer_lead(lead: dict) -> dict:
    """Recibe un dict de lead (con 'web' y 'pais') y devuelve los campos de contacto encontrados."""
    web = lead.get("web")
    pais = lead.get("pais", "AR")
    idioma = "pt" if pais == "BR" else "es"

    if not web:
        return {"estado": "sin_web"}

    rutas = RUTAS_POR_IDIOMA.get(idioma, RUTAS_POR_IDIOMA["es"])
    resultado = {"emails": set(), "telefonos": set(), "instagram": None, "whatsapp": None, "facebook": None}
    texto_total_len = 0
    algun_fetch_ok = False
    html_para_fallback = None

    headers = {"User-Agent": USER_AGENT}
    async with httpx.AsyncClient(headers=headers) as client:
        for i, ruta in enumerate(rutas):
            url = urljoin(web if web.endswith("/") else web + "/", ruta.lstrip("/"))
            html = await _fetch_pagina(client, url)
            if html:
                algun_fetch_ok = True
                texto = _texto_visible(html)
                texto_total_len += len(texto)
                if html_para_fallback is None:
                    html_para_fallback = html
                datos = extractors.extraer_todo(texto + " " + html, pais)
                resultado["emails"].update(datos["emails"])
                resultado["telefonos"].update(datos["telefonos"])
                resultado["instagram"] = resultado["instagram"] or datos["instagram"]
                resultado["whatsapp"] = resultado["whatsapp"] or datos["whatsapp"]
                resultado["facebook"] = resultado["facebook"] or datos["facebook"]
            if i < len(rutas) - 1:
                await asyncio.sleep(DELAY_ENTRE_REQUESTS)

    if not algun_fetch_ok:
        return {"estado": "error"}

    if texto_total_len < MIN_TEXTO_UTIL:
        logger.info("Poco contenido util en %s, probando fallback Playwright", web)
        try:
            datos_js = await website_js.enriquecer_con_playwright(web, pais)
            resultado["emails"].update(datos_js.get("emails", []))
            resultado["telefonos"].update(datos_js.get("telefonos", []))
            resultado["instagram"] = resultado["instagram"] or datos_js.get("instagram")
            resultado["whatsapp"] = resultado["whatsapp"] or datos_js.get("whatsapp")
            resultado["facebook"] = resultado["facebook"] or datos_js.get("facebook")
        except Exception as exc:
            logger.warning("Fallback Playwright falló para %s: %s", web, exc)

    email = next(iter(sorted(resultado["emails"])), None)
    telefono = next(iter(sorted(resultado["telefonos"])), None)

    return {
        "estado": "enriquecido",
        "email": email,
        "whatsapp": resultado["whatsapp"] or telefono,
        "ig": resultado["instagram"],
        "facebook": resultado["facebook"],
    }
