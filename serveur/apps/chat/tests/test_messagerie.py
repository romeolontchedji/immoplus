"""Messagerie : ouverture, envoi idempotent, séquence, coordonnées, limites, lecture, blocage, notifications."""

import datetime
import uuid

import pytest
from django.core.cache import cache
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.services import appareils, jetons
from apps.accounts.tests.fabriques import ClientFactory, DeviceFactory
from apps.chat import selectors, services, signals, ws
from apps.chat.models import Conversation, Message
from apps.core import parametres, stats
from apps.core.errors import ErreurMetier
from apps.core.providers import push
from apps.listings.tests.fabriques import ListingFactory, gerant_verifie
from apps.notifications.models import Notification

pytestmark = [pytest.mark.integration, pytest.mark.pg, pytest.mark.django_db]


def client_de(utilisateur, installation="inst-chat") -> APIClient:
    d, _ = appareils.ouvrir(utilisateur, installation_id=installation, platform="android")
    c = APIClient()
    c.credentials(HTTP_AUTHORIZATION=f"Bearer {jetons.emettre_acces(utilisateur, d)}")
    return c


def mid():
    return str(uuid.uuid4())


@pytest.fixture
def decor():
    gerant = gerant_verifie()
    annonce = ListingFactory(gerant=gerant)
    locataire = ClientFactory()
    return type("D", (), {"gerant": gerant, "annonce": annonce, "locataire": locataire})


def ouvrir(decor, corps="Bonjour, la chambre est-elle toujours disponible ?"):
    return services.ouvrir(decor.locataire, decor.annonce.pk, corps, mid())


class TestOuverture:
    def test_ouvre_une_conversation_avec_le_premier_message(self, decor):
        conversation, message, cree, _ = ouvrir(decor)
        assert (
            cree
            and conversation.client_id == decor.locataire.pk
            and conversation.gerant_id == decor.gerant.user_id
        )
        assert (
            message.seq == 1
            and conversation.last_seq == 1
            and conversation.last_message_preview.startswith("Bonjour")
        )
        assert stats.lire("conversations_started") == 1 and stats.lire("messages") == 1

    def test_une_seule_conversation_par_couple(self, decor):
        c1, *_ = ouvrir(decor)
        c2, m2, cree, _ = ouvrir(decor, "Deuxième message")
        assert c1.pk == c2.pk and not cree and m2.seq == 2
        assert Conversation.objects.count() == 1

    def test_refus(self, decor):
        gerant = decor.gerant.user
        for utilisateur, annonce_id, code in [
            (gerant, decor.annonce.pk, "wrong_audience"),
            (decor.locataire, uuid.uuid4(), "listing_unavailable"),
            (decor.locataire, "pas-un-uuid", "listing_unavailable"),
        ]:
            with pytest.raises(ErreurMetier) as e:
                services.ouvrir(utilisateur, annonce_id, "Bonjour", mid())
            assert e.value.code == code

    def test_annonce_non_publiee_refusee_mais_conversation_existante_reste_accessible(self, decor):
        c, *_ = ouvrir(decor)
        decor.annonce.status = "rented"
        decor.annonce.save()
        _, m, cree, _ = services.ouvrir(decor.locataire, decor.annonce.pk, "Encore là ?", mid())
        assert not cree and m.conversation_id == c.pk
        autre = ClientFactory()
        with pytest.raises(ErreurMetier) as e:
            services.ouvrir(autre, decor.annonce.pk, "Bonjour", mid())
        assert e.value.code == "listing_unavailable" and e.value.statut == 409

    def test_un_locataire_suspendu_n_ouvre_rien(self, decor):
        decor.locataire.status = "suspended"
        decor.locataire.suspended_until = timezone.now() + datetime.timedelta(days=3)
        decor.locataire.save()
        with pytest.raises(ErreurMetier) as e:
            ouvrir(decor)
        assert e.value.code == "account_suspended"

    def test_vingt_nouvelles_conversations_par_jour(self, decor):
        for annonce in ListingFactory.create_batch(20):
            services.ouvrir(decor.locataire, annonce.pk, "Bonjour", mid())
        with pytest.raises(ErreurMetier) as e:
            ouvrir(decor)
        assert e.value.code == "rate_limited" and e.value.statut == 429

    def test_la_limite_est_un_parametre(self, decor):
        parametres.definir("NEW_CONVERSATIONS_PER_DAY", 1)
        ouvrir(decor)
        with pytest.raises(ErreurMetier):
            services.ouvrir(decor.locataire, ListingFactory().pk, "Bonjour", mid())


