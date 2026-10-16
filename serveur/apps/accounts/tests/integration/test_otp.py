"""Service OTP : demande, protections anti-abus (§5.3), vérification, jeton à usage unique."""

import logging
import re

import pytest
from django.core.cache import cache
from django.utils import timezone

from apps.accounts.models import OtpCode
from apps.accounts.services import otp
from apps.accounts.tests.fabriques import ClientFactory
from apps.audit.models import AuditLog
from apps.core import parametres
from apps.core.errors import ErreurMetier
from apps.core.providers.sms import CLE_BOITE_DEV

pytestmark = [pytest.mark.integration, pytest.mark.pg, pytest.mark.django_db]

NUMERO = "+2290197654321"
SAISIE = "97654321"


def dernier_code() -> str:
    boite = cache.get(CLE_BOITE_DEV) or []
    assert boite, "aucun SMS envoyé"
    return re.search(r"\b(\d{6})\b", boite[0]["message"]).group(1)


def demander(objet="signup", saisie=SAISIE, **ctx):
    otp.demander(saisie, objet, otp.Contexte(**ctx))


def vieillir(minutes=0, heures=0):
    """Antidate les codes existants (les plafonds se calculent sur `created_at`)."""
    OtpCode.objects.update(
        created_at=timezone.now() - timezone.timedelta(minutes=minutes, hours=heures)
    )


def erreur_de(fonction, *args, **kwargs) -> ErreurMetier:
    with pytest.raises(ErreurMetier) as e:
        fonction(*args, **kwargs)
    return e.value


class TestDemande:
    def test_cree_un_code_hache_et_envoie_le_sms(self, django_capture_on_commit_callbacks):
        with django_capture_on_commit_callbacks(execute=True):
            demander(installation_id="inst-1", ip="41.0.0.1")
        ligne = OtpCode.objects.get()
        assert ligne.phone_e164 == NUMERO and ligne.purpose == "signup"
        assert re.fullmatch(r"[0-9a-f]{64}", ligne.code_hmac)
        assert dernier_code() not in ligne.code_hmac
        assert 299 <= (ligne.expires_at - timezone.now()).total_seconds() <= 300
        assert ligne.installation_id == "inst-1" and ligne.ip == "41.0.0.1"
        assert ligne.provider_ref and ligne.provider_ref.startswith("console-")

    def test_le_code_a_six_chiffres(self, django_capture_on_commit_callbacks):
        with django_capture_on_commit_callbacks(execute=True):
            demander()
        assert re.fullmatch(r"\d{6}", dernier_code())

    def test_numero_invalide_refuse(self):
        e = erreur_de(demander, saisie="123")
        assert e.code == "validation_error" and "phone" in e.champs

    def test_pays_non_autorise_refuse(self):
        assert erreur_de(demander, saisie="+33612345678").code == "validation_error"

    def test_pays_autorise_par_le_parametre(self, django_capture_on_commit_callbacks):
        parametres.definir("OTP_ALLOWED_COUNTRIES", ["BJ", "FR"])
        with django_capture_on_commit_callbacks(execute=True):
            demander(saisie="+33612345678")
        assert OtpCode.objects.get().phone_e164 == "+33612345678"

    @pytest.mark.parametrize(
        "saisie", ["97654321", "0197654321", "+229 97 65 43 21", "00229 0197654321"]
    )
    def test_formats_beninois_normalises(self, saisie, django_capture_on_commit_callbacks):
        with django_capture_on_commit_callbacks(execute=True):
            demander(saisie=saisie)
        assert OtpCode.objects.get().phone_e164 == NUMERO

    def test_code_de_debogage_en_developpement(self, settings, django_capture_on_commit_callbacks):
        settings.OTP_DEBUG_CODE = "424242"
        with django_capture_on_commit_callbacks(execute=True):
            demander()
        assert dernier_code() == "424242"

    def test_le_code_n_est_jamais_journalise(self, caplog, django_capture_on_commit_callbacks):
        caplog.set_level(logging.DEBUG)
        with django_capture_on_commit_callbacks(execute=True):
            demander()
        assert dernier_code() not in caplog.text


