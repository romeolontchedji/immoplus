# Flux de travail, intégration continue et déploiement

Comment une modification va de l'ordinateur du développeur jusqu'au VPS, et ce qui la contrôle à chaque étape.
Complète `docs/contribuer.md` (règles de nommage et de commit) et `docs/deploiement-vps-pas-a-pas.md` (installation du
serveur).

## 1. Vue d'ensemble

```
 Développeur                    GitHub (romeolontchedji/immoplus)                VPS rmeolab (hébergeur)
 ───────────                    ─────────────────────────────────               ───────────────────────
 branche feat/…
   │ commit ── hooks locaux (format, noms, secrets)
   │ git push ── hook pre-push : TOUS les contrôles
   ▼
 2 dépôts reçoivent la branche ──►  demande de fusion vers main
 (copie Magloireaffokpe/immoplus)        │ CI : commits · verifier · mobile · image
                                         │ tout vert ─► fusion (« Merge pull request »)
                                         ▼
                                       main ── CI rejouée sur main
                                                                    ──►  bash infra/vps/deployer.sh
                                                                         (git pull, image, migrations, redémarrage)
```

- **Intégration continue (CI)** : automatique, sur GitHub Actions, à chaque demande de fusion et à chaque mise à jour
  de `main`.
- **Déploiement (CD)** : **manuel et volontaire**, une commande lancée par l'hébergeur sur le VPS. Rien ne part en
  production sans quelqu'un pour le décider et surveiller (choix assumé : serveur partagé, équipe réduite).

## 2. Les dépôts

| Dépôt | Rôle |
|---|---|
| `romeolontchedji/immoplus` | **Référence.** Sa branche `main` est ce que le VPS déploie. Les demandes de fusion s'y font. |
| `Magloireaffokpe/immoplus` | Copie du développeur : reçoit toutes les branches à chaque `git push`. Son `main` ne sert pas. |

Configuration locale du développeur (déjà en place) :

```
origin  git@github.com:romeolontchedji/immoplus.git (fetch)   ← git pull lit la référence
origin  git@github.com:Magloireaffokpe/immoplus.git (push)    ← git push écrit dans les deux
origin  git@github.com:romeolontchedji/immoplus.git (push)
romeo   git@github.com:romeolontchedji/immoplus.git           ← utile pour viser la référence seule
```

Pour la refaire sur un autre poste :

```bash
git clone git@github.com:romeolontchedji/immoplus.git && cd immoplus
git remote set-url --add --push origin git@github.com:romeolontchedji/immoplus.git
git remote set-url --add --push origin git@github.com:Magloireaffokpe/immoplus.git
make hooks
```

Le développeur se connecte une fois à GitHub en ligne de commande (`gh auth login -w`, connexion par le navigateur :
le code à 8 caractères s'affiche dans le terminal). Une connexion vaut pour tous les dépôts où il a les droits.

## 3. Le flux au quotidien

```bash
# 1. Partir de main à jour
git checkout main && git pull
git switch -c feat/ma-modification              # type/mots-en-minuscules-separes-par-des-tirets

# 2. Travailler, commiter (le hook commit-msg vérifie le format)
git commit -m "feat(annonces): ajouter un filtre par prix" -m "Refs: n/a"

# 3. Vérifier puis pousser (le hook pre-push relance tous les contrôles)
make verifier
git push -u origin feat/ma-modification

# 4. Demande de fusion vers main de la référence (titre au format des commits)
gh pr create --repo romeolontchedji/immoplus --base main --fill
gh pr checks --watch                           # attendre les quatre contrôles

# 5. Fusionner quand tout est vert (« Create a merge commit », jamais « squash »)
gh pr merge --repo romeolontchedji/immoplus --merge
git checkout main && git pull
git branch -d feat/ma-modification

# 6. Prévenir l'hébergeur : il déploie (section 6)
```

Si la base PostgreSQL locale n'est pas démarrée, le hook pre-push saute les tests qui en ont besoin (« ⏭ pytest avec
PostgreSQL — sauté ») et lance les autres : la CI, elle, les joue tous. `make up` avant de pousser donne la vérification
complète en local.

