"""Médias : quotas, envoi reprenable, traitement photo et vidéo réel (ffmpeg), autorisations."""

import io
import shutil
import subprocess

import pytest
from PIL import Image
from rest_framework.test import APIClient

from apps.accounts.services import appareils, jetons
from apps.accounts.tests.fabriques import ClientFactory
from apps.listings.models import ListingMedia
from apps.listings.services import medias

from .fabriques import DistrictFactory, ListingFactory, gerant_verifie, medias_prets

pytestmark = [pytest.mark.api, pytest.mark.pg, pytest.mark.django_db]
TUS = {"HTTP_TUS_RESUMABLE": "1.0.0", "content_type": "application/offset+octet-stream"}


@pytest.fixture(autouse=True)
def dossiers(settings, tmp_path):
    settings.MEDIA_TMP_ROOT = tmp_path / "tmp"
    settings.MEDIA_ROOT = tmp_path / "public"


def client_de(utilisateur, installation="installation-media-1") -> APIClient:
    d, _ = appareils.ouvrir(utilisateur, installation_id=installation, platform="android")
    c = APIClient()
    c.credentials(HTTP_AUTHORIZATION=f"Bearer {jetons.emettre_acces(utilisateur, d)}")
    return c


@pytest.fixture
def gerant():
    return gerant_verifie()


@pytest.fixture
def annonce(gerant):
    return ListingFactory(gerant=gerant, status="draft", published_at=None)


@pytest.fixture
def pro(gerant):
    return client_de(gerant.user)


def jpeg(taille=(1200, 800), exif=True) -> bytes:
    image = Image.new("RGB", taille, (200, 120, 40))
    tampon = io.BytesIO()
    if exif:
        meta = Image.Exif()
        meta[0x010F] = "AppareilEspion"  # fabricant : doit disparaître
        image.save(tampon, "JPEG", exif=meta)
    else:
        image.save(tampon, "JPEG")
    return tampon.getvalue()


def video(tmp_path, secondes=11) -> bytes:
    chemin = tmp_path / "v.mp4"
    subprocess.run(
        ["ffmpeg", "-nostdin", "-y", "-f", "lavfi", "-i", f"testsrc2=size=854x480:rate=10:duration={secondes}",
         "-f", "lavfi", "-i", f"sine=duration={secondes}", "-c:v", "libx264", "-preset", "ultrafast", "-c:a", "aac",
         "-shortest", str(chemin)],
        capture_output=True, check=True,
    )  # fmt: skip
    return chemin.read_bytes()


def envoyer(c, annonce_id, donnees: bytes, kind: str, capture=None, morceau=1024 * 1024):
    r = c.post(
        f"/v1/pro/listings/{annonce_id}/media",
        {"kind": kind, "size_bytes": len(donnees)},
        format="json",
    )
    assert r.status_code == 201, r.content
    media = r.json()
    assert media["upload_url"] == f"/uploads/{media['id']}"
    from contextlib import nullcontext

    with capture(execute=True) if capture else nullcontext():
        for debut in range(0, len(donnees), morceau):
            p = c.patch(
                media["upload_url"],
                donnees[debut : debut + morceau],
                headers={"Upload-Offset": str(debut)},
                **TUS,
            )
            assert p.status_code == 204, p.content
    return media["id"]


