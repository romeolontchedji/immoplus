"""Formulaires du site (validation de forme seulement ; les règles métier sont dans les services)."""

from django import forms


class _Base(forms.Form):
    """Applique la classe CSS des champs à tous les widgets."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for champ in self.fields.values():
            if not isinstance(champ.widget, (forms.HiddenInput, forms.CheckboxInput)):
                champ.widget.attrs.setdefault("class", "champ__saisie")


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
    full_name = forms.CharField(label="Nom complet", max_length=120)
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


class ChangementNom(_Base):
    full_name = forms.CharField(label="Nom complet", max_length=120)


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