## 4. Les contrôles locaux (hooks Git, `.githooks/`)

Activés par `make hooks` (`git config core.hooksPath .githooks`). Ne jamais les contourner (`--no-verify`) : la CI
refait les mêmes contrôles et une demande de fusion rouge ne se fusionne pas.

| Hook | Quand | Ce qu'il vérifie |
|---|---|---|
| `pre-commit` | `git commit` | Format Python (ruff), noms de fichiers et mots interdits, hygiène des fichiers indexés (secrets, `print`, débogage, tailles) |
| `commit-msg` | `git commit` | Message `type(portée): sujet` (minuscule, 72 caractères), `Refs:` pour `feat` et `fix` |
| `pre-push` | `git push` | Nom de branche ; refus d'un push direct sur `main` (sauf amorçage `IMMOPLUS_PREMIER_PUSH=1` d'un dépôt sans `main`) ; format de chaque commit envoyé ; puis `outils/verifier_tout.sh` en entier |

`outils/verifier_tout.sh` (aussi `make verifier`) : noms, hygiène, branche, ruff (lint et format), djlint (gabarits),
jetons de design synchronisés et contrastes WCAG, tests des outils, mobile (types, lint, tests), import-linter
(frontières entre modules), bandit (sécurité), migrations à jour, OpenAPI à jour, migration-linter, pytest complet.

## 5. L'intégration continue (GitHub Actions, `.github/workflows/`)

| Workflow · tâche | Déclencheur | Étapes | Durée |
|---|---|---|---|
| `commits` · **commits** | Demande de fusion (ouverte, modifiée, mise à jour) | Titre de la demande au format des commits ; nom de la branche ; format de chaque commit | ~10 s |
| `verifier` · **verifier** | Demande de fusion et push sur `main` | PostgreSQL 16 et Redis 7 en services ; ffmpeg ; `verifier_tout.sh` complet ; couverture ≥ 85 % ; preuve des hooks (`tester_hooks.sh`, 9 cas) ; **audit des dépendances** (`pip-audit --strict`) | ~4 min |
| `verifier` · **mobile** | idem | `npm ci` (verrou exact), types, lint, 103 tests, client d'API régénéré identique au contrat `docs/api/openapi.json` | ~1 min |
| `verifier` · **image** | idem | Construction de l'image Docker du serveur ; validation de la configuration Compose et des deux Caddyfile | ~45 s |

Une nouvelle poussée annule l'exécution précédente de la même branche (`concurrency`). Les tâches n'ont que le droit
de lecture sur le dépôt (`permissions: contents: read`) : la CI ne publie rien et ne déploie rien.

**Ce qui fait échouer la CI le plus souvent, et le remède :**

| Symptôme | Cause | Remède |
|---|---|---|
| `commits` rouge sur « Titre de la demande de fusion » | Titre libre | `gh pr edit <n> --title "feat(portée): sujet"` |
| `mobile` rouge sur `npm ci` | `package-lock.json` produit par une autre version de npm | `npx npm@10.9.4 install --package-lock-only --ignore-scripts` dans `mobile/`, commiter |
| `verifier` rouge sur « Audit des dépendances » | Faille publiée dans une dépendance Python | `uv pip compile serveur/requirements/base.in -o serveur/requirements/base.txt --python-version 3.12 --upgrade-package <paquet>` (idem `dev`), tests, commit `build(deps): …` |
| `verifier` rouge sur « Couverture » | Code ajouté sans tests | Écrire les tests |
| `mobile` rouge sur « Client d'API à jour » | Contrat de l'API modifié sans régénérer le client | `make openapi` puis `npm run api:generer` dans `mobile/` |

## 6. Le déploiement (manuel, par l'hébergeur)

