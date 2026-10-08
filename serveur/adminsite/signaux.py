"""Journalise les connexions, échecs et déconnexions du personnel (ajout seul dans `audit_logs`)."""

from axes.signals import user_locked_out
from django.contrib.auth.signals import user_logged_in, user_logged_out, user_login_failed
from django.dispatch import receiver
from django.utils import timezone

from apps.audit import services as audit
from apps.core.http import ip_client, user_agent


@receiver(user_logged_in)
def connexion(sender, request, user, **kwargs):
    if getattr(user, "est_personnel", False):
        request.session["debut"] = int(
            timezone.now().timestamp()
        )  # durée absolue comptée depuis la connexion
        audit.enregistrer(
            "admin.connexion",
            acteur=user,
            cible=user,
            ip=ip_client(request),
            user_agent=user_agent(request),
        )


@receiver(user_logged_out)
def deconnexion(sender, request, user, **kwargs):
    if user is not None and getattr(user, "est_personnel", False):
        audit.enregistrer(
            "admin.deconnexion",
            acteur=user,
            cible=user,
            ip=ip_client(request),
            user_agent=user_agent(request),
        )


@receiver(user_login_failed)
def echec(sender, credentials, request=None, **kwargs):
    # L'identifiant saisi n'est jamais journalisé en clair : il peut être un mot de passe tapé dans le mauvais champ.
    audit.enregistrer(
        "admin.connexion_echec",
        cible_type="admin",
        ip=ip_client(request) if request else None,
        user_agent=user_agent(request) if request else None,
    )


@receiver(user_locked_out)
def verrouillage(sender, request, username, ip_address, **kwargs):
    audit.enregistrer("admin.compte_verrouille", cible_type="admin", ip=ip_address)
