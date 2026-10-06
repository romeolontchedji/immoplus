#!/usr/bin/env bash
# Test de fumée : la pile tourne-t-elle et se comporte-t-elle comme prévu ? (`make fumee`)
# Variables : BASE_WWW (défaut http://www.localhost:8080), BASE_ADMIN (défaut http://pilotage.localhost:8080).
set -uo pipefail
WWW="${BASE_WWW:-http://www.localhost:8080}"
ADMIN="${BASE_ADMIN:-http://pilotage.localhost:8080}"
ko=0

verifier() { # verifier <libellé> <code attendu> <url> [curl...]
  local libelle="$1" attendu="$2" url="$3"; shift 3
  local code
  code="$(curl -s -o /dev/null -m 10 -w '%{http_code}' "$@" "$url" || true)"
  if [ "$code" = "$attendu" ]; then echo "  ✔ $libelle ($code)"
  else echo "  ✗ $libelle : attendu $attendu, reçu ${code:-aucun} — voir docs/aide-ia-depannage.md"; ko=1; fi
}

echo "Test de fumée Logeo :"
verifier "vivacité /healthz" 200 "$WWW/healthz"
verifier "disponibilité /readyz (base, Redis, disque)" 200 "$WWW/readyz"
verifier "page d'accueil" 200 "$WWW/"
verifier "CSS empreinté servi par Caddy" 200 "$WWW/$(curl -s -m 10 "$WWW/" | grep -o 'static/css/dist/logeo\.[0-9a-f]*\.css' | head -1)"
verifier "aucune route d'administration sur le site" 404 "$WWW/admin/"
verifier "l'hôte d'administration répond (liste blanche)" 200 "$ADMIN/healthz"
if curl -s -m 10 -D - -o /dev/null "$WWW/healthz" | grep -qi '^content-security-policy:'; then
  echo "  ✔ en-tête Content-Security-Policy présent"
else echo "  ✗ en-tête Content-Security-Policy absent"; ko=1; fi
[ "$ko" -eq 0 ] && echo "✔ Pile en bonne santé." || { echo "✗ Des vérifications ont échoué."; exit 1; }
