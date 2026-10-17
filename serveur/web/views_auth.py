"""Pages d'authentification et d'espace compte du site (adaptateurs : aucune règle métier ici)."""

from functools import wraps

from django.conf import settings
from django.contrib.auth import login, logout, update_session_auth_hash
from django.shortcuts import redirect, render
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from apps.accounts.services import appareils, authentification, compte, inscription, otp
from apps.core.errors import ErreurMetier
from apps.core.http import ip_client, user_agent

from . import forms


def _contexte_otp(request, captcha: str | None) -> otp.Contexte:
    return otp.Contexte(ip=ip_client(request), jeton_captcha=captcha, surface="web")


def _signaler(form, erreur: ErreurMetier) -> None:
    """Affiche une erreur métier dans le formulaire (champ concerné, sinon erreur générale)."""
    rattachee = False
    for champ, messages in erreur.champs.items():
        cible = champ if champ in form.fields else None
        for m in messages:
            form.add_error(cible, erreur.message if cible is None else m)
            rattachee = True
    if not rattachee:
        form.add_error(None, erreur.message)


DUREE_SE_SOUVENIR_S = 30 * 24 * 60 * 60


def _ouvrir_session(request, utilisateur, *, se_souvenir: bool = True) -> None:
    """Sans « se souvenir de moi », la session s'arrête à la fermeture du navigateur (ADR 0005)."""
    login(request, utilisateur, backend="django.contrib.auth.backends.ModelBackend")
    request.session["tv"] = utilisateur.token_version
    request.session.set_expiry(DUREE_SE_SOUVENIR_S if se_souvenir else 0)


