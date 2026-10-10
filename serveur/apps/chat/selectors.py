"""Lectures de la messagerie : jamais de lecture de `messages` pour la liste ni pour les non-lus (CDC §9.22)."""

import uuid

from django.db.models import F, Q
from django.utils.dateparse import parse_datetime

from apps.accounts import selectors as comptes
from apps.core.errors import ErreurMetier
from apps.listings import selectors as annonces

from .models import Conversation, Message

PAGE_MESSAGES = 50
PLACEHOLDER_MODERE = "Message retiré par la modération."


def _uuid(valeur):
    try:
        return uuid.UUID(str(valeur))
    except ValueError:
        return None


def conversation_du_participant(utilisateur_id, conversation_id) -> Conversation:
    """404 pour tout non-participant : l'existence d'une conversation ne se révèle pas."""
    ident = _uuid(conversation_id)
    conversation = (
        Conversation.objects.filter(pk=ident)
        .filter(Q(client_id=utilisateur_id) | Q(gerant_id=utilisateur_id))
        .first()
        if ident
        else None
    )
    if conversation is None:
        raise ErreurMetier("not_found", "Conversation introuvable.", statut=404)
    return conversation


def conversation_par_id(conversation_id) -> Conversation | None:
    ident = _uuid(conversation_id)
    return Conversation.objects.filter(pk=ident).first() if ident else None


def est_client(conversation: Conversation, utilisateur_id) -> bool:
    return conversation.client_id == utilisateur_id


def autre_participant(conversation: Conversation, utilisateur_id):
    return (
        conversation.gerant_id
        if conversation.client_id == utilisateur_id
        else conversation.client_id
    )


def position_de_lecture(conversation: Conversation, utilisateur_id) -> int:
    return (
        conversation.client_read_seq
        if est_client(conversation, utilisateur_id)
        else conversation.gerant_read_seq
    )


def non_lus(conversation: Conversation, utilisateur_id) -> int:
    return max(0, conversation.last_seq - position_de_lecture(conversation, utilisateur_id))


def en_silence(conversation: Conversation, utilisateur_id, maintenant) -> bool:
    jusque = (
        conversation.client_muted_until
        if est_client(conversation, utilisateur_id)
        else conversation.gerant_muted_until
    )
    return bool(jusque and jusque > maintenant)


def liste(utilisateur_id, *, role: str, annonce_id=None, avant=None, limite: int = 30):
    """Conversations de l'utilisateur, plus actives d'abord ; curseur = date du dernier message rendu."""
    colonne = "client_id" if role == "client" else "gerant_id"
    requete = Conversation.objects.filter(
        **{colonne: utilisateur_id}, last_message_at__isnull=False
    )
    if annonce_id is not None:
        requete = requete.filter(listing_id=annonce_id)
    if avant is not None:
        requete = requete.filter(last_message_at__lt=avant)
    lignes = list(requete.order_by("-last_message_at", "-id")[: limite + 1])
    suivant = None
    if len(lignes) > limite:
        lignes = lignes[:limite]
        suivant = lignes[-1].last_message_at.isoformat()
    return lignes, suivant


def decrire(conversations: list[Conversation], utilisateur_id) -> list[dict]:
    """Aperçu de chaque conversation (annonce, interlocuteur, non-lus) en deux requêtes pour toute la page."""
    from django.utils import timezone

    maintenant = timezone.now()
    fiches = annonces.annonces_pour_messagerie({c.listing_id for c in conversations})
    noms = comptes.noms_utilisateurs({autre_participant(c, utilisateur_id) for c in conversations})
    sortie = []
    for c in conversations:
        autre = autre_participant(c, utilisateur_id)
        annonce = fiches.get(c.listing_id, {})
        sortie.append(
            {
                "id": c.pk,
                "listing": {
                    "id": annonce.get("id"),
                    "slug": annonce.get("slug"),
                    "title": annonce.get("title"),
                    "status": annonce.get("status"),
                },
                "other": {"id": autre, "name": noms.get(autre)},
                "status": c.status,
                "blocked_by_me": c.blocked_by_id == utilisateur_id,
                "last_message_preview": c.last_message_preview,
                "last_message_at": c.last_message_at,
                "unread_count": non_lus(c, utilisateur_id),
                "muted": en_silence(c, utilisateur_id, maintenant),
            }
        )
    return sortie


def total_non_lus(utilisateur_id, role: str) -> int:
    colonne, lecture = (
        ("client_id", "client_read_seq") if role == "client" else ("gerant_id", "gerant_read_seq")
    )
    return sum(
        max(0, d)
        for d in Conversation.objects.filter(**{colonne: utilisateur_id})
        .annotate(delta=F("last_seq") - F(lecture))
        .values_list("delta", flat=True)
    )


def messages(
    conversation: Conversation,
    *,
    avant_seq: int | None = None,
    apres_seq: int | None = None,
    limite: int = PAGE_MESSAGES,
):
    """Historique par `before_seq` (plus anciens, ordre croissant) ou `after_seq` (plus récents)."""
    requete = Message.objects.filter(conversation=conversation)
    if apres_seq is not None:
        lignes = list(requete.filter(seq__gt=apres_seq).order_by("seq")[: limite + 1])
        plus = len(lignes) > limite
        return lignes[:limite], plus
    if avant_seq is not None:
        requete = requete.filter(seq__lt=avant_seq)
    lignes = list(requete.order_by("-seq")[: limite + 1])
    plus = len(lignes) > limite
    return list(reversed(lignes[:limite])), plus


def message_par_id(message_id) -> Message | None:
    ident = _uuid(message_id)
    return (
        Message.objects.filter(pk=ident).select_related("conversation").first() if ident else None
    )


def parse_curseur(valeur):
    if not valeur:
        return None
    resultat = parse_datetime(valeur)
    if resultat is None:
        raise ErreurMetier("invalid_cursor", "Curseur invalide.", champs={"cursor": ["Invalide"]})
    return resultat
