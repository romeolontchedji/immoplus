"""Annonces : création de brouillons, modification, publication et cycle de vie (CDC §9.8, §9.23, §11.1)."""

import uuid
from typing import TYPE_CHECKING

from django.db import connection, transaction
from django.utils import timezone
from django.utils.text import slugify

from apps.accounts.enums import Statut, StatutVerification
from apps.audit import services as audit
from apps.core.errors import ErreurMetier

from ..enums import Compteur, Eau, StatutAnnonce, StatutMedia, TypeChambre, TypeMedia
from ..models import District, Listing, ListingMedia
from . import contenu, geo

if TYPE_CHECKING:
    from apps.accounts.models import GerantProfile

CHAMPS_TEXTE_A_CONTROLER = ("title", "landmark_text", "address_private", "description_md")
CHAMPS_MODIFIABLES = (
    "title", "room_type", "district", "landmark_text", "address_private", "latitude", "longitude", "rent_amount",
    "deposit_months", "advance_months", "agent_fee_amount", "available_from", "has_private_bathroom", "is_fenced",
    "water_source", "electricity_meter", "description_md",
)  # fmt: skip
OBLIGATOIRES = (
    "title", "room_type", "district", "landmark_text", "latitude", "longitude", "rent_amount", "deposit_months",
    "advance_months", "available_from", "has_private_bathroom", "is_fenced", "water_source", "electricity_meter",
)  # fmt: skip
LIMITES_BENIN = {"latitude": (6.0, 12.6), "longitude": (0.7, 3.9)}


def _champ(nom: str, message: str) -> ErreurMetier:
    return ErreurMetier("validation_error", message, champs={nom: [message]})


def _valider(d: dict) -> None:
    """Contrôles de valeur sur les champs présents (la base garde en plus ses contraintes)."""
    if "title" in d and len((d["title"] or "").strip()) < 5:
        raise _champ("title", "Le titre doit faire au moins 5 caractères.")
    if "room_type" in d and d["room_type"] not in TypeChambre.values:
        raise _champ("room_type", "Type de logement inconnu.")
    if "water_source" in d and d["water_source"] not in Eau.values:
        raise _champ("water_source", "Source d'eau inconnue.")
    if "electricity_meter" in d and d["electricity_meter"] not in Compteur.values:
        raise _champ("electricity_meter", "Type de compteur inconnu.")
    if "rent_amount" in d and not (isinstance(d["rent_amount"], int) and d["rent_amount"] > 0):
        raise _champ("rent_amount", "Le loyer doit être un entier positif en FCFA.")
    for nom in ("deposit_months", "advance_months"):
        if nom in d and not (isinstance(d[nom], int) and 0 <= d[nom] <= 12):
            raise _champ(nom, "Entre 0 et 12 mois.")
    if "agent_fee_amount" in d and not (
        isinstance(d["agent_fee_amount"], int) and d["agent_fee_amount"] >= 0
    ):
        raise _champ("agent_fee_amount", "Les frais doivent être un entier positif ou nul.")
    for nom, (bas, haut) in LIMITES_BENIN.items():
        if nom in d and not (bas <= float(d[nom]) <= haut):
            raise _champ(nom, "Position hors du Bénin.")


def _quartier(identifiant) -> District:
    try:
        return District.objects.get(pk=identifiant, is_active=True)
    except (District.DoesNotExist, ValueError, TypeError, Exception) as erreur:
        raise _champ("district", "Quartier inconnu.") from erreur


def _gerant_actif(gerant: "GerantProfile") -> None:
    if not gerant.user.is_active or gerant.user.status != Statut.ACTIVE:
        raise ErreurMetier("account_suspended", "Ton compte est suspendu.", statut=403)