def connecte_obligatoire(vue):
    @wraps(vue)
    def enveloppe(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect(f"/connexion?next={request.path}")
        return vue(request, *args, **kwargs)

    return enveloppe


def _suite(request) -> str:
    cible = request.GET.get("next") or request.POST.get("next") or "/compte"
    sure = url_has_allowed_host_and_scheme(
        cible, allowed_hosts={request.get_host()}, require_https=request.is_secure()
    )
    return cible if sure and cible.startswith("/") and not cible.startswith("//") else "/compte"


def _page(request, gabarit: str, form, titre: str, **extra):
    contexte = {
        "form": form, "titre": titre,
        "captcha_fictif": settings.CAPTCHA_PROVIDER == "fake",
        "site_key": settings.TURNSTILE_SITE_KEY,
        **extra,
    }  # fmt: skip
    return render(request, gabarit, contexte)


# --------------------------------------------------------------- connexion
def connexion(request):
    if request.user.is_authenticated:
        return redirect("/compte")
    form = forms.Connexion(request.POST or None)
    if request.method == "POST" and form.is_valid():
        try:
            utilisateur = authentification.authentifier(
                form.cleaned_data["phone"],
                form.cleaned_data["password"],
                ip_client(request) or "web",
            )
        except ErreurMetier as erreur:
            _signaler(form, erreur)
        else:
            _ouvrir_session(request, utilisateur, se_souvenir=form.cleaned_data["se_souvenir"])
            return redirect(_suite(request))
    return _page(request, "web/auth/formulaire.html", form, "Connexion", bouton="Se connecter", suite=request.GET.get("next", ""),
                 liens=[("/inscription", "Créer un compte"), ("/mot-de-passe-oublie", "Mot de passe oublié")])  # fmt: skip


@require_POST
def deconnexion(request):
    logout(request)
    return redirect("/")


# --------------------------------------------------------------- flux OTP commun (inscription, mot de passe oublié)
def _etape_telephone(
    request, objet: str, cle: str, gabarit_titre: str, suivante: str, bouton: str, etapes=None
):
    form = forms.Telephone(request.POST or None)
    if request.method == "POST" and form.is_valid():
        try:
            otp.demander(
                form.cleaned_data["phone"],
                objet,
                _contexte_otp(request, form.cleaned_data["captcha"]),
            )
        except ErreurMetier as erreur:
            _signaler(form, erreur)
        else:
            request.session[cle] = {"phone": form.cleaned_data["phone"]}
            return redirect(suivante)
    if request.method == "GET" and settings.CAPTCHA_PROVIDER == "fake":
        form.fields["captcha"].initial = "captcha-ok"
    return _page(
        request,
        "web/auth/formulaire.html",
        form,
        gabarit_titre,
        bouton=bouton,
        captcha_requis=True,
        etapes=etapes,
        etape_actuelle=1,
    )


def _etape_code(request, objet: str, cle: str, retour: str, suivante: str, titre: str, etapes=None):
    flux = request.session.get(cle)
    if not flux:
        return redirect(retour)
    form = forms.Code(request.POST or None)
    if request.method == "POST" and form.is_valid():
        try:
            flux["otp_token"] = otp.verifier(flux["phone"], objet, form.cleaned_data["code"])
        except ErreurMetier as erreur:
            _signaler(form, erreur)
        else:
            request.session[cle] = flux
            return redirect(suivante)
    return _page(
        request,
        "web/auth/formulaire.html",
        form,
        titre,
        bouton="Vérifier",
        liens=[(retour, "Changer de numéro")],
        etapes=etapes,
        etape_actuelle=2,
    )


# --------------------------------------------------------------- inscription
ETAPES_INSCRIPTION = ["Numéro", "Code", "Profil"]
ETAPES_OUBLI = ["Numéro", "Code", "Nouveau mot de passe"]


def inscription_telephone(request):
    return _etape_telephone(
        request,
        "signup",
        "inscription",
        "Créer un compte",
        "/inscription/code",
        "Recevoir un code",
        etapes=ETAPES_INSCRIPTION,
    )


def inscription_code(request):
    return _etape_code(
        request,
        "signup",
        "inscription",
        "/inscription",
        "/inscription/profil",
        "Saisis le code reçu",
        etapes=ETAPES_INSCRIPTION,
    )


def inscription_profil(request):
    flux = request.session.get("inscription")
    if not flux or "otp_token" not in flux:
        return redirect("/inscription")
    form = forms.Profil(request.POST or None)
    if request.method == "POST" and form.is_valid():
        d = form.cleaned_data
        try:
            utilisateur = inscription.inscrire_client(
                flux["otp_token"], d["full_name"], d["password"], d["terms_accepted"],
                occupation=d["occupation"] or None,
                ip=ip_client(request), user_agent=user_agent(request),
            )  # fmt: skip
        except ErreurMetier as erreur:
            _signaler(form, erreur)
            if erreur.code in ("otp_token_invalid", "phone_already_registered"):
                request.session.pop("inscription", None)
        else:
            request.session.pop("inscription", None)
            _ouvrir_session(request, utilisateur)
            return redirect("/compte")
    return _page(
        request,
        "web/auth/formulaire.html",
        form,
        "Termine ton inscription",
        bouton="Créer mon compte",
        etapes=ETAPES_INSCRIPTION,
        etape_actuelle=3,
    )


# --------------------------------------------------------------- mot de passe oublié
def oubli_telephone(request):
    return _etape_telephone(
        request,
        "reset_password",
        "oubli",
        "Mot de passe oublié",
        "/mot-de-passe-oublie/code",
        "Recevoir un code",
        etapes=ETAPES_OUBLI,
    )


def oubli_code(request):
    return _etape_code(
        request,
        "reset_password",
        "oubli",
        "/mot-de-passe-oublie",
        "/mot-de-passe-oublie/nouveau",
        "Saisis le code reçu",
        etapes=ETAPES_OUBLI,
    )


def oubli_nouveau(request):
    flux = request.session.get("oubli")
    if not flux or "otp_token" not in flux:
        return redirect("/mot-de-passe-oublie")
    form = forms.NouveauMotDePasse(request.POST or None)
    if request.method == "POST" and form.is_valid():
        try:
            inscription.reinitialiser_mot_de_passe(
                flux["otp_token"],
                form.cleaned_data["password"],
                ip=ip_client(request),
                user_agent=user_agent(request),
            )
        except ErreurMetier as erreur:
            _signaler(form, erreur)
        else:
            request.session.pop("oubli", None)
            return redirect("/connexion?reinitialise=1")
    return _page(
        request,
        "web/auth/formulaire.html",
        form,
        "Nouveau mot de passe",
        bouton="Enregistrer",
        etapes=ETAPES_OUBLI,
        etape_actuelle=3,
    )


# --------------------------------------------------------------- espace compte
@connecte_obligatoire
def espace_compte(request):
    u = request.user
    nom = forms.ChangementNom(
        request.POST if request.POST.get("action") == "nom" else None,
        initial={"full_name": u.full_name, "occupation": u.occupation or ""},
    )
    mdp = forms.ChangementMotDePasse(
        request.POST if request.POST.get("action") == "mot-de-passe" else None
    )
    suppression = forms.Suppression(
        request.POST if request.POST.get("action") == "suppression" else None
    )
    message = None
    if request.method == "POST":
        action = request.POST.get("action")
        try:
            if action == "nom" and nom.is_valid():
                compte.modifier_profil(
                    u,
                    nom=nom.cleaned_data["full_name"],
                    occupation=nom.cleaned_data["occupation"] or None,
                )
                message = "Ton profil a été mis à jour."
            elif action == "mot-de-passe" and mdp.is_valid():
                compte.changer_mot_de_passe(
                    u, mdp.cleaned_data["current_password"], mdp.cleaned_data["new_password"]
                )
                update_session_auth_hash(
                    request, u
                )  # garde CETTE session ouverte ; les autres tombent
                message = "Ton mot de passe a été changé. Les autres appareils sont déconnectés."
            elif action == "suppression" and suppression.is_valid():
                compte.supprimer(u, suppression.cleaned_data["password"])
                logout(request)
                return redirect("/?compte_supprime=1")
        except ErreurMetier as erreur:
            _signaler(
                {"nom": nom, "mot-de-passe": mdp, "suppression": suppression}.get(action, nom),
                erreur,
            )
    from apps.chat import selectors as chat_selectors
    from apps.listings import selectors as listing_selectors
    from apps.listings.services import types as types_chambre
    from apps.notifications import selectors as notif_selectors

    favoris = listing_selectors.favoris_de(u.pk) if u.role == "client" else []
    alertes = listing_selectors.alertes_de(u.pk) if u.role == "client" else []
    total_favoris, total_alertes = len(favoris), len(alertes)
    non_lus = chat_selectors.total_non_lus(u.pk, u.role)
    # Tableau de bord du locataire (plan v2, W6) : alertes actives résumées, derniers favoris.
    quartiers = {str(q.pk): q.name for q in listing_selectors.quartiers_actifs()}
    libelles = types_chambre.libelles()
    alertes_actives = [
        {
            "id": a.pk,
            "titre": a.label or " · ".join(
                filter(None, [", ".join(quartiers.get(str(d), "") for d in a.district_ids or []),
                              ", ".join(libelles.get(t, t) for t in a.room_types or [])])
            ) or "Toutes les chambres",
            "budget": a.max_rent,
        }
        for a in alertes if a.is_active
    ][:3]  # fmt: skip
    return render(
        request,
        "web/auth/compte.html",
        {
            "u": u,
            "nom": nom,
            "mdp": mdp,
            "suppression": suppression,
            "message": message,
            "titre": "Mon compte",
            "total_favoris": total_favoris,
            "total_alertes": total_alertes,
            "non_lus": non_lus,
            "notifs_non_lues": notif_selectors.non_lues(u.pk),
            "alertes_actives": alertes_actives,
            "derniers_favoris": favoris[:3],
            "consultees": listing_selectors.cartes_visibles(request.session.get("consultees", []))[
                :3
            ]
            if u.role == "client"
            else [],
        },
    )


@connecte_obligatoire
def mes_preferences(request):
    u = request.user
    form = forms.Preferences(
        request.POST or None, valeurs=compte.preferences(u)
    )  # fmt: skip
    message = None
    if request.method == "POST" and form.is_valid():
        try:
            compte.definir_preferences(u, form.vers_valeurs())
        except ErreurMetier as erreur:
            _signaler(form, erreur)
        else:
            message = "Tes préférences de notification sont enregistrées."
    return render(
        request,
        "web/auth/preferences.html",
        {"form": form, "message": message, "titre": "Préférences de notification"},
    )


def _navigateur(ua: str) -> str:
    """« Chrome sur Android » : lecture simple de l'en-tête User-Agent pour reconnaître la session en cours."""
    ua = ua or ""
    navigateur = next(
        (
            nom
            for cle, nom in (
                ("Edg/", "Edge"),
                ("OPR/", "Opera"),
                ("Firefox/", "Firefox"),
                ("Chrome/", "Chrome"),
                ("Safari/", "Safari"),
            )
            if cle in ua
        ),
        "Navigateur",
    )
    systeme = next(
        (
            nom
            for cle, nom in (
                ("Android", "Android"),
                ("iPhone", "iPhone"),
                ("iPad", "iPad"),
                ("Windows", "Windows"),
                ("Mac OS", "Mac"),
                ("Linux", "Linux"),
            )
            if cle in ua
        ),
        None,
    )
    return f"{navigateur} sur {systeme}" if systeme else navigateur


@connecte_obligatoire
def mes_appareils(request):
    message = None
    if request.method == "POST" and request.POST.get("action") == "partout":
        nombre = compte.deconnecter_partout(request.user)
        request.user.refresh_from_db()
        request.session["tv"] = request.user.token_version  # cette session-ci reste ouverte
        message = f"{nombre} appareil{'s' if nombre > 1 else ''} et toutes les autres sessions du site sont déconnectés."
    return render(
        request,
        "web/auth/appareils.html",
        {
            "appareils": appareils.lister(request.user),
            "session_courante": _navigateur(user_agent(request)),
            "message": message,
            "titre": "Appareils connectés",
        },
    )


@require_POST
@connecte_obligatoire
def revoquer_appareil(request, appareil_id):
    try:
        appareils.revoquer(request.user, appareil_id)
    except ErreurMetier:
        pass  # 404 silencieux : ne révèle pas l'existence d'un appareil d'autrui
    return redirect("/compte/appareils")


# --------------------------------------------------------------- changement de numéro
def _lisible(numero: str) -> str:
    """« 97777888 » → « 97 77 78 88 » (chiffres groupés par deux, comme sur une carte de visite)."""
    chiffres = "".join(c for c in str(numero) if c.isdigit())
    return " ".join(chiffres[i : i + 2] for i in range(0, len(chiffres), 2))


_LATERAL_NUMERO = {
    "accroche": "Ton numéro, c'est ta clé.",
    "sous_accroche": "Il sert à te connecter et à recevoir les codes de sécurité. Il n'est jamais montré aux gérants.",
    "promesses": [
        "Les autres appareils seront déconnectés",
        "Ton ancien numéro sera prévenu par SMS",
        "Tes favoris, alertes et messages restent",
    ],
}


@connecte_obligatoire
def changement_numero_telephone(request):
    form = forms.ChangementNumero(request.POST or None)
    if request.method == "POST" and form.is_valid():
        try:
            otp.demander(
                form.cleaned_data["phone"],
                "change_phone",
                _contexte_otp(request, form.cleaned_data["captcha"]),
            )
        except ErreurMetier as erreur:
            _signaler(form, erreur)
        else:
            request.session["changement_numero"] = {"phone": form.cleaned_data["phone"]}
            return redirect("/compte/numero/code")
    if request.method == "GET" and settings.CAPTCHA_PROVIDER == "fake":
        form.fields["captcha"].initial = "captcha-ok"
    return _page(
        request,
        "web/auth/formulaire.html",
        form,
        "Changer de numéro",
        bouton="Recevoir un code",
        captcha_requis=True,
        etapes=["Nouveau numéro", "Code et mot de passe"],
        etape_actuelle=1,
        sous_titre="On envoie un code par SMS à ton nouveau numéro pour vérifier qu'il est bien à toi.",
        **_LATERAL_NUMERO,
    )


def changement_numero_code(request):
    flux = request.session.get("changement_numero")
    if not flux or not request.user.is_authenticated:
        return redirect("/connexion?next=/compte/numero")
    form = forms.ChangementNumeroCode(request.POST or None)
    if request.method == "POST" and form.is_valid():
        try:
            jeton = otp.verifier(flux["phone"], "change_phone", form.cleaned_data["code"])
            compte.changer_numero(request.user, form.cleaned_data["password"], jeton)
        except ErreurMetier as erreur:
            _signaler(form, erreur)
        else:
            request.session.pop("changement_numero", None)
            return redirect("/compte?numero_change=1")
    return _page(
        request,
        "web/auth/formulaire.html",
        form,
        "Confirme le changement",
        bouton="Changer mon numéro",
        liens=[("/compte/numero", "Utiliser un autre numéro")],
        etapes=["Nouveau numéro", "Code et mot de passe"],
        etape_actuelle=2,
        sous_titre=f"Code envoyé au +229 {_lisible(flux['phone'])}. Confirme avec ton mot de passe actuel.",
        **_LATERAL_NUMERO,
    )
