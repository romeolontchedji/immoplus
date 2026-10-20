"""Pages d'authentification et d'espace compte du site (adaptateurs : aucune règle métier ici).

Sans code SMS (ADR 0009) : inscription sur une page, clé de secours affichée une fois, mot de passe oublié par
e-mail, par clé de secours ou par l'équipe, activation des gérants par lien.
"""

from functools import wraps

from django.conf import settings
from django.contrib.auth import login, logout, update_session_auth_hash
from django.shortcuts import redirect, render
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from apps.accounts.services import administration, appareils, authentification, compte, inscription
from apps.core.errors import ErreurMetier
from apps.core.http import ip_client, user_agent
from apps.core.providers import captcha

from . import forms


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


def _exiger_captcha(request, jeton: str | None) -> None:
    """Turnstile (Cloudflare) sur l'inscription et le mot de passe oublié du site (ADR 0009)."""
    if not captcha.fournisseur().verifier(jeton, ip_client(request)):
        raise ErreurMetier("captcha_required", "Confirme que tu n'es pas un robot, puis réessaie.")


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
    if request.method == "GET" and "captcha" in form.fields and settings.CAPTCHA_PROVIDER == "fake":
        form.fields["captcha"].initial = "captcha-ok"
    return render(request, gabarit, contexte)


FORMULAIRE = "web/auth/formulaire.html"


# --------------------------------------------------------------- connexion
def connexion(request):
    if request.user.is_authenticated:
        return redirect("/compte")
    form = forms.Connexion(request.POST or None)
    if request.method == "POST" and form.is_valid():
        try:
            utilisateur = authentification.authentifier(
                form.cleaned_data["username"],
                form.cleaned_data["password"],
                ip_client(request) or "web",
            )
        except ErreurMetier as erreur:
            _signaler(form, erreur)
        else:
            _ouvrir_session(request, utilisateur, se_souvenir=form.cleaned_data["se_souvenir"])
            return redirect(_suite(request))
    message = (
        "Ton mot de passe a été changé : connecte-toi." if request.GET.get("reinitialise") else None
    )
    return _page(request, FORMULAIRE, form, "Connexion", bouton="Se connecter", suite=request.GET.get("next", ""),
                 message_succes=message,
                 liens=[("/inscription", "Créer un compte"), ("/mot-de-passe-oublie", "Mot de passe oublié")])  # fmt: skip


@require_POST
def deconnexion(request):
    logout(request)
    return redirect("/")


# --------------------------------------------------------------- inscription
def inscription_page(request):
    if request.user.is_authenticated:
        return redirect("/compte")
    form = forms.Inscription(request.POST or None)
    if request.method == "POST" and form.is_valid():
        d = form.cleaned_data
        try:
            _exiger_captcha(request, d["captcha"])
            utilisateur, cle = inscription.inscrire_client(
                nom_utilisateur=d["username"], prenom=d["first_name"], nom=d["last_name"],
                telephone=d["phone"], mot_de_passe=d["password"], cgu_acceptees=d["terms_accepted"],
                occupation=d["occupation"] or None, ip=ip_client(request), user_agent=user_agent(request),
            )  # fmt: skip
        except ErreurMetier as erreur:
            _signaler(form, erreur)
        else:
            _ouvrir_session(request, utilisateur)
            request.session["cle_de_secours"] = cle  # affichée une seule fois, puis effacée
            return redirect("/compte/cle-de-secours")
    return _page(request, FORMULAIRE, form, "Créer un compte", bouton="Créer mon compte", captcha_requis=True,
                 sous_titre="Sans code par SMS : ton nom d'utilisateur et ton mot de passe suffisent.",
                 liens=[("/connexion", "J'ai déjà un compte")])  # fmt: skip


@connecte_obligatoire
def cle_de_secours(request):
    """Affiche la clé de secours une seule fois, après l'inscription, l'activation ou une régénération."""
    cle = request.session.get("cle_de_secours")
    if not cle:
        return redirect("/compte")
    form = forms.CleNotee(
        request.POST if request.method == "POST" else None
    )  # case non cochée : POST vide
    if request.method == "POST" and form.is_valid():
        request.session.pop("cle_de_secours", None)
        return redirect("/compte/profil?cle=1#securite")
    return _page(request, FORMULAIRE, form, "Ta clé de secours", bouton="J'ai gardé ma clé, continuer",
                 encart="web/auth/encart-cle.html", cle=cle,
                 sous_titre="Elle te permet de choisir un nouveau mot de passe si tu l'oublies. "
                            "Elle ne sera plus jamais affichée.")  # fmt: skip


