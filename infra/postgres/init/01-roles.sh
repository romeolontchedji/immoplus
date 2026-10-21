#!/bin/bash
# Création des trois rôles PostgreSQL et des extensions (exécuté une fois par l'image postgres).
# Les droits par colonne (users.role, tables du personnel, 2FA, audit_logs) sont posés par les
# migrations de la phase 1, quand les tables existent ; ce script prépare les rôles et le schéma.
set -euo pipefail

: "${POSTGRES_DB:=immoplus}"
: "${APP_DB_PASSWORD:?APP_DB_PASSWORD manquant}"
: "${ADMIN_DB_PASSWORD:?ADMIN_DB_PASSWORD manquant}"
: "${MIGRATE_DB_PASSWORD:?MIGRATE_DB_PASSWORD manquant}"

psql -v ON_ERROR_STOP=1 --username "${POSTGRES_USER:-postgres}" --dbname "$POSTGRES_DB" \
  -v base="$POSTGRES_DB" -v app_pw="$APP_DB_PASSWORD" -v admin_pw="$ADMIN_DB_PASSWORD" -v migrate_pw="$MIGRATE_DB_PASSWORD" <<'SQL'
CREATE EXTENSION IF NOT EXISTS pg_trgm;
CREATE EXTENSION IF NOT EXISTS unaccent;

-- `migrate` possède le schéma et exécute le DDL ; `app` et `admin_app` n'ont que des droits DML.
CREATE ROLE migrate LOGIN PASSWORD :'migrate_pw';
CREATE ROLE app LOGIN PASSWORD :'app_pw' NOSUPERUSER NOCREATEDB NOCREATEROLE;
CREATE ROLE admin_app LOGIN PASSWORD :'admin_pw' NOSUPERUSER NOCREATEDB NOCREATEROLE;
-- Rôle de rétention (purges d'audit_logs, CDC §9.18) : sans connexion, endossé par migrate via SET ROLE.
CREATE ROLE retention NOLOGIN;
GRANT retention TO migrate;

REVOKE ALL ON DATABASE :"base" FROM PUBLIC;
GRANT CONNECT ON DATABASE :"base" TO migrate, app, admin_app;

REVOKE CREATE ON SCHEMA public FROM PUBLIC;
ALTER SCHEMA public OWNER TO migrate;
GRANT USAGE ON SCHEMA public TO app, admin_app;

-- Droits par défaut sur ce que `migrate` créera : DML seulement.
ALTER DEFAULT PRIVILEGES FOR ROLE migrate IN SCHEMA public
  GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO app, admin_app;
ALTER DEFAULT PRIVILEGES FOR ROLE migrate IN SCHEMA public
  GRANT USAGE, SELECT ON SEQUENCES TO app, admin_app;

ALTER ROLE app SET statement_timeout = '5s';
ALTER ROLE admin_app SET statement_timeout = '30s';
SQL
