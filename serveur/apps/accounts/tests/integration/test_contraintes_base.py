"""Contraintes, déclencheurs et droits PostgreSQL des comptes (CDC §9.3 à §9.6, §9.18, §9.23)."""

import json
from contextlib import contextmanager

import pytest
from django.db import DatabaseError, IntegrityError, connection, transaction
from django.utils import timezone

from apps.accounts.models import Device, GerantProfile, User
from apps.accounts.tests.fabriques import (
    AdminFactory,
    ClientFactory,
    DeviceFactory,
    GerantFactory,
    GerantProfileFactory,
    PersonnelFactory,
)
from apps.audit.models import AuditLog

pytestmark = [pytest.mark.integration, pytest.mark.pg, pytest.mark.django_db]


@contextmanager
def en_tant_que(role: str):
    """Endosse un rôle PostgreSQL pour la transaction de test (les droits y sont alors réellement appliqués)."""
    with connection.cursor() as c:
        c.execute(f"SET LOCAL ROLE {role}")
    try:
        yield
    finally:
        with connection.cursor() as c:
            c.execute("RESET ROLE")


def refuse(requete: str, params=None, role: str = "app"):
    """La requête doit être refusée par PostgreSQL pour ce rôle."""
    with (
        en_tant_que(role),
        pytest.raises(DatabaseError),
        transaction.atomic(),
        connection.cursor() as c,
    ):
        c.execute(requete, params or [])


def execute(requete: str, params=None, role: str = "app"):
    with en_tant_que(role), connection.cursor() as c:
        c.execute(requete, params or [])
        return c.rowcount


# --- CHECK et unicités de `users` ---
class TestUsers:
    def test_role_inconnu_refuse(self):
        with pytest.raises(IntegrityError), transaction.atomic():
            User.objects.create(phone_e164="+2290197000001", full_name="X", role="pirate")

    def test_statut_inconnu_refuse(self):
        with pytest.raises(IntegrityError), transaction.atomic():
            User.objects.create(
                phone_e164="+2290197000002", full_name="X", role="client", status="zombie"
            )

    @pytest.mark.parametrize("role", ["client", "gerant"])
    def test_clientele_exige_un_numero(self, role):
        with pytest.raises(IntegrityError), transaction.atomic():
            User.objects.create(full_name="X", role=role)

    @pytest.mark.parametrize("role", ["moderator", "admin"])
    def test_personnel_exige_un_email(self, role):
        with pytest.raises(IntegrityError), transaction.atomic():
            User.objects.create(full_name="X", role=role)

    def test_numero_partage_permis(self):
        ClientFactory(phone_e164="+2290197111111")
        ClientFactory(phone_e164="+2290197111111")  # ADR 0009 : le numéro n'est plus unique

    def test_nom_d_utilisateur_unique(self):
        # Le format n'admet que des minuscules : l'unicité vaut donc sans tenir compte des majuscules.
        ClientFactory(username="awa.bio")
        with pytest.raises(IntegrityError), transaction.atomic():
            ClientFactory(username="awa.bio")

    @pytest.mark.parametrize("nom", ["ab", "Awa.Bio", ".awa", "awa.", "a b c"])
    def test_nom_d_utilisateur_mal_forme_refuse(self, nom):
        with pytest.raises(IntegrityError), transaction.atomic():
            ClientFactory(username=nom)

    def test_un_locataire_a_un_nom_d_utilisateur(self):
        with pytest.raises(IntegrityError), transaction.atomic():
            ClientFactory(username=None)

    def test_un_gerant_peut_attendre_son_activation_sans_nom(self):
        assert GerantFactory(username=None).pk

    def test_email_unique_mais_plusieurs_absents(self):
        ClientFactory()
        ClientFactory()  # deux comptes sans e-mail : l'unicité ne s'applique qu'aux valeurs non nulles
        PersonnelFactory(email="a@immoplus.test")
        with pytest.raises(IntegrityError), transaction.atomic():
            PersonnelFactory(email="a@immoplus.test")

    def test_valeurs_par_defaut_posees_par_la_base(self):
        with connection.cursor() as c:
            c.execute(
                "INSERT INTO users (id, username, phone_e164, password_hash, full_name, role) "
                "VALUES (gen_random_uuid(), 'par.defaut', '+2290197222222', 'x', 'Y', 'client') "
                "RETURNING status, token_version, notif_prefs, created_at IS NOT NULL"
            )
            statut, version, prefs, cree = c.fetchone()
            assert (
                statut,
                version,
                json.loads(prefs) if isinstance(prefs, str) else prefs,
                cree,
            ) == ("active", 0, {}, True)

    def test_le_personnel_a_les_droits_deduits_du_role(self):
        assert AdminFactory().is_superuser and AdminFactory().is_staff
        moderateur = PersonnelFactory()
        assert moderateur.is_staff and not moderateur.is_superuser
        assert not ClientFactory().is_staff

    def test_compte_suspendu_inactif_puis_actif_apres_echeance(self):
        u = ClientFactory(
            status="suspended", suspended_until=timezone.now() + timezone.timedelta(days=1)
        )
        assert not u.is_active
        u.suspended_until = timezone.now() - timezone.timedelta(seconds=1)
        assert u.is_active

    def test_permissions_du_moderateur_limitees(self):
        m = PersonnelFactory()
        assert m.has_perm("moderation.change_report")
        assert not m.has_perm("accounts.change_user")
        assert not m.has_perm("core.change_appsetting")
        assert AdminFactory().has_perm("core.change_appsetting")
        assert not ClientFactory().has_perm("moderation.change_report")