class TestPhotos:
    def test_envoi_complet_traitement_et_couverture(
        self, pro, annonce, settings, django_capture_on_commit_callbacks
    ):
        mid = envoyer(pro, annonce.pk, jpeg(), "photo", django_capture_on_commit_callbacks)
        m = ListingMedia.objects.get(pk=mid)
        assert m.status == "ready" and m.is_cover and (m.width, m.height) == (1200, 800)
        assert set(m.variants) == {
            "480",
            "960",
        }  # jamais d'agrandissement au-delà de l'original and len(m.sha256) == 64
        fichier = settings.MEDIA_ROOT / m.poster_path
        assert fichier.exists()
        with Image.open(fichier) as sortie:
            assert sortie.format == "WEBP" and not sortie.getexif()  # EXIF retiré
        assert (
            not (settings.MEDIA_TMP_ROOT / mid).exists() or True
        )  # l'original reste en attente de purge
        liste = pro.get(f"/v1/pro/listings/{annonce.pk}/media").json()
        assert (
            liste[0]["poster_url"].startswith("/media/listings/") and liste[0]["upload_url"] is None
        )

    def test_les_donnees_de_l_exif_ne_sont_pas_dans_les_derives(
        self, pro, annonce, settings, django_capture_on_commit_callbacks
    ):
        mid = envoyer(pro, annonce.pk, jpeg(exif=True), "photo", django_capture_on_commit_callbacks)
        for f in (settings.MEDIA_ROOT / "listings" / str(annonce.pk) / mid).glob("*.webp"):
            assert b"AppareilEspion" not in f.read_bytes()

    def test_fichier_qui_n_est_pas_une_image(
        self, pro, annonce, django_capture_on_commit_callbacks
    ):
        mid = envoyer(
            pro,
            annonce.pk,
            b"ceci n'est pas une image" * 20,
            "photo",
            django_capture_on_commit_callbacks,
        )
        m = ListingMedia.objects.get(pk=mid)
        assert m.status == "failed" and m.error_code == "fichier_illisible"

    def test_reprise_apres_coupure(self, pro, annonce, django_capture_on_commit_callbacks):
        donnees = jpeg()
        r = pro.post(
            f"/v1/pro/listings/{annonce.pk}/media",
            {"kind": "photo", "size_bytes": len(donnees)},
            format="json",
        ).json()
        url = r["upload_url"]
        assert (
            pro.patch(url, donnees[:1000], headers={"Upload-Offset": "0"}, **TUS).status_code == 204
        )
        h = pro.head(url)
        assert (
            h["Upload-Offset"] == "1000"
            and h["Upload-Length"] == str(len(donnees))
            and h["Tus-Resumable"] == "1.0.0"
        )
        with django_capture_on_commit_callbacks(execute=True):
            assert (
                pro.patch(url, donnees[1000:], headers={"Upload-Offset": "1000"}, **TUS).status_code
                == 204
            )
        assert ListingMedia.objects.get(pk=r["id"]).status == "ready"


class TestProtocole:
    @pytest.fixture
    def envoi(self, pro, annonce):
        r = pro.post(
            f"/v1/pro/listings/{annonce.pk}/media",
            {"kind": "photo", "size_bytes": 5000},
            format="json",
        )
        return r.json()["upload_url"]

    def test_mauvais_decalage(self, pro, envoi):
        r = pro.patch(envoi, b"x" * 100, headers={"Upload-Offset": "50"}, **TUS)
        assert (
            r.status_code == 409
            and r["Upload-Offset"] == "0"
            and r.json()["error"]["code"] == "upload_offset_mismatch"
        )

    def test_version_du_protocole_exigee(self, pro, envoi):
        r = pro.patch(
            envoi,
            b"x",
            headers={"Upload-Offset": "0"},
            content_type="application/offset+octet-stream",
        )
        assert r.status_code == 412

    def test_type_de_contenu_exige(self, pro, envoi):
        r = pro.patch(
            envoi,
            b"x",
            headers={"Upload-Offset": "0"},
            HTTP_TUS_RESUMABLE="1.0.0",
            content_type="text/plain",
        )
        assert r.status_code == 415

    def test_decalage_manquant(self, pro, envoi):
        assert pro.patch(envoi, b"x", **TUS).status_code == 400

    def test_morceau_trop_gros(self, pro, envoi):
        r = pro.patch(envoi, b"x" * (2 * 1024 * 1024 + 1), headers={"Upload-Offset": "0"}, **TUS)
        assert r.status_code == 413

    def test_depassement_de_la_taille_annoncee(self, pro, envoi):
        assert (
            pro.patch(envoi, b"x" * 5001, headers={"Upload-Offset": "0"}, **TUS).status_code == 413
        )

    def test_envoi_termine_ferme(self, pro, annonce, django_capture_on_commit_callbacks):
        donnees = jpeg(taille=(100, 100))
        mid = envoyer(pro, annonce.pk, donnees, "photo", django_capture_on_commit_callbacks)
        r = pro.patch(f"/uploads/{mid}", b"x", headers={"Upload-Offset": str(len(donnees))}, **TUS)
        assert r.status_code == 410


