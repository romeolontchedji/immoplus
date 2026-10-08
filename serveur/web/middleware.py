"""Déconnecte la session du site quand le compte change de version de sécurité (mot de passe changé ailleurs, sanction)."""

from django.contrib.auth import logout

from apps.accounts.services import jetons


class VersionDeSessionMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            etat = jetons.etat_utilisateur(str(request.user.pk))
            if etat is None or not etat["actif"] or request.session.get("tv") != etat["ver"]:
                logout(request)
        return self.get_response(request)
