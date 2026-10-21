"""Fournisseurs de stockage des médias : disque local, choix par réglage, squelette S3 explicite."""

import pytest
from django.core.exceptions import ImproperlyConfigured

from apps.core.providers import stockage as fournisseurs
from apps.media import stockage


@pytest.fixture(autouse=True)
def dossiers(settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path / "public"
    settings.MEDIA_TMP_ROOT = tmp_path / "tmp"
    settings.STORAGE_PROVIDER = "local"


def test_disque_local_ecrit_publie_sert_et_supprime(settings):
    dossier = stockage.dossier_public("a1", "m1")
    (dossier / "960.webp").write_bytes(b"image")
    stockage.publier("a1", "m1", dossier)
    cle = stockage.cle("a1", "m1", "960.webp")
    assert cle == "listings/a1/m1/960.webp"
    assert (settings.MEDIA_ROOT / cle).read_bytes() == b"image"
    assert stockage.url_publique(cle) == "/media/listings/a1/m1/960.webp"
    assert stockage.url_publique(None) is None
    stockage.supprimer_derives("a1", "m1")
    assert not (settings.MEDIA_ROOT / "listings/a1/m1").exists()
    stockage.supprimer_derives("a1", "m1")  # sans erreur si déjà absent


def test_une_cle_ne_sort_jamais_de_la_racine():
    with pytest.raises(ValueError):
        fournisseurs.LocalStorageProvider().supprimer("../../etc")


def test_fournisseur_inconnu_refuse(settings):
    settings.STORAGE_PROVIDER = "inconnu"
    with pytest.raises(ImproperlyConfigured):
        fournisseurs.fournisseur()


def test_le_squelette_s3_sert_par_le_cdn_et_refuse_clairement_de_publier(settings):
    settings.STORAGE_PROVIDER = "s3"
    settings.MEDIA_PUBLIC_BASE_URL = "https://medias.exemple.bj/"
    assert (
        stockage.url_publique("listings/a/m/f.webp")
        == "https://medias.exemple.bj/listings/a/m/f.webp"
    )
    dossier = stockage.dossier_public("a", "m")
    assert str(settings.MEDIA_TMP_ROOT) in str(
        dossier
    )  # travail local, jamais dans le dossier public
    with pytest.raises(NotImplementedError, match="ADR"):
        stockage.publier("a", "m", dossier)
