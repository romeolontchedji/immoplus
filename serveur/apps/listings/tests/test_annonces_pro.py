"""Annonces côté gérant : création, contenu assaini, publication, cycle de vie, autorisations."""

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.services import appareils, jetons
from apps.accounts.tests.fabriques import ClientFactory
from apps.audit.models import AuditLog
from apps.listings.models import Listing, ListingMedia
from apps.listings.services import contenu, geo

from .fabriques import (
    DistrictFactory,
    ListingFactory,
    donnees_annonce,
    gerant_verifie,
    medias_prets,
)

pytestmark = [pytest.mark.api, pytest.mark.pg, pytest.mark.django_db]


def client_de(utilisateur) -> APIClient:
    d, _ = appareils.ouvrir(utilisateur, installation_id="installation-pro-1", platform="android")
    c = APIClient()
    c.credentials(HTTP_AUTHORIZATION=f"Bearer {jetons.emettre_acces(utilisateur, d)}")
    return c


@pytest.fixture
def quartier():
    return DistrictFactory()


@pytest.fixture
def gerant():
    return gerant_verifie()


@pytest.fixture
def pro(gerant):
    return client_de(gerant.user)


def creer(pro, quartier, **extra):
    r = pro.post("/v1/pro/listings", donnees_annonce(quartier, **extra), format="json")
    assert r.status_code == 201, r.content
    return r.json()


class TestCreation:
    def test_brouillon_complet(self, pro, quartier):
        a = creer(pro, quartier)
        assert a["status"] == "draft" and a["slug"].startswith("chambre-propre-pres-du-campus-")
        assert 0 < a["distance_to_campus_m"] < 2000 and a["district_name"] == quartier.name
        assert a["address_private"] == "Rue 12, maison bleue"
        annonce = Listing.objects.get(pk=a["id"])
        assert (
            "<strong>calme</strong>" in annonce.description_html
            and "<li>Douche interne</li>" in annonce.description_html
        )
        assert Listing.objects.filter(pk=a["id"], search_vector__isnull=False).exists()
        assert AuditLog.objects.filter(action="listing.cree").exists()

    def test_les_champs_obligatoires(self, pro, quartier):
        r = pro.post("/v1/pro/listings", {"title": "Chambre propre"}, format="json")
        assert r.status_code == 400 and "rent_amount" in r.json()["error"]["fields"]

    @pytest.mark.parametrize(
        "extra",
        [{"rent_amount": 0}, {"title": "abc"}, {"deposit_months": 13}, {"agent_fee_amount": -5},
         {"latitude": "48.85", "longitude": "2.35"}, {"room_type": "chateau"}],
    )  # fmt: skip
    def test_valeurs_invalides(self, pro, quartier, extra):
        r = pro.post("/v1/pro/listings", donnees_annonce(quartier, **extra), format="json")
        assert r.status_code == 400

    def test_quartier_inconnu(self, pro, quartier):
        r = pro.post(
            "/v1/pro/listings",
            donnees_annonce(quartier, district="00000000-0000-0000-0000-000000000000"),
            format="json",
        )
        assert r.status_code == 400 and "district" in r.json()["error"]["fields"]

    @pytest.mark.parametrize(
        ("champ", "texte"),
        [("description_md", "Appelle-moi au 97 12 34 56"), ("title", "Chambre écris au +229 97123456"),
         ("address_private", "joe@exemple.com"), ("landmark_text", "voir www.exemple.bj"),
         ("description_md", "zéro un neuf sept un deux trois quatre cinq six")],
    )  # fmt: skip
    def test_coordonnees_refusees(self, pro, quartier, champ, texte):
        r = pro.post("/v1/pro/listings", donnees_annonce(quartier, **{champ: texte}), format="json")
        assert r.status_code == 400 and r.json()["error"]["code"] == "contact_detected"
        assert Listing.objects.count() == 0

    def test_un_lien_dans_le_markdown_est_refuse_comme_un_contact(self, pro, quartier):
        r = pro.post(
            "/v1/pro/listings",
            donnees_annonce(quartier, description_md="[clic](http://x.y)"),
            format="json",
        )
        assert r.json()["error"]["code"] == "contact_detected"

    def test_les_montants_ne_sont_pas_pris_pour_des_numeros(self, pro, quartier):
        creer(
            pro,
            quartier,
            description_md="Loyer 25 000 FCFA, caution 50 000 000 F, avance 25000 CFA.",
        )

    def test_markdown_dangereux_neutralise(self, pro, quartier):
        a = creer(
            pro,
            quartier,
            description_md="<script>alert(1)</script>[clic](page) ![i](image) `code` # Titre",
        )
        html = Listing.objects.get(pk=a["id"]).description_html
        assert (
            "<script" not in html and "<a" not in html and "<img" not in html and "http" not in html
        )


