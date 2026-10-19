#!/bin/bash
# Sauvegarde nocturne (ADR 0008) :
#   1. base de données : pg_dump compressé dans le volume `backups`, 14 conservées ;
#   2. copie chiffrée hors du serveur avec restic (base + médias), si RESTIC_REPOSITORY est renseigné.
# Lancement manuel : `bash /scripts/boucle.sh une-fois`.
set -euo pipefail

DESTINATION="${SAUVEGARDE_DESTINATION:-/backups}"
INTERVALLE="${SAUVEGARDE_INTERVALLE_S:-86400}"
CONSERVER="${SAUVEGARDE_CONSERVER:-14}"

sauvegarder_base() {
  local fichier
  fichier="$DESTINATION/logeo-$(date -u +%Y%m%dT%H%M%SZ).sql.gz"
  # Vérifications explicites : appelée derrière `||`, la fonction ne s'arrête pas d'elle-même sur une erreur
  # (un pg_dump en échec donnait un fichier vide considéré comme une sauvegarde).
  if ! pg_dump --format=plain --no-owner "$PGDATABASE" | gzip -9 > "$fichier.tmp"; then
    rm -f "$fichier.tmp"
    echo "ÉCHEC de pg_dump : aucune sauvegarde écrite" >&2
    return 1
  fi
  if ! gzip -dc "$fichier.tmp" | tail -n 5 | grep -q "PostgreSQL database dump complete"; then
    rm -f "$fichier.tmp"
    echo "ÉCHEC : sauvegarde incomplète (fin de fichier absente), fichier supprimé" >&2
    return 1
  fi
  mv "$fichier.tmp" "$fichier"
  echo "sauvegarde de la base écrite : $fichier"
  # shellcheck disable=SC2012
  ls -1t "$DESTINATION"/logeo-*.sql.gz | tail -n +"$((CONSERVER + 1))" | xargs -r rm -f --
}

copier_hors_serveur() {
  if [ -z "${RESTIC_REPOSITORY:-}" ]; then
    echo "copie hors serveur NON CONFIGURÉE (RESTIC_REPOSITORY vide) : les sauvegardes restent sur ce serveur" >&2
    return 0
  fi
  : "${RESTIC_PASSWORD:?RESTIC_PASSWORD manquant : impossible de chiffrer la copie}"
  # Premier passage : crée le dépôt chiffré s'il n'existe pas encore.
  restic snapshots >/dev/null 2>&1 || restic init
  restic backup --tag logeo --host logeo \
    "$DESTINATION" /var/lib/logeo/media_public /var/lib/logeo/media_private
  restic forget --tag logeo --keep-daily 14 --keep-weekly 8 --prune
  echo "copie chiffrée hors serveur terminée ($(restic snapshots --tag logeo --json | grep -o '"short_id"' | wc -l) instantanés conservés)"
}

passe() {
  sauvegarder_base
  copier_hors_serveur || echo "ÉCHEC de la copie hors serveur" >&2
}

if [ "${1:-}" = "une-fois" ]; then passe; exit 0; fi
while true; do
  passe || echo "ÉCHEC de la sauvegarde de la base" >&2
  sleep "$INTERVALLE"
done