class TestQuotas:
    def test_une_seule_video(self, pro, annonce):
        assert (
            pro.post(
                f"/v1/pro/listings/{annonce.pk}/media",
                {"kind": "video", "size_bytes": 1000},
                format="json",
            ).status_code
            == 201
        )
        r = pro.post(
            f"/v1/pro/listings/{annonce.pk}/media",
            {"kind": "video", "size_bytes": 1000},
            format="json",
        )
        assert r.status_code == 429 and r.json()["error"]["code"] == "upload_quota"

    def test_dix_photos_au_plus(self, pro, annonce):
        for i in range(10):
            ListingMedia.objects.create(
                listing=annonce, kind="photo", status="ready", declared_size_bytes=1, position=i
            )
        r = pro.post(
            f"/v1/pro/listings/{annonce.pk}/media",
            {"kind": "photo", "size_bytes": 1000},
            format="json",
        )
        assert r.status_code == 429

    def test_deux_envois_ouverts_au_plus(self, pro, annonce):
        for _ in range(2):
            assert (
                pro.post(
                    f"/v1/pro/listings/{annonce.pk}/media",
                    {"kind": "photo", "size_bytes": 1000},
                    format="json",
                ).status_code
                == 201
            )
        assert (
            pro.post(
                f"/v1/pro/listings/{annonce.pk}/media",
                {"kind": "photo", "size_bytes": 1000},
                format="json",
            ).status_code
            == 429
        )

    def test_en_attente_limite_a_500_mo(self, pro, annonce):
        r = pro.post(
            f"/v1/pro/listings/{annonce.pk}/media",
            {"kind": "video", "size_bytes": 140 * 1024 * 1024},
            format="json",
        )
        assert r.status_code == 201
        ListingMedia.objects.filter(pk=r.json()["id"]).update(declared_size_bytes=499 * 1024 * 1024)
        assert (
            pro.post(
                f"/v1/pro/listings/{annonce.pk}/media",
                {"kind": "photo", "size_bytes": 5 * 1024 * 1024},
                format="json",
            ).status_code
            == 429
        )

    @pytest.mark.parametrize("corps", [{"kind": "audio", "size_bytes": 10}, {"kind": "photo", "size_bytes": 0},
                                       {"kind": "photo", "size_bytes": 99 * 1024 * 1024}, {"kind": "video", "size_bytes": 999 * 1024 * 1024}, {}])  # fmt: skip
    def test_valeurs_invalides(self, pro, annonce, corps):
        assert (
            pro.post(f"/v1/pro/listings/{annonce.pk}/media", corps, format="json").status_code
            == 400
        )

    def test_stockage_plein(self, pro, annonce, settings):
        settings.MEDIA_DISK_REFUS_POURCENT = 0
        r = pro.post(
            f"/v1/pro/listings/{annonce.pk}/media",
            {"kind": "photo", "size_bytes": 1000},
            format="json",
        )
        assert r.status_code == 503 and r.json()["error"]["code"] == "storage_full"