# --------------------------------------------------------------- mot de passe oublié
def oubli(request):
    """Mot de passe oublié : d'abord le lien par e-mail, puis la clé de secours, enfin l'équipe."""
    form = forms.LienParEmail(request.POST or None)
    envoye = False
    if request.method == "POST" and form.is_valid():
        try:
            _exiger_captcha(request, form.cleaned_data["captcha"])
            inscription.demander_lien_par_email(
                form.cleaned_data["identifier"], ip=ip_client(request)
            )
        except ErreurMetier as erreur:
            _signaler(form, erreur)
        else:
            envoye = True
    return _page(request, FORMULAIRE, form, "Mot de passe oublié", bouton="Recevoir un lien par e-mail",
                 captcha_requis=True, encart="web/auth/encart-oubli.html", envoye=envoye,
                 sous_titre="Si ton compte a un e-mail confirmé, nous t'envoyons un lien valable 30 minutes.",
                 liens=[("/mot-de-passe-oublie/cle", "J'ai ma clé de secours"), ("/connexion", "Retour à la connexion")])  # fmt: skip


def oubli_cle(request):
    form = forms.CleDeSecours(request.POST or None)
    if request.method == "POST" and form.is_valid():
        d = form.cleaned_data
        try:
            utilisateur, cle = inscription.reinitialiser_par_cle(
                d["username"], d["recovery_key"], d["password"], client=ip_client(request) or "web",
                ip=ip_client(request), user_agent=user_agent(request),
            )  # fmt: skip
        except ErreurMetier as erreur:
            _signaler(form, erreur)
        else:
            _ouvrir_session(request, utilisateur)
            request.session["cle_de_secours"] = (
                cle  # l'ancienne clé a servi : la nouvelle s'affiche une fois
            )
            return redirect("/compte/cle-de-secours")
    return _page(request, FORMULAIRE, form, "Avec ta clé de secours", bouton="Changer mon mot de passe",
                 sous_titre="La clé reçue à la création de ton compte (ex. K7QM-2XPA-9RTD-H4WN).",
                 liens=[("/mot-de-passe-oublie", "Je n'ai pas ma clé")])  # fmt: skip


def nouveau_mot_de_passe(request, jeton):
    """Lien reçu par e-mail ou transmis par l'équipe (usage unique)."""
    form = forms.NouveauMotDePasse(request.POST or None)
    if request.method == "POST" and form.is_valid():
        try:
            inscription.reinitialiser_par_lien(
                jeton,
                form.cleaned_data["password"],
                ip=ip_client(request),
                user_agent=user_agent(request),
            )
        except ErreurMetier as erreur:
            _signaler(form, erreur)
        else:
            return redirect("/connexion?reinitialise=1")
    return _page(request, FORMULAIRE, form, "Nouveau mot de passe", bouton="Enregistrer",
                 liens=[("/mot-de-passe-oublie", "Demander un nouveau lien")])  # fmt: skip


def activer_gerant(request, jeton):
    """Lien d'activation transmis par l'équipe : le gérant choisit son nom d'utilisateur et son mot de passe."""
    form = forms.Activation(request.POST or None)
    if request.method == "POST" and form.is_valid():
        try:
            gerant, cle = administration.activer_gerant(
                jeton, nom_utilisateur=form.cleaned_data["username"],
                mot_de_passe=form.cleaned_data["password"], ip=ip_client(request),
            )  # fmt: skip
        except ErreurMetier as erreur:
            _signaler(form, erreur)
        else:
            _ouvrir_session(request, gerant)
            request.session["cle_de_secours"] = cle
            return redirect("/compte/cle-de-secours")
    return _page(request, FORMULAIRE, form, "Active ton compte gérant", bouton="Activer mon compte",
                 sous_titre="Choisis le nom d'utilisateur et le mot de passe avec lesquels tu te connecteras.")  # fmt: skip


@connecte_obligatoire
def confirmer_email(request, jeton):
    try:
        compte.confirmer_email(jeton)
    except ErreurMetier as erreur:
        return redirect(f"/compte/profil?email=erreur&code={erreur.code}#securite")
    return redirect("/compte/profil?email=confirme#securite")


