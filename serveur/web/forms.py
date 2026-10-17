"""Formulaires du site (validation de forme seulement ; les règles métier sont dans les services)."""

from django import forms

from apps.accounts.enums import Occupation

_OCCUPATIONS = [("", "Je préfère ne pas répondre"), *Occupation.choices]


class _Base(forms.Form):
    """Applique la classe CSS des champs à tous les widgets ; préfixe +229 sur les numéros, cases sur les codes."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for nom, champ in self.fields.items():
            if not isinstance(champ.widget, (forms.HiddenInput, forms.CheckboxInput)):
                champ.widget.attrs.setdefault("class", "champ__saisie")
            if nom == "phone":
                champ.prefixe = "+229"  # lu par composants/champ.html (plan v2, W8)
            if nom == "code":
                champ.widget.attrs["class"] = "champ__saisie champ__saisie--code"


class Telephone(_Base):
    phone = forms.CharField(
        label="Numéro de téléphone",
        max_length=40,
        widget=forms.TextInput(
            attrs={"inputmode": "tel", "autocomplete": "tel", "placeholder": "97 12 34 56"}
        ),
    )
    captcha = forms.CharField(required=False, widget=forms.HiddenInput)


class Code(_Base):
    code = forms.CharField(
        label="Code reçu par SMS",
        max_length=6,
        min_length=6,
        widget=forms.TextInput(attrs={"inputmode": "numeric", "autocomplete": "one-time-code"}),
    )


class Profil(_Base):
    full_name = forms.CharField(
        label="Nom complet",
        max_length=120,
        widget=forms.TextInput(attrs={"autocomplete": "name", "placeholder": "Awa Bio"}),
    )
    occupation = forms.ChoiceField(label="Tu es", choices=_OCCUPATIONS, required=False)
    password = forms.CharField(
        label="Mot de passe",
        widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}),
        strip=False,
        max_length=128,
    )
    terms_accepted = forms.BooleanField(
        label="J'accepte les conditions d'utilisation et la politique de confidentialité",
        required=False,
    )


class NouveauMotDePasse(_Base):
    password = forms.CharField(
        label="Nouveau mot de passe",
        widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}),
        strip=False,
        max_length=128,
    )


class Connexion(_Base):
    phone = forms.CharField(
        label="Numéro de téléphone",
        max_length=40,
        widget=forms.TextInput(attrs={"inputmode": "tel", "autocomplete": "tel"}),
    )
    password = forms.CharField(
        label="Mot de passe",
        widget=forms.PasswordInput(attrs={"autocomplete": "current-password"}),
        strip=False,
        max_length=128,
    )
    # ADR 0005 : décochée par défaut (ordinateurs partagés, cybercafés) ; cochée, la session dure 30 jours.
    se_souvenir = forms.BooleanField(label="Se souvenir de moi pendant 30 jours", required=False)


class ChangementNom(_Base):
    full_name = forms.CharField(label="Nom complet", max_length=120)
    occupation = forms.ChoiceField(label="Tu es", choices=_OCCUPATIONS, required=False)


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
    phone = forms.CharField(
        label="Nouveau numéro de téléphone",
        max_length=40,
        widget=forms.TextInput(
            attrs={"inputmode": "tel", "autocomplete": "tel", "placeholder": "97 12 34 56"}
        ),
    )
    captcha = forms.CharField(required=False, widget=forms.HiddenInput)


class ChangementNumeroCode(_Base):
    code = forms.CharField(
        label="Code reçu sur le nouveau numéro",
        max_length=6,
        min_length=6,
        widget=forms.TextInput(attrs={"inputmode": "numeric", "autocomplete": "one-time-code"}),
    )
    password = forms.CharField(
        label="Mot de passe actuel",
        widget=forms.PasswordInput(attrs={"autocomplete": "current-password"}),
        strip=False,
        max_length=128,
    )