# --- devices ---
class TestDevices:
    def test_une_installation_par_utilisateur(self):
        d = DeviceFactory()
        with pytest.raises(IntegrityError), transaction.atomic():
            DeviceFactory(user=d.user, installation_id=d.installation_id)

    def test_meme_installation_pour_deux_utilisateurs_permise(self):
        d = DeviceFactory()
        DeviceFactory(installation_id=d.installation_id)

    def test_plateforme_inconnue_refusee(self):
        with pytest.raises(IntegrityError), transaction.atomic():
            DeviceFactory(platform="symbian")

    def test_fournisseur_push_inconnu_refuse(self):
        with pytest.raises(IntegrityError), transaction.atomic():
            DeviceFactory(push_provider="pigeon")

    def test_empreinte_de_rafraichissement_unique(self):
        DeviceFactory(refresh_hash="h" * 64)
        with pytest.raises(IntegrityError), transaction.atomic():
            DeviceFactory(refresh_hash="h" * 64)

    def test_plusieurs_appareils_sans_empreinte(self):
        DeviceFactory(refresh_hash=None)
        DeviceFactory(refresh_hash=None)

    def test_suppression_du_compte_supprime_les_appareils(self):
        d = DeviceFactory()
        d.user.delete()
        assert not Device.objects.filter(pk=d.pk).exists()


# --- gerant_profiles ---
class TestGerantProfiles:
    def test_profil_pour_un_gerant(self):
        assert GerantProfileFactory().verification_status == "pending"

    def test_un_locataire_n_a_pas_de_profil(self):
        with pytest.raises(DatabaseError), transaction.atomic():
            GerantProfile.objects.create(user=ClientFactory(), zone="Z", created_by=AdminFactory())

    def test_le_personnel_n_a_pas_de_profil(self):
        with pytest.raises(DatabaseError), transaction.atomic():
            GerantProfile.objects.create(
                user=PersonnelFactory(), zone="Z", created_by=AdminFactory()
            )

    def test_un_seul_profil_par_compte(self):
        p = GerantProfileFactory()
        with pytest.raises(IntegrityError), transaction.atomic():
            GerantProfile.objects.create(user=p.user, zone="Z", created_by=p.created_by)

    def test_un_gerant_avec_profil_ne_change_pas_de_role(self):
        p = GerantProfileFactory()
        with pytest.raises(DatabaseError), transaction.atomic():
            User.objects.filter(pk=p.user_id).update(role="client")

    def test_statut_de_verification_controle(self):
        p = GerantProfileFactory()
        with pytest.raises(IntegrityError), transaction.atomic():
            GerantProfile.complets.filter(pk=p.pk).update(verification_status="douteux")

    def test_type_de_piece_controle(self):
        p = GerantProfileFactory()
        with pytest.raises(IntegrityError), transaction.atomic():
            GerantProfile.complets.filter(pk=p.pk).update(id_doc_type="selfie")

    def test_le_gestionnaire_par_defaut_ne_charge_pas_les_pieces(self):
        GerantProfileFactory()
        p = GerantProfile.objects.get()
        charges = p.get_deferred_fields()
        assert {
            "interview_notes",
            "id_doc_path",
            "extra_doc_path",
            "id_doc_type",
            "docs_retain_until",
        } <= charges


