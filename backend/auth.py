"""Autenticación HTTP Basic opcional, para cuando la app corre expuesta a internet."""

import base64
import os
import secrets

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response


class BasicAuthMiddleware(BaseHTTPMiddleware):
    """Si APP_USERNAME/APP_PASSWORD están seteados, exige HTTP Basic Auth en toda la app.

    Si no están seteados (uso local sin exposición a internet), no exige nada,
    para no romper el flujo local existente.
    """

    async def dispatch(self, request: Request, call_next):
        usuario = os.getenv("APP_USERNAME")
        clave = os.getenv("APP_PASSWORD")

        if not usuario or not clave:
            return await call_next(request)

        auth_header = request.headers.get("authorization")
        if auth_header and self._credenciales_validas(auth_header, usuario, clave):
            return await call_next(request)

        return Response(
            status_code=401,
            headers={"WWW-Authenticate": 'Basic realm="Wep Scraper"'},
            content="Autenticación requerida.",
        )

    @staticmethod
    def _credenciales_validas(auth_header: str, usuario_esperado: str, clave_esperada: str) -> bool:
        try:
            esquema, credenciales_b64 = auth_header.split(" ", 1)
            if esquema.lower() != "basic":
                return False
            decoded = base64.b64decode(credenciales_b64).decode("utf-8")
            usuario, _, clave = decoded.partition(":")
        except (ValueError, UnicodeDecodeError):
            return False

                # compare_digest no soporta strings con caracteres no-ASCII (tildes, ñ, etc.)
        # directamente, así que comparamos los bytes en UTF-8 en su lugar.
        return secrets.compare_digest(
            usuario.encode("utf-8"), usuario_esperado.encode("utf-8")
        ) and secrets.compare_digest(clave.encode("utf-8"), clave_esperada.encode("utf-8"))