def _annonce_du_gerant(gerant: "GerantProfile", annonce_id, *, verrou: bool = False) -> Listing:
    requete = Listing.objects.select_for_update() if verrou else Listing.objects
    try:
        return requete.get(pk=annonce_id, gerant=gerant, deleted_at__isnull=True)
    except (Listing.DoesNotExist, ValueError, TypeError, Exception) as erreur:
        raise ErreurMetier("not_found", "Annonce introuvable.", statut=404) from erreur


def _vecteur_de_recherche(annonce: Listing) -> None:
    """Titre, description en texte brut et quartier, sans accents (CDC §9.8)."""
    texte = f"{annonce.title} {contenu.texte_brut(annonce.description_html)} {annonce.district.name} {annonce.landmark_text}"
    with connection.cursor() as c:
        c.execute(
            "UPDATE listings SET search_vector = to_tsvector('french', unaccent(%s)) WHERE id = %s",
            [texte, annonce.pk],
        )


def _slug(titre: str) -> str:
    return f"{slugify(titre)[:140] or 'annonce'}-{uuid.uuid4().hex[:6]}"


def _appliquer(annonce: Listing, donnees: dict) -> None:
    for nom in CHAMPS_MODIFIABLES:
        if nom in donnees:
            valeur = donnees[nom]
            if nom == "district":
                annonce.district = _quartier(valeur)
            elif nom == "description_md":
                annonce.description_md, annonce.description_html = contenu.rendre(valeur)
            elif nom in ("title", "landmark_text", "address_private"):
                setattr(annonce, nom, " ".join(str(valeur or "").split()))
            else:
                setattr(annonce, nom, valeur)
    if "latitude" in donnees or "longitude" in donnees:
        annonce.distance_to_campus_m = geo.distance_au_campus(annonce.latitude, annonce.longitude)


@transaction.atomic
def creer_brouillon(gerant: "GerantProfile", donnees: dict) -> Listing:
    _gerant_actif(gerant)
    manquants = [n for n in OBLIGATOIRES if donnees.get(n) in (None, "")]
    if manquants:
        raise ErreurMetier(
            "validation_error", "Des champs obligatoires sont manquants.",
            champs={n: ["Obligatoire"] for n in manquants},
        )  # fmt: skip
    _valider(donnees)
    contenu.refuser_si_coordonnees(
        **{n: str(donnees.get(n) or "") for n in CHAMPS_TEXTE_A_CONTROLER}
    )
    annonce = Listing(
        gerant=gerant,
        slug=_slug(donnees["title"]),
        agent_fee_amount=donnees.get("agent_fee_amount", 0),
    )
    _appliquer(annonce, donnees)
    annonce.save()
    _vecteur_de_recherche(annonce)
    audit.enregistrer("listing.cree", acteur=gerant.user, cible=annonce)
    return annonce


@transaction.atomic
def modifier(gerant: "GerantProfile", annonce_id, donnees: dict) -> Listing:
    _gerant_actif(gerant)
    annonce = _annonce_du_gerant(gerant, annonce_id, verrou=True)
    if annonce.status in (StatutAnnonce.ARCHIVED, StatutAnnonce.REMOVED):
        raise ErreurMetier(
            "listing_locked", "Cette annonce ne peut plus être modifiée.", statut=409
        )
    donnees = {k: v for k, v in donnees.items() if k in CHAMPS_MODIFIABLES}
    _valider(donnees)
    contenu.refuser_si_coordonnees(
        **{n: str(donnees[n] or "") for n in CHAMPS_TEXTE_A_CONTROLER if n in donnees}
    )
    loyer_avant = annonce.rent_amount
    _appliquer(annonce, donnees)
    annonce.save()
    _vecteur_de_recherche(annonce)
    audit.enregistrer(
        "listing.modifiee", acteur=gerant.user, cible=annonce,
        metadata={"champs": sorted(donnees), "loyer_avant": loyer_avant, "loyer_apres": annonce.rent_amount},
    )  # fmt: skip
    return annonce


