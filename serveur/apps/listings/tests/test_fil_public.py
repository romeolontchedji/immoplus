"""Fil public, recherche, fiche, vues, favoris, alertes (CDC §7.4, §7.5, §10.3)."""

import datetime

import pytest
from django.core.cache import cache
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.services import appareils, jetons
from apps.accounts.tests.fabriques import ClientFactory
from apps.core import stats
from apps.listings import selectors
from apps.listings.models import Alert, Favorite, Listing, ListingMedia
from apps.listings.services import alertes, annonces, favoris, fil, filtres, vues
from apps.notifications.models import Notification

from .fabriques import DistrictFactory, ListingFactory, gerant_verifie, medias_prets

pytestmark = [pytest.mark.integration, pytest.mark.pg, pytest.mark.django_db]


def indexer(a):
    annonces._vecteur_de_recherche(a)
    return a


def client_de(utilisateur, installation="inst-1") -> APIClient:
    d, _ = appareils.ouvrir(utilisateur, installation_id=installation, platform="android")
    c = APIClient()
    c.credentials(HTTP_AUTHORIZATION=f"Bearer {jetons.emettre_acces(utilisateur, d)}")
    return c


def f(**params):
    return filtres.normaliser(params)


class TestFiltres:
    def test_valeurs_par_defaut(self):
        d = f()
        assert d["sort"] == "recent" and d["limit"] == 10 and not filtres.a_des_criteres(d)

    @pytest.mark.parametrize(
        ("params", "champ"),
        [
            ({"sort": "hasard"}, "sort"),
            ({"type": "chateau"}, "type"),
            ({"water": "mer"}, "water"),
            ({"rent_min": "abc"}, "rent_min"),
            ({"rent_min": "100", "rent_max": "50"}, "rent_min"),
            ({"available_before": "demain"}, "available_before"),
            ({"bathroom": "peut-être"}, "bathroom"),
            ({"limit": "500"}, "limit"),
        ],
    )
    def test_refus(self, params, champ):
        from apps.core.errors import ErreurMetier

        with pytest.raises(ErreurMetier) as e:
            f(**params)
        assert champ in e.value.champs

    def test_criteres_valides(self):
        d = f(q="  chambre  douche ", type="single,studio", bathroom="true", fenced="0", rent_max="30000",
              available_before="2026-12-01", district="a,b", max_distance_m="800")  # fmt: skip
        assert d["q"] == "chambre douche" and d["types"] == ["single", "studio"]
        assert (
            d["bathroom"] is True
            and d["fenced"] is False
            and d["available_before"] == datetime.date(2026, 12, 1)
        )
        assert filtres.a_des_criteres(d)


