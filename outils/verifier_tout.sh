#!/usr/bin/env bash
# Enchaîne tous les contrôles. Un contrôle dont l'outil manque est « sauté » (jamais compté comme réussi).
# LOGEO_STRICT=1 (intégration continue) : un contrôle sauté fait échouer l'ensemble.
set -uo pipefail
cd "$(dirname "$0")/.."
echec=0; saute=0
etape() { # etape <libellé> <commande...>
  local libelle="$1"; shift
  if "$@" >/tmp/logeo-etape.log 2>&1; then
    echo "  ✔ $libelle"
  else
    echo "  ✗ $libelle"; sed 's/^/      /' /tmp/logeo-etape.log; echec=1
  fi
}
optionnelle() { # optionnelle <outil> <libellé> <commande...>
  local outil="$1" libelle="$2"; shift 2
  if command -v "$outil" >/dev/null 2>&1; then etape "$libelle" "$@"
  else echo "  ⏭ $libelle — sauté ($outil absent)"; saute=$((saute + 1)); fi
}
echo "Contrôles Logeo :"
etape "noms et mots interdits" python3 outils/verifier_noms.py
etape "hygiène (secrets, débogage, tailles)" python3 outils/verifier_hygiene.py
etape "nom de la branche courante" python3 outils/verifier_branche.py
optionnelle ruff "ruff check" ruff check .
optionnelle ruff "ruff format --check" ruff format --check .
optionnelle djlint "djlint --check" djlint --check serveur/web
[ -d outils/tests ] && etape "tests des outils" python3 -m unittest discover -s outils/tests -q
if [ -f serveur/manage.py ]; then
  optionnelle pytest "pytest (hors tests lents)" python3 -m pytest -x -q -m "not lent" serveur
  optionnelle lint-imports "import-linter" lint-imports
  optionnelle bandit "bandit" bandit -q -r serveur/apps
fi
if [ "$echec" -ne 0 ]; then echo "✗ Contrôles en échec."; exit 1; fi
if [ "$saute" -ne 0 ] && [ "${LOGEO_STRICT:-0}" = "1" ]; then echo "✗ $saute contrôle(s) sauté(s) en mode strict."; exit 1; fi
echo "✔ Contrôles réussis ($saute sauté(s))."
