"""Exportación de leads a CSV."""

import csv
import io
from datetime import date

COLUMNAS_DISPONIBLES = [
    "nombre", "pais_nombre", "nicho", "ciudad", "direccion", "email",
    "telefono", "whatsapp", "ig", "facebook", "web", "categoria",
    "rating", "tags", "estado", "contactado_at", "created_at",
]

COLUMNAS_DEFAULT = [
    "nombre", "pais_nombre", "nicho", "ciudad", "email", "telefono",
    "whatsapp", "ig", "web", "tags", "estado",
]


def generar_csv(leads: list[dict], columnas: list[str] | None = None) -> str:
    columnas = [c for c in (columnas or COLUMNAS_DEFAULT) if c in COLUMNAS_DISPONIBLES]
    if not columnas:
        columnas = COLUMNAS_DEFAULT

    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=columnas, extrasaction="ignore")
    writer.writeheader()
    for lead in leads:
        fila = dict(lead)
        if isinstance(fila.get("tags"), list):
            fila["tags"] = ", ".join(fila["tags"])
        writer.writerow(fila)

    return buffer.getvalue()


def nombre_archivo(pais: str | None, nicho: str | None) -> str:
    pais_slug = (pais or "todos").lower()
    nicho_slug = (nicho or "todos").lower().replace(" ", "-")
    fecha = date.today().isoformat()
    return f"wep-leads-{pais_slug}-{nicho_slug}-{fecha}.csv"
