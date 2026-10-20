from django.urls import path

from . import views as v

urlpatterns = [
    path("auth/username-available", v.Disponibilite.as_view(), name="auth-username-available"),
    path("auth/register", v.Inscription.as_view(), name="auth-register"),
    path("auth/login", v.Connexion.as_view(), name="auth-login"),
    path("auth/refresh", v.Rafraichissement.as_view(), name="auth-refresh"),
    path("auth/logout", v.Deconnexion.as_view(), name="auth-logout"),
    path("auth/password/email-link", v.LienParEmail.as_view(), name="auth-password-email-link"),
    path("auth/password/recovery-key", v.CleDeSecours.as_view(), name="auth-password-recovery-key"),
    path("auth/password/change", v.ChangementMotDePasse.as_view(), name="auth-password-change"),
    path("me", v.Moi.as_view(), name="me"),
    path("me/phone/change", v.ChangementNumero.as_view(), name="me-phone-change"),
    path("me/email", v.AjoutEmail.as_view(), name="me-email"),
    path("me/recovery-key", v.NouvelleCleDeSecours.as_view(), name="me-recovery-key"),
    path("me/preferences", v.Preferences.as_view(), name="me-preferences"),
    path("devices", v.Appareils.as_view(), name="devices"),
    path("devices/current/push-token", v.JetonPush.as_view(), name="devices-push-token"),
    path("devices/<uuid:appareil_id>", v.AppareilDetail.as_view(), name="devices-detail"),
]
