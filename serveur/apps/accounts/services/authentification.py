"""Connexion par nom d'utilisateur et mot de passe (ADR 0009, CDC EF-AUT-04, EF-AUT-05, EF-AUT-08).

Transition : jusqu'à `CONNEXION_PAR_NUMERO_JUSQUA`, un compte créé avant l'ADR 0009 peut encore se connecter avec
son numéro, si ce numéro ne désigne qu'un seul compte.
"""

import datetime
import hashlib

from django.utils import timezone

from apps.accounts.models import ROLES_CLIENTELE, Statut, User
from apps.accounts.phone import NumeroInvalide, normaliser
from apps.audit import services as audit
from apps.core import parametres
from apps.core.errors import ErreurMetier

from . import identifiants, mots_de_passe, verrouillage

CONNEXION_PAR_NUMERO_JUSQUA = datetime.date(2026, 11, 20)


def _cle_telephone(saisie: str) -> tuple[str, str | None]:
    """Retourne (clé de comptage, numéro E.164 ou None). Une saisie illisible est comptée comme un numéro inconnu."""
    try:
        e164 = normaliser(saisie, tuple(parametres.lire("OTP_ALLOWED_COUNTRIES")))
        return e164, e164
    except NumeroInvalide:
        brut = (saisie or "").strip().lower()[:40]
        return "x:" + hashlib.sha256(brut.encode()).hexdigest()[:24], None


def numero_masque(e164: str | None) -> str:
    """« +2290197123456 » → « +229 01 ** ** 34 56 » : assez pour reconnaître un compte, jamais le numéro entier."""
    if not e164:
        return "numéro illisible"
    chiffres = e164.removeprefix("+229")
    return f"+229 {chiffres[:2]} ** ** {chiffres[-4:-2]} {chiffres[-2:]}"


def _journaliser_echec(cle: str, e164, utilisateur, client: str, verrouille: bool) -> None:
    """Échec de connexion du site ou de l'application, visible dans l'administration (plan v3, J2)."""
    adresse = any(
        c in client for c in ".:"
    )  # le site passe l'adresse IP (ou « web »), l'application son installation
    surface = "site" if adresse or client == "web" else "application"
    audit.enregistrer(
        "auth.compte_verrouille" if verrouille else "auth.connexion_echouee",
        cible=utilisateur, cible_type=None if utilisateur else "user",
        metadata={"identifiant": cle[2:] if cle.startswith("u:") else numero_masque(e164),
                  "surface": surface, "compte_connu": utilisateur is not None},
        ip=client if adresse else None,
    )  # fmt: skip


def _compte(identifiant: str) -> tuple[str, User | None, str | None]:
    """(clé de comptage, compte ou None, numéro E.164 si la saisie en est un)."""
    nom = identifiants.normaliser_nom_utilisateur(identifiant)
    base = User.objects.filter(role__in=ROLES_CLIENTELE, deleted_at__isnull=True)
    if identifiants.MOTIF.match(nom) and not nom.isdigit():
        return "u:" + nom, base.filter(username=nom).first(), None
    cle, e164 = _cle_telephone(identifiant)
    utilisateur = None
    if e164 and timezone.localdate() < CONNEXION_PAR_NUMERO_JUSQUA:
        comptes = list(base.filter(phone_e164=e164)[:2])
        utilisateur = comptes[0] if len(comptes) == 1 else None
    return cle, utilisateur, e164


def authentifier(identifiant: str, mot_de_passe: str, client: str) -> User:
    """Retourne le compte (locataire ou gérant) si les identifiants sont corrects.

    `client` est l'identifiant d'installation (application) ou l'adresse IP (site). Toute erreur d'identifiants
    — nom inconnu, mauvais mot de passe, compte du personnel, verrouillage — donne le même refus 401.
    Un compte suspendu ou banni n'est révélé qu'après un mot de passe correct.
    """
    cle, utilisateur, e164 = _compte(identifiant)
    verrouillage.controler(cle, client)
    correct = mots_de_passe.verifier(utilisateur, mot_de_passe or "")
    if not correct or utilisateur is None:
        verrouille = verrouillage.enregistrer_echec(cle, client)
        _journaliser_echec(cle, e164, utilisateur, client, verrouille)
        raise verrouillage.refus_uniforme(1)

    if utilisateur.status == Statut.BANNED or not utilisateur.is_active:
        raise ErreurMetier(
            "account_suspended",
            "Ton compte est suspendu. Contacte le support de Immo+.",
            statut=403,
        )
    verrouillage.enregistrer_succes(cle, client)
    return utilisateur
