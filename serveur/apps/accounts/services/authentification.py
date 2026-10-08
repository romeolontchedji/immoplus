"""Connexion par numéro et mot de passe (CDC EF-AUT-04, EF-AUT-05, EF-AUT-08)."""

import hashlib

from apps.accounts.models import ROLES_CLIENTELE, Statut, User
from apps.accounts.phone import NumeroInvalide, normaliser
from apps.core import parametres
from apps.core.errors import ErreurMetier

from . import mots_de_passe, verrouillage


def _cle_telephone(saisie: str) -> tuple[str, str | None]:
    """Retourne (clé de comptage, numéro E.164 ou None). Une saisie illisible est comptée comme un numéro inconnu."""
    try:
        e164 = normaliser(saisie, tuple(parametres.lire("OTP_ALLOWED_COUNTRIES")))
        return e164, e164
    except NumeroInvalide:
        brut = (saisie or "").strip().lower()[:40]
        return "x:" + hashlib.sha256(brut.encode()).hexdigest()[:24], None


def authentifier(saisie_telephone: str, mot_de_passe: str, client: str) -> User:
    """Retourne le compte (locataire ou gérant) si les identifiants sont corrects.

    `client` est l'identifiant d'installation (application) ou l'adresse IP (site). Toute erreur d'identifiants
    — numéro inconnu, mauvais mot de passe, compte du personnel, verrouillage — donne le même refus 401.
    Un compte suspendu ou banni n'est révélé qu'après un mot de passe correct.
    """
    cle, e164 = _cle_telephone(saisie_telephone)
    verrouillage.controler(cle, client)

    utilisateur = None
    if e164:
        utilisateur = User.objects.filter(
            phone_e164=e164, role__in=ROLES_CLIENTELE, deleted_at__isnull=True
        ).first()
    correct = mots_de_passe.verifier(utilisateur, mot_de_passe or "")
    if not correct or utilisateur is None:
        verrouillage.enregistrer_echec(cle, client)
        raise verrouillage.refus_uniforme(1)

    if utilisateur.status == Statut.BANNED or not utilisateur.is_active:
        raise ErreurMetier(
            "account_suspended",
            "Ton compte est suspendu. Contacte le support de Logeo.",
            statut=403,
        )
    verrouillage.enregistrer_succes(cle, client)
    return utilisateur
