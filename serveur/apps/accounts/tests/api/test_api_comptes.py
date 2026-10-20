"""API /v1 des comptes : parcours complets, format d'erreur, sécurité des réponses."""

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.models import Device, User
from apps.accounts.services import identifiants
from apps.accounts.tests.fabriques import MOT_DE_PASSE, ClientFactory

pytestmark = [pytest.mark.api, pytest.mark.pg, pytest.mark.django_db]

FORT = "un-Mot-de-passe-solide-42"
TEL = "97565656"
E164 = "+2290197565656"


def api(installation="installation-test-1", **extra) -> APIClient:
    return APIClient(HTTP_X_INSTALLATION_ID=installation, HTTP_X_APP_VERSION="1.0.0", **extra)


def avec_jeton(client: APIClient, acces: str) -> APIClient:
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {acces}")
    return client


def corps_inscription(**extra) -> dict:
    return {
        "username": "awa.bio", "first_name": "Awa", "last_name": "Bio", "phone": TEL, "password": FORT,
        "terms_accepted": True, "platform": "android", **extra,
    }  # fmt: skip


def inscrire(client, capture=None, **extra):
    """Inscription sans code (ADR 0009) ; `capture` reste accepté pour les anciens appels."""
    return client.post("/v1/auth/register", corps_inscription(**extra), format="json")


@pytest.fixture
def session(django_capture_on_commit_callbacks):
    """Un locataire inscrit : (client authentifié, réponse JSON d'inscription)."""
    c = api()
    r = inscrire(c, django_capture_on_commit_callbacks)
    assert r.status_code == 201, r.content
    corps = r.json()
    return avec_jeton(c, corps["tokens"]["access"]), corps


def verifier_format_erreur(reponse, code):
    corps = reponse.json()
    assert set(corps) == {"error"} and set(corps["error"]) == {
        "code",
        "message",
        "fields",
        "request_id",
    }
    assert corps["error"]["code"] == code
    assert corps["error"]["request_id"] == reponse["X-Request-ID"]


class TestParcours:
    def test_inscription_connexion_rafraichissement_deconnexion(
        self, django_capture_on_commit_callbacks
    ):
        c = api()
        r = inscrire(c, django_capture_on_commit_callbacks)
        assert r.status_code == 201
        corps = r.json()
        assert corps["user"]["role"] == "client" and corps["user"]["phone"] == E164
        assert corps["user"]["username"] == "awa.bio" and corps["user"]["first_name"] == "Awa"
        assert corps["tokens"]["expires_in"] == 900 and corps["device_id"]
        assert len(corps["recovery_key"]) == 19  # XXXX-XXXX-XXXX-XXXX, donnée une seule fois

        moi = avec_jeton(api(), corps["tokens"]["access"])
        assert moi.get("/v1/me").json()["full_name"] == "Awa Bio"
        assert "recovery_key" not in moi.get("/v1/me").json()

        r = api().post(
            "/v1/auth/refresh", {"refresh_token": corps["tokens"]["refresh"]}, format="json"
        )
        assert r.status_code == 200
        nouveaux = r.json()
        assert nouveaux["refresh"] != corps["tokens"]["refresh"]

        c2 = avec_jeton(api(), nouveaux["access"])
        assert c2.post("/v1/auth/logout").status_code == 204
        assert c2.get("/v1/me").status_code == 401
        r = api().post("/v1/auth/refresh", {"refresh_token": nouveaux["refresh"]}, format="json")
        assert r.status_code == 401

    def test_connexion(self):
        ClientFactory(phone_e164=E164, username="kofi.zongo")
        r = api().post(
            "/v1/auth/login",
            {"username": "Kofi.Zongo", "password": MOT_DE_PASSE, "platform": "ios"},
            format="json",
        )
        assert r.status_code == 200  # majuscules ignorées
        assert r.json()["user"]["phone"] == E164
        assert Device.objects.get().platform == "ios"

    def test_connexion_par_numero_pendant_la_transition(self):
        ClientFactory(phone_e164=E164, username="ancien.compte")
        corps = {"username": TEL, "password": MOT_DE_PASSE, "platform": "ios"}
        assert api().post("/v1/auth/login", corps, format="json").status_code == 200
        ClientFactory(
            phone_e164=E164
        )  # le numéro désigne deux comptes : plus de connexion par numéro
        assert (
            api("installation-test-3").post("/v1/auth/login", corps, format="json").status_code
            == 401
        )

    def test_mot_de_passe_oublie_par_cle_de_secours(self, session):
        _, corps = session
        c = api("installation-test-2")
        r = c.post(
            "/v1/auth/password/recovery-key",
            {"username": "awa.bio", "recovery_key": corps["recovery_key"].lower(), "new_password": "encore-un-autre-42"},
            format="json",
        )  # fmt: skip
        assert r.status_code == 200 and r.json()["recovery_key"] != corps["recovery_key"]
        assert avec_jeton(api(), corps["tokens"]["access"]).get("/v1/me").status_code == 401
        r = api().post(
            "/v1/auth/login",
            {"username": "awa.bio", "password": "encore-un-autre-42", "platform": "android"},
            format="json",
        )
        assert r.status_code == 200
        # l'ancienne clé a servi : elle ne vaut plus rien
        r = c.post(
            "/v1/auth/password/recovery-key",
            {"username": "awa.bio", "recovery_key": corps["recovery_key"], "new_password": "troisieme-Mot-42"},
            format="json",
        )  # fmt: skip
        assert r.status_code == 401


