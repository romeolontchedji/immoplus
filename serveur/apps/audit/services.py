"""Écriture dans le journal d'activité (ajout seul). Unique point d'entrée pour les autres applications."""

from .models import AuditLog


def enregistrer(
    action: str,
    *,
    acteur=None,
    cible=None,
    cible_type: str | None = None,
    metadata: dict | None = None,
    ip: str | None = None,
    user_agent: str | None = None,
) -> None:
    """Journalise `action`. `cible` est un objet à clé uuid, ou on passe `cible_type` seul."""
    AuditLog.objects.create(
        actor=acteur,
        actor_role=getattr(acteur, "role", None),
        action=action[:64],
        target_type=(
            cible_type or (cible.__class__.__name__.lower() if cible is not None else None)
        ),
        target_id=getattr(cible, "pk", None),
        metadata=metadata or {},
        ip=ip or None,
        user_agent=(user_agent or "")[:255] or None,
    )


def compter_depuis(acteur, action: str, depuis) -> int:
    """Nombre d'écritures d'une action par un acteur depuis une date (plafonds de lecture du personnel)."""
    return AuditLog.objects.filter(actor=acteur, action=action, created_at__gte=depuis).count()


def purger_selon_retention(maintenant=None) -> dict:
    """Rétention (CDC §9.18) : vide ip et user_agent après 90 jours, supprime après 24 mois, via le rôle `retention`.

    Sans ce rôle (développement, tests), la fonction ne fait rien : l'application n'a pas le droit de modifier le journal.
    """
    from datetime import timedelta

    from django.db import connection, transaction
    from django.utils import timezone

    maintenant = maintenant or timezone.now()
    with transaction.atomic(), connection.cursor() as c:
        c.execute("SELECT 1 FROM pg_roles WHERE rolname = 'retention'")
        if c.fetchone() is None:
            return {"vides": 0, "supprimes": 0, "ignore": True}
        c.execute("SET LOCAL ROLE retention")
        c.execute(
            "UPDATE audit_logs SET ip = NULL, user_agent = NULL WHERE created_at < %s AND (ip IS NOT NULL OR user_agent IS NOT NULL)",
            [maintenant - timedelta(days=90)],
        )
        vides = c.rowcount
        c.execute(
            "DELETE FROM audit_logs WHERE created_at < %s", [maintenant - timedelta(days=730)]
        )
        supprimes = c.rowcount
        c.execute("RESET ROLE")
    return {"vides": vides, "supprimes": supprimes, "ignore": False}
