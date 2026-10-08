"""Inscription, activation du gérant, mot de passe oublié, gestion du compte."""

import pytest
from django.core.cache import cache
from django.utils import timezone

from apps.accounts import signals
from apps.accounts.models import Device, OtpCode, User
from apps.accounts.services import appareils, compte, inscription, jetons, mots_de_passe, otp
from apps.accounts.tests.aides import jeton_otp
from apps.accounts.tests.fabriques import (
    MOT_DE_PASSE,
    ClientFactory,
    GerantFactory,
    PersonnelFactory,
)
from apps.audit.models import AuditLog
from apps.core.errors import ErreurMetier
from apps.core.providers.sms import CLE_BOITE_DEV

pytestmark = [pytest.mark.integration, pytest.mark.pg, pytest.mark.django_db]

TEL = "+2290197121212"
FORT = "un-Mot-de-passe-solide-42"


def refus(fonction, *args, **kwargs) -> ErreurMetier:
    with pytest.raises(ErreurMetier) as e:
        fonction(*args, **kwargs)
    return e.value


def inscrire(**kw):
    base = {
        "jeton_otp": jeton_otp(TEL, "signup"),
        "nom": "Awa Bio",
        "mot_de_passe": FORT,
        "cgu_acceptees": True,
    }
    return inscription.inscrire_client(**{**base, **kw})


class TestInscription:
    def test_cree_le_locataire(self):
        u = inscrire(ip="41.0.0.1")
        assert (u.role, u.phone_e164, u.full_name, u.status) == ("client", TEL, "Awa Bio", "active")
        assert u.phone_verified_at and u.terms_version == "1" and u.terms_accepted_at
        assert u.check_password(FORT) and u.password.startswith(("md5$", "argon2$"))

    def test_trace_l_acceptation_des_cgu(self):
        u = inscrire(ip="41.0.0.1", user_agent="Logeo/1.0")
        ligne = AuditLog.objects.get(action="terms.accepted")
        assert (ligne.actor_id, ligne.metadata, str(ligne.ip)) == (
            u.pk,
            {"version": "1"},
            "41.0.0.1",
        )

    def test_cgu_obligatoires(self):
        assert refus(inscrire, cgu_acceptees=False).code == "terms_not_accepted"
        assert not User.objects.exists()

    @pytest.mark.parametrize("nom", ["", "A", " ", "x" * 121])
    def test_nom_invalide(self, nom):
        assert refus(inscrire, nom=nom).code == "validation_error"

    @pytest.mark.parametrize("mdp", ["court1", "password", "12345678", "azertyuiop"])
    def test_mot_de_passe_faible(self, mdp):
        e = refus(inscrire, mot_de_passe=mdp)
        assert e.code == "validation_error" and "password" in e.champs

    def test_le_jeton_ne_sert_qu_une_fois(self):
        jeton = jeton_otp(TEL, "signup")
        inscrire(jeton_otp=jeton)
        assert refus(inscrire, jeton_otp=jeton).code == "otp_token_invalid"

    def test_jeton_d_un_autre_usage_refuse(self):
        assert (
            refus(inscrire, jeton_otp=jeton_otp(TEL, "reset_password")).code == "otp_token_invalid"
        )

    def test_numero_deja_inscrit_revele_apres_la_preuve(self):
        ClientFactory(phone_e164=TEL)
        e = refus(inscrire)
        assert (e.code, e.statut) == ("phone_already_registered", 409)

    def test_les_espaces_du_nom_sont_normalises(self):
        assert inscrire(nom="  Awa   Bio ").full_name == "Awa Bio"

    def test_parcours_complet_avec_le_vrai_otp(self, settings, django_capture_on_commit_callbacks):
        settings.OTP_DEBUG_CODE = "123456"
        with django_capture_on_commit_callbacks(execute=True):
            otp.demander("97121212", "signup", otp.Contexte())
        jeton = otp.verifier("97121212", "signup", "123456")
        assert inscrire(jeton_otp=jeton).phone_e164 == TEL


