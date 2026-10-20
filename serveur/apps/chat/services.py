"""Messagerie : ouverture, envoi idempotent, lecture, blocage, silence (CDC §7.6, §10.5, §11.7, §11.9)."""

import logging
import statistics

from django.db import IntegrityError, transaction
from django.db.models import F
from django.utils import timezone

from apps.accounts import selectors as comptes
from apps.core import parametres, redis_file, stats, temps_reel
from apps.core.errors import ErreurMetier
from apps.listings import selectors as annonces
from apps.listings.enums import StatutAnnonce
from apps.listings.services import contenu
from apps.listings.services.entretien import annonces_louees_depuis
from apps.notifications import services as notifications
from apps.notifications import textes

from . import selectors, signals
from .models import Conversation, Message

journal = logging.getLogger(__name__)

LONGUEUR_MAX = 2000
APERCU_MAX = 80


# --------------------------------------------------------------- sérialisation selon le lecteur
def message_pour(message: Message, lecteur_id, *, personnel: bool = False) -> dict:
    """Représentation d'un message pour un lecteur : masquage, retrait par la modération, motif de marquage."""
    est_expediteur = message.sender_id == lecteur_id
    retire = message.moderation_status != "visible"
    if personnel:
        corps = message.body
    elif retire:
        corps = selectors.PLACEHOLDER_MODERE
    elif est_expediteur:
        corps = message.body
    else:
        corps = message.body_masked or message.body
    return {
        "id": message.pk,
        "seq": message.seq,
        "sender_id": message.sender_id,
        "client_msg_id": message.client_msg_id,
        "kind": message.kind,
        "body": corps,
        "moderation_status": message.moderation_status,
        "flag_reason": message.flag_reason if (est_expediteur or personnel) else None,
        "created_at": message.created_at,
    }


def _jsonable(d: dict) -> dict:
    return {
        k: (str(v) if k in ("id", "sender_id", "client_msg_id") and v else v) for k, v in d.items()
    } | {"created_at": d["created_at"].isoformat()}


# --------------------------------------------------------------- garde-fous
def _exiger_actif(utilisateur) -> None:
    if not utilisateur.is_active:
        raise ErreurMetier(
            "account_suspended", "Ton compte est suspendu : tu ne peux pas écrire.", statut=403
        )


def _limiter_debit(utilisateur) -> None:
    limite = int(parametres.lire("MESSAGE_PER_MINUTE"))
    r = redis_file.client()
    cle = f"chat:debit:{utilisateur.pk}:{int(timezone.now().timestamp() // 60)}"
    compte = r.incr(cle)
    if compte == 1:
        r.expire(cle, 90)
    if compte > limite:
        raise ErreurMetier(
            "rate_limited",
            "Trop de messages. Réessaie dans une minute.",
            statut=429,
            entetes={"Retry-After": "60"},
        )


def _nettoyer(corps) -> str:
    texte = str(corps or "").strip()
    if not texte:
        raise ErreurMetier(
            "validation_error", "Le message est vide.", champs={"body": ["Obligatoire"]}
        )
    if len(texte) > LONGUEUR_MAX:
        raise ErreurMetier(
            "validation_error",
            f"{LONGUEUR_MAX} caractères au plus.",
            champs={"body": ["Trop long"]},
        )
    return texte


def _analyser_coordonnees(texte: str) -> dict:
    """Applique `CONTACT_LEAK_MODE` : retourne {masque, motif, avertir} ou refuse en mode `block` (CDC §11.7).

    Par défaut `off` (décision du 2026-10-18) : locataire et gérant échangent librement numéros et liens, sans
    masquage, rappel ni signalement automatique. Les autres modes restent disponibles dans les paramètres.
    """
    if parametres.lire("CONTACT_LEAK_MODE") == "off":
        return {"masque": None, "motif": None, "avertir": False, "motifs": []}
    d = contenu.detecter(texte)
    if not d.forts and not d.faibles:
        return {"masque": None, "motif": None, "avertir": False, "motifs": []}
    motifs = [*d.forts, *d.faibles]
    motif = motifs[0]
    if not d.forts:  # mots-clés seuls : toujours seulement signalés
        return {"masque": None, "motif": motif, "avertir": False, "motifs": motifs}
    mode = parametres.lire("CONTACT_LEAK_MODE")
    if mode == "block":
        raise ErreurMetier(
            "contact_detected",
            "Les coordonnées (numéro, e-mail, lien) ne sont pas autorisées : les échanges se font dans Immo+.",
            statut=422,
            champs={"body": [f"Motif : {motif}"]},
        )
    return {
        "masque": contenu.masquer(texte) if mode == "mask" else None,
        "motif": motif,
        "avertir": True,
        "motifs": motifs,
    }


