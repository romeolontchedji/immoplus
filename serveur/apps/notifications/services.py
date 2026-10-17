"""Création et livraison des notifications (CDC §7.7, §11.9, annexe B).

Une notification = une ligne du centre + un suivi de livraison + une clé d'unicité facultative. Un échec
d'envoi ne remonte jamais à l'appelant : il est consigné dans la ligne et repris par la tâche.
"""

import logging

from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.accounts import selectors as comptes
from apps.accounts.services import appareils
from apps.core import presence, temps_reel
from apps.core.errors import ErreurMetier
from apps.core.providers import push

from . import selectors, signals
from .models import Notification

journal = logging.getLogger(__name__)

MAX_ESSAIS = 5
CATEGORIES = {
    "message.received": "messages",
    "message.unanswered_reminder": "rappels",
    "listing.reminder": "rappels",
    "alert.match": "alertes",
    "alert.digest": "alertes",
    "favorite.unavailable": "alertes",
}
NON_DESACTIVABLES = {"account.sanction"}

# Canaux Android créés par l'application (mobile/src/features/notifications/push.ts). Les messages sont prioritaires :
# bannière immédiate, son et vibration, même téléphone en veille, comme une messagerie.
CANAUX = {
    "message.received": "messages",
    "message.unanswered_reminder": "messages",
    "alert.match": "alertes",
    "alert.digest": "alertes",
    "favorite.unavailable": "alertes",
    "listing.reminder": "rappels",
    "listing.reported_rented": "rappels",
}
PRIORITAIRES = {"message.received", "message.unanswered_reminder", "account.sanction"}


def options_push(n: Notification) -> push.OptionsPush:
    """Canal, priorité, pastille de non-lus et sous-titre (chambre concernée) d'une notification."""
    return push.OptionsPush(
        canal=CANAUX.get(n.kind, "compte"),
        prioritaire=n.kind in PRIORITAIRES,
        badge=selectors.non_lues(n.user_id),
        sous_titre=(n.data.get("_sous_titre") or None),
    )


def _motif_de_saut(utilisateur_id, kind: str, data: dict) -> str | None:
    """Raison pour laquelle aucun push ne doit partir (préférences de l'utilisateur), sinon None."""
    if kind in NON_DESACTIVABLES:
        return None
    prefs = comptes.preferences_notifications(utilisateur_id)
    categorie = CATEGORIES.get(kind)
    if categorie and (prefs.get(categorie) or {}).get("push") is False:
        return "categorie_coupee"
    conversation = data.get("conversation_id")
    if conversation and str(conversation) in {str(c) for c in prefs.get("silence", [])}:
        return "silence"
    return None


def resume(n: Notification) -> dict:
    return {
        "id": str(n.pk),
        "kind": n.kind,
        "title": n.title,
        "body": n.body,
        "data": {k: v for k, v in n.data.items() if not k.startswith("_")},
        "read_at": n.read_at,
        "created_at": n.created_at,
    }


def creer(
    utilisateur_id,
    kind: str,
    titre: str,
    corps: str,
    *,
    data: dict | None = None,
    dedupe_key: str | None = None,
    collapse_key: str | None = None,
    silence: bool = False,
) -> Notification | None:
    """Crée une notification. Retourne None si `dedupe_key` existe déjà (aucun doublon, jamais d'erreur)."""
    data = data or {}
    motif = "silence" if silence else _motif_de_saut(utilisateur_id, kind, data)
    champs = {
        "user_id": utilisateur_id,
        "kind": kind,
        "title": titre[:120],
        "body": corps[:255],
        "data": data,
        "collapse_key": collapse_key,
        "delivery_status": "skipped" if motif else "pending",
        "last_error": motif,
    }
    try:
        with transaction.atomic():
            if dedupe_key:
                notification, creee = Notification.objects.get_or_create(
                    dedupe_key=dedupe_key, defaults=champs
                )
                if not creee:
                    return None
            else:
                notification = Notification.objects.create(**champs)
    except IntegrityError:
        return None
    transaction.on_commit(lambda: _apres_creation(notification.pk, motif))
    return notification


def mettre_a_jour_en_silence(dedupe_key: str, titre: str, corps: str, data: dict) -> bool:
    """Réécrit une notification existante sans nouveau push (récapitulatif qui grossit) ; faux si elle n'existe pas."""
    n = Notification.objects.filter(dedupe_key=dedupe_key).first()
    if n is None:
        return False
    n.title, n.body, n.data, n.read_at = titre[:120], corps[:255], data, None
    n.save(update_fields=["title", "body", "data", "read_at"])
    temps_reel.diffuser(
        n.user_id,
        "notification.new",
        {"unread_count": selectors.non_lues(n.user_id), "notification": _jsonable(resume(n))},
    )
    return True


def _apres_creation(notification_id, motif: str | None) -> None:
    notification = Notification.objects.filter(pk=notification_id).first()
    if notification is None:
        return
    temps_reel.diffuser(
        notification.user_id,
        "notification.new",
        {
            "unread_count": selectors.non_lues(notification.user_id),
            "notification": _jsonable(resume(notification)),
        },
    )
    if motif:
        signals.push_regle.send(
            sender=Notification, kind=notification.kind, data=notification.data, motif="saute"
        )
        return
    from .tasks import envoyer_push

    envoyer_push.delay(str(notification.pk))