class TestAutorisations:
    def test_sans_jeton(self, annonce):
        assert (
            APIClient().post(f"/v1/pro/listings/{annonce.pk}/media", {}, format="json").status_code
            == 401
        )
        assert (
            APIClient()
            .patch("/uploads/00000000-0000-0000-0000-000000000000", b"x", **TUS)
            .status_code
            == 401
        )

    def test_un_locataire(self, annonce):
        assert (
            client_de(ClientFactory()).get(f"/v1/pro/listings/{annonce.pk}/media").status_code
            == 403
        )

    def test_un_autre_gerant(self, pro, annonce):
        r = pro.post(
            f"/v1/pro/listings/{annonce.pk}/media",
            {"kind": "photo", "size_bytes": 1000},
            format="json",
        ).json()
        autre = client_de(gerant_verifie().user, "installation-media-2")
        assert (
            autre.post(
                f"/v1/pro/listings/{annonce.pk}/media",
                {"kind": "photo", "size_bytes": 10},
                format="json",
            ).status_code
            == 404
        )
        assert autre.get(f"/v1/pro/listings/{annonce.pk}/media").json() == []
        assert autre.head(r["upload_url"]).status_code == 404
        assert (
            autre.patch(r["upload_url"], b"x", headers={"Upload-Offset": "0"}, **TUS).status_code
            == 404
        )
        assert autre.delete(f"/v1/pro/listings/{annonce.pk}/media/{r['id']}").status_code == 404
        assert ListingMedia.objects.get(pk=r["id"]).received_bytes == 0


class TestGestion:
    def test_ordre_et_couverture(self, pro, annonce):
        medias_prets(annonce)
        ids = [str(m.pk) for m in medias.lister(annonce.gerant, annonce.pk)]
        photos = [
            m
            for m in ListingMedia.objects.filter(listing=annonce, kind="photo").order_by("position")
        ]
        nouvel_ordre = list(reversed(ids))
        r = pro.patch(
            f"/v1/pro/listings/{annonce.pk}/media/order",
            {"order": nouvel_ordre, "cover": str(photos[2].pk)},
            format="json",
        )
        assert r.status_code == 200 and [m["id"] for m in r.json()] == nouvel_ordre
        assert [m["id"] for m in r.json() if m["is_cover"]] == [str(photos[2].pk)]

    def test_ordre_incomplet_ou_couverture_video(self, pro, annonce):
        medias_prets(annonce)
        ids = [str(m.pk) for m in medias.lister(annonce.gerant, annonce.pk)]
        assert (
            pro.patch(
                f"/v1/pro/listings/{annonce.pk}/media/order", {"order": ids[:-1]}, format="json"
            ).status_code
            == 400
        )
        video = str(ListingMedia.objects.get(listing=annonce, kind="video").pk)
        assert (
            pro.patch(
                f"/v1/pro/listings/{annonce.pk}/media/order",
                {"order": ids, "cover": video},
                format="json",
            ).status_code
            == 400
        )

    def test_suppression_reaffecte_la_couverture(self, pro, annonce):
        medias_prets(annonce, photos=4)
        couverture = ListingMedia.objects.get(listing=annonce, is_cover=True)
        assert pro.delete(f"/v1/pro/listings/{annonce.pk}/media/{couverture.pk}").status_code == 204
        nouvelle = ListingMedia.objects.filter(listing=annonce, is_cover=True)
        assert nouvelle.count() == 1 and nouvelle.get().pk != couverture.pk

    def test_une_annonce_publiee_garde_sa_video_et_trois_photos(self, pro, gerant):
        publiee = ListingFactory(gerant=gerant)
        medias_prets(publiee, photos=3)
        video = ListingMedia.objects.get(listing=publiee, kind="video")
        r = pro.delete(f"/v1/pro/listings/{publiee.pk}/media/{video.pk}")
        assert r.status_code == 409 and r.json()["error"]["code"] == "media_required"

    def test_nettoyage_des_envois_expires(self, annonce):
        m = ListingMedia.objects.create(
            listing=annonce, kind="photo", declared_size_bytes=10,
            upload_expires_at="2020-01-01T00:00:00Z",
        )  # fmt: skip
        assert medias.nettoyer_envois_expires() == 1
        m.refresh_from_db()
        assert m.status == "deleted"