def _garde_conversation(conversation: Conversation, utilisateur) -> None:
    if conversation.status == "read_only":
        raise ErreurMetier(
            "conversation_read_only", "Cette conversation est en lecture seule.", statut=409
        )
    if conversation.status == "blocked" and conversation.blocked_by_id != utilisateur.pk:
        raise ErreurMetier("conversation_blocked", "Cette conversation est bloquée.", statut=409)


# --------------------------------------------------------------- envoi
def envoyer(utilisateur, conversation_id, corps, client_msg_id) -> tuple[Message, bool, dict]:
    """Enregistre un message. Retourne (message, créé, info) ; `info["warning"]` est le rappel à l'expéditeur.

    Idempotent par `client_msg_id` : une nouvelle tentative renvoie le message existant sans doublon.
    """
    from uuid import UUID

    try:
        identifiant = UUID(str(client_msg_id))
    except ValueError as erreur:
        raise ErreurMetier(
            "validation_error",
            "Identifiant de message invalide.",
            champs={"client_msg_id": ["UUID attendu"]},
        ) from erreur
    conversation = selectors.conversation_du_participant(utilisateur.pk, conversation_id)
    existant = Message.objects.filter(
        conversation=conversation, sender=utilisateur, client_msg_id=identifiant
    ).first()
    if existant is not None:
        return existant, False, {"warning": _rappel(existant.flag_reason)}
    _exiger_actif(utilisateur)
    texte = _nettoyer(corps)
    _garde_conversation(conversation, utilisateur)
    _limiter_debit(utilisateur)
    analyse = _analyser_coordonnees(texte)
    try:
        with transaction.atomic():
            verrouillee = Conversation.objects.select_for_update().get(pk=conversation.pk)
            _garde_conversation(verrouillee, utilisateur)
            verrouillee.last_seq += 1
            message = Message.objects.create(
                conversation=verrouillee,
                seq=verrouillee.last_seq,
                sender=utilisateur,
                client_msg_id=identifiant,
                body=texte,
                body_masked=analyse["masque"],
                flag_reason=analyse["motif"],
            )
            verrouillee.last_message_at = message.created_at
            verrouillee.last_sender = utilisateur
            verrouillee.last_message_preview = (analyse["masque"] or texte)[:APERCU_MAX]
            if verrouillee.gerant_id == utilisateur.pk and verrouillee.first_reply_at is None:
                verrouillee.first_reply_at = message.created_at
            # L'expéditeur a, par définition, lu jusqu'à son propre message.
            if verrouillee.client_id == utilisateur.pk:
                verrouillee.client_read_seq = verrouillee.last_seq
            else:
                verrouillee.gerant_read_seq = verrouillee.last_seq
            verrouillee.save()
            transaction.on_commit(
                lambda: _apres_envoi(message.pk, analyse["motifs"] if analyse["avertir"] else [])
            )
    except (
        IntegrityError
    ):  # deux envois simultanés du même client_msg_id : le second relit le premier
        existant = Message.objects.filter(
            conversation=conversation, sender=utilisateur, client_msg_id=identifiant
        ).first()
        if existant is None:
            raise
        return existant, False, {"warning": _rappel(existant.flag_reason)}
    stats.incrementer("messages")
    return message, True, {"warning": _rappel(analyse["motif"]) if analyse["avertir"] else None}


def _rappel(motif) -> str | None:
    if motif in ("telephone", "numero_epele", "email", "lien"):
        return "Pour ta sécurité, garde les échanges dans Immo+ : les coordonnées sont masquées et signalées à l'équipe."
    return None


def _apres_envoi(message_id, motifs: list[str]) -> None:
    """Diffusion directe par WebSocket, notification et signalement automatique (après validation de la transaction)."""
    message = selectors.message_par_id(message_id)
    if message is None:
        return
    conversation = message.conversation
    for participant in (conversation.client_id, conversation.gerant_id):
        temps_reel.diffuser(
            participant,
            "message.new",
            {
                "conversation_id": str(conversation.pk),
                "message": _jsonable(message_pour(message, participant)),
            },
        )
    from .tasks import notifier_message

    notifier_message.delay(str(message.pk))
    if motifs:
        signals.contact_detecte.send(
            sender=Message, conversation_id=conversation.pk, message_id=message.pk,
            expediteur_id=message.sender_id, motifs=motifs,
        )  # fmt: skip


