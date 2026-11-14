"""Messages entre l'équipe et les utilisateurs : réponse à une question, à un avis, suite à une décision de modération.

- L'équipe (administrateurs et modérateurs) écrit à un locataire ou à un gérant : la personne reçoit une notification
  (et un courriel si son adresse est confirmée) et lit le message dans « Équipe Immo+ ».
- La personne peut aussi écrire à l'équipe (une question) : au plus 5 messages par 24 h ; l'équipe reçoit un courriel et
  répond depuis l'administration.
"""

import datetime
import logging

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from apps.accounts import selectors as comptes
from apps.audit import services as audit
from apps.core.errors import ErreurMetier
from apps.core.tasks import envoyer_courriel
from apps.notifications import services as notifications

from .models import MessageEquipe

journal = logging.getLogger(__name__)
CORPS_MIN, CORPS_MAX, OBJET_MAX = 2, 2000, 120
PAR_JOUR_MAX = 5
ROLES_PERSONNEL = ("moderator", "admin")
ROLES_CLIENTELE = ("client", "gerant")


def _texte(corps: str) -> str:
    texte = "\n".join(ligne.rstrip() for ligne in (corps or "").strip().splitlines())
    if not CORPS_MIN <= len(texte) <= CORPS_MAX:
        raise ErreurMetier(
            "validation_error",
            f"Le message fait entre {CORPS_MIN} et {CORPS_MAX} caractères.",
            champs={"body": ["Longueur invalide"]},
        )
    return texte


@transaction.atomic
def ecrire_a(
    acteur, destinataire, corps: str, *, objet: str = "", contexte_type: str = "", contexte_id=None
) -> MessageEquipe:
    """L'équipe écrit à une personne ; les questions de cette personne encore en attente sont marquées traitées."""
    if getattr(acteur, "role", None) not in ROLES_PERSONNEL or not acteur.is_active:
        raise ErreurMetier("forbidden", "Réservé à l'équipe.", statut=403)
    if (
        destinataire is None
        or destinataire.role not in ROLES_CLIENTELE
        or destinataire.deleted_at is not None
    ):
        raise ErreurMetier("not_found", "Cette personne n'est pas joignable.", statut=404)
    texte = _texte(corps)
    message = MessageEquipe.objects.create(
        utilisateur_id=destinataire.pk,
        auteur_id=acteur.pk,
        vers_utilisateur=True,
        objet=" ".join((objet or "").split())[:OBJET_MAX],
        corps=texte,
        contexte_type=(contexte_type or "")[:12],
        contexte_id=contexte_id,
    )
    MessageEquipe.objects.filter(
        utilisateur_id=destinataire.pk, vers_utilisateur=False, traite_le__isnull=True
    ).update(traite_le=timezone.now())
    audit.enregistrer(
        "equipe.message_envoye",
        acteur=acteur,
        cible=destinataire,
        metadata={"contexte": message.contexte_type, "message": str(message.pk)},
    )
    notifications.creer(
        destinataire.pk,
        "team.message",
        message.objet or "Message de l'équipe Immo+",
        texte,
        data={"url": "/compte/equipe", "_corps": texte},
        dedupe_key=f"equipe:{message.pk}",
    )
    return message


@transaction.atomic
def classer_sans_repondre(acteur, ids) -> int:
    """Marque des questions comme traitées sans écrire à la personne ; renvoie le nombre de questions classées."""
    if acteur.role not in ROLES_PERSONNEL:
        raise ErreurMetier("forbidden", "Réservé à l'équipe.")
    nombre = MessageEquipe.objects.filter(
        pk__in=list(ids), vers_utilisateur=False, traite_le__isnull=True
    ).update(traite_le=timezone.now())
    if nombre:
        audit.enregistrer("equipe.classe_sans_reponse", acteur=acteur, metadata={"nombre": nombre})
    return nombre


def ecrire_a_l_equipe(utilisateur, corps: str, *, objet: str = "") -> MessageEquipe:
    """Une question d'un locataire ou d'un gérant à l'équipe (5 par 24 h au plus)."""
    if utilisateur.role not in ROLES_CLIENTELE:
        raise ErreurMetier("forbidden", "Réservé aux locataires et aux gérants.", statut=403)
    texte = _texte(corps)
    depuis = timezone.now() - datetime.timedelta(hours=24)
    if (
        MessageEquipe.objects.filter(
            utilisateur_id=utilisateur.pk, vers_utilisateur=False, created_at__gte=depuis
        ).count()
        >= PAR_JOUR_MAX
    ):
        raise ErreurMetier(
            "rate_limited",
            f"Tu as déjà écrit {PAR_JOUR_MAX} messages aujourd'hui : l'équipe te répond dès que possible.",
            statut=429,
        )
    message = MessageEquipe.objects.create(
        utilisateur_id=utilisateur.pk,
        auteur_id=utilisateur.pk,
        vers_utilisateur=False,
        objet=" ".join((objet or "").split())[:OBJET_MAX],
        corps=texte,
        contexte_type="question",
    )
    audit.enregistrer(
        "equipe.question_recue", acteur=utilisateur, metadata={"message": str(message.pk)}
    )
    transaction.on_commit(lambda: _prevenir_l_equipe(message, utilisateur))
    return message


def _prevenir_l_equipe(message: MessageEquipe, utilisateur) -> None:
    destinataires = comptes.courriels_equipe()
    if not destinataires:
        return
    nom = utilisateur.full_name or utilisateur.username or "Un utilisateur"
    role = "gérant" if utilisateur.role == "gerant" else "locataire"
    lien = f"https://pilotage.{settings.DOMAIN}/moderation/messageequipe/ecrire/{utilisateur.pk}/"
    texte = "\n".join(
        [
            f"{nom} ({role}) écrit à l'équipe :",
            "",
            message.corps,
            "",
            f"Répondre : {lien}",
        ]
    )
    for adresse in destinataires:
        try:
            envoyer_courriel.delay([adresse], f"Immo+ · message de {nom}", texte)
        except Exception:  # noqa: BLE001 - un courriel manquant ne doit jamais empêcher d'écrire à l'équipe
            journal.exception("Courriel de question à l'équipe impossible")


# --------------------------------------------------------------------------- lecture
def fil(utilisateur_id) -> list[MessageEquipe]:
    """Le fil d'une personne avec l'équipe, du plus ancien au plus récent."""
    return list(MessageEquipe.objects.filter(utilisateur_id=utilisateur_id).order_by("created_at"))


def marquer_lus(utilisateur_id) -> int:
    return MessageEquipe.objects.filter(
        utilisateur_id=utilisateur_id, vers_utilisateur=True, lu_le__isnull=True
    ).update(lu_le=timezone.now())


def non_lus(utilisateur_id) -> int:
    return MessageEquipe.objects.filter(
        utilisateur_id=utilisateur_id, vers_utilisateur=True, lu_le__isnull=True
    ).count()
