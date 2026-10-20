#!/usr/bin/env bash
# Preuve que les hooks refusent ce qu'ils doivent refuser : 9 cas dans un dépôt temporaire avec distant nu.
set -uo pipefail
# Le dépôt temporaire ne contient ni Django ni les outils de la CI : les contrôles complets y sont
# « sautés ». On n'hérite donc pas du mode strict posé par la CI (IMMOPLUS_STRICT=1), sinon le premier
# push d'amorçage échouerait pour de simples sauts, sans rapport avec les hooks testés.
unset IMMOPLUS_STRICT
SRC="$(cd "$(dirname "$0")/.." && pwd)"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
git init -q --bare "$TMP/distant.git"
git init -q -b main "$TMP/depot"
cd "$TMP/depot"
git config user.name "Test" && git config user.email "test@immoplus.local"
git remote add origin "$TMP/distant.git"
mkdir -p outils .githooks serveur
cp "$SRC"/outils/*.py "$SRC"/outils/*.sh "$SRC"/outils/mots-interdits.toml "$SRC"/outils/ruff.toml outils/
cp "$SRC"/serveur/pyproject.toml serveur/   # configuration ruff héritée par outils/ruff.toml
cp "$SRC"/.githooks/* .githooks/
git config core.hooksPath .githooks
git add . && git commit -q -m "chore(outils): amorcer le dépôt de test" || { echo "✗ amorçage impossible"; exit 1; }
IMMOPLUS_PREMIER_PUSH=1 git push -q origin main 2>/dev/null || { echo "✗ le premier push d'amorçage (IMMOPLUS_PREMIER_PUSH=1) a échoué"; exit 1; }

ok=0; ko=0
pousser() { # pousse en affichant la raison du refus (ligne « Push annulé »)
  local sortie; sortie="$(git push -q "$@" 2>&1)"; local code=$?
  printf '%s\n' "$sortie" | grep -E "Push annulé|Premier push" | sed 's/^/      /'
  return $code
}
verdict() { # verdict <n> <libellé> <attendu: refus|succes> <code retour>
  local attendu_ok=0; [ "$3" = "succes" ] && attendu_ok=1
  if { [ "$attendu_ok" = 1 ] && [ "$4" -eq 0 ]; } || { [ "$attendu_ok" = 0 ] && [ "$4" -ne 0 ]; }; then
    echo "  ✔ cas $1 — $2 : $3 comme attendu"; ok=$((ok + 1))
  else
    echo "  ✗ cas $1 — $2 : comportement INATTENDU (code $4)"; ko=$((ko + 1))
  fi
}
ecrire() { printf '%s\n' "$2" > "$1"; git add "$1"; }
FAUX="AKIA""ABCDEFGHIJKLMNOP"   # fausse clé, assemblée à l'exécution : jamais écrite dans le dépôt

echo "Cas 1 — message sans format"
ecrire a.txt un; git commit -q -m "ajout truc"; verdict 1 "commit « ajout truc »" refus $?; git reset -q
echo "Cas 2 — feat sans Refs"
ecrire a.txt un; git commit -q -m "feat(serveur): ajouter l'envoi de message"; verdict 2 "feat sans Refs" refus $?
echo "Cas 3 — feat avec Refs"
git commit -q -m "feat(serveur): ajouter l'envoi de message" -m "Refs: EF-MSG-03"; verdict 3 "feat avec Refs" succes $?
echo "Cas 4 — dossier interdit"
mkdir -p "$(printf 'back%s' end)"; ecrire "$(printf 'back%s' end)/x.py" "x = 1"
git commit -q -m "chore(serveur): ajouter un fichier"; verdict 4 "fichier dans un dossier interdit" refus $?; git reset -q; rm -rf "$(printf 'back%s' end)"
echo "Cas 5 — mauvaise branche"
git checkout -q -b Feat/Mauvais_Nom; pousser origin Feat/Mauvais_Nom; verdict 5 "push de Feat/Mauvais_Nom" refus $?
echo "Cas 6 — push direct sur main"
git checkout -q main; pousser origin main; verdict 6 "push direct sur main" refus $?
echo "Cas 7 — commit wip poussé"
git checkout -q -b fix/essai-wip; ecrire b.txt deux; git commit -q --no-verify -m "wip"
pousser origin fix/essai-wip; verdict 7 "commit « wip » poussé" refus $?
echo "Cas 8 — secret"
git checkout -q main; git checkout -q -b fix/essai-secret; ecrire c.py "cle = \"$FAUX\""   # guillemets doubles : conforme à ruff, seul le secret peut provoquer le refus
git commit -q -m "chore(serveur): ajouter une clé"; verdict 8 "fausse clé secrète (commit)" refus $?
git commit -q --no-verify -m "chore(serveur): ajouter une clé"
pousser origin fix/essai-secret; verdict 8 "fausse clé secrète (push après --no-verify)" refus $?
echo "Cas 9 — série valide"
git checkout -q main; git checkout -q -b feat/serie-valide
ecrire d.txt trois; git commit -q -m "docs(docs): décrire la série valide"
ecrire e.txt quatre; git commit -q -m "feat(web): ajouter une page" -m "Refs: n/a"
pousser origin feat/serie-valide; verdict 9 "série valide poussée" succes $?

echo ""; echo "Résultat : $ok conforme(s), $ko non conforme(s)."
[ "$ko" -eq 0 ]
