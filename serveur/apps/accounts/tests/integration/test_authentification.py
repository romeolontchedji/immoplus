"""Connexion : verrouillage progressif, réponse uniforme, travail à vide, séparation des espaces."""

import pytest
from django.contrib.auth.hashers import make_password

from apps.accounts.services import authentification, mots_de_passe, verrouillage
from apps.accounts.tests.fabriques import (
    MOT_DE_PASSE,
    AdminFactory,
    ClientFactory,
    GerantFactory,
    PersonnelFactory,
)
from apps.core import redis_file
from apps.core.errors import ErreurMetier

pytestmark = [pytest.mark.integration, pytest.mark.pg, pytest.mark.django_db]

NOM = "kofi.zongo"
SAISIE = "kofi.zongo"


@pytest.fixture
def client_inscrit():
    return ClientFactory(username=NOM)


def connexion(mdp=MOT_DE_PASSE, saisie=SAISIE, client="inst-1"):
    return authentification.authentifier(saisie, mdp, client)


def echec(mdp="faux-mot-de-passe", saisie=SAISIE, client="inst-1") -> ErreurMetier:
    with pytest.raises(ErreurMetier) as e:
        connexion(mdp, saisie, client)
    return e.value


def retirer_verrous():
    r = redis_file.client()
    for cle in r.keys("login:verrou:*"):
        r.delete(cle)


class TestConnexion:
    def test_identifiants_corrects(self, client_inscrit):
        assert connexion() == client_inscrit

    @pytest.mark.parametrize("saisie", ["Kofi.Zongo", "@kofi.zongo", " kofi.zongo "])
    def test_ecritures_du_nom_acceptees(self, client_inscrit, saisie):
        assert connexion(saisie=saisie) == client_inscrit

    def test_gerant_active(self):
        g = GerantFactory(username=NOM)
        assert connexion() == g

    def test_mauvais_mot_de_passe(self, client_inscrit):
        e = echec()
        assert (e.code, e.statut) == ("invalid_credentials", 401)
        assert int(e.entetes["Retry-After"]) >= 1

    def test_les_trois_echecs_ont_la_meme_reponse(self, client_inscrit):
        mauvais_mdp = echec()
        inconnu = echec(saisie="personne.inconnue")
        illisible = echec(saisie="n'importe quoi")
        for e in (inconnu, illisible):
            assert (e.code, e.message, e.statut) == (
                mauvais_mdp.code,
                mauvais_mdp.message,
                mauvais_mdp.statut,
            )

    def test_le_personnel_ne_peut_pas_se_connecter_au_site_ni_a_l_api(self):
        PersonnelFactory(username=NOM)  # même avec un nom d'utilisateur renseigné
        assert echec(mdp=MOT_DE_PASSE).code == "invalid_credentials"
        AdminFactory(username="chef.equipe")
        assert echec(mdp=MOT_DE_PASSE, saisie="chef.equipe").code == "invalid_credentials"

    def test_gerant_non_active_ne_peut_pas_se_connecter(self):
        g = GerantFactory(username=NOM)
        g.set_unusable_password()
        g.save()
        assert echec(mdp="").code == "invalid_credentials"
        assert echec(mdp="n'importe quoi").code == "invalid_credentials"

    def test_compte_supprime_ne_peut_pas_se_connecter(self, client_inscrit):
        from apps.accounts.services import compte

        compte.supprimer(client_inscrit, MOT_DE_PASSE)
        assert echec(mdp=MOT_DE_PASSE).code == "invalid_credentials"

    @pytest.mark.parametrize("statut", ["suspended", "banned"])
    def test_compte_suspendu_revele_apres_mot_de_passe_correct_seulement(self, statut):
        from django.utils import timezone

        ClientFactory(
            username=NOM,
            status=statut,
            suspended_until=timezone.now() + timezone.timedelta(days=3),
        )
        e = echec(mdp=MOT_DE_PASSE)
        assert (e.code, e.statut) == ("account_suspended", 403)
        assert echec().code == "invalid_credentials"  # mauvais mot de passe : aucune fuite d'état

    def test_suspension_echue_permet_la_connexion(self):
        from django.utils import timezone

        ClientFactory(
            username=NOM,
            status="suspended",
            suspended_until=timezone.now() - timezone.timedelta(hours=1),
        )
        assert connexion().username == NOM