class TestFil:
    def test_seules_les_annonces_publiees_apparaissent_les_recentes_d_abord(self):
        vieille = ListingFactory(published_at=timezone.now() - datetime.timedelta(days=2))
        recente = ListingFactory()
        ListingFactory(status="hidden")
        ListingFactory(status="rented")
        ListingFactory(status="draft", published_at=None)
        ListingFactory(deleted_at=timezone.now())
        ids = [c["id"] for c in selectors.fil(f())["items"]]
        assert ids == [recente.pk, vieille.pk]

    def test_pagination_par_curseur_sans_doublon_ni_oubli(self):
        base = timezone.now()
        creees = [
            ListingFactory(published_at=base - datetime.timedelta(minutes=i)) for i in range(7)
        ]
        p1 = selectors.fil(f(limit="3"))
        p2 = selectors.fil(f(limit="3", cursor=p1["next_cursor"]))
        p3 = selectors.fil(f(limit="3", cursor=p2["next_cursor"]))
        ids = [c["id"] for p in (p1, p2, p3) for c in p["items"]]
        assert ids == [a.pk for a in creees] and p3["next_cursor"] is None

    def test_egalite_de_date_departagee_par_identifiant(self):
        instant = timezone.now()
        [ListingFactory(published_at=instant) for _ in range(5)]
        p1 = selectors.fil(f(limit="2"))
        p2 = selectors.fil(f(limit="2", cursor=p1["next_cursor"]))
        p3 = selectors.fil(f(limit="2", cursor=p2["next_cursor"]))
        ids = [c["id"] for p in (p1, p2, p3) for c in p["items"]]
        assert len(ids) == len(set(ids)) == 5

    @pytest.mark.parametrize(
        ("tri", "cle", "sens"),
        [
            ("rent_asc", "rent_amount", 1),
            ("rent_desc", "rent_amount", -1),
            ("distance", "distance_m", 1),
        ],
    )
    def test_tris_et_curseur_par_tri(self, tri, cle, sens):
        for i, (loyer, dist) in enumerate(
            [(30000, 900), (15000, 300), (22000, 1200), (18000, 50), (26000, 700)]
        ):
            ListingFactory(rent_amount=loyer, distance_to_campus_m=dist, title=f"Chambre test {i}")
        p1 = selectors.fil(f(sort=tri, limit="2"))
        p2 = selectors.fil(f(sort=tri, limit="2", cursor=p1["next_cursor"]))
        p3 = selectors.fil(f(sort=tri, limit="2", cursor=p2["next_cursor"]))
        valeurs = [c[cle] for p in (p1, p2, p3) for c in p["items"]]
        assert len(valeurs) == 5 and valeurs == sorted(valeurs, reverse=sens < 0)

    def test_curseur_d_un_autre_tri_ou_corrompu_refuse(self):
        from apps.core.errors import ErreurMetier

        ListingFactory.create_batch(3)
        curseur = selectors.fil(f(limit="1"))["next_cursor"]
        for mauvais in (curseur, "n'importe quoi", None):
            if mauvais is None:
                continue
            with pytest.raises(ErreurMetier) as e:
                selectors.fil(f(sort="rent_asc", cursor=mauvais))
            assert e.value.code == "invalid_cursor"

    def test_filtres_combines(self):
        q1, q2 = DistrictFactory(slug="banikanni"), DistrictFactory(slug="titirou")
        bon = ListingFactory(district=q1, rent_amount=20000, room_type="studio", has_private_bathroom=True,
                             is_fenced=True, water_source="borehole", electricity_meter="shared",
                             distance_to_campus_m=400, available_from="2026-10-15")  # fmt: skip
        ListingFactory(district=q2, rent_amount=20000, room_type="studio")
        ListingFactory(district=q1, rent_amount=50000, room_type="studio")
        ListingFactory(district=q1, rent_amount=20000, room_type="single")
        ListingFactory(
            district=q1, rent_amount=20000, room_type="studio", has_private_bathroom=False
        )
        ListingFactory(
            district=q1, rent_amount=20000, room_type="studio", distance_to_campus_m=3000
        )
        r = selectors.fil(f(district="banikanni", type="studio", rent_min="10000", rent_max="30000", bathroom="true",
                            water="borehole", meter="shared", fenced="true", available_before="2026-11-01",
                            max_distance_m="500"))  # fmt: skip
        assert [c["id"] for c in r["items"]] == [bon.pk]

    def test_recherche_sans_accents_et_tolerante_aux_fautes(self):
        a = indexer(
            ListingFactory(
                title="Chambre propre près du campus", landmark_text="Derrière la pharmacie"
            )
        )
        b = indexer(
            ListingFactory(title="Studio moderne à Banikanni", landmark_text="Près du marché")
        )
        for requete, attendu in [("pres du campus", a), ("chambre", a), ("CHAMBRE", a), ("chmabre", a),
                                 ("studio", b), ("studio banikani", b), ("pharmacie", a)]:  # fmt: skip
            ids = [c["id"] for c in selectors.fil(f(q=requete))["items"]]
            assert attendu.pk in ids, requete
        assert selectors.fil(f(q="zzzzqqqq"))["items"] == []

    def test_une_apostrophe_ou_un_symbole_ne_casse_pas_la_recherche(self):
        indexer(ListingFactory())
        for q in ("l'ami", '"chambre"', "a & b | c", "% _ \\", "(((", "chambre -"):
            selectors.fil(f(q=q))

    def test_carte_legere_sans_donnee_privee(self):
        a = ListingFactory(address_private="Rue 12 maison bleue")
        medias_prets(a, photos=3, video=True)
        carte = selectors.fil(f())["items"][0]
        texte = str(carte)
        assert "Rue 12" not in texte and "address_private" not in carte and "phone" not in texte
        assert carte["distance_m"] == 500 and carte["has_video"] is True
        assert len(__import__("json").dumps(carte, default=str)) < 4096

    def test_cout_en_requetes_borne(self, django_assert_max_num_queries):
        for a in ListingFactory.create_batch(10):
            medias_prets(a)
        cache.clear()
        with django_assert_max_num_queries(4):
            assert len(selectors.fil(f())["items"]) == 10

    def test_cache_de_page_invalide_par_changement_de_statut(self):
        a = ListingFactory()
        assert len(selectors.fil(f())["items"]) == 1
        Listing.objects.filter(pk=a.pk).update(status="hidden")
        assert len(selectors.fil(f())["items"]) == 1  # encore en cache (60 s)
        selectors.invalider_fil()
        assert selectors.fil(f())["items"] == []

    def test_changer_statut_invalide_le_cache(self):
        p = gerant_verifie()
        a = ListingFactory(gerant=p)
        assert selectors.fil(f())["items"]
        annonces.changer_statut(a, "hidden", acteur=p.user, raison="owner")
        assert selectors.fil(f())["items"] == []

    def test_recherche_vide_compte_et_propose_une_alerte(self):
        r = fil.rechercher({"q": "introuvable", "max_distance_m": "100"})
        assert r["vide"] and r["alerte_proposee"] and stats.lire("search_empty") == 1
        fil.rechercher({"q": "introuvable", "cursor": None})
        assert stats.lire("search_empty") == 2


