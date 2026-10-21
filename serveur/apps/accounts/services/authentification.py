"""Connexion par nom d'utilisateur et mot de passe (ADR 0009, CDC EF-AUT-04, EF-AUT-05, EF-AUT-08).

Aucun numéro de téléphone n'est conservé : le nom d'utilisateur est le seul identifiant.
"""

import hashlib

from apps.accounts.models import ROLES_CLIENTELE, Statut, User
from apps.audit import services as audit
from apps.core.errors import ErreurMetier

from . import identifiants, mots_de_passe, verrouillage


def _journaliser_echec(cle: str, utilisateur, client: str, verrouille: bool) -> None:
    """Échec de connexion du site ou de l'application, visible dans l'administration (plan v3, J2)."""
    adresse = any(
        c in client for c in ".:"
    )  # le site passe l'adresse IP (ou « web »), l'application son installation
    surface = "site" if adresse or client == "web" else "application"
    audit.enregistrer(
        "auth.compte_verrouille" if verrouille else "auth.connexion_echouee",
        cible=utilisateur, cible_type=None if utilisateur else "user",
        metadata={"identifiant": cle[2:] if cle.startswith("u:") else "illisible",
                  "surface": surface, "compte_connu": utilisateur is not None},
        ip=client if adresse else None,
    )  # fmt: skip


def _compte(identifiant: str) -> tuple[str, User | None]:
    """(clé de comptage, compte ou None). Une saisie illisible est comptée sans être conservée telle quelle."""
    nom = identifiants.normaliser_nom_utilisateur(identifiant)
    if not identifiants.MOTIF.match(nom):
        return "x:" + hashlib.sha256(nom[:40].encode()).hexdigest()[:24], None
    compte = User.objects.filter(
        username=nom, role__in=ROLES_CLIENTELE, deleted_at__isnull=True
    ).first()
    return "u:" + nom, compte


def authentifier(identifiant: str, mot_de_passe: str, client: str) -> User:
    """Retourne le compte (locataire ou gérant) si les identifiants sont corrects.

    `client` est l'identifiant d'installation (application) ou l'adresse IP (site). Toute erreur d'identifiants
    — nom inconnu, mauvais mot de passe, compte du personnel, verrouillage — donne le même refus 401.
    Un compte suspendu ou banni n'est révélé qu'après un mot de passe correct.
    """
    cle, utilisateur = _compte(identifiant)
    verrouillage.controler(cle, client)
    correct = mots_de_passe.verifier(utilisateur, mot_de_passe or "")
    if not correct or utilisateur is None:
        verrouille = verrouillage.enregistrer_echec(cle, client)
        _journaliser_echec(cle, utilisateur, client, verrouille)
        raise verrouillage.refus_uniforme(1)

    if utilisateur.status == Statut.BANNED or not utilisateur.is_active:
        raise ErreurMetier(
            "account_suspended",
            "Ton compte est suspendu. Contacte le support de Immo+.",
            statut=403,
        )
    verrouillage.enregistrer_succes(cle, client)
    return utilisateur
