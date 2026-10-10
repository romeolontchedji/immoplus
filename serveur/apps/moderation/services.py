"""Signalements, file de modération, sanctions et lecture journalisée (CDC §7.9, §9.16, §9.17, §11.7).

Chaque décision est écrite dans `moderation_actions` et dans `audit_logs`, avec un motif obligatoire ; la personne
concernée est notifiée (catégorie « account.sanction », qu'elle ne peut pas désactiver).
"""

import logging
import uuid
from datetime import timedelta

from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.accounts import selectors as comptes
from apps.accounts.enums import Role, Statut
from apps.accounts.services import administration as comptes_admin
from apps.audit import services as audit
from apps.chat import selectors as chat_selectors
from apps.chat import services as chat_services
from apps.core import parametres, stats
from apps.core.errors import ErreurMetier
from apps.listings import selectors as annonces
from apps.listings.services import annonces as annonces_services
from apps.notifications import services as notifications

from .enums import ETATS_OUVERTS, MOTIFS
from .models import ModerationAction, Report

journal = logging.getLogger(__name__)
SIGNALEMENTS_PAR_JOUR = 20
MOTIF_MIN = 10


def _uuid(valeur):
    try:
        return uuid.UUID(str(valeur))
    except ValueError:
        return None


# --------------------------------------------------------------- signalements
def _verifier_cible(utilisateur, cible_type: str, cible_id):
    """Vérifie que la cible existe et que le signalant peut la voir ; retourne l'annonce concernée (ou None)."""
    if cible_type == "listing":
        fiche = annonces.fiche_publique(cible_id)
        if fiche is None:
            raise ErreurMetier("not_found", "Annonce introuvable.", statut=404)
        if fiche["gerant_user_id"] == utilisateur.pk:
            raise ErreurMetier(
                "forbidden", "Tu ne peux pas signaler ta propre annonce.", statut=403
            )
        return fiche["id"]
    if cible_type == "conversation":
        c = chat_selectors.conversation_du_participant(utilisateur.pk, cible_id)
        return c.listing_id
    if cible_type == "message":
        m = chat_selectors.message_par_id(cible_id)
        if m is None:
            raise ErreurMetier("not_found", "Message introuvable.", statut=404)
        c = chat_selectors.conversation_du_participant(utilisateur.pk, m.conversation_id)
        if m.sender_id == utilisateur.pk:
            raise ErreurMetier(
                "forbidden", "Tu ne peux pas signaler ton propre message.", statut=403
            )
        return c.listing_id
    if cible_type == "user":
        if str(cible_id) == str(utilisateur.pk):
            raise ErreurMetier("forbidden", "Tu ne peux pas te signaler toi-même.", statut=403)
        if not comptes.noms_utilisateurs([cible_id]):
            raise ErreurMetier("not_found", "Utilisateur introuvable.", statut=404)
        return None
    raise ErreurMetier(
        "validation_error", "Type de cible inconnu.", champs={"target_type": ["Valeur inconnue"]}
    )


def signaler(
    utilisateur, cible_type: str, cible_id, motif: str, details: str = ""
) -> tuple[Report, bool]:
    """Signalement par un utilisateur. Idempotent : un signalement ouvert par auteur et par cible (CDC §9.16)."""
    if motif not in MOTIFS:
        raise ErreurMetier(
            "validation_error", "Motif inconnu.", champs={"reason_code": ["Valeur inconnue"]}
        )
    identifiant = _uuid(cible_id)
    if identifiant is None:
        raise ErreurMetier(
            "validation_error", "Identifiant invalide.", champs={"target_id": ["UUID attendu"]}
        )
    debut = timezone.localtime().replace(hour=0, minute=0, second=0, microsecond=0)
    if (
        Report.objects.filter(reporter=utilisateur, created_at__gte=debut).count()
        >= SIGNALEMENTS_PAR_JOUR
    ):
        raise ErreurMetier("rate_limited", "Trop de signalements aujourd'hui.", statut=429)
    annonce_id = _verifier_cible(utilisateur, cible_type, identifiant)
    existant = Report.objects.filter(
        reporter=utilisateur,
        target_type=cible_type,
        target_id=identifiant,
        status__in=ETATS_OUVERTS,
    ).first()
    if existant is not None:
        return existant, False
    try:
        with transaction.atomic():
            rapport = Report.objects.create(
                reporter=utilisateur, target_type=cible_type, target_id=identifiant, listing_id=annonce_id,
                reason_code=motif, details=" ".join(details.split())[:500],
            )  # fmt: skip
    except IntegrityError:
        return Report.objects.get(
            reporter=utilisateur,
            target_type=cible_type,
            target_id=identifiant,
            status__in=ETATS_OUVERTS,
        ), False
    stats.incrementer("reports_created")
    return rapport, True


