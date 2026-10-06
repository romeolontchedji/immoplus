#!/usr/bin/env bash
# Exécute une commande localement, ou dans un conteneur Python si Python est absent.
set -euo pipefail
if command -v "$1" >/dev/null 2>&1; then
  exec "$@"
fi
if command -v docker >/dev/null 2>&1; then
  exec docker run --rm -v "$PWD":/w -w /w python:3.12-slim "$@"
fi
echo "✗ « $1 » est introuvable et Docker n'est pas installé : installe Python 3.12 ou Docker (voir docs/guide-installation-pas-a-pas.md)." >&2
exit 1