# --------------------------------------------------------------- ouverture
def ouvrir(
    utilisateur, annonce_id, corps, client_msg_id
) -> tuple[Conversation, Message, bool, dict]:
    """Ouvre (ou retrouve) la conversation d'une annonce et y envoie le premier message (EF-MSG-01)."""
    if getattr(utilisateur, "role", None) != "client":
        raise ErreurMetier(
            "wrong_audience", "Seuls les locataires ouvrent une conversation.", statut=403
        )
    _exiger_actif(utilisateur)
    annonce = annonces.annonce_pour_messagerie(annonce_id) if _uuid_ok(annonce_id) else None
    if annonce is None or annonce["status"] != StatutAnnonce.PUBLISHED:
        existante = _conversation_existante(utilisateur, annonce)
        if existante is None:
            raise ErreurMetier(
                "listing_unavailable",
                "Cette annonce n'est plus disponible.",
                statut=404 if annonce is None else 409,
            )
        conversation, cree = existante, False
    else:
        if annonce["gerant_user_id"] == utilisateur.pk:
            raise ErreurMetier(
                "forbidden", "Tu ne peux pas écrire à propos de ta propre annonce.", statut=403
            )
        conversation, cree = _obtenir_ou_creer(utilisateur, annonce)
    message, _, info = envoyer(utilisateur, conversation.pk, corps, client_msg_id)
    conversation.refresh_from_db()
    if cree:
        stats.incrementer("conversations_started")
        stats.incrementer("conversations_started", sujet=str(annonce["id"]))
    return conversation, message, cree, info


def demarrer(utilisateur, annonce_id) -> Conversation:
    """« Contacter le gérant » : ouvre (ou retrouve) la conversation sans message imposé (plan v3, B6).

    Le locataire écrit lui-même son premier message dans la discussion ; tant qu'elle est vide, elle n'apparaît
    pas dans les listes et le gérant n'est pas dérangé."""
    if getattr(utilisateur, "role", None) != "client":
        raise ErreurMetier(
            "wrong_audience", "Seuls les locataires ouvrent une conversation.", statut=403
        )
    _exiger_actif(utilisateur)
    annonce = annonces.annonce_pour_messagerie(annonce_id) if _uuid_ok(annonce_id) else None
    if annonce is None or annonce["status"] != StatutAnnonce.PUBLISHED:
        existante = _conversation_existante(utilisateur, annonce)
        if existante is None:
            raise ErreurMetier(
                "listing_unavailable",
                "Cette annonce n'est plus disponible.",
                statut=404 if annonce is None else 409,
            )
        return existante
    if annonce["gerant_user_id"] == utilisateur.pk:
        raise ErreurMetier(
            "forbidden", "Tu ne peux pas écrire à propos de ta propre annonce.", statut=403
        )
    conversation, cree = _obtenir_ou_creer(utilisateur, annonce)
    if cree:
        stats.incrementer("conversations_started")
        stats.incrementer("conversations_started", sujet=str(annonce["id"]))
    return conversation


def _uuid_ok(valeur) -> bool:
    from uuid import UUID

    try:
        UUID(str(valeur))
        return True
    except ValueError:
        return False


def _conversation_existante(utilisateur, annonce) -> Conversation | None:
    if annonce is None:
        return None
    return Conversation.objects.filter(listing_id=annonce["id"], client=utilisateur).first()


def _obtenir_ou_creer(utilisateur, annonce: dict) -> tuple[Conversation, bool]:
    existante = Conversation.objects.filter(listing_id=annonce["id"], client=utilisateur).first()
    if existante is not None:
        return existante, False
    debut = timezone.localtime().replace(hour=0, minute=0, second=0, microsecond=0)
    if Conversation.objects.filter(client=utilisateur, created_at__gte=debut).count() >= int(
        parametres.lire("NEW_CONVERSATIONS_PER_DAY")
    ):
        raise ErreurMetier(
            "rate_limited",
            "Tu as atteint la limite de nouvelles conversations pour aujourd'hui.",
            statut=429,
        )
    try:
        with transaction.atomic():
            return (
                Conversation.objects.create(
                    listing_id=annonce["id"],
                    client=utilisateur,
                    gerant_id=annonce["gerant_user_id"],
                ),
                True,
            )
    except IntegrityError:
        return Conversation.objects.get(listing_id=annonce["id"], client=utilisateur), False