@transaction.atomic
def supprimer_brouillon(gerant: "GerantProfile", annonce_id) -> None:
    annonce = _annonce_du_gerant(gerant, annonce_id, verrou=True)
    if annonce.status != StatutAnnonce.DRAFT:
        raise ErreurMetier("listing_locked", "Seul un brouillon peut être supprimé.", statut=409)
    annonce.deleted_at = timezone.now()
    annonce.save(update_fields=["deleted_at", "updated_at"])
    audit.enregistrer("listing.supprimee", acteur=gerant.user, cible=annonce)


# --------------------------------------------------------------- cycle de vie
def changer_statut(annonce: Listing, nouveau: str, *, acteur, raison: str | None = None) -> None:
    """Un seul point d'entrée pour changer de statut : écrit `listing.status_changed` dans le journal."""
    ancien = annonce.status
    annonce.status = nouveau
    annonce.hidden_reason = raison if nouveau == StatutAnnonce.HIDDEN else None
    annonce.save(
        update_fields=[
            "status",
            "hidden_reason",
            "published_at",
            "rented_at",
            "last_confirmed_at",
            "reminder_stage",
            "updated_at",
        ]
    )
    audit.enregistrer(
        "listing.status_changed", acteur=acteur, cible=annonce,
        metadata={"ancien": ancien, "nouveau": nouveau, "loyer": annonce.rent_amount, "raison": raison},
    )  # fmt: skip


def manques_a_la_publication(annonce: Listing) -> list[str]:
    """Liste lisible de ce qui empêche la publication (§9.23)."""
    manques = []
    gerant = annonce.gerant
    if gerant.verification_status != StatutVerification.VERIFIED:
        manques.append("gerant_non_verifie")
    if not gerant.user.is_active:
        manques.append("gerant_suspendu")
    for nom in OBLIGATOIRES:
        valeur = getattr(annonce, f"{nom}_id" if nom == "district" else nom, None)
        if valeur in (None, ""):
            manques.append(f"champ:{nom}")
    media = ListingMedia.objects.filter(listing=annonce, status=StatutMedia.READY)
    if not media.filter(kind=TypeMedia.VIDEO).exists():
        manques.append("video_prete")
    if media.filter(kind=TypeMedia.PHOTO).count() < 3:
        manques.append("trois_photos_pretes")
    return manques


@transaction.atomic
def publier(gerant: "GerantProfile", annonce_id) -> Listing:
    """Publie si toutes les conditions sont réunies ; sinon 409 `listing_not_publishable` avec les manques."""
    _gerant_actif(gerant)
    annonce = _annonce_du_gerant(gerant, annonce_id, verrou=True)
    if annonce.status not in (StatutAnnonce.DRAFT, StatutAnnonce.PROCESSING, StatutAnnonce.HIDDEN):
        raise ErreurMetier(
            "listing_locked",
            "Cette annonce ne peut pas être publiée dans son état actuel.",
            statut=409,
        )
    manques = manques_a_la_publication(annonce)
    en_traitement = ListingMedia.objects.filter(
        listing=annonce, status__in=[StatutMedia.UPLOADED, StatutMedia.PROCESSING]
    ).exists()
    if manques and not (en_traitement and set(manques) <= {"video_prete", "trois_photos_pretes"}):
        raise ErreurMetier(
            "listing_not_publishable", "L'annonce n'est pas encore publiable.", statut=409,
            champs={"manques": manques},
        )  # fmt: skip
    if manques:  # médias encore en traitement : l'annonce attend, invisible du public
        changer_statut(annonce, StatutAnnonce.PROCESSING, acteur=gerant.user)
        return annonce
    premiere = not Listing.objects.filter(gerant=gerant, published_at__isnull=False).exists()
    if premiere:  # première annonce : la vidéo est relue par la modération avant la mise en ligne
        changer_statut(annonce, StatutAnnonce.PROCESSING, acteur=gerant.user)
        return annonce
    mettre_en_ligne(annonce, acteur=gerant.user)
    return annonce