class TestAutorisations:
    def test_sans_jeton(self):
        assert APIClient().get("/v1/pro/listings").status_code == 401

    def test_un_locataire_n_a_pas_acces(self):
        r = client_de(ClientFactory()).get("/v1/pro/listings")
        assert r.status_code == 403 and r.json()["error"]["code"] == "wrong_audience"

    def test_un_autre_gerant_ne_voit_rien(self, pro, quartier):
        a = creer(pro, quartier)
        autre = client_de(gerant_verifie().user)
        for appel in (autre.get, autre.delete):
            assert appel(f"/v1/pro/listings/{a['id']}").status_code == 404
        assert (
            autre.patch(
                f"/v1/pro/listings/{a['id']}", {"title": "Volée par un autre"}, format="json"
            ).status_code
            == 404
        )
        assert autre.post(f"/v1/pro/listings/{a['id']}/publish").status_code == 404
        assert autre.get("/v1/pro/listings").json() == []

    def test_districts_publics(self, quartier):
        r = APIClient().get("/v1/districts")
        assert r.status_code == 200 and r.json()[0]["slug"] == quartier.slug


class TestPosition:
    """Décision V7 : la position n'est plus demandée ; centre du quartier, ou GPS partagé par le gérant."""

    def test_sans_position_la_chambre_est_au_centre_du_quartier(self, pro):
        quartier = DistrictFactory(latitude=9.36, longitude=2.61)
        corps = donnees_annonce(quartier)
        corps.pop("latitude"), corps.pop("longitude")
        r = pro.post("/v1/pro/listings", corps, format="json")
        assert r.status_code == 201, r.content
        assert (r.json()["latitude"], r.json()["longitude"]) == (9.36, 2.61)
        assert r.json()["distance_to_campus_m"] == geo.distance_au_campus(9.36, 2.61)

    def test_une_seule_coordonnee_refusee(self, pro, quartier):
        corps = donnees_annonce(quartier)
        corps.pop("longitude")
        r = pro.post("/v1/pro/listings", corps, format="json")
        assert r.status_code == 400 and "latitude" in r.json()["error"]["fields"]

    def test_changer_de_quartier_replace_la_chambre(self, pro, quartier):
        a = creer(pro, quartier, latitude="9.341000", longitude="2.633000")
        autre = DistrictFactory(latitude=9.38, longitude=2.6)
        r = pro.patch(f"/v1/pro/listings/{a['id']}", {"district": str(autre.pk)}, format="json")
        assert (r.json()["latitude"], r.json()["longitude"]) == (9.38, 2.6)

    def test_le_gps_reste_si_le_quartier_ne_change_pas(self, pro, quartier):
        a = creer(pro, quartier, latitude="9.341000", longitude="2.633000")
        r = pro.patch(
            f"/v1/pro/listings/{a['id']}",
            {"district": str(quartier.pk), "rent_amount": 26000},
            format="json",
        )
        assert (r.json()["latitude"], r.json()["longitude"]) == (9.341, 2.633)


class TestModification:
    def test_modifier_recalcule_la_distance(self, pro, quartier):
        a = creer(pro, quartier)
        r = pro.patch(
            f"/v1/pro/listings/{a['id']}",
            {"latitude": "9.4", "longitude": "2.7", "rent_amount": 30000},
            format="json",
        )
        assert r.status_code == 200 and r.json()["rent_amount"] == 30000
        assert r.json()["distance_to_campus_m"] > a["distance_to_campus_m"]
        ligne = AuditLog.objects.get(action="listing.modifiee")
        assert (ligne.metadata["loyer_avant"], ligne.metadata["loyer_apres"]) == (25000, 30000)

    def test_supprimer_un_brouillon(self, pro, quartier):
        a = creer(pro, quartier)
        assert pro.delete(f"/v1/pro/listings/{a['id']}").status_code == 204
        assert pro.get(f"/v1/pro/listings/{a['id']}").status_code == 404

    def test_une_annonce_publiee_ne_se_supprime_pas(self, gerant, pro):
        a = ListingFactory(gerant=gerant)
        assert pro.delete(f"/v1/pro/listings/{a.pk}").status_code == 409


