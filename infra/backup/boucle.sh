#!/bin/bash
# Sauvegarde logique quotidienne de PostgreSQL (pg_dump compressé), avec rotation.
# Phase 0 : base seule. Archivage WAL, restic pour les médias et restauration : phase 9 (docs/exploitation.md).
set -euo pipefail

DESTINATION="${SAUVEGARDE_DESTINATION:-/backups}"
INTERVALLE="${SAUVEGARDE_INTERVALLE_S:-86400}"
CONSERVER="${SAUVEGARDE_CONSERVER:-14}"

sauvegarder() {
  local fichier
  fichier="$DESTINATION/logeo-$(date -u +%Y%m%dT%H%M%SZ).sql.gz"
  pg_dump --format=plain --no-owner "$PGDATABASE" | gzip -9 > "$fichier.tmp"
  mv "$fichier.tmp" "$fichier"
  echo "sauvegarde écrite : $fichier"
  # shellcheck disable=SC2012
  ls -1t "$DESTINATION"/logeo-*.sql.gz | tail -n +"$((CONSERVER + 1))" | xargs -r rm -f --
}

if [ "${1:-}" = "une-fois" ]; then sauvegarder; exit 0; fi
while true; do
  sauvegarder || echo "ÉCHEC de la sauvegarde" >&2
  sleep "$INTERVALLE"
done
