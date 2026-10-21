"""Notifications : création, unicité, préférences, push par appareil, présence, reprises, API du centre."""

import pytest
from django.core.cache import cache
from rest_framework.test import APIClient

from apps.accounts.services import appareils, jetons
from apps.accounts.tests.fabriques import ClientFactory, DeviceFactory
from apps.core import presence
from apps.core.providers import push
from apps.notifications import selectors, services, signals
from apps.notifications.models import Notification

pytestmark = [pytest.mark.integration, pytest.mark.pg, pytest.mark.django_db]


def appareil_avec_jeton(utilisateur, jeton="jeton-ok"):
    return DeviceFactory(user=utilisateur, push_provider="expo", push_token=jeton)


def creer_et_envoyer(django_capture_on_commit_callbacks, utilisateur, **kw):
    with django_capture_on_commit_callbacks(execute=True):
        n = services.creer(utilisateur.pk, kw.pop("kind", "alert.match"), "Titre", "Corps", **kw)
    return n


def boite():
    return cache.get(push.CLE_BOITE_PUSH_DEV, [])


class TestCreation:
    def test_cree_une_ligne_et_envoie_le_push(self, django_capture_on_commit_callbacks):
        u = ClientFactory()
        appareil_avec_jeton(u)
        n = creer_et_envoyer(django_capture_on_commit_callbacks, u, data={"listing_id": "x"})
        n.refresh_from_db()
        assert n.delivery_status == "sent" and n.delivered_at is not None
        assert boite()[0]["titre"] == "Titre" and boite()[0]["data"]["listing_id"] == "x"

    def test_la_cle_d_unicite_empeche_tout_doublon(self, django_capture_on_commit_callbacks):
        u = ClientFactory()
        appareil_avec_jeton(u)
        assert creer_et_envoyer(django_capture_on_commit_callbacks, u, dedupe_key="alert:1:2")
        assert (
            creer_et_envoyer(django_capture_on_commit_callbacks, u, dedupe_key="alert:1:2") is None
        )
        assert Notification.objects.filter(dedupe_key="alert:1:2").count() == 1
        assert len(boite()) == 1

    def test_sans_cle_chaque_appel_cree_sa_notification(self, django_capture_on_commit_callbacks):
        u = ClientFactory()
        creer_et_envoyer(django_capture_on_commit_callbacks, u)
        creer_et_envoyer(django_capture_on_commit_callbacks, u)
        assert Notification.objects.filter(user=u).count() == 2

    def test_les_textes_sont_tronques(self):
        u = ClientFactory()
        n = services.creer(u.pk, "alert.match", "T" * 300, "C" * 600)
        assert len(n.title) == 120 and len(n.body) == 255

    def test_aucun_appareil_saute_le_push_avec_un_signal_motive(
        self, django_capture_on_commit_callbacks
    ):
        u = ClientFactory()
        recus = []
        signals.push_regle.connect(
            lambda **kw: recus.append(kw), dispatch_uid="t-aucun", weak=False
        )
        try:
            n = creer_et_envoyer(django_capture_on_commit_callbacks, u)
        finally:
            signals.push_regle.disconnect(dispatch_uid="t-aucun")
        n.refresh_from_db()
        assert (n.delivery_status, n.last_error) == ("skipped", "aucun_appareil")
        assert recus and recus[0]["motif"] == "saute"


