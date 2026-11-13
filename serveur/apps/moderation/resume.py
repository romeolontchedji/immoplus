"""Résumé hebdomadaire par courriel à l'équipe (administrateurs et modérateurs) : nouvelles annonces, signalements
ouverts, paiements. Part chaque lundi matin (`config/celery.py`), sauf si `EMAIL_RESUME_HEBDOMADAIRE` est décoché."""

import datetime
import logging

from django.conf import settings
from django.utils import timezone

from apps.accounts import selectors as comptes
from apps.billing import services as paiements
from apps.core import parametres
from apps.core.tasks import envoyer_courriel
from apps.listings import selectors as annonces

from . import services

journal = logging.getLogger(__name__)
JOURS = 7


def construire(maintenant: datetime.datetime | None = None) -> tuple[str, str]:
    """(sujet, texte) du résumé des 7 derniers jours."""
    maintenant = maintenant or timezone.now()
    debut = maintenant - datetime.timedelta(days=JOURS)
    pilotage = f"https://pilotage.{settings.DOMAIN}"
    total, liste = annonces.nouvelles_annonces(debut)
    dossiers = services.tableau()
    bilan = paiements.bilan_paiements(debut)
    du, au = timezone.localtime(debut), timezone.localtime(maintenant)
    lignes = [f"Résumé d'Immo+ du {du:%d/%m} au {au:%d/%m/%Y}.", ""]

    lignes.append(f"Nouvelles annonces : {total}")
    lignes += [
        f"- {a['title']} · {a['district']} · {a['rent_amount']} F/mois" for a in liste
    ]
    if total > len(liste):
        lignes.append(f"- … et {total - len(liste)} autre(s)")
    lignes += [
        f"Voir les nouvelles annonces : {pilotage}/listings/listing/?published_at__gte={debut:%Y-%m-%d}",
        "",
    ]

    hors_delai = dossiers["hors_delai"]
    lignes.append(
        f"Signalements ouverts : {dossiers['ouverts']}"
        + (f" (dont {hors_delai} hors délai de 24 h)" if hors_delai else "")
    )
    lignes += [f"Traiter les signalements : {pilotage}/moderation/report/", ""]

    if bilan["nombre"]:
        lignes.append(
            f"Paiements de la semaine : {bilan['nombre']} pour {bilan['total']} F "
            f"(abonnements : {bilan['abonnements']}, alertes : {bilan['alertes']})"
        )
    else:
        lignes.append("Paiements de la semaine : aucun")
    lignes += [
        f"Voir les paiements : {pilotage}/billing/transaction/",
        f"Voir les statistiques : {pilotage}/statistiques/",
    ]
    return f"Immo+ · résumé de la semaine ({total} nouvelle(s) annonce(s))", "\n".join(lignes) + "\n"


def envoyer(maintenant: datetime.datetime | None = None) -> dict:
    """Dépose un courriel par destinataire ; sans effet si le paramètre est décoché ou si personne n'a d'adresse."""
    if not parametres.lire("EMAIL_RESUME_HEBDOMADAIRE"):
        return {"envoyes": 0, "raison": "desactive"}
    destinataires = comptes.courriels_equipe()
    if not destinataires:
        return {"envoyes": 0, "raison": "sans_destinataire"}
    sujet, texte = construire(maintenant)
    envoyes = 0
    for adresse in destinataires:
        try:
            envoyer_courriel.delay([adresse], sujet, texte)
            envoyes += 1
        except Exception:  # noqa: BLE001 - un destinataire en échec ne doit pas priver les autres
            journal.exception("Résumé hebdomadaire non déposé pour un destinataire")
    return {"envoyes": envoyes}
