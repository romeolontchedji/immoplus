import hashlib
import hmac
import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest
from django.core.cache import cache
from django.core.exceptions import ImproperlyConfigured

from apps.core.providers import captcha, sms

pytestmark = pytest.mark.unitaire


class AgregateurFactice:
    """Serveur HTTP local qui joue un agrégateur SMS : enregistre les requêtes et suit un scénario de réponses."""

    def __init__(self, reponses):
        self.reponses = list(reponses)
        self.recues = []
        proprietaire = self

        class Gestionnaire(BaseHTTPRequestHandler):
            def do_POST(self):
                taille = int(self.headers.get("Content-Length", 0))
                proprietaire.recues.append((dict(self.headers), self.rfile.read(taille)))
                code, corps = proprietaire.reponses.pop(0) if proprietaire.reponses else (200, {})
                self.send_response(code)
                self.end_headers()
                self.wfile.write(json.dumps(corps).encode())

            def log_message(self, *args):
                pass

        self.serveur = HTTPServer(("127.0.0.1", 0), Gestionnaire)
        self.url = f"http://127.0.0.1:{self.serveur.server_port}/envoyer"
        threading.Thread(target=self.serveur.serve_forever, daemon=True).start()

    def arreter(self):
        self.serveur.shutdown()
        self.serveur.server_close()


@pytest.fixture
def agregateur():
    crees = []

    def fabrique(reponses):
        a = AgregateurFactice(reponses)
        crees.append(a)
        return a

    yield fabrique
    for a in crees:
        a.arreter()


class TestSmsConsole:
    def test_ecrit_dans_la_boite_de_developpement(self, settings, capsys):
        cache.clear()
        resultat = sms.ConsoleSmsProvider().envoyer("+2290197123456", "Ton code Immo+ : 123456")
        assert resultat.cout_xof == 0
        assert "123456" in capsys.readouterr().err
        assert cache.get(sms.CLE_BOITE_DEV)[0]["a"] == "+2290197123456"

    def test_refuse_en_production(self, settings):
        settings.DEBUG = False
        settings.DEV_INBOX_ENABLED = False
        with pytest.raises(ImproperlyConfigured):
            sms.ConsoleSmsProvider()

    def test_choix_du_fournisseur(self, settings):
        settings.SMS_PROVIDER = "inconnu"
        with pytest.raises(ImproperlyConfigured):
            sms.fournisseur()
        settings.SMS_PROVIDER = "console"
        assert isinstance(sms.fournisseur(), sms.ConsoleSmsProvider)


class TestSmsHttp:
    def configurer(self, settings, url, **extra):
        settings.SMS_HTTP_URL = url
        settings.SMS_HTTP_TOKEN = "jeton-secret"
        settings.SMS_HTTP_SECRET = "secret-de-signature"
        for k, v in extra.items():
            setattr(settings, k, v)

    def test_url_obligatoire(self, settings):
        settings.SMS_HTTP_URL = ""
        with pytest.raises(ImproperlyConfigured):
            sms.GenericHttpSmsProvider()

    @pytest.mark.parametrize(
        "url", ["file:///etc/passwd", "ftp://x/y", "javascript:alert(1)", "//hote/chemin"]
    )
    def test_schemas_autres_que_http_refuses(self, settings, url):
        settings.SMS_HTTP_URL = url
        with pytest.raises(ImproperlyConfigured):
            sms.GenericHttpSmsProvider()

    def test_envoi_signe_et_lecture_du_cout(self, settings, agregateur):
        a = agregateur([(200, {"id": "msg-42", "cost": 12})])
        self.configurer(settings, a.url)
        resultat = sms.GenericHttpSmsProvider().envoyer("+2290197123456", "bonjour")
        assert (resultat.reference, resultat.cout_xof) == ("msg-42", 12)
        en_tetes, corps = a.recues[0]
        assert json.loads(corps) == {"to": "+2290197123456", "message": "bonjour"}
        assert en_tetes["Authorization"] == "Bearer jeton-secret"
        attendu = hmac.new(b"secret-de-signature", corps, hashlib.sha256).hexdigest()
        assert en_tetes["X-Signature"] == attendu

    def test_reessaie_apres_une_erreur_serveur(self, settings, agregateur):
        a = agregateur([(503, {}), (502, {}), (200, {"id": "ok"})])
        self.configurer(settings, a.url, SMS_HTTP_RETRIES=2)
        assert sms.GenericHttpSmsProvider().envoyer("+2290197123456", "x").reference == "ok"
        assert len(a.recues) == 3

    def test_abandonne_apres_les_reprises(self, settings, agregateur):
        a = agregateur([(500, {})] * 5)
        self.configurer(settings, a.url, SMS_HTTP_RETRIES=1)
        with pytest.raises(sms.ErreurFournisseurSms):
            sms.GenericHttpSmsProvider().envoyer("+2290197123456", "x")
        assert len(a.recues) == 2

    def test_ne_reessaie_pas_une_erreur_du_client(self, settings, agregateur):
        a = agregateur([(400, {})] * 3)
        self.configurer(settings, a.url, SMS_HTTP_RETRIES=2)
        with pytest.raises(sms.ErreurFournisseurSms):
            sms.GenericHttpSmsProvider().envoyer("+2290197123456", "x")
        assert len(a.recues) == 1

    def test_serveur_injoignable(self, settings):
        self.configurer(
            settings, "http://127.0.0.1:1/envoyer", SMS_HTTP_RETRIES=0, SMS_HTTP_TIMEOUT_S=1
        )
        with pytest.raises(sms.ErreurFournisseurSms):
            sms.GenericHttpSmsProvider().envoyer("+2290197123456", "x")

    def test_champs_de_reponse_configurables(self, settings, agregateur):
        a = agregateur([(200, {"message_id": "z9", "prix": 8})])
        self.configurer(
            settings, a.url, SMS_HTTP_REF_FIELD="message_id", SMS_HTTP_COST_FIELD="prix"
        )
        resultat = sms.GenericHttpSmsProvider().envoyer("+2290197123456", "x")
        assert (resultat.reference, resultat.cout_xof) == ("z9", 8)


class TestCaptcha:
    def test_factice(self):
        p = captcha.FakeCaptchaProvider()
        assert p.verifier("captcha-ok") is True
        assert p.verifier("faux") is False
        assert p.verifier(None) is False

    def test_turnstile_exige_son_secret(self, settings):
        settings.TURNSTILE_SECRET = ""
        with pytest.raises(ImproperlyConfigured):
            captcha.TurnstileProvider()

    def test_turnstile_sans_jeton_est_refuse_sans_appel_reseau(self, settings):
        settings.TURNSTILE_SECRET = "s"
        assert captcha.TurnstileProvider().verifier(None) is False

    def test_turnstile_echec_reseau_vaut_refus(self, settings, monkeypatch):
        settings.TURNSTILE_SECRET = "s"
        monkeypatch.setattr(captcha, "URL_VERIFICATION", "http://127.0.0.1:1/x")
        assert captcha.TurnstileProvider().verifier("jeton") is False