# --- audit_logs : ajout seul ---
class TestAuditLogs:
    def ligne(self, **kw):
        return AuditLog.objects.create(action="test.action", **kw)

    def test_modification_refusee(self):
        entree = self.ligne()
        with pytest.raises(DatabaseError, match="ajout seul"), transaction.atomic():
            AuditLog.objects.filter(pk=entree.pk).update(action="autre")

    def test_suppression_refusee(self):
        entree = self.ligne()
        with pytest.raises(DatabaseError, match="ajout seul"), transaction.atomic():
            AuditLog.objects.filter(pk=entree.pk).delete()

    def test_vidage_refuse(self):
        self.ligne()
        with connection.cursor() as c:
            c.execute("SET CONSTRAINTS ALL IMMEDIATE")
        with (
            pytest.raises(DatabaseError, match="ajout seul"),
            transaction.atomic(),
            connection.cursor() as c,
        ):
            c.execute("TRUNCATE audit_logs")

    def ancienne(self, jours: int, **kw):
        """Une ligne antidatée dès la création (aucune modification : le journal reste en ajout seul)."""
        return self.ligne(created_at=timezone.now() - timezone.timedelta(days=jours), **kw)

    def test_retention_vide_ip_apres_90_jours(self):
        entree = self.ancienne(91, ip="10.0.0.1", user_agent="x")
        assert (
            execute(
                "UPDATE audit_logs SET ip = NULL, user_agent = NULL WHERE id = %s",
                [entree.pk],
                role="retention",
            )
            == 1
        )

    def test_retention_ne_vide_pas_une_ligne_recente(self):
        entree = self.ancienne(10, ip="10.0.0.1")
        refuse(
            "UPDATE audit_logs SET ip = NULL, user_agent = NULL WHERE id = %s",
            [entree.pk],
            role="retention",
        )

    def test_retention_ne_modifie_pas_le_contenu(self):
        entree = self.ancienne(91, ip="10.0.0.1")
        refuse(
            "UPDATE audit_logs SET action = 'falsifie', ip = NULL WHERE id = %s",
            [entree.pk],
            role="retention",
        )

    def test_retention_ne_supprime_qu_apres_24_mois(self):
        recente = self.ancienne(100)
        refuse("DELETE FROM audit_logs WHERE id = %s", [recente.pk], role="retention")
        vieille = self.ancienne(25 * 31)
        assert execute("DELETE FROM audit_logs WHERE id = %s", [vieille.pk], role="retention") == 1

    def test_retention_ne_vide_jamais_la_table(self):
        refuse("TRUNCATE audit_logs", role="retention")