def signaler_automatiquement(
    cible_type, cible_id, motif, details="", *, annonce_id=None
) -> Report | None:
    """Signalement du système (détection de coordonnées…) : un seul dossier ouvert par cible et par motif."""
    try:
        with transaction.atomic():
            rapport = Report.objects.create(
                source="system", target_type=cible_type, target_id=cible_id, listing_id=annonce_id,
                reason_code=motif, details=details[:500],
            )  # fmt: skip
    except IntegrityError:
        return None
    stats.incrementer("contact_detected" if motif == "contact_leak" else "reports_created")
    return rapport


def signaler_deja_louee(utilisateur, annonce_id) -> tuple[Report, bool]:
    """« Déjà louée » : trois signalements distincts préviennent le gérant, une seule fois (EF-ANN-14)."""
    rapport, cree = signaler(utilisateur, "listing", annonce_id, "already_rented")
    seuil = int(parametres.lire("RENTED_REPORTS_THRESHOLD"))
    auteurs = (
        Report.objects.filter(
            target_type="listing",
            target_id=rapport.target_id,
            reason_code="already_rented",
            status__in=ETATS_OUVERTS,
        )
        .exclude(reporter__isnull=True)
        .values("reporter")
        .distinct()
        .count()
    )
    if cree and auteurs >= seuil:
        fiche = annonces.fiche_publique(rapport.target_id)
        if fiche:
            notifications.creer(
                fiche["gerant_user_id"],
                "listing.reported_rented",
                "Cette chambre est-elle encore disponible ?",
                f"Plusieurs personnes disent que « {fiche['title']} » est déjà louée. Confirme ou marque-la louée.",
                data={"listing_id": str(fiche["id"]), "slug": fiche["slug"]},
                dedupe_key=f"reported-rented:{fiche['id']}:{seuil}",
            )
    return rapport, cree


# --------------------------------------------------------------- file de modération
def _exiger_personnel(acteur) -> None:
    if getattr(acteur, "role", None) not in (Role.MODERATOR, Role.ADMIN):
        raise ErreurMetier("forbidden", "Réservé à la modération.", statut=403)


def _motif(motif: str) -> str:
    motif = " ".join((motif or "").split())
    if len(motif) < MOTIF_MIN:
        raise ErreurMetier(
            "validation_error",
            f"Motif obligatoire ({MOTIF_MIN} caractères au moins).",
            champs={"reason": ["Trop court"]},
        )
    return motif


def prendre_en_charge(acteur, rapport: Report) -> Report:
    _exiger_personnel(acteur)
    if rapport.status not in ETATS_OUVERTS:
        raise ErreurMetier("report_closed", "Ce dossier est déjà clos.", statut=409)
    rapport.status, rapport.assigned_to = "in_review", acteur
    rapport.save(update_fields=["status", "assigned_to"])
    audit.enregistrer("signalement.pris", acteur=acteur, cible=rapport)
    return rapport


def classer_sans_suite(acteur, rapport: Report, note: str) -> Report:
    _exiger_personnel(acteur)
    if rapport.status not in ETATS_OUVERTS:
        raise ErreurMetier("report_closed", "Ce dossier est déjà clos.", statut=409)
    note = _motif(note)
    rapport.status, rapport.resolved_by, rapport.resolved_at = (
        "resolved_dismissed",
        acteur,
        timezone.now(),
    )
    rapport.resolution_note = note[:500]
    rapport.save(update_fields=["status", "resolved_by", "resolved_at", "resolution_note"])
    audit.enregistrer(
        "signalement.classe",
        acteur=acteur,
        cible=rapport,
        metadata={"note": rapport.resolution_note},
    )
    return rapport


