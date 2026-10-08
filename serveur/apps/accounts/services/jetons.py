"""Jetons de l'application : accès JWT de 15 minutes et rafraîchissement opaque avec rotation (CDC §5.2).

- Accès : HS256, clé distincte de celle de l'administration ; `aud` (client|gerant), `sub`, `did`, `ver`.
- Rafraîchissement : jeton opaque de 30 jours lié à un appareil, échangé à chaque usage. Un ancien jeton
  rejoué dans les 60 s renvoie la même nouvelle paire (réponse perdue en 3G) ; après 60 s, l'appareil est révoqué.
- `token_version` et la liste des appareils révoqués sont en cache et relus en base si le cache est vide.
"""

import base64
import hashlib
import secrets
from dataclasses import dataclass
from datetime import timedelta

import jwt
from cryptography.fernet import Fernet, InvalidToken
from django.conf import settings
from django.core.cache import cache
from django.db import transaction
from django.utils import timezone

from apps.accounts.models import Device, User
from apps.audit import services as audit
from apps.core import redis_file
from apps.core.errors import ErreurMetier

ISSUER = "logeo"
DUREE_ACCES = timedelta(minutes=15)
DUREE_REFRESH = timedelta(days=30)
GRACE_S = 60
AUDIENCES = ("client", "gerant")
DELAI_CACHE_S = 300


@dataclass(frozen=True)
class Identite:
    utilisateur_id: str
    appareil_id: str
    role: str


@dataclass(frozen=True)
class Paire:
    acces: str
    refresh: str
    expire_dans_s: int


def _non_valide() -> ErreurMetier:
    return ErreurMetier("invalid_token", "Session invalide ou expirée. Reconnecte-toi.", statut=401)


def empreinte(refresh: str) -> str:
    return hashlib.sha256(refresh.encode()).hexdigest()


# --- Cache des contrôles à chaque requête ---
def _cle_utilisateur(uid) -> str:
    return f"securite:utilisateur:{uid}"


def _cle_appareil(did) -> str:
    return f"securite:appareil:{did}"


def invalider_utilisateur(utilisateur_id) -> None:
    """À appeler après toute modification de `token_version`, du statut ou du rôle."""
    cache.delete(_cle_utilisateur(utilisateur_id))


def marquer_appareil_actif(appareil_id) -> None:
    cache.set(_cle_appareil(appareil_id), "ok", DELAI_CACHE_S)


def marquer_appareil_revoque(appareil_id) -> None:
    cache.set(_cle_appareil(appareil_id), "revoque", int(DUREE_REFRESH.total_seconds()))


def etat_utilisateur(uid: str) -> dict | None:
    etat = cache.get(_cle_utilisateur(uid))
    if etat is None:
        ligne = (
            User.objects.filter(pk=uid)
            .values("token_version", "role", "status", "suspended_until")
            .first()
        )
        if ligne is None:
            return None
        utilisateur = User(**ligne)
        etat = {
            "ver": ligne["token_version"],
            "role": ligne["role"],
            "actif": utilisateur.is_active,
        }
        cache.set(_cle_utilisateur(uid), etat, DELAI_CACHE_S)
    return etat


def _appareil_actif(did: str) -> bool:
    etat = cache.get(_cle_appareil(did))
    if etat is None:
        ligne = Device.objects.filter(pk=did).values("revoked_at").first()
        etat = "ok" if ligne and ligne["revoked_at"] is None else "revoque"
        cache.set(_cle_appareil(did), etat, DELAI_CACHE_S)
    return etat == "ok"


# --- Jeton d'accès ---
def emettre_acces(utilisateur: User, appareil: Device) -> str:
    maintenant = timezone.now()
    charge = {
        "iss": ISSUER,
        "aud": utilisateur.role,
        "sub": str(utilisateur.pk),
        "did": str(appareil.pk),
        "ver": utilisateur.token_version,
        "iat": int(maintenant.timestamp()),
        "exp": int((maintenant + DUREE_ACCES).timestamp()),
    }
    return jwt.encode(charge, settings.JWT_SIGNING_KEY, algorithm="HS256")


def verifier_acces(jeton: str) -> Identite:
    """Valide signature, durée, audience, version de sécurité, appareil et état du compte."""
    try:
        charge = jwt.decode(
            jeton,
            settings.JWT_SIGNING_KEY,
            algorithms=["HS256"],
            audience=list(AUDIENCES),
            issuer=ISSUER,
            options={"require": ["exp", "iat", "sub", "aud", "did", "ver", "iss"]},
        )
    except jwt.PyJWTError as erreur:
        raise _non_valide() from erreur
    etat = etat_utilisateur(charge["sub"])
    if etat is None or etat["ver"] != charge["ver"] or not _appareil_actif(charge["did"]):
        raise _non_valide()
    if etat["role"] != charge["aud"]:
        raise ErreurMetier("wrong_audience", "Ce jeton n'ouvre pas cet espace.", statut=403)
    if not etat["actif"]:
        raise ErreurMetier("account_suspended", "Ton compte est suspendu.", statut=403)
    return Identite(utilisateur_id=charge["sub"], appareil_id=charge["did"], role=etat["role"])


