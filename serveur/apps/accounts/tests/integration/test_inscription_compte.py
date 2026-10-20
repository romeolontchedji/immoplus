"""Inscription, mot de passe oublié, gestion du compte et activation des gérants, sans code SMS (ADR 0009)."""

import pytest
from django.core import mail

from apps.accounts import signals
from apps.accounts.models import Device, User
from apps.accounts.services import (
    administration,
    appareils,
    compte,
    identifiants,
    inscription,
    jetons,
    mots_de_passe,
)
from apps.accounts.tests.fabriques import (
    MOT_DE_PASSE,
    AdminFactory,
    ClientFactory,
    PersonnelFactory,
)
from apps.audit.models import AuditLog
from apps.core.errors import ErreurMetier

pytestmark = [pytest.mark.integration, pytest.mark.pg, pytest.mark.django_db]

TEL = "+2290197121212"
FORT = "un-Mot-de-passe-solide-42"


def refus(fonction, *args, **kwargs) -> ErreurMetier:
    with pytest.raises(ErreurMetier) as e:
        fonction(*args, **kwargs)
    return e.value


def inscrire(**kw):
    base = {
        "nom_utilisateur": "awa.bio", "prenom": "Awa", "nom": "Bio", "telephone": "97121212",
        "mot_de_passe": FORT, "cgu_acceptees": True,
    }  # fmt: skip
    return inscription.inscrire_client(**{**base, **kw})


def jeton_du_lien(url: str) -> str:
    return url.rsplit("/", 1)[1]


class TestInscription:
    def test_cree_le_locataire_sans_code(self):
        u, cle = inscrire(ip="41.0.0.1")
        assert (u.role, u.username, u.phone_e164, u.full_name, u.status) == (
            "client", "awa.bio", TEL, "Awa Bio", "active",
        )  # fmt: skip
        assert (u.first_name, u.last_name) == ("Awa", "Bio") and u.phone_verified_at is None
        assert u.terms_version == "1" and u.terms_accepted_at
        assert u.check_password(FORT) and u.password.startswith(("md5$", "argon2$"))
        assert identifiants.cle_correcte(u, cle) and u.recovery_key_created_at

    def test_trace_l_acceptation_des_cgu(self):
        u, _ = inscrire(ip="41.0.0.1", user_agent="Immo+/1.0")
        ligne = AuditLog.objects.get(action="terms.accepted")
        assert (ligne.actor_id, ligne.metadata, str(ligne.ip)) == (
            u.pk,
            {"version": "1"},
            "41.0.0.1",
        )

    def test_cgu_obligatoires(self):
        assert refus(inscrire, cgu_acceptees=False).code == "terms_not_accepted"
        assert not User.objects.exists()

    @pytest.mark.parametrize("prenom", ["", "   ", "x" * 61])
    def test_prenom_invalide(self, prenom):
        assert refus(inscrire, prenom=prenom).code == "validation_error"

    @pytest.mark.parametrize(
        "nom_utilisateur",
        ["ab", "a" * 31, "awa bio!", ".awa", "awa.", "awa..bio", "admin", "Immo_Plus"],
    )
    def test_nom_d_utilisateur_refuse(self, nom_utilisateur):
        assert refus(inscrire, nom_utilisateur=nom_utilisateur).code == "validation_error"

    def test_nom_normalise_et_unique_sans_tenir_compte_des_majuscules(self):
        u, _ = inscrire(nom_utilisateur="@Aïcha.Zongo")
        assert u.username == "aicha.zongo"
        assert refus(inscrire, nom_utilisateur="AICHA.ZONGO").code == "username_taken"

    def test_le_numero_n_est_pas_unique(self):
        inscrire()
        u, _ = inscrire(nom_utilisateur="autre.compte")
        assert User.objects.filter(phone_e164=u.phone_e164).count() == 2

    @pytest.mark.parametrize("mdp", ["123", "court-9", "password123", "awabio2026"])
    def test_mot_de_passe_faible(self, mdp):
        assert refus(inscrire, mot_de_passe=mdp).code == "validation_error"

    def test_numero_invalide(self):
        assert refus(inscrire, telephone="12").code == "validation_error"

    def test_les_espaces_des_noms_sont_normalises(self):
        u, _ = inscrire(prenom="  Awa  ", nom=" Bio   Kora ")
        assert u.full_name == "Awa Bio Kora"


