"""Cloudinary (ADR 0010) : signature, URL, envoi, suppression, cohabitation avec le disque. Aucun appel réseau."""

import pytest

from apps.core.providers import stockage as fournisseurs
from apps.media import stockage


@pytest.fixture(autouse=True)
def compte(settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path / "public"
    settings.MEDIA_TMP_ROOT = tmp_path / "tmp"
    settings.STORAGE_PROVIDER = "local"
    settings.CLOUDINARY_CLOUD_NAME = "immoplus-test"
    settings.CLOUDINARY_API_KEY = "123456"
    settings.CLOUDINARY_API_SECRET = (
        "secret-jamais-envoye"  # hors alphabet hexadécimal des séparateurs
    )
    settings.CLOUDINARY_FOLDER = "immoplus"


@pytest.fixture
def appels(monkeypatch):
    """Remplace l'appel HTTP : chaque requête est notée, la réponse est vide."""
    notes = []

    def faux(self, methode, url, corps=None, entetes=None):
        notes.append(
            {"methode": methode, "url": url, "corps": corps or b"", "entetes": entetes or {}}
        )
        return {}

    monkeypatch.setattr(fournisseurs.CloudinaryStorageProvider, "_requete", faux)
    return notes


def test_signature_de_la_documentation_cloudinary(settings):
    settings.CLOUDINARY_API_SECRET = "abcd"  # exemple officiel
    parametres = {
        "eager": "w_400,h_300,c_pad|w_260,h_200,c_crop",
        "public_id": "sample_image",
        "timestamp": "1315060510",
    }
    assert (
        fournisseurs.CloudinaryStorageProvider().signature(parametres)
        == "bfd09f95f331f558cbd1320e67aa8d488770583e"
    )


def test_cle_prefixee_et_url_du_cdn():
    cle = stockage.cle("a1", "m1", "960.webp", distant=True)
    assert cle == "cloudinary:listings/a1/m1/960.webp"
    assert stockage.url_publique(cle) == (
        "https://res.cloudinary.com/immoplus-test/image/upload/immoplus/listings/a1/m1/960.webp"
    )
    assert stockage.url_publique("cloudinary:listings/a1/m1/lecture.mp4") == (
        "https://res.cloudinary.com/immoplus-test/video/upload/immoplus/listings/a1/m1/lecture.mp4"
    )


def test_les_cles_du_disque_restent_servies_par_le_disque():
    assert stockage.url_publique("listings/a1/m1/960.webp") == "/media/listings/a1/m1/960.webp"


def test_publier_envoie_chaque_fichier_signe(appels):
    dossier = stockage.dossier_public("a1", "m1")
    (dossier / "480.webp").write_bytes(b"petite")
    (dossier / "960.webp").write_bytes(b"grande")
    stockage.publier_distant("a1", "m1", dossier)
    assert [a["url"] for a in appels] == [
        "https://api.cloudinary.com/v1_1/immoplus-test/image/upload"
    ] * 2
    corps = appels[1]["corps"]
    assert b'name="public_id"\r\n\r\nimmoplus/listings/a1/m1/960\r\n' in corps
    assert b'name="api_key"\r\n\r\n123456\r\n' in corps and b"grande" in corps
    assert (
        b'name="signature"' in corps and b"secret-jamais-envoye" not in corps
    )  # le secret ne part jamais


def test_envoi_refuse_sans_cle_ni_secret(settings, appels):
    settings.CLOUDINARY_API_SECRET = ""
    dossier = stockage.dossier_public("a1", "m1")
    (dossier / "960.webp").write_bytes(b"x")
    with pytest.raises(fournisseurs.ErreurStockageDistant, match="SECRET"):
        stockage.publier_distant("a1", "m1", dossier)
    assert appels == []


def test_supprimer_efface_les_trois_types_sous_le_prefixe(appels):
    fournisseurs.CloudinaryStorageProvider().supprimer("listings/a1/m1")
    assert [(a["methode"], a["url"]) for a in appels] == [
        ("DELETE", f"https://api.cloudinary.com/v1_1/immoplus-test/resources/{t}/upload"
         "?prefix=immoplus/listings/a1/m1/")
        for t in ("image", "video", "raw")
    ]  # fmt: skip
    assert appels[0]["entetes"]["Authorization"].startswith("Basic ")


def test_supprimer_derives_ne_contacte_cloudinary_que_pour_un_media_distant(appels):
    stockage.supprimer_derives("a1", "m1")
    assert appels == []
    stockage.supprimer_derives("a1", "m1", distant=True)  # tâche exécutée sur place en test
    assert len(appels) == 3


@pytest.mark.pg
@pytest.mark.django_db
def test_les_envois_vont_chez_cloudinary_seulement_si_active_et_configure(settings):
    from apps.core import parametres

    assert not stockage.envois_distants()  # disque par défaut
    parametres.definir("MEDIA_STORAGE", "cloudinary")
    assert stockage.envois_distants()
    settings.CLOUDINARY_CLOUD_NAME = ""
    assert not stockage.envois_distants()  # compte retiré : retour au disque, sans panne


def test_la_csp_autorise_le_cdn_seulement_quand_le_compte_est_renseigne(settings):
    from apps.core.middleware import construire_csp

    assert "img-src 'self' https://res.cloudinary.com data:" in construire_csp()
    settings.CLOUDINARY_CLOUD_NAME = ""
    assert "res.cloudinary.com" not in construire_csp()
