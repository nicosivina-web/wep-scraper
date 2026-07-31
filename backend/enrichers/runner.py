"""Orquesta el enrichment en background y expone su progreso para polling."""

import asyncio
import logging
from datetime import datetime, timezone

from backend import db
from backend.enrichers.website import enriquecer_lead

logger = logging.getLogger("wep.enrich.runner")

CONCURRENCIA_MAX = 3


class EnrichmentState:
    def __init__(self):
        self.en_curso = False
        self.total = 0
        self.procesados = 0
        self.encontrados = 0
        self.errores = 0

    def reset(self, total: int) -> None:
        self.en_curso = True
        self.total = total
        self.procesados = 0
        self.encontrados = 0
        self.errores = 0

    def as_dict(self) -> dict:
        return {
            "en_curso": self.en_curso,
            "total": self.total,
            "procesados": self.procesados,
            "encontrados": self.encontrados,
            "errores": self.errores,
        }


state = EnrichmentState()


def _leads_pendientes() -> list[dict]:
    conn = db.get_connection()
    try:
        rows = conn.execute(
            """
            SELECT * FROM leads
            WHERE web IS NOT NULL AND web != '' AND enriquecido_at IS NULL
            """
        ).fetchall()
        return [db.dict_from_row(r) for r in rows]
    finally:
        conn.close()


def _guardar_resultado(lead_id: int, resultado: dict) -> None:
    conn = db.get_connection()
    try:
        estado = resultado.get("estado", "error")
        conn.execute(
            """
            UPDATE leads
            SET email = COALESCE(?, email),
                whatsapp = COALESCE(?, whatsapp),
                ig = COALESCE(?, ig),
                facebook = COALESCE(?, facebook),
                estado = ?,
                enriquecido_at = ?
            WHERE id = ?
            """,
            (
                resultado.get("email"),
                resultado.get("whatsapp"),
                resultado.get("ig"),
                resultado.get("facebook"),
                estado,
                datetime.now(timezone.utc).isoformat(),
                lead_id,
            ),
        )
        conn.commit()
    finally:
        conn.close()


async def _procesar_lead(sem: asyncio.Semaphore, lead: dict) -> None:
    async with sem:
        try:
            resultado = await enriquecer_lead(lead)
        except Exception as exc:
            logger.exception("Error inesperado enriqueciendo lead %s: %s", lead.get("id"), exc)
            resultado = {"estado": "error"}

        _guardar_resultado(lead["id"], resultado)
        state.procesados += 1
        if resultado.get("estado") == "enriquecido":
            state.encontrados += 1
        elif resultado.get("estado") == "error":
            state.errores += 1


async def ejecutar_enrichment() -> None:
    state.en_curso = True
    try:
        leads = _leads_pendientes()
        state.reset(total=len(leads))
        logger.info("Iniciando enrichment de %d leads", len(leads))
        sem = asyncio.Semaphore(CONCURRENCIA_MAX)
        await asyncio.gather(*(_procesar_lead(sem, lead) for lead in leads))
    except Exception:
        logger.exception("Error corriendo el enrichment en background")
    finally:
        state.en_curso = False
        logger.info(
            "Enrichment terminado: %d procesados, %d encontrados, %d errores",
            state.procesados, state.encontrados, state.errores,
        )
