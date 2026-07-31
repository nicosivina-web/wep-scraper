"""Capa de acceso a SQLite para Wep Scraper."""

import json
import logging
import os
import sqlite3
from pathlib import Path

logger = logging.getLogger("wep.db")

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = Path(os.getenv("DATA_DIR", BASE_DIR / "data"))
DB_PATH = DATA_DIR / "wep.db"

LEADS_SCHEMA = """
CREATE TABLE IF NOT EXISTS leads (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    place_id TEXT UNIQUE NOT NULL,
    nombre TEXT,
    direccion TEXT,
    telefono TEXT,
    web TEXT,
    categoria TEXT,
    rating REAL,
    lat REAL,
    lng REAL,
    pais TEXT NOT NULL DEFAULT 'AR',
    pais_nombre TEXT,
    nicho TEXT,
    ciudad TEXT,
    email TEXT,
    ig TEXT,
    whatsapp TEXT,
    facebook TEXT,
    tags TEXT DEFAULT '[]',
    estado TEXT DEFAULT 'nuevo',
    enriquecido_at TEXT,
    contactado_at TEXT,
    created_at TEXT DEFAULT (datetime('now'))
)
"""

BUSQUEDAS_SCHEMA = """
CREATE TABLE IF NOT EXISTS busquedas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    pais TEXT NOT NULL,
    nicho TEXT NOT NULL,
    ciudad TEXT NOT NULL,
    radio INTEGER,
    cantidad_pedida INTEGER,
    cantidad_encontrada INTEGER,
    created_at TEXT DEFAULT (datetime('now'))
)
"""

INDEXES = [
    "CREATE INDEX IF NOT EXISTS idx_leads_pais ON leads(pais)",
    "CREATE INDEX IF NOT EXISTS idx_leads_nicho ON leads(nicho)",
    "CREATE INDEX IF NOT EXISTS idx_leads_ciudad ON leads(ciudad)",
    "CREATE INDEX IF NOT EXISTS idx_leads_estado ON leads(estado)",
    "CREATE INDEX IF NOT EXISTS idx_busquedas_lookup ON busquedas(pais, nicho, ciudad)",
]


def get_connection() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def _column_names(conn: sqlite3.Connection, table: str) -> set[str]:
    return {row["name"] for row in conn.execute(f"PRAGMA table_info({table})")}


def migrate(conn: sqlite3.Connection) -> None:
    """Migra DBs de versiones anteriores que no tengan la columna `pais`."""
    tables = {row["name"] for row in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='leads'"
    )}
    if "leads" not in tables:
        return  # tabla recién creada por init_db, ya tiene todas las columnas
    cols = _column_names(conn, "leads")
    if "pais" not in cols:
        logger.info("Migrando DB: agregando columna 'pais' a leads")
        conn.execute("ALTER TABLE leads ADD COLUMN pais TEXT NOT NULL DEFAULT 'AR'")
    if "pais_nombre" not in cols:
        conn.execute("ALTER TABLE leads ADD COLUMN pais_nombre TEXT")
    conn.commit()


def init_db() -> None:
    conn = get_connection()
    try:
        conn.execute(LEADS_SCHEMA)
        conn.execute(BUSQUEDAS_SCHEMA)
        migrate(conn)
        for idx in INDEXES:
            conn.execute(idx)
        conn.commit()
        logger.info("DB inicializada en %s", DB_PATH)
    finally:
        conn.close()


def dict_from_row(row: sqlite3.Row) -> dict:
    d = dict(row)
    if d.get("tags") is not None:
        try:
            d["tags"] = json.loads(d["tags"])
        except (json.JSONDecodeError, TypeError):
            d["tags"] = []
    return d


def build_leads_filter(
    pais: str | None = None,
    nicho: str | None = None,
    ciudad: str | None = None,
    con_email: bool | None = None,
    con_ig: bool | None = None,
    sin_contactar: bool | None = None,
    tag: str | None = None,
    q: str | None = None,
) -> tuple[str, list]:
    """Arma una clausula WHERE reutilizable para /api/leads y /api/export."""
    condiciones = []
    params: list = []

    if pais:
        condiciones.append("pais = ?")
        params.append(pais)
    if nicho:
        condiciones.append("nicho = ?")
        params.append(nicho)
    if ciudad:
        condiciones.append("ciudad = ?")
        params.append(ciudad)
    if con_email:
        condiciones.append("email IS NOT NULL AND email != ''")
    if con_ig:
        condiciones.append("ig IS NOT NULL AND ig != ''")
    if sin_contactar:
        condiciones.append("contactado_at IS NULL")
    if tag:
        condiciones.append("tags LIKE ?")
        params.append(f'%"{tag}"%')
    if q:
        condiciones.append("nombre LIKE ?")
        params.append(f"%{q}%")

    where = f"WHERE {' AND '.join(condiciones)}" if condiciones else ""
    return where, params
