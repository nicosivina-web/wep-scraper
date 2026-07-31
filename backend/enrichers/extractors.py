"""Extracción de datos de contacto desde HTML: emails, teléfonos, IG, WhatsApp, Facebook."""

import re

import phonenumbers

EMAIL_RE = re.compile(
    r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}"
)

DOMINIOS_EXCLUIDOS = {
    "sentry.io", "wixpress.com", "wordpress.com", "google.com",
    "facebook.com", "instagram.com", "whatsapp.com", "ejemplo.com",
    "example.com", "sample.com", "godaddy.com", "hostinger.com",
}

# Secuencias candidatas a teléfono: dígitos con separadores típicos (+, espacios, guiones, paréntesis)
PHONE_CANDIDATE_RE = re.compile(r"[+()\d][\d\s\-().]{6,}\d")

INSTAGRAM_RE = re.compile(
    r"instagram\.com/([A-Za-z0-9_.]+)", re.IGNORECASE
)
INSTAGRAM_EXCLUDED_PREFIXES = {"p", "reel", "reels", "stories", "explore", "tv", "accounts", "direct"}

WA_ME_RE = re.compile(r"wa\.me/\+?(\d{6,15})", re.IGNORECASE)
WA_API_RE = re.compile(r"(?:api\.)?whatsapp\.com/send\?[^\"'\s]*phone=\+?(\d{6,15})", re.IGNORECASE)

FACEBOOK_RE = re.compile(
    r"facebook\.com/([A-Za-z0-9_.\-]+)", re.IGNORECASE
)
FACEBOOK_EXCLUDED_PREFIXES = {
    "sharer", "plugins", "tr", "profile.php", "share.php", "login",
    "dialog", "policies", "help", "privacy", "ads", "business",
}


def extraer_emails(texto: str) -> list[str]:
    encontrados = {m.group(0).lower() for m in EMAIL_RE.finditer(texto)}
    validos = []
    for email in encontrados:
        local, _, dominio = email.partition("@")
        if dominio in DOMINIOS_EXCLUIDOS:
            continue
        if "noreply" in local or "no-reply" in local:
            continue
        validos.append(email)
    return sorted(validos)


def extraer_telefonos(texto: str, region_code: str) -> list[str]:
    encontrados: set[str] = set()
    for match in phonenumbers.PhoneNumberMatcher(texto, region_code):
        numero = phonenumbers.format_number(
            match.number, phonenumbers.PhoneNumberFormat.E164
        )
        encontrados.add(numero)
    return sorted(encontrados)


def extraer_instagram(texto: str) -> str | None:
    for match in INSTAGRAM_RE.finditer(texto):
        handle = match.group(1).strip("/")
        primer_segmento = handle.split("/")[0].lower()
        if primer_segmento in INSTAGRAM_EXCLUDED_PREFIXES or not primer_segmento:
            continue
        return primer_segmento
    return None


def extraer_whatsapp(texto: str, region_code: str) -> str | None:
    candidato = None
    m = WA_ME_RE.search(texto)
    if m:
        candidato = m.group(1)
    else:
        m = WA_API_RE.search(texto)
        if m:
            candidato = m.group(1)
    if not candidato:
        return None
    # wa.me y whatsapp.com/send siempre traen el numero completo con codigo de
    # pais (sin '+'), no un numero nacional: parsear como E.164, sin region hint.
    try:
        numero = phonenumbers.parse("+" + candidato, None)
        if phonenumbers.is_valid_number(numero):
            return phonenumbers.format_number(numero, phonenumbers.PhoneNumberFormat.E164)
    except phonenumbers.NumberParseException:
        pass
    # Fallback: por si el link tiene un numero local sin codigo de pais.
    try:
        numero = phonenumbers.parse(candidato, region_code)
        if phonenumbers.is_valid_number(numero):
            return phonenumbers.format_number(numero, phonenumbers.PhoneNumberFormat.E164)
    except phonenumbers.NumberParseException:
        pass
    return None


def extraer_facebook(texto: str) -> str | None:
    for match in FACEBOOK_RE.finditer(texto):
        handle = match.group(1).strip("/")
        primer_segmento = handle.split("/")[0].split("?")[0].lower()
        if primer_segmento in FACEBOOK_EXCLUDED_PREFIXES or not primer_segmento:
            continue
        return primer_segmento
    return None


def extraer_todo(texto: str, region_code: str) -> dict:
    return {
        "emails": extraer_emails(texto),
        "telefonos": extraer_telefonos(texto, region_code),
        "instagram": extraer_instagram(texto),
        "whatsapp": extraer_whatsapp(texto, region_code),
        "facebook": extraer_facebook(texto),
    }
