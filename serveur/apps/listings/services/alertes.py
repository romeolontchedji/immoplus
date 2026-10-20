"""Alertes des locataires (CDC §7.5) : gestion et correspondance à la publication."""

import uuid

from django.db.models import Count

from apps.core import parametres
from apps.core.errors import ErreurMetier
from apps.notifications import selectors as notif_selectors
from apps.notifications import services as notifications
from apps.notifications import textes

from .. import selectors
from ..enums import Compteur, Cuisine, Eau
from ..models import Alert, District, Listing
from . import types as types_chambre

CHAMPS = (
    "label",
    "district_ids",
    "room_types",
    "max_rent",
    "private_bathroom_required",
    "max_distance_m",
    "water_sources",
    "electricity_meters",
    "kitchens",
    "fenced_required",
    "is_active",
)
# Critères : il en faut au moins un pour créer une alerte (le nom seul ne suffit pas).
CRITERES = tuple(c for c in CHAMPS if c not in ("label", "is_active"))
EQUIPEMENTS = {"water_sources": Eau, "electricity_meters": Compteur, "kitchens": Cuisine}


BUDGETS_DE_BASE = (10_000, 15_000, 20_000, 25_000, 30_000, 40_000, 50_000, 75_000)
BUDGETS_MAX = 8


def _budgets_frequents() -> list[int]:
    """Plafonds proposés : quartiles des loyers publiés (arrondis aux 5 000 F supérieurs), complétés par les
    paliers courants, sans doublon, du plus petit au plus grand."""
    loyers = sorted(
        Listing.objects.filter(status="published", deleted_at__isnull=True).values_list(
            "rent_amount", flat=True
        )
    )
    reperes = set()
    if loyers:
        for q in (0.25, 0.5, 0.75, 0.9):
            loyer = loyers[min(len(loyers) - 1, int(q * len(loyers)))]
            reperes.add(-(-loyer // 5_000) * 5_000)
    for b in BUDGETS_DE_BASE:
        if len(reperes) >= BUDGETS_MAX:
            break
        reperes.add(b)
    return sorted(reperes)[:BUDGETS_MAX]


def options() -> dict:
    """Listes de l'éditeur d'alerte (plan v2, M5) : quartiers les plus demandés d'abord (alertes actives qui les
    citent, puis annonces publiées), budgets fréquents. Même source pour le site et le mobile."""
    from django.db import connection

    with connection.cursor() as c:
        c.execute(
            "SELECT unnest(district_ids) AS d, count(*) FROM alerts WHERE is_active GROUP BY d"
        )
        demandes = {str(d): n for d, n in c.fetchall()}
    offres = {
        str(d): n
        for d, n in Listing.objects.filter(status="published", deleted_at__isnull=True)
        .values_list("district_id")
        .annotate(n=Count("id"))
        .values_list("district_id", "n")
    }
    quartiers = [
        {
            "id": q.pk,
            "name": q.name,
            "slug": q.slug,
            "alerts": demandes.get(str(q.pk), 0),
            "listings": offres.get(str(q.pk), 0),
            "ordre": q.sort_order,
        }
        for q in District.objects.filter(is_active=True)
    ]
    quartiers.sort(key=lambda q: (-q["alerts"], -q["listings"], q["ordre"], q["name"]))
    return {
        "districts": [{k: v for k, v in q.items() if k != "ordre"} for q in quartiers],
        "budgets": _budgets_frequents(),
    }


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
    if "fenced_required" in d:
        propre["fenced_required"] = bool(d["fenced_required"])
    for nom, valeurs in EQUIPEMENTS.items():
        if nom in d:
            choix = list(d[nom] or [])
            if any(v not in valeurs.values for v in choix):
                raise ErreurMetier(
                    "validation_error", "Valeur inconnue.", champs={nom: ["Valeur inconnue"]}
                )
            propre[nom] = [v for v in valeurs.values if v in choix]
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


def a_un_critere(criteres: dict) -> bool:
    """Vrai si au moins une option est choisie (quartier, type, budget, équipement…)."""
    return any(criteres.get(c) not in (None, False, "", [], ()) for c in CRITERES)


def _exiger_un_critere(criteres: dict) -> None:
    if not a_un_critere(criteres):
        raise ErreurMetier(
            "alert_empty",
            "Choisis d'abord au moins une option : quartier, type, budget ou équipement.",
            champs={"non_field_errors": ["Choisis d'abord au moins une option."]},
        )


def creer(utilisateur, donnees: dict) -> Alert:
    propre = _valider(donnees)
    _exiger_un_critere(propre)
    _verifier_plafond(utilisateur)
    return Alert.objects.create(user=utilisateur, **propre)


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
    if set(propre) & set(CRITERES):  # pause, reprise ou nom seul : pas de contrôle des critères
        _exiger_un_critere({c: getattr(alerte, c) for c in CRITERES})
    alerte.save()
    return alerte


def supprimer(utilisateur, alerte_id) -> None:
    _trouver(utilisateur, alerte_id).delete()


PLAFOND_ALERTE_PAR_JOUR = 3


def _recapitulatif(alerte_id, utilisateur_id, nom: str) -> int:
    """4e chambre du jour : un récapitulatif (« 4 nouvelles chambres… ») ; les suivantes l'incrémentent en silence."""
    from django.utils import timezone

    cle = f"alert-digest:{alerte_id}:{timezone.localdate().isoformat()}"
    precedent = notif_selectors.donnees_par_cle(cle)
    compte = (
        int(precedent.get("count", PLAFOND_ALERTE_PAR_JOUR)) + 1
        if precedent
        else PLAFOND_ALERTE_PAR_JOUR + 1
    )
    titre = f"{compte} nouvelles chambres pour ton alerte « {nom} »"
    corps_recap = "Elles correspondent à tes critères. Ouvre tes alertes pour les voir toutes."
    data = {"alert_id": str(alerte_id), "count": compte}
    if precedent is not None:
        notifications.mettre_a_jour_en_silence(cle, titre, corps_recap, data)
        return 0
    n = notifications.creer(
        utilisateur_id, "alert.digest", titre, corps_recap, data=data, dedupe_key=cle
    )
    return 1 if n else 0


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
    correspondances = list(selectors.alertes_correspondantes(annonce_id))
    libelles = dict(
        Alert.objects.filter(pk__in=[a for a, _ in correspondances]).values_list("pk", "label")
    )
    for alerte_id, utilisateur_id in correspondances:
        deja = notif_selectors.nombre_du_jour(
            utilisateur_id, "alert.match", "alert_id", str(alerte_id)
        )
        if deja >= PLAFOND_ALERTE_PAR_JOUR:
            # Plan v2, A2 : au-delà de 3 chambres dans la journée, un seul récapitulatif qui grossit sans re-sonner.
            creees += _recapitulatif(
                alerte_id, utilisateur_id, libelles.get(alerte_id) or annonce.district.name
            )
            continue
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
