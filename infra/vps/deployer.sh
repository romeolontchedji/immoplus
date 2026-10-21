#!/usr/bin/env bash
# Met Immo+ à jour (ou le démarre la première fois) sur le serveur. À lancer depuis la racine du dépôt :
#   bash infra/vps/deployer.sh            # VPS partagé (Caddy central en façade, cas du VPS rmeolab)
#   MODE=dedie bash infra/vps/deployer.sh # serveur dédié : notre Caddy prend lui-même les ports 80 et 443
#
# Étapes : code à jour (avance rapide seulement), image reconstruite, pile démarrée. Le service `migrer` applique les
# migrations et rassemble les fichiers statiques avant que les processus web ne démarrent. Rien n'est supprimé :
# ni volume, ni donnée. Jamais `down -v`.
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"
MODE="${MODE:-partage}"
FICHIERS=(-f infra/compose/docker-compose.yml -f infra/compose/docker-compose.prod.yml)
if [ "$MODE" = "partage" ]; then
  FICHIERS+=(-f infra/compose/docker-compose.vps-partage.yml)
  docker network inspect web_proxy >/dev/null 2>&1 || {
    echo "Le réseau web_proxy n'existe pas : le Caddy central est-il installé ? (docker network create web_proxy)" >&2
    exit 1
  }
fi
COMPOSE=(docker compose --env-file .env "${FICHIERS[@]}" --profile prod)

[ -f .env ] || { echo "Fichier .env absent : lance d'abord python3 outils/creer_env.py (guide, étape 5)." >&2; exit 1; }

echo "==> Code"
git pull --ff-only

echo "==> Image et démarrage"
"${COMPOSE[@]}" up -d --build --remove-orphans

echo "==> État"
sleep 20
"${COMPOSE[@]}" ps --format 'table {{.Service}}\t{{.Status}}'
echo
echo "Journaux en direct : ${COMPOSE[*]} logs -f web-api"
