"""Création d'un gérant par l'administration, sans mot de passe ni SMS : lien d'activation (ADR 0009, EF-ADM-01)."""

import pytest

from apps.accounts.models import GerantProfile, User
from apps.accounts.services import administration
from apps.accounts.tests.fabriques import AdminFactory, ClientFactory
from apps.audit.models import AuditLog
from apps.core.errors import ErreurMetier

pytestmark = [pytest.mark.integration, pytest.mark.pg, pytest.mark.django_db]

TEL = "+2290197121212"
TEL_LOCAL = "97121212"


def creer(**kw):
    base = {"telephone": TEL, "prenom": "Idris", "nom": "Adam", "zone": "Banikanni"}
    return administration.creer_gerant(acteur=AdminFactory(), **{**base, **kw})


class TestCreationGerant:
    def test_sans_mot_de_passe_ni_nom_d_utilisateur(self):
        gerant = creer()
        assert (
            gerant.role == "gerant" and gerant.username is None and not gerant.has_usable_password()
        )
        assert (gerant.first_name, gerant.last_name, gerant.full_name) == (
            "Idris",
            "Adam",
            "Idris Adam",
        )
        assert GerantProfile.complets.get(user=gerant).zone == "Banikanni"
        assert AuditLog.objects.filter(action="gerant.cree", target_id=gerant.pk).exists()

    def test_numero_normalise_en_e164(self):
        assert creer(telephone=TEL_LOCAL).phone_e164 == TEL

    def test_numero_deja_utilise_par_un_locataire_accepte(self):
        ClientFactory(phone_e164=TEL)  # le numéro n'est plus unique (ADR 0009)
        assert creer().pk

    def test_numero_invalide(self):
        with pytest.raises(ErreurMetier) as e:
            creer(telephone="12")
        assert e.value.code == "validation_error"


class TestLiens:
    def test_lien_d_activation_sur_le_site_et_journalise(self, settings):
        settings.SITE_URL = "https://www.immoplus.bj"
        gerant = creer()
        url = administration.lien_activation(acteur=AdminFactory(), gerant=gerant)
        assert url.startswith("https://www.immoplus.bj/activer/")
        assert AuditLog.objects.filter(
            action="gerant.lien_activation", target_id=gerant.pk
        ).exists()

    def test_pas_de_lien_d_activation_pour_un_compte_deja_actif(self):
        gerant = creer()
        url = administration.lien_activation(acteur=AdminFactory(), gerant=gerant)
        administration.activer_gerant(
            url.rsplit("/", 1)[1], nom_utilisateur="idris.adam", mot_de_passe="Un-Mot-De-Passe-42"
        )
        with pytest.raises(ErreurMetier) as e:
            administration.lien_activation(
                acteur=AdminFactory(), gerant=User.objects.get(pk=gerant.pk)
            )
        assert e.value.code == "already_active"