class TestPublication:
    def test_manques_listes(self, pro, quartier):
        a = creer(pro, quartier)
        r = pro.post(f"/v1/pro/listings/{a['id']}/publish")
        assert r.status_code == 409 and r.json()["error"]["code"] == "listing_not_publishable"
        assert {"video_prete", "trois_photos_pretes"} <= set(r.json()["error"]["fields"]["manques"])

    def test_gerant_non_verifie(self, quartier):
        from apps.accounts.tests.fabriques import GerantProfileFactory

        p = GerantProfileFactory()
        c = client_de(p.user)
        a = creer(c, quartier)
        medias_prets(Listing.objects.get(pk=a["id"]))
        r = c.post(f"/v1/pro/listings/{a['id']}/publish")
        assert (
            r.status_code == 409 and "gerant_non_verifie" in r.json()["error"]["fields"]["manques"]
        )

    def test_premiere_annonce_attend_la_relecture(self, pro, quartier):
        a = creer(pro, quartier)
        medias_prets(Listing.objects.get(pk=a["id"]))
        assert pro.post(f"/v1/pro/listings/{a['id']}/publish").json()["status"] == "processing"

    def test_annonce_suivante_publiee_directement(self, gerant, pro, quartier):
        ListingFactory(gerant=gerant)  # une première annonce déjà publiée
        a = creer(pro, quartier)
        medias_prets(Listing.objects.get(pk=a["id"]))
        r = pro.post(f"/v1/pro/listings/{a['id']}/publish").json()
        assert r["status"] == "published" and r["published_at"] and r["last_confirmed_at"]
        statut = AuditLog.objects.filter(action="listing.status_changed").latest("id")
        assert (statut.metadata["ancien"], statut.metadata["nouveau"]) == ("draft", "published")

    def test_media_en_traitement_met_l_annonce_en_attente(self, gerant, pro, quartier):
        ListingFactory(gerant=gerant)
        a = creer(pro, quartier)
        ListingMedia.objects.create(
            listing_id=a["id"], kind="video", status="processing", declared_size_bytes=1
        )
        assert pro.post(f"/v1/pro/listings/{a['id']}/publish").json()["status"] == "processing"

    def test_compte_suspendu(self, gerant, pro, quartier):
        a = creer(pro, quartier)
        type(gerant.user).objects.filter(pk=gerant.user_id).update(
            status="suspended", suspended_until=timezone.now() + timezone.timedelta(days=2)
        )
        jetons.invalider_utilisateur(gerant.user_id)
        assert pro.post(f"/v1/pro/listings/{a['id']}/publish").status_code == 403