class TestPreferences:
    def test_categorie_coupee_cree_la_ligne_sans_push(self, django_capture_on_commit_callbacks):
        u = ClientFactory(notif_prefs={"alertes": {"push": False}})
        appareil_avec_jeton(u)
        n = creer_et_envoyer(django_capture_on_commit_callbacks, u, kind="alert.match")
        n.refresh_from_db()
        assert (n.delivery_status, n.last_error) == ("skipped", "categorie_coupee")
        assert boite() == []

    def test_une_sanction_ne_se_coupe_pas(self, django_capture_on_commit_callbacks):
        u = ClientFactory(notif_prefs={"alertes": {"push": False}, "rappels": {"push": False}})
        appareil_avec_jeton(u)
        n = creer_et_envoyer(django_capture_on_commit_callbacks, u, kind="account.sanction")
        n.refresh_from_db()
        assert n.delivery_status == "sent"

    def test_conversation_en_silence(self, django_capture_on_commit_callbacks):
        u = ClientFactory(notif_prefs={"silence": ["conv-1"]})
        appareil_avec_jeton(u)
        n = creer_et_envoyer(
            django_capture_on_commit_callbacks,
            u,
            kind="message.received",
            data={"conversation_id": "conv-1"},
        )
        n.refresh_from_db()
        assert (n.delivery_status, n.last_error) == ("skipped", "silence")

    def test_silence_demande_par_l_appelant(self, django_capture_on_commit_callbacks):
        u = ClientFactory()
        appareil_avec_jeton(u)
        n = creer_et_envoyer(django_capture_on_commit_callbacks, u, silence=True)
        n.refresh_from_db()
        assert n.last_error == "silence"

    def test_apercu_coupe_masque_le_texte_du_message(self, django_capture_on_commit_callbacks):
        u = ClientFactory(notif_prefs={"messages": {"apercu": False}})
        appareil_avec_jeton(u)
        creer_et_envoyer(
            django_capture_on_commit_callbacks,
            u,
            kind="message.received",
            data={"conversation_id": "c"},
        )
        assert boite()[0]["corps"] == "Nouveau message"

    def test_apercu_coupe_garde_le_nombre_de_messages(self, django_capture_on_commit_callbacks):
        u = ClientFactory(notif_prefs={"messages": {"apercu": False}})
        appareil_avec_jeton(u)
        creer_et_envoyer(
            django_capture_on_commit_callbacks, u, kind="message.received",
            data={"conversation_id": "c", "_nombre": 3},
        )  # fmt: skip
        assert boite()[0]["corps"] == "3 nouveaux messages"


