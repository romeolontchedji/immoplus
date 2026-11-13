"""Alertes : expiration après 14 jours, budget saisi à la main, cases visibles, nom en premier, fiche sans carte."""

import datetime

import pytest
from django.test import Client
from django.utils import timezone

from apps.accounts.tests.fabriques import ClientFactory
from apps.listings.models import Alert
from apps.listings.services import alertes
from apps.listings.tests.fabriques import DistrictFactory, ListingFactory
from apps.notifications.models import Notification

pytestmark = [pytest.mark.integration, pytest.mark.pg, pytest.mark.django_db]


def connecte(utilisateur) -> Client:
    c = Client()
    c.force_login(utilisateur, backend="django.contrib.auth.backends.ModelBackend")
    session = c.session
    session["tv"] = utilisateur.token_version
    session.save()
    return c


def verifie():
    return ClientFactory(email="awa@exemple.test", email_verified_at=timezone.now())


def vieillir(alerte, jours: int) -> None:
    Alert.objects.filter(pk=alerte.pk).update(
        last_engaged_at=timezone.now() - datetime.timedelta(days=jours)
    )


class TestExpiration:
    def test_une_alerte_sans_activite_depuis_14_jours_est_mise_en_pause(self):
        u = ClientFactory()
        ancienne = Alert.objects.create(user=u, label="Zongo", max_rent=20000)
        recente = Alert.objects.create(user=u, label="Récente", max_rent=20000)
        vieillir(ancienne, 15)
        vieillir(recente, 13)
        assert alertes.expirer_inactives() == 1
        ancienne.refresh_from_db()
        recente.refresh_from_db()
        assert not ancienne.is_active and recente.is_active
        n = Notification.objects.get(user=u, kind="alert.expired")
        assert "Zongo" in n.title and n.data["alert_id"] == str(ancienne.pk)
        assert alertes.expirer_inactives() == 0  # une seule fois

    def test_une_alerte_en_pause_ne_recoit_plus_de_correspondance(self):
        from apps.listings import selectors

        u = ClientFactory()
        alerte = Alert.objects.create(user=u, max_rent=30000)
        vieillir(alerte, 20)
        alertes.expirer_inactives()
        assert not selectors.alertes_correspondantes(ListingFactory(rent_amount=20000).pk)

    def test_ouvrir_la_page_des_alertes_relance_le_delai(self):
        u = verifie()
        alerte = Alert.objects.create(user=u, max_rent=20000)
        vieillir(alerte, 13)
        connecte(u).get("/compte/alertes")
        assert alertes.expirer_inactives() == 0
        alerte.refresh_from_db()
        assert alerte.is_active
        assert timezone.now() - alerte.last_engaged_at < datetime.timedelta(minutes=1)

    def test_ouvrir_la_notification_d_une_alerte_relance_le_delai(self):
        u = verifie()
        alerte = Alert.objects.create(user=u, max_rent=20000)
        vieillir(alerte, 13)
        n = Notification.objects.create(
            user=u, kind="alert.match", title="T", body="C", data={"alert_id": str(alerte.pk)}
        )
        connecte(u).get(f"/compte/notifications/{n.pk}/ouvrir")
        alerte.refresh_from_db()
        assert timezone.now() - alerte.last_engaged_at < datetime.timedelta(minutes=1)

    def test_modifier_ou_reactiver_relance_le_delai(self):
        u = ClientFactory()
        alerte = Alert.objects.create(user=u, max_rent=20000, is_active=False)
        vieillir(alerte, 30)
        alertes.modifier(u, alerte.pk, {"is_active": True})
        alerte.refresh_from_db()
        assert alerte.is_active
        assert timezone.now() - alerte.last_engaged_at < datetime.timedelta(minutes=1)


class TestFormulaire:
    def test_le_montant_saisi_l_emporte_et_la_distance_n_est_plus_proposee(self):
        u = verifie()
        q = DistrictFactory()
        c = connecte(u)
        c.post(
            "/compte/alertes",
            {"action": "creer", "district_ids": [str(q.pk)], "max_rent": "20000",
             "max_rent_libre": "35 000", "max_distance_m": "500"},
        )  # fmt: skip
        alerte = Alert.objects.get(user=u)
        assert alerte.max_rent == 35000 and alerte.max_distance_m is None

    def test_montant_invalide_refuse(self):
        u = verifie()
        q = DistrictFactory()
        r = connecte(u).post(
            "/compte/alertes",
            {"action": "creer", "district_ids": [str(q.pk)], "max_rent_libre": "abc"},
        )
        assert "Entier positif" in r.content.decode() and not Alert.objects.filter(user=u).exists()

    def test_la_page_montre_le_nom_en_premier_et_les_cases_sans_distance(self):
        page = connecte(verifie()).get("/compte/alertes?nouvelle=1").content.decode()
        assert "Distance de l" not in page
        assert page.index("Nom de l&#x27;alerte") < page.index("Quartiers")
        assert 'name="indispensables"' in page and "Douche et WC internes" in page
        assert "Cour clôturée" in page and "Rien d&#x27;obligatoire" not in page
        assert 'name="max_rent_libre"' in page

    def test_le_lien_voir_les_chambres_suit_le_budget_avec_tolerance(self):
        u = verifie()
        Alert.objects.create(user=u, max_rent=20000)
        page = connecte(u).get("/compte/alertes").content.decode()
        assert "rent_max=25000" in page


def test_la_fiche_n_a_plus_de_lien_vers_une_carte():
    a = ListingFactory()
    page = Client().get(f"/annonces/{a.slug}").content.decode()
    assert "openstreetmap" not in page and "Voir le quartier sur la carte" not in page