class TestTravailAVide:
    """Le temps de réponse ne doit pas dépendre de l'existence du compte (CDC EF-AUT-05)."""

    @pytest.fixture
    def compteur(self, monkeypatch):
        appels = []
        reel = mots_de_passe.check_password

        def espion(mdp, hache, *a, **k):
            appels.append(hache)
            return reel(mdp, hache, *a, **k)

        monkeypatch.setattr(mots_de_passe, "check_password", espion)
        return appels

    def test_un_nom_inconnu_declenche_un_hachage_complet(self, client_inscrit, compteur):
        echec(saisie="personne.inconnue")
        assert len(compteur) == 1

    def test_un_nom_connu_declenche_un_hachage_et_un_seul(self, client_inscrit, compteur):
        echec()
        assert len(compteur) == 1

    def test_un_compte_sans_mot_de_passe_utilisable_declenche_aussi_un_hachage(self, compteur):
        g = GerantFactory(username=NOM)
        g.set_unusable_password()
        g.save()
        echec()
        assert len(compteur) == 1

    def test_le_hachage_factice_est_au_meme_format_que_les_vrais(
        self, client_inscrit, compteur, settings
    ):
        settings.PASSWORD_HASHERS = ["django.contrib.auth.hashers.Argon2PasswordHasher"]
        client_inscrit.password = make_password(MOT_DE_PASSE)
        client_inscrit.save()
        mots_de_passe._HACHAGE_FACTICE = None
        echec(saisie="personne.inconnue")
        echec()
        assert (
            compteur[0].split("$")[:3]
            == compteur[1].split("$")[:3]
            == ["argon2", "argon2id", "v=19"]
        )
        mots_de_passe._HACHAGE_FACTICE = None


class TestVerrouillage:
    def test_cinq_echecs_verrouillent_pour_quinze_minutes(self, client_inscrit):
        for _ in range(5):
            assert echec().code == "invalid_credentials"
        e = echec(mdp=MOT_DE_PASSE)  # même le bon mot de passe est refusé pendant le verrou
        assert (e.code, e.statut) == ("invalid_credentials", 401)
        assert 890 <= int(e.entetes["Retry-After"]) <= 900

    def test_quatre_echecs_ne_verrouillent_pas(self, client_inscrit):
        for _ in range(4):
            echec()
        assert connexion() == client_inscrit

    def test_un_nom_inconnu_se_verrouille_de_la_meme_facon(self):
        for _ in range(5):
            echec(saisie="personne.inconnue")
        e = echec(saisie="personne.inconnue")
        assert 890 <= int(e.entetes["Retry-After"]) <= 900

    def test_le_verrou_est_par_couple_nom_et_appareil(self, client_inscrit):
        for _ in range(5):
            echec(client="inst-pirate")
        assert (
            connexion(client="inst-legitime") == client_inscrit
        )  # le propriétaire n'est pas bloqué à distance

    def test_un_autre_compte_n_est_pas_touche(self, client_inscrit):
        ClientFactory(username="autre.compte")
        for _ in range(5):
            echec()
        assert connexion(saisie="autre.compte").username == "autre.compte"

    def test_duree_doublee_a_chaque_recidive(self, client_inscrit):
        durees = []
        for _ in range(3):
            for _ in range(5):
                echec()
            durees.append(int(echec().entetes["Retry-After"]))
            retirer_verrous()
        assert [round(d / 60) for d in durees] == [15, 30, 60]

    def test_un_succes_remet_le_compteur_a_zero(self, client_inscrit):
        for _ in range(4):
            echec()
        connexion()
        for _ in range(4):
            echec()
        assert connexion() == client_inscrit

    def test_un_succes_remet_aussi_la_recidive_a_zero(self, client_inscrit):
        for _ in range(5):
            echec()
        retirer_verrous()
        connexion()
        for _ in range(5):
            echec()
        assert round(int(echec().entetes["Retry-After"]) / 60) == 15

    def test_plafond_de_trente_echecs_par_heure_et_par_nom(self, client_inscrit):
        for n in range(30):
            echec(client=f"appareil-{n}")  # 30 appareils différents : aucun couple ne se verrouille
        e = echec(mdp=MOT_DE_PASSE, client="appareil-neuf")
        assert e.code == "invalid_credentials"
        assert 3500 <= int(e.entetes["Retry-After"]) <= 3600

    def test_le_plafond_horaire_ne_touche_pas_les_autres_comptes(self, client_inscrit):
        ClientFactory(username="autre.compte")
        for n in range(30):
            echec(client=f"appareil-{n}")
        assert connexion(saisie="autre.compte", client="x").username == "autre.compte"

    def test_les_compteurs_sont_dans_redis_queue_pas_dans_le_cache(self, client_inscrit):
        from django.core.cache import cache

        for _ in range(5):
            echec()
        cache.clear()  # l'éviction du cache ne libère pas un verrou
        assert echec(mdp=MOT_DE_PASSE).code == "invalid_credentials"
        assert redis_file.client().keys("login:verrou:*")

    def test_les_cles_ne_contiennent_pas_le_nom(self, client_inscrit):
        echec()
        for cle in redis_file.client().keys("login:*"):
            assert NOM not in cle

    def test_parametres_modifiables(self, client_inscrit):
        from apps.core import parametres

        parametres.definir("LOGIN_LOCK_THRESHOLD", 2)
        parametres.definir("LOGIN_LOCK_MINUTES", 1)
        echec()
        echec()
        assert int(echec().entetes["Retry-After"]) <= 60

    def test_refus_uniforme_a_les_memes_champs(self):
        e = verrouillage.refus_uniforme(5)
        assert (e.code, e.statut, e.entetes) == ("invalid_credentials", 401, {"Retry-After": "5"})