class TestPresenceEtAppareils:
    def test_conversation_ouverte_supprime_le_push_de_cet_appareil_seulement(
        self, django_capture_on_commit_callbacks
    ):
        u = ClientFactory()
        ouvert = appareil_avec_jeton(u, "jeton-ouvert")
        appareil_avec_jeton(u, "jeton-autre")
        presence.poser(u.pk, ouvert.pk, "conv-1")
        creer_et_envoyer(
            django_capture_on_commit_callbacks,
            u,
            kind="message.received",
            data={"conversation_id": "conv-1"},
        )
        assert [b["jeton"] for b in boite()] == ["jeton-autre"]

    def test_tous_les_appareils_sur_la_conversation_saute_sans_marquer_traite(
        self, django_capture_on_commit_callbacks
    ):
        u = ClientFactory()
        a = appareil_avec_jeton(u)
        presence.poser(u.pk, a.pk, "conv-1")
        recus = []
        signals.push_regle.connect(lambda **kw: recus.append(kw), dispatch_uid="t-pres", weak=False)
        try:
            n = creer_et_envoyer(
                django_capture_on_commit_callbacks,
                u,
                kind="message.received",
                data={"conversation_id": "conv-1"},
            )
        finally:
            signals.push_regle.disconnect(dispatch_uid="t-pres")
        n.refresh_from_db()
        assert (n.delivery_status, n.last_error) == ("skipped", "presence")
        assert recus == []  # un push supprimé par la présence ne pose pas notified_at

    def test_le_rattrapage_renvoie_quand_la_presence_a_disparu(
        self, django_capture_on_commit_callbacks
    ):
        u = ClientFactory()
        a = appareil_avec_jeton(u)
        presence.poser(u.pk, a.pk, "conv-1")
        n = creer_et_envoyer(
            django_capture_on_commit_callbacks,
            u,
            kind="message.received",
            data={"conversation_id": "conv-1"},
        )
        presence.effacer(u.pk, a.pk)
        assert services.relancer(n.pk) == "sent"
        assert len(boite()) == 1

    def test_la_presence_expire_et_s_efface(self):
        u = ClientFactory()
        presence.poser(u.pk, "d1", "c1")
        assert presence.appareils_sur_conversation(u.pk, "c1") == {"d1"}
        assert presence.appareils_sur_conversation(u.pk, "autre") == set()
        presence.effacer(u.pk, "d1")
        assert presence.appareils_sur_conversation(u.pk, "c1") == set()

    def test_jeton_invalide_desactive_l_appareil(self, django_capture_on_commit_callbacks):
        u = ClientFactory()
        mauvais = appareil_avec_jeton(u, "invalide-1")
        n = creer_et_envoyer(django_capture_on_commit_callbacks, u)
        n.refresh_from_db()
        mauvais.refresh_from_db()
        assert n.delivery_status == "failed" and mauvais.push_invalid_at is not None

    def test_livraison_partielle(self, django_capture_on_commit_callbacks):
        u = ClientFactory()
        appareil_avec_jeton(u, "jeton-ok")
        appareil_avec_jeton(u, "invalide-2")
        n = creer_et_envoyer(django_capture_on_commit_callbacks, u)
        n.refresh_from_db()
        assert n.delivery_status == "partial"

    def test_une_panne_est_reprise_sans_doubler_les_appareils_livres(self, settings):
        u = ClientFactory()
        appareil_avec_jeton(u, "jeton-ok")
        appareil_avec_jeton(u, "panne-1")
        n = services.creer(u.pk, "alert.match", "T", "C")
        assert services.envoyer_push(n.pk) == "a_reprendre"
        assert len(boite()) == 1
        assert services.envoyer_push(n.pk) == "a_reprendre"
        assert len(boite()) == 1  # l'appareil livré n'est pas relancé

    def test_cinq_essais_puis_partiel(self):
        u = ClientFactory()
        appareil_avec_jeton(u, "jeton-ok")
        appareil_avec_jeton(u, "panne-1")
        n = services.creer(u.pk, "alert.match", "T", "C")
        etats = [services.envoyer_push(n.pk) for _ in range(services.MAX_ESSAIS)]
        assert etats[:-1] == ["a_reprendre"] * (services.MAX_ESSAIS - 1) and etats[-1] == "partial"

    def test_panne_totale_apres_cinq_essais_echoue(self):
        u = ClientFactory()
        appareil_avec_jeton(u, "panne-1")
        n = services.creer(u.pk, "alert.match", "T", "C")
        for _ in range(services.MAX_ESSAIS):
            etat = services.envoyer_push(n.pk)
        n.refresh_from_db()
        assert etat == "failed" and n.delivery_attempts == services.MAX_ESSAIS

    def test_un_fournisseur_qui_leve_ne_casse_pas(self, monkeypatch):
        class Casse(push.PushProvider):
            def envoyer(self, *a, **k):
                raise RuntimeError("boum")

        monkeypatch.setattr(push, "fournisseur", lambda: Casse())
        u = ClientFactory()
        appareil_avec_jeton(u)
        n = services.creer(u.pk, "alert.match", "T", "C")
        assert services.envoyer_push(n.pk) == "a_reprendre"

    def test_une_notification_deja_traitee_n_est_pas_renvoyee(self):
        u = ClientFactory()
        appareil_avec_jeton(u)
        n = services.creer(u.pk, "alert.match", "T", "C")
        assert services.envoyer_push(n.pk) == "sent"
        assert services.envoyer_push(n.pk) == "sent" and len(boite()) == 1

    def test_notification_inconnue(self):
        import uuid

        assert services.envoyer_push(uuid.uuid4()) == "absent"
        assert services.relancer(uuid.uuid4()) == "absent"


class TestFournisseurs:
    def test_console_refuse_hors_developpement(self, settings):
        from django.core.exceptions import ImproperlyConfigured

        settings.DEV_INBOX_ENABLED = False
        settings.DEBUG = False
        with pytest.raises(ImproperlyConfigured):
            push.ConsolePushProvider()

    def test_fournisseur_inconnu_et_fcm_non_implemente(self, settings):
        from django.core.exceptions import ImproperlyConfigured

        settings.PUSH_PROVIDER = "inconnu"
        with pytest.raises(ImproperlyConfigured):
            push.fournisseur()
        settings.PUSH_PROVIDER = "fcm"
        with pytest.raises(NotImplementedError):
            push.fournisseur().envoyer("j", "t", "c", {})
        settings.PUSH_PROVIDER = "expo"
        assert isinstance(push.fournisseur(), push.ExpoPushProvider)