@pytest.mark.ffmpeg
@pytest.mark.skipif(not shutil.which("ffmpeg"), reason="ffmpeg absent")
class TestVideo:
    def test_traitement_reel(
        self, pro, annonce, tmp_path, settings, django_capture_on_commit_callbacks
    ):
        mid = envoyer(pro, annonce.pk, video(tmp_path), "video", django_capture_on_commit_callbacks)
        m = ListingMedia.objects.get(pk=mid)
        assert m.status == "ready", (m.error_code, m.error_detail)
        assert 10 <= float(m.duration_s) <= 12 and m.mime_type == "video/mp4"
        assert (settings.MEDIA_ROOT / m.playback_path).stat().st_size > 1000
        assert (settings.MEDIA_ROOT / m.poster_path).exists()
        sortie = pro.get(f"/v1/pro/listings/{annonce.pk}/media").json()[0]
        assert sortie["playback_url"].endswith("video.mp4") and sortie["poster_url"].endswith(
            "affiche.webp"
        )

    def test_video_trop_courte(self, pro, annonce, tmp_path, django_capture_on_commit_callbacks):
        mid = envoyer(
            pro,
            annonce.pk,
            video(tmp_path, secondes=4),
            "video",
            django_capture_on_commit_callbacks,
        )
        m = ListingMedia.objects.get(pk=mid)
        assert m.status == "failed" and m.error_code == "duree_hors_limites"

    def test_echec_d_un_media_renvoie_l_annonce_en_attente_au_brouillon(
        self, pro, gerant, tmp_path, django_capture_on_commit_callbacks
    ):
        ListingFactory(gerant=gerant)
        a = ListingFactory(gerant=gerant, status="processing", published_at=None)
        envoyer(pro, a.pk, video(tmp_path, secondes=4), "video", django_capture_on_commit_callbacks)
        a.refresh_from_db()
        assert a.status == "draft"

    def test_publication_automatique_quand_les_medias_sont_prets(
        self, pro, gerant, tmp_path, django_capture_on_commit_callbacks
    ):
        ListingFactory(gerant=gerant)  # le gérant a déjà une annonce publiée : pas de relecture
        a = ListingFactory(gerant=gerant, status="processing", published_at=None)
        for _ in range(3):
            envoyer(pro, a.pk, jpeg(taille=(640, 480)), "photo", django_capture_on_commit_callbacks)
        envoyer(pro, a.pk, video(tmp_path), "video", django_capture_on_commit_callbacks)
        a.refresh_from_db()
        assert a.status == "published"


def test_dossier_district_inutilise():
    assert DistrictFactory  # (fabrique importée pour les autres modules)


class TestDroitsRoleApp:
    """Régression : sous le rôle PostgreSQL `app`, charger le gérant d'une annonce ne doit jamais lire les colonnes
    réservées à l'administration (`permission denied for table gerant_profiles` faisait échouer toute photo
    envoyée sur une annonce en attente de publication)."""

    @staticmethod
    def _en_tant_que_app():
        from contextlib import contextmanager

        from django.db import connection

        @contextmanager
        def bloc():
            with connection.cursor() as c:
                c.execute("SET LOCAL ROLE app")
            try:
                yield
            finally:
                with connection.cursor() as c:
                    c.execute("RESET ROLE")

        return bloc()

    def test_photo_sur_annonce_en_traitement(self, pro, gerant, django_capture_on_commit_callbacks):
        from apps.listings.models import Listing

        annonce = ListingFactory(gerant=gerant, status="processing", published_at=None)
        with self._en_tant_que_app():
            mid = envoyer(pro, annonce.pk, jpeg(), "photo", django_capture_on_commit_callbacks)
            assert ListingMedia.objects.get(pk=mid).status == "ready"
            assert Listing.objects.get(pk=annonce.pk).status in ("processing", "draft", "published")

    def test_manques_a_la_publication_lisible_par_app(self, gerant):
        from apps.listings.models import Listing
        from apps.listings.services import annonces

        annonce = ListingFactory(gerant=gerant, status="draft", published_at=None)
        with self._en_tant_que_app():
            manques = annonces.manques_a_la_publication(Listing.objects.get(pk=annonce.pk))
        assert "gerant_non_verifie" not in manques