class TestIdentifiantsApi:
    def test_disponibilite_et_suggestions(self, session):
        r = api().get(
            "/v1/auth/username-available",
            {"username": "AWA.BIO", "first_name": "Awa", "last_name": "Bio"},
        )
        corps = r.json()
        assert corps["available"] is False and corps["suggestions"][0] == "awa.bio2"
        assert (
            api().get("/v1/auth/username-available", {"username": "kofi"}).json()["available"]
            is True
        )
        reserve = api().get("/v1/auth/username-available", {"username": "admin"}).json()
        assert reserve["available"] is False and "réservé" in reserve["message"]

    def test_nom_deja_pris_et_numero_partage(self, session):
        r = inscrire(api("installation-test-2"))
        assert r.status_code == 409
        verifier_format_erreur(r, "username_taken")
        # le numéro n'est plus unique (ADR 0009) : un autre compte peut l'indiquer
        assert inscrire(api("installation-test-3"), username="awa.bio.2").status_code == 201

    def test_lien_par_email_reponse_identique(self, session):
        inconnu = api().post(
            "/v1/auth/password/email-link", {"identifier": "personne"}, format="json"
        )
        connu = api().post("/v1/auth/password/email-link", {"identifier": "awa.bio"}, format="json")
        assert inconnu.status_code == connu.status_code == 202

    def test_cle_fausse_uniforme_et_verrouillee(self, session):
        c = api("installation-test-5")
        corps = {
            "username": "awa.bio",
            "recovery_key": "AAAA-BBBB-CCCC-DDDD",
            "new_password": "encore-un-autre-42",
        }
        reponses = [
            c.post("/v1/auth/password/recovery-key", corps, format="json") for _ in range(5)
        ]
        inconnu = c.post(
            "/v1/auth/password/recovery-key", {**corps, "username": "personne"}, format="json"
        )
        assert {r.status_code for r in reponses} == {401}
        assert reponses[0].json()["error"]["message"] == inconnu.json()["error"]["message"]
        _, inscription_corps = session
        bonne = c.post(
            "/v1/auth/password/recovery-key",
            {**corps, "recovery_key": inscription_corps["recovery_key"]},
            format="json",
        )
        assert bonne.status_code == 401  # verrouillé : même la bonne clé est refusée un moment

    def test_regenerer_la_cle(self, session):
        client, corps = session
        assert (
            client.post("/v1/me/recovery-key", {"password": "faux"}, format="json").status_code
            == 400
        )
        r = client.post("/v1/me/recovery-key", {"password": FORT}, format="json")
        assert r.status_code == 200 and r.json()["recovery_key"] != corps["recovery_key"]
        u = User.objects.get(pk=corps["user"]["id"])
        assert identifiants.cle_correcte(u, r.json()["recovery_key"])
        assert not identifiants.cle_correcte(u, corps["recovery_key"])


