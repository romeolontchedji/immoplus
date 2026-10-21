"""Présentation des notifications : textes (montants, pluriels), canal Android, priorité, pastille, charge Expo."""

import json

import pytest
from django.core.cache import cache

from apps.accounts.tests.fabriques import ClientFactory, DeviceFactory
from apps.core.providers import push
from apps.notifications import services, textes

pytestmark = [pytest.mark.integration, pytest.mark.pg, pytest.mark.django_db]


class TestTextes:
    def test_francs_avec_espace_fine(self):
        assert textes.francs(15000) == "15 000 F"
        assert textes.francs(500) == "500 F"

    @pytest.mark.parametrize(("n", "attendu"), [(0, "0 jour"), (1, "1 jour"), (3, "3 jours")])
    def test_pluriel(self, n, attendu):
        assert textes.pluriel(n, "jour") == attendu

    def test_pluriel_irregulier(self):
        assert textes.pluriel(2, "message non lu", "messages non lus") == "2 messages non lus"

    def test_distance(self):
        assert textes.distance(600) == "600 m" and textes.distance(1800) == "1,8 km"
        assert textes.distance(None) is None

    def test_tronquer(self):
        assert textes.tronquer("Chambre  salon\nBanikanni", 50) == "Chambre salon Banikanni"
        assert textes.tronquer("A" * 50, 10) == "A" * 9 + "…"


def _envoyer(capture, utilisateur, kind):
    DeviceFactory(user=utilisateur, push_provider="expo", push_token="jeton-ok")
    with capture(execute=True):
        services.creer(
            utilisateur.pk, kind, "Titre", "Corps", data={"_sous_titre": "Studio Titirou"}
        )
    return cache.get(push.CLE_BOITE_PUSH_DEV, [])[0]


class TestCanaux:
    def test_un_message_part_sur_le_canal_prioritaire(self, django_capture_on_commit_callbacks):
        envoi = _envoyer(django_capture_on_commit_callbacks, ClientFactory(), "message.received")
        assert envoi["canal"] == "messages" and envoi["prioritaire"] is True
        assert envoi["badge"] == 1  # la notification elle-même, non lue
        assert "_sous_titre" not in envoi["data"]  # donnée interne, jamais envoyée

    def test_une_alerte_part_sur_le_canal_alertes(self, django_capture_on_commit_callbacks):
        envoi = _envoyer(django_capture_on_commit_callbacks, ClientFactory(), "alert.match")
        assert envoi["canal"] == "alertes" and envoi["prioritaire"] is False

    def test_un_evenement_de_compte_part_sur_le_canal_compte(
        self, django_capture_on_commit_callbacks
    ):
        envoi = _envoyer(django_capture_on_commit_callbacks, ClientFactory(), "listing.published")
        assert envoi["canal"] == "compte"


class TestChargeExpo:
    def test_canal_priorite_pastille_et_sous_titre(self, monkeypatch):
        envoye = {}

        class Reponse:
            def __enter__(self):
                return self

            def __exit__(self, *a):
                return False

            def read(self):
                return json.dumps({"data": {"status": "ok"}}).encode()

        def ouvrir(requete, timeout):
            envoye.update(json.loads(requete.data))
            return Reponse()

        monkeypatch.setattr(push.urllib.request, "urlopen", ouvrir)
        options = push.OptionsPush(canal="messages", prioritaire=True, badge=3, sous_titre="Studio")
        r = push.ExpoPushProvider().envoyer(
            "ExponentPushToken[x]", "Aïcha", "Bonjour", {}, "conv:1", options
        )
        assert r.ok
        assert envoye["channelId"] == "messages" and envoye["priority"] == "high"
        assert (
            envoye["badge"] == 3
            and envoye["subtitle"] == "Studio"
            and envoye["collapseId"] == "conv:1"
        )
