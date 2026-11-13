"""Textes légaux modifiés depuis l'administration : enregistrement, version, journal, droits."""

import datetime

import pytest
from django.test import Client

from apps.accounts.tests.fabriques import AdminFactory, PersonnelFactory
from apps.audit.models import AuditLog
from apps.core import legal, parametres
from apps.core.errors import ErreurMetier

pytestmark = [pytest.mark.integration, pytest.mark.pg, pytest.mark.django_db]

TEXTE = (
    "# Conditions test\n\nRésumé du document.\n\n## 1. Premier point\n\n"
    "Texte **en gras**, écrit par [[raison_sociale]].\n"
)


def test_un_texte_enregistre_remplace_celui_d_origine_sur_le_site_et_l_api():
    admin = AdminFactory()
    legal.enregistrer("conditions", TEXTE, acteur=admin)
    page = Client().get("/conditions").content.decode()
    assert "Conditions test" in page and "<strong>en gras</strong>" in page and "NEXIX" in page
    assert Client().get("/v1/legal/conditions").json()["title"] == "Conditions test"
    assert (
        Client().get("/confidentialite").status_code == 200
    )  # l'autre document reste celui d'origine
    legal.retablir("conditions", acteur=admin)
    assert "Conditions d&#x27;utilisation" in Client().get("/conditions").content.decode()


def test_la_date_et_la_version_suivent_l_enregistrement():
    legal.enregistrer("conditions", TEXTE, acteur=AdminFactory())
    assert parametres.lire("LEGAL_UPDATED_AT") == datetime.date.today().isoformat()
    avant = int(parametres.lire("TERMS_VERSION"))
    legal.enregistrer("conditions", TEXTE, acteur=AdminFactory(), nouvelle_acceptation=True)
    assert int(parametres.lire("TERMS_VERSION")) == avant + 1


def test_seul_un_administrateur_modifie_un_texte():
    with pytest.raises(ErreurMetier) as e:
        legal.enregistrer("conditions", TEXTE, acteur=PersonnelFactory())
    assert e.value.statut == 403


def test_le_html_brut_du_texte_est_neutralise():
    legal.enregistrer("conditions", TEXTE + "\n<script>alert(1)</script>\n", acteur=AdminFactory())
    page = Client().get("/conditions").content.decode()
    assert "<script>alert(1)</script>" not in page


def test_la_modification_est_inscrite_au_journal():
    from django.test import override_settings
    from django.urls import reverse

    from adminsite.tests.test_administration import REGLAGES, se_connecter

    admin = AdminFactory()
    with override_settings(**REGLAGES):
        c, _ = se_connecter(admin)
        c.post(reverse("admin:core_legaldocument_modifier", args=["conditions"]), {"texte": TEXTE})
        c.post(reverse("admin:core_legaldocument_modifier", args=["conditions"]), {"retablir": "1"})
    assert AuditLog.objects.filter(action="legal.modifie", actor=admin).count() == 1
    assert AuditLog.objects.filter(action="legal.retabli", actor=admin).count() == 1
