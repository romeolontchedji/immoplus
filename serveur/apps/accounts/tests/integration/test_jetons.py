"""Jetons d'accès JWT et rotation du jeton de rafraîchissement (CDC §5.2)."""

import jwt
import pytest
import time_machine
from django.conf import settings
from django.core.cache import cache
from django.utils import timezone

from apps.accounts.models import Device
from apps.accounts.services import appareils, jetons
from apps.accounts.tests.fabriques import ClientFactory, GerantFactory
from apps.audit.models import AuditLog
from apps.core import redis_file
from apps.core.errors import ErreurMetier

pytestmark = [pytest.mark.integration, pytest.mark.pg, pytest.mark.django_db]


@pytest.fixture
def session():
    """Un locataire connecté sur une installation : (utilisateur, appareil, refresh, accès)."""
    utilisateur = ClientFactory()
    appareil, refresh = appareils.ouvrir(utilisateur, installation_id="inst-1", platform="android")
    return utilisateur, appareil, refresh, jetons.emettre_acces(utilisateur, appareil)


def code_erreur(fonction, *args, **kwargs):
    with pytest.raises(ErreurMetier) as e:
        fonction(*args, **kwargs)
    return e.value.code


def decoder_sans_verifier(jeton):
    return jwt.decode(jeton, options={"verify_signature": False})


class TestAcces:
    def test_aller_retour(self, session):
        utilisateur, appareil, _, acces = session
        identite = jetons.verifier_acces(acces)
        assert (identite.utilisateur_id, identite.appareil_id, identite.role) == (
            str(utilisateur.pk), str(appareil.pk), "client"
        )  # fmt: skip

    def test_contenu_du_jeton(self, session):
        utilisateur, appareil, _, acces = session
        charge = decoder_sans_verifier(acces)
        assert charge["aud"] == "client" and charge["sub"] == str(utilisateur.pk)
        assert charge["did"] == str(appareil.pk) and charge["ver"] == 0
        assert charge["exp"] - charge["iat"] == 900  # 15 minutes
        assert jwt.get_unverified_header(acces)["alg"] == "HS256"

    def test_audience_gerant(self):
        g = GerantFactory()
        d, _ = appareils.ouvrir(g, installation_id="i", platform="ios")
        assert decoder_sans_verifier(jetons.emettre_acces(g, d))["aud"] == "gerant"

    def test_expire_apres_quinze_minutes(self, session):
        _, _, _, acces = session
        with time_machine.travel(timezone.now() + timezone.timedelta(minutes=14), tick=False):
            jetons.verifier_acces(acces)
        with time_machine.travel(timezone.now() + timezone.timedelta(minutes=16), tick=False):
            assert code_erreur(jetons.verifier_acces, acces) == "invalid_token"

    def test_signature_falsifiee(self, session):
        _, _, _, acces = session
        entete, charge, _ = acces.split(".")
        assert code_erreur(jetons.verifier_acces, f"{entete}.{charge}.AAAA") == "invalid_token"

    def test_cle_differente(self, session):
        utilisateur, appareil, _, acces = session
        charge = decoder_sans_verifier(acces)
        faux = jwt.encode(
            charge, "autre-cle-de-signature-tres-longue-0123456789", algorithm="HS256"
        )
        assert code_erreur(jetons.verifier_acces, faux) == "invalid_token"

    def test_jeton_signe_avec_la_cle_de_l_administration_refuse(self, session):
        _, _, _, acces = session
        faux = jwt.encode(decoder_sans_verifier(acces), settings.SECRET_KEY, algorithm="HS256")
        assert code_erreur(jetons.verifier_acces, faux) == "invalid_token"

    def test_algorithme_none_refuse(self, session):
        _, _, _, acces = session
        faux = jwt.encode(decoder_sans_verifier(acces), key=None, algorithm="none")
        assert code_erreur(jetons.verifier_acces, faux) == "invalid_token"

    def test_autre_algorithme_refuse(self, session):
        _, _, _, acces = session
        faux = jwt.encode(
            decoder_sans_verifier(acces), settings.JWT_SIGNING_KEY * 3, algorithm="HS512"
        )
        assert code_erreur(jetons.verifier_acces, faux) == "invalid_token"

    @pytest.mark.parametrize("manquant", ["aud", "did", "ver", "sub", "exp", "iss", "iat"])
    def test_champ_obligatoire_manquant(self, session, manquant):
        _, _, _, acces = session
        charge = decoder_sans_verifier(acces)
        del charge[manquant]
        faux = jwt.encode(charge, settings.JWT_SIGNING_KEY, algorithm="HS256")
        assert code_erreur(jetons.verifier_acces, faux) == "invalid_token"

    def test_audience_inconnue(self, session):
        _, _, _, acces = session
        charge = {**decoder_sans_verifier(acces), "aud": "admin"}
        faux = jwt.encode(charge, settings.JWT_SIGNING_KEY, algorithm="HS256")
        assert code_erreur(jetons.verifier_acces, faux) == "invalid_token"

    def test_audience_differente_du_role_actuel(self, session):
        utilisateur, _, _, acces = session
        type(utilisateur).objects.filter(pk=utilisateur.pk).update(role="gerant")
        jetons.invalider_utilisateur(utilisateur.pk)
        assert code_erreur(jetons.verifier_acces, acces) == "wrong_audience"

    def test_utilisateur_inconnu(self, session):
        utilisateur, _, _, acces = session
        utilisateur.delete()
        cache.clear()
        assert code_erreur(jetons.verifier_acces, acces) == "invalid_token"

    @pytest.mark.parametrize("mauvais", ["", "abc", "a.b.c", "Bearer x"])
    def test_jetons_illisibles(self, mauvais):
        assert code_erreur(jetons.verifier_acces, mauvais) == "invalid_token"