class TestCycleDeVie:
    @pytest.fixture
    def publiee(self, gerant):
        a = ListingFactory(gerant=gerant)
        medias_prets(a)
        return a

    def test_confirmer_reinitialise_la_fraicheur(self, pro, publiee):
        Listing.objects.filter(pk=publiee.pk).update(reminder_stage=2)
        assert pro.post(f"/v1/pro/listings/{publiee.pk}/confirm").status_code == 200
        publiee.refresh_from_db()
        assert publiee.reminder_stage == 0 and publiee.last_confirmed_at

    def test_masquer_puis_confirmer_remet_en_ligne(self, pro, publiee):
        assert pro.post(f"/v1/pro/listings/{publiee.pk}/hide").json()["status"] == "hidden"
        assert pro.post(f"/v1/pro/listings/{publiee.pk}/confirm").json()["status"] == "published"

    def test_une_annonce_masquee_par_la_moderation_ne_se_confirme_pas(self, pro, publiee):
        Listing.objects.filter(pk=publiee.pk).update(status="hidden", hidden_reason="moderation")
        assert pro.post(f"/v1/pro/listings/{publiee.pk}/confirm").status_code == 409

    def test_marquer_louee_programme_la_suppression_de_la_video(self, pro, publiee):
        r = pro.post(f"/v1/pro/listings/{publiee.pk}/mark-rented").json()
        assert r["status"] == "rented"
        video = ListingMedia.objects.get(listing=publiee, kind="video")
        assert 6 <= (video.delete_after - timezone.now()).days <= 7

    def test_annuler_louee_tant_que_la_video_existe(self, pro, publiee):
        pro.post(f"/v1/pro/listings/{publiee.pk}/mark-rented")
        assert (
            pro.post(f"/v1/pro/listings/{publiee.pk}/undo-rented").json()["status"] == "published"
        )
        assert ListingMedia.objects.get(listing=publiee, kind="video").delete_after is None

    def test_annuler_louee_apres_suppression_de_la_video_exige_un_nouveau_brouillon(
        self, pro, publiee
    ):
        pro.post(f"/v1/pro/listings/{publiee.pk}/mark-rented")
        ListingMedia.objects.filter(listing=publiee, kind="video").update(status="deleted")
        assert pro.post(f"/v1/pro/listings/{publiee.pk}/undo-rented").json()["status"] == "draft"

    def test_transitions_interdites(self, pro, gerant):
        brouillon = ListingFactory(gerant=gerant, status="draft")
        assert pro.post(f"/v1/pro/listings/{brouillon.pk}/mark-rented").status_code == 409
        assert pro.post(f"/v1/pro/listings/{brouillon.pk}/hide").status_code == 409
        retiree = ListingFactory(gerant=gerant, status="removed")
        assert (
            pro.patch(
                f"/v1/pro/listings/{retiree.pk}", {"title": "Nouveau titre"}, format="json"
            ).status_code
            == 409
        )


class TestServicesPurs:
    def test_haversine(self):
        assert geo.haversine_m(9.34, 2.63, 9.34, 2.63) == 0
        assert 110_000 < geo.haversine_m(9.0, 2.63, 10.0, 2.63) < 112_000  # un degré de latitude
        assert geo.arrondir_50(1234) == 1250 and geo.arrondir_position(9.340987) == 9.341

    def test_apercu_markdown(self, pro):
        r = pro.post("/v1/pro/markdown/preview", {"markdown": "### Titre\n- a\n- b"}, format="json")
        assert (
            r.status_code == 200
            and "<h3>Titre</h3>" in r.json()["html"]
            and r.json()["html"].count("<li>") == 2
        )

    def test_description_trop_longue(self):
        from apps.core.errors import ErreurMetier

        with pytest.raises(ErreurMetier):
            contenu.rendre("a" * 4001)
        with pytest.raises(ErreurMetier):
            contenu.rendre("\n".join(f"- ligne {i}" for i in range(41)))

    @pytest.mark.parametrize(
        "texte", ["mon numéro est caché", "écris sur WhatsApp", "telegram svp"]
    )
    def test_mots_cles_seulement_signales(self, texte):
        d = contenu.detecter(texte)
        assert d.faibles and not d.fort


class TestPreparationEtStatistiques:
    """Pour l'espace gérant mobile (MM5, MM7) : mêmes sources que le site."""

    def test_ce_qui_manque_pour_publier(self, pro, quartier):
        a = creer(pro, quartier)
        r = pro.get(f"/v1/pro/listings/{a['id']}/readiness")
        assert r.status_code == 200 and r.json()["publishable"] is False
        assert {"code": "video_prete", "label": "la vidéo n'est pas encore prête"} in r.json()[
            "missing"
        ]

    def test_statistiques_par_jour(self, pro, quartier):
        from apps.core import stats

        a = creer(pro, quartier)
        stats.incrementer("views", 4, sujet=a["id"])
        stats.incrementer("conversations_started", sujet=a["id"])
        r = pro.get(f"/v1/pro/listings/{a['id']}/stats?days=7")
        corps = r.json()
        assert r.status_code == 200 and corps["days"] == 7 and len(corps["daily"]) == 7
        assert (corps["views"], corps["contacts"], corps["favorites"]) == (4, 1, 0)
        assert corps["daily"][-1]["views"] == 4

    def test_l_annonce_d_un_autre_gerant_est_introuvable(self, pro):
        autre = ListingFactory()
        assert pro.get(f"/v1/pro/listings/{autre.pk}/stats").status_code == 404
        assert pro.get(f"/v1/pro/listings/{autre.pk}/readiness").status_code == 404
