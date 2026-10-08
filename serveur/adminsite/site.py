"""Site d'administration : 2FA (TOTP) obligatoire, connexion par e-mail, titres en français."""

from django import forms
from django_otp.admin import OTPAdminSite
from django_otp.forms import OTPAuthenticationForm


class FormulaireConnexion(OTPAuthenticationForm):
    """Adresse e-mail, mot de passe et code à 6 chiffres de l'application d'authentification."""

    def __init__(self, request=None, *args, **kwargs):
        super().__init__(request, *args, **kwargs)
        self.fields["username"] = forms.CharField(
            label="Adresse e-mail",
            max_length=254,
            widget=forms.TextInput(attrs={"autofocus": True, "autocomplete": "username"}),
        )
        self.fields["otp_token"].label = "Code de vérification"
        self.fields["otp_token"].required = True
        self.fields["otp_token"].widget.attrs.update(
            {"autocomplete": "one-time-code", "inputmode": "numeric"}
        )

    def clean_otp_token(self):
        return self.cleaned_data["otp_token"]

    def _chosen_device(self, user):
        """Choisit l'appareil TOTP confirmé de l'utilisateur déjà authentifié par mot de passe.

        django-otp exige un choix explicite pour ne pas essuyer d'échecs sur les autres appareils ; ici le
        personnel n'a qu'un appareil TOTP, et la sélection se limite toujours aux appareils de CET utilisateur.
        """
        from django_otp.plugins.otp_totp.models import TOTPDevice

        return (
            super()._chosen_device(user)
            or TOTPDevice.objects.filter(user=user, confirmed=True).first()
        )


class AdminLogeo(OTPAdminSite):
    site_header = "Logeo — administration"
    site_title = "Logeo"
    index_title = "Tableau de bord"
    login_form = FormulaireConnexion