class TestEnvoi:
    def test_sequence_croissante_sans_trou_et_cache_de_conversation(self, decor):
        conversation, *_ = ouvrir(decor)
        for i in range(2, 6):
            m, cree, _ = services.envoyer(
                decor.gerant.user if i % 2 else decor.locataire, conversation.pk, f"msg {i}", mid()
            )
            assert cree and m.seq == i
        conversation.refresh_from_db()
        assert list(Message.objects.order_by("seq").values_list("seq", flat=True)) == [
            1,
            2,
            3,
            4,
            5,
        ]
        assert conversation.last_seq == 5 and conversation.last_message_preview == "msg 5"

    def test_idempotence_par_client_msg_id(self, decor):
        conversation, *_ = ouvrir(decor)
        cle = mid()
        m1, cree1, _ = services.envoyer(decor.locataire, conversation.pk, "Une fois", cle)
        m2, cree2, _ = services.envoyer(decor.locataire, conversation.pk, "Une fois", cle)
        assert cree1 and not cree2 and m1.pk == m2.pk
        assert Message.objects.filter(conversation=conversation).count() == 2
        assert stats.lire("messages") == 2

    def test_deux_expediteurs_peuvent_reutiliser_le_meme_identifiant(self, decor):
        conversation, *_ = ouvrir(decor)
        cle = mid()
        a, *_ = services.envoyer(decor.locataire, conversation.pk, "A", cle)
        b, cree, _ = services.envoyer(decor.gerant.user, conversation.pk, "B", cle)
        assert cree and a.pk != b.pk

    @pytest.mark.parametrize("corps", ["", "   ", "x" * 2001])
    def test_corps_invalide(self, decor, corps):
        conversation, *_ = ouvrir(decor)
        with pytest.raises(ErreurMetier) as e:
            services.envoyer(decor.locataire, conversation.pk, corps, mid())
        assert e.value.code == "validation_error"

    def test_longueur_maximale_acceptee(self, decor):
        conversation, *_ = ouvrir(decor)
        m, *_ = services.envoyer(decor.locataire, conversation.pk, "x" * 2000, mid())
        assert len(m.body) == 2000

    def test_client_msg_id_invalide(self, decor):
        conversation, *_ = ouvrir(decor)
        with pytest.raises(ErreurMetier) as e:
            services.envoyer(decor.locataire, conversation.pk, "Salut", "pas-un-uuid")
        assert "client_msg_id" in e.value.champs

    def test_un_tiers_ne_peut_ni_lire_ni_ecrire(self, decor):
        conversation, *_ = ouvrir(decor)
        intrus = ClientFactory()
        with pytest.raises(ErreurMetier) as e:
            services.envoyer(intrus, conversation.pk, "Coucou", mid())
        assert e.value.statut == 404
        with pytest.raises(ErreurMetier):
            selectors.conversation_du_participant(intrus.pk, "n-importe-quoi")

    def test_premiere_reponse_du_gerant_enregistree_une_fois(self, decor):
        conversation, *_ = ouvrir(decor)
        assert Conversation.objects.get(pk=conversation.pk).first_reply_at is None
        services.envoyer(decor.gerant.user, conversation.pk, "Oui, elle est libre", mid())
        premiere = Conversation.objects.get(pk=conversation.pk).first_reply_at
        services.envoyer(decor.gerant.user, conversation.pk, "Visite demain ?", mid())
        assert (
            premiere is not None
            and Conversation.objects.get(pk=conversation.pk).first_reply_at == premiere
        )

    def test_trente_messages_par_minute(self, decor):
        conversation, *_ = ouvrir(decor)
        for _ in range(29):
            services.envoyer(decor.locataire, conversation.pk, "ok", mid())
        with pytest.raises(ErreurMetier) as e:
            services.envoyer(decor.locataire, conversation.pk, "trop", mid())
        assert e.value.code == "rate_limited" and e.value.entetes["Retry-After"] == "60"

    def test_un_compte_suspendu_ne_peut_plus_ecrire(self, decor):
        conversation, *_ = ouvrir(decor)
        decor.gerant.user.status = "suspended"
        decor.gerant.user.suspended_until = timezone.now() + datetime.timedelta(days=1)
        decor.gerant.user.save()
        with pytest.raises(ErreurMetier) as e:
            services.envoyer(decor.gerant.user, conversation.pk, "Bonjour", mid())
        assert e.value.code == "account_suspended"

    def test_lecture_seule(self, decor):
        conversation, *_ = ouvrir(decor)
        services.passer_en_lecture_seule([conversation.pk])
        with pytest.raises(ErreurMetier) as e:
            services.envoyer(decor.locataire, conversation.pk, "Encore", mid())
        assert e.value.code == "conversation_read_only"
        with pytest.raises(ErreurMetier):
            services.bloquer(decor.locataire, conversation.pk)


