"""Textes légaux : même source pour le site (/conditions, /confidentialite) et l'API (/v1/legal/{slug})."""

import pytest
from django.test import Client

from apps.core import parametres

pytestmark = [pytest.mark.integration, pytest.mark.pg, pytest.mark.django_db]


@pytest.mark.parametrize("slug", ["conditions", "confidentialite"])
def test_api_rend_un_document_structure(slug):
    r = Client().get(f"/v1/legal/{slug}")
    assert r.status_code == 200, r.content
    doc = r.json()
    assert doc["slug"] == slug and doc["title"] and doc["summary"]
    assert doc["provisional"] is True  # identité fictive tant que LEGAL_PROVISIONAL est vrai
    assert len(doc["sections"]) >= 8
    for section in doc["sections"]:
        assert section["title"] and section["blocks"] and section["html"]
    assert "[[" not in r.content.decode()  # aucun gabarit laissé non rempli


def test_puces_avec_libelle_en_gras():
    doc = Client().get("/v1/legal/confidentialite").json()
    donnees = next(s for s in doc["sections"] if s["title"].startswith("2."))
    assert donnees["blocks"][0] == {
        "type": "li",
        "label": "Compte",
        "text": donnees["blocks"][0]["text"],
    }


def test_identite_de_l_editeur_vient_des_parametres():
    parametres.definir("LEGAL_COMPANY", "ÉDITEUR TEST SARL")
    parametres.definir("LEGAL_PROVISIONAL", False)
    doc = Client().get("/v1/legal/confidentialite").json()
    assert doc["editor"]["company"] == "ÉDITEUR TEST SARL" and doc["provisional"] is False
    assert "ÉDITEUR TEST SARL" in doc["sections"][0]["blocks"][0]["text"]


def test_document_inconnu_404():
    assert Client().get("/v1/legal/inconnu").status_code == 404


@pytest.mark.parametrize(
    ("url", "titre"),
    [
        ("/conditions", "Conditions d&#x27;utilisation"),
        ("/confidentialite", "Politique de confidentialité"),
    ],
)
def test_pages_web(url, titre):
    r = Client().get(url)
    assert r.status_code == 200
    html = r.content.decode()
    assert titre in html and 'class="legal-hero"' in html and "Version provisoire" in html
    assert "style=" not in html.split('class="legal-hero"')[1]  # CSP : aucun style en ligne


@pytest.mark.parametrize("url", ["/conditions", "/confidentialite"])
def test_le_nom_de_l_editeur_s_affiche_sans_rccm_ni_ifu(url):
    html = Client().get(url).content.decode()
    assert "NEXIX" in html and "RCCM" not in html and "IFU" not in html


def test_rccm_et_ifu_ne_s_affichent_que_s_ils_sont_renseignes():
    parametres.definir("LEGAL_RCCM", "RB/PKO/99 B 00042")
    html = Client().get("/conditions").content.decode()
    assert "RCCM : RB/PKO/99 B 00042" in html and "IFU" not in html


def test_les_textes_disent_la_verite_sur_les_paiements_et_la_lecture_des_conversations():
    conditions = Client().get("/v1/legal/conditions").content.decode()
    assert "entièrement gratuit" not in conditions and "KKiaPay" in conditions
    confidentialite = Client().get("/v1/legal/confidentialite").content.decode()
    assert "KKiaPay" in confidentialite and "pour la modération" in confidentialite


# --------------------------------------------------------------- texte modifiable depuis l'administration
from apps.accounts.tests.fabriques import AdminFactory, PersonnelFactory  # noqa: E402
from apps.audit.models import AuditLog  # noqa: E402
from apps.core import legal  # noqa: E402
from apps.core.errors import ErreurMetier  # noqa: E402

TEXTE = "# Conditions test\n\nRésumé du document.\n\n## 1. Premier point\n\nTexte **en gras**, écrit par [[raison_sociale]].\n"


@pytest.mark.parametrize(
    ("texte", "message"),
    [
        ("", "vide"),
        ("Sans titre\n\n## 1. Section", "titre du document"),
        ("# Titre seul", "au moins une section"),
        ("# T\n\n## 1. S\n\n[[inconnue]]", "Variable inconnue"),
    ],
)
def test_un_texte_invalide_est_refuse_avec_une_explication(texte, message):
    with pytest.raises(ErreurMetier) as e:
        legal.valider(texte)
    assert message in e.value.message


def test_un_texte_enregistre_remplace_celui_d_origine_sur_le_site_et_l_api():
    admin = AdminFactory()
    legal.enregistrer("conditions", TEXTE, acteur=admin)
    page = Client().get("/conditions").content.decode()
    assert "Conditions test" in page and "<strong>en gras</strong>" in page and "NEXIX" in page
    assert Client().get("/v1/legal/conditions").json()["title"] == "Conditions test"
    assert (
        Client().get("/confidentialite").status_code == 200
    )  # l'autre document reste celui d'origine
    assert AuditLog.objects.filter(action="legal.modifie", actor=admin).exists()
    legal.retablir("conditions", acteur=admin)
    assert "Conditions d&#x27;utilisation" in Client().get("/conditions").content.decode()


def test_la_date_et_la_version_suivent_l_enregistrement():
    import datetime

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