class TestActivationGerant:
    def gerant(self):
        g = GerantFactory(phone_e164=TEL)
        g.set_unusable_password()
        g.save()
        return g

    def test_active_le_compte(self):
        self.gerant()
        u = inscription.activer_gerant(jeton_otp(TEL, "gerant_activation"), FORT, True)
        assert u.role == "gerant" and u.has_usable_password() and u.terms_version == "1"
        assert AuditLog.objects.filter(action="auth.gerant_active").exists()

    def test_deja_active(self):
        GerantFactory(phone_e164=TEL)
        e = refus(inscription.activer_gerant, jeton_otp(TEL, "gerant_activation"), FORT, True)
        assert e.code == "already_activated"

    def test_ne_concerne_pas_un_locataire(self):
        ClientFactory(phone_e164=TEL)
        assert (
            refus(
                inscription.activer_gerant, jeton_otp(TEL, "gerant_activation"), FORT, True
            ).statut
            == 404
        )

    def test_cgu_et_mot_de_passe_exiges(self):
        self.gerant()
        assert (
            refus(inscription.activer_gerant, jeton_otp(TEL, "gerant_activation"), FORT, False).code
            == "terms_not_accepted"
        )
        assert (
            refus(
                inscription.activer_gerant, jeton_otp(TEL, "gerant_activation"), "1234", True
            ).code
            == "validation_error"
        )


class TestMotDePasseOublie:
    def test_reinitialisation_revoque_tout(self):
        u = ClientFactory(phone_e164=TEL)
        d1, _ = appareils.ouvrir(u, installation_id="a", platform="android")
        d2, _ = appareils.ouvrir(u, installation_id="b", platform="ios")
        ancien_acces = jetons.emettre_acces(u, d1)
        inscription.reinitialiser_mot_de_passe(jeton_otp(TEL, "reset_password"), FORT)
        u.refresh_from_db()
        assert u.check_password(FORT) and u.token_version == 1
        assert Device.objects.filter(user=u, revoked_at__isnull=True).count() == 0
        assert refus(jetons.verifier_acces, ancien_acces).code == "invalid_token"
        assert d2.pk

    def test_mot_de_passe_faible_refuse(self):
        ClientFactory(phone_e164=TEL)
        assert (
            refus(
                inscription.reinitialiser_mot_de_passe, jeton_otp(TEL, "reset_password"), "123"
            ).code
            == "validation_error"
        )

    def test_numero_sans_compte(self):
        assert (
            refus(
                inscription.reinitialiser_mot_de_passe, jeton_otp(TEL, "reset_password"), FORT
            ).statut
            == 404
        )

    def test_ne_concerne_pas_le_personnel(self):
        PersonnelFactory(phone_e164=TEL)
        assert (
            refus(
                inscription.reinitialiser_mot_de_passe, jeton_otp(TEL, "reset_password"), FORT
            ).statut
            == 404
        )


