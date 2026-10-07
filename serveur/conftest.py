"""Fixtures racine : CSS construit, clients de test. Complétées à chaque phase (CDC §12 bis)."""

import sys
from pathlib import Path

import pytest

RACINE_DEPOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RACINE_DEPOT / "outils"))


@pytest.fixture(scope="session", autouse=True)
def css_construit():
    """Le site exige le CSS empreinté : on le construit une fois par session de test."""
    import construire_css

    construire_css.construire()
    from web.templatetags import logeo

    logeo._manifeste.cache_clear()


# --- Rôles PostgreSQL de production, recréés pour les tests de droits (CDC §8.2) ---
@pytest.fixture(scope="session")
def roles_postgres():
    """Crée `app`, `admin_app`, `retention` et leurs droits par défaut avant la création de la base de test.

    Les droits par défaut sont posés sur `template1` : la base de test en est copiée, ce qui reproduit
    `ALTER DEFAULT PRIVILEGES` du script d'initialisation de production.
    """
    import os

    import psycopg

    params = {
        "user": os.environ.get("DB_USER", "app"),
        "password": os.environ.get("DB_PASSWORD", "app-dev"),
        "host": os.environ.get("DB_HOST", "localhost"),
        "port": os.environ.get("DB_PORT", "5432"),
    }
    with psycopg.connect(dbname="postgres", autocommit=True, **params) as conn:
        for role, extra in (("app", "LOGIN"), ("admin_app", "LOGIN"), ("retention", "NOLOGIN")):
            conn.execute(
                f"DO $$ BEGIN IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = '{role}') "
                f"THEN CREATE ROLE {role} {extra}; END IF; END $$"
            )
    with psycopg.connect(dbname="template1", autocommit=True, **params) as conn:
        utilisateur = params["user"]
        conn.execute(
            f"ALTER DEFAULT PRIVILEGES FOR ROLE {utilisateur} IN SCHEMA public "
            "GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO app, admin_app"
        )
        conn.execute(
            f"ALTER DEFAULT PRIVILEGES FOR ROLE {utilisateur} IN SCHEMA public "
            "GRANT USAGE, SELECT ON SEQUENCES TO app, admin_app"
        )


@pytest.fixture(scope="session")
def django_db_setup(roles_postgres, django_db_setup):
    """La base de test est créée après les rôles : les migrations posent alors les droits."""
