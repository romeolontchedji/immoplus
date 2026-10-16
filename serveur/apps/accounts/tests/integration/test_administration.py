"""Création d'un gérant par l'administration et SMS informatif (EF-ADM-01)."""

import pytest
from django.core.cache import cache

from apps.accounts.models import GerantProfile, User
from apps.accounts.services import administration
from apps.accounts.tests.fabriques import AdminFactory, ClientFactory
from apps.audit.models import AuditLog
from apps.core.errors import ErreurMetier
from apps.core.providers import sms
from apps.core.providers.sms import CLE_BOITE_DEV

pytestmark = [pytest.mark.integration, pytest.mark.pg, pytest.mark.django_db]

TEL = "+2290197121212"
TEL_LOCAL = "97121212"
MOT_DE_PASSE = "Un-Mot-De-Passe-42"


class FournisseurEnPanne:
    """Fournisseur factice qui échoue à tous les coups."""

    def envoyer(self, numero_e164: str, message: str) -> None:
        raise sms.ErreurFournisseurSms("panne simulée")


def creer(**kw):
    base = {
        "telephone": TEL,
        "nom": "Idris Adam",
        "zone": "Banikanni",
        "mot_de_passe": MOT_DE_PASSE,
    }
    return administration.creer_gerant(acteur=AdminFactory(), **{**base, **kw})


def boite():
    return cache.get(CLE_BOITE_DEV) or []


class TestCreationGerant:
    def test_envoie_le_sms_apres_commit(self, django_capture_on_commit_callbacks):
        with django_capture_on_commit_callbacks(execute=True):
            creer()
        assert [m["a"] for m in boite()] == [TEL]
        assert boite()[0]["message"] == administration.MESSAGE_COMPTE_PRET

    def test_aucun_sms_si_la_creation_est_refusee(self, django_capture_on_commit_callbacks):
        ClientFactory(phone_e164=TEL)
        with django_capture_on_commit_callbacks(execute=True), pytest.raises(ErreurMetier) as e:
            creer()
        assert e.value.code == "phone_already_registered"
        assert not boite()

    def test_le_compte_est_cree_meme_si_le_fournisseur_echoue(
        self, django_capture_on_commit_callbacks, monkeypatch
    ):
        monkeypatch.setattr(sms, "fournisseur", lambda: FournisseurEnPanne())
        with django_capture_on_commit_callbacks(execute=True):
            gerant = creer()
        assert User.objects.filter(pk=gerant.pk).exists()
        assert AuditLog.objects.get(action="gerant.notification_echec").target_id == gerant.pk

    def test_numero_normalise_en_e164(self):
        gerant = creer(telephone=TEL_LOCAL)
        assert gerant.phone_e164 == TEL

    def test_aucun_renvoi_lors_d_une_modification(self, django_capture_on_commit_callbacks):
        with django_capture_on_commit_callbacks(execute=True):
            gerant = creer()
        assert boite()
        cache.delete(CLE_BOITE_DEV)
        profil = GerantProfile.complets.get(user=gerant)
        administration.definir_verification(acteur=AdminFactory(), profil=profil, statut="verified")
        gerant.full_name = "Idris A."
        gerant.save()
        assert not boite()
