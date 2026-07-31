"""Fallback con Playwright para sitios que necesitan JS para mostrar contenido."""

import logging

from playwright.async_api import async_playwright

from backend.enrichers import extractors

logger = logging.getLogger("wep.enrich.js")

TIMEOUT_MS = 15_000


async def enriquecer_con_playwright(url: str, region_code: str) -> dict:
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        try:
            page = await browser.new_page()
            await page.goto(url, timeout=TIMEOUT_MS, wait_until="networkidle")
            texto = await page.inner_text("body")
            html = await page.content()
        finally:
            await browser.close()

    return extractors.extraer_todo(texto + " " + html, region_code)