# --------------------------------------------------------------- lecture
def lire(utilisateur, conversation_id, jusqua_seq: int) -> Conversation:
    """Position de lecture (jamais en arrière) ; accusés envoyés aux deux participants (EF-MSG-07)."""
    if not isinstance(jusqua_seq, int) or jusqua_seq < 0:
        raise ErreurMetier(
            "validation_error",
            "Position invalide.",
            champs={"up_to_seq": ["Entier positif attendu"]},
        )
    conversation = selectors.conversation_du_participant(utilisateur.pk, conversation_id)
    with transaction.atomic():
        verrouillee = Conversation.objects.select_for_update().get(pk=conversation.pk)
        cible = min(jusqua_seq, verrouillee.last_seq)
        champ = "client_read_seq" if verrouillee.client_id == utilisateur.pk else "gerant_read_seq"
        if cible <= getattr(verrouillee, champ):
            return verrouillee
        setattr(verrouillee, champ, cible)
        verrouillee.save(update_fields=[champ, "updated_at"])
        # Constat de lecture : ces messages n'ont plus besoin de push (CDC §11.9, point 7).
        Message.objects.filter(
            conversation=verrouillee, seq__lte=cible, notified_at__isnull=True
        ).exclude(sender=utilisateur).update(notified_at=timezone.now())
        transaction.on_commit(lambda: _apres_lecture(verrouillee.pk, utilisateur.pk, cible))
    return verrouillee


def _apres_lecture(conversation_id, lecteur_id, jusqua_seq: int) -> None:
    conversation = selectors.conversation_par_id(conversation_id)
    if conversation is None:
        return
    notifications.marquer_conversation_lue(lecteur_id, conversation_id)
    for participant in (conversation.client_id, conversation.gerant_id):
        temps_reel.diffuser(
            participant, "conversation.read",
            {"conversation_id": str(conversation_id), "by": str(lecteur_id), "up_to_seq": jusqua_seq},
        )  # fmt: skip


# --------------------------------------------------------------- blocage et silence
def _diffuser_statut(conversation: Conversation) -> None:
    for participant in (conversation.client_id, conversation.gerant_id):
        temps_reel.diffuser(
            participant, "conversation.updated",
            {"conversation_id": str(conversation.pk), "status": conversation.status,
             "blocked_by": str(conversation.blocked_by_id) if conversation.blocked_by_id else None},
        )  # fmt: skip


def bloquer(utilisateur, conversation_id) -> Conversation:
    conversation = selectors.conversation_du_participant(utilisateur.pk, conversation_id)
    if conversation.status == "read_only":
        raise ErreurMetier(
            "conversation_read_only", "Cette conversation est en lecture seule.", statut=409
        )
    conversation.status, conversation.blocked_by = "blocked", utilisateur
    conversation.save(update_fields=["status", "blocked_by", "updated_at"])
    transaction.on_commit(lambda: _diffuser_statut(conversation))
    return conversation


def debloquer(utilisateur, conversation_id) -> Conversation:
    conversation = selectors.conversation_du_participant(utilisateur.pk, conversation_id)
    if conversation.status != "blocked" or conversation.blocked_by_id != utilisateur.pk:
        raise ErreurMetier("forbidden", "Seul celui qui a bloqué peut débloquer.", statut=403)
    conversation.status, conversation.blocked_by = "open", None
    conversation.save(update_fields=["status", "blocked_by", "updated_at"])
    transaction.on_commit(lambda: _diffuser_statut(conversation))
    return conversation


def definir_silence(utilisateur, conversation_id, jusqua) -> Conversation:
    conversation = selectors.conversation_du_participant(utilisateur.pk, conversation_id)
    if jusqua is not None and jusqua <= timezone.now():
        jusqua = None
    champ = (
        "client_muted_until" if conversation.client_id == utilisateur.pk else "gerant_muted_until"
    )
    setattr(conversation, champ, jusqua)
    conversation.save(update_fields=[champ, "updated_at"])
    return conversation