# --- droits du rôle `app` (ce que ferait une faille de web-api) ---
class TestDroitsDuRoleApp:
    def test_peut_creer_un_locataire(self):
        assert (
            execute(
                "INSERT INTO users (id, username, phone_e164, password_hash, full_name, role) "
                "VALUES (gen_random_uuid(), 'role.app', '+2290197444444', 'x', 'Y', 'client')"
            )
            == 1
        )

    @pytest.mark.parametrize("role", ["gerant", "moderator", "admin"])
    def test_ne_peut_pas_creer_un_autre_role(self, role):
        refuse(
            "INSERT INTO users (id, phone_e164, email, password_hash, full_name, role) "
            "VALUES (gen_random_uuid(), '+2290197444445', 'a@b.c', 'x', 'Y', %s)",
            [role],
        )

    def test_ne_peut_pas_changer_un_role(self):
        u = ClientFactory()
        refuse("UPDATE users SET role = 'admin' WHERE id = %s", [u.pk])

    def test_ne_peut_pas_promouvoir_un_gerant_en_admin(self):
        u = GerantFactory()
        refuse("UPDATE users SET role = 'admin' WHERE id = %s", [u.pk])

    def test_modifie_le_courriel_d_un_locataire_jamais_celui_du_personnel(self):
        # ADR 0009 : un locataire ajoute son e-mail depuis son profil ; le personnel reste intouchable.
        assert execute("UPDATE users SET email = 'x@y.z' WHERE id = %s", [ClientFactory().pk]) == 1
        refuse("UPDATE users SET email = 'x@y.z' WHERE id = %s", [AdminFactory().pk])

    def test_ne_peut_pas_modifier_le_personnel(self):
        a = AdminFactory()
        refuse("UPDATE users SET full_name = 'pirate' WHERE id = %s", [a.pk])
        refuse("UPDATE users SET password_hash = 'x' WHERE id = %s", [a.pk])
        refuse("UPDATE users SET token_version = 0 WHERE id = %s", [a.pk])

    def test_ne_peut_pas_supprimer_le_personnel(self):
        a = AdminFactory()
        refuse("DELETE FROM users WHERE id = %s", [a.pk])

    def test_peut_modifier_son_profil(self):
        u = ClientFactory()
        assert (
            execute(
                "UPDATE users SET full_name = 'Nouveau', token_version = token_version + 1 WHERE id = %s",
                [u.pk],
            )
            == 1
        )

    def test_ne_peut_pas_lire_les_pieces_ni_les_notes(self):
        p = GerantProfileFactory()
        for colonne in (
            "interview_notes",
            "id_doc_path",
            "extra_doc_path",
            "id_doc_type",
            "docs_retain_until",
        ):
            refuse(f"SELECT {colonne} FROM gerant_profiles WHERE user_id = %s", [p.pk])

    def test_peut_lire_le_profil_public(self):
        p = GerantProfileFactory()
        assert (
            execute(
                "SELECT zone, verification_status FROM gerant_profiles WHERE user_id = %s", [p.pk]
            )
            == 1
        )

    def test_ne_peut_pas_creer_ni_verifier_un_profil(self):
        p = GerantProfileFactory()
        refuse(
            "UPDATE gerant_profiles SET verification_status = 'verified' WHERE user_id = %s", [p.pk]
        )
        refuse("UPDATE gerant_profiles SET id_doc_path = 'x' WHERE user_id = %s", [p.pk])
        refuse("DELETE FROM gerant_profiles WHERE user_id = %s", [p.pk])

    def test_journal_en_ajout_seul(self):
        assert execute("INSERT INTO audit_logs (action, metadata) VALUES ('t.a', '{}')") == 1
        refuse("UPDATE audit_logs SET action = 'x'")
        refuse("DELETE FROM audit_logs")
        refuse("TRUNCATE audit_logs")

    def test_parametres_en_lecture_seule(self):
        assert execute("SELECT count(*) FROM app_settings") == 1
        refuse("INSERT INTO app_settings (key, value, description) VALUES ('K', '1', 'd')")

    def test_lecture_complete_du_profil_par_l_orm_est_possible_sans_colonnes_reservees(self):
        GerantProfileFactory()
        with en_tant_que("app"):
            assert GerantProfile.objects.get().zone == "Banikanni"


class TestDroitsDuRoleAdminApp:
    def test_peut_creer_un_gerant_et_un_profil(self):
        u = execute(
            "INSERT INTO users (id, phone_e164, password_hash, full_name, role) "
            "VALUES (gen_random_uuid(), '+2290197555555', 'x', 'G', 'gerant')",
            role="admin_app",
        )
        assert u == 1

    def test_peut_changer_un_role(self):
        u = ClientFactory()
        assert (
            execute("UPDATE users SET role = 'gerant' WHERE id = %s", [u.pk], role="admin_app") == 1
        )

    def test_ne_modifie_pas_le_journal(self):
        refuse("UPDATE audit_logs SET action = 'x'", role="admin_app")
        refuse("DELETE FROM audit_logs", role="admin_app")
