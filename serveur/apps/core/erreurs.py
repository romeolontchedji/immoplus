"""Suivi des erreurs : toute erreur journalisée (site, API, temps réel, tâches) est regroupée et conservée.

Comment ça marche :
1. `JournalErreursHandler` est branché sur la journalisation (réglage LOGGING) au niveau ERROR, dans tous les
   processus. Une erreur non prévue d'une page ou de l'API, une tâche qui échoue : tout passe par lui.
2. Les erreurs identiques (même type, même endroit du code) sont **regroupées** sous une empreinte : on garde le
   nombre d'occurrences, la première et la dernière date, le dernier détail (masqué : ni numéro ni code).
3. Le tout vit dans redis-queue (30 jours, 200 erreurs au plus) et s'affiche dans l'administration (« Erreurs »).
4. Un courriel part vers `ERREURS_DESTINATAIRES` à la première apparition, puis au plus une fois par heure et par
   erreur : quelques courriels par jour au pire, gratuits avec n'importe quel serveur SMTP.

Le gestionnaire ne lève jamais : si Redis est absent, l'erreur reste dans les journaux habituels, rien de plus.
"""

import hashlib
import json
import logging
import os
import time
import traceback
from datetime import UTC, datetime

from django.conf import settings
from django.utils import timezone

from apps.core.logging import masquer

INDEX = "erreurs:index"
PREFIXE = "erreurs:e:"
CONSERVATION_S = 30 * 86400
MAX_ERREURS = 200
DELAI_COURRIEL_S = 3600
DETAIL_MAX = 6000


def _lieu(record: logging.LogRecord) -> str:
    """Dernier endroit du code de Immo+ traversé par l'erreur (« apps/chat/services.py:142 »), sinon le logger."""
    if record.exc_info and record.exc_info[2]:
        lieux = [
            f"{os.path.relpath(f.filename, '/app') if f.filename.startswith('/app') else f.filename}:{f.lineno}"
            for f in traceback.extract_tb(record.exc_info[2])
        ]
        du_projet = [
            lieu for lieu in lieux if "site-packages" not in lieu and "/lib/python" not in lieu
        ]
        return (du_projet or lieux or [record.name])[-1]
    return f"{record.pathname}:{record.lineno}"


def _type(record: logging.LogRecord) -> str:
    return (
        record.exc_info[0].__name__
        if record.exc_info and record.exc_info[0]
        else "Erreur journalisée"
    )


def empreinte(record: logging.LogRecord) -> str:
    """Même type et même endroit = même erreur, quel que soit le texte exact (identifiants, dates…)."""
    base = f"{_type(record)}|{_lieu(record)}|{record.msg if not record.exc_info else ''}"
    return hashlib.sha1(base.encode(), usedforsecurity=False).hexdigest()[:16]


class JournalErreursHandler(logging.Handler):
    def emit(self, record: logging.LogRecord) -> None:
        try:
            self._enregistrer(record)
        except Exception:  # noqa: BLE001, S110  # nosec B110 - le suivi des erreurs ne doit jamais en créer une autre
            pass

    def _enregistrer(self, record: logging.LogRecord) -> None:
        from apps.core import redis_file

        r = redis_file.client()
        cle = empreinte(record)
        maintenant = int(time.time())
        detail = masquer(
            "".join(traceback.format_exception(*record.exc_info))
            if record.exc_info
            else record.getMessage()
        )[-DETAIL_MAX:]
        brut = r.get(PREFIXE + cle)
        erreur = json.loads(brut) if brut else {
            "id": cle,
            "type": _type(record),
            "lieu": _lieu(record),
            "premiere": maintenant,
            "nombre": 0,
            "courriel": 0,
        }  # fmt: skip
        erreur.update(
            message=masquer(record.getMessage())[:300],
            logger=record.name,
            processus=os.environ.get("IMMOPLUS_SERVICE", "inconnu"),
            derniere=maintenant,
            detail=detail,
            nombre=erreur["nombre"] + 1,
        )
        envoyer = maintenant - erreur["courriel"] >= DELAI_COURRIEL_S
        if envoyer:
            erreur["courriel"] = maintenant
        r.set(PREFIXE + cle, json.dumps(erreur), ex=CONSERVATION_S)
        r.zadd(INDEX, {cle: maintenant})
        r.zremrangebyrank(INDEX, 0, -(MAX_ERREURS + 1))  # ne garde que les plus récentes
        if envoyer:
            _prevenir(erreur)


def _prevenir(erreur: dict) -> None:
    destinataires = list(getattr(settings, "ERREURS_DESTINATAIRES", []) or [])
    if not destinataires:
        return
    from apps.core.tasks import envoyer_courriel

    envoyer_courriel.delay(
        destinataires,
        f"Immo+ · erreur {erreur['type']} ({erreur['processus']})",
        f"Une erreur vient de se produire sur Immo+.\n\n"
        f"Type : {erreur['type']}\nEndroit : {erreur['lieu']}\nProcessus : {erreur['processus']}\n"
        f"Occurrences : {erreur['nombre']}\nMessage : {erreur['message']}\n\n"
        f"Détail (dernières lignes) :\n{erreur['detail'][-2500:]}\n\n"
        "Liste complète : administration › Erreurs. Prochain courriel pour cette erreur : dans une heure au plus tôt.\n",
    )


# ---------------------------------------------------------------- lectures (administration)
def liste(limite: int = 100) -> list[dict]:
    """Erreurs les plus récentes d'abord ; une erreur expirée disparaît aussi de l'index."""
    from apps.core import redis_file

    r = redis_file.client()
    sortie = []
    for cle in r.zrevrange(INDEX, 0, limite - 1):
        brut = r.get(PREFIXE + cle)
        if brut is None:
            r.zrem(INDEX, cle)
            continue
        erreur = json.loads(brut)
        for champ in ("premiere", "derniere"):  # dates lisibles, heure du Bénin
            erreur[f"{champ}_le"] = timezone.localtime(
                datetime.fromtimestamp(erreur[champ], tz=UTC)
            ).strftime("%d/%m/%Y %H:%M")
        sortie.append(erreur)
    return sortie


def resoudre(cle: str) -> None:
    """« Corrigée » : l'erreur disparaît ; si elle revient, elle repart de zéro (et un courriel repart)."""
    from apps.core import redis_file

    r = redis_file.client()
    r.delete(PREFIXE + cle)
    r.zrem(INDEX, cle)