class TestRevocation:
    def test_token_version_incrementee_revoque_tous_les_jetons(self, session):
        utilisateur, _, _, acces = session
        utilisateur.token_version += 1
        utilisateur.save()
        jetons.invalider_utilisateur(utilisateur.pk)
        assert code_erreur(jetons.verifier_acces, acces) == "invalid_token"

    def test_appareil_revoque(self, session):
        _, appareil, _, acces = session
        jetons.revoquer_appareil(appareil)
        assert code_erreur(jetons.verifier_acces, acces) == "invalid_token"

    def test_la_revocation_survit_a_la_perte_du_cache(self, session):
        _, appareil, _, acces = session
        jetons.revoquer_appareil(appareil)
        cache.clear()
        assert code_erreur(jetons.verifier_acces, acces) == "invalid_token"

    def test_token_version_relue_en_base_si_le_cache_est_vide(self, session):
        utilisateur, _, _, acces = session
        type(utilisateur).objects.filter(pk=utilisateur.pk).update(token_version=5)
        cache.clear()
        assert code_erreur(jetons.verifier_acces, acces) == "invalid_token"

    def test_compte_suspendu(self, session):
        utilisateur, _, _, acces = session
        type(utilisateur).objects.filter(pk=utilisateur.pk).update(
            status="suspended", suspended_until=timezone.now() + timezone.timedelta(days=1)
        )
        jetons.invalider_utilisateur(utilisateur.pk)
        assert code_erreur(jetons.verifier_acces, acces) == "account_suspended"

    def test_les_controles_utilisent_le_cache(self, session, django_assert_num_queries):
        _, _, _, acces = session
        jetons.verifier_acces(acces)
        with django_assert_num_queries(0):
            jetons.verifier_acces(acces)


