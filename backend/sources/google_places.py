"""Cliente para Google Places API (New): Text Search + Place Details."""

import asyncio
import logging
import os
import time

import httpx

logger = logging.getLogger("wep.places")

PLACES_BASE_URL = "https://places.googleapis.com/v1"

SEARCH_FIELD_MASK = ",".join([
    "places.id",
    "places.displayName",
    "places.formattedAddress",
    "places.location",
    "places.rating",
    "places.primaryTypeDisplayName",
    "places.websiteUri",
    "places.internationalPhoneNumber",
    "places.nationalPhoneNumber",
])

DETAILS_FIELD_MASK = ",".join([
    "id",
    "displayName",
    "formattedAddress",
    "location",
    "rating",
    "primaryTypeDisplayName",
    "websiteUri",
    "internationalPhoneNumber",
    "nationalPhoneNumber",
])

MAX_QPS = 10
MAX_RETRIES = 4


class PlacesRateLimiter:
    """Token bucket simple para no superar MAX_QPS peticiones/segundo."""

    def __init__(self, max_qps: int = MAX_QPS):
        self._interval = 1.0 / max_qps
        self._lock = asyncio.Lock()
        self._last_call = 0.0

    async def wait(self) -> None:
        async with self._lock:
            now = time.monotonic()
            elapsed = now - self._last_call
            if elapsed < self._interval:
                await asyncio.sleep(self._interval - elapsed)
            self._last_call = time.monotonic()


_rate_limiter = PlacesRateLimiter()


class PlacesAPIError(Exception):
    pass


def _get_api_key() -> str:
    api_key = os.getenv("GOOGLE_PLACES_API_KEY")
    if not api_key:
        raise PlacesAPIError(
            "Falta GOOGLE_PLACES_API_KEY. Configurala en el archivo .env"
        )
    return api_key


async def _request_with_backoff(
    client: httpx.AsyncClient, method: str, url: str, **kwargs
) -> httpx.Response:
    for attempt in range(MAX_RETRIES):
        await _rate_limiter.wait()
        try:
            resp = await client.request(method, url, **kwargs)
        except httpx.RequestError as exc:
            if attempt == MAX_RETRIES - 1:
                raise PlacesAPIError(f"Error de red llamando a Places API: {exc}") from exc
            await asyncio.sleep(2 ** attempt)
            continue

        if resp.status_code == 429 or resp.status_code >= 500:
            if attempt == MAX_RETRIES - 1:
                raise PlacesAPIError(
                    f"Places API respondió {resp.status_code} tras {MAX_RETRIES} intentos: {resp.text[:300]}"
                )
            await asyncio.sleep(2 ** attempt)
            continue

        if resp.status_code >= 400:
            raise PlacesAPIError(f"Places API error {resp.status_code}: {resp.text[:300]}")

        return resp

    raise PlacesAPIError("Places API: se agotaron los reintentos")


def _language_code(idioma: str) -> str:
    return "pt-BR" if idioma == "pt" else "es"


async def text_search(
    query: str,
    region_code: str,
    idioma: str,
    radio_km: float | None = None,
    max_resultados: int = 20,
) -> list[dict]:
    """Busca negocios por texto libre, acotado a un país via regionCode."""
    api_key = _get_api_key()
    url = f"{PLACES_BASE_URL}/places:searchText"
    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": api_key,
        "X-Goog-FieldMask": SEARCH_FIELD_MASK,
    }
    body = {
        "textQuery": query,
        "regionCode": region_code,
        "languageCode": _language_code(idioma),
    }

    resultados: list[dict] = []
    async with httpx.AsyncClient(timeout=20) as client:
        page_token = None
        while len(resultados) < max_resultados:
            payload = dict(body)
            if page_token:
                payload["pageToken"] = page_token
            resp = await _request_with_backoff(client, "POST", url, headers=headers, json=payload)
            data = resp.json()
            places = data.get("places", [])
            resultados.extend(places)
            page_token = data.get("nextPageToken")
            if not page_token or not places:
                break
            await asyncio.sleep(2)  # Google exige esperar antes de usar el pageToken

    return resultados[:max_resultados]


def normalizar_lugar(place: dict, pais_iso: str, pais_nombre: str, nicho: str, ciudad: str) -> dict:
    location = place.get("location") or {}
    return {
        "place_id": place.get("id"),
        "nombre": (place.get("displayName") or {}).get("text"),
        "direccion": place.get("formattedAddress"),
        "telefono": place.get("internationalPhoneNumber") or place.get("nationalPhoneNumber"),
        "web": place.get("websiteUri"),
        "categoria": place.get("primaryTypeDisplayName", {}).get("text") if place.get("primaryTypeDisplayName") else None,
        "rating": place.get("rating"),
        "lat": location.get("latitude"),
        "lng": location.get("longitude"),
        "pais": pais_iso,
        "pais_nombre": pais_nombre,
        "nicho": nicho,
        "ciudad": ciudad,
    }


async def buscar_negocios(
    nicho: str, ciudad: str, pais_iso: str, pais_nombre: str, idioma: str,
    radio_km: float | None = None, max_resultados: int = 20,
) -> list[dict]:
    query = f"{nicho} en {ciudad}"
    logger.info("Buscando en Places: %s (pais=%s, idioma=%s)", query, pais_iso, idioma)
    places = await text_search(query, pais_iso, idioma, radio_km, max_resultados)
    return [normalizar_lugar(p, pais_iso, pais_nombre, nicho, ciudad) for p in places if p.get("id")]
