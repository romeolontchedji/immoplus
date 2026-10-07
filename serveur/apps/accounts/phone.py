"""Normalisation des numéros de téléphone en E.164 (CDC EF-AUT-01).

Le Bénin est passé à 10 chiffres (préfixe « 01 ») en 2024 : `phonenumbers` refuse désormais les anciens numéros à
8 chiffres. Forme canonique : `+229` + `01` + 8 chiffres. Un numéro à 8 chiffres est complété par `01`.
"""

import re

import phonenumbers
from phonenumbers import NumberParseException, PhoneNumberType

PAYS_PAR_DEFAUT = "BJ"
_NON_CHIFFRES = re.compile(r"[^\d+]")


class NumeroInvalide(ValueError):
    """Le numéro saisi n'est pas un mobile valide d'un pays autorisé."""


def _forme_beninoise(chiffres: str) -> str | None:
    """Réduit une saisie béninoise à `01XXXXXXXX` ; None si elle n'a pas la bonne forme."""
    for prefixe in ("00229", "229"):
        if chiffres.startswith(prefixe):
            chiffres = chiffres[len(prefixe) :]
            break
    if len(chiffres) == 8:
        return "01" + chiffres
    if len(chiffres) == 10 and chiffres.startswith("01"):
        return chiffres
    return None


def normaliser(
    saisie: str, pays_autorises: list[str] | tuple[str, ...] = (PAYS_PAR_DEFAUT,)
) -> str:
    """Retourne le numéro en E.164, ou lève `NumeroInvalide`. Seuls les mobiles des pays autorisés passent."""
    if not isinstance(saisie, str) or len(saisie) > 40:
        raise NumeroInvalide("numéro illisible")
    nettoye = _NON_CHIFFRES.sub("", saisie)
    if nettoye.count("+") > 1 or ("+" in nettoye and not nettoye.startswith("+")):
        raise NumeroInvalide("numéro illisible")
    chiffres = nettoye.lstrip("+")
    if not chiffres:
        raise NumeroInvalide("numéro vide")

    etranger = nettoye.startswith("+") and not chiffres.startswith("229")
    if etranger:
        candidat = nettoye
    elif PAYS_PAR_DEFAUT in pays_autorises or not nettoye.startswith("+"):
        forme = _forme_beninoise(chiffres)
        if forme is None:
            raise NumeroInvalide(
                "format béninois attendu : 8 chiffres ou 10 chiffres commençant par 01"
            )
        candidat = "+229" + forme
    else:
        candidat = nettoye
    try:
        numero = phonenumbers.parse(candidat, None)
    except NumberParseException as erreur:
        raise NumeroInvalide("numéro illisible") from erreur
    if not phonenumbers.is_valid_number(numero):
        raise NumeroInvalide("numéro invalide")
    if phonenumbers.number_type(numero) != PhoneNumberType.MOBILE:
        raise NumeroInvalide("un numéro de mobile est exigé")
    region = phonenumbers.region_code_for_number(numero)
    if region not in pays_autorises:
        raise NumeroInvalide("pays non autorisé")
    return phonenumbers.format_number(numero, phonenumbers.PhoneNumberFormat.E164)


def masquer(e164: str) -> str:
    """Forme affichable sans exposer le numéro entier : `+229 •• •• ••56`."""
    if len(e164) < 6:
        return "••••"
    return f"{e164[:4]} {'•• ' * 3}{e164[-2:]}"