class TestRotation:
    def test_echange_donne_une_nouvelle_paire(self, session):
        utilisateur, appareil, refresh, acces = session
        paire = jetons.echanger_refresh(refresh, "inst-1", "41.0.0.9")
        assert paire.refresh != refresh and paire.expire_dans_s == 900
        jetons.verifier_acces(paire.acces)
        appareil.refresh_from_db()
        assert appareil.refresh_hash == jetons.empreinte(paire.refresh)
        assert appareil.prev_refresh_hash == jetons.empreinte(refresh)
        assert appareil.last_ip == "41.0.0.9"

    def test_le_jeton_en_base_n_est_jamais_en_clair(self, session):
        _, appareil, refresh, _ = session
        assert appareil.refresh_hash != refresh and len(appareil.refresh_hash) == 64

    def test_chaine_de_rotations(self, session):
        _, _, refresh, _ = session
        for _ in range(5):
            refresh = jetons.echanger_refresh(refresh, "inst-1").refresh

    def test_rejeu_dans_la_grace_renvoie_la_meme_paire_sans_revoquer(self, session):
        _, appareil, refresh, _ = session
        premiere = jetons.echanger_refresh(refresh, "inst-1")
        rejeu = jetons.echanger_refresh(refresh, "inst-1")  # réponse perdue : le client réessaie
        assert rejeu.refresh == premiere.refresh
        jetons.verifier_acces(rejeu.acces)
        appareil.refresh_from_db()
        assert appareil.revoked_at is None
        jetons.echanger_refresh(premiere.refresh, "inst-1")  # la nouvelle paire reste utilisable

    def test_rejeu_apres_la_grace_revoque_l_appareil(self, session):
        _, appareil, refresh, _ = session
        nouvelle = jetons.echanger_refresh(refresh, "inst-1")
        Device.objects.filter(pk=appareil.pk).update(
            rotated_at=timezone.now() - timezone.timedelta(seconds=61)
        )
        assert code_erreur(jetons.echanger_refresh, refresh, "inst-1") == "invalid_token"
        appareil.refresh_from_db()
        assert appareil.revoked_at is not None and appareil.refresh_hash is None
        # le voleur comme le propriétaire perdent l'accès : reconnexion nécessaire
        assert code_erreur(jetons.echanger_refresh, nouvelle.refresh, "inst-1") == "invalid_token"
        assert code_erreur(jetons.verifier_acces, nouvelle.acces) == "invalid_token"
        assert AuditLog.objects.filter(
            action="auth.appareil_revoque", metadata__raison="refresh_reutilise"
        ).exists()

    def test_grace_expiree_cote_redis_refuse_sans_revoquer(self, session):
        _, appareil, refresh, _ = session
        jetons.echanger_refresh(refresh, "inst-1")
        redis_file.client().flushall()
        assert code_erreur(jetons.echanger_refresh, refresh, "inst-1") == "invalid_token"
        appareil.refresh_from_db()
        assert appareil.revoked_at is None

    def test_la_grace_n_expose_pas_le_jeton_en_clair_dans_redis(self, session):
        _, _, refresh, _ = session
        nouvelle = jetons.echanger_refresh(refresh, "inst-1")
        for cle in redis_file.client().keys("refresh:grace:*"):
            assert nouvelle.refresh not in redis_file.client().get(cle)

    def test_installation_differente_refusee(self, session):
        _, appareil, refresh, _ = session
        assert (
            code_erreur(jetons.echanger_refresh, refresh, "autre-installation") == "invalid_token"
        )
        appareil.refresh_from_db()
        assert appareil.refresh_hash == jetons.empreinte(refresh)  # rien n'a changé

    def test_jeton_inconnu(self, session):
        assert code_erreur(jetons.echanger_refresh, "inconnu", "inst-1") == "invalid_token"

    @pytest.mark.parametrize("mauvais", ["", None, "x" * 500])
    def test_jetons_de_rafraichissement_illisibles(self, mauvais):
        assert code_erreur(jetons.echanger_refresh, mauvais, "inst-1") == "invalid_token"

    def test_refresh_expire(self, session):
        _, appareil, refresh, _ = session
        Device.objects.filter(pk=appareil.pk).update(
            refresh_expires_at=timezone.now() - timezone.timedelta(seconds=1)
        )
        assert code_erreur(jetons.echanger_refresh, refresh, "inst-1") == "invalid_token"

    def test_refresh_valable_trente_jours(self, session):
        _, appareil, refresh, _ = session
        jetons.echanger_refresh(refresh, "inst-1")
        appareil.refresh_from_db()
        assert 29 <= (appareil.refresh_expires_at - timezone.now()).days <= 30

    def test_appareil_revoque_ne_peut_plus_echanger(self, session):
        _, appareil, refresh, _ = session
        jetons.revoquer_appareil(appareil)
        assert code_erreur(jetons.echanger_refresh, refresh, "inst-1") == "invalid_token"

    def test_compte_suspendu_ne_peut_plus_echanger(self, session):
        utilisateur, _, refresh, _ = session
        type(utilisateur).objects.filter(pk=utilisateur.pk).update(status="banned")
        assert code_erreur(jetons.echanger_refresh, refresh, "inst-1") == "invalid_token"