# --------------------------------------------------------------- actions
def appliquer(
    acteur, action: str, *, motif: str, rapport: Report | None = None, utilisateur=None,
    annonce_id=None, message_id=None, jusqua=None,
) -> ModerationAction:  # fmt: skip
    """Applique une décision : motif obligatoire, droits par rôle, effet, notification, journal."""
    _exiger_personnel(acteur)
    motif = _motif(motif)
    if action in ("ban",) and acteur.role != Role.ADMIN:
        raise ErreurMetier("forbidden", "Seul un administrateur bannit.", statut=403)
    cible_utilisateur, cible_annonce = utilisateur, None
    with transaction.atomic():
        if action in ("message_masked", "message_deleted"):
            message = chat_selectors.message_par_id(message_id)
            if message is None:
                raise ErreurMetier("not_found", "Message introuvable.", statut=404)
            chat_services.moderer_message(
                message.pk, "masked" if action == "message_masked" else "deleted"
            )
            cible_utilisateur = _utilisateur(message.sender_id) if message.sender_id else None
        elif action in ("listing_hidden", "listing_removed"):
            cible_annonce = annonces_services_annonce(annonce_id)
            if action == "listing_hidden":
                annonces_services.changer_statut(
                    cible_annonce, "hidden", acteur=acteur, raison="moderation"
                )
            else:
                annonces_services.changer_statut(cible_annonce, "removed", acteur=acteur)
            cible_utilisateur = _utilisateur(cible_annonce.gerant_id)
        elif action == "warning":
            _exiger_utilisateur(cible_utilisateur)
        elif action == "suspension":
            _exiger_utilisateur(cible_utilisateur)
            jusqua = _fin_de_suspension(acteur, jusqua)
            comptes_admin.changer_statut(
                acteur=acteur,
                cible=cible_utilisateur,
                statut=Statut.SUSPENDED,
                jusqu_a=jusqua,
                motif=motif,
            )
        elif action == "ban":
            _exiger_utilisateur(cible_utilisateur)
            comptes_admin.changer_statut(
                acteur=acteur, cible=cible_utilisateur, statut=Statut.BANNED, motif=motif
            )
        elif action == "reinstatement":
            _exiger_utilisateur(cible_utilisateur)
            comptes_admin.changer_statut(
                acteur=acteur, cible=cible_utilisateur, statut=Statut.ACTIVE, motif=motif
            )
            ModerationAction.objects.filter(
                target_user=cible_utilisateur,
                action__in=["suspension", "ban"],
                revoked_at__isnull=True,
            ).update(revoked_at=timezone.now(), revoked_by=acteur)
        else:
            raise ErreurMetier(
                "validation_error", "Action inconnue.", champs={"action": ["Valeur inconnue"]}
            )
        decision = ModerationAction.objects.create(
            actor=acteur, report=rapport, action=action, target_user=cible_utilisateur,
            target_listing=cible_annonce, target_message_id=message_id if action.startswith("message") else None,
            ends_at=jusqua if action == "suspension" else None, reason=motif,
        )  # fmt: skip
        audit.enregistrer(
            f"moderation.{action}", acteur=acteur, cible=decision,
            metadata={"motif": motif[:200], "rapport": str(rapport.pk) if rapport else None,
                      "utilisateur": str(cible_utilisateur.pk) if cible_utilisateur else None},
        )  # fmt: skip
        if rapport is not None and rapport.status in ETATS_OUVERTS:
            rapport.status, rapport.resolved_by, rapport.resolved_at = (
                "resolved_actioned",
                acteur,
                timezone.now(),
            )
            rapport.resolution_note = motif[:500]
            rapport.save(update_fields=["status", "resolved_by", "resolved_at", "resolution_note"])
        _notifier(decision, cible_utilisateur, motif)
    return decision


def _utilisateur(identifiant):
    return comptes.utilisateur_ou_none(identifiant)


def _exiger_utilisateur(utilisateur) -> None:
    if utilisateur is None:
        raise ErreurMetier(
            "validation_error",
            "Cette action vise un utilisateur.",
            champs={"target_user": ["Obligatoire"]},
        )


def annonces_services_annonce(annonce_id):
    annonce = annonces.annonce_par_id(annonce_id)
    if annonce is None:
        raise ErreurMetier("not_found", "Annonce introuvable.", statut=404)
    return annonce


def _fin_de_suspension(acteur, jusqua):
    maintenant = timezone.now()
    if jusqua is None or jusqua <= maintenant:
        raise ErreurMetier(
            "validation_error",
            "Date de fin de suspension obligatoire et future.",
            champs={"ends_at": ["Date future requise"]},
        )
    plafond = maintenant + timedelta(days=int(parametres.lire("MODERATOR_MAX_SUSPENSION_DAYS")))
    if acteur.role != Role.ADMIN and jusqua > plafond:
        raise ErreurMetier(
            "forbidden",
            f"Un modérateur suspend {parametres.lire('MODERATOR_MAX_SUSPENSION_DAYS')} jours au plus.",
            statut=403,
        )
    return jusqua


