"""Alertes des locataires (CDC §7.5) : gestion et correspondance à la publication."""

import uuid

from apps.core import parametres
from apps.core.errors import ErreurMetier
from apps.notifications import services as notifications
from apps.notifications import textes

from .. import selectors
from ..models import Alert, District, Listing
from . import types as types_chambre

CHAMPS = (
    "label",
    "district_ids",
    "room_types",
    "max_rent",
    "private_bathroom_required",
    "max_distance_m",
    "is_active",
)


def _valider(d: dict) -> dict:
    propre = {}
    if "label" in d:
        propre["label"] = " ".join(str(d["label"] or "").split())[:80]
    if "district_ids" in d:
        ids = [uuid.UUID(str(i)) for i in d["district_ids"] or []][:30]
        connus = set(
            District.objects.filter(pk__in=ids, is_active=True).values_list("pk", flat=True)
        )
        if set(ids) - connus:
            raise ErreurMetier(
                "validation_error",
                "Quartier inconnu.",
                champs={"district_ids": ["Quartier inconnu"]},
            )
        propre["district_ids"] = ids
    if "room_types" in d:
        propre["room_types"] = types_chambre.verifier_valides(d["room_types"])
    for nom in ("max_rent", "max_distance_m"):
        if nom in d:
            valeur = d[nom]
            if valeur is not None and (not isinstance(valeur, int) or valeur <= 0):
                raise ErreurMetier(
                    "validation_error",
                    "Entier positif attendu.",
                    champs={nom: ["Entier positif attendu"]},
                )
            propre[nom] = valeur
    if "private_bathroom_required" in d:
        propre["private_bathroom_required"] = bool(d["private_bathroom_required"])
    if "is_active" in d:
        propre["is_active"] = bool(d["is_active"])
    return propre


def _verifier_plafond(utilisateur, ignorer=None) -> None:
    actives = Alert.objects.filter(user=utilisateur, is_active=True)
    if ignorer is not None:
        actives = actives.exclude(pk=ignorer)
    if actives.count() >= int(parametres.lire("ALERTS_MAX_PER_USER")):
        raise ErreurMetier(
            "alerts_limit",
            f"Tu as déjà {parametres.lire('ALERTS_MAX_PER_USER')} alertes actives.",
            statut=409,
        )


def creer(utilisateur, donnees: dict) -> Alert:
    _verifier_plafond(utilisateur)
    return Alert.objects.create(user=utilisateur, **_valider(donnees))


def _trouver(utilisateur, alerte_id) -> Alert:
    alerte = (
        Alert.objects.filter(pk=alerte_id, user=utilisateur).first()
        if _uuid_ok(alerte_id)
        else None
    )
    if alerte is None:
        raise ErreurMetier("not_found", "Alerte introuvable.", statut=404)
    return alerte


def _uuid_ok(valeur) -> bool:
    try:
        uuid.UUID(str(valeur))
        return True
    except ValueError:
        return False


def modifier(utilisateur, alerte_id, donnees: dict) -> Alert:
    alerte = _trouver(utilisateur, alerte_id)
    propre = _valider({k: v for k, v in donnees.items() if k in CHAMPS})
    if propre.get("is_active") and not alerte.is_active:
        _verifier_plafond(utilisateur, ignorer=alerte.pk)
    for nom, valeur in propre.items():
        setattr(alerte, nom, valeur)
    alerte.save()
    return alerte


def supprimer(utilisateur, alerte_id) -> None:
    _trouver(utilisateur, alerte_id).delete()


def notifier_correspondances(annonce_id) -> int:
    """À la publication : une notification par couple alerte/annonce (clé d'unicité), jamais deux (EF-ALR-03)."""
    annonce = Listing.objects.filter(pk=annonce_id, status="published").first()
    if annonce is None:
        return 0
    creees = 0
    loin = textes.distance(annonce.distance_to_campus_m)
    details = [
        types_chambre.libelle(annonce.room_type),
        f"{textes.francs(annonce.rent_amount)}/mois",
        f"à {loin} de l'UP" if loin else None,
    ]
    corps = " · ".join(d for d in details if d) + ". Vois-la avant les autres."
    for alerte_id, utilisateur_id in selectors.alertes_correspondantes(annonce_id):
        n = notifications.creer(
            utilisateur_id,
            "alert.match",
            f"Nouvelle chambre à {annonce.district.name}",
            corps,
            data={"listing_id": str(annonce.pk), "slug": annonce.slug, "alert_id": str(alerte_id)},
            dedupe_key=f"alert:{alerte_id}:{annonce_id}",
        )
        creees += 1 if n else 0
    return creees
