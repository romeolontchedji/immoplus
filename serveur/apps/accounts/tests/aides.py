"""Aides de test communes aux services de comptes."""

import uuid

from django.core import signing

from apps.accounts.services import otp


def jeton_otp(telephone: str, objet: str) -> str:
    """Un jeton OTP valide fabriqué directement (les tests du service OTP couvrent le vrai parcours)."""
    return signing.dumps({"p": telephone, "o": objet, "i": str(uuid.uuid4())}, salt=otp.SEL_JETON)
