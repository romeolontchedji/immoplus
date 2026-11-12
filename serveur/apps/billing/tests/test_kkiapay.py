"""Paiements par la fenêtre KKiaPay : abonnement des gérants, alertes des locataires (vérification côté serveur)."""

import secrets

import pytest
from django.test import Client, override_settings

from apps.accounts.tests.fabriques import MOT_DE_PASSE
from apps.accounts.tests.fabriques import ClientFactory as _ClientFactory
from apps.billing import services, transactions
from apps.billing.models import Subscription, Transaction
from apps.core import parametres
from apps.core.errors import ErreurMetier
from apps.listings.services import alertes
from apps.listings.tests.fabriques import DistrictFactory, gerant_verifie

pytestmark = [pytest.mark.pg, pytest.mark.django_db]


def ClientFactory(**champs):  # noqa: N802 - locataire avec e-mail confirmé (exigé pour une alerte)
    import uuid

    from django.utils import timezone

    champs.setdefault("email", f"{uuid.uuid4().hex[:10]}@exemple.bj")
    champs.setdefault("email_verified_at", timezone.now())
    return _ClientFactory(**champs)

PUBLIQUE = secrets.token_urlsafe(16)
SECRET = secrets.token_urlsafe(16)  # hash secret du webhook
CLES = {
    "KKIAPAY_WEBHOOK_SECRET": SECRET,
    "KKIAPAY_SECRET": secrets.token_urlsafe(16),
    "KKIAPAY_PUBLIC_KEY": PUBLIQUE,
    "KKIAPAY_PRIVATE_KEY": secrets.token_urlsafe(16),
}


@pytest.fixture(autouse=True)
def kkiapay(monkeypatch):
    """Clés présentes ; KKiaPay répond « réussi » pour le montant demandé, sauf instruction contraire."""
    reponse = {"status": "SUCCESS", "amount": None}
    monkeypatch.setattr(
        transactions, "_verifier", lambda ref: {**reponse, "amount": reponse["amount"] or 10**6}
    )
    with override_settings(**CLES):
        yield reponse


@pytest.fixture
def abonnement_exige():
    parametres.definir("SUBSCRIPTION_ENABLED", True)
    parametres.definir(
        "PLANS",
        [
            {"code": "free_v1", "label": "Gratuit", "price": 0, "period_months": 1, "active": True},
            {"code": "standard", "label": "Standard", "price": 2000, "period_months": 1, "active": True},
        ],
    )
    yield
    parametres.definir("SUBSCRIPTION_ENABLED", False)


@pytest.fixture
def alertes_payantes():
    parametres.definir("PAID_ALERTS_ENABLED", True)
    parametres.definir("ALERT_PRICE", 500)
    yield
    parametres.definir("PAID_ALERTS_ENABLED", False)


class TestAlertes:
    def test_sans_paiement_pas_d_alerte(self, alertes_payantes):
        u, q = ClientFactory(), DistrictFactory()
        with pytest.raises(ErreurMetier) as e:
            alertes.creer(u, {"district_ids": [str(q.pk)]})
        assert e.value.code == "payment_required" and e.value.statut == 402

    def test_gratuites_quand_le_drapeau_est_eteint(self):
        u, q = ClientFactory(), DistrictFactory()
        assert alertes.creer(u, {"district_ids": [str(q.pk)]}).pk

    def test_un_paiement_vaut_une_alerte(self, alertes_payantes):
        u, q = ClientFactory(), DistrictFactory()
        attente, _ = transactions.preparer(u, "alerte")
        assert attente.amount == 500
        transactions.confirmer(u, str(attente.pk), "tx-1")
        assert transactions.credits_alerte(u) == 1
        alertes.creer(u, {"district_ids": [str(q.pk)]})
        assert transactions.credits_alerte(u) == 0
        with pytest.raises(ErreurMetier):  # le crédit est consommé
            alertes.creer(u, {"district_ids": [str(q.pk)], "label": "deux"})

    def test_supprimer_l_alerte_ne_rend_pas_le_credit(self, alertes_payantes):
        u, q = ClientFactory(), DistrictFactory()
        attente, _ = transactions.preparer(u, "alerte")
        transactions.confirmer(u, str(attente.pk), "tx-2")
        alerte = alertes.creer(u, {"district_ids": [str(q.pk)]})
        alertes.supprimer(u, alerte.pk)
        assert transactions.credits_alerte(u) == 0