class TestMotDePasseOublie:
    def test_cle_de_secours_revoque_tout_et_se_renouvelle(self):
        u, cle = inscrire()
        d1, _ = appareils.ouvrir(u, installation_id="a", platform="android")
        ancien_acces = jetons.emettre_acces(u, d1)
        _, nouvelle = inscription.reinitialiser_par_cle(
            "awa.bio", cle, "nouveau-Mot-de-passe-7", client="x"
        )
        u.refresh_from_db()
        assert u.check_password("nouveau-Mot-de-passe-7") and u.token_version == 1
        assert Device.objects.filter(user=u, revoked_at__isnull=True).count() == 0
        assert refus(jetons.verifier_acces, ancien_acces).code == "invalid_token"
        assert identifiants.cle_correcte(u, nouvelle) and not identifiants.cle_correcte(u, cle)
        ligne = AuditLog.objects.get(action="auth.mot_de_passe_reinitialise")
        assert ligne.metadata == {"porte": "cle_de_secours"}

    def test_cle_fausse_ou_compte_inconnu(self):
        inscrire()
        assert (
            refus(
                inscription.reinitialiser_par_cle,
                "awa.bio",
                "AAAA-BBBB-CCCC-DDDD",
                FORT,
                client="x",
            ).statut
            == 401
        )
        assert (
            refus(
                inscription.reinitialiser_par_cle,
                "personne",
                "AAAA-BBBB-CCCC-DDDD",
                FORT,
                client="y",
            ).statut
            == 401
        )

    def test_lien_par_email_seulement_si_l_email_est_confirme(
        self, django_capture_on_commit_callbacks
    ):
        u, _ = inscrire()
        inscription.demander_lien_par_email("awa.bio")
        assert not mail.outbox  # pas d'e-mail confirmé : rien n'est envoyé, rien n'est révélé
        u.email, u.email_verified_at = "awa@exemple.bj", u.created_at
        u.save()
        inscription.demander_lien_par_email("AWA@exemple.bj")
        assert len(mail.outbox) == 1 and "/mot-de-passe/nouveau/" in mail.outbox[0].body

    def test_lien_a_usage_unique(self):
        u, _ = inscrire()
        jeton = identifiants.creer_jeton(u, "reinitialisation")
        inscription.reinitialiser_par_lien(jeton, "nouveau-Mot-de-passe-7")
        assert (
            refus(inscription.reinitialiser_par_lien, jeton, "encore-un-Autre-8").code
            == "link_invalid"
        )

    def test_lien_falsifie_ou_d_un_autre_usage(self):
        u, _ = inscrire()
        assert (
            refus(inscription.reinitialiser_par_lien, "nimporte:quoi", FORT).code == "link_invalid"
        )
        jeton_email = identifiants.creer_jeton(u, "email", a="a@b.bj")
        assert refus(inscription.reinitialiser_par_lien, jeton_email, FORT).code == "link_invalid"

    def test_lien_de_l_equipe_journalise(self):
        u, _ = inscrire()
        url = administration.lien_reinitialisation(acteur=AdminFactory(), cible=u)
        inscription.reinitialiser_par_lien(jeton_du_lien(url), "nouveau-Mot-de-passe-7")
        assert AuditLog.objects.filter(action="auth.lien_reinitialisation_equipe").exists()
        assert AuditLog.objects.get(action="auth.mot_de_passe_reinitialise").metadata == {
            "porte": "equipe"
        }

    def test_ne_concerne_pas_le_personnel(self):
        personnel = PersonnelFactory()
        assert (
            refus(
                administration.lien_reinitialisation, acteur=AdminFactory(), cible=personnel
            ).statut
            == 403
        )


class TestGerant:
    def test_creation_sans_mot_de_passe_puis_activation(self):
        gerant = administration.creer_gerant(
            acteur=AdminFactory(), telephone="97454545", prenom="Kofi", nom="Gérant", zone="Zongo"
        )
        assert gerant.username is None and not gerant.has_usable_password()
        url = administration.lien_activation(acteur=AdminFactory(), gerant=gerant)
        g, cle = administration.activer_gerant(
            jeton_du_lien(url), nom_utilisateur="kofi.gerant", mot_de_passe=FORT
        )
        assert (
            g.username == "kofi.gerant"
            and g.check_password(FORT)
            and identifiants.cle_correcte(g, cle)
        )
        # usage unique : le mot de passe a changé, le lien ne vaut plus rien
        assert (
            refus(
                administration.activer_gerant,
                jeton_du_lien(url),
                nom_utilisateur="autre",
                mot_de_passe=FORT,
            ).code
            == "link_invalid"
        )
        assert (
            refus(administration.lien_activation, acteur=AdminFactory(), gerant=g).code
            == "already_active"
        )