def passer_en_lecture_seule(conversation_ids) -> int:
    """Annonce louée depuis plus de 30 jours : les conversations restent lisibles mais plus modifiables."""
    faites = Conversation.objects.filter(
        pk__in=list(conversation_ids), status__in=["open", "blocked"]
    ).update(status="read_only", updated_at=timezone.now())
    for conversation in Conversation.objects.filter(
        pk__in=list(conversation_ids), status="read_only"
    ):
        _diffuser_statut(conversation)
    return faites


# --------------------------------------------------------------- notification d'un message (file `notifications`)
def notifier(message_id) -> str:
    """Crée la notification du destinataire pour ce message (une par message) et lance son push."""
    message = selectors.message_par_id(message_id)
    if message is None or message.kind != "text":
        return "absent"
    conversation = message.conversation
    destinataire = selectors.autre_participant(conversation, message.sender_id)
    if selectors.position_de_lecture(conversation, destinataire) >= message.seq:
        Message.objects.filter(pk=message.pk, notified_at__isnull=True).update(
            notified_at=timezone.now()
        )
        return "lu"
    existante = notifications.trouver_par_cle(f"message:{message.pk}")
    if existante is not None:
        return notifications.relancer(existante.pk)
    noms = comptes.noms_utilisateurs([message.sender_id])
    apercu = (message.body_masked or message.body)[:APERCU_MAX]
    silence = selectors.en_silence(conversation, destinataire, timezone.now())
    annonce = annonces.annonce_pour_messagerie(conversation.listing_id)
    chambre = textes.tronquer(annonce["title"], 32) if annonce else None
    nom = noms.get(message.sender_id) or "Nouveau message"
    # La notification d'une conversation remplace la précédente (même collapse_key) : elle dit combien attendent.
    # Compté jusqu'à ce message.
    en_attente = message.seq - selectors.position_de_lecture(conversation, destinataire)
    corps = f"{en_attente} nouveaux messages · {apercu}" if en_attente > 1 else apercu
    notifications.creer(
        destinataire,
        "message.received",
        f"{nom} · {chambre}" if chambre else nom,  # comme une messagerie : qui, à propos de quoi
        corps,
        data={"conversation_id": str(conversation.pk), "message_id": str(message.pk), "seq": message.seq,
              "listing_id": str(conversation.listing_id), "_sous_titre": chambre, "_nombre": en_attente},
        dedupe_key=f"message:{message.pk}",
        collapse_key=f"conv:{conversation.pk}",
        silence=silence,
    )  # fmt: skip
    return "cree"


def marquer_notifie(message_id) -> None:
    Message.objects.filter(pk=message_id, notified_at__isnull=True).update(
        notified_at=timezone.now()
    )


def rattraper(delai_s: int = 30) -> int:
    """Rattrapage chaque minute : tout message sans notification ni lecture depuis plus de 30 s repart (EF-NTF-07)."""
    limite = timezone.now() - timezone.timedelta(seconds=delai_s)
    traites = 0
    for message in (
        Message.objects.filter(notified_at__isnull=True, kind="text", created_at__lt=limite)
        .select_related("conversation")
        .order_by("created_at")[:200]
    ):
        notifier(message.pk)
        traites += 1
    return traites


def rappeler_gerants_sans_reponse() -> int:
    """Message resté non lu depuis 2 h : un rappel au gérant, une seule fois par état de lecture (EF-NTF-08)."""
    heures = int(parametres.lire("UNANSWERED_REMINDER_H"))
    limite = timezone.now() - timezone.timedelta(hours=heures)
    envoyes = 0
    for c in Conversation.objects.filter(
        last_message_at__lt=limite,
        last_seq__gt=F("gerant_read_seq"),
        last_sender_id=F("client_id"),
        status="open",
    )[:500]:
        nom = comptes.noms_utilisateurs([c.client_id]).get(c.client_id) or "Un locataire"
        non_lus = textes.pluriel(
            selectors.non_lus(c, c.gerant_id), "message non lu", "messages non lus"
        )
        n = notifications.creer(
            c.gerant_id,
            "message.unanswered_reminder",
            f"{nom} attend ta réponse",
            f"{non_lus} depuis plus de {textes.pluriel(heures, 'heure')}. "
            "Réponds vite : les locataires choisissent le gérant le plus réactif.",
            data={"conversation_id": str(c.pk), "listing_id": str(c.listing_id)},
            dedupe_key=f"reminder:{c.pk}:{c.last_seq}",
            silence=selectors.en_silence(c, c.gerant_id, timezone.now()),
        )
        if n is not None:
            envoyes += 1
            if parametres.lire("SMS_FALLBACK_ENABLED"):
                _sms_de_repli(c.gerant_id)
    return envoyes


