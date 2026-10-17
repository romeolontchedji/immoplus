#!/usr/bin/env bash
# Enchaîne tous les contrôles. Un contrôle dont l'outil manque est « sauté » (jamais compté comme réussi).
# LOGEO_STRICT=1 (intégration continue) : un contrôle sauté fait échouer l'ensemble.
set -uo pipefail
cd "$(dirname "$0")/.."
[ -d .venv/bin ] && PATH="$PWD/.venv/bin:$PATH"
echec=0; saute=0
journal="$(mktemp)"; trap 'rm -f "$journal"' EXIT

etape() { # etape <libellé> <commande...>
  local libelle="$1"; shift
  if "$@" >"$journal" 2>&1; then
    echo "  ✔ $libelle"
  else
    echo "  ✗ $libelle"; sed 's/^/      /' "$journal"; echec=1
  fi
}
optionnelle() { # optionnelle <outil> <libellé> <commande...>
  local outil="$1" libelle="$2"; shift 2
  if command -v "$outil" >/dev/null 2>&1; then etape "$libelle" "$@"
  else echo "  ⏭ $libelle — sauté ($outil absent)"; saute=$((saute + 1)); fi
}
dans_serveur() { ( cd serveur && "$@" ); }

echo "Contrôles Logeo :"
etape "noms et mots interdits" python3 outils/verifier_noms.py
etape "hygiène (secrets, débogage, tailles)" python3 outils/verifier_hygiene.py
etape "nom de la branche courante" python3 outils/verifier_branche.py
optionnelle ruff "ruff check (serveur)" ruff check serveur
optionnelle ruff "ruff check (outils)" ruff check --config outils/ruff.toml outils
optionnelle ruff "ruff format --check" bash -c 'ruff format --check serveur && ruff format --check --config outils/ruff.toml outils'
[ -d serveur/web ] && optionnelle djlint "djlint --check" djlint --check serveur/web
[ -f docs/design/tokens.json ] && etape "jetons de design synchronisés (site et mobile)" python3 outils/construire_tokens.py --verifier
[ -f serveur/web/static/css/tokens.css ] && etape "contrastes WCAG des jetons" python3 outils/contraste.py
[ -d outils/tests ] && etape "tests des outils" python3 -m unittest discover -s outils/tests -q

if [ -f serveur/manage.py ] && command -v python3 >/dev/null && python3 -c "import django" 2>/dev/null; then
  optionnelle lint-imports "import-linter" bash -c 'cd serveur && lint-imports'
  optionnelle bandit "bandit" bandit -q -r serveur/apps serveur/config serveur/web -x "*/tests/*,*/tests"
  etape "makemigrations --check (tous les modèles)" dans_serveur env DJANGO_SETTINGS_MODULE=config.settings.migrer SECRET_KEY=controle python3 manage.py makemigrations --check --dry-run
  etape "OpenAPI valide et à jour" bash -c 'cd serveur && python3 manage.py spectacular --format openapi-json --file /tmp/openapi-courant.json --validate --fail-on-warn && cmp -s /tmp/openapi-courant.json ../docs/api/openapi.json || { echo "docs/api/openapi.json périmé : lance make openapi"; exit 1; }'
  if python3 outils/base_disponible.py; then
    etape "migration-linter (ruptures de schéma)" dans_serveur env DJANGO_SETTINGS_MODULE=config.settings.migrer SECRET_KEY=controle python3 manage.py lintmigrations
    optionnelle pytest "pytest (complet)" dans_serveur python3 -m pytest -q
  else
    echo "  ⏭ pytest avec PostgreSQL — sauté (PostgreSQL injoignable)"; saute=$((saute + 1))
    optionnelle pytest "pytest partiel (sans PostgreSQL)" dans_serveur python3 -m pytest -q -m "not pg"
  fi
else
  echo "  ⏭ contrôles Django — sautés (Django non installé)"; saute=$((saute + 1))
fi

if [ "$echec" -ne 0 ]; then echo "✗ Contrôles en échec."; exit 1; fi
if [ "$saute" -ne 0 ] && [ "${LOGEO_STRICT:-0}" = "1" ]; then echo "✗ $saute contrôle(s) sauté(s) en mode strict."; exit 1; fi
echo "✔ Contrôles réussis ($saute sauté(s))."