class TestFormatsEtEntetes:
    def test_installation_obligatoire(self):
        r = APIClient().post(
            "/v1/auth/login",
            {"username": "awa.bio", "password": "x", "platform": "android"},
            format="json",
        )
        assert r.status_code == 400
        verifier_format_erreur(r, "validation_error")

    @pytest.mark.parametrize("valeur", ["court", "a" * 65, "contient des espaces", "<script>"])
    def test_installation_invalide(self, valeur):
        r = APIClient(HTTP_X_INSTALLATION_ID=valeur).post(
            "/v1/auth/register",
            corps_inscription(),
            format="json",
        )
        assert r.status_code == 400

    def test_inscription_sans_installation_ne_cree_aucun_compte(self):
        r = APIClient().post("/v1/auth/register", corps_inscription(), format="json")
        assert r.status_code == 400 and not User.objects.exists()
        assert inscrire(api()).status_code == 201  # le client corrige l'en-tête et réessaie

    def test_champs_manquants(self):
        r = api().post("/v1/auth/login", {}, format="json")
        assert r.status_code == 400
        assert {"username", "platform"} <= set(r.json()["error"]["fields"])

    def test_corps_non_json(self):
        r = api().post("/v1/auth/login", "phone=1", content_type="text/plain")
        assert r.status_code == 415
        verifier_format_erreur(r, "unsupported_media_type")

    def test_json_malforme(self):
        r = api().post("/v1/auth/login", "{pas du json", content_type="application/json")
        assert r.status_code == 400
        verifier_format_erreur(r, "parse_error")

    def test_methode_non_autorisee(self):
        r = api().get("/v1/auth/login")
        assert r.status_code == 405
        verifier_format_erreur(r, "method_not_allowed")

    def test_les_reponses_d_authentification_ne_sont_pas_cachees(self, session):
        client, _ = session
        assert client.get("/v1/me")["Cache-Control"] == "no-store"
        assert api().post("/v1/auth/login", {}, format="json")["Cache-Control"] == "no-store"

    def test_pas_de_cookie_ni_de_csrf(self, session):
        client, _ = session
        assert "Set-Cookie" not in client.get("/v1/me")
        csrf = APIClient(enforce_csrf_checks=True, HTTP_X_INSTALLATION_ID="installation-test-1")
        r = csrf.post(
            "/v1/auth/login",
            {"username": "awa.bio", "password": "x", "platform": "android"},
            format="json",
        )
        assert r.status_code == 401  # refus d'identifiants, pas de refus CSRF (403)