class TestCompte:
    def test_changer_mot_de_passe_garde_l_appareil_courant(self):
        u = ClientFactory()
        courant, _ = appareils.ouvrir(u, installation_id="a", platform="android")
        autre, _ = appareils.ouvrir(u, installation_id="b", platform="android")
        compte.changer_mot_de_passe(u, MOT_DE_PASSE, FORT, courant.pk)
        assert u.check_password(FORT)
        assert [d.pk for d in appareils.lister(u)] == [courant.pk] and autre.pk

    def test_ancien_mot_de_passe_exige(self):
        assert (
            refus(compte.changer_mot_de_passe, ClientFactory(), "faux", FORT).code
            == "invalid_password"
        )

    def test_nouveau_mot_de_passe_faible(self):
        assert (
            refus(compte.changer_mot_de_passe, ClientFactory(), MOT_DE_PASSE, "123").code
            == "validation_error"
        )

    def test_changer_de_numero_sans_code(self):
        u = ClientFactory(phone_e164=TEL)
        compte.changer_numero(u, MOT_DE_PASSE, "97787878")
        u.refresh_from_db()
        assert u.phone_e164 == "+2290197787878"
        assert AuditLog.objects.filter(action="auth.numero_change").exists()

    def test_changer_de_numero_exige_le_mot_de_passe(self):
        assert (
            refus(compte.changer_numero, ClientFactory(), "faux", "97787878").code
            == "invalid_password"
        )

    def test_email_confirme_par_lien_unique(self, django_capture_on_commit_callbacks):
        u = ClientFactory()
        with django_capture_on_commit_callbacks(execute=True):
            compte.demander_ajout_email(u, "Awa@Exemple.bj")
        assert "/compte/email/confirmer/" in mail.outbox[0].body and mail.outbox[0].to == [
            "awa@exemple.bj"
        ]
        jeton = identifiants.creer_jeton(u, "email", a="awa@exemple.bj")
        compte.confirmer_email(jeton)
        u.refresh_from_db()
        assert u.email == "awa@exemple.bj" and u.email_verified_at
        assert refus(compte.confirmer_email, jeton).code == "link_invalid"  # l'e-mail a changé

    def test_email_deja_pris(self):
        ClientFactory(email="pris@exemple.bj")
        assert (
            refus(compte.demander_ajout_email, ClientFactory(), "PRIS@exemple.bj").code
            == "email_taken"
        )

    def test_profil(self):
        u = ClientFactory()
        compte.modifier_profil(u, prenom=" Aminata ", nom=" Sanni  Bio ")
        assert (u.first_name, u.last_name, u.full_name) == (
            "Aminata",
            "Sanni Bio",
            "Aminata Sanni Bio",
        )
        assert refus(compte.modifier_profil, u, prenom=" ").code == "validation_error"

    def test_preferences(self):
        u = ClientFactory()
        compte.definir_preferences(
            u, {"messages": {"push": False, "apercu": True}, "silence": ["conv-1"]}
        )
        u.refresh_from_db()
        assert u.notif_prefs["messages"] == {"push": False, "apercu": True}
        assert u.notif_prefs["silence"] == ["conv-1"]

    @pytest.mark.parametrize(
        "valeurs",
        [{"securite": {"push": False}}, {"sanction": {"push": False}}, {"inconnue": {}}, {"messages": {"push": "non"}},
         {"messages": {"autre": True}}, {"silence": "x"}, "pas un objet"],
    )  # fmt: skip
    def test_preferences_invalides(self, valeurs):
        assert (
            refus(compte.definir_preferences, ClientFactory(), valeurs).code == "validation_error"
        )


class TestSuppression:
    def test_anonymise_et_deconnecte(self):
        u = ClientFactory(phone_e164=TEL, username="awa.bio", email="awa@exemple.bj")
        appareils.ouvrir(u, installation_id="a", platform="android")
        recus = []
        signals.compte_supprime.connect(
            lambda sender, **kw: recus.append(kw), weak=False, dispatch_uid="t"
        )
        compte.supprimer(u, MOT_DE_PASSE)
        u.refresh_from_db()
        assert u.status == "deleted" and u.full_name == "Compte supprimé" and u.deleted_at
        assert u.phone_e164.startswith("del:") and len(u.phone_e164) <= 16 and u.email is None
        assert u.username.startswith("supprime.") and u.recovery_key_hash is None
        assert not u.has_usable_password() and u.token_version == 1
        assert not Device.objects.filter(user=u).exists()
        assert AuditLog.objects.filter(
            action="compte.supprime", actor=u
        ).exists()  # la trace est conservée
        assert recus and recus[0]["utilisateur_id"] == u.pk
        signals.compte_supprime.disconnect(dispatch_uid="t")

    def test_le_nom_d_utilisateur_est_libere(self):
        u = ClientFactory(username="awa.bio")
        compte.supprimer(u, MOT_DE_PASSE)
        assert ClientFactory(username="awa.bio").pk != u.pk

    def test_mot_de_passe_exige(self):
        u = ClientFactory()
        assert refus(compte.supprimer, u, "faux").code == "invalid_password"
        u.refresh_from_db()
        assert u.status == "active"

    def test_le_personnel_ne_se_supprime_pas_ici(self):
        assert refus(compte.supprimer, PersonnelFactory(), MOT_DE_PASSE).statut == 403

    def test_jetons_invalides_apres_suppression(self):
        u = ClientFactory()
        d, _ = appareils.ouvrir(u, installation_id="a", platform="android")
        acces = jetons.emettre_acces(u, d)
        compte.supprimer(u, MOT_DE_PASSE)
        assert refus(jetons.verifier_acces, acces).code == "invalid_token"


def test_mot_de_passe_hache_avec_argon2(settings):
    settings.PASSWORD_HASHERS = ["django.contrib.auth.hashers.Argon2PasswordHasher"]
    assert mots_de_passe.hacher(FORT).startswith("argon2$argon2id$")
