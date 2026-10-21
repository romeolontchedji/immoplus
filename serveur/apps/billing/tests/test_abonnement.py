"""Abonnement prêt mais inactif (CDC §7.11) : drapeau, plan gratuit, machine à états, paiement, webhooks."""

import datetime
import json
import uuid

import pytest
from django.test import override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.services import administration
from apps.accounts.tests.fabriques import AdminFactory, GerantProfileFactory
from apps.billing import services
from apps.billing.models import Payment, Subscription
from apps.core import parametres
from apps.core.errors import ErreurMetier
from apps.core.providers.paiement import PaiementFactice
from apps.listings.tests.fabriques import DistrictFactory, donnees_annonce, gerant_verifie
from apps.listings.tests.test_annonces_pro import client_de

pytestmark = [pytest.mark.pg, pytest.mark.django_db]


@pytest.fixture
def active():
    parametres.definir("SUBSCRIPTION_ENABLED", True)
    parametres.definir(
        "PLANS",
        [
            {
                "code": "free_v1",
                "label": "Gratuit V1",
                "price": 0,
                "period_months": 1,
                "max_active_listings": None,
                "active": True,
            },
            {
                "code": "standard",
                "label": "Standard",
                "price": 2000,
                "period_months": 1,
                "max_active_listings": None,
                "active": True,
            },
        ],
    )
    yield
    parametres.definir("SUBSCRIPTION_ENABLED", False)


class TestDesactive:
    """EF-ABO-02 et 03 : rien ne change pour les gérants tant que le drapeau est faux."""

    def test_points_d_entree_en_404(self):
        g = gerant_verifie()
        c = client_de(g.user)
        for url in ("/v1/pro/plans", "/v1/pro/subscription"):
            r = c.get(url)
            assert r.status_code == 404 and r.json()["error"]["code"] == "feature_disabled"
        assert (
            APIClient().post("/v1/webhooks/payments/sandbox", {}, format="json").status_code == 404
        )

    def test_publication_libre(self):
        g = gerant_verifie()
        Subscription.objects.filter(gerant_id=g.pk).update(status="expired")
        assert services.can_publish(g.pk) is True
        r = client_de(g.user).post(
            "/v1/pro/listings", donnees_annonce(DistrictFactory()), format="json"
        )
        assert r.status_code == 201

    def test_absent_du_schema_public(self):
        schema = json.loads(open("../docs/api/openapi.json", encoding="utf-8").read())
        assert not [
            p
            for p in schema["paths"]
            if "subscription" in p or "webhooks" in p or p.endswith("/plans")
        ]


class TestPlanGratuit:
    def test_attribue_a_la_verification(self):
        g = GerantProfileFactory(verification_status="pending")
        assert not Subscription.objects.filter(gerant_id=g.pk).exists()
        administration.definir_verification(acteur=AdminFactory(), profil=g, statut="verified")
        a = Subscription.objects.get(gerant_id=g.pk)
        assert (a.plan_code, a.status) == ("free_v1", "active")

    def test_une_seule_attribution(self):
        g = gerant_verifie()
        services.attribuer_gratuit(g.pk)
        services.attribuer_gratuit(g.pk)
        assert Subscription.objects.filter(gerant_id=g.pk).exclude(status="expired").count() == 1


