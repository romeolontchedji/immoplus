"""Formulaires du site (validation de forme seulement ; les règles métier sont dans les services)."""

from django import forms

from apps.accounts.enums import Occupation

_OCCUPATIONS = [("", "Je préfère ne pas répondre"), *Occupation.choices]


class _Base(forms.Form):
    """Applique la classe CSS des champs à tous les widgets ; préfixe +229 sur les numéros."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for nom, champ in self.fields.items():
            if not isinstance(champ.widget, (forms.HiddenInput, forms.CheckboxInput)):
                champ.widget.attrs.setdefault("class", "champ__saisie")
            if nom == "phone":
                champ.prefixe = "+229"  # lu par composants/champ.html (plan v2, W8)


_MOT_DE_PASSE_NOUVEAU = {
    "widget": forms.PasswordInput(attrs={"autocomplete": "new-password"}),
    "strip": False,
    "max_length": 128,
    "help_text": "10 caractères au moins, différent de ton nom.",
}


def _nom_utilisateur(label: str = "Nom d'utilisateur", **attrs) -> forms.CharField:
    return forms.CharField(
        label=label,
        max_length=40,
        widget=forms.TextInput(
            attrs={
                "autocomplete": "username",
                "autocapitalize": "none",
                "spellcheck": "false",
                **attrs,
            }
        ),
    )


class Inscription(_Base):
    """Une seule page, sans code (ADR 0009)."""

    first_name = forms.CharField(
        label="Prénom", max_length=60, widget=forms.TextInput(attrs={"autocomplete": "given-name"})
    )
    last_name = forms.CharField(
        label="Nom", max_length=60, widget=forms.TextInput(attrs={"autocomplete": "family-name"})
    )
    username = _nom_utilisateur(placeholder="awa.bio")
    phone = forms.CharField(
        label="Numéro de téléphone",
        max_length=40,
        widget=forms.TextInput(
            attrs={"inputmode": "tel", "autocomplete": "tel", "placeholder": "97 12 34 56"}
        ),
    )
    occupation = forms.ChoiceField(label="Tu es", choices=_OCCUPATIONS, required=False)
    password = forms.CharField(label="Mot de passe", **_MOT_DE_PASSE_NOUVEAU)
    terms_accepted = forms.BooleanField(
        label="J'accepte les conditions d'utilisation et la politique de confidentialité",
        required=False,
    )
    captcha = forms.CharField(required=False, widget=forms.HiddenInput)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields[
            "username"
        ].help_text = "3 à 30 caractères : lettres, chiffres, point ou tiret bas."


class CleNotee(_Base):
    confirme = forms.BooleanField(
        label="J'ai noté ma clé de secours (ou fait une capture d'écran)",
        error_messages={
            "required": "Garde ta clé avant de continuer : elle ne sera plus affichée."
        },
    )


class NouveauMotDePasse(_Base):
    password = forms.CharField(label="Nouveau mot de passe", **_MOT_DE_PASSE_NOUVEAU)


class LienParEmail(_Base):
    identifier = forms.CharField(
        label="Nom d'utilisateur ou e-mail",
        max_length=254,
        widget=forms.TextInput(attrs={"autocomplete": "username", "autocapitalize": "none"}),
    )
    captcha = forms.CharField(required=False, widget=forms.HiddenInput)


class CleDeSecours(_Base):
    username = _nom_utilisateur()
    recovery_key = forms.CharField(
        label="Clé de secours",
        max_length=40,
        widget=forms.TextInput(
            attrs={
                "autocomplete": "off",
                "autocapitalize": "characters",
                "placeholder": "K7QM-2XPA-9RTD-H4WN",
            }
        ),
    )
    password = forms.CharField(label="Nouveau mot de passe", **_MOT_DE_PASSE_NOUVEAU)


class Activation(_Base):
    """Gérant : choisit son nom d'utilisateur et son mot de passe depuis le lien de l'équipe (ADR 0009)."""

    username = _nom_utilisateur(placeholder="kofi.immo")
    password = forms.CharField(label="Mot de passe", **_MOT_DE_PASSE_NOUVEAU)


class Connexion(_Base):
    username = _nom_utilisateur()
    password = forms.CharField(
        label="Mot de passe",
        widget=forms.PasswordInput(attrs={"autocomplete": "current-password"}),
        strip=False,
        max_length=128,
    )
    # ADR 0005 : décochée par défaut (ordinateurs partagés, cybercafés) ; cochée, la session dure 30 jours.
    se_souvenir = forms.BooleanField(label="Se souvenir de moi pendant 30 jours", required=False)


class ChangementNom(_Base):
    first_name = forms.CharField(label="Prénom", max_length=60)
    last_name = forms.CharField(label="Nom", max_length=60)
    occupation = forms.ChoiceField(label="Tu es", choices=_OCCUPATIONS, required=False)


class AjoutEmail(_Base):
    email = forms.EmailField(
        label="Adresse e-mail",
        max_length=254,
        widget=forms.EmailInput(attrs={"autocomplete": "email", "placeholder": "awa@exemple.com"}),
    )


class MotDePasseActuel(_Base):
    password = forms.CharField(
        label="Ton mot de passe actuel",
        widget=forms.PasswordInput(attrs={"autocomplete": "current-password"}),
        strip=False,
        max_length=128,
    )


class ChangementMotDePasse(_Base):
    current_password = forms.CharField(
        label="Mot de passe actuel", widget=forms.PasswordInput, strip=False, max_length=128
    )
    new_password = forms.CharField(
        label="Nouveau mot de passe",
        widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}),
        strip=False,
        max_length=128,
    )
    confirmation = forms.CharField(
        label="Répète le nouveau mot de passe",
        widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}),
        strip=False,
        max_length=128,
    )

    def clean(self):
        donnees = super().clean()
        if donnees.get("new_password") and donnees.get("confirmation") != donnees.get(
            "new_password"
        ):
            self.add_error("confirmation", "Les deux mots de passe ne correspondent pas.")
        return donnees


class Suppression(_Base):
    password = forms.CharField(
        label="Confirme avec ton mot de passe",
        widget=forms.PasswordInput,
        strip=False,
        max_length=128,
    )


class Preferences(_Base):
    """Cases à cocher : pour chaque catégorie, recevoir une notification et/ou un aperçu."""

    CATEGORIES = (
        ("messages", "Messages"),
        ("alertes", "Alertes"),
        ("rappels", "Rappels"),
    )

    def __init__(self, *args, valeurs=None, **kwargs):
        valeurs = valeurs or {}
        super().__init__(*args, **kwargs)
        for categorie, libelle in self.CATEGORIES:
            reglage = valeurs.get(categorie) or {}
            for cle, sous_libelle in (
                ("push", "Recevoir une notification"),
                ("apercu", "Afficher un aperçu"),
            ):
                self.fields[f"{categorie}_{cle}"] = forms.BooleanField(
                    label=f"{libelle} — {sous_libelle}",
                    required=False,
                    initial=bool(reglage.get(cle, True)),
                )

    def vers_valeurs(self) -> dict:
        donnees = self.cleaned_data
        return {
            categorie: {
                "push": donnees[f"{categorie}_push"],
                "apercu": donnees[f"{categorie}_apercu"],
            }
            for categorie, _ in self.CATEGORIES
        }


class ChangementNumero(_Base):
    """Sans code (ADR 0009) : le mot de passe actuel suffit."""

    phone = forms.CharField(
        label="Nouveau numéro de téléphone",
        max_length=40,
        widget=forms.TextInput(
            attrs={"inputmode": "tel", "autocomplete": "tel", "placeholder": "97 12 34 56"}
        ),
    )
    password = forms.CharField(
        label="Mot de passe actuel",
        widget=forms.PasswordInput(attrs={"autocomplete": "current-password"}),
        strip=False,
        max_length=128,
    )