_TITRES = {
    "message_masked": "Un de tes messages a été masqué",
    "message_deleted": "Un de tes messages a été supprimé",
    "listing_hidden": "Ton annonce a été masquée",
    "listing_removed": "Ton annonce a été retirée",
    "warning": "Avertissement de la modération",
    "suspension": "Ton compte est suspendu",
    "ban": "Ton compte est banni",
    "reinstatement": "Ton compte est rétabli",
}


def _notifier(decision: ModerationAction, utilisateur, motif: str) -> None:
    if utilisateur is None:
        return
    notifications.creer(
        utilisateur.pk, "account.sanction", _TITRES[decision.action], motif,
        data={"action": decision.action, "decision_id": str(decision.pk)},
        dedupe_key=f"sanction:{decision.pk}",
    )  # fmt: skip


# --------------------------------------------------------------- fin de suspension (tâche horaire)
def expirer_sanctions() -> int:
    """Suspensions échues : compte réactivé, annonces remises en ligne si encore valides, sanction levée."""
    levees = 0
    for utilisateur in comptes.suspensions_echues():
        if comptes_admin.lever_suspension_echue(utilisateur):
            ModerationAction.objects.filter(
                target_user=utilisateur, action="suspension", revoked_at__isnull=True
            ).update(revoked_at=timezone.now())
            notifications.creer(
                utilisateur.pk, "account.sanction", "Ta suspension est terminée", "Tu peux de nouveau publier et écrire.",
                data={"action": "reinstatement"}, dedupe_key=f"suspension-levee:{utilisateur.pk}:{int(timezone.now().timestamp() // 60)}",
            )  # fmt: skip
            levees += 1
    return levees


# --------------------------------------------------------------- lecture journalisée (EF-MOD-03)
def lire_conversation(acteur, conversation_id, motif: str) -> dict:
    """Ouverture d'une conversation par le personnel : motif saisi avant lecture, journalisée, plafonnée par jour."""
    _exiger_personnel(acteur)
    motif = _motif(motif)
    conversation = chat_selectors.conversation_par_id(conversation_id)
    if conversation is None:
        raise ErreurMetier("not_found", "Conversation introuvable.", statut=404)
    audit.enregistrer(
        "conversation.lue_par_personnel", acteur=acteur, cible=conversation,
        metadata={"motif": motif[:200], "listing": str(conversation.listing_id)},
    )  # fmt: skip
    lues_aujourdhui = _lectures_du_jour(acteur)
    if lues_aujourdhui > int(parametres.lire("STAFF_READS_ALERT_THRESHOLD")):
        audit.enregistrer(
            "conversation.lectures_excessives",
            acteur=acteur,
            metadata={"lectures": lues_aujourdhui},
        )
    lignes, _ = chat_selectors.messages(conversation, limite=500)
    return {
        "conversation": conversation,
        "messages": [chat_services.message_pour(m, acteur.pk, personnel=True) for m in lignes],
    }


def _lectures_du_jour(acteur) -> int:
    debut = timezone.localtime().replace(hour=0, minute=0, second=0, microsecond=0)
    return audit.compter_depuis(acteur, "conversation.lue_par_personnel", debut)


# --------------------------------------------------------------- tableau de modération (EF-MOD-07)
def tableau() -> dict:
    """Volume de dossiers et délai médian de traitement (heures) sur 30 jours."""
    from django.db.models import Count

    depuis = timezone.now() - timedelta(days=30)
    par_statut = dict(
        Report.objects.values_list("status").annotate(n=Count("id")).values_list("status", "n")
    )
    durees = sorted(
        (r.resolved_at - r.created_at).total_seconds() / 3600
        for r in Report.objects.filter(resolved_at__isnull=False, resolved_at__gte=depuis)
    )
    mediane = durees[len(durees) // 2] if durees else None
    ouverts = Report.objects.filter(status__in=ETATS_OUVERTS)
    return {
        "par_statut": par_statut,
        "ouverts": ouverts.count(),
        "hors_delai": ouverts.filter(created_at__lt=timezone.now() - timedelta(hours=24)).count(),
        "delai_median_h": round(mediane, 1) if mediane is not None else None,
    }
