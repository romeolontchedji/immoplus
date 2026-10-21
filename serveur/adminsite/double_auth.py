"""Double authentification de l'administration : un code à 6 chiffres envoyé par courriel à chaque connexion.

Le mot de passe est vérifié comme d'habitude (axes, journal). La session est alors marquée « en attente » et
`DoubleAuthMiddleware` renvoie toute page vers l'écran de vérification tant que le code n'est pas saisi : un mot de
passe volé ne suffit plus. Le code ne vit que 10 minutes dans redis-queue, sous forme d'empreinte HMAC ; 5 erreurs
déconnectent ; un renvoi est possible toutes les 60 s, 3 fois au plus.
"""

import hashlib
import hmac
import json
import secrets

from django.conf import settings
from django.contrib.auth import logout
from django.utils import timezone

from apps.audit import services as audit
from apps.core import redis_file
from apps.core.http import ip_client, user_agent

CLE_SESSION = "double_auth_ok"
DUREE_S = 600
ESSAIS_MAX = 5
RENVOIS_MAX = 3
DELAI_RENVOI_S = 60


def active() -> bool:
    """Réglage `ADMIN_2FA_ACTIVE` (vrai par défaut, toujours vrai en production)."""
    return bool(getattr(settings, "ADMIN_2FA_ACTIVE", True))


def _cle(request) -> str:
    return f"admin:2fa:{request.session.session_key}"


def _empreinte(code: str, utilisateur_id) -> str:
    message = f"{utilisateur_id}|{code}".encode()
    return hmac.new(settings.SECRET_KEY.encode(), message, hashlib.sha256).hexdigest()


def masquer_courriel(adresse: str) -> str:
    """« admin.essai@immoplus.bj » → « a••••••••••@immoplus.bj » : on montre où le code est parti sans tout révéler."""
    nom, _, domaine = (adresse or "").partition("@")
    return f"{nom[:1]}{'•' * max(len(nom) - 1, 1)}@{domaine}" if domaine else "ton adresse"


def _envoyer(request, utilisateur, etat: dict) -> None:
    from apps.core.tasks import envoyer_courriel

    code = f"{secrets.randbelow(10**6):06d}"
    etat.update(
        h=_empreinte(code, utilisateur.pk), essais=0, dernier=int(timezone.now().timestamp())
    )
    redis_file.client().set(_cle(request), json.dumps(etat), ex=DUREE_S)
    heure = timezone.localtime().strftime("%H:%M")
    envoyer_courriel.delay(
        [utilisateur.email],
        f"Immo+ · ton code de connexion : {code}",
        f"Bonjour {utilisateur.full_name or ''},\n\n"
        f"Ton code de connexion à l'administration Immo+ : {code}\n"
        f"Il est valable 10 minutes.\n\n"
        f"Demande faite à {heure} depuis l'adresse {ip_client(request) or 'inconnue'}.\n"
        "Si ce n'est pas toi, ne transmets ce code à personne et change ton mot de passe : "
        "quelqu'un connaît ton mot de passe.\n",
    )


def demarrer(request, utilisateur) -> None:
    """Après un mot de passe correct : session en attente, premier code envoyé."""
    if not active():
        request.session[CLE_SESSION] = True
        return
    request.session[CLE_SESSION] = False
    request.session.save()  # la clé de session sert d'identifiant du défi
    _envoyer(request, utilisateur, {"u": str(utilisateur.pk), "renvois": 0})
    audit.enregistrer(
        "admin.2fa_envoye", acteur=utilisateur, cible=utilisateur,
        ip=ip_client(request), user_agent=user_agent(request),
    )  # fmt: skip


def en_attente(request) -> bool:
    return request.user.is_authenticated and request.session.get(CLE_SESSION) is False


def verifier(request, code: str) -> str:
    """Retourne « ok », « faux » (il reste des essais), « bloque » (déconnecté) ou « expire »."""
    r = redis_file.client()
    brut = r.get(_cle(request))
    if brut is None:
        logout(request)
        return "expire"
    etat = json.loads(brut)
    saisi = "".join(c for c in (code or "") if c.isdigit())
    if hmac.compare_digest(etat["h"], _empreinte(saisi, request.user.pk)):
        r.delete(_cle(request))
        request.session[CLE_SESSION] = True
        audit.enregistrer(
            "admin.2fa_reussie", acteur=request.user, cible=request.user,
            ip=ip_client(request), user_agent=user_agent(request),
        )  # fmt: skip
        return "ok"
    etat["essais"] += 1
    if etat["essais"] >= ESSAIS_MAX:
        r.delete(_cle(request))
        audit.enregistrer(
            "admin.2fa_bloquee", acteur=request.user, cible=request.user,
            ip=ip_client(request), user_agent=user_agent(request),
        )  # fmt: skip
        logout(request)
        return "bloque"
    r.set(_cle(request), json.dumps(etat), keepttl=True)
    return "faux"


def renvoyer(request) -> str:
    """Retourne « envoye », « attendre » (moins de 60 s) ou « plafond » (3 renvois déjà faits)."""
    r = redis_file.client()
    brut = r.get(_cle(request))
    if brut is None:
        return "plafond"
    etat = json.loads(brut)
    if etat["renvois"] >= RENVOIS_MAX:
        return "plafond"
    if int(timezone.now().timestamp()) - etat["dernier"] < DELAI_RENVOI_S:
        return "attendre"
    etat["renvois"] += 1
    _envoyer(request, request.user, etat)
    return "envoye"