class TestSecuriteDesAcces:
    @pytest.mark.parametrize("chemin", ["/v1/me", "/v1/devices", "/v1/me/preferences"])
    def test_sans_jeton(self, chemin):
        r = api().get(chemin)
        assert r.status_code == 401 and r["WWW-Authenticate"].startswith("Bearer")
        verifier_format_erreur(r, "not_authenticated")

    @pytest.mark.parametrize(
        "en_tete", ["Bearer", "Bearer a b", "Bearer abc.def.ghi", "Basic dXNlcjpwYXNz", "bearer"]
    )
    def test_jeton_mal_forme(self, en_tete):
        c = api(HTTP_AUTHORIZATION=en_tete)
        assert c.get("/v1/me").status_code == 401

    def test_jeton_expire(self, session):
        import time_machine

        client, _ = session
        with time_machine.travel(timezone.now() + timezone.timedelta(minutes=16), tick=False):
            r = client.get("/v1/me")
        assert r.status_code == 401
        verifier_format_erreur(r, "invalid_token")

    def test_compte_suspendu(self, session):
        client, corps = session
        from apps.accounts.services import jetons

        User.objects.filter(pk=corps["user"]["id"]).update(status="banned")
        jetons.invalider_utilisateur(corps["user"]["id"])
        r = client.get("/v1/me")
        assert r.status_code == 403
        verifier_format_erreur(r, "account_suspended")

    def test_connexion_en_echec_est_uniforme_et_verrouille(self):
        ClientFactory(phone_e164=E164, username="kofi.zongo")
        c = api()
        corps = {"username": "kofi.zongo", "password": "faux", "platform": "android"}
        reponses = [c.post("/v1/auth/login", corps, format="json") for _ in range(5)]
        inconnu = api("installation-test-9").post(
            "/v1/auth/login", {**corps, "username": "personne.inconnue"}, format="json"
        )
        assert {r.status_code for r in reponses} == {401}
        assert reponses[0].json()["error"]["message"] == inconnu.json()["error"]["message"]
        bon = c.post("/v1/auth/login", {**corps, "password": MOT_DE_PASSE}, format="json")
        assert bon.status_code == 401 and int(bon["Retry-After"]) > 0

    def test_limite_de_debit_par_adresse(self):
        c = api()
        codes = [c.post("/v1/auth/login", {}, format="json").status_code for _ in range(32)]
        assert codes[:30] == [400] * 30 and codes[30:] == [429, 429]
        r = c.post("/v1/auth/login", {}, format="json")
        verifier_format_erreur(r, "rate_limited")
        assert int(r["Retry-After"]) >= 1

    def test_les_adresses_sont_comptees_separement(self):
        for _ in range(31):
            api().post("/v1/auth/login", {}, format="json")
        r = APIClient(HTTP_X_INSTALLATION_ID="installation-test-1", REMOTE_ADDR="41.0.0.99").post(
            "/v1/auth/login", {}, format="json"
        )
        assert r.status_code == 400

    def test_x_forwarded_for_ignore_hors_proxy(self):
        for _ in range(31):
            api().post("/v1/auth/login", {}, format="json", HTTP_X_FORWARDED_FOR="9.9.9.9")
        r = api().post("/v1/auth/login", {}, format="json", HTTP_X_FORWARDED_FOR="8.8.8.8")
        assert r.status_code == 429  # l'en-tête falsifié ne permet pas de contourner la limite

    def test_x_forwarded_for_lu_derriere_caddy(self, settings):
        settings.USE_X_FORWARDED_FOR = True
        for _ in range(31):
            api().post("/v1/auth/login", {}, format="json", HTTP_X_FORWARDED_FOR="9.9.9.9")
        r = api().post("/v1/auth/login", {}, format="json", HTTP_X_FORWARDED_FOR="8.8.8.8")
        assert r.status_code == 400