class TestCoordonnees:
    def test_masque_par_defaut_original_garde_rappel_et_signal(
        self, decor, django_capture_on_commit_callbacks
    ):
        conversation, *_ = ouvrir(decor)
        recus = []
        signals.contact_detecte.connect(
            lambda **kw: recus.append(kw), dispatch_uid="t-contact", weak=False
        )
        try:
            with django_capture_on_commit_callbacks(execute=True):
                m, _, info = services.envoyer(
                    decor.locataire, conversation.pk, "Appelle-moi au 97 12 34 56 ok", mid()
                )
        finally:
            signals.contact_detecte.disconnect(dispatch_uid="t-contact")
        assert (
            m.body == "Appelle-moi au 97 12 34 56 ok"
            and "97 12" not in m.body_masked
            and "*" in m.body_masked
        )
        assert (
            info["warning"]
            and recus
            and recus[0]["message_id"] == m.pk
            and "telephone" in recus[0]["motifs"]
        )
        vu_destinataire = services.message_pour(m, decor.gerant.user_id)
        vu_expediteur = services.message_pour(m, decor.locataire.pk)
        assert "97 12" not in vu_destinataire["body"] and "97 12" in vu_expediteur["body"]
        assert (
            vu_destinataire["flag_reason"] is None and vu_expediteur["flag_reason"] == "telephone"
        )
        assert "97 12" in services.message_pour(m, decor.gerant.user_id, personnel=True)["body"]
        assert "97 12" not in Conversation.objects.get(pk=conversation.pk).last_message_preview

    @pytest.mark.parametrize(
        "texte", ["écris à moi@exemple.com", "va sur www.exemple.bj", "https://wa.me/22997123456"]
    )
    def test_autres_signaux_forts(self, decor, texte):
        conversation, *_ = ouvrir(decor)
        m, _, info = services.envoyer(decor.locataire, conversation.pk, texte, mid())
        assert m.body_masked and info["warning"]

    def test_un_prix_n_est_pas_une_coordonnee(self, decor):
        conversation, *_ = ouvrir(decor)
        m, _, info = services.envoyer(
            decor.locataire, conversation.pk, "Le loyer de 25 000 FCFA, caution 50000 F", mid()
        )
        assert m.body_masked is None and m.flag_reason is None and info["warning"] is None

    def test_mot_cle_seul_signale_sans_masquer_ni_avertir(self, decor):
        conversation, *_ = ouvrir(decor)
        m, _, info = services.envoyer(
            decor.locataire, conversation.pk, "On peut parler sur WhatsApp ?", mid()
        )
        assert m.body_masked is None and m.flag_reason == "mot_cle" and info["warning"] is None

    def test_mode_flag_livre_tel_quel_mais_marque(self, decor):
        parametres.definir("CONTACT_LEAK_MODE", "flag")
        conversation, *_ = ouvrir(decor)
        m, _, info = services.envoyer(
            decor.locataire, conversation.pk, "Mon mail : a.b@exemple.com", mid()
        )
        assert m.body_masked is None and m.flag_reason == "email" and info["warning"]
        assert "a.b@exemple.com" in services.message_pour(m, decor.gerant.user_id)["body"]

    def test_mode_block_refuse_le_message(self, decor):
        parametres.definir("CONTACT_LEAK_MODE", "block")
        conversation, *_ = ouvrir(decor)
        with pytest.raises(ErreurMetier) as e:
            services.envoyer(decor.locataire, conversation.pk, "97123456", mid())
        assert e.value.code == "contact_detected" and e.value.statut == 422
        assert Message.objects.filter(conversation=conversation).count() == 1

    def test_message_retire_par_la_moderation(self, decor):
        conversation, m, *_ = ouvrir(decor)
        Message.objects.filter(pk=m.pk).update(moderation_status="deleted")
        m.refresh_from_db()
        assert (
            services.message_pour(m, decor.gerant.user_id)["body"] == selectors.PLACEHOLDER_MODERE
        )
        assert services.message_pour(m, decor.locataire.pk)["body"] == selectors.PLACEHOLDER_MODERE
        assert services.message_pour(m, decor.gerant.user_id, personnel=True)["body"].startswith(
            "Bonjour"
        )


