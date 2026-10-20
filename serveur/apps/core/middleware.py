"""Intergiciels transverses : identifiant de requête et en-têtes de sécurité (CSP stricte)."""

from django.conf import settings

from . import requete


class IdentifiantRequeteMiddleware:
    """Pose `X-Request-ID` sur la requête, les journaux et la réponse."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        identifiant = requete.nouvel_identifiant(request.headers.get("X-Request-ID"))
        jeton = requete.definir(identifiant)
        request.id_requete = identifiant
        try:
            reponse = self.get_response(request)
        finally:
            requete._identifiant.reset(jeton)
        reponse["X-Request-ID"] = identifiant
        return reponse


def construire_csp() -> str:
    """CSP sans script ni style en ligne ; sources supplémentaires uniquement par réglage."""
    scripts = getattr(settings, "CSP_SCRIPT_SOURCES", ["'self'"])
    styles = getattr(settings, "CSP_STYLE_SOURCES", ["'self'"])
    connexions = getattr(settings, "CSP_CONNECT_SOURCES", ["'self'"])
    cadres = getattr(settings, "CSP_FRAME_SOURCES", ["https://challenges.cloudflare.com"])
    medias = (
        "'self' https://res.cloudinary.com"
        if getattr(settings, "CLOUDINARY_CLOUD_NAME", "")
        else "'self'"
    )
    directives = [
        "default-src 'self'",
        f"script-src {' '.join(scripts)}",
        f"style-src {' '.join(styles)}",
        f"img-src {medias} data:",
        "font-src 'self'",
        f"connect-src {' '.join(connexions)}",
        f"media-src {medias} blob:",
        f"frame-src {' '.join(cadres)}",
        "object-src 'none'",
        "base-uri 'self'",
        "form-action 'self'",
        "frame-ancestors 'none'",
    ]
    return "; ".join(directives)


class EnTetesSecuriteMiddleware:
    """CSP, `Permissions-Policy` et `Cross-Origin-Opener-Policy` ; jamais de valeur en ligne côté page."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        reponse = self.get_response(request)
        reponse.setdefault("Content-Security-Policy", construire_csp())
        reponse.setdefault(
            "Permissions-Policy", "camera=(), microphone=(), geolocation=(), payment=()"
        )
        reponse.setdefault("Cross-Origin-Opener-Policy", "same-origin")
        return reponse