class TestAucuneFuiteDExistence:
    @pytest.mark.parametrize("objet", ["reset_password", "change_phone", "signup"])
    def test_meme_reponse_quel_que_soit_le_numero(self, objet, django_capture_on_commit_callbacks):
        ClientFactory(phone_e164=NUMERO)
        with django_capture_on_commit_callbacks(execute=True):
            existant = otp.demander(SAISIE, objet, otp.Contexte())
        with django_capture_on_commit_callbacks(execute=True):
            inconnu = otp.demander("97111111", objet, otp.Contexte())
        assert existant is None and inconnu is None  # même retour, aucune exception

    def test_reinitialisation_sans_compte_n_envoie_aucun_sms(
        self, django_capture_on_commit_callbacks
    ):
        with django_capture_on_commit_callbacks(execute=True):
            demander("reset_password")
        assert not cache.get(CLE_BOITE_DEV)
        ligne = OtpCode.objects.get()
        assert ligne.provider_ref == otp.MARQUE_NON_ENVOYE  # tracé pour les plafonds

    def test_reinitialisation_avec_compte_envoie_un_sms(self, django_capture_on_commit_callbacks):
        ClientFactory(phone_e164=NUMERO)
        with django_capture_on_commit_callbacks(execute=True):
            demander("reset_password")
        assert dernier_code()

    def test_les_lignes_sans_sms_ne_consomment_pas_le_budget(self):
        demander("reset_password")
        assert otp._envoyes_aujourdhui("reset_password") == 0

    def test_changement_de_numero_vers_un_numero_deja_pris_n_envoie_rien(
        self, django_capture_on_commit_callbacks
    ):
        ClientFactory(phone_e164=NUMERO)
        with django_capture_on_commit_callbacks(execute=True):
            demander("change_phone")
        assert not cache.get(CLE_BOITE_DEV)


class TestPlafonds:
    def test_delai_avant_renvoi(self):
        demander()
        e = erreur_de(demander)
        assert e.code == "otp_resend_too_soon" and e.statut == 429
        assert 1 <= int(e.entetes["Retry-After"]) <= 60

    def test_renvoi_possible_apres_le_delai(self):
        demander()
        vieillir(minutes=2)
        demander()
        assert OtpCode.objects.count() == 2

    def test_trois_demandes_par_heure_et_par_numero(self):
        for _ in range(3):
            demander()
            vieillir(minutes=5)
        e = erreur_de(demander)
        assert e.code == "otp_rate_limited" and e.statut == 429

    def test_le_plafond_horaire_se_libere(self):
        for _ in range(3):
            demander()
            vieillir(minutes=5)
        vieillir(minutes=61)
        demander()

    def test_dix_demandes_par_jour_et_par_appareil_avec_attestation(self):
        for n in range(10):
            demander(
                saisie=f"9700{n:04d}",
                installation_id="inst-A",
                jeton_attestation="attestation-valide",
            )
        e = erreur_de(
            demander,
            saisie="97009999",
            installation_id="inst-A",
            jeton_attestation="attestation-valide",
        )
        assert e.code == "otp_rate_limited"

    def test_plafond_appareil_reduit_de_moitie_sans_attestation(self):
        for n in range(5):
            demander(saisie=f"9700{n:04d}", installation_id="inst-B")
        assert (
            erreur_de(demander, saisie="97009999", installation_id="inst-B").code
            == "otp_rate_limited"
        )

    def test_appareils_distincts_comptes_separement(self):
        for n in range(5):
            demander(saisie=f"9700{n:04d}", installation_id="inst-C")
        demander(saisie="97009999", installation_id="inst-D")

    def test_soixante_demandes_par_jour_et_par_plage_ip(self):
        OtpCode.objects.bulk_create(
            OtpCode(
                phone_e164=f"+22901970{n:05d}", purpose="signup", code_hmac="a" * 64,
                expires_at=timezone.now(), ip=f"41.0.0.{n % 250}",
            )
            for n in range(60)
        )  # fmt: skip
        e = erreur_de(demander, ip="41.0.0.77")
        assert e.code == "otp_rate_limited"

    def test_une_autre_plage_ip_n_est_pas_touchee(self):
        OtpCode.objects.bulk_create(
            OtpCode(
                phone_e164=f"+22901970{n:05d}", purpose="signup", code_hmac="a" * 64,
                expires_at=timezone.now(), ip=f"41.0.0.{n % 250}",
            )
            for n in range(60)
        )  # fmt: skip
        demander(ip="41.0.1.5")

    def test_ipv6_plafonnee_par_plage_64(self):
        OtpCode.objects.bulk_create(
            OtpCode(
                phone_e164=f"+22901970{n:05d}", purpose="signup", code_hmac="a" * 64,
                expires_at=timezone.now(), ip=f"2001:db8:1:2::{n:x}",
            )
            for n in range(1, 61)
        )  # fmt: skip
        assert erreur_de(demander, ip="2001:db8:1:2::ffff").code == "otp_rate_limited"
        demander(ip="2001:db8:1:3::1")

    def test_plafonds_modifiables_sans_redeploiement(self):
        parametres.definir("OTP_PHONE_PER_HOUR", 1)
        demander()
        vieillir(minutes=5)
        assert erreur_de(demander).code == "otp_rate_limited"