# --------------------------------------------------------------- espace compte
@connecte_obligatoire
def espace_compte(request):
    """Tableau de bord du locataire ; ses informations personnelles sont dans « Mon profil » (plan v3, E1)."""
    u = request.user
    if u.role != "client":
        return redirect("/compte/profil" + (f"?{request.GET.urlencode()}" if request.GET else ""))
    from apps.chat import selectors as chat_selectors
    from apps.listings import selectors as listing_selectors
    from apps.listings.services import types as types_chambre
    from apps.notifications import selectors as notif_selectors

    favoris = listing_selectors.favoris_de(u.pk)
    alertes = listing_selectors.alertes_de(u.pk)
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
            "titre": "Tableau de bord",
            "total_favoris": len(favoris),
            "total_alertes": sum(1 for a in alertes if a.is_active),
            "non_lus": chat_selectors.total_non_lus(u.pk, u.role),
            "notifs_non_lues": notif_selectors.non_lues(u.pk),
            "alertes_actives": alertes_actives,
            "derniers_favoris": favoris[:3],
            "consultees": listing_selectors.cartes_visibles(request.session.get("consultees", []))[
                :3
            ],
        },
    )


@connecte_obligatoire
def mon_profil(request):
    """Mon profil : prénom et nom, numéro, e-mail, clé de secours, mot de passe, suppression (ADR 0009)."""
    u = request.user
    action = request.POST.get("action") if request.method == "POST" else None

    def lie(nom, classe, **kw):
        return classe(request.POST if action == nom else None, **kw)

    formulaires = {
        "nom": lie("nom", forms.ChangementNom, initial={"first_name": u.first_name, "last_name": u.last_name,
                                                       "occupation": u.occupation or ""}),
        "numero": lie("numero", forms.ChangementNumero),
        "email": lie("email", forms.AjoutEmail),
        "cle": lie("cle", forms.MotDePasseActuel),
        "mot-de-passe": lie("mot-de-passe", forms.ChangementMotDePasse),
        "suppression": lie("suppression", forms.Suppression),
    }  # fmt: skip
    messages_get = {
        "email": {"confirme": "Ton adresse e-mail est confirmée.",
                  "erreur": "Ce lien de confirmation n'est plus valable : ajoute ton e-mail à nouveau."},
        "cle": {"1": "Clé de secours gardée. Pense aussi à ajouter un e-mail."},
    }  # fmt: skip
    message = next(
        (messages_get[c].get(request.GET[c]) for c in messages_get if request.GET.get(c)), None
    )
    form = formulaires.get(action)
    if form is not None and form.is_valid():
        d = form.cleaned_data
        try:
            if action == "nom":
                compte.modifier_profil(
                    u,
                    prenom=d["first_name"],
                    nom=d["last_name"],
                    occupation=d["occupation"] or None,
                )
                message = "Ton profil a été mis à jour."
            elif action == "numero":
                compte.changer_numero(u, d["password"], d["phone"])
                message = "Ton numéro a été changé."
            elif action == "email":
                compte.demander_ajout_email(u, d["email"])
                message = (
                    f"Un lien de confirmation a été envoyé à {d['email']} (valable 24 heures)."
                )
            elif action == "cle":
                request.session["cle_de_secours"] = compte.regenerer_cle_de_secours(
                    u, d["password"]
                )
                return redirect("/compte/cle-de-secours")
            elif action == "mot-de-passe":
                compte.changer_mot_de_passe(u, d["current_password"], d["new_password"])
                update_session_auth_hash(
                    request, u
                )  # garde CETTE session ouverte ; les autres tombent
                message = "Ton mot de passe a été changé. Les autres appareils sont déconnectés."
            elif action == "suppression":
                compte.supprimer(u, d["password"])
                logout(request)
                return redirect("/?compte_supprime=1")
        except ErreurMetier as erreur:
            _signaler(form, erreur)
    return render(
        request,
        "web/auth/profil.html",
        {"u": u, "titre": "Mon profil", "message": message, **{k.replace("-", "_"): f for k, f in formulaires.items()},
         "numero_actuel": _lisible((u.phone_e164 or "").removeprefix("+229"))},
    )  # fmt: skip


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
