"""Types de logement (décision V1) : officiels, proposés par les gérants, validés ou rattachés par la modération.

- Un gérant utilise tout type validé, et ses propres propositions en attente (visibles tout de suite pour lui).
- Les filtres, les alertes et la liste publique ne montrent que les types validés.
- Rattacher une proposition à un type existant réécrit les annonces et les alertes qui la portent, puis la supprime :
  il n'y a pas de refus sec, une annonce garde toujours un type.
"""

import re
import unicodedata

from django.core.cache import cache
from django.db import IntegrityError, connection, transaction
from django.db.models import Count, Q
from django.utils import timezone
from django.utils.text import slugify

from apps.audit import services as audit
from apps.core.errors import ErreurMetier

from ..enums import StatutAnnonce, StatutTypeChambre
from ..models import Listing, RoomType
from . import contenu

PROPOSITIONS_EN_ATTENTE_MAX = 3
_CLE_LIBELLES = "listings:types:libelles"


def _champ(message: str) -> ErreurMetier:
    return ErreurMetier("validation_error", message, champs={"room_type": [message]})


def _cle_comparaison(texte: str) -> str:
    """« Entrée-coucher », « entree coucher » et « ENTRÉE COUCHER » sont le même type."""
    sans_accents = unicodedata.normalize("NFKD", texte).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "", sans_accents.lower())


def vider_cache() -> None:
    cache.delete(_CLE_LIBELLES)


# --------------------------------------------------------------------------- lecture
def libelles() -> dict[str, str]:
    """slug → libellé, pour tous les types (y compris en attente : une annonce publiée peut en porter un)."""
    valeur = cache.get(_CLE_LIBELLES)
    if valeur is None:
        valeur = dict(RoomType.objects.values_list("slug", "label"))
        cache.set(_CLE_LIBELLES, valeur, 60)
    return valeur


def libelle(slug: str | None) -> str | None:
    if not slug:
        return None
    return libelles().get(slug, slug)


def slugs_valides() -> list[str]:
    return list(
        RoomType.objects.filter(status=StatutTypeChambre.APPROVED).values_list("slug", flat=True)
    )


def publics() -> list[dict]:
    """Types validés, les plus utilisés d'abord (nombre d'annonces publiées), puis l'ordre officiel."""
    requete = RoomType.objects.filter(status=StatutTypeChambre.APPROVED)
    comptes = dict(
        Listing.objects.filter(status=StatutAnnonce.PUBLISHED, deleted_at__isnull=True)
        .values_list("room_type")
        .annotate(n=Count("id"))
        .values_list("room_type", "n")
    )
    types = [
        {"slug": t.slug, "label": t.label, "count": comptes.get(t.slug, 0), "ordre": t.sort_order}
        for t in requete
    ]
    types.sort(key=lambda t: (-t["count"], t["ordre"], t["label"]))
    return [{k: v for k, v in t.items() if k != "ordre"} for t in types]


def pour_gerant(gerant) -> list[dict]:
    """Types proposés au gérant : validés, puis les propositions en attente qu'il a faites ou qu'il utilise déjà."""
    siens = Listing.objects.filter(gerant_id=gerant.pk, deleted_at__isnull=True).values("room_type")
    requete = RoomType.objects.filter(
        Q(status=StatutTypeChambre.APPROVED)
        | Q(status=StatutTypeChambre.PENDING, proposed_by_id=gerant.pk)
        | Q(status=StatutTypeChambre.PENDING, slug__in=siens)
    ).order_by("sort_order", "label")
    return [{"slug": t.slug, "label": t.label, "status": t.status} for t in requete]


def verifier_pour_annonce(slug) -> None:
    """Une annonce peut porter tout type existant : validé, ou proposé (le sien, ou le même proposé par un autre)."""
    if not slug or not RoomType.objects.filter(slug=slug).exists():
        raise _champ("Type de logement inconnu.")


def verifier_valides(slugs) -> list[str]:
    """Pour les filtres et les alertes : seulement des types validés."""
    slugs = [str(s) for s in slugs or []]
    if set(slugs) - set(slugs_valides()):
        raise ErreurMetier(
            "validation_error", "Type inconnu.", champs={"room_types": ["Type inconnu"]}
        )
    return slugs