class TestLecture:
    def test_non_lus_par_difference_de_positions(self, decor):
        conversation, *_ = ouvrir(decor)
        for _ in range(3):
            services.envoyer(decor.locataire, conversation.pk, "ping", mid())
        conversation.refresh_from_db()
        assert selectors.non_lus(conversation, decor.gerant.user_id) == 4
        assert selectors.non_lus(conversation, decor.locataire.pk) == 0
        services.lire(decor.gerant.user, conversation.pk, 2)
        conversation.refresh_from_db()
        assert selectors.non_lus(conversation, decor.gerant.user_id) == 2

    def test_la_position_ne_recule_jamais_et_est_bornee(self, decor):
        conversation, *_ = ouvrir(decor)
        services.lire(decor.gerant.user, conversation.pk, 999)
        c = services.lire(decor.gerant.user, conversation.pk, 0)
        assert c.gerant_read_seq == 1
        with pytest.raises(ErreurMetier):
            services.lire(decor.gerant.user, conversation.pk, -1)

    def test_lire_pose_notified_at_et_lit_les_notifications(
        self, decor, django_capture_on_commit_callbacks
    ):
        with django_capture_on_commit_callbacks(execute=True):
            conversation, m, *_ = ouvrir(decor)
        Message.objects.filter(pk=m.pk).update(notified_at=None)
        Notification.objects.filter(user_id=decor.gerant.user_id).update(read_at=None)
        with django_capture_on_commit_callbacks(execute=True):
            services.lire(decor.gerant.user, conversation.pk, 1)
        m.refresh_from_db()
        assert m.notified_at is not None
        assert not Notification.objects.filter(
            user_id=decor.gerant.user_id, read_at__isnull=True
        ).exists()