class TestCentre:
    def test_compteur_borne_a_cent(self):
        u = ClientFactory()
        Notification.objects.bulk_create(
            [Notification(user=u, kind="alert.match", title="t", body="b") for _ in range(105)]
        )
        assert selectors.non_lues(u.pk) == 100

    def test_marquer_lu_et_tout_lire(self):
        u, autre = ClientFactory(), ClientFactory()
        a = services.creer(u.pk, "alert.match", "T", "C")
        services.creer(u.pk, "alert.match", "T", "C")
        b = services.creer(autre.pk, "alert.match", "T", "C")
        services.marquer_lue(u.pk, a.pk)
        assert selectors.non_lues(u.pk) == 1
        from apps.core.errors import ErreurMetier

        with pytest.raises(ErreurMetier) as e:
            services.marquer_lue(u.pk, b.pk)  # celle d'un autre : introuvable
        assert e.value.statut == 404
        assert services.tout_marquer_lu(u.pk) == 1 and selectors.non_lues(u.pk) == 0

    def test_lecture_d_une_conversation_lit_ses_notifications(self):
        u = ClientFactory()
        services.creer(u.pk, "message.received", "T", "C", data={"conversation_id": "c1"})
        services.creer(u.pk, "message.received", "T", "C", data={"conversation_id": "c2"})
        assert services.marquer_conversation_lue(u.pk, "c1") == 1
        assert selectors.non_lues(u.pk) == 1

    def test_pagination_par_date(self):
        u = ClientFactory()
        for i in range(5):
            services.creer(u.pk, "alert.match", f"T{i}", "C")
        page1, suivant = selectors.liste(u.pk, limite=2)
        assert len(page1) == 2 and suivant
        from django.utils.dateparse import parse_datetime

        page2, _ = selectors.liste(u.pk, avant=parse_datetime(suivant), limite=10)
        assert len(page2) == 3 and not ({n.pk for n in page1} & {n.pk for n in page2})


def client_de(utilisateur) -> APIClient:
    d, _ = appareils.ouvrir(utilisateur, installation_id="inst-notif-1", platform="android")
    c = APIClient()
    c.credentials(HTTP_AUTHORIZATION=f"Bearer {jetons.emettre_acces(utilisateur, d)}")
    return c


@pytest.mark.api
class TestApi:
    def test_connexion_requise(self):
        assert APIClient().get("/v1/notifications").status_code == 401

    def test_liste_compteur_lecture(self):
        u = ClientFactory()
        n = services.creer(u.pk, "alert.match", "Une annonce", "Corps", data={"listing_id": "l"})
        services.creer(u.pk, "alert.match", "Autre", "Corps", data={"_livres": ["d"]})
        c = client_de(u)
        r = c.get("/v1/notifications")
        assert r.status_code == 200
        corps = r.json()
        assert corps["unread_count"] == 2 and len(corps["items"]) == 2
        assert all(
            "_livres" not in i["data"] for i in corps["items"]
        )  # champs internes jamais exposés
        assert c.get("/v1/notifications/unread-count").json() == {"unread_count": 2}
        assert c.post(f"/v1/notifications/{n.pk}/read").status_code == 204
        assert c.get("/v1/notifications/unread-count").json() == {"unread_count": 1}
        assert c.post("/v1/notifications/read-all").json() == {"updated": 1}

    def test_la_notification_d_un_autre_est_introuvable(self):
        autre = services.creer(ClientFactory().pk, "alert.match", "T", "C")
        r = client_de(ClientFactory()).post(f"/v1/notifications/{autre.pk}/read")
        assert r.status_code == 404 and r.json()["error"]["code"] == "not_found"

    def test_curseur_et_limite_invalides(self):
        c = client_de(ClientFactory())
        assert (
            c.get("/v1/notifications?cursor=pasunedate").json()["error"]["code"] == "invalid_cursor"
        )
        assert c.get("/v1/notifications?limit=abc").status_code == 400
        assert c.get("/v1/notifications?limit=1").status_code == 200
