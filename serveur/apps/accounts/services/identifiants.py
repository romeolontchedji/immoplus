"""Identifiants sans code SMS (ADR 0009) : nom d'utilisateur, clé de secours et liens signés à usage unique.

Les liens (activation d'un gérant, réinitialisation, confirmation d'un e-mail) ne demandent aucune table : ils
sont signés et contiennent une empreinte de l'état qu'ils modifient (mot de passe, version de sécurité, e-mail).
Dès qu'ils ont servi, cet état change et le lien ne vaut plus rien.
"""

import hashlib
import re
import secrets
import unicodedata

from django.contrib.auth.hashers import check_password, make_password
from django.core import signing
from django.db.models.functions import Lower
from django.utils import timezone

from apps.accounts.models import User
from apps.core.errors import ErreurMetier

MOTIF = re.compile(r"^[a-z0-9][a-z0-9._]{1,28}[a-z0-9]$")
RESERVES = frozenset(
    {
        "admin", "administrateur", "administration", "moderateur", "moderation", "support", "aide",
        "contact", "equipe", "immoplus", "immo", "pilotage", "api", "www", "root", "systeme", "securite",
        "gerant", "gerants", "locataire", "compte", "comptes", "connexion", "inscription", "null", "anonyme",
    }
)  # fmt: skip
# Alphabet sans caractères ambigus (ni 0/O, ni 1/I/L) : la clé se recopie à la main sans erreur.
ALPHABET_CLE = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"
LONGUEUR_CLE = 16

DUREES_LIENS_S = {
    "activation": 72 * 3600,  # gérant créé par l'équipe
    "reinitialisation": 30 * 60,  # lien par e-mail
    "reinitialisation_equipe": 24 * 3600,  # lien généré par l'équipe
    "email": 24 * 3600,  # confirmation d'un e-mail ajouté au profil
}
_SEL = "immoplus.identifiants"


# --------------------------------------------------------------------------- nom d'utilisateur
def normaliser_nom_utilisateur(saisie: str | None) -> str:
    """« @Aïcha.Zongo » → « aicha.zongo » : minuscules, sans accent ni « @ » initial ni espaces."""
    texte = unicodedata.normalize("NFKD", (saisie or "").strip()).encode("ascii", "ignore").decode()
    return texte.lower().lstrip("@").replace(" ", "")


def _erreur_nom(message: str) -> ErreurMetier:
    return ErreurMetier("validation_error", message, champs={"username": [message]})


def valider_nom_utilisateur(saisie: str | None, *, ignorer: User | None = None) -> str:
    """Retourne le nom normalisé s'il est valide et libre ; sinon une erreur explicite sur le champ."""
    nom = normaliser_nom_utilisateur(saisie)
    if not 3 <= len(nom) <= 30:
        raise _erreur_nom("Entre 3 et 30 caractères.")
    if not MOTIF.match(nom) or ".." in nom:
        raise _erreur_nom(
            "Lettres, chiffres, point et tiret bas seulement ; ni au début ni à la fin pour le point."
        )
    if nom.replace(".", "").replace("_", "") in RESERVES:
        raise _erreur_nom("Ce nom est réservé. Choisis-en un autre.")
    if not disponible(nom, ignorer=ignorer):
        raise ErreurMetier(
            "username_taken",
            "Ce nom d'utilisateur est déjà pris.",
            statut=409,
            champs={"username": ["Déjà pris"]},
        )
    return nom


def disponible(nom: str, *, ignorer: User | None = None) -> bool:
    requete = User.objects.annotate(n=Lower("username")).filter(n=normaliser_nom_utilisateur(nom))
    if ignorer is not None:
        requete = requete.exclude(pk=ignorer.pk)
    return not requete.exists()


def suggestions(prenom: str, nom: str, n: int = 3) -> list[str]:
    """Quelques noms libres tirés du prénom et du nom (« aicha.zongo », « aicha.zongo2 »…)."""
    base = normaliser_nom_utilisateur(f"{prenom}.{nom}")
    base = re.sub(r"[^a-z0-9._]", "", base).strip("._")[:26] or "immo"
    if len(base) < 3:
        base = (base + "immo")[:26]
    proposes, i = [], 1
    while len(proposes) < n and i < 50:
        candidat = base if i == 1 else f"{base}{i}"
        if MOTIF.match(candidat) and disponible(candidat):
            proposes.append(candidat)
        i += 1
    return proposes


# --------------------------------------------------------------------------- clé de secours
def nouvelle_cle_de_secours(utilisateur: User) -> str:
    """Génère une clé « K7QM-2XPA-9RTD-H4WN », n'en garde que l'empreinte et la retourne une seule fois."""
    brute = "".join(secrets.choice(ALPHABET_CLE) for _ in range(LONGUEUR_CLE))
    utilisateur.recovery_key_hash = make_password(brute)
    utilisateur.recovery_key_created_at = timezone.now()
    return "-".join(brute[i : i + 4] for i in range(0, LONGUEUR_CLE, 4))


def cle_correcte(utilisateur: User | None, saisie: str) -> bool:
    """Compare sans tenir compte des tirets, espaces ni majuscules ; travail identique si le compte est inconnu."""
    brute = re.sub(r"[^A-Za-z0-9]", "", saisie or "").upper()
    if utilisateur is None or not utilisateur.recovery_key_hash:
        check_password(brute, make_password(secrets.token_hex(8)))
        return False
    return check_password(brute, utilisateur.recovery_key_hash)


# --------------------------------------------------------------------------- liens signés
def _empreinte(utilisateur: User, objet: str) -> str:
    """Ce qui doit changer pour que le lien ne serve qu'une fois."""
    etat = (utilisateur.email or "") if objet == "email" else (utilisateur.password or "")
    brut = f"{utilisateur.pk}|{utilisateur.token_version}|{etat}"
    return hashlib.sha256(brut.encode()).hexdigest()[:20]


def creer_jeton(utilisateur: User, objet: str, **donnees) -> str:
    if objet not in DUREES_LIENS_S:
        raise ValueError(f"Objet de lien inconnu : {objet}")
    contenu = {"u": str(utilisateur.pk), "o": objet, "e": _empreinte(utilisateur, objet), **donnees}
    return signing.dumps(contenu, salt=f"{_SEL}.{objet}", compress=True)


def lire_jeton(jeton: str, objet: str) -> tuple[User, dict]:
    """Retourne (compte, données) si le lien est authentique, récent et pas encore utilisé."""
    invalide = ErreurMetier(
        "link_invalid", "Ce lien n'est plus valable. Demande-en un nouveau.", statut=400
    )
    try:
        contenu = signing.loads(jeton, salt=f"{_SEL}.{objet}", max_age=DUREES_LIENS_S[objet])
    except signing.BadSignature as erreur:  # SignatureExpired en hérite
        raise invalide from erreur
    utilisateur = User.objects.filter(pk=contenu.get("u"), deleted_at__isnull=True).first()
    if (
        utilisateur is None
        or contenu.get("o") != objet
        or contenu.get("e") != _empreinte(utilisateur, objet)
    ):
        raise invalide
    return utilisateur, contenu
