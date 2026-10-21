#!/usr/bin/env bash
# Redémarre les conteneurs Immo+ figés (sonde de santé « unhealthy »). Docker relance un conteneur qui s'arrête,
# mais pas un conteneur qui tourne sans répondre : ce script comble ce manque.
#
# Lancé chaque minute par systemd (immoplus-autoguerison.timer, installé par bootstrap.sh). Exécution sur le serveur,
# jamais dans un conteneur : aucun conteneur n'a besoin d'accéder au moteur Docker.
#
# Garde-fou : au plus MAX_PAR_HEURE redémarrages par conteneur et par heure ; au-delà, on arrête d'insister (une
# vraie panne demande un humain) et on l'écrit dans le journal système : `journalctl -t immoplus-autoguerison`.
set -euo pipefail

PROJET="${PROJET:-immoplus}"
MAX_PAR_HEURE="${MAX_PAR_HEURE:-3}"
ETAT="${ETAT:-/var/lib/immoplus-autoguerison}"
mkdir -p "$ETAT"

journal() { logger -t immoplus-autoguerison "$*"; echo "$*"; }

maintenant=$(date +%s)
for conteneur in $(docker ps --filter "label=com.docker.compose.project=$PROJET" --filter "health=unhealthy" --format '{{.Names}}'); do
  trace="$ETAT/$conteneur"
  touch "$trace"
  # Ne garde que les redémarrages de la dernière heure.
  awk -v limite=$((maintenant - 3600)) '$1 > limite' "$trace" > "$trace.tmp" && mv "$trace.tmp" "$trace"
  if [ "$(wc -l < "$trace")" -ge "$MAX_PAR_HEURE" ]; then
    journal "ALERTE : $conteneur reste malade après $MAX_PAR_HEURE redémarrages en une heure : intervention nécessaire."
    continue
  fi
  journal "$conteneur ne répond plus (unhealthy) : redémarrage."
  docker restart --time 30 "$conteneur" >/dev/null
  echo "$maintenant" >> "$trace"
done
