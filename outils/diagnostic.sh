#!/usr/bin/env bash
# Diagnostic de l'environnement local : à lancer avant `make up`, et à coller dans une IA en cas de panne.
set -uo pipefail
cd "$(dirname "$0")/.."
echo "== Système"; uname -a; echo "Mémoire :"; (free -h 2>/dev/null || vm_stat 2>/dev/null | head -4) | head -4
echo "== Outils"
for o in git make python3 docker; do
  if command -v "$o" >/dev/null 2>&1; then printf '  ✔ %-8s %s\n' "$o" "$("$o" --version 2>&1 | head -1)"
  else printf '  ✗ %-8s ABSENT\n' "$o"; fi
done
if command -v docker >/dev/null 2>&1; then
  echo "  Docker Compose : $(docker compose version 2>&1 | head -1)"
  docker info >/dev/null 2>&1 && echo "  ✔ le démon Docker répond" || echo "  ✗ le démon Docker ne répond pas (lance Docker Desktop / systemctl start docker)"
fi
echo "== Fichiers"
[ -f .env ] && echo "  ✔ .env présent" || echo "  ✗ .env absent : lance « make env »"
[ "$(git config core.hooksPath 2>/dev/null)" = ".githooks" ] && echo "  ✔ hooks Git installés" || echo "  ✗ hooks absents : lance « make hooks »"
echo "== Ports (8080 : site local)"
for p in 8080; do
  if (exec 3<>"/dev/tcp/127.0.0.1/$p") 2>/dev/null; then echo "  ✗ le port $p est déjà utilisé"; else echo "  ✔ le port $p est libre"; fi
done
echo "== État de la pile"
command -v docker >/dev/null 2>&1 && docker compose -f infra/compose/docker-compose.yml --profile dev ps 2>&1 | head -20
