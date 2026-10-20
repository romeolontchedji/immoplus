"""Codes à usage unique : demande, vérification, jeton OTP (CDC §5.3, EF-AUT-02).

Protections cumulées : pays autorisés, plafonds (numéro, appareil, plage /24), budget quotidien par usage avec
friction à 80 % et arrêt à 100 %, attestation d'appareil, défi anti-robot, HMAC, essais limités, réponse
identique que le numéro existe ou non. Tous les décomptes viennent de `otp_codes`, jamais du cache.
"""

import hashlib
import hmac
import logging
import math
import secrets
from dataclasses import dataclass
from datetime import timedelta

from django.conf import settings
from django.core import signing
from django.core.cache import cache
from django.db import transaction
from django.db.models import F
from django.utils import timezone

from apps.accounts import tasks
from apps.accounts.models import ROLES_CLIENTELE, OtpCode, User
from apps.accounts.phone import NumeroInvalide, normaliser
from apps.audit import services as audit
from apps.core import parametres, redis_file
from apps.core.errors import ErreurMetier
from apps.core.lookups import plage_de
from apps.core.providers import attestation as attestation_fournisseur
from apps.core.providers import captcha as captcha_fournisseur

journal = logging.getLogger(__name__)

LONGUEUR = 6
VALIDITE = timedelta(minutes=5)
ESSAIS_MAX = 5
VALIDITE_JETON_S = 600
SEUIL_FRICTION = 0.8
MARQUE_NON_ENVOYE = (
    "non-envoye"  # ligne enregistrée pour les plafonds, sans SMS (compte inexistant)
)
SEL_JETON = "immoplus.otp.jeton"


@dataclass(frozen=True)
class Contexte:
    """Ce que l'on sait du demandeur : sert aux plafonds et aux preuves anti-robot."""

    installation_id: str | None = None
    ip: str | None = None
    jeton_attestation: str | None = None
    jeton_captcha: str | None = None
    surface: str = "app"  # « app » ou « web »


def _hmac(phone: str, objet: str, code: str) -> str:
    message = f"{phone}|{objet}|{code}".encode()
    return hmac.new(settings.OTP_HMAC_KEY.encode(), message, hashlib.sha256).hexdigest()


def _generer_code() -> str:
    if settings.OTP_DEBUG_CODE:  # jamais présent en production : le démarrage échoue sinon
        return settings.OTP_DEBUG_CODE
    return f"{secrets.randbelow(10**LONGUEUR):0{LONGUEUR}d}"


def _debut_de_journee():
    local = timezone.localtime(timezone.now())
    return local.replace(hour=0, minute=0, second=0, microsecond=0)


def _normaliser(saisie: str) -> str:
    try:
        return normaliser(saisie, tuple(parametres.lire("OTP_ALLOWED_COUNTRIES")))
    except NumeroInvalide as erreur:
        raise ErreurMetier(
            "validation_error",
            "Ce numéro n'est pas valide. Utilise un numéro mobile béninois.",
            champs={"phone": [str(erreur)]},
        ) from erreur


def _envoyes_aujourdhui(objet: str) -> int:
    """Envois réels du jour pour un usage (les lignes sans SMS ne consomment pas le budget)."""
    return (
        OtpCode.objects.filter(purpose=objet, created_at__gte=_debut_de_journee())
        .exclude(provider_ref=MARQUE_NON_ENVOYE)
        .count()
    )


def _etat_budget(objet: str) -> tuple[int, int]:
    budget = int(parametres.lire("OTP_DAILY_BUDGET").get(objet, 0))
    return _envoyes_aujourdhui(objet), budget


def _alerter_budget_epuise(objet: str) -> None:
    """Une alerte par usage et par jour : journal critique et trace d'audit (le canal de notification vient en phase 7)."""
    if cache.add(f"alerte:otp-budget:{objet}:{_debut_de_journee().date()}", 1, 86400):
        journal.critical(
            "Budget OTP épuisé pour l'usage %s : demandes refusées jusqu'à demain.", objet
        )
        audit.enregistrer("otp.budget_epuise", cible_type="otp", metadata={"usage": objet})


def _retry_after(delai: timedelta | float) -> dict:
    secondes = delai.total_seconds() if isinstance(delai, timedelta) else delai
    return {"Retry-After": str(max(1, math.ceil(secondes)))}


def _moitie(n: int) -> int:
    """Plafond divisé par deux, arrondi au supérieur : 3 devient 2, jamais 1 pour un usage légitime."""
    return max(1, math.ceil(n / 2))