class TestBlocageEtSilence:
    def test_celui_qui_bloque_empeche_l_autre_d_ecrire(self, decor):
        conversation, *_ = ouvrir(decor)
        services.bloquer(decor.gerant.user, conversation.pk)
        with pytest.raises(ErreurMetier) as e:
            services.envoyer(decor.locataire, conversation.pk, "S'il vous plaît ?", mid())
        assert e.value.code == "conversation_blocked"
        services.envoyer(decor.gerant.user, conversation.pk, "Je peux encore écrire", mid())

    def test_seul_celui_qui_a_bloque_debloque(self, decor):
        conversation, *_ = ouvrir(decor)
        services.bloquer(decor.gerant.user, conversation.pk)
        with pytest.raises(ErreurMetier) as e:
            services.debloquer(decor.locataire, conversation.pk)
        assert e.value.statut == 403
        c = services.debloquer(decor.gerant.user, conversation.pk)
        assert c.status == "open" and c.blocked_by_id is None
        services.envoyer(decor.locataire, conversation.pk, "Merci", mid())

    def test_silence(self, decor):
        conversation, *_ = ouvrir(decor)
        jusque = timezone.now() + datetime.timedelta(hours=2)
        c = services.definir_silence(decor.gerant.user, conversation.pk, jusque)
        assert c.gerant_muted_until == jusque and c.client_muted_until is None
        assert selectors.en_silence(c, decor.gerant.user_id, timezone.now())
        assert (
            services.definir_silence(
                decor.gerant.user, conversation.pk, timezone.now() - datetime.timedelta(hours=1)
            ).gerant_muted_until
            is None
        )


def boite():
    return cache.get(push.CLE_BOITE_PUSH_DEV, [])