Après chaque fusion sur `main`, sur le VPS :

```bash
ssh immoplus@213.156.133.76
cd ~/apps/immoplus
immoplus exec backup bash /scripts/boucle.sh une-fois     # sauvegarde juste avant (alias de l'étape 7 du guide)
bash infra/vps/deployer.sh
```

`infra/vps/deployer.sh` :

1. vérifie que `.env` et le réseau du Caddy central (`web_proxy`) existent ;
2. `git pull --ff-only` : n'accepte qu'une avance de `main`, jamais une histoire réécrite ;
3. reconstruit l'image et relance la pile (`up -d --build --remove-orphans`) ; le service `migrer` applique les
   migrations et rassemble les fichiers statiques **avant** le démarrage des processus web ;
4. affiche l'état des services. Aucun volume ni aucune donnée n'est supprimé.

Ensuite : `https://www.immoplus.bj/readyz` doit répondre 200, et `make fumee` (depuis une adresse autorisée) passer.
Si `.env.example` a reçu une nouvelle variable, l'ajouter à `.env` puis `python3 outils/creer_env.py --services` avant
de relancer `deployer.sh`.

**Revenir en arrière** : `git checkout <commit>` puis `immoplus up -d --build` (guide de déploiement, étape 16) ; restaurer la sauvegarde si la version annulée contenait une migration.

**Ce qui tourne seul ensuite** : la minuterie d'autoguérison redémarre un conteneur figé, la sauvegarde de la nuit,
les tâches planifiées (beat).

**Application mobile** : pas de publication automatique. Compilation EAS et envoi au Play Store à la main (guide de
déploiement, étape 13), après le déploiement du serveur si l'application dépend d'une nouveauté de l'API.

## 7. Sécurité de la chaîne

- **Protection de `main` sur le dépôt de référence** : aujourd'hui **absente** (vérifié le 21 octobre 2026). Les hooks
  locaux se contournent ; seule GitHub peut l'imposer. À faire par le propriétaire (Romeo), une fois :

  ```bash
  gh api -X PUT repos/romeolontchedji/immoplus/branches/main/protection --input - <<'JSON'
  {
    "required_status_checks": {"strict": true, "contexts": ["commits", "verifier", "mobile", "image"]},
    "enforce_admins": true,
    "required_pull_request_reviews": null,
    "restrictions": null,
    "allow_force_pushes": false,
    "allow_deletions": false
  }
  JSON
  ```

  Pour exiger en plus l'approbation de l'hébergeur avant chaque fusion, remplacer `null` par
  `{"required_approving_review_count": 1}`. Dans *Settings › General* : branche par défaut `main`, et décocher
  « Allow squash merging ».
- **Dependabot** (activé sur le dépôt de référence) signale les failles connues et ouvre des branches de mise à jour ;
  `pip-audit` bloque la CI tant qu'une faille Python connue reste dans `base.txt`.
- **Secrets** : jamais dans Git (hook d'hygiène) ; `.env` vit sur le serveur et dans le coffre de l'équipe. La CI
  n'utilise aucun secret de production. La clé de déploiement du VPS est en **lecture seule**.
- **Fichiers sensibles** : `.github/CODEOWNERS` désigne qui relit `infra/`, `outils/`, `.github/`, `.githooks/` et
  `AGENTS.md` (remplacer `@porteur-du-projet` par l'identifiant GitHub de Romeo pour que la règle s'applique).

## 8. Pistes, non mises en place

- **Déploiement automatique** après fusion (tâche GitHub Actions qui se connecte au VPS en SSH et lance
  `deployer.sh`) : possible, mais demande de stocker une clé SSH du VPS dans GitHub. À décider avec l'hébergeur.
- **Version mobile automatique** (`eas build` déclenché par un tag) : à envisager une fois le Play Store en place.
- **Tags de version** (`v1.0.0`…) posés à chaque mise en production, pour des retours en arrière plus lisibles.