class TestFiche:
    def test_fiche_complete_sans_donnee_privee(self):
        p = gerant_verifie()
        a = ListingFactory(gerant=p, address_private="Rue 12 maison bleue", latitude="9.341234",
                           longitude="2.633987", distance_to_campus_m=530, description_html="<p>Calme</p>")  # fmt: skip
        medias_prets(a)
        fiche = selectors.fiche_publique(a.slug)
        assert (
            fiche["latitude"] == 9.341
            and fiche["longitude"] == 2.634
            and fiche["distance_m"] == 550
        )
        assert fiche["gerant"]["verified"] is True
        assert "Rue 12" not in str(fiche) and "address_private" not in fiche
        assert str(p.user.phone_e164) not in str(fiche)
        assert fiche["media"][0]["kind"] in ("video", "photo")

    def test_par_identifiant_ou_slug_et_statuts(self):
        a = ListingFactory()
        assert selectors.fiche_publique(a.pk)["id"] == a.pk
        assert selectors.fiche_publique(a.slug)["id"] == a.pk
        for statut in ("hidden", "draft", "archived", "removed"):
            Listing.objects.filter(pk=a.pk).update(status=statut)
            assert selectors.fiche_publique(a.slug) is None
        Listing.objects.filter(pk=a.pk).update(status="rented")
        assert selectors.fiche_publique(a.slug)["status"] == "rented"
        assert selectors.fiche_publique("inconnue") is None

    def test_annonce_louee_sans_video(self):
        a = ListingFactory(status="rented")
        medias_prets(a, video=True)
        assert all(m["kind"] != "video" for m in selectors.fiche_publique(a.slug)["media"])

    def test_variantes_photo(self):
        a = ListingFactory()
        ListingMedia.objects.create(
            listing=a, kind="photo", status="ready", declared_size_bytes=1, is_cover=True,
            variants={"480": "w480.webp", "960": "w960.webp", "1600": "w1600.webp"},
            poster_path=f"listings/{a.pk}/m1/w1600.webp",
        )  # fmt: skip
        fiche = selectors.fiche_publique(a.slug)
        assert fiche["media"][0]["url"].endswith("/w960.webp") and fiche["media"][0][
            "thumb_url"
        ].endswith("/w480.webp")
        assert selectors.fil(f())["items"][0]["cover_url"].endswith("/w480.webp")


