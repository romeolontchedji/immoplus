"""Journaux JSON ; le filtre masque numéros de téléphone et codes à usage unique."""

import json
import logging
import re
from datetime import UTC, datetime

from . import requete

_TELEPHONE = re.compile(r"(?<![\w.])(?:\+|00)?(?:229[\s.-]?)?(?:\d[\s.-]?){7,13}\d(?![\w])")
_CODE = re.compile(r"(?i)\b(code|otp)(\s*[:=]?\s*)(\d{6})\b")
MASQUE = "[masqué]"


def masquer(texte: str) -> str:
    """Remplace les numéros (8 à 14 chiffres) et les codes à 6 chiffres annoncés par « code »."""
    texte = _CODE.sub(lambda m: f"{m.group(1)}{m.group(2)}{MASQUE}", texte)
    return _TELEPHONE.sub(MASQUE, texte)


class FiltreMasque(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.msg = masquer(record.getMessage())
        record.args = None
        return True


class FormateurJson(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        charge = {
            "ts": datetime.fromtimestamp(record.created, UTC).isoformat(timespec="milliseconds"),
            "niveau": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "id_requete": requete.courant(),
        }
        if record.exc_info:
            charge["exception"] = masquer(self.formatException(record.exc_info))
        return json.dumps(charge, ensure_ascii=False)