# --- Jeton de rafraîchissement ---
def _fernet() -> Fernet:
    cle = hashlib.sha256(f"{settings.JWT_SIGNING_KEY}|grace".encode()).digest()
    return Fernet(base64.urlsafe_b64encode(cle))


def nouveau_refresh() -> tuple[str, str]:
    brut = secrets.token_urlsafe(48)
    return brut, empreinte(brut)


def emettre_paire(utilisateur: User, appareil: Device, refresh: str) -> Paire:
    return Paire(
        acces=emettre_acces(utilisateur, appareil),
        refresh=refresh,
        expire_dans_s=int(DUREE_ACCES.total_seconds()),
    )


def _garder_pour_la_grace(ancienne_empreinte: str, nouveau_refresh_brut: str) -> None:
    jeton = _fernet().encrypt(nouveau_refresh_brut.encode()).decode()
    redis_file.client().set(f"refresh:grace:{ancienne_empreinte}", jeton, ex=GRACE_S)


def _rejouer_dans_la_grace(ancienne_empreinte: str) -> str | None:
    valeur = redis_file.client().get(f"refresh:grace:{ancienne_empreinte}")
    if not valeur:
        return None
    try:
        return _fernet().decrypt(valeur.encode()).decode()
    except InvalidToken:
        return None


def echanger_refresh(refresh: str, installation_id: str | None, ip: str | None = None) -> Paire:
    """Rotation du jeton de rafraîchissement ; détecte le vol (rejeu d'un ancien jeton après la grâce)."""
    if not refresh or len(refresh) > 200:
        raise _non_valide()
    hache = empreinte(refresh)
    maintenant = timezone.now()
    with transaction.atomic():
        appareil = (
            Device.objects.select_for_update()
            .select_related("user")
            .filter(refresh_hash=hache)
            .first()
        )
        if appareil is not None:
            if appareil.revoked_at or appareil.refresh_expires_at <= maintenant:
                raise _non_valide()
            if installation_id and appareil.installation_id != installation_id:
                raise _non_valide()
            if not appareil.user.is_active or appareil.user.role not in AUDIENCES:
                raise _non_valide()
            nouveau, nouvelle_empreinte = nouveau_refresh()
            appareil.prev_refresh_hash = hache
            appareil.refresh_hash = nouvelle_empreinte
            appareil.refresh_expires_at = maintenant + DUREE_REFRESH
            appareil.rotated_at = maintenant
            appareil.last_seen_at = maintenant
            appareil.last_ip = ip or appareil.last_ip
            appareil.save(
                update_fields=[
                    "prev_refresh_hash", "refresh_hash", "refresh_expires_at", "rotated_at", "last_seen_at", "last_ip",
                ]
            )  # fmt: skip
            _garder_pour_la_grace(hache, nouveau)
            return emettre_paire(appareil.user, appareil, nouveau)

        ancien = (
            Device.objects.select_for_update()
            .select_related("user")
            .filter(prev_refresh_hash=hache)
            .first()
        )
        if ancien is None or ancien.revoked_at:
            raise _non_valide()
        dans_la_grace = (
            ancien.rotated_at and (maintenant - ancien.rotated_at).total_seconds() <= GRACE_S
        )
        if dans_la_grace:
            rejoue = _rejouer_dans_la_grace(hache)
            if rejoue is None:
                raise _non_valide()  # grâce expirée côté Redis : on refuse sans révoquer
            return emettre_paire(ancien.user, ancien, rejoue)
        revoquer_appareil(ancien, raison="refresh_reutilise")
    raise _non_valide()


def revoquer_appareil(appareil: Device, *, raison: str = "revocation") -> None:
    """Invalide un appareil : jetons de rafraîchissement effacés, accès refusés dès la prochaine requête."""
    appareil.revoked_at = timezone.now()
    appareil.refresh_hash = None
    appareil.prev_refresh_hash = None
    appareil.push_token = None
    appareil.save(update_fields=["revoked_at", "refresh_hash", "prev_refresh_hash", "push_token"])
    marquer_appareil_revoque(appareil.pk)
    audit.enregistrer(
        "auth.appareil_revoque", acteur=appareil.user, cible=appareil, metadata={"raison": raison}
    )