class TestCompte:
    def test_changer_mot_de_passe_garde_l_appareil_courant(self):
        u = ClientFactory()
        courant, _ = appareils.ouvrir(u, installation_id="a", platform="android")
        autre, _ = appareils.ouvrir(u, installation_id="b", platform="android")
        compte.changer_mot_de_passe(u, MOT_DE_PASSE, FORT, courant.pk)
        assert u.check_password(FORT)
        assert [d.pk for d in appareils.lister(u)] == [courant.pk] and autre.pk

    def test_ancien_mot_de_passe_exige(self):
        assert (
            refus(compte.changer_mot_de_passe, ClientFactory(), "faux", FORT).code
            == "invalid_password"
        )

    def test_nouveau_mot_de_passe_faible(self):
        assert (
            refus(compte.changer_mot_de_passe, ClientFactory(), MOT_DE_PASSE, "123").code
            == "validation_error"
        )

    def test_changer_de_numero(self, django_capture_on_commit_callbacks):
        u = ClientFactory(phone_e164=TEL)
        courant, _ = appareils.ouvrir(u, installation_id="a", platform="android")
        appareils.ouvrir(u, installation_id="b", platform="android")
        with django_capture_on_commit_callbacks(execute=True):
            compte.changer_numero(
                u, MOT_DE_PASSE, jeton_otp("+2290197343434", "change_phone"), courant.pk
            )
        u.refresh_from_db()
        assert u.phone_e164 == "+2290197343434"
        assert [d.pk for d in appareils.lister(u)] == [courant.pk]
        assert any(m["a"] == TEL for m in cache.get(CLE_BOITE_DEV))  # l'ancien numéro est prévenu
        assert "•" in AuditLog.objects.get(action="auth.numero_change").metadata["nouveau"]

    def test_changer_de_numero_exige_le_mot_de_passe(self):
        u = ClientFactory(phone_e164=TEL)
        assert (
            refus(
                compte.changer_numero, u, "faux", jeton_otp("+2290197343434", "change_phone")
            ).code
            == "invalid_password"
        )

    def test_changer_de_numero_deja_pris(self):
        ClientFactory(phone_e164="+2290197343434")
        u = ClientFactory(phone_e164=TEL)
        assert (
            refus(
                compte.changer_numero, u, MOT_DE_PASSE, jeton_otp("+2290197343434", "change_phone")
            ).code
            == "phone_already_registered"
        )
        u.refresh_from_db()
        assert u.phone_e164 == TEL

    def test_profil(self):
        u = ClientFactory()
        assert compte.modifier_profil(u, nom=" Nouveau  Nom ").full_name == "Nouveau Nom"
        assert refus(compte.modifier_profil, u, nom="x").code == "validation_error"

    def test_preferences(self):
        u = ClientFactory()
        compte.definir_preferences(
            u, {"messages": {"push": False, "apercu": True}, "silence": ["conv-1"]}
        )
        u.refresh_from_db()
        assert u.notif_prefs["messages"] == {"push": False, "apercu": True} and u.notif_prefs[
            "silence"
        ] == ["conv-1"]

    @pytest.mark.parametrize(
        "valeurs",
        [{"securite": {"push": False}}, {"sanction": {"push": False}}, {"inconnue": {}}, {"messages": {"push": "non"}},
         {"messages": {"autre": True}}, {"silence": "x"}, "pas un objet"],
    )  # fmt: skip
    def test_preferences_invalides(self, valeurs):
        assert (
            refus(compte.definir_preferences, ClientFactory(), valeurs).code == "validation_error"
        )


class TestSuppression:
    def test_anonymise_et_deconnecte(self):
        u = ClientFactory(phone_e164=TEL)
        appareils.ouvrir(u, installation_id="a", platform="android")
        OtpCode.objects.create(
            phone_e164=TEL, purpose="signup", code_hmac="a" * 64, expires_at=timezone.now()
        )
        recus = []
        signals.compte_supprime.connect(
            lambda sender, **kw: recus.append(kw), weak=False, dispatch_uid="t"
        )
        compte.supprimer(u, MOT_DE_PASSE)
        u.refresh_from_db()
        assert u.status == "deleted" and u.full_name == "Compte supprimé" and u.deleted_at
        assert u.phone_e164.startswith("del:") and len(u.phone_e164) <= 16 and u.email is None
        assert not u.has_usable_password() and u.token_version == 1
        assert not Device.objects.filter(user=u).exists()
        assert (
            not OtpCode.objects.filter(phone_e164=TEL).exists()
            and OtpCode.objects.filter(phone_e164="").exists()
        )
        assert AuditLog.objects.filter(
            action="compte.supprime", actor=u
        ).exists()  # la trace est conservée
        assert recus and recus[0]["utilisateur_id"] == u.pk
        signals.compte_supprime.disconnect(dispatch_uid="t")

    def test_le_numero_est_reutilisable(self):
        u = ClientFactory(phone_e164=TEL)
        compte.supprimer(u, MOT_DE_PASSE)
        assert ClientFactory(phone_e164=TEL).pk != u.pk

    def test_mot_de_passe_exige(self):
        u = ClientFactory()
        assert refus(compte.supprimer, u, "faux").code == "invalid_password"
        u.refresh_from_db()
        assert u.status == "active"

    def test_le_personnel_ne_se_supprime_pas_ici(self):
        assert refus(compte.supprimer, PersonnelFactory(), MOT_DE_PASSE).statut == 403

    def test_jetons_invalides_apres_suppression(self):
        u = ClientFactory()
        d, _ = appareils.ouvrir(u, installation_id="a", platform="android")
        acces = jetons.emettre_acces(u, d)
        compte.supprimer(u, MOT_DE_PASSE)
        assert refus(jetons.verifier_acces, acces).code == "invalid_token"


def test_mot_de_passe_hache_avec_argon2(settings):
    settings.PASSWORD_HASHERS = ["django.contrib.auth.hashers.Argon2PasswordHasher"]
    assert mots_de_passe.hacher(FORT).startswith("argon2$argon2id$")