class TestConfirmation:
    def test_montant_insuffisant_refuse(self, alertes_payantes, kkiapay):
        u = ClientFactory()
        attente, _ = transactions.preparer(u, "alerte")
        kkiapay["amount"] = 100
        with pytest.raises(ErreurMetier) as e:
            transactions.confirmer(u, str(attente.pk), "tx-3")
        assert e.value.code == "payment_failed"
        assert transactions.credits_alerte(u) == 0

    def test_paiement_non_reussi_refuse(self, alertes_payantes, kkiapay):
        u = ClientFactory()
        attente, _ = transactions.preparer(u, "alerte")
        kkiapay["status"] = "FAILED"
        with pytest.raises(ErreurMetier):
            transactions.confirmer(u, str(attente.pk), "tx-4")
        attente.refresh_from_db()
        assert attente.status == "failed"

    def test_un_identifiant_kkiapay_ne_sert_qu_une_fois(self, alertes_payantes):
        u = ClientFactory()
        premiere, _ = transactions.preparer(u, "alerte")
        seconde, _ = transactions.preparer(u, "alerte")
        transactions.confirmer(u, str(premiere.pk), "tx-5")
        with pytest.raises(ErreurMetier) as e:
            transactions.confirmer(u, str(seconde.pk), "tx-5")
        assert e.value.code == "conflict"

    def test_confirmation_idempotente(self, alertes_payantes):
        u = ClientFactory()
        attente, _ = transactions.preparer(u, "alerte")
        transactions.confirmer(u, str(attente.pk), "tx-6")
        transactions.confirmer(u, str(attente.pk), "tx-6")
        assert transactions.credits_alerte(u) == 1

    def test_le_paiement_d_un_autre_compte_est_introuvable(self, alertes_payantes):
        attente, _ = transactions.preparer(ClientFactory(), "alerte")
        with pytest.raises(ErreurMetier) as e:
            transactions.confirmer(ClientFactory(), str(attente.pk), "tx-7")
        assert e.value.statut == 404

    def test_sans_cles_pas_de_paiement(self, alertes_payantes):
        with override_settings(KKIAPAY_PRIVATE_KEY="", KKIAPAY_PUBLIC_KEY="", KKIAPAY_SECRET=""):
            with pytest.raises(ErreurMetier) as e:
                transactions.preparer(ClientFactory(), "alerte")
        assert e.value.statut == 503


class TestAbonnement:
    def test_le_plan_gratuit_ne_suffit_plus(self, abonnement_exige):
        g = gerant_verifie()
        assert services.can_publish(g.pk) is False

    def test_payer_la_formule_permet_de_publier(self, abonnement_exige):
        g = gerant_verifie()
        attente, fenetre = transactions.preparer(g.user, "abonnement", "standard")
        assert fenetre["amount"] == 2000 and fenetre["key"] == PUBLIQUE
        transactions.confirmer(g.user, str(attente.pk), "tx-8")
        assert services.can_publish(g.pk) is True
        assert Subscription.objects.filter(gerant_id=g.pk, plan_code="standard", status="active").exists()

    def test_formule_gratuite_ou_inconnue_refusee(self, abonnement_exige):
        g = gerant_verifie()
        for code in ("free_v1", "inconnue"):
            with pytest.raises(ErreurMetier):
                transactions.preparer(g.user, "abonnement", code)

    def test_un_locataire_ne_paie_pas_d_abonnement(self, abonnement_exige):
        with pytest.raises(ErreurMetier):
            transactions.preparer(ClientFactory(), "abonnement", "standard")


class TestPagesWeb:
    def test_preparer_et_confirmer_par_le_navigateur(self, alertes_payantes):
        u = ClientFactory(username="payeur.test")
        c = Client()
        c.post("/connexion", {"username": "payeur.test", "password": MOT_DE_PASSE})
        r = c.post("/paiement/preparer", {"objet": "alerte"}, content_type="application/json")
        assert r.status_code == 200 and r.json()["amount"] == 500
        r = c.post(
            "/paiement/confirmer",
            {"reference": r.json()["reference"], "transaction_id": "tx-9"},
            content_type="application/json",
        )
        assert r.status_code == 200 and r.json()["status"] == "succeeded"
        assert Transaction.objects.filter(user=u, status="succeeded").count() == 1

    def test_anonyme_redirige(self):
        r = Client().post("/paiement/preparer", {}, content_type="application/json")
        assert r.status_code == 302

    def test_page_abonnement_quand_le_paiement_est_eteint(self):
        g = gerant_verifie()
        c = Client()
        c.post("/connexion", {"username": g.user.username, "password": MOT_DE_PASSE})
        r = c.get("/compte/abonnement")
        assert r.status_code == 200 and "publier est gratuit" in r.content.decode()