class TestBudget:
    def petit_budget(self, total=10):
        parametres.definir(
            "OTP_DAILY_BUDGET",
            {"signup": total, "reset_password": 5, "change_phone": 5},
        )

    def remplir(self, n, objet="signup"):
        OtpCode.objects.bulk_create(
            OtpCode(
                phone_e164=f"+22901971{i:05d}", purpose=objet, code_hmac="a" * 64,
                expires_at=timezone.now(), provider_ref="console-x",
            )
            for i in range(n)
        )  # fmt: skip

    def test_sous_le_seuil_aucune_friction_sur_l_app(self):
        self.petit_budget()
        self.remplir(7)
        demander()

    def test_a_80_pour_cent_le_site_exige_le_defi_anti_robot(self):
        self.petit_budget()
        self.remplir(8)
        assert erreur_de(demander, surface="web").code == "captcha_required"
        demander(surface="web", jeton_captcha="captcha-ok")

    def test_a_80_pour_cent_l_app_exige_l_attestation(self):
        self.petit_budget()
        self.remplir(8)
        assert erreur_de(demander).code == "attestation_required"
        demander(jeton_attestation="attestation-valide")

    def test_a_80_pour_cent_les_plafonds_sont_divises_par_deux(self):
        self.petit_budget(total=100)
        self.remplir(80)
        for _ in range(1):
            demander(jeton_attestation="attestation-valide")
            vieillir(minutes=5)
        demander(jeton_attestation="attestation-valide")  # 2 par heure et par numéro (3 // 2)
        vieillir(minutes=5)
        assert (
            erreur_de(demander, jeton_attestation="attestation-valide").code == "otp_rate_limited"
        )

    def test_a_100_pour_cent_les_demandes_sont_refusees_et_l_alerte_part_une_fois(self):
        self.petit_budget()
        self.remplir(10)
        e = erreur_de(demander, jeton_attestation="attestation-valide")
        assert e.code == "otp_unavailable" and e.statut == 503
        assert "Retry-After" in e.entetes
        erreur_de(demander, jeton_attestation="attestation-valide")
        assert AuditLog.objects.filter(action="otp.budget_epuise").count() == 1

    def test_un_usage_epuise_ne_bloque_pas_les_autres(self, django_capture_on_commit_callbacks):
        self.petit_budget()
        self.remplir(10, objet="signup")
        ClientFactory(phone_e164=NUMERO)
        with django_capture_on_commit_callbacks(execute=True):
            demander("reset_password")
        assert dernier_code()

    def test_le_budget_vient_de_la_base_pas_du_cache(self):
        self.petit_budget()
        self.remplir(10)
        cache.clear()
        assert erreur_de(demander, jeton_attestation="attestation-valide").code == "otp_unavailable"

    def test_budget_nul_ferme_l_usage(self):
        parametres.definir("OTP_DAILY_BUDGET", {"signup": 0})
        assert erreur_de(demander).code == "otp_unavailable"


class TestSiteEtDefi:
    def test_le_site_exige_le_defi_quand_il_est_active(self):
        assert erreur_de(demander, surface="web").code == "captcha_required"

    def test_defi_desactivable(self):
        parametres.definir("TURNSTILE_ENABLED", False)
        demander(surface="web")

    def test_mauvais_jeton_de_defi_refuse(self):
        assert erreur_de(demander, surface="web", jeton_captcha="faux").code == "captcha_required"


