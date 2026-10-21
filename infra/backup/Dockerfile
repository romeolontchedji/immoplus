# Image du conteneur `backup` : pg_dump (client PostgreSQL 16) + restic pour la copie chiffrée hors du serveur (ADR 0008).
FROM postgres:16-bookworm
RUN apt-get update \
 && apt-get install -y --no-install-recommends restic ca-certificates \
 && rm -rf /var/lib/apt/lists/*
