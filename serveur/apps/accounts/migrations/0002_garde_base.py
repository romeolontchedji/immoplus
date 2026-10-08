"""Déclencheurs et droits PostgreSQL des comptes (CDC §5.1, §9.18, §9.23, §8.2).

- `users` : le rôle `app` ne crée que des locataires, ne change jamais un rôle, ne touche jamais au personnel.
- `gerant_profiles` : réservé aux comptes de rôle gérant ; pièces et notes illisibles pour `app`.
- `audit_logs` : ajout seul ; seul le rôle `retention` peut vider ip/user_agent (90 j) ou supprimer (24 mois).
- Les droits ne sont posés que si les rôles `app` et `admin_app` existent (ils n'existent pas en test).
"""

from django.db import migrations

CREER_FONCTIONS = r"""
CREATE OR REPLACE FUNCTION users_garde_role() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  IF current_user = 'app' THEN
    IF TG_OP = 'INSERT' AND NEW.role <> 'client' THEN
      RAISE EXCEPTION 'le rôle app ne peut créer que des locataires' USING ERRCODE = '42501';
    ELSIF TG_OP = 'UPDATE' AND (OLD.role IN ('moderator', 'admin') OR NEW.role <> OLD.role) THEN
      RAISE EXCEPTION 'le rôle app ne peut ni modifier le personnel ni changer un rôle' USING ERRCODE = '42501';
    ELSIF TG_OP = 'DELETE' AND OLD.role IN ('moderator', 'admin') THEN
      RAISE EXCEPTION 'le rôle app ne peut pas supprimer le personnel' USING ERRCODE = '42501';
    END IF;
  END IF;
  IF TG_OP = 'UPDATE' AND NEW.role <> 'gerant'
     AND EXISTS (SELECT 1 FROM gerant_profiles WHERE user_id = NEW.id) THEN
    RAISE EXCEPTION 'un compte qui a un profil de gérant doit rester gérant' USING ERRCODE = '23514';
  END IF;
  IF TG_OP = 'DELETE' THEN RETURN OLD; END IF;
  RETURN NEW;
END $$;

CREATE TRIGGER users_garde_role BEFORE INSERT OR UPDATE OR DELETE ON users
  FOR EACH ROW EXECUTE FUNCTION users_garde_role();

CREATE OR REPLACE FUNCTION gerant_profiles_garde() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  IF (SELECT role FROM users WHERE id = NEW.user_id) IS DISTINCT FROM 'gerant' THEN
    RAISE EXCEPTION 'seul un compte de rôle gérant peut avoir un profil de gérant' USING ERRCODE = '23514';
  END IF;
  RETURN NEW;
END $$;

CREATE TRIGGER gerant_profiles_garde BEFORE INSERT OR UPDATE OF user_id ON gerant_profiles
  FOR EACH ROW EXECUTE FUNCTION gerant_profiles_garde();

CREATE OR REPLACE FUNCTION audit_logs_immuable() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  IF current_user = 'retention' THEN
    IF TG_OP = 'UPDATE' THEN
      IF OLD.created_at < now() - interval '90 days'
         AND NEW.ip IS NULL AND NEW.user_agent IS NULL
         AND (to_jsonb(NEW) - 'ip' - 'user_agent') = (to_jsonb(OLD) - 'ip' - 'user_agent') THEN
        RETURN NEW;
      END IF;
    ELSIF TG_OP = 'DELETE' THEN
      IF OLD.created_at < now() - interval '24 months' THEN RETURN OLD; END IF;
    END IF;
  END IF;
  RAISE EXCEPTION 'audit_logs est en ajout seul' USING ERRCODE = '42501';
END $$;

CREATE TRIGGER audit_logs_pas_de_modification BEFORE UPDATE OR DELETE ON audit_logs
  FOR EACH ROW EXECUTE FUNCTION audit_logs_immuable();
CREATE TRIGGER audit_logs_pas_de_vidage BEFORE TRUNCATE ON audit_logs
  FOR EACH STATEMENT EXECUTE FUNCTION audit_logs_immuable();
"""

SUPPRIMER_FONCTIONS = """
DROP TRIGGER IF EXISTS audit_logs_pas_de_vidage ON audit_logs;
DROP TRIGGER IF EXISTS audit_logs_pas_de_modification ON audit_logs;
DROP FUNCTION IF EXISTS audit_logs_immuable();
DROP TRIGGER IF EXISTS gerant_profiles_garde ON gerant_profiles;
DROP FUNCTION IF EXISTS gerant_profiles_garde();
DROP TRIGGER IF EXISTS users_garde_role ON users;
DROP FUNCTION IF EXISTS users_garde_role();
"""

DROITS = r"""
DO $droits$
BEGIN
  IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'app') THEN
    -- users : pas de modification du rôle, du courriel ni de l'identifiant par le site et l'API.
    REVOKE UPDATE ON users FROM app;
    GRANT UPDATE (phone_e164, phone_verified_at, password_hash, full_name, status, suspended_until,
                  avatar_path, token_version, terms_version, terms_accepted_at, notif_prefs,
                  last_seen_at, deleted_at, updated_at) ON users TO app;
    -- gerant_profiles : ni pièces d'identité, ni notes d'entretien, ni création.
    REVOKE ALL ON gerant_profiles FROM app;
    GRANT SELECT (user_id, display_name, zone, verification_status, verified_at, verified_by,
                  response_rate_30d, median_response_min, created_by, created_at, updated_at)
      ON gerant_profiles TO app;
    GRANT UPDATE (display_name, zone, response_rate_30d, median_response_min, updated_at)
      ON gerant_profiles TO app;
    -- audit_logs : ajout et lecture seulement.
    REVOKE ALL ON audit_logs FROM app;
    GRANT SELECT, INSERT ON audit_logs TO app;
    GRANT USAGE, SELECT ON SEQUENCE audit_logs_id_seq TO app;
    -- app_settings : lecture seule (modifiée depuis l'administration).
    REVOKE INSERT, UPDATE, DELETE ON app_settings FROM app;
  END IF;
  IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'retention') THEN
    -- Le déclencheur limite ensuite ces droits : vider ip/user_agent après 90 jours, supprimer après 24 mois.
    GRANT SELECT, DELETE ON audit_logs TO retention;
    GRANT UPDATE (ip, user_agent) ON audit_logs TO retention;
  END IF;
  IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'admin_app') THEN
    REVOKE ALL ON audit_logs FROM admin_app;
    GRANT SELECT, INSERT ON audit_logs TO admin_app;
    GRANT USAGE, SELECT ON SEQUENCE audit_logs_id_seq TO admin_app;
  END IF;
END
$droits$;
"""

ANNULER_DROITS = r"""
DO $droits$
BEGIN
  IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'app') THEN
    GRANT SELECT, INSERT, UPDATE, DELETE ON users, gerant_profiles, audit_logs, app_settings TO app;
  END IF;
  IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'admin_app') THEN
    GRANT SELECT, INSERT, UPDATE, DELETE ON audit_logs TO admin_app;
  END IF;
END
$droits$;
"""


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0001_initial"),
        ("audit", "0001_initial"),
        ("core", "0001_initial"),
    ]
    operations = [
        migrations.RunSQL(CREER_FONCTIONS, reverse_sql=SUPPRIMER_FONCTIONS),
        migrations.RunSQL(DROITS, reverse_sql=ANNULER_DROITS),
    ]