class TestMachineAEtats:
    @pytest.mark.parametrize(
        "depart,arrivee,permis",
        [("active", "past_due", True), ("past_due", "active", True), ("past_due", "expired", True),
         ("canceled", "expired", True), ("expired", "active", False), ("canceled", "active", False),
         ("active", "trialing", False), ("active", "expired", False)],
    )  # fmt: skip
    def test_transitions(self, depart, arrivee, permis):
        a = services.attribuer_gratuit(gerant_verifie().pk)
        Subscription.objects.filter(pk=a.pk).update(status=depart)
        a.refresh_from_db()
        if permis:
            assert services.changer_statut(a, arrivee).status == arrivee
        else:
            with pytest.raises(ErreurMetier):
                services.changer_statut(a, arrivee)

    def test_echeances_impaye_puis_expire(self, active):
        g = gerant_verifie()
        Subscription.objects.filter(gerant_id=g.pk).delete()
        passe = timezone.now() - datetime.timedelta(days=1)
        a = Subscription.objects.create(
            gerant_id=g.pk,
            plan_code="standard",
            status="active",
            current_period_start=passe - datetime.timedelta(days=30),
            current_period_end=passe,
        )
        services.echeances()
        a.refresh_from_db()
        assert a.status == "past_due" and services.can_publish(g.pk)  # grâce de 7 jours
        services.echeances(timezone.now() + datetime.timedelta(days=8))
        a.refresh_from_db()
        assert a.status == "expired"
        Subscription.objects.filter(gerant_id=g.pk).delete()
        assert not Subscription.objects.filter(gerant_id=g.pk).exists()


class TestPaiementEtWebhook:
    def _payer(self, g, cle="cle-1", telephone="+2290197111111"):
        return client_de(g.user).post(
            "/v1/pro/subscription/checkout",
            {
                "plan_code": "standard",
                "method": "mtn_momo",
                "phone": telephone,
                "idempotency_key": cle,
            },
            format="json",
        )

    def _webhook(self, reference, statut="succeeded", event="evt-1", signature=None):
        corps = json.dumps({"event_id": event, "reference": reference, "status": statut}).encode()
        return APIClient().generic(
            "POST", "/v1/webhooks/payments/sandbox", corps, content_type="application/json",
            HTTP_X_SIGNATURE=signature if signature is not None else PaiementFactice.signer(corps),
        )  # fmt: skip

    def test_parcours_complet_et_idempotence(self, active, django_capture_on_commit_callbacks):
        g = gerant_verifie()
        r = self._payer(g)
        assert r.status_code == 202 and r.json()["status"] == "pending"
        assert self._payer(g).json()["id"] == r.json()["id"]  # même clé : pas de double débit
        p = Payment.objects.get(pk=r.json()["id"])
        with django_capture_on_commit_callbacks(execute=True):
            assert self._webhook(p.provider_ref).json() == {"received": True, "duplicate": False}
        with django_capture_on_commit_callbacks(execute=True):
            assert self._webhook(p.provider_ref).json()["duplicate"] is True
        p.refresh_from_db()
        assert p.status == "succeeded" and len(p.webhook_events) == 1
        courant = services.abonnement_courant(g.pk)
        assert (courant.plan_code, courant.status) == ("standard", "active")

    def test_signature_refusee(self, active):
        g = gerant_verifie()
        p = Payment.objects.get(pk=self._payer(g).json()["id"])
        assert self._webhook(p.provider_ref, signature="faux").status_code == 400
        p.refresh_from_db()
        assert p.webhook_events == []

    def test_plan_gratuit_ne_se_paie_pas(self, active):
        g = gerant_verifie()
        r = client_de(g.user).post(
            "/v1/pro/subscription/checkout",
            {
                "plan_code": "free_v1",
                "method": "mtn_momo",
                "phone": "+2290197111111",
                "idempotency_key": str(uuid.uuid4()),
            },
            format="json",
        )
        assert r.status_code == 400

    def test_abonnement_expire_bloque_la_publication(self, active):
        """Le jour où le plan gratuit est retiré : sans abonnement vivant, plus de publication (402)."""
        parametres.definir("PLANS", [p for p in parametres.lire("PLANS") if p["code"] != "free_v1"])
        g = gerant_verifie()
        Subscription.objects.filter(gerant_id=g.pk).update(status="expired")
        r = client_de(g.user).post(
            "/v1/pro/listings", donnees_annonce(DistrictFactory()), format="json"
        )
        assert r.status_code == 402 and r.json()["error"]["code"] == "subscription_required"

    @override_settings(PAYMENT_PROVIDER="sandbox")
    def test_numero_en_echec(self, active):
        g = gerant_verifie()
        assert (
            self._payer(g, cle="cle-echec", telephone="+2290197111110").json()["status"] == "failed"
        )
