from django.urls import path

from . import views as v

urlpatterns = [
    path("pro/plans", v.Plans.as_view(), name="pro-plans"),
    path("pro/subscription", v.Abonnement.as_view(), name="pro-subscription"),
    path("pro/subscription/checkout", v.Paiement.as_view(), name="pro-subscription-checkout"),
    path("pro/subscription/cancel", v.Annulation.as_view(), name="pro-subscription-cancel"),
    path("webhooks/payments/<slug:fournisseur>", v.Webhook.as_view(), name="payments-webhook"),
]