# --------------------------------------------------------------------------- proposition (gérant)
def proposer(gerant, libelle_saisi: str) -> RoomType:
    """Propose un type ; renvoie le type équivalent s'il existe déjà (validé, ou proposé par n'importe qui)."""
    texte = " ".join(str(libelle_saisi or "").split())
    if not 3 <= len(texte) <= 40:
        raise _champ("Le nom du type fait entre 3 et 40 caractères.")
    contenu.refuser_si_coordonnees(room_type=texte)
    cle = _cle_comparaison(texte)
    for existant in RoomType.objects.all():
        if _cle_comparaison(existant.label) == cle or existant.slug.replace("_", "") == cle:
            # Même s'il est proposé par un autre gérant et pas encore validé : partagé plutôt que dupliqué.
            return existant
    en_attente = RoomType.objects.filter(
        proposed_by_id=gerant.pk, status=StatutTypeChambre.PENDING
    ).count()
    if en_attente >= PROPOSITIONS_EN_ATTENTE_MAX:
        raise _champ(
            f"Tu as déjà {PROPOSITIONS_EN_ATTENTE_MAX} types en attente de validation : attends la réponse de l'équipe."
        )
    slug = slugify(texte).replace("-", "_")[:40].strip("_") or "type"
    texte = texte[0].upper() + texte[1:]
    try:
        with transaction.atomic():
            nouveau = RoomType.objects.create(slug=slug, label=texte, proposed_by_id=gerant.pk)
    except IntegrityError:  # slug déjà pris par un libellé différent : suffixe court
        nouveau = RoomType.objects.create(
            slug=f"{slug[:34]}_{timezone.now():%H%M%S}", label=texte, proposed_by_id=gerant.pk
        )
    vider_cache()
    audit.enregistrer(
        "room_type.propose", acteur=gerant.user, metadata={"slug": nouveau.slug, "label": texte}
    )
    return nouveau


# --------------------------------------------------------------------------- modération
@transaction.atomic
def valider(type_chambre: RoomType, *, acteur) -> RoomType:
    type_chambre.status = StatutTypeChambre.APPROVED
    type_chambre.reviewed_by = acteur
    type_chambre.reviewed_at = timezone.now()
    type_chambre.save(update_fields=["status", "reviewed_by", "reviewed_at"])
    vider_cache()
    audit.enregistrer(
        "room_type.valide",
        acteur=acteur,
        metadata={"slug": type_chambre.slug, "label": type_chambre.label},
    )
    return type_chambre


@transaction.atomic
def rattacher(type_chambre: RoomType, cible: RoomType, *, acteur) -> int:
    """Fusionne une proposition dans un type validé : annonces et alertes réécrites, proposition supprimée."""
    if cible.status != StatutTypeChambre.APPROVED:
        raise ErreurMetier("validation_error", "Le type de destination doit être validé.")
    if type_chambre.pk == cible.pk:
        raise ErreurMetier("validation_error", "Choisis un autre type de destination.")
    if type_chambre.status == StatutTypeChambre.APPROVED and type_chambre.proposed_by_id is None:
        raise ErreurMetier("validation_error", "Un type officiel ne se rattache pas à un autre.")
    annonces = Listing.objects.filter(room_type=type_chambre.slug).update(room_type=cible.slug)
    with connection.cursor() as c:  # remplace le slug dans les tableaux des alertes, sans doublon
        c.execute(
            "UPDATE alerts SET room_types = ARRAY(SELECT DISTINCT unnest(array_replace(room_types, %s, %s)))"
            " WHERE %s = ANY(room_types)",
            [type_chambre.slug, cible.slug, type_chambre.slug],
        )
    audit.enregistrer(
        "room_type.rattache",
        acteur=acteur,
        metadata={"de": type_chambre.slug, "vers": cible.slug, "annonces": annonces},
    )
    type_chambre.delete()
    vider_cache()
    return annonces