def _jsonable(resume: dict) -> dict:
    return {
        **resume,
        "read_at": resume["read_at"].isoformat() if resume["read_at"] else None,
        "created_at": resume["created_at"].isoformat(),
    }


def _contenu_push(n: Notification) -> tuple[str, str]:
    """Titre et corps du push ; pour un message, l'aperçu dépend de la préférence (EF-NTF-02)."""
    if n.kind == "message.received":
        prefs = comptes.preferences_notifications(n.user_id)
        if (prefs.get("messages") or {}).get("apercu") is False:
            return n.title, "Nouveau message"
    return n.title, n.body


def envoyer_push(notification_id) -> str:
    """Envoie le push aux appareils concernés. Retourne l'état : sent, partial, failed, skipped, a_reprendre."""
    n = Notification.objects.filter(pk=notification_id).first()
    if n is None:
        return "absent"
    if n.delivery_status != "pending":
        return n.delivery_status
    candidats = comptes.appareils_push(n.user_id)
    if not candidats:
        return _regler_sans_envoi(n, "aucun_appareil", motive=True)
    conversation = n.data.get("conversation_id")
    ouverts = (
        presence.appareils_sur_conversation(n.user_id, conversation)
        if conversation and n.kind == "message.received"
        else set()
    )
    deja_livres = set(n.data.get("_livres", []))
    cibles = [
        a for a in candidats if str(a["id"]) not in ouverts and str(a["id"]) not in deja_livres
    ]
    if not cibles and not deja_livres:
        return _regler_sans_envoi(n, "presence", motive=False)
    titre, corps = _contenu_push(n)
    charge = {"kind": n.kind, **{k: v for k, v in n.data.items() if not k.startswith("_")}}
    fournisseur = push.fournisseur()
    options = options_push(n)
    livres, echecs, invalides, derniere = set(deja_livres), 0, 0, ""
    for appareil in cibles:
        try:
            resultat = fournisseur.envoyer(
                appareil["token"], titre, corps, charge, n.collapse_key, options
            )
        except Exception as erreur:  # noqa: BLE001 - un fournisseur défaillant ne casse jamais l'appelant
            resultat = push.ResultatPush(ok=False, erreur=type(erreur).__name__)
        if resultat.ok:
            livres.add(str(appareil["id"]))
        elif resultat.jeton_invalide:
            invalides += 1
            appareils.desactiver_push(appareil["id"])
        else:
            echecs += 1
            derniere = resultat.erreur
    n.delivery_attempts += 1
    n.data = {**n.data, "_livres": sorted(livres)}
    if echecs and n.delivery_attempts < MAX_ESSAIS:
        n.last_error = derniere[:255]
        n.save(update_fields=["data", "delivery_attempts", "last_error"])
        return "a_reprendre"
    if livres:
        n.delivery_status = "sent" if not (echecs or invalides) else "partial"
        n.delivered_at = timezone.now()
    else:
        n.delivery_status = "failed"
        n.last_error = (derniere or "jeton_invalide")[:255]
    n.save(
        update_fields=["data", "delivery_attempts", "delivery_status", "delivered_at", "last_error"]
    )
    if livres:
        signals.push_regle.send(sender=Notification, kind=n.kind, data=n.data, motif="envoye")
    return n.delivery_status


def _regler_sans_envoi(n: Notification, motif: str, *, motive: bool) -> str:
    n.delivery_status = "skipped"
    n.last_error = motif
    n.save(update_fields=["delivery_status", "last_error"])
    if motive:  # saut motive : le message est considéré comme traité
        signals.push_regle.send(sender=Notification, kind=n.kind, data=n.data, motif="saute")
    return "skipped"


def relancer(notification_id) -> str:
    """Rattrapage : renvoie une notification dont le push n'est jamais parti ou a été supprimé par la présence."""
    n = Notification.objects.filter(pk=notification_id).first()
    if n is None:
        return "absent"
    if (
        n.delivery_status == "skipped" and n.last_error == "presence"
    ) or n.delivery_status == "pending":
        n.delivery_status, n.delivery_attempts = "pending", 0
        n.save(update_fields=["delivery_status", "delivery_attempts"])
        return envoyer_push(n.pk)
    return n.delivery_status


def trouver_par_cle(dedupe_key: str) -> Notification | None:
    return Notification.objects.filter(dedupe_key=dedupe_key).first()


# --------------------------------------------------------------- centre de notifications
def marquer_lue(utilisateur_id, notification_id) -> None:
    try:
        faites = Notification.objects.filter(
            pk=notification_id, user_id=utilisateur_id, read_at__isnull=True
        ).update(read_at=timezone.now())
        existe = (
            faites
            or Notification.objects.filter(pk=notification_id, user_id=utilisateur_id).exists()
        )
    except (ValueError, TypeError) as erreur:
        raise ErreurMetier("not_found", "Notification introuvable.", statut=404) from erreur
    if not existe:
        raise ErreurMetier("not_found", "Notification introuvable.", statut=404)


def tout_marquer_lu(utilisateur_id) -> int:
    return Notification.objects.filter(user_id=utilisateur_id, read_at__isnull=True).update(
        read_at=timezone.now()
    )


def marquer_conversation_lue(utilisateur_id, conversation_id) -> int:
    """Les notifications de messages d'une conversation sont lues quand la conversation l'est."""
    return Notification.objects.filter(
        user_id=utilisateur_id,
        kind="message.received",
        read_at__isnull=True,
        data__conversation_id=str(conversation_id),
    ).update(read_at=timezone.now())