class TestNotificationsDeMessage:
    def test_une_notification_par_message_et_notified_at_apres_le_push(
        self, decor, django_capture_on_commit_callbacks
    ):
        DeviceFactory(user=decor.gerant.user, push_provider="expo", push_token="jeton-gerant")
        with django_capture_on_commit_callbacks(execute=True):
            conversation, m1, *_ = ouvrir(decor)
            m2, *_ = services.envoyer(decor.locataire, conversation.pk, "Et la caution ?", mid())
        notifs = Notification.objects.filter(user=decor.gerant.user, kind="message.received")
        assert notifs.count() == 2 and len(boite()) == 2
        assert {n.collapse_key for n in notifs} == {
            f"conv:{conversation.pk}"
        }  # groupées à l'affichage seulement
        assert boite()[0]["titre"].startswith(
            f"{decor.locataire.full_name} · "
        )  # qui · quelle chambre
        for m in (m1, m2):
            m.refresh_from_db()
            assert m.notified_at is not None

    def test_la_notification_compte_les_messages_en_attente_et_porte_les_actions(
        self, decor, django_capture_on_commit_callbacks
    ):
        """N2 et N3 : « 2 nouveaux messages · … » remplace la précédente ; catégorie « message » (Répondre, Lu)."""
        DeviceFactory(user=decor.gerant.user, push_provider="expo", push_token="jeton-gerant")
        with django_capture_on_commit_callbacks(execute=True):
            conversation, *_ = ouvrir(decor)
            services.envoyer(decor.locataire, conversation.pk, "Et la caution ?", mid())
        dernier, premier = boite()[0], boite()[1]
        assert (
            premier["corps"].startswith("Bonjour")
            and dernier["corps"] == "2 nouveaux messages · Et la caution ?"
        )
        assert (
            dernier["categorie"] == "message" and dernier["collapse"] == f"conv:{conversation.pk}"
        )

    def test_aucun_appareil_saut_motive_pose_notified_at(
        self, decor, django_capture_on_commit_callbacks
    ):
        with django_capture_on_commit_callbacks(execute=True):
            _, m, *_ = ouvrir(decor)
        m.refresh_from_db()
        assert m.notified_at is not None and boite() == []

    def test_conversation_ouverte_ne_pose_pas_notified_at_et_le_rattrapage_renvoie(
        self, decor, django_capture_on_commit_callbacks
    ):
        from apps.core import presence

        appareil = DeviceFactory(
            user=decor.gerant.user, push_provider="expo", push_token="jeton-gerant"
        )
        conversation, *_ = ouvrir(decor)
        Message.objects.all().update(notified_at=timezone.now())  # le premier message est réglé
        presence.poser(decor.gerant.user_id, appareil.pk, conversation.pk)
        with django_capture_on_commit_callbacks(execute=True):
            m, *_ = services.envoyer(decor.locataire, conversation.pk, "Tu es là ?", mid())
        m.refresh_from_db()
        assert m.notified_at is None and boite() == []
        presence.effacer(decor.gerant.user_id, appareil.pk)
        Message.objects.filter(pk=m.pk).update(
            created_at=timezone.now() - datetime.timedelta(minutes=2)
        )
        assert services.rattraper() == 1
        m.refresh_from_db()
        assert m.notified_at is not None and len(boite()) == 1

    def test_message_deja_lu_n_est_pas_notifie(self, decor):
        conversation, m, *_ = ouvrir(decor)
        Message.objects.filter(pk=m.pk).update(notified_at=None)
        services.lire(decor.gerant.user, conversation.pk, 1)
        Message.objects.filter(pk=m.pk).update(notified_at=None)
        assert services.notifier(m.pk) == "lu"
        assert services.notifier(uuid.uuid4()) == "absent"

    def test_apercu_masque_dans_la_notification(self, decor, django_capture_on_commit_callbacks):
        with django_capture_on_commit_callbacks(execute=True):
            ouvrir(decor, "Mon numéro : 97 12 34 56")
        assert "97 12" not in Notification.objects.get(kind="message.received").body

    def test_conversation_en_silence_cree_la_ligne_sans_push(
        self, decor, django_capture_on_commit_callbacks
    ):
        DeviceFactory(user=decor.gerant.user, push_provider="expo", push_token="jeton-gerant")
        conversation, *_ = ouvrir(decor)
        services.definir_silence(
            decor.gerant.user, conversation.pk, timezone.now() + datetime.timedelta(hours=1)
        )
        with django_capture_on_commit_callbacks(execute=True):
            services.envoyer(decor.locataire, conversation.pk, "Encore moi", mid())
        n = Notification.objects.filter(kind="message.received").order_by("-created_at").first()
        assert n.delivery_status == "skipped" and n.last_error == "silence"

    def test_rappel_au_gerant_apres_deux_heures_une_seule_fois(self, decor):
        conversation, *_ = ouvrir(decor)
        assert services.rappeler_gerants_sans_reponse() == 0
        Conversation.objects.filter(pk=conversation.pk).update(
            last_message_at=timezone.now() - datetime.timedelta(hours=3)
        )
        assert services.rappeler_gerants_sans_reponse() == 1
        assert services.rappeler_gerants_sans_reponse() == 0
        assert (
            Notification.objects.filter(
                kind="message.unanswered_reminder", user=decor.gerant.user
            ).count()
            == 1
        )

    def test_pas_de_rappel_si_le_gerant_a_lu_ou_repondu(self, decor):
        conversation, *_ = ouvrir(decor)
        services.lire(decor.gerant.user, conversation.pk, 1)
        Conversation.objects.filter(pk=conversation.pk).update(
            last_message_at=timezone.now() - datetime.timedelta(hours=3)
        )
        assert services.rappeler_gerants_sans_reponse() == 0

    def test_sms_de_repli_derriere_le_drapeau(self, decor, monkeypatch):
        envoyes = []

        class Faux:
            def envoyer(self, numero, message):
                envoyes.append(numero)

        monkeypatch.setattr("apps.core.providers.sms.fournisseur", lambda: Faux())
        conversation, *_ = ouvrir(decor)
        Conversation.objects.filter(pk=conversation.pk).update(
            last_message_at=timezone.now() - datetime.timedelta(hours=3)
        )
        parametres.definir("SMS_FALLBACK_ENABLED", True)
        services.rappeler_gerants_sans_reponse()
        assert envoyes == [decor.gerant.user.phone_e164]

    def test_annonce_louee_previent_les_conversations_sans_doublon_avec_les_favoris(
        self, decor, django_capture_on_commit_callbacks
    ):
        from apps.listings.services import annonces

        ouvrir(decor)
        with django_capture_on_commit_callbacks(execute=True):
            annonces.marquer_louee(decor.gerant, decor.annonce.pk)
        assert (
            Notification.objects.filter(kind="favorite.unavailable", user=decor.locataire).count()
            == 1
        )