def _controler_plafonds(phone: str, ctx: Contexte, *, friction: bool, attestation_ok: bool) -> None:
    maintenant = timezone.now()
    reduit = friction or not attestation_ok

    dernier = OtpCode.objects.filter(phone_e164=phone).order_by("-created_at").first()
    delai = timedelta(seconds=int(parametres.lire("OTP_RESEND_DELAY_S")))
    if dernier and maintenant - dernier.created_at < delai:
        raise ErreurMetier(
            "otp_resend_too_soon",
            "Un code vient d'être envoyé. Patiente un instant avant d'en demander un autre.",
            statut=429,
            entetes=_retry_after(delai - (maintenant - dernier.created_at)),
        )

    par_heure = int(parametres.lire("OTP_PHONE_PER_HOUR"))
    par_heure = _moitie(par_heure) if friction else par_heure
    depuis = maintenant - timedelta(hours=1)
    if OtpCode.objects.filter(phone_e164=phone, created_at__gte=depuis).count() >= par_heure:
        raise ErreurMetier(
            "otp_rate_limited",
            "Trop de demandes pour ce numéro. Réessaie dans une heure.",
            statut=429,
            entetes=_retry_after(timedelta(hours=1)),
        )

    depuis_24h = maintenant - timedelta(hours=24)
    if ctx.installation_id:
        par_jour = int(parametres.lire("OTP_INSTALLATION_PER_DAY"))
        par_jour = _moitie(par_jour) if reduit else par_jour
        if (
            OtpCode.objects.filter(
                installation_id=ctx.installation_id, created_at__gte=depuis_24h
            ).count()
            >= par_jour
        ):
            raise ErreurMetier(
                "otp_rate_limited",
                "Trop de demandes depuis cet appareil. Réessaie demain.",
                statut=429,
                entetes=_retry_after(timedelta(hours=24)),
            )
    if ctx.ip:
        par_plage = int(parametres.lire("OTP_IP24_PER_DAY"))
        par_plage = _moitie(par_plage) if reduit else par_plage
        requetes = OtpCode.objects.filter(
            ip__dans_reseau=plage_de(ctx.ip), created_at__gte=depuis_24h
        )
        if requetes.count() >= par_plage:
            raise ErreurMetier(
                "otp_rate_limited",
                "Trop de demandes depuis ce réseau. Réessaie demain.",
                statut=429,
                entetes=_retry_after(timedelta(hours=24)),
            )


def _compte_a_prevenir(phone: str, objet: str) -> bool:
    """Faut-il réellement envoyer un SMS ? Jamais d'envoi vers un numéro sans compte quand l'usage en exige un."""
    utilisateur = User.objects.filter(phone_e164=phone).only("role", "status", "password").first()
    if objet == "signup":
        return True  # l'existence d'un compte n'est révélée qu'après preuve de possession (à l'inscription)
    if objet == "change_phone":
        return utilisateur is None  # le nouveau numéro doit être libre
    if objet == "reset_password":
        return bool(
            utilisateur and utilisateur.role in ROLES_CLIENTELE and utilisateur.status != "deleted"
        )
    return False


def demander(saisie: str, objet: str, ctx: Contexte) -> None:
    """Demande un OTP. Retourne toujours sans rien dire de l'existence du numéro ; lève `ErreurMetier` sinon."""
    phone = _normaliser(saisie)

    envoyes, budget = _etat_budget(objet)
    if budget <= 0 or envoyes >= budget:
        _alerter_budget_epuise(objet)
        raise ErreurMetier(
            "otp_unavailable",
            "L'envoi de codes est momentanément indisponible. Réessaie plus tard.",
            statut=503,
            entetes=_retry_after(timedelta(hours=1)),
        )
    friction = envoyes >= budget * SEUIL_FRICTION

    attestation_ok = bool(
        ctx.surface == "app"
        and attestation_fournisseur.fournisseur().verifier(
            ctx.jeton_attestation, ctx.installation_id
        )
    )
    if friction:
        if ctx.surface == "web" and not captcha_fournisseur.fournisseur().verifier(
            ctx.jeton_captcha, ctx.ip
        ):
            raise ErreurMetier(
                "captcha_required",
                "Confirme que tu n'es pas un robot pour recevoir un code.",
                statut=400,
            )
        if ctx.surface == "app" and not attestation_ok:
            raise ErreurMetier(
                "attestation_required",
                "Ton appareil n'a pas pu être vérifié. Mets l'application à jour et réessaie.",
                statut=400,
            )
    elif ctx.surface == "web" and parametres.lire("TURNSTILE_ENABLED"):
        if not captcha_fournisseur.fournisseur().verifier(ctx.jeton_captcha, ctx.ip):
            raise ErreurMetier(
                "captcha_required",
                "Confirme que tu n'es pas un robot pour recevoir un code.",
                statut=400,
            )

    _controler_plafonds(
        phone, ctx, friction=friction, attestation_ok=attestation_ok or ctx.surface == "web"
    )

    code = _generer_code()
    envoyer = _compte_a_prevenir(phone, objet)
    with transaction.atomic():
        ligne = OtpCode.objects.create(
            phone_e164=phone,
            purpose=objet,
            code_hmac=_hmac(phone, objet, code),
            expires_at=timezone.now() + VALIDITE,
            installation_id=ctx.installation_id,
            ip=ctx.ip,
            provider_ref=None if envoyer else MARQUE_NON_ENVOYE,
        )
        if envoyer:
            message = f"Immo+ : ton code est {code}. Il expire dans 5 minutes. Ne le partage avec personne."
            transaction.on_commit(lambda: tasks.envoyer_sms.delay(phone, message, str(ligne.id)))


