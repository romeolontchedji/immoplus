import pytest
from django.core.exceptions import ImproperlyConfigured

from apps.core.providers import captcha

pytestmark = pytest.mark.unitaire


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