class TestApi:
    def test_fil_et_fiche_sans_compte(self):
        a = ListingFactory()
        c = APIClient()
        r = c.get("/v1/listings?limit=5")
        assert r.status_code == 200 and r["Cache-Control"].startswith("public")
        assert r.json()["items"][0]["slug"] == a.slug
        assert c.get(f"/v1/listings/{a.pk}").json()["is_favorite"] is False
        assert c.get(f"/v1/listings/{a.slug}").status_code == 200
        assert c.get("/v1/listings/inexistante").json()["error"]["code"] == "not_found"

    def test_parametre_invalide(self):
        r = APIClient().get("/v1/listings?sort=nimporte")
        assert r.status_code == 400 and "sort" in r.json()["error"]["fields"]

    def test_jeton_invalide_refuse_meme_en_lecture_publique(self):
        c = APIClient()
        c.credentials(HTTP_AUTHORIZATION="Bearer faux")
        assert c.get("/v1/listings").status_code == 401

    def test_is_favorite_pour_un_locataire_connecte(self):
        a, u = ListingFactory(), ClientFactory()
        c = client_de(u)
        assert c.put(f"/v1/me/favorites/{a.pk}").status_code == 204
        assert c.get(f"/v1/listings/{a.slug}").json()["is_favorite"] is True

    def test_vues_dedupliquees_sans_proprietaire_ni_robot(self):
        p = gerant_verifie()
        a = ListingFactory(gerant=p)
        anonyme = APIClient()
        assert anonyme.post(f"/v1/listings/{a.slug}/views", HTTP_X_INSTALLATION_ID="i1").json() == {
            "counted": True
        }
        assert anonyme.post(f"/v1/listings/{a.slug}/views", HTTP_X_INSTALLATION_ID="i1").json() == {
            "counted": False
        }
        assert anonyme.post(f"/v1/listings/{a.slug}/views", HTTP_X_INSTALLATION_ID="i2").json() == {
            "counted": True
        }
        assert anonyme.post(
            f"/v1/listings/{a.slug}/views", HTTP_USER_AGENT="Googlebot/2.1"
        ).json() == {"counted": False}
        assert client_de(p.user).post(f"/v1/listings/{a.slug}/views").json() == {"counted": False}
        assert client_de(ClientFactory(), "i3").post(f"/v1/listings/{a.slug}/views").json() == {
            "counted": True
        }
        assert vues.vider_compteurs() == 3
        assert stats.lire("views", sujet=str(a.pk)) == 3
        assert vues.vider_compteurs() == 0  # idempotent
        assert anonyme.post("/v1/listings/inconnue/views").status_code == 404

    def test_les_gerants_n_ont_pas_de_favoris(self):
        r = client_de(gerant_verifie().user).get("/v1/me/favorites")
        assert r.status_code == 403 and r.json()["error"]["code"] == "wrong_audience"


class TestFavoris:
    def test_ajout_idempotent_liste_retrait(self):
        a, u = ListingFactory(), ClientFactory()
        c = client_de(u)
        c.put(f"/v1/me/favorites/{a.pk}")
        c.put(f"/v1/me/favorites/{a.pk}")
        assert Favorite.objects.filter(user=u).count() == 1
        assert (
            stats.lire("favorites_added") == 1
            and stats.lire("favorites_added", sujet=str(a.pk)) == 1
        )
        assert [x["id"] for x in c.get("/v1/me/favorites").json()] == [str(a.pk)]
        assert c.delete(f"/v1/me/favorites/{a.pk}").status_code == 204
        assert c.get("/v1/me/favorites").json() == []

    def test_une_annonce_masquee_ne_se_met_pas_en_favori(self):
        a = ListingFactory(status="hidden")
        assert client_de(ClientFactory()).put(f"/v1/me/favorites/{a.pk}").status_code == 404

    def test_une_annonce_louee_reste_visible_dans_les_favoris(self):
        a, u = ListingFactory(), ClientFactory()
        favoris.ajouter(u, a.pk)
        Listing.objects.filter(pk=a.pk).update(status="rented")
        assert selectors.favoris_de(u.pk)[0]["status"] == "rented"

    def test_plafond(self, monkeypatch):
        monkeypatch.setattr(favoris, "LIMITE", 2)
        u = ClientFactory()
        from apps.core.errors import ErreurMetier

        for a in ListingFactory.create_batch(2):
            favoris.ajouter(u, a.pk)
        with pytest.raises(ErreurMetier) as e:
            favoris.ajouter(u, ListingFactory().pk)
        assert e.value.code == "favorites_limit"

    def test_notification_quand_un_favori_devient_loue_une_seule_fois(
        self, django_capture_on_commit_callbacks
    ):
        p = gerant_verifie()
        a, u1, u2 = ListingFactory(gerant=p), ClientFactory(), ClientFactory()
        favoris.ajouter(u1, a.pk)
        favoris.ajouter(u2, a.pk)
        with django_capture_on_commit_callbacks(execute=True):
            annonces.marquer_louee(p, a.pk)
        assert Notification.objects.filter(kind="favorite.unavailable").count() == 2
        assert favoris.notifier_indisponibilite(a.pk, "rented") == 0  # clé d'unicité

    def test_notification_quand_un_favori_est_masque(self, django_capture_on_commit_callbacks):
        p = gerant_verifie()
        a, u = ListingFactory(gerant=p), ClientFactory()
        favoris.ajouter(u, a.pk)
        with django_capture_on_commit_callbacks(execute=True):
            annonces.masquer(p, a.pk)
        n = Notification.objects.get(kind="favorite.unavailable")
        assert "n'est plus disponible" in n.title and n.user_id == u.pk