def _ouvrir_api(c, annonce, corps="Bonjour"):
    return c.post(
        "/v1/conversations",
        {"listing_id": str(annonce.pk), "body": corps, "client_msg_id": mid()},
        format="json",
    )


class TestApi:
    def test_parcours_complet(self, decor):
        loc, ger = client_de(decor.locataire, "i-l"), client_de(decor.gerant.user, "i-g")
        r = _ouvrir_api(loc, decor.annonce, "Bonjour")
        assert r.status_code == 201
        ident = r.json()["conversation"]["id"]
        assert _ouvrir_api(loc, decor.annonce, "Re-bonjour").status_code == 200
        liste = ger.get("/v1/conversations").json()
        assert liste["unread_total"] == 2 and liste["items"][0]["unread_count"] == 2
        assert liste["items"][0]["other"]["name"] == decor.locataire.full_name
        corps = {"body": "Oui, libre", "client_msg_id": mid()}
        r = ger.post(f"/v1/conversations/{ident}/messages", corps, format="json")
        assert r.status_code == 201 and r.json()["message"]["seq"] == 3
        assert (
            ger.post(f"/v1/conversations/{ident}/messages", corps, format="json").status_code == 200
        )  # idempotent
        h = loc.get(f"/v1/conversations/{ident}/messages").json()
        assert (
            [m["seq"] for m in h["items"]] == [1, 2, 3] and h["last_seq"] == 3 and not h["has_more"]
        )
        assert [
            m["seq"]
            for m in loc.get(f"/v1/conversations/{ident}/messages?after_seq=2").json()["items"]
        ] == [3]
        assert [
            m["seq"]
            for m in loc.get(f"/v1/conversations/{ident}/messages?before_seq=3").json()["items"]
        ] == [1, 2]
        assert (
            ger.post(f"/v1/conversations/{ident}/read", {"up_to_seq": 3}, format="json").json()[
                "unread_count"
            ]
            == 0
        )
        assert ger.get("/v1/conversations").json()["unread_total"] == 0

    def test_pagination_de_l_historique(self, decor):
        loc = client_de(decor.locataire)
        conversation, *_ = ouvrir(decor)
        Message.objects.bulk_create(
            [
                Message(
                    conversation=conversation,
                    seq=i,
                    sender=decor.locataire,
                    client_msg_id=uuid.uuid4(),
                    body=f"m{i}",
                )
                for i in range(2, 61)
            ]
        )
        Conversation.objects.filter(pk=conversation.pk).update(last_seq=60)
        page = loc.get(f"/v1/conversations/{conversation.pk}/messages").json()
        assert len(page["items"]) == 50 and page["has_more"] and page["items"][0]["seq"] == 11
        ancienne = loc.get(f"/v1/conversations/{conversation.pk}/messages?before_seq=11").json()
        assert [m["seq"] for m in ancienne["items"]] == list(range(1, 11)) and not ancienne[
            "has_more"
        ]

    def test_detail_adresse_privee_reservee_au_gerant(self, decor):
        conversation, *_ = ouvrir(decor)
        decor.annonce.address_private = "Rue 12 maison bleue"
        decor.annonce.save()
        d_ger = client_de(decor.gerant.user).get(f"/v1/conversations/{conversation.pk}").json()
        d_loc = client_de(decor.locataire).get(f"/v1/conversations/{conversation.pk}").json()
        assert (
            d_ger["address_private"] == "Rue 12 maison bleue" and d_loc["address_private"] is None
        )
        assert d_loc["last_seq"] == 1 and d_loc["my_read_seq"] == 1 and d_loc["other_read_seq"] == 0

    def test_filtre_par_annonce_cote_gerant(self, decor):
        autre = ListingFactory(gerant=decor.gerant)
        ouvrir(decor)
        services.ouvrir(decor.locataire, autre.pk, "Et celle-ci ?", mid())
        ger = client_de(decor.gerant.user)
        assert len(ger.get("/v1/conversations").json()["items"]) == 2
        assert len(ger.get(f"/v1/conversations?listing={autre.pk}").json()["items"]) == 1

    def test_erreurs(self, decor):
        loc = client_de(decor.locataire)
        conversation, *_ = ouvrir(decor)
        intrus = client_de(ClientFactory(), "i-x")
        assert intrus.get(f"/v1/conversations/{conversation.pk}").status_code == 404
        assert intrus.get(f"/v1/conversations/{conversation.pk}/messages").status_code == 404
        assert loc.get("/v1/conversations/nimporte").status_code == 404
        assert (
            loc.get(f"/v1/conversations/{conversation.pk}/messages?before_seq=abc").status_code
            == 400
        )
        assert (
            loc.post(
                f"/v1/conversations/{conversation.pk}/messages",
                {"body": "", "client_msg_id": mid()},
                format="json",
            ).status_code
            == 400
        )
        assert (
            loc.post(
                f"/v1/conversations/{conversation.pk}/read", {"up_to_seq": -1}, format="json"
            ).status_code
            == 400
        )
        assert APIClient().get("/v1/conversations").status_code == 401
        assert loc.get("/v1/conversations?cursor=zzz").json()["error"]["code"] == "invalid_cursor"
        gerant_seul = client_de(decor.gerant.user, "i-g").post(
            "/v1/conversations",
            {"listing_id": str(decor.annonce.pk), "body": "x", "client_msg_id": mid()},
            format="json",
        )
        assert gerant_seul.status_code == 403

    def test_rappel_a_l_expediteur_dans_la_reponse(self, decor):
        loc = client_de(decor.locataire)
        r = _ouvrir_api(loc, decor.annonce, "Écris-moi : moi@exemple.com")
        assert r.json()["warning"] and r.json()["message"]["flag_reason"] == "email"

    def test_blocage_silence_et_statut(self, decor):
        loc, ger = client_de(decor.locataire, "i-l"), client_de(decor.gerant.user, "i-g")
        ident = _ouvrir_api(loc, decor.annonce).json()["conversation"]["id"]
        r = ger.post(f"/v1/conversations/{ident}/block")
        assert r.json()["status"] == "blocked" and r.json()["blocked_by_me"] is True
        r = loc.post(
            f"/v1/conversations/{ident}/messages",
            {"body": "?", "client_msg_id": mid()},
            format="json",
        )
        assert r.status_code == 409 and r.json()["error"]["code"] == "conversation_blocked"
        assert loc.post(f"/v1/conversations/{ident}/unblock").status_code == 403
        assert ger.post(f"/v1/conversations/{ident}/unblock").json()["status"] == "open"
        futur = (timezone.now() + datetime.timedelta(hours=1)).isoformat()
        assert (
            ger.patch(f"/v1/conversations/{ident}", {"muted_until": futur}, format="json").json()[
                "muted"
            ]
            is True
        )
        assert (
            ger.patch(f"/v1/conversations/{ident}", {"muted_until": None}, format="json").json()[
                "muted"
            ]
            is False
        )

    def test_le_personnel_n_utilise_pas_la_messagerie_des_clients(self):
        from apps.accounts.tests.fabriques import PersonnelFactory

        assert client_de(PersonnelFactory()).get("/v1/conversations").status_code in (401, 403)

    def test_ticket_websocket_a_usage_unique(self, decor):
        r = client_de(decor.locataire).post("/v1/ws-ticket")
        assert r.status_code == 200 and r.json()["expires_in"] == 30
        ticket = r.json()["ticket"]
        assert ws.consommer(ticket)["utilisateur_id"] == str(decor.locataire.pk)
        assert ws.consommer(ticket) is None
        assert ws.consommer("") is None and ws.consommer("x" * 500) is None