class TestWebhook:
    def _envoyer(self, donnees, secret=SECRET):
        import json

        entetes = {"HTTP_X_KKIAPAY_SECRET": secret} if secret else {}
        return Client().post(
            "/paiement/webhook/kkiapay", json.dumps(donnees), content_type="application/json", **entetes
        )

    def test_secret_faux_refuse(self, alertes_payantes):
        r = self._envoyer({"transactionId": "w-1", "event": "transaction.success"}, secret="faux")
        assert r.status_code == 403
        assert self._envoyer({"transactionId": "w-1"}, secret="").status_code == 403

    def test_le_webhook_valide_un_paiement_dont_le_navigateur_s_est_ferme(self, alertes_payantes):
        u = ClientFactory()
        attente, _ = transactions.preparer(u, "alerte")
        r = self._envoyer(
            {"transactionId": "w-2", "event": "transaction.success", "stateData": str(attente.pk)}
        )
        assert r.status_code == 200 and r.json()["result"] == "applique"
        assert transactions.credits_alerte(u) == 1
        # Rejeu (KKiaPay réessaie) puis retour tardif de la fenêtre : toujours un seul crédit.
        self._envoyer({"transactionId": "w-2", "event": "transaction.success"})
        transactions.confirmer(u, str(attente.pk), "w-2")
        assert transactions.credits_alerte(u) == 1

    def test_le_webhook_ne_croit_pas_son_corps(self, alertes_payantes, kkiapay):
        u = ClientFactory()
        attente, _ = transactions.preparer(u, "alerte")
        kkiapay["status"] = "FAILED"  # KKiaPay dit autre chose que le corps reçu
        r = self._envoyer(
            {"transactionId": "w-3", "event": "transaction.success", "stateData": {"data": str(attente.pk)}}
        )
        assert r.json()["result"] == "refuse" and transactions.credits_alerte(u) == 0

    def test_transaction_inconnue_acquittee(self, alertes_payantes):
        r = self._envoyer({"transactionId": "w-4", "event": "transaction.success"})
        assert r.status_code == 200 and r.json()["result"] == "inconnu"

    def test_echec_marque_la_transaction(self, alertes_payantes):
        u = ClientFactory()
        attente, _ = transactions.preparer(u, "alerte")
        self._envoyer({"transactionId": "w-5", "event": "transaction.failed", "stateData": str(attente.pk)})
        attente.refresh_from_db()
        assert attente.status == "failed"


class TestEspeces:
    def test_l_administrateur_active_l_abonnement_en_especes(self, abonnement_exige):
        from apps.accounts.tests.fabriques import AdminFactory

        g = gerant_verifie()
        assert services.can_publish(g.pk) is False
        services.activer_en_especes(
            acteur=AdminFactory(), gerant_id=g.pk, plan_code="standard", periodes=2
        )
        assert services.can_publish(g.pk) is True
        ligne = Transaction.objects.get(user=g.user, objet="abonnement")
        assert ligne.amount == 4000 and ligne.provider_ref.startswith("especes-")

    def test_reserve_aux_administrateurs(self, abonnement_exige):
        from apps.accounts.tests.fabriques import PersonnelFactory

        g = gerant_verifie()
        with pytest.raises(ErreurMetier) as e:
            services.activer_en_especes(
                acteur=PersonnelFactory(), gerant_id=g.pk, plan_code="standard"
            )
        assert e.value.statut == 403

    def test_formule_gratuite_refusee(self, abonnement_exige):
        from apps.accounts.tests.fabriques import AdminFactory

        with pytest.raises(ErreurMetier):
            services.activer_en_especes(
                acteur=AdminFactory(), gerant_id=gerant_verifie().pk, plan_code="free_v1"
            )


class TestParcoursGerantEtEmail:
    def test_sans_e_mail_confirme_pas_de_paiement_d_alerte(self, alertes_payantes):
        sans = _ClientFactory()
        with pytest.raises(ErreurMetier) as e:
            transactions.preparer(sans, "alerte")
        assert e.value.code == "email_required"

    def test_sans_e_mail_confirme_pas_d_alerte_sur_le_site(self):
        u = _ClientFactory(username="sans.mail")
        c = Client()
        c.post("/connexion", {"username": "sans.mail", "password": MOT_DE_PASSE})
        q = DistrictFactory()
        r = c.post("/compte/alertes", {"action": "creer", "district_ids": str(q.pk)})
        from apps.listings.models import Alert

        assert "adresse e-mail" in r.content.decode()
        assert not Alert.objects.filter(user=u).exists()

    def test_gerant_sans_abonnement_redirige_vers_les_formules(self, abonnement_exige):
        g = gerant_verifie()
        c = Client()
        c.post("/connexion", {"username": g.user.username, "password": MOT_DE_PASSE})
        r = c.get("/pro/annonces/nouvelle")
        assert r.status_code == 302 and r["Location"] == "/compte/abonnement?raison=publier"
        page = c.get("/compte/abonnement?raison=publier").content.decode()
        assert "abonnement actif" in page and "Standard" in page

    def test_gerant_abonne_accede_a_l_editeur(self, abonnement_exige):
        from apps.accounts.tests.fabriques import AdminFactory

        g = gerant_verifie()
        services.activer_en_especes(acteur=AdminFactory(), gerant_id=g.pk, plan_code="standard")
        c = Client()
        c.post("/connexion", {"username": g.user.username, "password": MOT_DE_PASSE})
        assert c.get("/pro/annonces/nouvelle").status_code == 200
