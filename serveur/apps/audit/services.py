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