class TestAlertes:
    def test_creation_modification_suppression(self):
        q, u = DistrictFactory(), ClientFactory()
        c = client_de(u)
        r = c.post("/v1/me/alerts", {"label": "Près du campus", "district_ids": [str(q.pk)], "room_types": ["studio"],
                                     "max_rent": 30000, "private_bathroom_required": True}, format="json")  # fmt: skip
        assert r.status_code == 201
        ident = r.json()["id"]
        assert (
            c.patch(f"/v1/me/alerts/{ident}", {"max_rent": 20000}, format="json").json()["max_rent"]
            == 20000
        )
        assert len(c.get("/v1/me/alerts").json()) == 1
        assert c.delete(f"/v1/me/alerts/{ident}").status_code == 204
        assert c.get("/v1/me/alerts").json() == []

    def test_cinq_alertes_actives_au_plus(self):
        u = ClientFactory()
        c = client_de(u)
        for _ in range(5):
            assert c.post("/v1/me/alerts", {"max_rent": 20000}, format="json").status_code == 201
        r = c.post("/v1/me/alerts", {"max_rent": 20000}, format="json")
        assert r.status_code == 409 and r.json()["error"]["code"] == "alerts_limit"
        premiere = Alert.objects.filter(user=u).first()
        c.patch(f"/v1/me/alerts/{premiere.pk}", {"is_active": False}, format="json")
        assert c.post("/v1/me/alerts", {"max_rent": 20000}, format="json").status_code == 201
        assert (
            c.patch(f"/v1/me/alerts/{premiere.pk}", {"is_active": True}, format="json").status_code
            == 409
        )

    def test_validations(self):
        c = client_de(ClientFactory())
        assert (
            c.post(
                "/v1/me/alerts",
                {"district_ids": ["00000000-0000-0000-0000-000000000000"]},
                format="json",
            ).status_code
            == 400
        )
        assert (
            c.post("/v1/me/alerts", {"room_types": ["château"]}, format="json").status_code == 400
        )
        assert c.post("/v1/me/alerts", {"max_rent": -5}, format="json").status_code == 400

    def test_alerte_d_un_autre_introuvable(self):
        autre = Alert.objects.create(user=ClientFactory())
        c = client_de(ClientFactory())
        assert c.delete(f"/v1/me/alerts/{autre.pk}").status_code == 404
        assert (
            c.patch(f"/v1/me/alerts/{autre.pk}", {"max_rent": 5}, format="json").status_code == 404
        )
        assert c.delete("/v1/me/alerts/pas-un-uuid").status_code == 404

    def test_correspondance_sql(self):
        q1, q2 = DistrictFactory(), DistrictFactory()
        a = ListingFactory(
            district=q1,
            room_type="studio",
            rent_amount=20000,
            distance_to_campus_m=400,
            has_private_bathroom=False,
        )
        u = [ClientFactory() for _ in range(8)]
        Alert.objects.create(user=u[0])  # tout
        Alert.objects.create(
            user=u[1],
            district_ids=[q1.pk],
            room_types=["studio"],
            max_rent=25000,
            max_distance_m=500,
        )
        Alert.objects.create(user=u[2], district_ids=[q2.pk])  # autre quartier
        Alert.objects.create(user=u[3], max_rent=10000)  # trop chère
        Alert.objects.create(user=u[4], room_types=["single"])  # autre type
        Alert.objects.create(user=u[5], private_bathroom_required=True)  # douche exigée
        Alert.objects.create(user=u[6], max_distance_m=100)  # trop loin
        Alert.objects.create(user=u[7], is_active=False)  # inactive
        assert {uid for _, uid in selectors.alertes_correspondantes(a.pk)} == {u[0].pk, u[1].pk}

    def test_publication_notifie_une_fois_par_couple(self, django_capture_on_commit_callbacks):
        p = gerant_verifie()
        u = ClientFactory()
        alerte = Alert.objects.create(user=u, max_rent=30000)
        a = ListingFactory(gerant=p, status="draft", published_at=None)
        medias_prets(a)
        with django_capture_on_commit_callbacks(execute=True):
            annonces.mettre_en_ligne(a, acteur=p.user)
        n = Notification.objects.get(kind="alert.match")
        assert n.dedupe_key == f"alert:{alerte.pk}:{a.pk}" and n.data["listing_id"] == str(a.pk)
        assert alertes.notifier_correspondances(a.pk) == 0
        assert Notification.objects.filter(kind="alert.match").count() == 1

    def test_pas_de_notification_pour_une_annonce_non_publiee(self):
        a = ListingFactory(status="draft", published_at=None)
        Alert.objects.create(user=ClientFactory())
        assert alertes.notifier_correspondances(a.pk) == 0


