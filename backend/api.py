"""Endpoints FastAPI de Wep Scraper."""

import asyncio
import json
import logging
from datetime import datetime, timedelta

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from backend import db
from backend.config.countries import get_country
from backend.enrichers import runner as enrich_runner
from backend.exporters import csv_export
from backend.sources import google_places

logger = logging.getLogger("wep.api")

router = APIRouter(prefix="/api")


class BusquedaRequest(BaseModel):
    pais: str = Field(..., description="Código ISO del país, ej: AR")
    nicho: str
    ciudad: str
    radio_km: float | None = None
    cantidad: int = Field(default=20, ge=1, le=60)


@router.post("/search")
async def buscar(body: BusquedaRequest):
    pais = get_country(body.pais)
    aviso_duplicado = _chequear_busqueda_reciente(body.pais, body.nicho, body.ciudad)

    try:
        negocios = await google_places.buscar_negocios(
            nicho=body.nicho,
            ciudad=body.ciudad,
            pais_iso=pais["iso"],
            pais_nombre=pais["nombre"],
            idioma=pais["idioma"],
            radio_km=body.radio_km,
            max_resultados=body.cantidad,
        )
    except google_places.PlacesAPIError as exc:
        logger.exception("Error consultando Places API")
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    agregados, duplicados = _guardar_leads(negocios)
    _guardar_busqueda(body, cantidad_encontrada=len(negocios))

    return {
        "encontrados": len(negocios),
        "agregados": agregados,
        "duplicados": duplicados,
        "aviso_duplicado": aviso_duplicado,
    }


def _chequear_busqueda_reciente(pais: str, nicho: str, ciudad: str) -> dict | None:
    conn = db.get_connection()
    try:
        limite = (datetime.utcnow() - timedelta(days=7)).isoformat()
        row = conn.execute(
            """
            SELECT id, created_at FROM busquedas
            WHERE pais = ? AND nicho = ? AND ciudad = ? AND created_at >= ?
            ORDER BY created_at DESC LIMIT 1
            """,
            (pais, nicho, ciudad, limite),
        ).fetchone()
        if row:
            return {"busqueda_id": row["id"], "fecha": row["created_at"]}
        return None
    finally:
        conn.close()


def _guardar_leads(negocios: list[dict]) -> tuple[int, int]:
    conn = db.get_connection()
    agregados = 0
    duplicados = 0
    try:
        for n in negocios:
            try:
                conn.execute(
                    """
                    INSERT INTO leads (
                        place_id, nombre, direccion, telefono, web, categoria,
                        rating, lat, lng, pais, pais_nombre, nicho, ciudad
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        n["place_id"], n["nombre"], n["direccion"], n["telefono"],
                        n["web"], n["categoria"], n["rating"], n["lat"], n["lng"],
                        n["pais"], n["pais_nombre"], n["nicho"], n["ciudad"],
                    ),
                )
                agregados += 1
            except Exception as exc:  # place_id UNIQUE constraint u otro error de fila
                if "UNIQUE" in str(exc):
                    duplicados += 1
                else:
                    logger.warning("No se pudo guardar lead %s: %s", n.get("place_id"), exc)
        conn.commit()
    finally:
        conn.close()
    return agregados, duplicados


def _guardar_busqueda(body: BusquedaRequest, cantidad_encontrada: int) -> None:
    conn = db.get_connection()
    try:
        conn.execute(
            """
            INSERT INTO busquedas (pais, nicho, ciudad, radio, cantidad_pedida, cantidad_encontrada)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (body.pais, body.nicho, body.ciudad, body.radio_km, body.cantidad, cantidad_encontrada),
        )
        conn.commit()
    finally:
        conn.close()


@router.get("/leads")
def listar_leads(
    page: int = 1,
    page_size: int = 50,
    pais: str | None = None,
    nicho: str | None = None,
    ciudad: str | None = None,
    con_email: bool = False,
    con_ig: bool = False,
    sin_contactar: bool = False,
    tag: str | None = None,
    q: str | None = None,
):
    where, params = db.build_leads_filter(
        pais=pais, nicho=nicho, ciudad=ciudad, con_email=con_email,
        con_ig=con_ig, sin_contactar=sin_contactar, tag=tag, q=q,
    )
    conn = db.get_connection()
    try:
        offset = (page - 1) * page_size
        rows = conn.execute(
            f"SELECT * FROM leads {where} ORDER BY created_at DESC LIMIT ? OFFSET ?",
            (*params, page_size, offset),
        ).fetchall()
        total = conn.execute(f"SELECT COUNT(*) AS c FROM leads {where}", params).fetchone()["c"]
        return {
            "items": [db.dict_from_row(r) for r in rows],
            "total": total,
            "page": page,
            "page_size": page_size,
        }
    finally:
        conn.close()


