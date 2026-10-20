#!/usr/bin/env python3
"""Code de sortie 0 si PostgreSQL répond avec les variables DB_* (sinon 1). Sans dépendance Django."""

import os
import sys

try:
    import psycopg

    with psycopg.connect(
        dbname=os.environ.get("DB_NAME", "immoplus"),
        user=os.environ.get("DB_USER", "app"),
        password=os.environ.get("DB_PASSWORD", "app-dev"),
        host=os.environ.get("DB_HOST", "localhost"),
        port=os.environ.get("DB_PORT", "5432"),
        connect_timeout=3,
    ):
        sys.exit(0)
except Exception:  # noqa: BLE001 - toute erreur de connexion = base indisponible
    sys.exit(1)
