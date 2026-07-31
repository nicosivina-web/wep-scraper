"""Países LATAM soportados por Wep Scraper."""

COUNTRIES = {
    "AR": {"nombre": "Argentina", "iso": "AR", "cod_telefono": "+54", "idioma": "es", "timezone": "America/Argentina/Buenos_Aires", "flag": "🇦🇷"},
    "BO": {"nombre": "Bolivia", "iso": "BO", "cod_telefono": "+591", "idioma": "es", "timezone": "America/La_Paz", "flag": "🇧🇴"},
    "BR": {"nombre": "Brasil", "iso": "BR", "cod_telefono": "+55", "idioma": "pt", "timezone": "America/Sao_Paulo", "flag": "🇧🇷"},
    "CL": {"nombre": "Chile", "iso": "CL", "cod_telefono": "+56", "idioma": "es", "timezone": "America/Santiago", "flag": "🇨🇱"},
    "CO": {"nombre": "Colombia", "iso": "CO", "cod_telefono": "+57", "idioma": "es", "timezone": "America/Bogota", "flag": "🇨🇴"},
    "CR": {"nombre": "Costa Rica", "iso": "CR", "cod_telefono": "+506", "idioma": "es", "timezone": "America/Costa_Rica", "flag": "🇨🇷"},
    "CU": {"nombre": "Cuba", "iso": "CU", "cod_telefono": "+53", "idioma": "es", "timezone": "America/Havana", "flag": "🇨🇺"},
    "EC": {"nombre": "Ecuador", "iso": "EC", "cod_telefono": "+593", "idioma": "es", "timezone": "America/Guayaquil", "flag": "🇪🇨"},
    "SV": {"nombre": "El Salvador", "iso": "SV", "cod_telefono": "+503", "idioma": "es", "timezone": "America/El_Salvador", "flag": "🇸🇻"},
    "GT": {"nombre": "Guatemala", "iso": "GT", "cod_telefono": "+502", "idioma": "es", "timezone": "America/Guatemala", "flag": "🇬🇹"},
    "HN": {"nombre": "Honduras", "iso": "HN", "cod_telefono": "+504", "idioma": "es", "timezone": "America/Tegucigalpa", "flag": "🇭🇳"},
    "MX": {"nombre": "México", "iso": "MX", "cod_telefono": "+52", "idioma": "es", "timezone": "America/Mexico_City", "flag": "🇲🇽"},
    "NI": {"nombre": "Nicaragua", "iso": "NI", "cod_telefono": "+505", "idioma": "es", "timezone": "America/Managua", "flag": "🇳🇮"},
    "PA": {"nombre": "Panamá", "iso": "PA", "cod_telefono": "+507", "idioma": "es", "timezone": "America/Panama", "flag": "🇵🇦"},
    "PY": {"nombre": "Paraguay", "iso": "PY", "cod_telefono": "+595", "idioma": "es", "timezone": "America/Asuncion", "flag": "🇵🇾"},
    "PE": {"nombre": "Perú", "iso": "PE", "cod_telefono": "+51", "idioma": "es", "timezone": "America/Lima", "flag": "🇵🇪"},
    "PR": {"nombre": "Puerto Rico", "iso": "PR", "cod_telefono": "+1", "idioma": "es", "timezone": "America/Puerto_Rico", "flag": "🇵🇷"},
    "DO": {"nombre": "República Dominicana", "iso": "DO", "cod_telefono": "+1", "idioma": "es", "timezone": "America/Santo_Domingo", "flag": "🇩🇴"},
    "UY": {"nombre": "Uruguay", "iso": "UY", "cod_telefono": "+598", "idioma": "es", "timezone": "America/Montevideo", "flag": "🇺🇾"},
    "VE": {"nombre": "Venezuela", "iso": "VE", "cod_telefono": "+58", "idioma": "es", "timezone": "America/Caracas", "flag": "🇻🇪"},
}

DEFAULT_COUNTRY = "AR"


def get_country(iso: str) -> dict:
    return COUNTRIES.get(iso.upper(), COUNTRIES[DEFAULT_COUNTRY])


def list_countries() -> list[dict]:
    return list(COUNTRIES.values())