class TestVerification:
    def emettre(self, objet="signup", django_capture_on_commit_callbacks=None):
        demander(objet)
        return dernier_code()

    @pytest.fixture
    def code(self, django_capture_on_commit_callbacks):
        with django_capture_on_commit_callbacks(execute=True):
            demander()
        return dernier_code()

    def test_bon_code_donne_un_jeton(self, code):
        jeton = otp.verifier(SAISIE, "signup", code)
        assert otp.consommer_jeton(jeton, "signup") == NUMERO
        assert OtpCode.objects.get().consumed_at is not None

    def test_le_jeton_est_a_usage_unique(self, code):
        jeton = otp.verifier(SAISIE, "signup", code)
        otp.consommer_jeton(jeton, "signup")
        assert erreur_de(otp.consommer_jeton, jeton, "signup").code == "otp_token_invalid"

    def test_le_jeton_est_lie_a_l_usage(self, code):
        jeton = otp.verifier(SAISIE, "signup", code)
        assert erreur_de(otp.consommer_jeton, jeton, "reset_password").code == "otp_token_invalid"

    def test_jeton_falsifie_refuse(self, code):
        jeton = otp.verifier(SAISIE, "signup", code)
        assert (
            erreur_de(otp.consommer_jeton, jeton[:-3] + "abc", "signup").code == "otp_token_invalid"
        )

    def test_jeton_expire_apres_dix_minutes(self, code, monkeypatch):
        jeton = otp.verifier(SAISIE, "signup", code)
        monkeypatch.setattr(otp, "VALIDITE_JETON_S", 0)
        import time

        time.sleep(1.1)
        assert erreur_de(otp.consommer_jeton, jeton, "signup").code == "otp_token_invalid"

    def test_code_incorrect_decompte_les_essais(self, code):
        faux = "000000" if code != "000000" else "111111"
        e = erreur_de(otp.verifier, SAISIE, "signup", faux)
        assert e.code == "otp_invalid" and "4 essai" in e.message
        assert OtpCode.objects.get().attempts == 1  # le décompte survit à l'erreur

    def test_cinq_essais_puis_verrouillage_meme_avec_le_bon_code(self, code):
        faux = "000000" if code != "000000" else "111111"
        for _ in range(5):
            assert erreur_de(otp.verifier, SAISIE, "signup", faux).code == "otp_invalid"
        e = erreur_de(otp.verifier, SAISIE, "signup", code)
        assert e.code == "otp_locked" and e.statut == 429
        assert OtpCode.objects.get().consumed_at is None

    def test_code_expire(self, code):
        OtpCode.objects.update(expires_at=timezone.now() - timezone.timedelta(seconds=1))
        assert erreur_de(otp.verifier, SAISIE, "signup", code).code == "otp_expired"

    def test_code_deja_utilise(self, code):
        otp.verifier(SAISIE, "signup", code)
        assert erreur_de(otp.verifier, SAISIE, "signup", code).code == "otp_expired"

    def test_un_nouveau_code_remplace_l_ancien(self, code, django_capture_on_commit_callbacks):
        ancien = code
        vieillir(minutes=2)
        with django_capture_on_commit_callbacks(execute=True):
            demander()
        nouveau = dernier_code()
        if ancien != nouveau:
            assert erreur_de(otp.verifier, SAISIE, "signup", ancien).code == "otp_invalid"
        otp.verifier(SAISIE, "signup", nouveau)

    def test_code_pour_un_autre_usage_refuse(self, code):
        assert erreur_de(otp.verifier, SAISIE, "reset_password", code).code == "otp_expired"

    @pytest.mark.parametrize("mauvais", ["", "abc123", "12345", "1234567", " ", "12 456"])
    def test_formats_de_code_invalides(self, code, mauvais):
        assert erreur_de(otp.verifier, SAISIE, "signup", mauvais).code == "otp_invalid"

    def test_numero_sans_demande(self):
        assert erreur_de(otp.verifier, "97000000", "signup", "123456").code == "otp_expired"

    def test_un_numero_inconnu_ne_peut_pas_etre_valide_meme_en_devinant(
        self, django_capture_on_commit_callbacks
    ):
        # reset_password sur un numéro sans compte : ligne « non envoyée », code jamais communiqué à personne
        with django_capture_on_commit_callbacks(execute=True):
            demander("reset_password")
        assert erreur_de(otp.verifier, SAISIE, "reset_password", "123456").code in {"otp_invalid"}