class TestCompteApi:
    def test_profil(self, session):
        client, _ = session
        r = client.patch("/v1/me", {"first_name": "Aminata", "last_name": "Sanni"}, format="json")
        assert r.status_code == 200 and r.json()["full_name"] == "Aminata Sanni"
        assert client.patch("/v1/me", {"first_name": " "}, format="json").status_code == 400

    def test_le_profil_n_expose_aucun_champ_interne(self, session):
        client, _ = session
        assert set(client.get("/v1/me").json()) == {
            "id",
            "username",
            "first_name",
            "last_name",
            "full_name",
            "email",
            "recovery_key_created_at",
            "occupation",
            "role",
            "phone",
            "terms_version",
            "created_at",
        }

    def test_role_non_modifiable_par_le_profil(self, session):
        client, corps = session
        client.patch(
            "/v1/me",
            {"first_name": "Pirate", "role": "admin", "status": "active", "username": "admin2"},
            format="json",
        )
        u = User.objects.get(pk=corps["user"]["id"])
        assert u.role == "client" and u.username == "awa.bio"

    def test_changement_de_mot_de_passe(self, session):
        client, corps = session
        autre = api("installation-test-2")
        r = autre.post(
            "/v1/auth/login",
            {"username": "awa.bio", "password": FORT, "platform": "ios"},
            format="json",
        )
        jeton_autre = r.json()["tokens"]["access"]
        r = client.post(
            "/v1/auth/password/change",
            {"current_password": FORT, "new_password": "nouveau-Mot-42-passe"},
            format="json",
        )
        assert r.status_code == 204
        assert client.get("/v1/me").status_code == 200  # l'appareil courant reste connecté
        assert avec_jeton(api(), jeton_autre).get("/v1/me").status_code == 401
        assert corps

    def test_changement_de_mot_de_passe_ancien_faux(self, session):
        client, _ = session
        r = client.post(
            "/v1/auth/password/change",
            {"current_password": "faux", "new_password": "nouveau-Mot-42-passe"},
            format="json",
        )
        assert r.status_code == 400
        verifier_format_erreur(r, "invalid_password")

    def test_preferences(self, session):
        client, _ = session
        assert client.get("/v1/me/preferences").json() == {}
        r = client.put(
            "/v1/me/preferences", {"messages": {"push": False, "apercu": False}}, format="json"
        )
        assert r.status_code == 200 and r.json()["messages"]["push"] is False
        r = client.put("/v1/me/preferences", {"securite": {"push": False}}, format="json")
        assert r.status_code == 400

    def test_changement_de_numero(self, session):
        client, _ = session
        r = client.post(
            "/v1/me/phone/change", {"password": "faux", "phone": "97787878"}, format="json"
        )
        assert r.status_code == 400
        r = client.post(
            "/v1/me/phone/change", {"password": FORT, "phone": "97787878"}, format="json"
        )
        assert r.status_code == 200 and r.json()["phone"] == "+2290197787878"

    def test_ajout_d_un_email_confirme_par_lien(self, session, django_capture_on_commit_callbacks):
        from apps.accounts.services import compte

        client, corps = session
        with django_capture_on_commit_callbacks(execute=True):
            assert (
                client.post("/v1/me/email", {"email": "awa@exemple.bj"}, format="json").status_code
                == 202
            )
        u = User.objects.get(pk=corps["user"]["id"])
        assert u.email is None  # rien d'enregistré avant la confirmation
        jeton = identifiants.creer_jeton(u, "email", a="awa@exemple.bj")
        compte.confirmer_email(jeton)
        assert client.get("/v1/me").json()["email"] == "awa@exemple.bj"

    def test_suppression_du_compte(self, session):
        client, corps = session
        assert client.delete("/v1/me", {"password": "faux"}, format="json").status_code == 400
        assert client.delete("/v1/me", {"password": FORT}, format="json").status_code == 204
        assert client.get("/v1/me").status_code == 401
        supprime = User.objects.get(pk=corps["user"]["id"])
        assert supprime.status == "deleted" and supprime.username.startswith("supprime.")
        assert inscrire(api("installation-test-4")).status_code == 201  # le nom est libéré


class TestAppareilsApi:
    def test_liste_marque_l_appareil_courant(self, session):
        client, corps = session
        api("installation-test-2").post(
            "/v1/auth/login",
            {"username": "awa.bio", "password": FORT, "platform": "ios"},
            format="json",
        )
        liste = client.get("/v1/devices").json()
        assert len(liste) == 2
        courants = [a["id"] for a in liste if a["current"]]
        assert courants == [corps["device_id"]]
        assert all("last_ip" not in a and "refresh_hash" not in a for a in liste)

    def test_deconnecter_un_autre_appareil(self, session):
        client, _ = session
        autre = api("installation-test-2")
        r = autre.post(
            "/v1/auth/login",
            {"username": "awa.bio", "password": FORT, "platform": "ios"},
            format="json",
        )
        assert client.delete(f"/v1/devices/{r.json()['device_id']}").status_code == 204
        assert avec_jeton(api(), r.json()["tokens"]["access"]).get("/v1/me").status_code == 401
        assert client.get("/v1/me").status_code == 200

    def test_impossible_de_deconnecter_l_appareil_d_un_autre_compte(self, session):
        client, _ = session
        victime = ClientFactory(phone_e164="+2290197343434")
        d = Device.objects.create(
            user=victime, installation_id="installation-victime", platform="android",
            refresh_expires_at="2099-01-01T00:00:00Z",
        )  # fmt: skip
        r = client.delete(f"/v1/devices/{d.pk}")
        assert r.status_code == 404
        d.refresh_from_db()
        assert d.revoked_at is None

    def test_jeton_de_notification(self, session):
        client, corps = session
        r = client.put(
            "/v1/devices/current/push-token",
            {"provider": "expo", "token": "ExponentPushToken[x]"},
            format="json",
        )
        assert r.status_code == 204
        assert Device.objects.get(pk=corps["device_id"]).push_token == "ExponentPushToken[x]"
        assert (
            client.put(
                "/v1/devices/current/push-token",
                {"provider": "pigeon", "token": "x"},
                format="json",
            ).status_code
            == 400
        )