def mettre_en_ligne(annonce: Listing, *, acteur) -> None:
    maintenant = timezone.now()
    annonce.published_at = annonce.published_at or maintenant
    annonce.last_confirmed_at = maintenant
    annonce.reminder_stage = 0
    changer_statut(annonce, StatutAnnonce.PUBLISHED, acteur=acteur)


@transaction.atomic
def confirmer(gerant: "GerantProfile", annonce_id) -> Listing:
    """Confirme la disponibilité : fraîcheur réinitialisée ; une annonce masquée pour péremption est remise en ligne."""
    annonce = _annonce_du_gerant(gerant, annonce_id, verrou=True)
    if annonce.status not in (StatutAnnonce.PUBLISHED, StatutAnnonce.HIDDEN):
        raise ErreurMetier("listing_locked", "Rien à confirmer pour cette annonce.", statut=409)
    if annonce.status == StatutAnnonce.HIDDEN:
        if annonce.hidden_reason not in ("stale", "owner"):
            raise ErreurMetier(
                "listing_locked", "Cette annonce est masquée par la modération.", statut=409
            )
        manques = manques_a_la_publication(annonce)
        if manques:
            raise ErreurMetier(
                "listing_not_publishable",
                "L'annonce n'est pas publiable.",
                statut=409,
                champs={"manques": manques},
            )
        mettre_en_ligne(annonce, acteur=gerant.user)
    else:
        annonce.last_confirmed_at, annonce.reminder_stage = timezone.now(), 0
        annonce.save(update_fields=["last_confirmed_at", "reminder_stage", "updated_at"])
        audit.enregistrer("listing.confirmee", acteur=gerant.user, cible=annonce)
    return annonce


@transaction.atomic
def masquer(gerant: "GerantProfile", annonce_id) -> Listing:
    annonce = _annonce_du_gerant(gerant, annonce_id, verrou=True)
    if annonce.status != StatutAnnonce.PUBLISHED:
        raise ErreurMetier(
            "listing_locked", "Seule une annonce publiée peut être masquée.", statut=409
        )
    changer_statut(annonce, StatutAnnonce.HIDDEN, acteur=gerant.user, raison="owner")
    return annonce


@transaction.atomic
def marquer_louee(gerant: "GerantProfile", annonce_id) -> Listing:
    annonce = _annonce_du_gerant(gerant, annonce_id, verrou=True)
    if annonce.status != StatutAnnonce.PUBLISHED:
        raise ErreurMetier(
            "listing_locked", "Seule une annonce publiée peut être marquée louée.", statut=409
        )
    annonce.rented_at = timezone.now()
    ListingMedia.objects.filter(listing=annonce, kind=TypeMedia.VIDEO).exclude(
        status__in=[StatutMedia.DELETED, StatutMedia.FAILED]
    ).update(delete_after=annonce.rented_at + timezone.timedelta(days=7))  # vidéo supprimée à J+7
    changer_statut(annonce, StatutAnnonce.RENTED, acteur=gerant.user)
    return annonce


@transaction.atomic
def annuler_louee(gerant: "GerantProfile", annonce_id) -> Listing:
    annonce = _annonce_du_gerant(gerant, annonce_id, verrou=True)
    if annonce.status != StatutAnnonce.RENTED:
        raise ErreurMetier("listing_locked", "Cette annonce n'est pas marquée louée.", statut=409)
    video_encore_la = ListingMedia.objects.filter(
        listing=annonce, kind=TypeMedia.VIDEO, status=StatutMedia.READY, deleted_at__isnull=True
    ).exists()
    if not video_encore_la:  # vidéo supprimée : il faut en envoyer une nouvelle
        annonce.rented_at = None
        changer_statut(annonce, StatutAnnonce.DRAFT, acteur=gerant.user)
        return annonce
    ListingMedia.objects.filter(listing=annonce, kind=TypeMedia.VIDEO).update(delete_after=None)
    annonce.rented_at = None
    mettre_en_ligne(annonce, acteur=gerant.user)
    return annonce