@router.get("/export")
def exportar_leads(
    pais: str | None = None,
    nicho: str | None = None,
    ciudad: str | None = None,
    con_email: bool = False,
    con_ig: bool = False,
    sin_contactar: bool = False,
    tag: str | None = None,
    q: str | None = None,
    columnas: str | None = None,
):
    where, params = db.build_leads_filter(
        pais=pais, nicho=nicho, ciudad=ciudad, con_email=con_email,
        con_ig=con_ig, sin_contactar=sin_contactar, tag=tag, q=q,
    )
    conn = db.get_connection()
    try:
        rows = conn.execute(f"SELECT * FROM leads {where} ORDER BY created_at DESC", params).fetchall()
        leads = [db.dict_from_row(r) for r in rows]
    finally:
        conn.close()

    columnas_lista = columnas.split(",") if columnas else None
    csv_texto = csv_export.generar_csv(leads, columnas_lista)
    filename = csv_export.nombre_archivo(pais, nicho)

    return StreamingResponse(
        iter([csv_texto]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


class BulkAccionRequest(BaseModel):
    ids: list[int]
    accion: str = Field(..., description="'tag', 'contactado' o 'eliminar'")
    tag: str | None = None


@router.patch("/leads/bulk")
def bulk_leads(body: BulkAccionRequest):
    if not body.ids:
        raise HTTPException(status_code=400, detail="No se enviaron ids")

    placeholders = ",".join("?" for _ in body.ids)
    conn = db.get_connection()
    try:
        if body.accion == "eliminar":
            conn.execute(f"DELETE FROM leads WHERE id IN ({placeholders})", body.ids)
        elif body.accion == "contactado":
            conn.execute(
                f"UPDATE leads SET contactado_at = ? WHERE id IN ({placeholders})",
                (datetime.utcnow().isoformat(), *body.ids),
            )
        elif body.accion == "tag":
            if not body.tag:
                raise HTTPException(status_code=400, detail="Falta 'tag' para la acción 'tag'")
            rows = conn.execute(
                f"SELECT id, tags FROM leads WHERE id IN ({placeholders})", body.ids
            ).fetchall()
            for row in rows:
                try:
                    tags = json.loads(row["tags"]) if row["tags"] else []
                except (json.JSONDecodeError, TypeError):
                    tags = []
                if body.tag not in tags:
                    tags.append(body.tag)
                conn.execute("UPDATE leads SET tags = ? WHERE id = ?", (json.dumps(tags), row["id"]))
        else:
            raise HTTPException(status_code=400, detail=f"Acción desconocida: {body.accion}")
        conn.commit()
    finally:
        conn.close()
    return {"actualizados": len(body.ids)}


class TagsUpdateRequest(BaseModel):
    tags: list[str]


@router.patch("/leads/{lead_id}")
def actualizar_tags(lead_id: int, body: TagsUpdateRequest):
    conn = db.get_connection()
    try:
        cur = conn.execute(
            "UPDATE leads SET tags = ? WHERE id = ?", (json.dumps(body.tags), lead_id)
        )
        conn.commit()
        if cur.rowcount == 0:
            raise HTTPException(status_code=404, detail="Lead no encontrado")
    finally:
        conn.close()
    return {"ok": True}


@router.get("/busquedas")
def listar_busquedas():
    conn = db.get_connection()
    try:
        rows = conn.execute(
            "SELECT * FROM busquedas ORDER BY created_at DESC LIMIT 200"
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


@router.get("/countries")
def listar_paises():
    from backend.config.countries import list_countries
    return list_countries()


@router.post("/enrich/start")
async def iniciar_enrichment():
    if enrich_runner.state.en_curso:
        raise HTTPException(status_code=409, detail="Ya hay un enrichment en curso")
    asyncio.create_task(enrich_runner.ejecutar_enrichment())
    return {"iniciado": True}


@router.get("/enrich/status")
def estado_enrichment():
    return enrich_runner.state.as_dict()
