# AGENTS.md — règles pour toute IA et tout développeur

Source unique. `CLAUDE.md` renvoie ici. En cas de doute : `docs/cahier-des-charges.md` d'abord, puis les ADR (`docs/adr/`).

## 1. Projet en 10 lignes

- Immo+ aide les étudiants de Parakou (Bénin) à trouver une chambre : annonces avec vidéo réelle, gérants vérifiés, messagerie intégrée, aucun contact hors plateforme.
- Trois surfaces : **APP** (application mobile, partie 2, pas encore commencée), **WEB** (site public rendu par le serveur), **ADM** (administration, hôte séparé).
- Un seul serveur : monolithe modulaire Django 5.2 LTS, PostgreSQL 16, Redis, Celery, Channels, Caddy.
- Partie 1 (ce dépôt) : serveur, site web, API `/v1`, administration, infrastructure, outils. Reste : le mobile (`mobile/`).
- Montants en FCFA entiers, fuseau `Africa/Porto-Novo`, textes en français.
- Pas de Node, pas de Next.js : CSS pur assemblé par `outils/construire_css.py`.

## 2. Commandes essentielles

| Commande                                                             | Effet                                                                     |
| -------------------------------------------------------------------- | ------------------------------------------------------------------------- |
| `make up` / `make down`                                              | démarre / arrête la pile Docker locale (site : http://www.localhost:8080) |
| `make migrate`                                                       | applique les migrations (rôle `migrate`)                                  |
| `make seed`                                                          | données de démonstration (à partir de la phase 1)                         |
| `make css`                                                           | assemble le CSS empreinté                                                 |
| `make test`                                                          | tests hors `lent` et `e2e`                                                |
| `make test-unitaires`, `make test-integration`, `make test-securite` | tests par marqueur                                                        |
| `make couverture`                                                    | couverture, seuil 85 %                                                    |
| `make lint`                                                          | ruff                                                                      |
| `make verifier`                                                      | tous les contrôles (hook `pre-push` et CI)                                |
| `make hooks`                                                         | installe les hooks Git                                                    |
| `make openapi`                                                       | régénère `docs/api/openapi.json`                                          |
| `make docs`                                                          | cohérence de la documentation (phase 9)                                   |
| `make fumee`, `make diagnostic`                                      | test de fumée, diagnostic de l'environnement                              |

Un seul test : `cd serveur && python -m pytest apps/core/tests/integration/test_sante.py::test_healthz_repond_ok`.
Shell Django : `make shell`. Installation locale hors Docker : `make installer`.

## 3. Carte du dépôt

**Le dossier s'appelle `serveur/`, jamais « backend ».**

- `serveur/config/` : réglages (`base`, `local`, `public`, `admin`, `test`), URL, ASGI, Celery.
- `serveur/apps/<app>/` : `core`, `accounts`, `listings`, `media`, `chat`, `notifications`, `moderation`, `billing`, `audit`.
- `serveur/web/` : site public (gabarits, CSS, JS, vues minces). `serveur/adminsite/` : administration.
- `infra/` : Docker, Compose, Caddy, PostgreSQL, sauvegarde. `outils/` : scripts de contrôle et de construction.
- `docs/` : cahier des charges, ADR, avancement, vérification. `.githooks/`, `.github/` : barrières Git.
- `mobile/` : réservé à la partie 2.

## 4. Architecture en règles

Couches d'une application : `models / selectors / services / events / providers` et des adaptateurs minces (`api`, `web`, `consumers`, `tasks`).

- Une règle métier = un service. Aucune règle métier dans une vue, un consumer ou une tâche.
- Les adaptateurs appellent les services et les sélecteurs ; ils n'importent jamais `models`.
- Une application n'importe pas les modèles d'une autre ; elle passe par les services ou les événements de l'autre.
- `apps.core` n'importe aucune autre application. Ces règles sont imposées par `import-linter` (`serveur/pyproject.toml`).
- Ajouter une fonctionnalité sans rien casser : service → test → sélecteur → API → vue web → OpenAPI (`make openapi`) → documentation → migration en deux temps.

## 5. Sécurité (à ne jamais enfreindre)

- Administration séparée : autre hôte, autre clé, autre cookie, autre rôle PostgreSQL, liste blanche d'adresses.
- Aucun numéro de téléphone n'est conservé (ADR 0009) ; l'adresse précise d'un logement n'est jamais exposée.
- Aucun script ni style en ligne (CSP stricte) : pas d'attribut `style=`, pas de `onclick=`.
- Aucun secret dans le dépôt ; `.env` et `infra/compose/env/*.env` sont ignorés.
- 404 plutôt que 403 pour ne pas révéler l'existence d'une ressource.
- Toute autorisation est vérifiée côté serveur. Les actions sensibles sont journalisées (`audit`).
- `DEBUG` et les secrets `dev-…` font échouer le démarrage des réglages `public` et `admin`.

## 6. Format Git

Commit : `type(portée): sujet`.

- `type` ∈ `feat fix refactor perf test docs style build ci chore revert sec`.
- `portée` obligatoire ∈ `serveur web admin api ws media auth annonces messagerie notifications moderation abonnement audit infra docs deps design i18n outils mobile`.
- Première ligne : 72 caractères au plus, sujet en minuscule, sans point final, 5 caractères de sujet au moins.
- `!` après la portée = changement cassant (corps obligatoire).
- `feat` et `fix` portent une ligne `Refs: EF-…` ou `Refs: n/a`.
- `fixup!`, `squash!`, `wip` : refusés au push.
- Aucune ligne `Co-Authored-By` ni mention d'outil ou d'assistant dans les commits, PR et fichiers (confidentialité).

Branche : `^(main|(feat|fix|refactor|perf|test|docs|style|build|ci|chore|sec)/[a-z0-9]+(-[a-z0-9]+)*)$`, 60 caractères au plus.
Pas de push direct sur `main` (sauf premier push : `IMMOPLUS_PREMIER_PUSH=1`). Pas de fusion « squash ».
Le hook `pre-push` lance `outils/verifier_tout.sh` ; la CI refait les mêmes contrôles.
**Ne jamais utiliser `--no-verify`.**

## 7. Conventions de code

- `ruff` (lint et format), lignes de 100 caractères. Noms : `snake_case` Python, `kebab-case` gabarits, CSS, JS, documents.
- Tests : `pytest`, marqueurs `unitaire`, `integration`, `api`, `ws`, `securite`, `e2e`, `lent`, `pg`, `ffmpeg`.
- Pas de `print`, `breakpoint()`, `pdb`, `console.log`. Journaux JSON (`apps.core.logging`) ; numéros et codes sont masqués.
- Textes visibles en français, via les fichiers de traduction.

## 8. Design

Voir `docs/design-system.md`. Aucune couleur, taille ou ombre en dur hors de `serveur/web/static/css/tokens.css`.
Tout nouveau composant est présenté dans `/styleguide`. `make verifier` contrôle les contrastes (`outils/contraste.py`).

## 9. API

Additive uniquement, versionnée sous `/v1`. Après toute modification : `make openapi`. `docs/api/openapi.json` est versionné et vérifié.

## 10. Terminé = …

Code et tests écrits, `make verifier` au vert, API et documentation à jour, `docs/avancement.md` mis à jour, aucune dépendance sans ADR.
Avant de pousser : `make verifier`, relire le diff, vérifier le format du commit et de la branche.

## 11. Reprise de travail

Avant toute chose, lis `docs/avancement.md` ; à la fin de chaque session, mets-le à jour (phase, ce qui est fait, ce qui reste, décisions, pièges rencontrés).

## 12. Interdits

Ajouter une dépendance sans ADR · mettre de la logique dans une vue · contourner un hook · committer un fichier `.env` · inventer des données réelles · introduire Node ou Next.js · créer un dossier `backend/` ou `frontend/`.

## 13. Sources de vérité

`docs/cahier-des-charges.md`, puis `docs/adr/`.

## Design

Avant toute tâche d'interface (Django templates ou React Native), lis `docs/design/DESIGN.md` et compare avec les maquettes de `docs/design/screens/`.
Règles clés : pas d'emoji ni de sticker (icônes Lucide uniquement), logo `docs/design/assets/logo.svg` inchangé, tokens de DESIGN.md uniquement, tutoiement, inscription publique réservée aux locataires.

## Données

La base (models.py, migrations) et le cahier des charges priment sur les maquettes. Le design est strict pour le style ; les champs s'adaptent à l'existant. N'invente aucun champ ni migration : signale les écarts dans `docs/design/ECARTS.md` et demande avant de modifier le schéma. Voir section 12 de DESIGN.md.