def noter_envoi(otp_id: str, reference: str, cout_xof: int | None) -> None:
    """Enregistre la référence du message et son coût estimé (appelé par la tâche d'envoi)."""
    OtpCode.objects.filter(pk=otp_id).update(provider_ref=reference[:80], unit_cost_xof=cout_xof)


def verifier(saisie: str, objet: str, code: str) -> str:
    """Vérifie un code ; retourne un jeton OTP (10 minutes, usage unique) lié au numéro et à l'usage.

    Les écritures (essai compté, code consommé) sont validées AVANT de lever une erreur : une exception levée
    dans la transaction annulerait le décompte des essais.
    """
    phone = _normaliser(saisie)
    code = (code or "").strip()
    maintenant = timezone.now()
    with transaction.atomic():
        ligne = (
            OtpCode.objects.select_for_update()
            .filter(phone_e164=phone, purpose=objet, consumed_at__isnull=True)
            .order_by("-created_at")
            .first()
        )
        if ligne is None or ligne.expires_at <= maintenant:
            issue, essais_restants = "expire", 0
        elif ligne.attempts >= ESSAIS_MAX:
            issue, essais_restants = "verrouille", 0
        else:
            OtpCode.objects.filter(pk=ligne.pk).update(attempts=F("attempts") + 1)
            attendu = (
                _hmac(phone, objet, code) if len(code) == LONGUEUR and code.isdigit() else None
            )
            if attendu is not None and hmac.compare_digest(ligne.code_hmac, attendu):
                OtpCode.objects.filter(pk=ligne.pk).update(consumed_at=maintenant)
                issue, essais_restants = "ok", 0
            else:
                issue, essais_restants = "incorrect", ESSAIS_MAX - ligne.attempts - 1

    if issue == "expire":
        raise ErreurMetier(
            "otp_expired",
            "Ce code a expiré. Demande un nouveau code.",
            champs={"code": ["Code expiré"]},
        )
    if issue == "verrouille":
        raise ErreurMetier(
            "otp_locked",
            "Trop d'essais. Demande un nouveau code.",
            statut=429,
            champs={"code": ["Trop d'essais"]},
        )
    if issue == "incorrect":
        reste = f" Il te reste {essais_restants} essai(s)." if essais_restants > 0 else ""
        raise ErreurMetier(
            "otp_invalid", "Ce code est incorrect." + reste, champs={"code": ["Code incorrect"]}
        )
    return signing.dumps({"p": phone, "o": objet, "i": str(ligne.id)}, salt=SEL_JETON)


def consommer_jeton(jeton: str, objet: str) -> str:
    """Valide un jeton OTP (signature, durée, usage, usage unique) et retourne le numéro E.164."""
    invalide = ErreurMetier(
        "otp_token_invalid",
        "Ta vérification a expiré. Recommence en demandant un nouveau code.",
        statut=400,
    )
    try:
        contenu = signing.loads(jeton, salt=SEL_JETON, max_age=VALIDITE_JETON_S)
    except signing.BadSignature as erreur:
        raise invalide from erreur
    if contenu.get("o") != objet:
        raise invalide
    if not redis_file.client().set(
        f"otp:jeton-utilise:{contenu['i']}", 1, nx=True, ex=VALIDITE_JETON_S + 60
    ):
        raise invalide
    return contenu["p"]