def _sms_de_repli(gerant_id) -> None:
    """SMS de repli au gérant (désactivé par défaut) : un échec n'interrompt jamais le rappel."""
    from apps.core.providers import sms

    numero = comptes.telephone(gerant_id)
    if not numero:
        return
    try:
        sms.fournisseur().envoyer(
            numero, "Immo+ : un locataire attend ta réponse. Ouvre l'application."
        )
    except Exception:  # noqa: BLE001
        journal.warning("sms_repli_echoue")


def prevenir_conversations(annonce_id, nouveau_statut: str) -> int:
    """Annonce louée, masquée ou retirée : événement temps réel et notification aux locataires en conversation."""
    annonce = annonces.annonce_pour_messagerie(annonce_id)
    if annonce is None:
        return 0
    envoyees = 0
    for c in Conversation.objects.filter(listing_id=annonce_id):
        _diffuser_statut(c)
        titre = textes.tronquer(annonce["title"], 40)
        n = notifications.creer(
            c.client_id,
            "favorite.unavailable",
            f"« {titre} » vient d'être louée"
            if nouveau_statut == StatutAnnonce.RENTED
            else f"« {titre} » n'est plus disponible",
            "Continue ta recherche : d'autres chambres t'attendent sur Immo+.",
            data={
                "listing_id": str(annonce_id),
                "slug": annonce["slug"],
                "conversation_id": str(c.pk),
            },
            dedupe_key=f"favorite:{c.client_id}:{annonce_id}:{nouveau_statut}",  # même clé que les favoris : pas de doublon
        )
        envoyees += 1 if n else 0
    return envoyees


def moderer_message(message_id, nouveau_statut: str) -> Message:
    """Masque ou supprime un message pour les participants ; le texte d'origine reste lisible par le personnel."""
    if nouveau_statut not in ("masked", "deleted", "visible"):
        raise ErreurMetier("validation_error", "Statut de message inconnu.", statut=400)
    message = selectors.message_par_id(message_id)
    if message is None:
        raise ErreurMetier("not_found", "Message introuvable.", statut=404)
    message.moderation_status = nouveau_statut
    message.save(update_fields=["moderation_status"])
    conversation = message.conversation
    for participant in (conversation.client_id, conversation.gerant_id):
        temps_reel.diffuser(
            participant, "message.moderated",
            {"conversation_id": str(conversation.pk), "message_id": str(message.pk), "seq": message.seq,
             "moderation_status": nouveau_statut},
        )  # fmt: skip
    return message


def passer_en_lecture_seule_apres_location() -> int:
    """Annonce louée depuis 30 jours : ses conversations passent en lecture seule (EF-MSG-08)."""
    jours = int(parametres.lire("READONLY_AFTER_RENT_DAYS"))
    annonces_ids = annonces_louees_depuis(jours)
    ids = Conversation.objects.filter(
        listing_id__in=annonces_ids, status__in=["open", "blocked"]
    ).values_list("pk", flat=True)
    return passer_en_lecture_seule(list(ids))


def calculer_indicateurs_gerants() -> dict:
    """Taux et délai médian de réponse sur 30 jours, par gérant : {gerant: (taux en %, minutes)}."""
    depuis = timezone.now() - timezone.timedelta(days=30)
    par_gerant: dict = {}
    for c in Conversation.objects.filter(
        created_at__gte=depuis, last_message_at__isnull=False
    ).only("gerant_id", "created_at", "first_reply_at"):
        total, delais = par_gerant.setdefault(c.gerant_id, [0, []])
        par_gerant[c.gerant_id][0] += 1
        if c.first_reply_at is not None:
            delais.append((c.first_reply_at - c.created_at).total_seconds() / 60)
    sortie = {}
    for gerant_id, (total, delais) in par_gerant.items():
        # Vraie médiane : avec un nombre pair de délais, la moyenne des deux du milieu (pas le plus grand).
        mediane = round(statistics.median(delais)) if delais else None
        sortie[gerant_id] = (round(100 * len(delais) / total, 2), mediane)
    return sortie