class TestNotificationsGerant:
    def test_masquage_par_peremption_previent_le_gerant(self, django_capture_on_commit_callbacks):
        p = gerant_verifie()
        a = ListingFactory(gerant=p)
        with django_capture_on_commit_callbacks(execute=True):
            annonces.changer_statut(a, "hidden", acteur=None, raison="stale")
        n = Notification.objects.get(kind="listing.hidden")
        assert n.user_id == p.user_id and "confirmée" in n.body

    def test_masquage_par_le_gerant_ne_le_notifie_pas(self, django_capture_on_commit_callbacks):
        p = gerant_verifie()
        a = ListingFactory(gerant=p)
        with django_capture_on_commit_callbacks(execute=True):
            annonces.masquer(p, a.pk)
        assert not Notification.objects.filter(kind="listing.hidden").exists()

    def test_mise_en_ligne_apres_traitement_notifie(self, django_capture_on_commit_callbacks):
        p = gerant_verifie()
        a = ListingFactory(gerant=p, status="processing", published_at=None)
        medias_prets(a)
        with django_capture_on_commit_callbacks(execute=True):
            annonces.mettre_en_ligne(a, acteur=p.user)
        assert Notification.objects.filter(kind="listing.published", user=p.user).count() == 1

    def test_echec_de_media_previent_le_gerant(self):
        from apps.listings.services import medias as svc

        p = gerant_verifie()
        a = ListingFactory(gerant=p)
        m = ListingMedia.objects.create(
            listing=a, kind="video", status="failed", declared_size_bytes=1
        )
        svc._notifier_echec(m, "Vidéo trop courte.")
        svc._notifier_echec(m, "Vidéo trop courte.")
        n = Notification.objects.get(kind="listing.media_failed")
        assert n.body == "Vidéo trop courte." and n.user_id == p.user_id


class TestTableauDeBord:
    def test_indicateurs_du_gerant(self):
        from apps.chat import services as chat

        p = gerant_verifie()
        a = ListingFactory(gerant=p)
        ListingFactory(gerant=p, status="hidden")
        ListingFactory(gerant=p, last_confirmed_at=timezone.now() - datetime.timedelta(days=9))
        chat.ouvrir(ClientFactory(), a.pk, "Bonjour", str(__import__("uuid").uuid4()))
        client = client_de(ClientFactory(), "i-vue")
        client.post(f"/v1/listings/{a.slug}/views")
        vues.vider_compteurs()
        favoris.ajouter(ClientFactory(), a.pk)
        r = client_de(p.user, "i-g").get("/v1/pro/dashboard")
        assert r.status_code == 200
        d = r.json()
        assert d["listings_by_status"] == {"published": 2, "hidden": 1}
        assert d["views_30d"] == 1 and d["favorites_30d"] == 1 and d["conversations_30d"] == 1
        assert d["to_confirm"] == 1 and d["unread_messages"] == 1
        assert d["response_rate_30d"] is None and d["median_response_min"] is None

    def test_reserve_aux_gerants(self):
        assert client_de(ClientFactory()).get("/v1/pro/dashboard").status_code == 403
        assert APIClient().get("/v1/pro/dashboard").status_code == 401
