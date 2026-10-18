1. **Le cahier des charges (CDC), fourni en Partie B de ce même fichier** (entre les marqueurs `<!-- DEBUT CDC -->` et `<!-- FIN CDC -->`) : référence unique du périmètre, des exigences (identifiants `EF-…` et `ENF-…`), du modèle de données (19 tables), de l'API (§10), des règles métier (§11), de la sécurité (§5) et des budgets de performance (§4.6, §8). **Première action : extrais la Partie B par script** (par exemple `sed -n '/<!-- DEBUT CDC -->/,/<!-- FIN CDC -->/p' fichier.md > docs/cahier-des-charges.md`, sans la retaper) si ce fichier est disponible dans ton bac à sable ; sinon écris-la depuis ton contexte. Lis-la intégralement avant d'écrire la moindre ligne, puis relis la section concernée avant chaque phase. Les sections de planification, de risques et le glossaire du document d'origine ont été retirés ; les numéros de section sont conservés, certains renvois pointent donc vers des sections absentes : ignore-les.
2. **Ce prompt** : il précise et complète le CDC. En cas de conflit, **ce prompt l'emporte** sur : le nommage (§2), la pile CSS (§4), le format Git et ses contrôles (§6), le design (§9), les livrables de documentation (§11), le pack de passation mobile (§10), l'environnement de génération (§0 bis).
3. Tes propres décisions, consignées en ADR, uniquement pour les points non couverts.

Chaque exigence du CDC porte une priorité : **M** (obligatoire), **S** (à faire sauf impossibilité justifiée en ADR), **C** (facultatif : à faire en dernier, seulement si tout le reste est terminé). Tu implémentes tous les M et tous les S de la partie 1. Les exigences qui concernent uniquement l'application mobile (`APP` seul) sont hors de cette partie ; mais le **serveur** qui les sert, lui, est dans cette partie.

# 2. Nommage, langues et vocabulaire (règles impératives)

- **Le dossier du code serveur s'appelle `serveur/`. Le mot « backend » est interdit** dans les noms de dossiers, de fichiers, de paquets, de modules, de variables, de classes, de commandes `make`, de services Docker et de clés de configuration que tu choisis. (Exceptions techniques imposées par les outils, listées dans `outils/mots-interdits.toml` : `AUTHENTICATION_BACKENDS`, `EMAIL_BACKEND`, `CHANNEL_LAYERS[...]["BACKEND"]`, `result_backend` de Celery, `CACHES[...]["BACKEND"]`.) L'interface de stockage du CDC nommée `StorageProvider` s'appelle **`StorageProvider`** dans le code (variable `STORAGE_PROVIDER`), comme les autres fournisseurs. Ce renommage est consigné dans un ADR.
- Le front du site web vit dans `serveur/web/` (gabarits Django). Il n'existe **aucun** dossier `frontend/`. L'application mobile viendra dans `mobile/` (partie 2).
- **Langues :** identifiants de code, noms de tables et de colonnes, noms de routes d'API, noms de branches : **anglais** (comme dans le CDC). Textes affichés à l'utilisateur, messages d'erreur d'API (`message`), documentation, commentaires de haut niveau, **messages de commit** : **français**.
- URLs publiques du site en français (`/chambres`, `/quartiers`, `/inscription`…), comme dans le CDC §10.9.
- Orthographe française soignée (accents, apostrophes typographiques dans les textes affichés, espaces insécables avant `:`, `;`, `?`, `!` et dans « 25 000 FCFA »).

# 3. Contraintes non négociables (extrait du CDC, à ne jamais violer)

1. **Une seule base PostgreSQL, un seul code** : monolithe modulaire Django ; l'API (mobile) et les vues du site appellent **les mêmes services**. Aucune règle métier dans une vue, un sérialiseur, un consommateur WebSocket ou une tâche.
2. **Administration complètement séparée** : autre hôte, autre processus, autres réglages, autre clé secrète, autre cookie, autre rôle PostgreSQL (`admin_app`), autre fichier d'environnement ; aucune route d'administration sur le site public et aucune route publique sur l'hôte d'administration. 2FA TOTP obligatoire, verrouillage par compte (django-axes), accès réservé à une liste d'adresses ou à un VPN. Détail : CDC §5.1.
3. **Le numéro n'est jamais exposé par Logeo** : le numéro du gérant n'apparaît ni dans l'API, ni dans les pages, ni dans les aperçus de lien, ni dans les journaux. Messagerie en **texte seul**. **Amendé le 2026-10-18 (décision du porteur)** : dans la messagerie, locataire et gérant peuvent s'échanger librement numéros et liens et poursuivre hors plateforme ; le revenu vient de l'abonnement des gérants et des alertes payantes des locataires, pas du maintien des échanges. Détection des coordonnées (§11.7) en mode `off` par défaut dans la messagerie ; les annonces restent sans coordonnées.
4. **Pas de Node en production** ni dans les images de production. Pas de Next.js. Site rendu par Django (gabarits) + HTMX + Alpine.js (build compatible CSP) + **CSS maison en CSS pur** (sans Tailwind : voir §4), assemblé par un script Python. Node n'est utilisé nulle part dans cette partie 1 (au plus pour récupérer des fichiers JS figés pendant la génération).
5. **Sécurité par conception** (CDC §5) : CSP stricte sans script ni style en ligne, cookies `__Host-`, CSRF, Argon2id, JWT court + rafraîchissement opaque à rotation, ticket WebSocket à usage unique, anti-pompage SMS, journal d'audit résistant à la modification, pièces d'identité chiffrées, rôles de base séparés.
6. **Mobile first** : toutes les pages se conçoivent d'abord à 360 px sur 3G, puis s'élargissent. Budgets : HTML < 30 Ko compressés, JavaScript initial < 60 Ko compressés, LCP < 2,5 s en 4G.
7. **Évolutivité** : API additive uniquement (`/v1`), migrations en deux temps, énumérations ouvertes, drapeaux de fonctionnalité dans `app_settings`, fournisseurs derrière des interfaces, processus sans état.
8. **Le serveur est prêt pour le mobile dès la fin de cette partie** : tous les points d'entrée du CDC §10 (hors pages du site) sont implémentés, testés et documentés (§10 de ce prompt).

# 4. Pile technique (versions à figer à l'installation)

Choisis la **dernière version stable** de chaque composant à la date du jour, vérifie leur compatibilité entre elles, et **fige** toutes les versions exactes dans les fichiers de verrouillage. Note le résultat dans `docs/adr/0001-versions-et-pile.md` (avec le calendrier de support de Django : retiens une version à support long terme encore supportée).

| Couche | Choix |
|---|---|
| Langage | Python 3.12 (ou plus récent supporté par tout l'ensemble) |
| Framework | Django (LTS), Django REST Framework, drf-spectacular |
| Temps réel | Django Channels, channels-redis, Uvicorn sous Gunicorn |
| Tâches | Celery + Redis, Celery beat (verrou pour garantir une seule instance) |
| Base | PostgreSQL 16 (pg_trgm, unaccent), psycopg 3 avec pool natif |
| Cache et files | Deux instances Redis : `redis-cache` (éviction LRU) et `redis-queue` (AOF, sans éviction) |
| Authentification | PyJWT (HS256, clés distinctes site/administration), argon2-cffi, django-otp (TOTP du personnel), django-axes (administration), phonenumbers (version récente figée) |
| Site | Gabarits Django, HTMX, Alpine.js (build CSP), **CSS pur organisé en couches** (`tokens.css`, `base.css`, `layout.css`, `components/*.css`, `utilities.css` limité à une quarantaine de classes), assemblé, minifié et empreinté par `outils/construire_css.py` (bibliothèque standard Python, aucun binaire à télécharger) ; hls.js et tus-js-client en fichiers figés dans `serveur/web/static/vendor/` (récupérés par `outils/telecharger_vendor.py`, voir §0 bis) |
| Administration | django-unfold (sinon thème standard + feuille de style maison : décision documentée), Chart.js servi en local |
| Médias | ffmpeg/ffprobe, Pillow + pillow-heif, nh3 (assainissement HTML), markdown-it-py (liste blanche) |
| Proxy | Caddy 2 (HTTPS automatique, HTTP/3, zstd/gzip) |
| Qualité et tests | ruff (lint + format), pytest, pytest-django, pytest-cov, pytest-xdist, pytest-randomly, factory_boy, hypothesis, time-machine, fakeredis, httpx, schemathesis, pytest-asyncio (Channels), import-linter, django-migration-linter, bandit, pip-audit, djlint (gabarits), oasdiff (en conteneur), Playwright (Python) + axe pour le site, k6 (en conteneur) pour la charge |
| Conteneurs | Docker, Docker Compose (profils `dev`, `prod`) |
| CI | GitHub Actions |

**Écart assumé avec le CDC :** le CDC mentionne Tailwind ; la génération se faisant dans un bac à sable sans garantie de téléchargement de binaire, le CSS est écrit en CSS pur (même résultat visuel, aucun outil externe). Consigne-le dans `docs/adr/0002-css-pur.md`. Aucun paquet n'est ajouté sans justification ; chaque ajout non listé ici reçoit une ligne dans l'ADR 0001.

# 5. Structure du dépôt (à créer à l'identique)

```
logeo/
├─ AGENTS.md                      règles pour toute IA et tout développeur (§7) — source unique
├─ CLAUDE.md                      une ligne : « Lis AGENTS.md. » (compatibilité des outils)
├─ README.md                      présentation, démarrage en 5 commandes, liens vers docs/
├─ Makefile                       cibles : up, down, migrate, seed, css, vendor, test, test-unitaires, test-integration, test-e2e, test-securite, test-lent, couverture, lint, verifier, hooks, openapi, docs, fumee, diagnostic, nettoyer
├─ .editorconfig  .gitignore  .gitattributes  .env.example  .dockerignore
├─ .githooks/                     pre-commit, commit-msg, pre-push (appellent outils/)
├─ .github/
│  ├─ workflows/verifier.yml      mêmes contrôles que pre-push + tests complets + construction d'image
│  ├─ workflows/commits.yml       vérifie format des commits et titre de la demande de fusion
│  ├─ pull_request_template.md  CODEOWNERS  ISSUE_TEMPLATE/
├─ serveur/                       TOUT le code Python (jamais « backend »)
│  ├─ pyproject.toml  requirements/ (verrouillés)  manage.py
│  ├─ config/                     settings/{base,local,public,admin,test}.py ; asgi ; urls_public.py ; urls_admin.py ; celery.py
│  ├─ apps/
│  │  ├─ accounts/  listings/  media/  chat/  notifications/  moderation/  billing/  audit/  core/
│  │  └─ (dans chaque app : models.py, selectors.py, services.py, events.py, api/, web/, consumers.py, tasks.py, tests/)
│  ├─ web/                        gabarits, vues du site, static/{css,js,vendor,img}, composants (§9)
│  ├─ adminsite/                  administration : tableaux de bord, vues sur mesure, thème
│  └─ tests/                      tests transverses (sécurité, charge de requêtes, contrats d'API, e2e site)
├─ infra/
│  ├─ docker/                     Dockerfile (multi-étapes), entrypoints
│  ├─ compose/                    docker-compose.yml, docker-compose.prod.yml, env/ (un fichier d'exemple par service)
│  ├─ caddy/Caddyfile  caddy/Caddyfile.local
│  ├─ postgres/                   init : rôles app, admin_app, migrate ; extensions
│  ├─ backup/                     scripts restic, pg_dump, archivage WAL, restauration
│  └─ vps/                        bootstrap.sh (durcissement), fail2ban, unattended-upgrades
├─ outils/                        scripts de contrôle (§6) et utilitaires : construire_css.py, telecharger_vendor.py, contraste.py, ws_client.py, diagnostic.sh, amorcer_depot.sh, tester_hooks.sh, fumee…
├─ docs/                          documentation complète (§11)
└─ mobile/                        (vide pour l'instant : un fichier LISEZMOI.md renvoie à docs/mobile/passation.md)
```

# 6. Format Git imposé et refus automatique du push

**Objectif : un push qui ne respecte pas le format est refusé.** Tu implémentes trois barrières : hooks Git locaux, intégration continue, protection de branche.

## 6.1 Règles de format

**Messages de commit** — Conventional Commits en français :

```
type(portée): sujet à l'impératif, en minuscules, sans point final

Corps facultatif : pourquoi, pas comment (lignes ≤ 100 caractères).

Refs: EF-MSG-03, ENF-PERF-02
```

- `type` ∈ `feat`, `fix`, `refactor`, `perf`, `test`, `docs`, `style`, `build`, `ci`, `chore`, `revert`, `sec`.
- `portée` obligatoire ∈ `serveur`, `web`, `admin`, `api`, `ws`, `media`, `auth`, `annonces`, `messagerie`, `notifications`, `moderation`, `abonnement`, `audit`, `infra`, `docs`, `deps`, `design`, `i18n`, `outils`, `mobile`.
- Première ligne : **72 caractères au plus**, sujet commençant par une minuscule, sans point final, au moins 5 caractères de sujet. `!` après la portée signale un changement cassant (`feat(api)!: …`) ; il exige un corps expliquant la migration.
- Les commits de type `feat` et `fix` portent obligatoirement une ligne `Refs:` avec au moins un identifiant du CDC (`EF-…`, `ENF-…`) ou `Refs: n/a`.
- Commits `fixup!`, `squash!`, `WIP`, `wip` : autorisés en local, **refusés au push**. Les commits de fusion automatiques (`Merge …`) et de retour arrière générés par Git sont tolérés.
- Un commit ne mélange pas des portées sans rapport ; un commit = un changement cohérent qui passe les tests.

**Branches** — expression régulière : `^(main|(feat|fix|refactor|perf|test|docs|style|build|ci|chore|sec)/[a-z0-9]+(-[a-z0-9]+)*)$`. Exemple : `feat/messagerie-envoi-message`. Pas de majuscules, pas d'accents, pas d'underscore, 60 caractères au plus.

**Pousser sur `main` est interdit** par le hook local (sauf premier push d'amorçage avec `LOGEO_PREMIER_PUSH=1`, documenté dans `docs/contribuer.md`) ; `main` est protégée côté GitHub (§6.4). Tout passe par demande de fusion (squash interdit : l'historique propre est la règle ; fusion « rebase » ou fusion classique).

**Titre de demande de fusion** : même format que l'en-tête d'un commit.

## 6.2 Contrôles à implémenter (dans `outils/`, en Python pur, sans dépendance hors bibliothèque standard pour les contrôles de format)

- `outils/verifier_commit.py <fichier-message>` : valide l'en-tête, la longueur, la portée, `Refs:`, les mots interdits au début (`wip`). Message d'erreur **en français, lisible, avec l'exemple correct**.
- `outils/verifier_branche.py` : valide le nom de la branche courante et celui des branches poussées.
- `outils/verifier_noms.py` : refuse tout chemin suivi par Git contenant un segment `backend`, `back-end` ou `Backend`, tout fichier hors conventions (`snake_case` pour Python, `kebab-case` pour gabarits, CSS, JS et documents, `UPPER` seulement pour `README`, `AGENTS`, `CLAUDE`, `LICENSE`, `CODEOWNERS`, `Makefile`, `Dockerfile`), et le mot interdit dans le code selon `outils/mots-interdits.toml` (liste d'exceptions explicitées).
- `outils/verifier_hygiene.py` : refuse les fichiers de plus de 1 Mo (liste d'exceptions), les `print(`, `breakpoint()`, `pdb`, `console.log` dans le code, les secrets (détection par motifs : clés, jetons, mots de passe, URL avec identifiants ; utilise `gitleaks` s'il est installé), les fichiers `.env` réels, les sauvegardes.
- `outils/verifier_tout.sh` (appelé par `make verifier`, le hook `pre-push` et la CI) : enchaîne `ruff check`, `ruff format --check`, `djlint --check`, `manage.py makemigrations --check --dry-run`, `django-migration-linter`, `lint-imports`, `bandit`, `pytest -x -q -m "not lent"`, `manage.py spectacular --validate` et la vérification que `docs/api/openapi.json` est à jour, puis les quatre scripts ci-dessus.

## 6.3 Hooks Git (dossier versionné `.githooks/`, installé par `make hooks` : `git config core.hooksPath .githooks`)

- `pre-commit` : formatage (`ruff format --check`), `verifier_noms`, `verifier_hygiene` sur les fichiers indexés (rapide, moins de 10 s).
- `commit-msg` : `verifier_commit`.
- `pre-push` : lit les références poussées ; pour **chaque** commit de la plage : `verifier_commit` ; `verifier_branche` ; refus d'un push direct sur `main` ; refus d'un commit `fixup!`/`squash!`/`wip` ; puis `outils/verifier_tout.sh`. **Au premier échec : code de sortie non nul, message explicatif en français (quoi, où, comment corriger), push annulé.**
- `make hooks` est lancé automatiquement par `make up` la première fois ; le README et le guide d'installation l'exigent. Un hook doit s'exécuter dans Docker si Python n'est pas installé localement (script d'enveloppe `outils/dans-docker.sh`).

## 6.4 Barrières côté serveur Git (indispensables : les hooks locaux se contournent avec `--no-verify`)

- `.github/workflows/commits.yml` : sur chaque demande de fusion, valide tous les commits et le titre (mêmes scripts) ; échec = fusion impossible.
- `.github/workflows/verifier.yml` : exécute `outils/verifier_tout.sh` + tests complets + construction de l'image + `oasdiff` contre `main` + analyse `pip-audit`.
- `docs/contribuer.md` contient la **procédure pas à pas** de protection de branche (`gh api` ou clics) : `main` exige la demande de fusion, les contrôles `commits` et `verifier` au vert, une revue approuvée, la branche à jour, l'interdiction des pushs forcés, y compris pour les administrateurs.
- `.github/CODEOWNERS` : les fichiers `AGENTS.md`, `.githooks/`, `outils/`, `.github/`, `infra/` exigent la revue du porteur du projet.

## 6.5 Preuve que le refus fonctionne (à exécuter réellement dans le bac à sable)

Écris `outils/tester_hooks.sh` (lancé aussi par la CI) : il crée un dépôt temporaire avec un **dépôt distant nu** (`git init --bare`), installe les hooks, puis vérifie, avec la sortie affichée : (1) un commit `ajout truc` est **refusé** ; (2) un commit `feat(serveur): ajouter l'envoi de message` sans `Refs:` est **refusé** ; (3) le même commit avec `Refs: EF-MSG-03` est **accepté** ; (4) un fichier `backend/x.py` est **refusé** ; (5) une branche `Feat/Mauvais_Nom` est **refusée** au push ; (6) un push direct sur `main` est **refusé** ; (7) un commit `wip` poussé est **refusé** ; (8) un fichier contenant une fausse clé secrète est **refusé** ; (9) une série valide est **poussée avec succès**. Joins la sortie complète de ce test dans `docs/verification.md`. Tant qu'un de ces neuf cas ne se comporte pas comme attendu, la phase 0 n'est pas terminée.

# 7. Le fichier `AGENTS.md` (à écrire en phase 0, à tenir à jour en continu)

C'est la **mémoire permanente** du projet pour toute IA et tout développeur futur. Court, dense, impératif (moins de 400 lignes), en français. Contenu obligatoire :

1. **Projet en 10 lignes** : ce qu'est Logeo, les surfaces (APP, WEB, ADM), le périmètre de la partie 1, ce qui reste (mobile).
2. **Commandes essentielles** : `make up`, `make migrate`, `make seed`, `make css`, `make test`, `make lint`, `make test-unitaires`, `make test-integration`, `make test-e2e`, `make test-securite`, `make test-lent`, `make couverture`, `make verifier`, `make hooks`, `make openapi`, `make docs` ; comment lancer un seul test ; comment ouvrir un shell Django.
3. **Carte du dépôt** : le rôle de chaque dossier ; **rappel en gras : le dossier s'appelle `serveur/`, jamais « backend »**.
4. **Architecture en règles** : couches `models / selectors / services / events / providers / adaptateurs (api, web, consumers, tasks)` ; qui a le droit d'importer quoi ; « une règle métier = un service » ; comment ajouter une fonctionnalité sans rien casser (checklist : service → test → sélecteur → API → vue web → OpenAPI → doc → migration en deux temps).
5. **Règles de sécurité à ne jamais enfreindre** : séparation administration, numéro du gérant jamais exposé, aucun script/style en ligne (CSP), pas de secret dans le dépôt, 404 plutôt que 403, autorisation côté serveur, journal d'audit.
6. **Format Git** : reprise exacte du §6 (types, portées, regex de commit et de branche, `Refs:`), liste des contrôles qui refusent le push, et **la consigne de ne jamais utiliser `--no-verify`**.
7. **Conventions de code** : ruff, noms, tests (`pytest`, marqueur `lent`), pas de `print`, journalisation JSON, fuseau `Africa/Porto-Novo`, montants en entiers FCFA, textes en français via fichiers de traduction.
8. **Conventions de design** : renvoi vers `docs/design-system.md` ; interdiction d'écrire une couleur, une taille ou une ombre en dur hors des jetons ; tout nouveau composant passe par `/styleguide`.
9. **API** : additive uniquement ; `make openapi` obligatoire après toute modification d'API ; le fichier `docs/api/openapi.json` est versionné et vérifié.
10. **Définition de « terminé »** (CDC §14.4) et **checklist avant push**.
11. **Reprise de travail** : « Avant toute chose, lis `docs/avancement.md` ; à la fin de chaque session, mets-le à jour (phase, ce qui est fait, ce qui reste, décisions, pièges rencontrés). »
12. **Interdits** : ajouter une dépendance sans ADR, mettre de la logique dans une vue, contourner un hook, committer un fichier `.env`, inventer des données réelles, introduire Node ou Next.js, créer un dossier `backend/` ou `frontend/`.
13. **Sources de vérité** : `docs/cahier-des-charges.md` d'abord, puis les ADR.

`CLAUDE.md` ne contient que : `Lis AGENTS.md avant toute action ; ce fichier fait foi.` Un test (`serveur/tests/test_agents.py`) vérifie que `AGENTS.md` existe, mentionne `serveur/`, ne contient pas « backend/ » en dehors de la règle qui l'interdit, et que chaque cible `make` citée existe dans le `Makefile`.

# 8. Le serveur : consignes détaillées

Implémente **tout** ce que décrivent les sections 4 à 11 du CDC. Les points ci-dessous précisent ou renforcent ; ils ne remplacent pas le CDC.

## 8.1 Organisation et couches

- Applications et responsabilités : celles du CDC §4.4 (structure du dépôt) ; `core` porte utilitaires, événements, interfaces des fournisseurs, pagination par curseur, format d'erreur unique, middleware d'identifiant de requête, filtre de journaux qui masque numéros et codes.
- `import-linter` : contrats écrits dès la phase 0 (aucune application n'importe les `models` d'une autre ; les adaptateurs n'importent pas les modèles directement ; `core` n'importe aucune application).
- Chaque service : une fonction publique, une transaction courte, un seul endroit pour la règle ; tests unitaires nominaux, d'erreur et d'autorisation.
- Événements : `on_commit` ; diffusion WebSocket **directe** pour les messages, notification via la file `notifications`, alertes et statistiques en tâches séparées (CDC §4.4, §4.5, §11.9).

## 8.2 Réglages et processus

- Réglages `base`, `local`, `public`, `admin`, `test` ; **un fichier d'environnement par service** ; clés distinctes ; le démarrage **échoue** en production si `OTP_DEBUG_CODE`, `DEBUG` ou un secret de développement est présent.
- Processus (CDC §4.3) : `caddy`, `web-api`, `realtime`, `admin`, `worker`, `worker-media`, `beat`, `postgres`, `redis-cache`, `redis-queue`, `backup`. Une seule image, plusieurs commandes. `worker-media` : sans accès Internet, une tâche à la fois, limites CPU/mémoire, ne monte que `media_tmp` et `media_public`.
- Volumes : `media_tmp`, `media_public`, `media_private` (monté **uniquement** dans `admin` et `backup`), tous distincts du volume PostgreSQL. Refus des envois au-delà de 85 % d'occupation.
- Rôles PostgreSQL `app`, `admin_app`, `migrate` créés par script d'initialisation avec droits **par colonne** là où le CDC l'exige (`users.role`, tables du personnel, tables de 2FA et de verrouillage) et déclencheurs de refus ; `audit_logs` : `INSERT` et `SELECT` seuls pour `app`, déclencheur contre `UPDATE`/`DELETE`/`TRUNCATE` sauf rôle de rétention.
- Caddy : routage par hôte du CDC §4.3, `request_body` **non imbriqués**, `encode zstd gzip`, en-têtes de sécurité (CSP, HSTS, `X-Content-Type-Options`, `Referrer-Policy`, `Permissions-Policy`), cache d'un an pour `/static/*` et `/media/*` à empreinte, HTTP/3 (UDP 443), administration en `handle @autorise` avec réponse 404 sinon, **test avec `ADMIN_ALLOWED_IPS` vide : l'hôte refuse tout**.

## 8.3 Modèle de données

- Crée **exactement** les 19 tables du CDC §9 (colonnes, types, contraintes `CHECK`, clés, index partiels, index GIN/trigramme, `ON DELETE`), y compris `daily_stats` (clé `day, metric, subject`). Aucune table supplémentaire métier. Migrations Django nettes, nommées, réversibles quand c'est possible ; extensions `pg_trgm` et `unaccent` créées par migration ; déclencheurs SQL créés par migration `RunSQL` avec leur inverse.
- Tests de contraintes : chaque `CHECK`, chaque unicité partielle, chaque règle d'intégrité du §9.23 a un test.
- Jeu de volume : commande `manage.py generer_volume` (50 000 annonces, 1 million de messages) pour les plans `EXPLAIN` du §9.22 ; marqueur `lent`.

## 8.4 Authentification, sessions, OTP (CDC §5.2, §5.3, §7.1)

- Inscription locataire en deux temps (OTP puis nom + mot de passe), connexion, mot de passe oublié, changement de mot de passe, changement de numéro (mot de passe actuel + OTP du nouveau numéro, révocation des autres appareils, message à l'ancien numéro), création manuelle du compte gérant par l'administration, suppression de compte (application **et** site), liste et révocation des appareils.
- OTP : 6 chiffres, 5 min, 5 essais, HMAC, comparaison à temps constant, plafonds (numéro, appareil, plage /24), budget **par usage** avec friction à 80 % et arrêt à 100 %, calculé depuis `otp_codes`, pays autorisés, réponse identique que le numéro existe ou non, attestation d'appareil (interface `DeviceAttestationProvider` + implémentation factice et squelette Play Integrity), Turnstile sur le site.
- Verrouillage de connexion par (numéro saisi, IP ou appareil) y compris pour numéro inconnu, réponse `401` uniforme avec `Retry-After`, plafond de 30 échecs/heure/numéro, hachage factice pour temps constant. Les compteurs vivent dans `redis-queue`, jamais dans le cache à éviction.
- JWT d'accès 15 min (`aud`, `sub`, `did`, `ver`), rafraîchissement opaque 30 jours lié à l'appareil, **rotation avec grâce de 60 s**, détection de réutilisation, liste d'appareils révoqués et `token_version` en cache avec relecture en base si le cache est vide.
- Web : sessions Django, cookie `__Host-lgsid`, CSRF, identifiant régénéré à la connexion ; administration : session séparée, `__Host-lgadm`, TOTP, codes de secours, sessions courtes, une session active par compte.
- Fournisseur SMS : interface `SmsProvider` ; implémentations `console` (écrit le code dans les journaux en local) et `generic_http` configurable (squelette complet avec signature, délai, reprises, parsing du coût) en attendant l'agrégateur retenu (`[À FOURNIR : agrégateur SMS]`).

## 8.5 Annonces et médias (CDC §7.3, §9.8, §9.9, §11.1, §11.2, §11.8)

- Assistant de création en étapes avec brouillons côté serveur ; champs obligatoires du §7.3 ; description en Markdown restreint rendue **une seule fois** (`description_html`, markdown-it-py en liste blanche puis nh3) ; mêmes règles dans l'API et sur le site ; jeu de tests commun d'entrées/sorties (`serveur/tests/fixtures/markdown_cases.json`) qui servira aussi au mobile.
- Détection des coordonnées (§11.7) dans titre, repère, adresse privée, description et messages ; mode `mask` par défaut, `flag`, `block` ; corpus de tests (numéros épelés, mélange chiffres/lettres, e-mails, liens, mots-clés) ; aucun faux positif sur les prix.
- Distance au campus par haversine à l'enregistrement ; position publique arrondie à 3 décimales.
- Pipeline média : création d'envoi avec quotas (§11.2), **protocole tus** (création, `HEAD`, `PATCH`, morceaux de 1 Mo, lecture du flux par blocs sans charger en mémoire, comptage dans `received_bytes`, expiration 24 h, reprise après coupure), contrôle `ffprobe` (conteneur mov/mp4/webm), `ffmpeg` avec format d'entrée forcé, `-protocol_whitelist file` et délai maximal, HLS 360p/720p en segments de 2 s, affiche WebP, photos WebP sans EXIF, SHA-256, détection de doublons, suppression différée, états visibles. Interface `StorageProvider` (local, squelette S3/R2) et `VideoProvider` (local ffmpeg).
- Publication : conditions du §9.23, première annonce d'un gérant en relecture par la modération, passage automatique à `published` quand tout est prêt ; fraîcheur J+7/J+10/J+14 ; « louée » avec vidéo supprimée à J+7 et conversations en lecture seule à J+30 ; archivage à J+90.

## 8.6 Fil, recherche, fiche, favoris, alertes (§7.4, §7.5, §9.22)

- Fil par curseur `(published_at, id)`, filtres et tris du CDC, recherche `unaccent` + `pg_trgm` + `tsvector`, cache de page de 60 s invalidé par compteur de version, cartes de moins de 4 Ko, plafonds de requêtes SQL par test (`assertNumQueries`), `EXPLAIN` vérifié sur le jeu de volume.
- Vues comptées via Redis (clé visiteur, expiration 26 h) puis `UPSERT` toutes les 5 min dans `daily_stats`.
- Alertes : correspondance SQL à la publication, `dedupe_key` `alert:{alerte}:{annonce}`, une seule notification par couple.

## 8.7 Messagerie temps réel (§7.6, §10.8, §4.5)

- Envoi par HTTP (idempotent par `client_msg_id`, `seq` attribué en transaction avec verrou de ligne), réception par WebSocket (`wss://…/ws/v1/?ticket=…`, groupe `user.{id}`), **diffusion directe** par `group_send` après `on_commit`, resynchronisation `after_seq` à la reconnexion, toutes les 15 s si coupé et toutes les 30 s même connecté. Le WebSocket est « au mieux » ; la garantie est portée par HTTP : écris-le dans `docs/websocket.md`.
- Événements, protection (5 connexions/utilisateur, trame de 8 Ko, 30 événements/min, fermeture sans `ping` 60 s), codes de fermeture 4401/4403/4429, présence `conversation.focus` liée à la connexion et effacée à la déconnexion et à l'arrière-plan.
- Blocage, silence, lecture seule, accusés de lecture par position, limites (30 messages/min, 20 nouvelles conversations/jour), premier message proposé.

## 8.8 Notifications, modération, administration (§7.7 à §7.10, §11.9 à §11.11)

- Une notification **par message** ; `collapse_key` pour l'affichage seul ; push par appareil via `PushProvider` (implémentations `console` et `expo`, squelette `fcm`) ; `notified_at` posé seulement après envoi, constat de lecture ou saut motivé ; rattrapage chaque minute ; rappel au gérant à 2 h ; jetons invalides désactivés.
- Signalements, file de modération, lecture d'une conversation par le personnel avec motif obligatoire **avant** affichage et ligne dans `audit_logs`, alerte au-delà de 20 lectures/jour, sanctions, suspension unique via `users.status`, notifications à l'utilisateur.
- Administration : tableau de pilotage, statistiques complètes du catalogue §7.10 (agrégations SQL en lecture seule, cache 5 min, export CSV, périodes longues via `daily_stats`), gérants (création, pièces **chiffrées Fernet** sur `media_private`, affichage déchiffré à la demande et journalisé, badge), utilisateurs, annonces, modération, journal (filtres, export CSV), paramètres et drapeaux modifiables sans redéploiement (valeur de `app_settings` prioritaire, variable d'environnement = valeur initiale), personnel (rôles, 2FA), abonnements inactifs.

## 8.9 Fournisseurs (interfaces + implémentations factices complètes)

`SmsProvider`, `PushProvider`, `StorageProvider`, `VideoProvider`, `PaymentProvider`, `DeviceAttestationProvider`. Chaque interface a : une implémentation réelle ou squelette fidèle, une implémentation `console`/factice déterministe utilisée en local et en test, des tests de contrat communs. Abonnement : tout le modèle, les services, les webhooks signés et idempotents, `can_publish`, le plan `free_v1`, les écrans masqués par `SUBSCRIPTION_ENABLED` (faux) et les endpoints en `404 feature_disabled`.

## 8.10 Observabilité, performance, résilience

Journaux JSON avec identifiant de requête propagé aux tâches ; Sentry sans données personnelles (filtre testé) ; `/healthz` et `/readyz` ; `pg_stat_statements` ; `statement_timeout` 5 s (API) / 60 s (tâches) ; limites de débit DRF par catégorie ; pagination bornée ; ETag/Cache-Control sur les lectures publiques ; `X-App-Version` tracé ; `GET /v1/app-config` complet. Sauvegardes : `pg_dump` quotidien, archivage WAL, restic pour médias, scripts de **restauration** testés (`infra/backup/restaurer.sh` + procédure dans `docs/exploitation.md`).

# 9. Site web et design : « très propre, très joli, sans ressources externes »

Le site (et l'administration) doivent donner une impression de **produit soigné et professionnel** alors qu'on n'a ni photographe, ni illustrateur, ni banque d'images. La beauté vient de : un système de design rigoureux, une typographie maîtrisée, des espaces généreux, des illustrations **vectorielles originales** générées dans le code, des états vides et de chargement travaillés, et une cohérence totale. **Aucune image externe, aucun CDN, aucune police externe.**

> **Amendement du 2026-10-17 (accord du porteur, ADR 0006) :** des **photos d'ambiance** à licence libre sont
> autorisées pour le décor seulement (§9.3, point 8). Elles sont **hébergées par Logeo** (fichiers statiques du site,
> ressources de l'application), jamais chargées depuis un site tiers : la règle « aucune image externe, aucun CDN »
> reste entière. Les annonces n'utilisent jamais de photo de banque d'images.

## 9.1 Identité

- Nom de travail **Logeo**. Logo : logotype vectoriel en SVG (mot « Logeo » en graisse 700, un pictogramme original d'une porte ouverte formant une épingle de localisation), versions claire, sombre et monochrome, favicon, icônes PWA (192/512, maskable), image de partage Open Graph générée (SVG converti en PNG 1200×630 par un script Pillow, texte « Trouve ta chambre à Parakou »).
- Ton éditorial : chaleureux, simple, rassurant, tutoiement pour les locataires et les gérants (« Trouve ta chambre », « Confirme que ta chambre est libre »), phrases courtes, jamais de jargon. Tous les textes sont dans les fichiers de traduction.

## 9.2 Jetons de design (fichier unique `serveur/web/static/css/tokens.css` ; ne jamais écrire une valeur en dur ailleurs)

**Couleurs** (échelles complètes ; vérifie les contrastes WCAG AA avec `outils/contraste.py` qui échoue en intégration continue) :
- Marque émeraude : 50 `#ECF8F3`, 100 `#D3F0E3`, 200 `#A9E1C9`, 300 `#76CCA9`, 400 `#43B287`, 500 `#1F9669`, 600 `#117853`, 700 `#0E6045`, 800 `#0D4C38`, 900 `#0A3D2E`.
- Accent terre cuite : 50 `#FEF3EE`, 100 `#FDE1D3`, 200 `#FAC0A3`, 300 `#F69771`, 400 `#EE7143`, 500 `#E4572E`, 600 `#C9421F`, 700 `#A5341A`, 800 `#852D1B`, 900 `#6D281A`.
- Neutres « sable » : 0 `#FFFFFF`, 25 `#FCFAF6`, 50 `#F8F4EC`, 100 `#F0EADF`, 200 `#E3DACA`, 300 `#CFC3AE`, 400 `#A89B84`, 500 `#81755F`, 600 `#625845`, 700 `#4A4234`, 800 `#342E24`, 900 `#211D16`, 950 `#14110C`.
- Sémantiques : succès `#1F9669`, avertissement `#D99A00`, danger `#D13B3B`, information `#2F6FDE` (chacun avec une teinte de fond claire et une teinte de texte foncée).
- Jetons sémantiques (`--bg`, `--surface`, `--surface-raised`, `--border`, `--text`, `--text-muted`, `--primary`, `--primary-hover`, `--accent`, `--focus`, etc.) définis pour le thème clair, puis redéfinis pour le thème sombre (`prefers-color-scheme` + attribut `data-theme`). Le thème sombre est de priorité S ; le sélecteur de thème de priorité C.

**Typographie :** pile système raffinée (`ui-sans-serif, system-ui, "Segoe UI", Roboto, "Helvetica Neue", Arial, "Noto Sans", sans-serif`) pour le texte. Pour les titres, une police variable auto-hébergée de 35 Ko maximum (sous-ensemble latin étendu, licence libre, `font-display: swap`, préchargée) est **autorisée si tu peux la télécharger depuis la source officielle** ; sinon pile système et note dans l'ADR (le site doit être beau dans les deux cas). Échelle : 12 / 14 / 16 / 18 / 20 / 24 / 30 / 36 / 48 / 60 px (`rem`), interlignage 1,5 (texte) et 1,15 à 1,25 (titres), crénage serré sur les grands titres, chiffres tabulaires pour les prix, longueur de ligne 60–75 caractères.

**Espacement et formes :** grille de 4 px ; rayons 8 / 12 / 16 / 24 / pilule ; ombres douces à deux couches (jamais noires pures, teintées sable) ; bordures de 1 px sable-200 ; anneau de focus de 3 px marque-300 avec décalage de 2 px ; cibles tactiles de 44 px au minimum (48 px pour les actions principales).

**Mouvement :** transitions de 150 à 250 ms, courbe `cubic-bezier(.2,.8,.2,1)` ; squelettes avec dégradé animé ; apparition des cartes en fondu ; **respect strict de `prefers-reduced-motion`**. Aucune animation qui bloque l'interaction.

**Points de rupture :** 360 (base), 640, 768, 1024, 1280.

## 9.3 Remplacer les photos : le vocabulaire visuel

1. **Motif géométrique de marque** : un motif répétitif abstrait (losanges, demi-cercles et points, inspiré des tissus wax mais original et simple) généré en SVG, utilisé en fond atténué (opacité 6–10 %) des héros, des pieds de page et des états vides, en deux teintes de la marque.
2. **Affiche de repli d'annonce** : quand une annonce n'a pas encore d'affiche (traitement en cours) ou dans les tests/seeds, génère une **affiche vectorielle déterministe** à partir du quartier et du type de chambre : dégradé choisi dans une palette de 8 couples dérivés des jetons (selon un hachage du quartier), motif de marque, pictogramme du type de chambre (lit, entrée-coucher, salon, studio) et libellé. Même rendu côté serveur (SVG en ligne ou fichier) pour les aperçus.
3. **Avatars** : initiales sur disque coloré (couleur dérivée d'un hachage de l'identifiant, 8 teintes), avec badge « Vérifié » pour les gérants.
4. **Pictogrammes** : un sprite SVG `icons.svg` d'environ 60 icônes (style trait, 1,75 px, coins arrondis) : accueil, recherche, filtre, lieu, loyer, douche, eau, électricité, clôture, vidéo/lecture, favori, message, cloche, utilisateur, plus, modifier, supprimer, partager, signaler, vérifié, horloge, calendrier, flèches, fermer, menu, réglages, tableau de bord, statistiques, alerte, envoi, coche, œil, cadenas, etc. Ces icônes sont **dessinées dans le code** (formes simples) ou reprises d'un jeu à licence libre (MIT/ISC) dont la licence est copiée dans `serveur/web/static/img/LICENCE-ICONES.txt`.
5. **Illustrations d'états vides** (SVG originaux, trait fin + aplats de marque) : aucune annonce trouvée, aucun message, aucune notification, aucun favori, aucune alerte, erreur 404, erreur 500, hors connexion, maintenance, mise à jour requise. Chacune a un titre court, une phrase et **une action**.
6. **Héros de l'accueil** : grand titre, champ de recherche central avec sélecteur de quartier, puces de filtres rapides, motif de marque en fond, trois blocs « Comment ça marche » (vidéo → message → visite) avec pictogrammes, bandeau de confiance (gérants vérifiés, vidéos réelles, aucune arnaque par téléphone), appel à l'action gérant.
8. **Photos d'ambiance (amendement du 2026-10-17, ADR 0006)** : 9 photos à licence libre (Unsplash, Pexels, Pixabay)
   pour la bannière de l'accueil (3), la présentation de l'application (4), l'écran de bienvenue (1) et la page
   « Publie ta chambre » (1). Converties en WebP (480/960/1600 px pour le site, 960 px dans l'application), licence
   et lien de chaque photo dans `docs/design/credits-photos.md`. **Jamais** pour représenter une chambre : une annonce
   sans image garde l'affiche vectorielle de repli (point 2), pour ne pas faire passer une photo de banque d'images
   pour la vraie chambre.
7. **Cartes d'annonce** : rapport 16/10, affiche (ou affiche de repli), bouton lecture centré, durée de la vidéo, prix en gras avec « FCFA / mois », puces (douche interne, eau, compteur, clôture), distance au campus, badge « Vérifié », cœur de favori, indicateur « Confirmée il y a X jours ». Aucun saut de mise en page (dimensions réservées, `aspect-ratio`).

## 9.4 Bibliothèque de composants (gabarits `{% include %}` + classes sémantiques en CSS pur, une feuille par composant dans `components/`)

Boutons (primaire, secondaire, fantôme, danger ; tailles ; états chargement/désactivé), champs (texte, numéro de téléphone avec préfixe +229, mot de passe avec afficheur, zone de texte, sélecteur, cases, interrupteurs, curseur de loyer), puces, badges, cartes, listes, onglets, accordéons, boîtes de dialogue (`<dialog>` natif), feuilles basses sur mobile, barres d'alerte, toasts (région ARIA live), squelettes, pagination par défilement infini (HTMX `hx-trigger="revealed"`), fil d'Ariane, assistant en étapes avec barre de progression, zone de dépôt de fichiers avec progression et reprise, éditeur de description (barre d'outils G / I / S / titre / listes, onglet Aperçu rendu par le serveur), bulles de messagerie (envoyé, reçu, système, statuts, séparateurs de date, bandeau « conversation en lecture seule »), éléments de notification, tuiles de statistiques et sparklines SVG, tableaux de données (administration), formulaires avec erreurs en ligne accessibles, pied de page, en-tête adaptatif.

**Page `/styleguide`** (activée en `local` seulement) : affiche **tous** les composants dans tous leurs états, en clair et en sombre. Elle sert de revue visuelle et de base aux tests d'écran.

## 9.5 Mises en page et navigation

- **Mobile (< 1024 px)** : en-tête compact, barre d'onglets en bas (locataire : Accueil, Recherche, Messages, Alertes, Profil ; gérant : Tableau de bord, Annonces, Messages, Profil), action principale flottante en bas de l'écran, feuilles basses pour les filtres.
- **Bureau (≥ 1024 px)** : en-tête complet, espace connecté avec barre latérale, messagerie en deux colonnes (liste + conversation), fiche annonce en deux colonnes (média à gauche, informations et bouton « Contacter » collant à droite).
- États systématiques sur chaque écran : chargement (squelettes), vide (illustration + action), erreur (message clair + « Réessayer »), hors connexion (bandeau).
- Pages d'erreur 400/403/404/500 et de maintenance **dessinées**, pas par défaut.

## 9.6 Accessibilité, SEO, PWA, performance

- WCAG AA : contrastes vérifiés par script, navigation clavier complète, ordre de focus logique, `aria-live` pour toasts et nouveaux messages, libellés explicites, `lang="fr"`, saut au contenu, cibles de 44 px, respect de la taille de police système, `prefers-reduced-motion`. Tests `axe` via Playwright sur toutes les pages publiques et connectées : zéro violation critique ou sérieuse.
- SEO : titres et descriptions uniques, Open Graph/Twitter, URL canoniques, `sitemap.xml`, `robots.txt`, données structurées schema.org (`Accommodation`/`Offer`), espaces connectés en `noindex`, annonces louées en `noindex` après 30 jours.
- PWA : manifeste, icônes, service worker minimal (page hors connexion et mise en cache des statiques), installation proposée après une action utile.
- Performance : HTML < 30 Ko, JavaScript initial < 60 Ko (HTMX + Alpine seuls ; hls.js et tus-js-client chargés à la demande), CSS purgée, images en `loading="lazy"` avec dimensions, `fetchpriority` sur l'image principale, préchargement du minimum. Mesure Lighthouse sur 4 pages types (accueil, recherche, fiche, messagerie) : performance ≥ 90, accessibilité ≥ 95, SEO ≥ 95, bonnes pratiques ≥ 95 ; résultats consignés dans `docs/qualite-web.md`.
- **CSP stricte** : aucun script ni style en ligne ; HTMX configuré (`allowEval` faux, `includeIndicatorStyles` faux) ; Alpine en build CSP ; `script-src 'self' https://challenges.cloudflare.com` ; l'administration a sa propre CSP. Un test Playwright échoue à la moindre violation CSP dans la console.

## 9.7 Pages et parcours à livrer (site)

Publiques : accueil ; recherche (`/chambres`, filtres en feuille, tris, résultat vide avec proposition d'alerte) ; fiche (`/chambres/{slug}`, lecteur HLS, galerie, caractéristiques, description rendue, boutons Contacter/Favori/Partager/Signaler/« Déjà louée ») ; page de quartier ; « Je suis gérant » ; CGU et confidentialité (texte `[À FOURNIR : textes juridiques]` avec gabarit propre) ; 404/500/maintenance ; `/sitemap.xml`, `/robots.txt`, `/manifest.webmanifest`.
Authentification : inscription (numéro → OTP → nom + mot de passe), connexion, mot de passe oublié, consentement CGU.
Espace locataire (`/compte`) : favoris, alertes (création/édition), messages (liste + conversation temps réel par WebSocket, repli par interrogation), notifications, profil, appareils, préférences, suppression de compte.
Espace gérant (`/pro`) : tableau de bord (indicateurs + liste « à faire »), annonces (liste par statut, modifier, confirmer, marquer louée, annuler), assistant de création en étapes **sur une page** avec éditeur à barre d'outils, aperçu, détection de coordonnées, import de vidéo reprenable (tus-js-client) avec progression, photos réordonnables, statistiques d'une annonce, messages, profil, « Mon abonnement » masqué par drapeau.
Administration (hôte séparé) : tous les écrans du CDC §12.5, habillés aux couleurs de la marque, avec cartes de statistiques et graphiques Chart.js locaux.

# 10. Le serveur est prêt pour le mobile : pack de passation (livrable de la partie 1)

Avant de terminer, tu génères `docs/mobile/` et les outils associés, de sorte que la partie 2 n'ait qu'à construire l'application :

1. **`docs/api/openapi.json`** versionné et vérifié par un test ; `make openapi` le régénère ; `docs/api/README.md` explique les conventions (CDC §10.1 : authentification, pagination par curseur, idempotence, erreurs, limites de débit, ETag, `X-App-Version`, `X-Installation-Id`, versionnement).
2. **Tous les endpoints du CDC §10.2 à §10.7** implémentés avec exemples de requêtes et de réponses dans le schéma, erreurs documentées, et **tests de contrat** (schemathesis) qui passent.
3. **`docs/mobile/passation.md`** : vue d'ensemble pour l'équipe mobile ; ordre de construction recommandé ; ce que fait le serveur pour l'application (rotation des jetons, ticket WebSocket, tus, push, `app-config`, mise à jour obligatoire, mode économie de données).
4. **`docs/mobile/flux-authentification.md`** (inscription, connexion, rafraîchissement avec grâce de 60 s, révocation, appareils, changement de numéro, suppression), **`docs/mobile/websocket.md`** (protocole complet, reprise `after_seq`, présence, codes), **`docs/mobile/envoi-video-tus.md`** (déroulé pas à pas avec exemples `curl` et reprise), **`docs/mobile/notifications-push.md`** (enregistrement du jeton, charge utile, ouverture de la conversation), **`docs/mobile/liens-profonds.md`** (`/.well-known/assetlinks.json` servi par Caddy avec un modèle `[À FOURNIR : empreinte de signature]`, schéma `logeo://`, correspondance des routes du site), **`docs/mobile/erreurs.md`** (tous les codes et comportements attendus du client), **`docs/mobile/comptes-de-test.md`** (comptes du jeu de données et leurs rôles), **`docs/mobile/markdown-description.md`** (sous-ensemble et jeu de tests `markdown_cases.json`).
5. **Outils** : `outils/ws_client.py` (client WebSocket en ligne de commande pour tester la messagerie), `outils/exporter_client_ts.sh` (génère le client TypeScript depuis OpenAPI **dans un conteneur** et l'écrit dans `mobile/src/api/` quand le dossier existera ; la commande est documentée et testée à blanc), collection `docs/api/logeo.postman_collection.json` générée depuis OpenAPI.
6. **Jeu de données de démonstration** (`make seed`) : quartiers `[À FOURNIR : liste réelle]` avec valeurs d'exemple clairement marquées fictives, 1 administrateur, 1 modérateur, 2 gérants vérifiés, 3 locataires, ~20 annonces avec vidéos courtes générées par ffmpeg (motifs vidéo synthétiques, pas de contenu tiers) et affiches de repli, conversations et notifications d'exemple.
7. **Fournisseurs `console`** : en local, les OTP et push s'affichent dans une page de développement `/dev/boite-de-reception` (activée en `local` seulement) qui liste les derniers codes OTP et notifications « envoyés », pour que le mobile se teste **sans SMS ni push réels**.
8. **`docs/mobile/checklist-partie-2.md`** : liste de ce qui reste à construire côté mobile avec, pour chaque écran du CDC §12.2 et §12.3, le point d'entrée d'API correspondant.

# 11. Documentation à générer (en français, claire, avec exemples exécutables)

- `README.md` : en 5 commandes, le projet tourne ; captures décrites ; liens.
- **`docs/guide-installation-pas-a-pas.md`** : guide pour quelqu'un qui n'a jamais lancé le projet — prérequis par système (Windows avec WSL2, macOS, Linux), installation de Git et Docker, clonage, `cp .env.example .env`, `make hooks`, `make up`, `make migrate`, `make seed`, `make css`, URLs locales (`www.localhost`, `api.localhost`, `pilotage.localhost`, `/styleguide`, `/dev/boite-de-reception`, documentation OpenAPI), comptes de test, connexion à l'administration avec 2FA de développement, lancement des tests, **dépannage** (ports occupés, mémoire Docker, ffmpeg, droits de fichiers, WSL2) avec les messages d'erreur réels et leurs remèdes.
- **`docs/premiere-execution.md`** : de l'archive décompressée au premier `make fumee` réussi (décompresser, `outils/diagnostic.sh`, `cp .env.example .env`, `make hooks`, `make up`, `make migrate`, `make seed`, `make fumee`), avec **la sortie attendue de chaque commande**, ce qui n'a pas pu être exécuté pendant la génération (renvoi vers `docs/verification.md`), puis création du dépôt GitHub, premier push (`LOGEO_PREMIER_PUSH=1`) et protection de branche.
- **`docs/aide-ia-depannage.md`** : texte prêt à coller dans une IA quand une commande échoue (contexte du projet en 10 lignes, les commandes de diagnostic à exécuter, les informations à fournir : sortie complète, système, version de Docker), plus tableau des erreurs probables au premier lancement (images non construites, ports occupés, droits des volumes, extensions PostgreSQL, ffmpeg absent, variables manquantes) avec remèdes.
- `docs/environnement-generation.md`, `docs/verification.md` (matrice exécuté / simulé / non exécuté).
- `docs/architecture.md` (schémas, flux, processus), `docs/securite.md` (modèle de menaces, séparation de l'administration, OTP, secrets, rotation des clés), `docs/websocket.md`, `docs/media.md`, `docs/design-system.md` (jetons, composants, règles, comment ajouter un composant), `docs/qualite-web.md` (mesures Lighthouse/axe/budgets), `docs/exploitation.md` (supervision, alertes, sauvegardes et **restauration pas à pas**, rotation des secrets, incidents types), `docs/contribuer.md` (format Git, hooks, protection de branche pas à pas, revue, fusion), `docs/glossaire.md`, `docs/a-fournir.md` (tout ce que l'équipe doit fournir), `docs/avancement.md`, `docs/adr/` (une note par décision), `docs/api/`, `docs/mobile/`.
- **`docs/deploiement-vps-pas-a-pas.md`** : du VPS vierge à la production — achat/choix du VPS, DNS (`www`, `api`, `pilotage`), `infra/vps/bootstrap.sh`, pare-feu (80, 443 TCP, 443 UDP, SSH), clés SSH, variables de production fichier par fichier, premier déploiement, HTTPS, VPN ou liste blanche de l'administration, création du premier administrateur en ligne de commande, activation de la 2FA, sauvegardes externes et **test de restauration**, mise à jour, retour arrière, supervision externe de `/readyz`. Chaque étape a sa commande exacte et son résultat attendu.
- Docstrings courtes sur les services et les fournisseurs ; commentaires seulement pour le « pourquoi ».

# 12. Phases de travail (enchaîne-les ; rapport à la fin de chacune)

Pour **chaque phase** : (a) relire les sections du CDC concernées ; (b) écrire les tests **en même temps que le code** selon le §12 bis ; (c) `make verifier` au vert ; (d) mettre à jour `docs/` et `docs/avancement.md` ; (e) commits conformes au §6 sur une branche `feat/…` (fusionnée dans `main` du dépôt local de génération à la fin de la phase) ; (f) `docs/verification.md` mis à jour ; (g) **archive `logeo-partie1.zip` régénérée et envoyée** (§0 bis.7) ; (h) rapport court : livré, tests exécutés (nombre, résultat), non exécuté, décisions (ADR), `[À FOURNIR]` ouverts, risques.

- **Phase 0 — Fondations** : dépôt, arborescence, `AGENTS.md`, hooks et contrôles du §6 (avec tests des scripts : cas valides et invalides), Docker Compose complet (tous les services démarrent), réglages `base/local/public/admin/test`, rôles PostgreSQL, Caddy local, import-linter, CI, `outils/construire_css.py`, jetons de design, `/styleguide` initial, `/healthz` `/readyz`, ADR 0001. Critère : les neuf cas de `outils/tester_hooks.sh` (§6.5) se comportent comme attendu, sortie jointe ; la pile Compose est écrite et relue (son démarrage réel est « non exécuté » si Docker est absent du bac à sable, et vérifié par `make fumee` chez l'utilisateur).
- **Phase 1 — Comptes** : modèles `users`, `otp_codes`, `devices`, `gerant_profiles`, `audit_logs`, `app_settings` ; OTP, inscription, connexion, rotation des jetons, appareils, création manuelle des gérants par l'administration, suppression de compte, mot de passe oublié, changement de numéro ; pages web d'authentification ; administration : hôte séparé, connexion, 2FA, axes, création de gérants, rôles ; tests de sécurité du §5 (CDC §14.2 scénarios 1, 2, 13, 14).
- **Phase 2 — Annonces** : `districts`, `listings` ; champs obligatoires, Markdown restreint + aperçu, détection de coordonnées, brouillons, distance, règles de publication ; assistant web ; API `/pro/listings`.
- **Phase 3 — Médias** : `listing_media` ; tus, quotas, ffprobe/ffmpeg durcis, HLS, photos WebP, états, suppression différée, `StorageProvider`, affiche de repli ; zone de dépôt web avec reprise. Mesure du transcodage consignée.
- **Phase 4 — Fil, recherche, fiche** : index et recherche, cache, fil, filtres, tris, fiche, lecteur HLS, favoris, vues et `daily_stats`, pages publiques et SEO, `/styleguide` complet, accueil finalisé, mesures Lighthouse.
- **Phase 5 — Messagerie** : `conversations`, `messages`, séquence, idempotence, API, WebSocket, resynchronisation, lecture, blocage, silence ; pages web ; tests de coupure et de charge à petite échelle.
- **Phase 6 — Notifications et alertes** : `notifications`, centre, push (factice + Expo), logique §11.9 complète, rattrapage, rappels, `alerts` et correspondance, préférences ; boîte de développement.
- **Phase 7 — Modération, tableau de bord, fraîcheur** : `reports`, `moderation_actions`, file, lecture journalisée, sanctions, tableau de bord du gérant, tâches planifiées (fraîcheur, louée, archivage, rétention).
- **Phase 8 — Statistiques, paramètres, abonnement inactif, PWA** : catalogue complet §7.10, paramètres et drapeaux, `app-config`, mise à jour obligatoire, `subscriptions`, `payments`, webhooks, écrans masqués, PWA, thème sombre.
- **Phase 9 — Durcissement et passation** : charge k6 à 3× la capacité (ENF-CAP-01), `EXPLAIN` des huit requêtes, ZAP passif, audit des dépendances, test de restauration complet, accessibilité, recette des scénarios du CDC §14.2 (sauf ceux qui exigent l'application mobile : ils sont listés dans `docs/mobile/checklist-partie-2.md`), pack de passation mobile (§10), vérification finale de la documentation : **si Docker est disponible**, exécution réelle du guide pas à pas sur un environnement vierge (`docker compose down -v` puis suivre le guide à la lettre ; corrige le guide s'il ment) ; **sinon**, relecture croisée de chaque commande du guide contre les fichiers réels (noms de cibles, de services, de variables, de ports) par un script `outils/verifier_docs.py`, et mention « non exécuté » dans la matrice.

# 12 bis. Tests : unitaires, intégration, API, sécurité, bout en bout (obligatoires)

**Principes.** Les tests s'écrivent avec chaque fonctionnalité, jamais après. Ils sont rapides, déterministes (temps figé avec `time-machine`, hasard fixé), indépendants (ordre aléatoire avec `pytest-randomly`, parallèle avec `pytest-xdist`) et lisibles (un test = un comportement, nom en français explicite). **Chaque exigence M et S** du CDC est couverte par au moins un test, qui cite son identifiant avec le marqueur `@pytest.mark.exigence("EF-MSG-03")` ; `outils/tracabilite.py` lit ces marqueurs pour produire `docs/tracabilite.md`. Chaque bogue corrigé reçoit un test de non-régression. Un test qui échoue n'est jamais supprimé ni affaibli ; un test instable est réparé ou, en dernier recours, marqué `lent` avec la raison.

**Marqueurs :** `unitaire`, `integration`, `api`, `ws`, `securite`, `e2e`, `lent`, `pg` (exige PostgreSQL réel), `ffmpeg`, `exigence(id)`. **Commandes :** `make test` (tout sauf `lent` et `e2e`), `make test-unitaires`, `make test-integration`, `make test-e2e`, `make test-securite`, `make test-lent`, `make couverture` (rapport HTML + seuil).

**Arborescence :** `serveur/apps/<app>/tests/unitaires/` et `…/integration/` ; transverses dans `serveur/tests/{securite,contrats,e2e,charge,fixtures}/`. `conftest.py` racine fournit : clients API par rôle (visiteur, locataire, gérant, modérateur, administrateur), fabriques `factory_boy` pour les 19 tables, `boite_otp` (lit les codes envoyés par le fournisseur `console`), fournisseurs factices, `temps` (`time-machine`), `canal_ws` (communicateur Channels), `video_synthetique` et `photo_synthetique` (générées par ffmpeg `lavfi` et Pillow, aucun fichier tiers), `cas_markdown` (jeu partagé `markdown_cases.json`).

## Niveau A — Tests unitaires (sans réseau, sans base quand c'est possible)

- **Détection des coordonnées** : corpus (numéros à 8 et 10 chiffres avec espaces, points, tirets, +229, 00229 ; numéros épelés ; mélanges chiffres/lettres ; e-mails ; liens ; mots-clés) ; **aucun prix** (« 25 000 FCFA », « 25000 F », « 3 mois d'avance ») ne déclenche ; tests de propriétés `hypothesis` (tout numéro inséré dans un texte aléatoire est détecté ; tout texte de prix aléatoire ne l'est pas) ; comportement des modes `mask`, `flag`, `block`.
- **Texte enrichi** : jeu commun d'entrées/sorties ; propriétés : jamais de balise `script`, de lien, d'image, d'attribut d'événement en sortie, quel que soit le texte d'entrée ; sortie identique pour deux rendus.
- **Calculs** : haversine (cas connus), arrondi de la position publique, délai médian et taux de réponse, déduplication des vues, formatage FCFA et dates (fuseau `Africa/Porto-Novo`), validation des numéros béninois (8 chiffres, 10 chiffres préfixe 01, formats invalides).
- **Sécurité pure** : HMAC d'OTP et comparaison à temps constant ; paramètres Argon2id ; création et validation de JWT (expiration, `aud`, `ver`, `did`, signature, clés distinctes site/administration) ; rotation du jeton de rafraîchissement avec **grâce de 60 s** et révocation au-delà ; plafonds d'OTP (numéro, appareil, plage /24), budget par usage, friction à 80 %, arrêt à 100 % ; verrouillage de connexion par couple (numéro, IP ou appareil) y compris numéro inconnu ; chiffrement Fernet des pièces (aller-retour, échec sans clé).
- **Machines à états** : annonce (§11.1), média (§11.2), vérification d'un gérant (§11.3), signalement (§11.4), abonnement (§11.5) — **toutes les transitions valides et toutes les transitions invalides** (paramétrées).
- **Fournisseurs** : tests de contrat communs (une même suite exécutée contre chaque implémentation) pour `SmsProvider`, `PushProvider`, `StorageProvider`, `VideoProvider`, `PaymentProvider`, `DeviceAttestationProvider`.
- **Outils** (`outils/`) : `verifier_commit`, `verifier_branche`, `verifier_noms`, `verifier_hygiene`, `contraste`, `construire_css`, `tracabilite`, `verifier_docs` — cas valides et invalides.

## Niveau B — Tests d'intégration (PostgreSQL réel, tâches immédiates, Channels en mémoire)

- **Base de données** : migrations appliquées depuis zéro ; `makemigrations --check` ; chaque `CHECK`, chaque unicité partielle, chaque clé étrangère et règle `ON DELETE` (dont `moderation_actions.target_message_id` en `SET NULL`) ; déclencheurs d'audit (`UPDATE`, `DELETE`, `TRUNCATE` refusés) ; **droits des rôles** (connexions réelles avec `app`, `admin_app`, `migrate` : `app` ne peut ni écrire `users.role` pour un rôle du personnel, ni modifier `audit_logs`).
- **Services transactionnels** : **concurrence** (plusieurs envois simultanés dans une conversation → `seq` sans trou ni doublon ; test avec transactions réelles et threads) ; idempotence (`client_msg_id`, `Idempotency-Key`) ; règles de publication du §9.23 ; quotas et plafonds (annonces actives, alertes, conversations par jour, messages par minute).
- **Événements et notifications** : après `on_commit`, diffusion WebSocket et création de **une notification par message** ; logique complète du §11.9 : push supprimé par la présence puis **rattrapage** si le message n'est pas lu, `notified_at` posé seulement après envoi/lecture/saut motivé, silence et catégorie coupée, jetons invalides désactivés, 5 reprises ; alertes (une seule notification par couple alerte/annonce, même après republication).
- **Tâches planifiées** (temps figé) : fraîcheur J+7, J+10, J+14 ; louée → vidéo supprimée à J+7, conversations en lecture seule à J+30, archivage à J+90 ; annulation avant échéance ; sanctions échues ; vidage des compteurs de vues ; envois abandonnés ; purge de rétention (OTP, pièces, conversations) **avec vérification de toutes les colonnes anonymisées** (§9.23) ; agrégats nocturnes dans `daily_stats`.
- **Pipeline média** (fichiers synthétiques) : `ffprobe` accepte mov/mp4/webm et **refuse** faux formats, faux MP4, playlists piégées, durées hors limites, résolution trop basse ; HLS 360p/720p produit et lisible ; photos WebP sans EXIF ; SHA-256 et doublons ; délai maximal ; quotas d'envoi et refus à 85 % de disque ; **tus** : création, `HEAD`, `PATCH`, reprise après coupure, dépassement de taille, expiration, flux lu par blocs.
- **Recherche et fil** : accents et fautes, filtres, tris, pagination par curseur sans doublon ni trou même pendant des publications ; cache du fil et invalidation ; plafonds de requêtes SQL (`assertNumQueries`) pour chaque point d'entrée critique ; plans `EXPLAIN` des huit requêtes du §9.22 sur le jeu de volume (`lent`).
- **Facturation inactive** : `can_publish`, drapeau faux, webhooks signés, idempotence par identifiant d'événement, `404 feature_disabled`.
- **Suppression de compte** : anonymisation complète, conservation des lignes de modération et de journal.

## Niveau C — Tests d'API et de contrat

- **Matrice endpoint × rôle générée automatiquement** à partir du schéma : chaque point d'entrée du §10 est testé pour visiteur, locataire, gérant, modérateur, administrateur et jeton OTP, avec résultats attendus (200/201, 401, 403 `wrong_audience`, 404) ; **un endpoint sans règle d'accès explicite fait échouer le test**.
- Validation des entrées, format d'erreur unique, pagination, `ETag` et `304`, limites de débit (`429` + `Retry-After`), `X-App-Version` inférieur au minimum → `426`, `GET /app-config`, ressources non visibles → 404 (jamais 403).
- **Contrats `schemathesis`** sur `openapi.json` (cas nominaux et limites) ; test que `docs/api/openapi.json` est **à jour** avec le code ; compatibilité additive (`oasdiff` en CI).
- **Aucune fuite du numéro du gérant** : parcours de toutes les réponses publiques, de toutes les pages publiques, des aperçus de lien et des journaux.

## Niveau D — Temps réel (`ws`)

Ticket à usage unique, expiré, rejoué, mauvaise origine ; groupes `user.{id}` multi-appareils ; ordre et absence de doublon ; resynchronisation `after_seq` après coupure et **périodiquement même connecté** ; **perte volontaire d'une diffusion** → le message arrive quand même par resynchronisation ; présence liée à la connexion (déconnexion et arrière-plan l'effacent) ; codes de fermeture 4401, 4403, 4429 ; limites (5 connexions par utilisateur, trame de 8 Ko, 30 événements par minute, fermeture après 60 s sans `ping`) ; `conversation.read`, `conversation.updated`, `notification.new`.

## Niveau E — Tests de sécurité (`securite`)

Autorisation et IDOR ; CSRF par requêtes inter-origines ; **XSS** (corpus de charges rejoué sur messages, description, titres, noms, repères) ; injection dans les filtres et la recherche ; **séparation de l'administration** (routes introuvables sur www et api et inversement, cookies et clés distincts, jeton du site invalide sur l'administration, comptes locataire/gérant refusés sur l'administration, comptes du personnel refusés sur le site et l'API, compte sans 2FA limité à sa configuration, 5 échecs verrouillent le compte **quelle que soit l'adresse IP**, hôte d'administration refusant tout quand `ADMIN_ALLOWED_IPS` est vide) ; **pompage d'OTP** (scénario d'abus : refus, friction, alerte) ; **énumération** (réponses identiques et temps comparables pour numéro connu et inconnu, à l'inscription, à la connexion et à la réinitialisation) ; rejeu de jetons et réutilisation du jeton de rafraîchissement hors grâce ; en-têtes (CSP sans `unsafe-inline`, HSTS, cookies `__Host-`, `Referrer-Policy`) ; filtre des journaux et de Sentry (numéros et codes masqués) ; pièces d'identité illisibles sans clé ; envoi de fichiers piégés ; secrets de développement refusés au démarrage en production.

## Niveau F — Site web et bout en bout (`e2e`, Playwright Python + axe)

- **Pages** : chaque URL du §10.9 répond, aucun gabarit en erreur, **aucune violation CSP dans la console**, `axe` sans violation critique ou sérieuse, poids mesurés (HTML < 30 Ko et JavaScript initial < 60 Ko compressés), contraste des jetons (`outils/contraste.py`), formulaires de base utilisables **sans JavaScript**.
- **Parcours complets** (deux contextes de navigateur pour la messagerie) : inscription par OTP → connexion → recherche → fiche → contacter → message reçu en temps réel par le gérant → réponse → accusé de lecture ; gérant : création d'annonce avec texte enrichi et aperçu, **import d'une vidéo synthétique avec coupure réseau simulée puis reprise**, publication, « louée » ; favoris ; alerte ; suppression de compte ; administration : connexion + 2FA, création d'un gérant, traitement d'un signalement, lecture d'une conversation avec motif, changement d'un paramètre.
- **Captures d'écran** des pages types à 360, 768 et 1280 px en clair et sombre, **examinées** pendant la génération pour corriger le design ; non-régression visuelle avec seuil tolérant seulement si l'environnement de l'utilisateur le permet.

## Niveau G — Scénarios de recette (CDC §14.2)

Chaque scénario devient un test nommé `test_scenario_NN_…` (marqueur `exigence`). Ceux qui supposent l'application mobile (1, 2, 3, 5, 12, 15 en partie) sont **joués par un client HTTP et WebSocket qui simule l'application** (`httpx`, communicateur Channels, envoi tus par l'API) ; seule la partie visuelle de l'application reste à vérifier en partie 2 et est listée dans `docs/mobile/checklist-partie-2.md`.

## Niveau H — Charge et performance (`lent`)

Scripts k6 écrits pour : lecture du fil et de la fiche à 50 requêtes par seconde, envoi et diffusion de messages à 200 par minute avec 500 connexions WebSocket, transcodage pendant la charge. Exécutés si l'environnement le permet, sinon livrés et marqués « non exécuté » avec la commande. Budgets (ENF-PERF-01 à 09) exprimés en seuils k6 qui font échouer l'exécution.

## Seuils et rapport

Couverture globale des services ≥ 85 % ; ≥ 95 % sur comptes, authentification, OTP, permissions et messagerie (échec de `make couverture` en dessous). À chaque fin de phase, le rapport donne : nombre de tests **par niveau**, taux de réussite, couverture, tests ignorés avec leur raison. Les suites attendues par phase : phase 0 (outils, hooks, contraste, CSS) ; phase 1 (niveaux A, B, C, E sur comptes et administration) ; phase 2 (A, B, C annonces, texte enrichi, détection) ; phase 3 (B média et tus, E fichiers piégés) ; phase 4 (B recherche et fil, C, F pages publiques, accessibilité) ; phase 5 (B concurrence, D, F messagerie) ; phase 6 (B notifications et rattrapage, alertes) ; phase 7 (B tâches planifiées, E modération, F administration) ; phase 8 (B abonnement, statistiques) ; phase 9 (G, H, rejeu complet de tous les niveaux, traçabilité à 100 %).

# 13. Qualité : critères de réussite globaux

- `make verifier` passe à 100 % pour tout ce qui est exécutable dans le bac à sable (le reste est consigné « non exécuté » avec sa commande de validation) ; couverture conforme au §12 bis (≥ 85 % global, ≥ 95 % sur comptes, authentification, OTP, permissions, messagerie) ; tous les identifiants `EF-…`/`ENF-…` de priorité M et S de la partie 1 sont couverts par au moins un test ou une vérification documentée ; un fichier `docs/tracabilite.md` (généré par `outils/tracabilite.py`) liste chaque exigence, son statut et son test.
- Aucun script ou style en ligne ; zéro violation `axe` critique ; budgets de poids respectés ; Lighthouse conforme (§9.6).
- Aucune fuite du numéro du gérant (test qui parcourt toutes les réponses publiques et les pages).
- Le guide pas à pas est cohérent avec les fichiers réels (vérifié par script) et exécuté pour de vrai là où le bac à sable le permet ; le pack de passation mobile est complet (§10) ; `make fumee` est prêt ; la matrice `docs/verification.md` est honnête.
- Le mot « backend » n'apparaît dans aucun chemin ni identifiant (hors exceptions listées) ; `AGENTS.md` est à jour.

# 14. Rapport final (dernier message)

Un message court : (1) ce qui est livré ; (2) comment lancer (`make up` + URLs + comptes) ; (3) tableau des exigences M/S non terminées avec la raison ; (4) la liste `[À FOURNIR]` ; (5) les risques ouverts ; (6) la liste exacte des fichiers du pack de passation mobile ; (7) la commande pour vérifier que tout est sain (`make fumee` puis `make verifier`) ; (8) **la matrice exécuté / simulé / non exécuté** en tableau court. L'archive finale est jointe. Pas de recap des étapes.

# 15. Interdits récapitulatifs

Affirmer qu'une commande a réussi sans l'avoir exécutée ; recopier des fichiers entiers dans la conversation au lieu de les écrire dans le bac à sable ; livrer une archive sans `.git` ni historique conforme ; nommer un dossier ou un module « backend » ; mettre de la logique métier dans une vue, un sérialiseur, une tâche ou un consommateur ; ajouter Node, Next.js, un CDN, une police ou une image externes ; script ou style en ligne ; écrire une couleur/taille/ombre en dur hors jetons ; exposer le numéro d'un gérant ; stocker un secret dans le dépôt ; contourner un hook (`--no-verify`) ; affaiblir un test pour qu'il passe ; livrer un stub à la place d'une exigence M ; inventer des données réelles ; modifier le CDC (propose un ADR à la place) ; terminer sans avoir exécuté les commandes que tu affirmes avoir réussies.

---

<!-- DEBUT CDC -->

# PARTIE B — CAHIER DES CHARGES DÉVELOPPEUR DE LOGEO (référence, à copier dans `docs/cahier-des-charges.md`)

*Dans cette spécification, le code serveur vit dans `serveur/` (le prompt, Partie A, fait foi pour l'arborescence exacte, §5). Sections retirées de l'original pour alléger : sprints, risques, glossaire, couverture et sommaire. Les figures ne sont pas reproduites ; leur contenu est décrit par les tableaux et listes.*

## 1. Objet du document et décisions arrêtées

Ce document est la référence unique pour construire Logeo : quoi développer, avec quelles technologies, sur quelles données, selon quelles règles, et comment le système tient la charge, résiste aux attaques et évolue sans casser. Les exigences portent un identifiant stable (par exemple `EF-MSG-03`) à citer dans les tickets et les tests. Priorités : **M** (indispensable au lancement), **S** (attendu, sacrifiable en dernier recours), **C** (si le temps le permet).

### Décisions arrêtées

| Décision de l'équipe | Conséquence pour le développement |
|---|---|
| Inscription par OTP, connexion par numéro + mot de passe, réinitialisation par OTP | L'OTP n'est envoyé que dans trois cas (inscription, réinitialisation, changement de numéro) : le coût des SMS reste borné (§5.3, §16). |
| Aucun contact hors plateforme : tout passe par la messagerie de Logeo | Messagerie temps réel dès le lancement, une notification par message reçu, numéro du gérant jamais exposé, détection des coordonnées. |
| Messagerie en texte seul : ni vocal, ni image, ni vidéo pour l'instant | Une seule table de messages sans pièce jointe ; l'ajout ultérieur n'oblige pas à modifier l'existant (§6.4). |
| Une seule application mobile (React Native), expérience selon le rôle | Un seul binaire, deux espaces (locataire, gérant) choisis après la connexion. |
| Un seul site web en gabarits Django (pas de Next.js, pas de Node en production) | Rendu serveur, HTMX et Alpine.js servis comme fichiers statiques ; CSS pur assemblé par un script (voir §4 du prompt). |
| Espace d'administration complètement séparé des pages publiques | Autre nom d'hôte, autre processus, autres réglages, aucune route d'administration sur le site public, 2FA et protection contre la force brute (§5.1). |
| Hébergement centralisé, tout en local d'abord mais prêt pour l'hébergement | Un seul serveur (VPS) avec Docker Compose au départ ; chemin de montée en charge sans refonte (§6.3). |
| Application et site lancés ensemble, même base, communication entre plateformes | Une logique métier unique, appelée par l'API (mobile) et par les vues du site ; un locataire sur le web dialogue avec un gérant sur mobile. |
| Mobile first | Écrans conçus dès 360 px ; budgets de poids et de latence mesurés sur un Android d'entrée de gamme en 3G. |
| Les gérants importent leurs propres vidéos | Envoi reprenable, contrôle, transcodage HLS sur le serveur (§4.5). |
| Description en texte enrichi, informations clés en champs obligatoires | Sous-ensemble Markdown assaini côté serveur, mêmes règles partout. |
| Comptes gérants créés par l'administration après vérification | Aucune inscription publique de gérant. |
| Abonnement prévu, non lancé | Tables, services et écrans livrés mais désactivés par un drapeau (§7.11). |
| Modèle de données réduit à 19 tables | Fusion des tables secondaires, suppression de PostGIS et des pièces jointes (§9). |

> **Principe de conception.** À valeur égale, on choisit la solution la plus simple à exploiter pour deux développeurs, la plus sobre en octets pour un téléphone modeste en 3G, et celle qui garde les échanges dans Logeo. Aucune brique n'est ajoutée sans un besoin mesurable.

## 2. Contexte, objectifs et périmètre

### Contexte et valeur

À Parakou, démarcheurs et gérants publient leurs chambres dans des groupes WhatsApp, des statuts ou sur Facebook : la découverte est fermée, un étudiant qui arrive en ville ne voit rien. Logeo rassemble les chambres libres en un lieu ouvert, présentées en courtes vidéos, filtrables par quartier et par distance au campus, avec des gérants vérifiés à la main et une messagerie intégrée. Le public visé est large (étudiants, puis tout chercheur de chambre) et l'usage est mobile avant tout.

### Objectifs mesurables

Cibles indicatives à calibrer avec le démarcheur partenaire ; le back-office les affiche (EF-ADM-04).

| Indicateur | Cible indicative | Source dans les données |
|---|---|---|
| Chambres actives de gérants vérifiés | 40 | `listings` publiées |
| Comptes locataires (numéro vérifié) | 300 à 3 mois | `users` rôle client |
| Délai médian de première réponse d'un gérant | moins de 2 heures | `conversations.first_reply_at` |
| Locations conclues via Logeo | 20 à 3 mois | `listings.rented_at` |
| Locataires actifs sur les 30 derniers jours (part des inscrits) | 30 % | `users.last_seen_at`, `daily_stats` |

### Dans le périmètre de la première version

- Comptes locataires (OTP puis mot de passe), mode invité, comptes gérants créés par l'administration.
- Publication d'annonces : champs obligatoires, description enrichie, vidéo importée, photos.
- Fil, recherche, filtres, tri par proximité du campus, fiche, favoris, alertes.
- Messagerie texte en temps réel avec notification de chaque message reçu.
- Tableau de bord du gérant ; fraîcheur des annonces (relances, masquage, « déjà louée »).
- Signalement, modération et administration séparée avec statistiques complètes.
- Pages web publiques indexables et partageables.
- Architecture d'abonnement complète mais inactive.

### Hors périmètre de la première version

- Paiement réel et facturation (architecture prête, lancement reporté).
- Pièces jointes, messages vocaux, appels et images dans la messagerie.
- Affichage sur une carte et recherche par rayon autour de la position de l'utilisateur (les coordonnées sont déjà stockées ; voir §6.4).
- Publication sur l'App Store iOS (le code le permet ; voir §17).
- Autres langues que le français, autres villes que Parakou (le modèle est prêt, §6.4).
- Notifications Web Push sur le site (priorité C, §7.7).

## 3. Surfaces, rôles et permissions

### 3.1 Les trois surfaces

Trois surfaces partagent la même base de données et la même logique métier. Les codes ci-dessous servent dans tout le document.

| Code | Surface | Technologie | Utilisateurs et rôle |
|---|---|---|---|
| APP | Application mobile Logeo | React Native (Expo), TypeScript | Locataires et gérants. Après la connexion, l'application affiche l'espace locataire ou l'espace gérant selon le rôle du compte. Hôte : api. |
| WEB | Site web | Gabarits Django, HTMX, Alpine.js, CSS pur | Visiteurs, locataires, gérants. Pages publiques indexables, espace locataire, espace gérant (publier depuis un ordinateur). Hôte : www. |
| ADM | Administration | Django (réglages et URL séparés), thème moderne | Administrateurs et modérateurs : vérification des gérants, modération, statistiques complètes, paramètres. Hôte dédié, non public. |

### 3.2 Une base, des surfaces qui communiquent

- **Un compte, plusieurs surfaces.** Même numéro et même mot de passe sur APP et WEB. Un compte locataire n'ouvre pas l'espace gérant et inversement ; les comptes du personnel n'existent que sur ADM et ne peuvent pas se connecter ailleurs.
- **Messagerie commune.** Une conversation ouverte sur WEB apparaît en temps réel sur APP, et réciproquement ; les accusés de lecture se synchronisent.
- **Une seule logique métier.** L'API (pour APP) et les vues du site (pour WEB) appellent les mêmes services Python (§4.4) : une règle corrigée l'est partout, la parité n'est pas à maintenir à la main.
- **Parité par conception.** Chaque exigence du §7 indique ses surfaces ; une fonction présente sur une seule surface doit être justifiée.

### 3.3 Rôles

| Rôle | Création du compte | Description |
|---|---|---|
| Visiteur | Aucune | Consulte annonces, vidéos et fiches ; recherche et filtre. |
| Locataire | Auto-inscription : numéro + OTP, puis mot de passe | Visiteur + favoris, alertes, messagerie, signalements. |
| Gérant (ou démarcheur) | Créé par l'administration, mot de passe attribué puis modifiable | Publie et gère ses annonces, répond, suit ses statistiques. Badge « Vérifié ». |
| Modérateur | Créé par un administrateur (ADM) | Traite les signalements, lit les conversations (journalisé), masque, avertit, suspend. |
| Administrateur | Créé en ligne de commande (premier) puis par un administrateur | Tout ce que fait le modérateur + création et vérification des gérants, bannissement, paramètres, statistiques complètes, plans. |

### 3.4 Matrice des permissions

| Action | Visiteur | Locataire | Gérant | Modérateur | Admin |
|---|---|---|---|---|---|
| Consulter annonces, vidéos, fiches | Oui | Oui | Oui | Oui | Oui |
| Favoris, alertes | — | Oui | — | — | — |
| Ouvrir une conversation depuis une fiche | — | Oui | — | — | — |
| Répondre dans une conversation dont on est participant | — | Oui | Oui | — | — |
| Publier, modifier, marquer louée ses annonces | — | — | Oui | — | — |
| Voir ses statistiques | — | — | Oui | — | Globales |
| Signaler une annonce, un message, un utilisateur | — | Oui | Oui | — | — |
| Lire une conversation dont on n'est pas participant | — | — | — | Journalisé | Journalisé |
| Masquer un message ou une annonce, avertir | — | — | — | Oui | Oui |
| Suspendre un compte, locataire ou gérant (30 jours maximum) | — | — | — | Oui | Oui |
| Suspension longue, bannissement, rétablissement | — | — | — | — | Oui |
| Créer et vérifier un gérant, attribuer le badge | — | — | — | — | Oui |
| Paramètres, drapeaux, comptes du personnel | — | — | — | — | Oui |
| Statistiques complètes | — | — | — | Modération | Oui |
| Journal d'activité | — | — | — | Lecture | Oui |

### 3.5 Fonctionnalités par surface

| Fonctionnalité | APP | WEB | ADM |
|---|---|---|---|
| Inscription, connexion, mot de passe oublié | Oui | Oui | Connexion + 2FA |
| Fil, recherche, filtres, fiche, favoris, alertes (locataire) | Oui | Oui | Lecture |
| Messagerie temps réel et centre de notifications | Oui | Oui | Lecture (modération) |
| Notifications push | Oui | Web Push (C) | — |
| Création et édition d'annonce, import vidéo (gérant) | Oui | Oui | Édition de secours |
| Tableau de bord du gérant | Oui | Oui | Vue globale |
| Fraîcheur : confirmer, marquer louée (gérant) | Oui | Oui | Oui |
| Signalement | Oui | Oui | Traitement |
| Vérification des gérants, modération, journal, paramètres | — | — | Oui |
| Statistiques complètes | — | — | Oui |
| Pages publiques indexables, partage, PWA | — | Oui | — |

### 3.6 Principes mobile first

- **Conception à partir de 360 px** : une colonne, navigation par onglets en bas, action principale à portée du pouce. Le site s'enrichit à partir de 768 px (deux colonnes) puis 1024 px (barre latérale, messagerie liste/détail).
- **Données comptées** : images WebP dimensionnées, vidéo adaptative HLS démarrant en basse qualité, mode économie de données (affiche seulement).
- **Réseau instable** : brouillons enregistrés, envois reprenables, messages en file locale, dernier contenu en cache.
- **Appareil de référence** pour toutes les mesures : un Android d'environ 60 000 FCFA (2 Go de mémoire), réseau limité à une vitesse 3G.

## 4. Architecture technique

### 4.1 Vue d'ensemble

Logeo est un **monolithe modulaire** Django : un seul code, une seule base PostgreSQL, déployé en plusieurs processus spécialisés. L'application mobile parle à l'API REST, le site est rendu par Django, l'administration est un processus Django distinct. Les traitements lents (vidéo, notifications, alertes) passent par des files Celery. Tout service externe (SMS, push, paiement, stockage) est derrière une interface remplaçable. Ce choix, plutôt que des microservices, est délibéré : à deux développeurs et à l'échelle visée, il donne la fiabilité d'une transaction unique et une exploitation simple, tout en gardant des frontières nettes pour évoluer (§4.4, §6).

*Figure 1 — Architecture d'ensemble (un serveur au départ, chaque couche remplaçable ou duplicable ensuite). (schéma non reproduit ici : voir les listes et tableaux de la section.)*

### 4.2 Choix technologiques

| Couche | Choix | Justification |
|---|---|---|
| Mobile (APP) | React Native avec Expo, TypeScript strict, Expo Router (groupes de routes par rôle), TanStack Query (cache, reprise), React Hook Form + Zod, expo-secure-store, expo-notifications, expo-video (HLS), expo-image, react-native-compressor, tus-js-client | Décision de l'équipe. Une seule base de code Android (iOS possible, §17). Le client d'API TypeScript est généré depuis le schéma OpenAPI. Les modules natifs (compression vidéo) imposent des « builds de développement » Expo plutôt qu'Expo Go ; compatibilité à valider en phase 0 (§15). |
| Site (WEB) | Gabarits Django, HTMX (échanges partiels), Alpine.js en build compatible CSP (petits comportements), CSS pur assemblé par un script Python (écart décidé : voir §4 du prompt), hls.js et tus-js-client chargés uniquement sur les pages qui en ont besoin | Node uniquement en CI mobile et sur les postes de développement, jamais dans les images de production. Rendu serveur : pages indexables, aperçus de lien, premier affichage rapide sur réseau lent. Les bibliothèques JavaScript sont des fichiers figés dans `static/vendor`. |
| Administration (ADM) | Django admin personnalisé avec un thème moderne (django-unfold ou équivalent, choix en phase 0 ; repli : thème standard), django-otp (TOTP), django-axes, Chart.js servi en local | Authentification, permissions, listes et formulaires fournis ; tableaux de bord sur mesure. Hôte, processus, réglages, rôle de base de données et secrets séparés (§5.1). |
| Serveur (langage, framework) | Python 3.12, Django 5.2 LTS, Django REST Framework, drf-spectacular, PyJWT, argon2-cffi, phonenumbers (version récente figée : format béninois à 10 chiffres, §7.1), nh3 (assainissement HTML), markdown-it-py, Pillow + pillow-heif | Écosystème mûr, administration intégrée, compétences de l'équipe. Le calendrier de support de Django est à revérifier au démarrage (le projet révise son cycle de versions) et les versions exactes sont figées dans les fichiers de verrouillage. |
| Serveur d'applications | Gunicorn avec worker Uvicorn (ASGI) pour web-api, admin et realtime | Un seul modèle d'exécution pour HTTP et WebSocket ; redémarrage progressif et recyclage des processus par Gunicorn. |
| Temps réel | Django Channels, channels-redis (instance « files ») | Même code, mêmes modèles ; suffisant bien au-delà de la capacité visée (§8.1). |
| Tâches de fond | Celery, Redis (« files »), Celery beat ; files nommées `default`, `notifications`, `media` | Séparer les files empêche une vidéo lente de retarder un message. Tâches idempotentes. |
| Base de données | PostgreSQL 16 : pg_trgm, unaccent ; pool de connexions natif de Django avec psycopg 3 ; pas de PostGIS | Recherche tolérante aux accents et aux fautes ; distances calculées à l'enregistrement. PostGIS pourra s'ajouter sans toucher aux données (§6.4). |
| Cache et limites | Redis (instance « cache », politique d'éviction LRU) via django-redis ; sessions du site en `cached_db` (celles de l'administration en base seule) | Sépare ce qui peut être perdu (cache) de ce qui ne le doit pas (files, canaux). Les compteurs de sécurité (plafonds et budget OTP, verrouillages) ne dépendent jamais de ce cache : ils sont calculés depuis PostgreSQL (`otp_codes`) ou tenus dans redis-queue. |
| Médias | Disque du serveur, derrière une interface `StorageProvider` ; Caddy sert directement les fichiers publics avec cache longue durée | Le plus simple et le plus rapide au départ ; migration vers un stockage objet (S3, R2) prévue au palier 2 sans changer le code métier. |
| Vidéo | ffmpeg sur worker-media : HLS en 360p et 720p, segments de 2 s, affiche WebP ; interface `VideoProvider` | Deux qualités suffisent (360p pour la 3G, 720p pour le wifi) et divisent le temps de calcul ; un service managé reste possible (palier 3). |
| Notifications | Interface `PushProvider` : Expo Push ou FCM (décision en phase 0) | Les deux couvrent Android ; Expo simplifie les jetons. |
| SMS (OTP) | Interface `SmsProvider` ; agrégateur choisi sur devis (§17) | Aucun service gratuit ou généreux n'existe : la limite de coût est une exigence (§5.3). |
| Paiement (inactif) | Interface `PaymentProvider` ; implémentation factice, squelettes FedaPay et KKiaPay | Prêt sans être activé. |
| Reverse proxy | Caddy 2 : HTTPS automatique, HTTP/3 (UDP 443 ouvert), compression zstd ou gzip | Configuration courte, certificats gérés, un seul point d'entrée. |
| Conteneurs et livraison | Docker, Docker Compose, GitHub Actions, images publiées sur un registre | Même environnement en local et en production. |
| Exploitation | Journaux JSON, Sentry (sans données personnelles), sonde externe sur `/readyz`, sauvegardes avec restic + pg_dump chiffrés | Léger et suffisant pour un serveur (§13.4). |

### 4.3 Topologie des processus et du réseau

Tous les processus Django partagent la même image Docker et le même code ; seuls la commande de démarrage, les réglages et les volumes montés changent. Les services de données ne sont jamais publiés sur Internet : ils vivent sur un réseau interne Docker.

| Processus | Rôle | Instances | Remarques |
|---|---|---|---|
| caddy | Point d'entrée HTTPS, routage, fichiers statiques et médias | 1 | Seul conteneur exposé : 80 et 443 en TCP, 443 en UDP (HTTP/3). |
| web-api | Site (gabarits) et API REST ; réglages `public` | 1 à N | Sans état : sessions et cache dans Redis et PostgreSQL. |
| realtime | WebSocket (Channels) ; réglages `public` | 1 à N | Isolé pour qu'un afflux de connexions ne prive pas l'API de ressources. |
| admin | Administration ; réglages `admin`, URL propres | 1 | Autre clé secrète, autre cookie, autre hôte, autre rôle PostgreSQL, autre fichier d'environnement (§5.1). |
| worker | Tâches `default` et `notifications` | 1 à N | Concurrence 4 ; reprises avec temporisation. |
| worker-media | Tâche `media` (ffmpeg, photos) | 1 (puis N sur un autre serveur) | Concurrence 1, limites de CPU et de mémoire, aucun accès à Internet ; ne monte que `media_tmp` et `media_public`. |
| beat | Planificateur de tâches | exactement 1 | Verrou pour interdire les doublons. |
| postgres | Base de données unique | 1 | Réseau interne ; trois rôles : `app` (site et API), `admin_app` (administration, seul à écrire les rôles, la 2FA et les verrouillages du personnel) et `migrate` (DDL). |
| redis-cache | Cache, limites de débit, sessions du site | 1 | Éviction LRU ; peut être vidé sans perte de données ni de sécurité. |
| redis-queue | Files Celery et canaux WebSocket | 1 | Persistance AOF, aucune éviction. |
| backup | Sauvegardes planifiées (pg_dump, restic) | 1 | Indépendant de Celery pour continuer en cas de panne. |

#### Noms d'hôte et routage (Caddy)

| Hôte | Chemins | Destination |
|---|---|---|
| www.<domaine> | /static/*, /media/* | Fichiers servis directement par Caddy (cache d'un an, noms avec empreinte). |
| www.<domaine> | /ws/* | realtime |
| www.<domaine>, api.<domaine> | /uploads/* | web-api, corps limité à 2 Mo par requête (morceaux tus de 1 Mo) |
| www.<domaine> | tout le reste | web-api (site) |
| api.<domaine> | /v1/*, /ws/* | web-api, realtime (application mobile) |
| pilotage.<domaine> (nom non devinable) | tout | admin ; accès par VPN ou liste blanche d'adresses IP, obligatoire en production ; absent de tout lien, sitemap et robots |

```
www.{$DOMAIN} {
    encode zstd gzip
    handle /uploads/* {
        request_body { max_size 2MB }
        reverse_proxy web-api:8000
    }
    handle /static/* { root * /srv/static ; file_server }
    handle /media/* {
        root * /srv/media
        header Cache-Control "public, max-age=31536000, immutable"
        file_server
    }
    handle /ws/* { reverse_proxy realtime:8001 }
    handle {
        request_body { max_size 1MB }
        reverse_proxy web-api:8000
    }
}
pilotage.{$DOMAIN} {
    @autorise remote_ip {$ADMIN_ALLOWED_IPS}
    handle @autorise { reverse_proxy admin:8002 }
    handle { respond 404 }
}
```

*Extrait indicatif : chaque limite de corps ne s'applique qu'à sa branche (elles ne sont pas imbriquées) ; la version complète (en-têtes de sécurité, journaux, limites de délai) est écrite en phase 0, avec un test où la variable ADMIN_ALLOWED_IPS est vide (l'hôte doit alors tout refuser). Si un CDN est placé devant Caddy (palier 1), la liste blanche de l'administration doit lire l'adresse réelle transmise par le CDN et non celle du CDN.*

#### Volumes de fichiers : qui lit, qui écrit

| Volume | Contenu | Accès |
|---|---|---|
| media_tmp | Envois en cours (morceaux, originaux) | web-api écrit ; worker-media lit puis supprime. Jamais servi par Caddy. Plafonné par les quotas du §11.2. |
| media_public | HLS, affiches, photos WebP | worker-media écrit ; Caddy, web-api et admin lisent. |
| media_private | Pièces d'identité des gérants (chiffrées) | Monté **uniquement** dans admin. Ni web-api ni Caddy n'y accèdent. |

> **Dimensionnement de départ (estimation à valider par le test de charge, §14) :** serveur de 4 vCPU, 8 Go de mémoire, SSD de 160 Go. Budget mémoire approximatif : PostgreSQL 1,5 Go, web-api 0,8 Go, realtime 0,4 Go, admin 0,3 Go, workers 0,8 Go (+ 1 Go de pointe pour ffmpeg), Redis ×2 0,4 Go, Caddy et système 0,7 Go, soit environ 5,9 Go en pointe. Stockage : une vidéo de 60 s en 360p + 720p pèse environ 25 Mo, soit 25 Go pour 1 000 annonces actives ; l'original est supprimé 24 h après un traitement réussi. Les volumes de médias sont sur un disque ou un volume distinct de celui de PostgreSQL, et les envois sont refusés au-delà de 85 % d'occupation.

### 4.4 Organisation du code : frontières nettes pour évoluer

La robustesse d'un monolithe tient à ses frontières internes. Elles sont écrites et vérifiées automatiquement.

| Couche | Règle |
|---|---|
| models | Tables et contraintes. Une application n'importe pas les modèles d'une autre application. |
| selectors | Lectures optimisées (requêtes, annotations). Seul point d'entrée en lecture d'une application pour les autres. |
| services | Cas d'usage en écriture (publier une annonce, envoyer un message, marquer louée), dans une transaction. **Seul endroit où vit une règle métier.** Seul point d'entrée en écriture pour les autres applications. |
| api / web / consumers / tasks | Adaptateurs minces : vues DRF (mobile), vues et gabarits (site), WebSocket, tâches Celery. Ils valident l'entrée, appellent un service, mettent en forme la sortie. Aucune règle métier. |
| events | Après validation de la transaction (`on_commit`), le service signale l'événement (`message.created`, `listing.published`, `listing.rented`, `report.created`). Pour les messages, la diffusion WebSocket est un appel direct et la notification une tâche de la file dédiée ; alertes et statistiques sont des tâches Celery séparées, avec leurs reprises. Chaque abonné s'enregistre auprès de l'événement : en ajouter un ne modifie pas l'émetteur. |
| providers | Interfaces `StorageProvider`, `VideoProvider`, `SmsProvider`, `PushProvider`, `PaymentProvider` ; une implémentation réelle, une factice (locale et tests). |

- **Vérification automatique :** des contrats `import-linter` en intégration continue interdisent les imports croisés de modèles entre applications.
- **Tâches idempotentes et événements au moins une fois :** chaque abonné peut recevoir deux fois le même événement sans effet doublé (clés d'unicité, §9).
- **Filet contre les événements perdus :** une tâche de rattrapage toutes les minutes retrouve les messages et annonces sans notification attendue et relance l'abonné (EF-NTF-07).

#### Structure du dépôt

```
logeo/
├─ serveur/
│  ├─ config/                 réglages : base, local, public, admin ; ASGI ; Celery
│  ├─ apps/
│  │  ├─ accounts/            utilisateurs, OTP, appareils, profils gérants
│  │  ├─ listings/            quartiers, annonces, fraîcheur, favoris, alertes, statistiques
│  │  ├─ media/               envois reprenables, photos, vidéos, stockage
│  │  ├─ chat/                conversations, messages, WebSocket
│  │  ├─ notifications/       notifications, livraison push
│  │  ├─ moderation/          signalements, actions, détection de coordonnées
│  │  ├─ billing/             abonnements, paiements (inactif)
│  │  ├─ audit/               journal d'activité, paramètres
│  │  └─ core/                utilitaires, événements, interfaces des fournisseurs
│  ├─ web/                    gabarits, vues du site, static (css, vendor)
│  ├─ adminsite/              administration : tableaux de bord, vues sur mesure
│  └─ tests/
├─ mobile/                    application Expo (TypeScript) ; client d'API généré
├─ infra/                     docker-compose*.yml, Dockerfile, Caddyfile, scripts de déploiement et de sauvegarde
├─ docs/                      ce document, décisions d'architecture (ADR), guide d'installation
└─ Makefile                   up, migrate, seed, test, lint, css
```

### 4.5 Flux techniques clés

#### Import d'une vidéo (envoi reprenable)

1. Le gérant choisit une vidéo (galerie ou ordinateur). Le client contrôle format, durée et taille, puis, sur mobile, la compresse en 720p.
2. Il crée l'envoi : `POST /v1/pro/listings/{id}/media` (déclare taille, type, durée). Le serveur vérifie les quotas (§11.2), crée une ligne `listing_media` (statut `uploading`) et renvoie l'adresse d'envoi.
3. Envoi par le protocole **tus** (sous-ensemble : création, `HEAD`, `PATCH`) avec tus-js-client sur mobile et sur web, par morceaux de 1 Mo. Le serveur lit le corps par blocs (sans le charger en mémoire), écrit dans `media_tmp`, compte les octets reçus dans `received_bytes` et refuse tout dépassement de la taille déclarée. Après une coupure, `HEAD` donne le décalage et l'envoi reprend.
4. À la réception complète, le média passe à `uploaded` et une tâche est placée dans la file `media`.
5. worker-media contrôle le fichier avec ffprobe (conteneur mov, mp4 ou webm seulement, durée 10 à 60 s, résolution minimale), puis lance ffmpeg avec le format d'entrée forcé, `-protocol_whitelist file` et un délai maximal ; il calcule l'empreinte SHA-256, produit l'affiche et le HLS 360p/720p dans `media_public`, supprime l'original après 24 h, puis passe à `ready` (ou `failed` avec un motif lisible).
6. Le gérant voit l'état (notification et actualisation). Le gérant peut demander la publication pendant le traitement : l'annonce attend à l'état `processing` et passe d'elle-même à `published` quand la vidéo est `ready` (§11.1).

#### Envoi d'un message : envoi par HTTP, réception par WebSocket

1. L'expéditeur envoie `POST /v1/conversations/{id}/messages` avec un `client_msg_id` (idempotence). L'envoi par HTTP bénéficie des nouvelles tentatives, des limites de débit et de l'authentification habituelles ; le WebSocket ne sert qu'à recevoir.
2. Le service `send_message` ouvre une transaction, verrouille la ligne de la conversation, attribue `seq = last_seq + 1`, enregistre le message, applique la détection de coordonnées et valide.
3. Après validation (`on_commit`), le service diffuse directement `message.new` (`group_send`, sans passer par Celery) aux groupes WebSocket `user.{id}` des deux participants, puis place la création de la notification dans la file `notifications` (§11.9).
4. Le WebSocket est un canal au mieux ; la garantie est portée par HTTP. Le client interroge `GET …/messages?after_seq=` à la reconnexion, toutes les 15 s tant que le WebSocket est coupé et toutes les 30 s même connecté : aucun message n'est perdu durablement, l'ordre est celui de `seq`.
5. À l'ouverture de la conversation, le client envoie la lecture (`POST …/read`) ; l'autre participant reçoit `conversation.read`.

#### Publication, alertes et fraîcheur

1. La publication passe l'annonce à `published` et émet `listing.published`.
2. L'abonné « alertes » cherche les alertes actives qui correspondent (une requête SQL filtrée) et crée une notification par alerte, avec une clé d'unicité `alert:{alerte}:{annonce}` : une republication ne notifie jamais deux fois.
3. La tâche horaire de fraîcheur relance (J+7, J+10), masque (J+14) et émet les événements correspondants ; elle est rejouable sans effet de bord.

### 4.6 Performance et latence : budgets et parades

Le serveur ne contrôle pas le réseau : en Afrique de l'Ouest, l'aller-retour vers un serveur européen est souvent de l'ordre de 100 à 200 ms (à mesurer depuis Parakou, sur les réseaux MTN, Moov et Celtiis, avant de choisir la région du serveur). Les budgets ci-dessous visent donc d'abord le **nombre d'aller-retours** et le **poids** des réponses, puis le temps serveur.

| Chemin critique | Budget serveur (p95) | Parades prévues |
|---|---|---|
| Fil et recherche | 80 ms, 6 requêtes SQL au plus | Pagination par curseur ; index dédiés (§9.22) ; `select_related` et `prefetch_related` ; cache de page de 60 s invalidé par un compteur de version à chaque publication ; carte d'annonce de moins de 4 Ko ; un seul appel renvoie texte et URL de l'affiche. |
| Fiche annonce | 60 ms, 5 requêtes au plus | Description rendue une seule fois à l'enregistrement (`description_html`) ; cache par annonce invalidé par le service d'écriture. |
| Envoi et affichage d'un message | Serveur 100 ms ; total sous 1 s | Une seule transaction courte ; notification et diffusion hors transaction ; aucun appel externe pendant la requête. |
| Liste des conversations | 60 ms | Dernier message et compteur de non-lus stockés dans `conversations` (aucun calcul à l'affichage). |
| Page web (HTML) | Moins de 30 Ko compressés, JavaScript initial de 60 Ko au plus | Rendu serveur, HTMX et Alpine seuls au chargement ; hls.js et tus-js-client chargés à la demande ; CSS compilée et purgée ; polices du système. |
| Lecture vidéo | Démarrage sous 3 s à 1 Mb/s | HLS en segments de 2 s (premier segment d'environ 1,6 Mb en 360p), démarrage en 360p ; affiche WebP de 25 Ko au plus ; préchargement limité à la vidéo suivante ; mode économie de données. |
| Écritures lourdes | Réponse immédiate | Tout ce qui dépasse 200 ms (vidéo, alertes, notifications, statistiques) est asynchrone. |

#### Parades générales contre la latence

- **Aucune requête N+1 :** des tests fixent le nombre maximal de requêtes SQL par point d'entrée (`assertNumQueries`) ; un dépassement fait échouer l'intégration continue.
- **Index vérifiés :** les huit requêtes critiques du §9.22 sont examinées avec `EXPLAIN` sur un jeu de 50 000 annonces et 1 million de messages avant la mise en ligne ; `pg_stat_statements` actif en production.
- **Connexions :** pool natif de Django avec psycopg 3 ; `statement_timeout` de 5 s pour l'API et 60 s pour les tâches ; journal des requêtes de plus de 200 ms.
- **Réseau :** HTTP/3 et keep-alive (Caddy), compression zstd ou gzip, `Cache-Control` et `ETag` sur les lectures publiques, médias à empreinte avec cache d'un an.
- **Isolation des charges :** worker-media limité à une vidéo à la fois et à 2 vCPU par `cpus` Docker ; files séparées ; processus `realtime` distinct de `web-api`.
- **Surveillance continue :** le temps de réponse p95 par point d'entrée est tracé et alerté (§13.4) ; la mesure précède toute optimisation.

## 5. Sécurité

Logeo détient des numéros de téléphone, des conversations privées et des pièces d'identité de gérants, dans un marché où l'arnaque est le risque principal. La sécurité est donc une exigence de conception, pas une phase finale. Elle repose sur cinq principes.

- **Défense en profondeur :** chaque protection est doublée (réseau, application, base).
- **Moindre privilège :** rôles de base de données séparés, volumes montés au strict nécessaire, groupes de permissions minimaux.
- **Sûr par défaut :** tout refus est la réponse initiale ; un endpoint sans règle d'accès explicite est interdit (test automatique).
- **Autorisation côté serveur uniquement :** jamais déduite de l'interface ni d'un identifiant deviné ; 404 plutôt que 403 pour ne pas révéler l'existence d'une ressource.
- **Traçabilité :** toute action sensible du personnel est journalisée dans un journal résistant à la modification (`audit_logs`).

### 5.1 Isolation de l'administration

L'administration est le point le plus attractif pour un attaquant : elle est donc séparée du site à tous les niveaux, tout en partageant la base et le code métier.

| Mesure | Détail |
|---|---|
| Hôte séparé et non public | Nom d'hôte distinct, absent des liens, du sitemap et de `robots.txt` (`noindex`) ; il n'est pas secret (les journaux de transparence des certificats le révèlent) : la protection vient de l'accès restreint ci-dessous. Aucune route d'administration n'existe sur www ni sur api, et aucune route publique sur l'hôte d'administration : deux fichiers d'URL distincts. |
| Isolation de la base et des secrets | L'administration se connecte avec le rôle PostgreSQL `admin_app`, seul autorisé à écrire `users.role`, les comptes du personnel et les tables de 2FA et de verrouillage ; le rôle `app` ne peut ni créer ni modifier une ligne `moderator` ou `admin` (droits par colonne et déclencheur de refus). Un fichier d'environnement par service ; `PRIVATE_FILES_KEY` n'est injectée que dans admin et backup ; sessions de l'administration en base, hors du Redis partagé. Une faille de web-api ne donne donc ni élévation de rôle, ni lecture des pièces d'identité, ni accès aux secrets de l'administration. |
| Processus et réglages séparés | Conteneur `admin` avec ses propres réglages, sa propre clé secrète (un jeton du site n'est jamais valide ici), son propre nom de cookie en production (`__Host-lgadm`, hôte exact, `Secure`, `httpOnly`, `SameSite=Strict`). |
| Comptes du personnel uniquement | Un compte client ou gérant ne peut pas se connecter à l'administration, et un compte du personnel ne peut pas se connecter au site ni à l'API. Pas d'inscription, pas d'envoi d'e-mail de réinitialisation : la création et la réinitialisation se font par un administrateur ou en ligne de commande. |
| Double authentification obligatoire | TOTP (django-otp) exigé après le mot de passe, avec codes de secours à usage unique. Un compte sans 2FA configurée ne peut rien faire d'autre que la configurer. |
| Force brute | django-axes : verrouillage par compte seul après 5 échecs, durée croissante (changer d'adresse IP n'offre aucun essai de plus) ; fail2ban sur les journaux de Caddy pour bannir l'adresse au niveau du pare-feu ; message d'échec neutre. L'adresse IP réelle du client est transmise par Caddy et Django ne fait confiance qu'à lui. |
| VPN ou liste blanche d'adresses IP (obligatoire en production) | Caddy répond 404 hors liste. Si les administrateurs n'ont pas d'adresse stable, ils passent par un VPN (WireGuard) dont l'adresse sert de liste blanche. |
| Sessions courtes | Inactivité de 30 minutes, durée maximale de 8 heures, une session active par compte, déconnexion à la révocation du compte. |
| Accès aux données sensibles | Les pièces d'identité ne sont lisibles que depuis ce processus ; la lecture d'une conversation exige un motif (§11.11) ; toute action est écrite dans `audit_logs`. |
| Alertes | Notification au porteur du projet à chaque connexion d'un nouvel administrateur, à chaque verrouillage, et à tout changement de rôle. |

### 5.2 Authentification et sessions par surface

| Surface | Mécanisme | Détails |
|---|---|---|
| APP | Jeton d'accès JWT de 15 minutes (en-tête `Authorization`) + jeton de rafraîchissement opaque de 30 jours, lié à un appareil | Jeton d'accès signé (HS256, clé distincte de celle de l'administration) avec `aud` (client ou gerant), `sub`, `did` (appareil) et `ver` (version de sécurité du compte). Rafraîchissement par **rotation** : l'ancien jeton est invalidé ; la présentation d'un ancien jeton déjà échangé révoque l'appareil (vol détecté), sauf pendant une grâce de 60 s où il renvoie la même nouvelle paire (réponse perdue en 3G). `users.token_version` révoque tous les jetons d'un compte, et une liste des appareils révoqués (`did`) est vérifiée à chaque requête ; ces deux contrôles sont en cache et relus en base si le cache est vide. Stockage : `expo-secure-store`. |
| WEB | Session Django (cookie `__Host-lgsid`, `httpOnly`, `Secure`, `SameSite=Lax`) + jeton CSRF sur chaque requête qui modifie | Sessions dans Redis avec repli base de données ; identifiant régénéré à la connexion ; HTMX envoie le jeton CSRF en en-tête. Aucun jeton dans le stockage du navigateur. Le WebSocket utilise un ticket à usage unique. |
| ADM | Session Django séparée + mot de passe + TOTP | Voir §5.1. |

- **Mots de passe :** Argon2id, 8 caractères minimum, refus des mots de passe courants (liste intégrée), jamais journalisés ni renvoyés.
- **Connexion :** verrouillage progressif (5 échecs → 15 min, doublé à chaque récidive) compté par couple (numéro saisi, adresse IP ou appareil), y compris pour un numéro inconnu, avec réponse `401` uniforme et `Retry-After` : le verrouillage ne révèle pas qu'un numéro est inscrit et personne ne peut bloquer un compte à distance. Un plafond de 30 échecs par heure et par numéro, tous appareils confondus, ralentit les attaques réparties. Temps de réponse constant que le numéro existe ou non (hachage factice).
- **Ticket WebSocket :** `POST /ws-ticket` (authentifié) renvoie un ticket aléatoire valable 30 s, à usage unique, lié à l'utilisateur et à l'appareil, stocké dans Redis ; l'URL ne contient jamais de jeton d'accès.

### 5.3 Protection des codes OTP et du budget SMS

Le « pompage de SMS » (des robots déclenchent des milliers d'envois vers des numéros qu'ils contrôlent) est l'abus le plus coûteux d'un système à OTP, sans service gratuit pour l'absorber. Six protections se cumulent ; les valeurs sont à l'annexe A.

- **Pays autorisés :** seul l'indicatif +229 est accepté par défaut (paramètre `OTP_ALLOWED_COUNTRIES`).
- **Plafonds :** 3 demandes par heure et par numéro, 10 par jour et par appareil, 60 par jour et par plage d'adresses IP /24 (les réseaux mobiles et le Wi-Fi du campus partagent leurs adresses), délai de 60 s avant renvoi.
- **Budget avec friction croissante :** un budget quotidien par usage (inscription, réinitialisation, changement de numéro ; `OTP_DAILY_BUDGET`, valeur de départ 300 au total). À 80 %, le défi anti-robot devient obligatoire et les plafonds sont divisés par deux ; à 100 %, les demandes sont refusées avec un message d'indisponibilité et une alerte est envoyée. Les décomptes sont calculés depuis `otp_codes` (jamais depuis le cache) ; un usage épuisé ne bloque pas les autres, ni les connexions.
- **Preuve de l'appareil :** l'identifiant d'installation étant déclaré par le client, il ne suffit pas : l'application joint une attestation d'appareil (Play Integrity, à vérifier en phase 0) et ses plafonds sont réduits sans elle ; le site affiche le défi anti-robot Cloudflare Turnstile (gratuit), obligatoire dès la friction croissante.
- **Code :** 6 chiffres, 5 minutes, 5 essais, stocké sous forme d'HMAC, comparé en temps constant, invalidé à la réussite, jamais journalisé en production.
- **Aucune fuite d'existence :** la demande d'OTP répond identiquement quel que soit le numéro ; à l'inscription, l'existence d'un compte n'est révélée qu'après preuve de possession du numéro.

### 5.4 Modèle de menaces

| Menace | Parade | Vérification |
|---|---|---|
| Pompage de SMS | §5.3 : pays, plafonds, budget par usage, attestation, défi anti-robot | Test d'abus automatisé ; alerte déclenchée en recette |
| Force brute et bourrage d'identifiants (site, application) | Argon2id, verrouillage progressif par compte et par IP, messages neutres | Tests automatisés (EF-AUT-05) |
| Force brute sur l'administration | §5.1 : hôte séparé, 2FA, axes, fail2ban, liste blanche | Test : 5 échecs verrouillent ; compte sans 2FA bloqué |
| Accès à la ressource d'autrui (IDOR) | Contrôle propriétaire ou participant dans chaque service ; identifiants UUID ; 404 | Matrice de tests d'autorisation : chaque endpoint × chaque rôle |
| Fuite du numéro du gérant ou de l'adresse privée | Sérialiseurs et gabarits publics en liste blanche de champs | Test qui parcourt toutes les réponses publiques et échoue si un numéro ou une adresse privée apparaît |
| XSS stocké (description, messages, noms) | Markdown restreint puis nh3 ; échappement automatique des gabarits ; CSP sans script ni style en ligne | Corpus de charges XSS rejoué en test ; en-têtes vérifiés |
| CSRF | `SameSite`, jeton CSRF sur toute requête qui modifie (site) ; API par jeton en en-tête | Tests de requêtes inter-origines |
| Fichier malveillant ou piégé | Type déterminé par ffprobe et Pillow (pas par l'extension), tailles et durées bornées, EXIF supprimé, noms de fichiers UUID, ffmpeg appelé avec une liste d'arguments, format d'entrée forcé et `-protocol_whitelist file`, worker sans Internet, limité en CPU, mémoire et durée (10 min) | Tests avec fichiers corrompus, faux formats, très gros fichiers |
| Abus du WebSocket | Ticket à usage unique, contrôle de l'origine, 5 connexions par utilisateur, trame de 8 Ko, 30 événements par minute | Tests Channels et k6 |
| Déni de service applicatif | Limites Caddy (taille, délais), limites DRF par catégorie, pagination bornée, `statement_timeout`, files séparées ; CDN au palier 1 | Test de charge k6 aux seuils du §8.1 |
| Vol de jeton ou de session | Cookies `httpOnly` et `Secure`, jetons courts, rotation avec détection de réutilisation, révocation par `token_version` | Tests de rejeu |
| Élévation de privilèges du personnel | Groupes minimaux, vérification serveur, changement de rôle journalisé et notifié | Revue + tests par rôle |
| Abus de la lecture des conversations | Motif obligatoire, journal résistant à la modification, 2FA, alerte au-delà de 20 lectures par jour et par modérateur | Revue mensuelle du journal |
| Injection SQL ou de commandes | ORM et requêtes paramétrées ; aucune commande construite avec des entrées utilisateur | bandit en intégration continue ; revue |
| Fuite par journaux, sauvegardes ou erreurs | Filtre qui masque numéros et codes dans les journaux et dans Sentry ; sauvegardes chiffrées ; pages d'erreur sans détail | Revue ; test du filtre |
| Dépendance compromise | Fichiers de verrouillage, pip-audit, mises à jour de sécurité planifiées | Intégration continue |
| Hôte falsifié, redirection ouverte | `ALLOWED_HOSTS` strict, HSTS, paramètre `next` limité aux chemins du site | Tests |

### 5.5 Données sensibles et configuration

- **Pièces d'identité des gérants :** chiffrées par l'application (Fernet, clé hors base) avant d'être écrites sur le volume `media_private`, monté seulement dans l'administration ; durée de conservation et purge automatique (`docs_retain_until`).
- **Conversations :** lisibles par les deux participants ; par le personnel seulement avec motif et journal ; conservées 12 mois après la dernière activité, puis supprimées (durée à valider, §17).
- **En-têtes du site :** CSP (`default-src 'self'` ; `script-src 'self' https://challenges.cloudflare.com` ; `frame-src https://challenges.cloudflare.com` ; `style-src 'self'` ; `img-src 'self' data:` ; `media-src 'self' blob:` ; `worker-src blob:` ; `connect-src 'self' wss://www.<domaine>` ; `frame-ancestors 'none'` ; `base-uri 'none'` ; `form-action 'self'`), HSTS d'un an, `X-Content-Type-Options`, `Referrer-Policy: same-origin`, `Permissions-Policy` restrictive. Sans script ni style en ligne, HTMX est configuré sans évaluation de code (`allowEval` faux) ni styles injectés (`includeIndicatorStyles` faux) et Alpine.js est le build compatible CSP ; l'administration a sa propre CSP (django-unfold et Chart.js servis en local), réglée en phase 0.
- **Serveur :** durcissement décrit au §13.4 et vérifié par la liste du §13.5.
- **Base de données :** rôle `app` sans droit de modification de structure, rôle `admin_app` limité à l'administration (§5.1), rôle `migrate` utilisé seulement par la tâche de déploiement ; `audit_logs` résistant à la modification : `app` n'a que `INSERT` et `SELECT`, un déclencheur refuse `UPDATE`, `DELETE` et `TRUNCATE`, et une copie est exportée chaque jour hors du serveur (§9.18).
- **Secrets :** variables d'environnement lues depuis un fichier à droits restreints sur le serveur ; jamais dans le dépôt ; un fichier d'environnement par service ; clés distinctes pour le site et l'administration ; procédure de rotation documentée.
- **Référentiel :** OWASP ASVS niveau 1 ; liste de contrôle remplie et archivée avant la mise en ligne, revue croisée par l'autre développeur.

## 6. Évolutivité et montée en charge

Le système doit grandir en charge et en fonctionnalités sans réécriture. Cette section fixe les règles de développement qui le garantissent, les paliers de montée en charge avec leurs déclencheurs mesurés, et la manière d'ajouter les fonctions déjà envisagées.

### 6.1 Règles pour évoluer sans rien casser

1. **Frontières écrites et testées** (§4.4) : toute règle dans un service, toute communication entre applications par services, sélecteurs ou événements.
2. **API additive** : on ajoute des champs et des points d'entrée, on ne retire ni ne renomme rien dans une version publiée. Un contrôle `oasdiff` en intégration continue compare le schéma OpenAPI à celui de la version précédente et échoue si un changement est cassant.
3. **Migrations en deux temps (expand puis contract)** : on ajoute d'abord (colonne facultative, nouvelle table), on bascule le code, on nettoie une version plus tard. Aucune migration ne doit verrouiller une grosse table : index créés en mode concurrent, colonnes ajoutées sans valeur par défaut coûteuse. `django-migration-linter` vérifie chaque migration.
4. **Énumérations ouvertes** : les statuts et types sont des chaînes avec contrainte de valeurs ; tout client traite une valeur inconnue par un comportement par défaut (lecteur tolérant).
5. **Drapeaux de fonctionnalité** (`app_settings`) pour livrer en sommeil, activer progressivement et désactiver vite.
6. **Fournisseurs derrière des interfaces** : changer de SMS, de push, de stockage ou de paiement n'affecte aucun service métier.
7. **Processus sans état** : tout l'état durable est dans PostgreSQL, Redis ou le stockage de médias ; dupliquer un processus ne demande aucun changement de code (limite connue : l'envoi vidéo écrit sur disque tant que `StorageProvider` est local, voir palier 2).
8. **Décisions écrites** : toute décision d'architecture est consignée dans une courte note (ADR) dans `docs/`.

### 6.2 Compatibilité des applications mobiles

Une application installée ne se met pas à jour au moment voulu : plusieurs versions coexisteront toujours.

- **Version d'API :** préfixe `/v1`. Une version `/v2` n'apparaît que pour un changement cassant, et `/v1` reste servie au moins 6 mois après la sortie de l'application qui utilise `/v2`.
- **Configuration distante :** `GET /v1/app-config` renvoie `min_supported_version`, les drapeaux actifs, l'état de maintenance et les textes d'avis. En dessous de la version minimale, l'application affiche un écran de mise à jour obligatoire ; en maintenance, un message clair.
- **En-tête X-App-Version** sur chaque requête, tracé dans les journaux et dans les statistiques d'administration (répartition des versions).
- **Corrections à distance :** les correctifs en JavaScript sont livrés par mise à jour à distance d'Expo (EAS Update) sans repasser par le magasin ; les changements natifs passent par une nouvelle version du magasin.
- **Lecteur tolérant :** les clients ignorent les champs inconnus et affichent un repli pour un type de notification ou de message inconnu.

### 6.3 Paliers de montée en charge

Chaque palier est déclenché par une **mesure**, pas par une intuition. Les seuils sont des valeurs de départ à ajuster après le test de charge (§14). À chaque palier, le code métier ne change pas.

| Palier | Déclencheur mesuré | Action | Ce qui ne change pas |
|---|---|---|---|
| 0 Lancement | — | Un serveur 4 vCPU / 8 Go, tout dans Docker Compose. | — |
| 1 Monter en gamme | CPU supérieur à 60 % en heure de pointe pendant 1 h, ou p95 de lecture supérieur à 300 ms, ou disque supérieur à 70 % | Serveur plus gros ; CDN gratuit devant `/static` et `/media` ; réglage de PostgreSQL ; ajout d'une seconde instance web-api sur le même serveur. | Architecture, code, déploiement. |
| 2 Séparer les données | Base de plus de 25 Go, ou plus de 1 000 connexions WebSocket simultanées (la capacité de lancement est de 500, testée à 1 500), ou transcodage qui ralentit l'API | PostgreSQL géré ou sur serveur dédié avec PgBouncer ; worker-media sur un second serveur ; médias vers un stockage objet (S3 ou R2) par `StorageProvider` (l'envoi tus y écrit aussi), servis par un CDN sur `/media/*`, avec script de migration et double lecture temporaire ; Redis dédié. | API, règles métier, applications mobiles. |
| 3 Multiplier les instances | Plus de 20 000 utilisateurs actifs par jour, ou serveur unique devenu point de défaillance inacceptable | Plusieurs instances web-api et realtime derrière un répartiteur de charge ; réplique en lecture pour l'administration et les statistiques ; partitionnement mensuel de `messages` et `audit_logs` ; moteur de recherche dédié si plus de 50 000 annonces ou recherche lente ; vidéo managée possible. | Modèle de données, API publique. |

> **Honnêteté sur les limites du palier 0.** Un seul serveur est un point de défaillance unique : une panne du fournisseur coupe le service jusqu'à la restauration (objectif de remise en service : 4 h, ENF-DISP-04). C'est un choix de coût assumé pour le lancement. La capacité de 5 000 comptes et 500 connexions simultanées est très en deçà de ce que ce serveur supporte, ce qui laisse de la marge avant le palier 1.

### 6.4 Fonctions futures déjà prévues dans la structure

| Besoin futur | Comment l'ajouter | Ce qu'on ne touche pas |
|---|---|---|
| Images dans la messagerie | Table `message_attachments`, type de message `image`, point d'entrée d'envoi, traitement par la file `media`. Les anciennes versions affichent « pièce jointe non prise en charge ». | Table `messages`, séquence, notifications |
| Autres logements (appartements, maisons) | Colonne `property_type` avec valeur par défaut, nouvelles valeurs de `room_type`, filtres. | Messagerie, modération, notifications |
| Autre ville | Table `cities`, clé `districts.city_id`, point de référence par ville (migration en deux temps). | Annonces, API |
| Carte et recherche par rayon | Activer PostGIS, colonne `geography` calculée depuis latitude et longitude, index GiST ; l'API garde les mêmes champs. | Données existantes |
| Nouveau canal de notification (e-mail, SMS, Web Push) | Nouvelle implémentation de `PushProvider` et préférence correspondante. | Événements, messagerie |
| Activation de l'abonnement | Basculer le drapeau ; brancher le fournisseur réel ; valider les règles d'expiration (§17). | Publication, annonces existantes |
| Mise en avant payante | Colonne `boost_until` et critère de tri ; paiement via `PaymentProvider`. | Fil, recherche |
| Publication iOS | Construire la version iOS du même code ; notifications par Expo ou FCM. | API, serveur |

## 7. Exigences fonctionnelles

Chaque exigence indique ses surfaces (APP, WEB, ADM, §3.1) et sa priorité. « Toutes » = APP et WEB ; « Back » = traitement serveur sans écran. Les valeurs chiffrées sont des paramètres de départ regroupés dans l'annexe A.

### 7.1 Comptes et authentification (EF-AUT)

| ID | Exigence | Surfaces | Prio. |
|---|---|---|---|
| EF-AUT-01 | Inscription du locataire en deux temps : numéro (validé avec libphonenumber, +229 par défaut ; formats béninois à 8 chiffres et à 10 chiffres avec préfixe 01 acceptés et normalisés en E.164, à vérifier en phase 0), OTP, puis nom complet et mot de passe. Le compte n'existe qu'à la fin du second temps. | Toutes | M |
| EF-AUT-02 | OTP et protections anti-abus selon §5.3 ; valeurs de l'annexe A. | Toutes | M |
| EF-AUT-03 | Mot de passe de 8 caractères minimum, mots de passe courants refusés, hachage Argon2id. | Toutes | M |
| EF-AUT-04 | Connexion par numéro + mot de passe. APP : jeton d'accès de 15 min et jeton de rafraîchissement de 30 jours avec rotation (§5.2). WEB : session par cookie. | Toutes | M |
| EF-AUT-05 | Verrouillage progressif après 5 échecs, compté par (numéro saisi, IP ou appareil) ; réponse `401` uniforme, y compris pour un numéro inconnu ; temps de réponse constant (§5.2). | Toutes | M |
| EF-AUT-06 | Mot de passe oublié : OTP puis nouveau mot de passe ; toutes les sessions et tous les appareils sont révoqués. | Toutes | M |
| EF-AUT-07 | Création manuelle d'un gérant : l'administration crée le compte, attribue un mot de passe et le transmet hors plateforme ; aucune activation par OTP. | Toutes, ADM | M |
| EF-AUT-08 | Séparation des espaces : un locataire n'accède pas à l'espace gérant, un gérant pas à l'espace locataire ; un compte du personnel n'ouvre ni l'application ni le site, et inversement (§5.1). | Toutes, ADM | M |
| EF-AUT-09 | Mode invité : consultation sans compte ; une action qui exige un compte ouvre l'inscription puis ramène à l'action. | Toutes | M |
| EF-AUT-10 | CGU et politique de confidentialité acceptées à l'inscription (version et date dans `users`, événement dans `audit_logs`), avec mention de la consultation possible des conversations par la modération. | Toutes | M |
| EF-AUT-11 | Liste des appareils connectés (APP) ; déconnexion d'un appareil ou de tous. | Toutes | S |
| EF-AUT-12 | Changement de mot de passe (ancien requis). Changement de numéro : mot de passe actuel et OTP sur le nouveau numéro ; les autres appareils sont révoqués et l'ancien numéro reçoit un message d'avertissement. | Toutes | S |
| EF-AUT-13 | Suppression de compte à la demande, depuis l'application et depuis le site (exigence des magasins d'applications) : anonymisation des données personnelles (§9.23), conservation limitée des éléments de modération (durée à valider, §17). | Toutes | M |
| EF-AUT-14 | Administration : connexion par e-mail + mot de passe + TOTP obligatoire, codes de secours, verrouillage par django-axes, sessions courtes (§5.1). | ADM | M |

### 7.2 Profil et préférences (EF-PRO)

| ID | Exigence | Surfaces | Prio. |
|---|---|---|---|
| EF-PRO-01 | Modifier son nom et sa photo (facultative). | Toutes | S |
| EF-PRO-02 | Préférences de notification par catégorie (messages, alertes, rappels) et aperçu du message ; silence d'une conversation. Les notifications de sécurité et de sanction ne se coupent pas. | Toutes | M |
| EF-PRO-03 | Textes externalisés (i18n), français seul au lancement. | Toutes | S |

### 7.3 Annonces (EF-ANN)

| ID | Exigence | Surfaces | Prio. |
|---|---|---|---|
| EF-ANN-01 | Création par assistant en étapes (informations clés, localisation, équipements, médias, description, aperçu) ; brouillon enregistré côté serveur à chaque étape, repris sur un autre appareil. | Toutes (gérant) | M |
| EF-ANN-02 | Champs obligatoires, sans texte libre : titre (5 à 120 caractères), type de chambre, quartier, repère public, point GPS, loyer mensuel (FCFA), caution (mois), avance (mois), frais de démarcheur (FCFA, 0 si aucun), date de disponibilité, douche et WC internes, source d'eau, compteur d'électricité, clôture ou portail. | Toutes (gérant) | M |
| EF-ANN-03 | Description en texte enrichi pour tout le reste : gras, italique, barré, titre, listes, sauts de ligne ; 4 000 caractères. Markdown restreint, assaini côté serveur (§11.8), rendu identique partout. | Toutes (gérant) | M |
| EF-ANN-04 | Éditeur : barre d'outils qui insère le balisage avec onglet d'aperçu rendu par le serveur (même moteur que l'affichage) sur le site et sur mobile. | Toutes (gérant) | M |
| EF-ANN-05 | Coordonnées interdites dans titre, repère, adresse privée et description : numéros, liens, e-mails, mentions de messageries sont détectés ; l'enregistrement est refusé avec explication (§11.7). | Toutes (gérant) | M |
| EF-ANN-06 | Une vidéo principale obligatoire, importée par le gérant : MP4, MOV ou WebM ; 10 à 60 s ; 150 Mo maximum ; 480p minimum. Contrôle côté client puis revalidation serveur par ffprobe. | Toutes (gérant) | M |
| EF-ANN-07 | Sur mobile, compression en 720p avant envoi ; envoi par morceaux reprenable (protocole tus) avec progression et reprise automatique après coupure. | APP | M |
| EF-ANN-08 | Photos : 3 à 10, JPEG, PNG ou HEIC, 10 Mo maximum ; EXIF supprimé ; variantes WebP ; réordonnables ; photo de couverture au choix. | Toutes (gérant) | M |
| EF-ANN-09 | Traitement vidéo asynchrone avec état visible (envoi, traitement, prêt, échec avec motif). Une annonce n'est visible que si sa vidéo est prête. | Toutes (gérant) | M |
| EF-ANN-10 | Adresse précise facultative, visible seulement des participants d'une conversation ; le public voit le quartier, le repère et une position arrondie (environ 100 m). | Toutes | S |
| EF-ANN-11 | Publication immédiate pour un gérant vérifié, modération a posteriori ; exception : la première annonce de chaque gérant n'est publiée qu'après relecture de sa vidéo par la modération (cible 24 h). Pré-modération générale activable par paramètre. | Toutes, ADM | M |
| EF-ANN-12 | Modification d'une annonce publiée ; changements de statut et de loyer tracés dans `audit_logs`. | Toutes, ADM | M |
| EF-ANN-13 | « Louée » en un geste : conversations conservées, vidéo supprimée 7 jours plus tard sauf annulation, photos conservées. | Toutes (gérant) | M |
| EF-ANN-14 | Fraîcheur : relance à J+7 et J+10 sans confirmation, masquage automatique à J+14, réactivation par confirmation. | Toutes (gérant) | M |
| EF-ANN-15 | Bouton « Cette chambre est déjà louée » côté locataire ; trois signalements distincts préviennent le gérant et ouvrent un dossier. | Toutes (locataire) | S |
| EF-ANN-16 | Vidéo identique (même SHA-256) déjà publiée par un autre gérant : signalement automatique à la modération. | ADM | S |
| EF-ANN-17 | Plafond d'annonces actives par gérant (20 par défaut). | Toutes (gérant) | S |
| EF-ANN-18 | Dupliquer une annonce. | Toutes (gérant) | C |
| EF-ANN-19 | Quotas d'envoi : 1 vidéo et 10 photos par annonce ; 2 envois ouverts et 500 Mo en attente par gérant ; création d'envoi refusée quand le disque des médias dépasse 85 % (§11.2). | Back | M |

### 7.4 Fil, recherche et fiche (EF-REC)

| ID | Exigence | Surfaces | Prio. |
|---|---|---|---|
| EF-REC-01 | Fil des annonces publiées, plus récentes d'abord, vidéo en premier ; pagination par curseur (10 par page). | Toutes | M |
| EF-REC-02 | Mode économie de données, activé par défaut en connexion lente : affiche seule, lecture à l'appui, qualité la plus basse. | Toutes | M |
| EF-REC-03 | Lecture HLS adaptative : démarrage sous 3 s, une seule vidéo lue à la fois, préchargement limité à la vidéo suivante. | Toutes | M |
| EF-REC-04 | Recherche texte sur titre, description et quartier, insensible aux accents, tolérante aux petites fautes (unaccent, pg_trgm). | Toutes | M |
| EF-REC-05 | Filtres : quartiers, loyer min et max, type, douche et WC internes, eau, compteur, clôture, disponible avant une date, distance maximale au campus. | Toutes | M |
| EF-REC-06 | Tris : plus récentes, loyer croissant ou décroissant, plus proches du campus. | Toutes | M |
| EF-REC-07 | Fiche : vidéo, galerie, caractéristiques, description rendue, quartier et repère, distance, badge « Vérifié », date de confirmation ; boutons Contacter, Favori, Partager, Signaler. | Toutes | M |
| EF-REC-08 | Le numéro du gérant n'est jamais exposé (API, pages, aperçus de lien). | Toutes | M |
| EF-REC-09 | Partage par lien (feuille de partage native sur mobile) ; la page s'ouvre sans compte. | Toutes | M |
| EF-REC-10 | Annonces louées consultables jusqu'à l'archivage, marquées « Louée », sans vidéo. | Toutes | S |
| EF-REC-11 | Résultat vide : proposer de créer une alerte avec les critères. | Toutes | S |

### 7.5 Favoris et alertes (EF-ALR)

| ID | Exigence | Surfaces | Prio. |
|---|---|---|---|
| EF-ALR-01 | Ajouter, retirer, lister les favoris. | Toutes (locataire) | M |
| EF-ALR-02 | Créer une alerte : quartiers, loyer maximum, types, douche et WC internes, distance maximale ; 5 alertes actives au plus. | Toutes (locataire) | M |
| EF-ALR-03 | Correspondance à la publication, tâche asynchrone ; une seule notification par couple alerte/annonce (clé d'unicité). | Back | M |
| EF-ALR-04 | Un favori qui devient loué ou masqué déclenche une notification. | Toutes | S |

### 7.6 Messagerie (EF-MSG)

| ID | Exigence | Surfaces | Prio. |
|---|---|---|---|
| EF-MSG-01 | Un locataire connecté ouvre une conversation depuis une fiche ; une seule par couple (annonce, locataire). | Toutes | M |
| EF-MSG-02 | Messages texte de 2 000 caractères maximum ; envoi optimiste avec statut : en attente, envoyé, lu. **Texte seul** : ni image, ni vidéo, ni vocal. | Toutes | M |
| EF-MSG-03 | Envoi par HTTP, réception temps réel par WebSocket ; reconnexion automatique avec resynchronisation depuis le dernier `seq` reçu ; le WebSocket est au mieux et la garantie vient de HTTP : interrogation `after_seq` toutes les 30 s même connecté, 15 s si le WebSocket est coupé. | Toutes | M |
| EF-MSG-04 | Idempotence : un `client_msg_id` unique par message ; une nouvelle tentative ne crée jamais de doublon. | Toutes | M |
| EF-MSG-05 | Ordre garanti par un numéro de séquence propre à chaque conversation. | Back | M |
| EF-MSG-06 | Liste des conversations : dernier message, compteur de non-lus, tri par activité ; filtre par annonce côté gérant. | Toutes | M |
| EF-MSG-07 | Accusés de lecture par position de lecture. | Toutes | M |
| EF-MSG-08 | En-tête avec carte de l'annonce et son statut ; bandeau si louée ; lecture seule 30 jours après la location. | Toutes | S |
| EF-MSG-09 | Bloquer une conversation (le participant qui bloque empêche l'autre d'écrire) ; signaler un message ou une conversation. | Toutes | M |
| EF-MSG-10 | Détection des coordonnées : message enregistré et marqué, rappel à l'expéditeur, dossier automatique pour la modération ; modes aucun filtrage (par défaut depuis le 2026-10-18), masquer, signaler, bloquer (§11.7). | Back | M |
| EF-MSG-11 | Limites : 30 messages par minute et par utilisateur ; 20 nouvelles conversations par jour et par locataire. | Back | M |
| EF-MSG-12 | Premier message proposé et modifiable (« Bonjour, la chambre est-elle toujours disponible ? »). | Toutes | S |
| EF-MSG-13 | Indicateur « est en train d'écrire ». | Toutes | C |

### 7.7 Notifications (EF-NTF)

| ID | Exigence | Surfaces | Prio. |
|---|---|---|---|
| EF-NTF-01 | Chaque message reçu crée sa propre notification (centre et compteur) : une notification par message. | Toutes | M |
| EF-NTF-02 | Push mobile pour chaque message reçu, sauf vers l'appareil sur lequel la conversation est ouverte à l'écran (présence liée à la connexion WebSocket, §11.9) ; jamais de message sans push ni lecture. Titre : nom de l'expéditeur ; corps : début du message (80 caractères) ou « Nouveau message » selon la préférence ; l'appui ouvre la conversation. | APP | M |
| EF-NTF-03 | Regroupement à l'affichage seulement : chaque message garde sa notification et son push ; `collapse_key` (conversation) remplace la notification précédente dans le tiroir du téléphone, et le centre les présente groupées par conversation. | Toutes | M |
| EF-NTF-04 | Autres événements notifiés selon l'annexe B. | Toutes | M |
| EF-NTF-05 | Centre de notifications : liste paginée, lu, tout marquer lu, compteur sur l'icône. | Toutes | M |
| EF-NTF-06 | Appareils : enregistrement du jeton à la connexion, suppression à la déconnexion, nettoyage des jetons invalides. | Back | M |
| EF-NTF-07 | Fiabilité : file dédiée, 5 essais à temporisation croissante, suivi de livraison dans `notifications`, tâche de rattrapage chaque minute pour tout événement sans notification. Un échec de notification n'empêche jamais l'enregistrement d'un message. | Back | M |
| EF-NTF-08 | Rappel au gérant pour un message non lu depuis 2 h ; SMS de repli derrière un drapeau, désactivé par défaut. | Back | S |
| EF-NTF-09 | Au premier lancement, consigne pour exclure l'application de l'économie de batterie des fabricants Android. | APP | S |
| EF-NTF-10 | Web Push (VAPID) sur le site, après une première action utile. | WEB | C |

### 7.8 Tableau de bord du gérant (EF-DSH)

| ID | Exigence | Surfaces | Prio. |
|---|---|---|---|
| EF-DSH-01 | Indicateurs : annonces actives, louées, masquées ; vues ; conversations ouvertes ; messages non lus ; délai médian de réponse ; taux de réponse sur 30 jours. | Toutes (gérant) | M |
| EF-DSH-02 | Par annonce : vues uniques par jour, favoris, conversations, courbe sur 30 jours. | Toutes (gérant) | M |
| EF-DSH-03 | Liste « à faire » : annonces à confirmer, conversations sans réponse, vidéos en erreur. | Toutes (gérant) | S |
| EF-DSH-04 | Comptage des vues : un visiteur (compte ou appareil) par annonce et par jour, déduplication en cache ; propriétaire et robots exclus. | Back | M |

### 7.9 Signalement et modération (EF-MOD)

| ID | Exigence | Surfaces | Prio. |
|---|---|---|---|
| EF-MOD-01 | Signaler une annonce, un message, une conversation ou un utilisateur, avec un motif de liste et une précision facultative. | Toutes | M |
| EF-MOD-02 | File de modération (signalements et détections automatiques) : filtres, attribution, délai de traitement cible de 24 h. | ADM | M |
| EF-MOD-03 | Lecture d'une conversation par le personnel avec motif obligatoire saisi avant ouverture ; chaque ouverture est écrite dans `audit_logs` (qui, quand, motif, conversation). | ADM | M |
| EF-MOD-04 | Actions : masquer ou supprimer un message, masquer ou retirer une annonce, avertir, suspendre (30 jours au plus pour un modérateur), bannir (administrateur), rétablir. Motif obligatoire ; l'utilisateur est notifié ; tout est journalisé. | ADM | M |
| EF-MOD-05 | Un utilisateur suspendu ne peut ni publier ni écrire mais peut consulter, avec un bandeau explicatif ; un banni ne peut plus se connecter. | Toutes | M |
| EF-MOD-06 | La suspension d'un gérant masque ses annonces ; son rétablissement les remet en ligne si elles sont encore valides. | Back | M |
| EF-MOD-07 | Tableau de modération : volume de dossiers, délai médian de traitement. | ADM | S |
| EF-MOD-08 | Contestation d'une sanction par l'utilisateur. | Toutes | C |

### 7.10 Administration et statistiques (EF-ADM)

| ID | Exigence | Surfaces | Prio. |
|---|---|---|---|
| EF-ADM-01 | Création d'un gérant : nom, numéro, zone, pièces justificatives (chiffrées, volume privé), notes d'entretien. Statuts de vérification : en attente, entretien, vérifié, refusé ; la suspension est celle du compte (`users.status`). La création attribue un mot de passe (transmis hors plateforme) et déclenche un SMS informatif « compte prêt ». Badge « Vérifié » attribuable et retirable. | ADM | M |
| EF-ADM-02 | Gestion des utilisateurs : recherche, statut, appareils, historique des sanctions. | ADM | M |
| EF-ADM-03 | Gestion des annonces : recherche, aperçu complet, masquage, retrait, restauration. | ADM | M |
| EF-ADM-04 | Statistiques complètes selon le catalogue ci-dessous : tableaux et courbes, période au choix, export CSV. | ADM | M |
| EF-ADM-05 | Journal d'activité horodaté, filtrable, non modifiable, exportable en CSV. | ADM | M |
| EF-ADM-06 | Paramètres et drapeaux (annexe A) modifiables sans redéploiement ; chaque changement journalisé avec l'ancienne et la nouvelle valeur. | ADM | M |
| EF-ADM-07 | Gestion du personnel : création de comptes modérateur et administrateur, réinitialisation de 2FA, désactivation ; au moins deux personnes habilitées à modérer. | ADM | M |
| EF-ADM-08 | Plans d'abonnement (création, modification) sans effet tant que le drapeau est faux. | ADM | S |

#### Catalogue des statistiques de l'administration

Calculées par agrégations SQL en lecture seule, mises en cache 5 minutes ; les périodes longues s'appuient sur `daily_stats` (compteurs enregistrés chaque nuit, §9.10) et non sur les lignes détaillées, purgées selon §17 ; réplique en lecture au §6.3.

| Domaine | Indicateurs | Source |
|---|---|---|
| Acquisition | Inscriptions par jour, semaine et mois ; OTP demandés, réussis, échoués ; taux de conversion OTP → compte ; répartition APP / WEB et des versions de l'application | `users`, `otp_codes`, `devices`, `daily_stats` |
| Activation et rétention | Part des inscrits ayant ouvert une conversation en 7 jours ; utilisateurs actifs par jour et par mois (historique dans `daily_stats`) | `users.last_seen_at`, `conversations`, `daily_stats` |
| Offre | Annonces par statut, par quartier, par type ; loyer médian par quartier et par type ; part de vidéos prêtes ; âge moyen des annonces ; taux de confirmation de fraîcheur | `listings`, `listing_media`, `districts` |
| Gérants | Gérants par statut de vérification ; classement par délai de réponse, annonces actives, locations ; gérants inactifs depuis 14 jours | `gerant_profiles`, `conversations`, `listings` |
| Engagement | Vues, favoris, conversations ouvertes par annonce et par jour ; messages par jour ; alertes actives ; recherches sans résultat (compteur agrégé) | `daily_stats`, `messages`, `alerts` |
| Conversion | Locations conclues par semaine ; délai médian entre publication et location ; conversations par location | `listings.rented_at`, `conversations` |
| Qualité de service | Délai médian et p90 de première réponse ; part de conversations sans réponse sous 24 h | `conversations` |
| Modération et sécurité | Signalements par motif et par statut ; délai de traitement ; coordonnées détectées ; sanctions ; verrouillages de comptes | `reports`, `moderation_actions`, `audit_logs`, `users` |
| Technique et coûts | SMS envoyés et coût estimé ; notifications envoyées, échouées, taux de livraison ; vidéos en erreur ; stockage utilisé ; file Celery ; erreurs applicatives | `otp_codes`, `daily_stats`, `notifications`, `listing_media`, supervision |

### 7.11 Abonnement : architecture prête, non activée (EF-ABO)

| ID | Exigence | Surfaces | Prio. |
|---|---|---|---|
| EF-ABO-01 | Modèle de données et services de facturation complets (abonnements, paiements, événements de webhook), livrés, testés et inactifs ; les plans sont des paramètres (`app_settings`). | Back | M |
| EF-ABO-02 | Drapeau `SUBSCRIPTION_ENABLED`, faux par défaut : aucune restriction de publication, aucun écran d'abonnement, endpoints répondant `404 feature_disabled`. | Toutes | M |
| EF-ABO-03 | Point d'extension unique `can_publish(gerant)` appelé à la création et à la publication ; toujours vrai quand le drapeau est faux. | Back | M |
| EF-ABO-04 | Interface `PaymentProvider` (initier, vérifier, rembourser, traiter un webhook) ; implémentation factice, squelettes FedaPay et KKiaPay. | Back | M |
| EF-ABO-05 | Webhooks : signature vérifiée, idempotence par identifiant d'événement, traitement asynchrone. | Back | M |
| EF-ABO-06 | Plan « Gratuit V1 » (prix 0, sans limite) attribué à tout gérant vérifié, pour que l'activation future ne demande aucune migration de données. | Back | M |
| EF-ABO-07 | Écrans « Mon abonnement » et « Choisir un plan » développés, masqués par le drapeau. | Toutes (gérant) | S |
| EF-ABO-08 | Cycle de vie : essai, actif, impayé (grâce de 7 jours), annulé, expiré ; à l'expiration, annonces visibles 7 jours puis masquées (règle à valider avant activation). | Back | S |

### 7.12 Site web : pages publiques et référencement (EF-WEB)

| ID | Exigence | Surfaces | Prio. |
|---|---|---|---|
| EF-WEB-01 | Pages rendues par le serveur : accueil, recherche, fiche, page par quartier, « Je suis gérant » (explication, pas d'inscription), pages légales. | WEB | M |
| EF-WEB-02 | Open Graph et Twitter (titre, loyer, quartier, affiche), titre et description uniques, URL `/chambres/{slug}`, lien canonique. | WEB | M |
| EF-WEB-03 | `sitemap.xml` et `robots.txt` générés ; annonces louées en `noindex` après 30 jours ; données structurées schema.org. | WEB | S |
| EF-WEB-04 | Espaces connectés exclus de l'indexation ; interactions partielles par HTMX, pages utilisables sans JavaScript pour la lecture et les formulaires simples. | WEB | M |
| EF-WEB-05 | Application installable (PWA : manifeste, icônes, page minimale hors connexion). | WEB | S |
| EF-WEB-06 | Design soigné et responsive (360 px à 1440 px), jeu de composants unique, accessibilité de base. | WEB | M |

## 8. Exigences non fonctionnelles

Chaque cible se vérifie par un test ou un outil avant la mise en ligne. Mesures sur le serveur de référence du §4.3 et l'appareil de référence du §3.6.

### 8.1 Performance et capacité

| ID | Exigence | Mesure |
|---|---|---|
| ENF-PERF-01 | Temps de réponse de l'API et des pages (mesuré à Caddy) à 50 requêtes par seconde | p95 inférieur à 300 ms (lectures), 500 ms (écritures hors média) |
| ENF-PERF-02 | Latence d'un message de l'envoi à l'affichage chez un destinataire connecté | p95 inférieur à 1 s |
| ENF-PERF-03 | Démarrage à froid de l'application sur l'appareil de référence | Premier écran utile en moins de 4 s |
| ENF-PERF-04 | Page publique (hors vidéo) en 4G puis 3G simulée | LCP inférieur à 2,5 s en 4G ; premier affichage utile inférieur à 3 s en 3G ; JavaScript initial inférieur à 60 Ko compressés ; HTML inférieur à 30 Ko compressés |
| ENF-PERF-05 | Poids d'une page de 10 cartes d'annonces (JSON) | 40 Ko au plus |
| ENF-PERF-06 | Démarrage de la lecture vidéo à 1 Mb/s | Moins de 3 s |
| ENF-PERF-07 | Traitement d'une vidéo de 60 s par worker-media | Moins de 5 minutes |
| ENF-PERF-08 | Taille de téléchargement de l'application | 50 Mo au plus |
| ENF-PERF-09 | Requêtes SQL par point d'entrée critique | Plafonds fixés par test (§4.6) |
| ENF-CAP-01 | Dimensionnement de la première version | 5 000 comptes locataires, 100 gérants, 1 000 annonces actives, 500 connexions WebSocket simultanées, 200 messages par minute en pointe ; test de charge à 3 fois ces valeurs sans dépasser les cibles ENF-PERF-01 et 02 |

### 8.2 Disponibilité, sauvegarde et reprise

| ID | Exigence | Mesure |
|---|---|---|
| ENF-DISP-01 | Disponibilité mensuelle de l'API et du site | 99 % (environ 7 h d'arrêt par mois au plus) |
| ENF-DISP-02 | Sauvegarde de la base : copie logique quotidienne et archivage continu des journaux de transaction (WAL), chiffrés, envoyés hors du serveur | Copies conservées 14 jours quotidiens + 8 hebdomadaires ; WAL conservés 14 jours |
| ENF-DISP-03 | Sauvegarde des médias publics et des pièces privées (incrémentale, chiffrée, hors du serveur) | Quotidienne |
| ENF-DISP-04 | Objectifs de reprise | Perte de données maximale 5 min (archivage continu dès le lancement) ; remise en service en moins de 4 h sur un serveur neuf, secrets compris (§13.4) |
| ENF-DISP-05 | Test de restauration complet documenté, sur un serveur vierge | Avant la mise en ligne, puis chaque trimestre |
| ENF-DISP-06 | Déploiement | Coupure inférieure à 10 s ; reconnexion automatique des WebSocket ; migrations compatibles avec la version précédente (retour arrière du code sans retour arrière de la base) |
| ENF-DISP-07 | Points de contrôle `/healthz` (processus) et `/readyz` (base, Redis, disque) | Sonde externe toutes les minutes, alerte après 3 échecs |

### 8.3 Sécurité

| ID | Exigence | Mesure |
|---|---|---|
| ENF-SEC-01 | Mise en œuvre du §5 (administration isolée, jetons, OTP, modèle de menaces) ; OWASP ASVS niveau 1 | Liste de contrôle archivée ; revue croisée avant la mise en ligne |
| ENF-SEC-02 | Transport : HTTPS et WSS partout, HSTS ; aucune donnée sensible dans les URL ni les journaux | Scan automatisé (en-têtes, TLS) |
| ENF-SEC-03 | Autorisation vérifiée côté serveur sur chaque point d'entrée, tous rôles confondus | Matrice de tests endpoint × rôle ; un endpoint sans règle fait échouer l'intégration |
| ENF-SEC-04 | Aucune fuite du numéro du gérant ni de l'adresse privée | Test de parcours des réponses publiques |
| ENF-SEC-05 | Entrées : validation systématique, texte assaini, fichiers contrôlés par signature, tailles limitées | Tests et analyse statique (bandit, ruff) |
| ENF-SEC-06 | Secrets hors dépôt ; clés distinctes site et administration ; production refusant les raccourcis de développement (code OTP fixe, débogage) | Analyse de secrets en CI ; vérification au démarrage |
| ENF-SEC-07 | Dépendances auditées à chaque intégration | Aucune vulnérabilité critique connue à la livraison |
| ENF-SEC-08 | Journal `audit_logs` résistant à la modification (le rôle `app` n'a que l'insertion et la lecture), actions du personnel et lectures de conversations tracées | Tentative de modification refusée par la base (test) |

### 8.4 Données personnelles et conformité

- **Minimisation :** numéro et nom sont les seules données obligatoires du locataire ; aucune position GPS n'est collectée chez les locataires.
- **Transparence :** CGU et politique de confidentialité en français clair, acceptées à l'inscription, indiquant la consultation possible des conversations par la modération et les durées de conservation.
- **Droits :** accès, rectification, suppression (EF-AUT-13) ; durées de conservation définies pour les messages, les pièces des gérants, les journaux et les sauvegardes.
- **Cadre légal :** la loi béninoise sur les données personnelles (code du numérique) et l'autorité compétente sont à vérifier avec un juriste avant l'ouverture, notamment l'obligation éventuelle de déclaration (§17).
- **Droits sur les contenus :** les CGU font garantir par le gérant ses droits sur les vidéos et photos et prévoient une procédure de retrait.

### 8.5 Fiabilité réseau, compatibilité, accessibilité

| ID | Exigence | Mesure |
|---|---|---|
| ENF-RES-01 | Mobile : file locale des messages, nouvelle tentative automatique, cache du dernier fil, squelettes de chargement | Parcours testés réseau coupé puis rétabli |
| ENF-RES-02 | Créations sensibles idempotentes (messages, envois, paiements) | Tests de répétition de requête |
| ENF-COMP-01 | Android 8.0 (API 26) et plus visé ; minimum réel à confirmer selon la version d'Expo retenue | Appareil de référence et appareil récent |
| ENF-COMP-02 | Navigateurs : deux dernières versions de Chrome, Firefox, Edge, Samsung Internet ; Safari iOS 15 et plus. Opera Mini non pris en charge | Tests Playwright sur Chrome, vérification manuelle des autres |
| ENF-ACC-01 | Contrastes WCAG AA, cibles tactiles de 48 dp au moins, taille de police du système respectée, messages d'erreur clairs | Contrôles automatiques (axe) et revue manuelle |
| ENF-I18N-01 | Français ; montants « 25 000 FCFA » ; dates dans le fuseau Africa/Porto-Novo, stockées en UTC | Tests de formatage |

### 8.6 Exploitation, évolutivité et qualité

| ID | Exigence | Mesure |
|---|---|---|
| ENF-OBS-01 | Journaux JSON avec identifiant de requête propagé jusqu'aux tâches ; Sentry sans données personnelles ; temps de réponse p95 par point d'entrée | Un incident se diagnostique sans accès à la base |
| ENF-OBS-02 | Alertes : indisponibilité, disque supérieur à 80 %, file Celery bloquée, échecs répétés de push ou de SMS, coupe-circuit OTP déclenché, sauvegarde manquante | Alertes testées avant la mise en ligne |
| ENF-EVO-01 | Frontières entre applications vérifiées (import-linter) | Bloquant en intégration continue |
| ENF-EVO-02 | Aucun changement cassant d'API dans `/v1` | oasdiff en intégration continue |
| ENF-EVO-03 | Migrations sûres : sans verrouillage long, en deux temps | django-migration-linter en intégration continue |
| ENF-EVO-04 | Version minimale d'application et drapeaux distants (`app-config`) | Test de l'écran de mise à jour obligatoire |
| ENF-MNT-01 | TypeScript strict, ruff et ESLint sans erreur, revue de code obligatoire par l'autre développeur | Contrôles bloquants en CI |
| ENF-MNT-02 | Couverture d'au moins 80 % sur comptes, messagerie et annonces (services) | Rapport de couverture |
| ENF-MNT-03 | README, ADR, schéma OpenAPI et guide d'installation locale (moins de 30 minutes) à jour | Un nouveau développeur démarre sans aide |
| ENF-POR-01 | Docker Compose, configuration par variables d'environnement, aucune dépendance sans interface de remplacement | Passage local vers serveur par configuration seule |

## 9. Modèle de données

### 9.1 Conventions

- **Moteur :** PostgreSQL 16 avec les extensions pg_trgm et unaccent. Migrations Django ; noms en anglais, `snake_case`, tables au pluriel. **19 tables métier** ; les tables du framework (sessions, permissions, django-otp, django-axes, migrations) s'y ajoutent.
- **Clés :** `id` de type `uuid` (généré par l'application), sauf les journaux en `bigint` à identité. Clés composées signalées.
- **Dates :** `timestamptz` en UTC ; `created_at` et `updated_at` sur les tables modifiables. **Montants :** entiers en FCFA. **Positions :** `numeric(9,6)` latitude et longitude (pas de PostGIS).
- **Énumérations :** `varchar` avec contrainte `CHECK` (évolution simple ; les clients tolèrent les valeurs inconnues, §6.2).
- **Notations des contraintes :** NN non nul ; UQ unique ; PK clé primaire ; FK→table clé étrangère ; DEF valeur par défaut ; CK valeurs permises.
- **Cohérence :** les colonnes de cache (`median_response_min`, `last_message_preview`…) sont recalculables et jamais sources de vérité. Les écritures qui touchent plusieurs lignes se font dans une transaction courte.

### 9.2 Vue par domaines

*Figure 2 — Six domaines, 19 tables. (schéma non reproduit ici : voir les listes et tableaux de la section.)*

### 9.3 users — Utilisateurs

Locataires, gérants et personnel dans une table. Les locataires et gérants se connectent par numéro ; le personnel par e-mail, uniquement sur l'administration. La 2FA du personnel utilise les tables de django-otp.

| Champ | Type | Contraintes | Description |
|---|---|---|---|
| id | uuid | PK | Identifiant |
| phone_e164 | varchar(16) | UQ (si non nul) | Numéro au format E.164 (+229…) |
| email | varchar(254) | UQ (si non nul) | Personnel uniquement |
| phone_verified_at | timestamptz |  | Validation par OTP |
| password_hash | varchar(255) | NN | Argon2id |
| full_name | varchar(120) | NN |  |
| role | varchar(12) | NN, CK(client, gerant, moderator, admin) | Rôle. CK : client et gerant exigent phone_e164 ; moderator et admin exigent email |
| status | varchar(12) | NN, DEF 'active', CK(active, suspended, banned, deleted) | État du compte |
| suspended_until | timestamptz |  | Fin de suspension |
| avatar_path | varchar(255) |  | Photo (volume public) |
| token_version | integer | NN, DEF 0 | Incrémenté pour révoquer tous les jetons (§5.2) |
| terms_version / terms_accepted_at | varchar(16) / timestamptz |  | Dernières CGU acceptées |
| notif_prefs | jsonb | NN, DEF '{}' | Préférences : par catégorie {push, apercu}, silence |
| last_seen_at | timestamptz |  | Dernière activité (web ou application), mise à jour au plus une fois par jour |
| deleted_at | timestamptz |  | Anonymisation |
| created_at / updated_at | timestamptz | NN |  |

### 9.4 otp_codes — Codes à usage unique

Un enregistrement par code envoyé ; sert aussi à compter les envois et leur coût. Purge à 90 jours.

| Champ | Type | Contraintes | Description |
|---|---|---|---|
| id | uuid | PK |  |
| phone_e164 | varchar(16) | NN | Destinataire |
| purpose | varchar(20) | NN, CK(signup, reset_password, change_phone) | Usage |
| code_hmac | varchar(64) | NN | HMAC du code ; jamais le code en clair |
| expires_at | timestamptz | NN | Création + 5 minutes |
| attempts | smallint | NN, DEF 0 | Essais ; maximum 5 |
| consumed_at | timestamptz |  | Réussite |
| installation_id | varchar(64) |  | Appareil demandeur (plafonds) |
| ip | inet |  | Adresse demandeuse (plafonds) |
| provider_ref / unit_cost_xof | varchar(80) / smallint |  | Référence du message et coût unitaire estimé (statistiques) |
| created_at | timestamptz | NN | Index (phone_e164, purpose, created_at DESC) |

### 9.5 devices — Appareils et sessions de l'application

Une ligne par installation connectée : jeton de rafraîchissement, jeton de notification, dernière activité. Les sessions du site utilisent les sessions de Django.

| Champ | Type | Contraintes | Description |
|---|---|---|---|
| id | uuid | PK |  |
| user_id | uuid | NN, FK→users, ON DELETE CASCADE |  |
| installation_id | varchar(64) | NN, UQ avec user_id | Identifiant d'installation généré par l'application |
| platform | varchar(8) | NN, CK(android, ios, web) |  |
| app_version / label | varchar(20) / varchar(120) |  | Version ; nom lisible (« Tecno Spark ») |
| refresh_hash / prev_refresh_hash | char(64) | UQ / — | Empreintes du jeton courant et du précédent (détection de réutilisation, grâce de 60 s) |
| refresh_expires_at | timestamptz | NN | + 30 jours |
| push_provider / push_token | varchar(8) / text | CK(expo, fcm, webpush) | Jeton de notification ; abonnement pour Web Push (priorité C) |
| push_invalid_at | timestamptz |  | Jeton déclaré invalide par le fournisseur |
| last_seen_at / last_ip | timestamptz / inet |  | Activité de l'appareil |
| revoked_at / created_at | timestamptz |  | Révocation ; création |

### 9.6 gerant_profiles — Profils de gérants

Extension 1-1 de `users` pour le rôle gérant. Les pièces sont des fichiers chiffrés du volume privé, lisibles seulement depuis l'administration.

| Champ | Type | Contraintes | Description |
|---|---|---|---|
| user_id | uuid | PK, FK→users |  |
| display_name / zone | varchar(120) / varchar(160) | — / NN | Nom commercial ; zone d'activité |
| verification_status | varchar(12) | NN, DEF 'pending', CK(pending, interview, verified, rejected) | La suspension est portée par `users.status` |
| verified_at / verified_by | timestamptz / uuid | — / FK→users |  |
| interview_notes | text |  | Jamais exposé par l'API publique |
| id_doc_type / id_doc_path / extra_doc_path | varchar(20) / varchar(255) | CK(id_card, passport, other) | Pièces chiffrées (volume privé) |
| docs_retain_until | date |  | Purge automatique des pièces |
| response_rate_30d / median_response_min | numeric(5,2) / integer |  | Caches recalculés chaque nuit |
| created_by | uuid | NN, FK→users | Administrateur créateur |
| created_at / updated_at | timestamptz | NN |  |

### 9.7 districts — Quartiers

Une ville au lancement ; la colonne `city` permet de ne rien casser avant l'arrivée d'une vraie table de villes (§6.4). Le point de référence du campus est un paramètre (`CAMPUS_REFERENCE`).

| Champ | Type | Contraintes | Description |
|---|---|---|---|
| id | uuid | PK |  |
| name / slug | varchar(80) | NN / UQ |  |
| city | varchar(40) | NN, DEF 'Parakou' |  |
| latitude / longitude | numeric(9,6) | NN | Point central |
| sort_order / is_active | smallint / boolean | NN |  |

### 9.8 listings — Annonces (chambres)

Les informations qui servent à filtrer sont des colonnes ; le reste est dans la description enrichie.

| Champ | Type | Contraintes | Description |
|---|---|---|---|
| id | uuid | PK |  |
| gerant_id | uuid | NN, FK→gerant_profiles(user_id) | Propriétaire |
| slug | varchar(160) | UQ, NN | URL publique lisible |
| title | varchar(120) | NN, CK(≥ 5 caractères) |  |
| room_type | varchar(40) | NN | Slug d'un type de `room_types` (amendement du 2026-10-17, décision V1) : 4 officiels (single, entree_coucher, chambre_salon, studio) et propositions des gérants, contrôlé par le service ; filtres et alertes sur les seuls types validés |
| district_id | uuid | NN, FK→districts |  |
| landmark_text | varchar(160) | NN | Repère public |
| address_private | varchar(255) |  | Visible des seuls participants d'une conversation |
| latitude / longitude | numeric(9,6) | NN | Position exacte ; l'API publique l'arrondit à 3 décimales (environ 110 m) |
| distance_to_campus_m | integer | NN | Calculée à l'enregistrement (formule de haversine) ; sert au tri et au filtre |
| rent_amount | integer | NN, CK(> 0) | Loyer mensuel en FCFA |
| deposit_months / advance_months | smallint | NN, CK(0 à 12) | Caution ; avance de loyer |
| agent_fee_amount | integer | NN, DEF 0, CK(≥ 0) | Frais de démarcheur en FCFA |
| available_from | date | NN |  |
| has_private_bathroom / is_fenced | boolean | NN | Douche et WC internes ; clôture ou portail |
| water_source | varchar(10) | NN, CK(running, well, borehole) |  |
| electricity_meter | varchar(10) | NN, CK(individual, shared) |  |
| description_md | text | NN, DEF '' | Markdown restreint assaini, 4 000 caractères au plus |
| description_html | text | NN, DEF '' | Rendu assaini, calculé une fois à l'enregistrement (pages web) |
| search_vector | tsvector |  | Titre, description en texte brut, quartier ; mis à jour par le service d'écriture |
| status | varchar(12) | NN, DEF 'draft', CK(draft, processing, published, hidden, rented, archived, removed) | Voir §11.1 |
| hidden_reason | varchar(16) | CK(stale, moderation, owner, gerant_suspended) |  |
| published_at / rented_at | timestamptz |  | Première publication ; passage à louée |
| last_confirmed_at / reminder_stage | timestamptz / smallint | — / NN, DEF 0 | Dernière confirmation de fraîcheur ; relances déjà envoyées (0, 1, 2) |
| created_at / updated_at / deleted_at | timestamptz | NN / NN / — | Suppression logique |

### 9.9 listing_media — Médias des annonces

Vidéos et photos ; porte aussi l'état de l'envoi reprenable (pas de table dédiée). Originaux jamais publics.

| Champ | Type | Contraintes | Description |
|---|---|---|---|
| id | uuid | PK |  |
| listing_id | uuid | NN, FK→listings, ON DELETE CASCADE |  |
| kind | varchar(5) | NN, CK(video, photo) |  |
| position / is_cover | smallint / boolean | NN, DEF 0 / NN, DEF false | Ordre ; couverture (une seule par annonce, index unique partiel) |
| status | varchar(12) | NN, DEF 'uploading', CK(uploading, uploaded, processing, ready, failed, deleted) | Voir §11.2 |
| declared_size_bytes / received_bytes | bigint | NN / NN, DEF 0 | Taille annoncée ; octets reçus (décalage de reprise tus) |
| upload_expires_at | timestamptz |  | Création + 24 h ; nettoyage des envois abandonnés |
| original_path | varchar(255) |  | Fichier d'origine dans `media_tmp` (supprimé 24 h après `ready`) |
| mime_type / size_bytes | varchar(60) / bigint |  | Constatés par ffprobe ou Pillow |
| sha256 | char(64) |  | Empreinte (détection de doublons ; index) |
| width / height / duration_s | integer / integer / numeric(6,2) |  |  |
| playback_path / poster_path | varchar(255) |  | Manifeste HLS ou variante principale ; affiche WebP |
| variants | jsonb |  | Photos : tailles ; vidéo : qualités produites |
| error_code / error_detail | varchar(40) / text |  | Motif d'échec affichable |
| delete_after / deleted_at | timestamptz |  | Suppression différée (vidéo d'une annonce louée) |
| created_at / updated_at | timestamptz | NN | Une seule vidéo active par annonce : index unique partiel (listing_id) où kind = 'video' et status hors deleted, failed |

### 9.10 daily_stats — Statistiques journalières

Compteurs agrégés par jour. Par annonce (vues, favoris, conversations) : compteurs Redis vidés toutes les 5 minutes par un `UPSERT`, déduplication par clé de visiteur avec expiration de 26 h. Globaux (inscriptions, OTP et coût des SMS, messages, conversations, recherches sans résultat, actifs du jour) : enregistrés chaque nuit. Ils survivent à la purge des lignes détaillées et fondent les statistiques de période longue.

| Champ | Type | Contraintes | Description |
|---|---|---|---|
| day | date | PK (1/3) | Jour, fuseau Africa/Porto-Novo |
| metric | varchar(32) | PK (2/3) | views, favorites_added, conversations_started, signups, otp_sent, sms_cost_xof, messages, active_users, search_empty… |
| subject | varchar(40) | PK (3/3), NN, DEF 'global' | `global` ou identifiant de l'annonce ; index (subject, day) |
| value | integer | NN, DEF 0 | Valeur du jour |

### 9.11 favorites — Favoris

| Champ | Type | Contraintes | Description |
|---|---|---|---|
| user_id | uuid | PK (1/2), FK→users |  |
| listing_id | uuid | PK (2/2), FK→listings | Index inverse (listing_id) pour la notification « plus disponible » |
| created_at | timestamptz | NN |  |

### 9.12 alerts — Alertes des locataires

La correspondance se fait en SQL à la publication ; l'unicité de la notification est portée par `notifications.dedupe_key`.

| Champ | Type | Contraintes | Description |
|---|---|---|---|
| id | uuid | PK |  |
| user_id | uuid | NN, FK→users, ON DELETE CASCADE | Maximum 5 alertes actives par utilisateur |
| label | varchar(80) |  |  |
| district_ids / room_types | uuid[] / varchar(16)[] | NN, DEF '{}' | Vide = tous ; index GIN sur district_ids |
| max_rent | integer |  |  |
| private_bathroom_required | boolean | NN, DEF false |  |
| max_distance_m | integer |  | Distance maximale au campus |
| is_active | boolean | NN, DEF true |  |
| created_at / updated_at | timestamptz | NN |  |

### 9.13 conversations — Conversations

Une par couple (annonce, locataire). Elle porte les colonnes de cache qui évitent de lire `messages` pour la liste et les non-lus.

| Champ | Type | Contraintes | Description |
|---|---|---|---|
| id | uuid | PK |  |
| listing_id | uuid | NN, FK→listings |  |
| client_id / gerant_id | uuid | NN, FK→users | Locataire ; gérant de l'annonce à la création. UQ (listing_id, client_id) |
| status | varchar(10) | NN, DEF 'open', CK(open, read_only, blocked) |  |
| blocked_by | uuid | FK→users | Participant ayant bloqué |
| last_seq | bigint | NN, DEF 0 | Dernier numéro attribué (verrou de ligne pour la séquence) |
| last_message_at / last_sender_id | timestamptz / uuid |  | Tri de la liste |
| last_message_preview | varchar(80) |  | Aperçu du dernier message (cache) |
| client_read_seq / gerant_read_seq | bigint | NN, DEF 0 | Positions de lecture ; non-lus = last_seq − position |
| client_muted_until / gerant_muted_until | timestamptz |  | Silence des notifications |
| first_reply_at | timestamptz |  | Première réponse du gérant (délai de réponse) |
| created_at / updated_at | timestamptz | NN | Index (client_id, last_message_at DESC) et (gerant_id, last_message_at DESC) |

### 9.14 messages — Messages

Texte seul. Le numéro `seq` est attribué dans la transaction d'insertion.

| Champ | Type | Contraintes | Description |
|---|---|---|---|
| id | uuid | PK |  |
| conversation_id | uuid | NN, FK→conversations, ON DELETE CASCADE |  |
| seq | bigint | NN | UQ (conversation_id, seq) |
| sender_id | uuid | FK→users | Vide pour un message système |
| client_msg_id | uuid | NN | UQ (conversation_id, sender_id, client_msg_id) : idempotence |
| kind | varchar(8) | NN, DEF 'text', CK(text, system) | Une valeur `image` pourra s'ajouter (§6.4) |
| body | text | NN, CK(longueur ≤ 2000) |  |
| flag_reason | varchar(24) |  | Motif de marquage (phone, link, keyword…) |
| moderation_status | varchar(12) | NN, DEF 'visible', CK(visible, masked, hidden, deleted) |  |
| notified_at | timestamptz |  | Posé après envoi du push, constat de lecture ou saut motivé (§11.9) ; sert au rattrapage (index partiel où nul) |
| created_at | timestamptz | NN |  |

### 9.15 notifications — Notifications

Centre de notifications, suivi de livraison et unicité (alertes) dans une seule table.

| Champ | Type | Contraintes | Description |
|---|---|---|---|
| id | uuid | PK |  |
| user_id | uuid | NN, FK→users, ON DELETE CASCADE | Destinataire |
| kind | varchar(40) | NN | Voir annexe B (message.received, alert.match…) |
| title / body | varchar(120) / varchar(255) | NN |  |
| data | jsonb | NN, DEF '{}' | Paramètres de navigation (conversation_id, listing_id…) |
| dedupe_key | varchar(120) | UQ (si non nul) | Par exemple alert:{alerte}:{annonce} ; empêche tout doublon |
| collapse_key | varchar(80) |  | Affichage groupé (conv:{id}) : remplace la notification précédente dans le tiroir du téléphone, ne fusionne jamais deux notifications |
| read_at | timestamptz |  |  |
| delivery_status | varchar(10) | NN, DEF 'pending', CK(pending, sent, partial, failed, skipped) | skipped : catégorie coupée, silence, ou conversation ouverte sur tous les appareils actifs |
| delivery_attempts / last_error | smallint / varchar(255) | NN, DEF 0 / — | Reprises (5 au plus) |
| delivered_at / created_at | timestamptz | — / NN | Index (user_id, created_at DESC) ; index partiel (user_id) où read_at est nul |

### 9.16 reports — Signalements

Alimentée par les utilisateurs et par les détections automatiques.

| Champ | Type | Contraintes | Description |
|---|---|---|---|
| id | uuid | PK |  |
| reporter_id | uuid | FK→users | Vide pour un signalement automatique |
| source | varchar(10) | NN, DEF 'user', CK(user, system) |  |
| target_type / target_id | varchar(12) / uuid | NN, CK(listing, message, user, conversation) |  |
| listing_id | uuid | FK→listings | Annonce concernée (filtre) |
| reason_code | varchar(24) | NN | fake_listing, already_rented, price_mismatch, contact_leak, harassment, scam, other |
| details | varchar(500) |  |  |
| status | varchar(18) | NN, DEF 'open', CK(open, in_review, resolved_actioned, resolved_dismissed) |  |
| assigned_to / resolved_by | uuid | FK→users |  |
| resolved_at / resolution_note | timestamptz / varchar(500) |  |  |
| created_at | timestamptz | NN | Index (status, created_at) ; un signalement ouvert par (reporter_id, target_type, target_id) |

### 9.17 moderation_actions — Actions de modération

Chaque sanction ou décision, avec sa durée et son éventuelle levée.

| Champ | Type | Contraintes | Description |
|---|---|---|---|
| id | uuid | PK |  |
| actor_id | uuid | NN, FK→users | Modérateur ou administrateur |
| report_id | uuid | FK→reports |  |
| action | varchar(20) | NN, CK(message_masked, message_deleted, listing_hidden, listing_removed, warning, suspension, ban, reinstatement) |  |
| target_user_id / target_listing_id / target_message_id | uuid | FK ; target_message_id ON DELETE SET NULL | Au moins une cible à la création ; le message supprimé par la purge laisse la ligne intacte |
| ends_at | timestamptz |  | Fin de la suspension |
| revoked_at / revoked_by | timestamptz / uuid |  | Levée |
| reason | text | NN | Motif communiqué à l'utilisateur |
| created_at | timestamptz | NN | Index (target_user_id, created_at DESC) |

### 9.18 audit_logs — Journal d'activité

Résistant à la modification : le rôle `app` n'a que `INSERT` et `SELECT`, et un déclencheur refuse `UPDATE`, `DELETE` et `TRUNCATE` (sauf au rôle de rétention, qui peut seulement vider `ip` et `user_agent` après 90 jours et supprimer à 24 mois). Une copie est exportée chaque jour hors du serveur. Regroupe les historiques de statuts, les accès aux conversations et les acceptations de CGU.

| Champ | Type | Contraintes | Description |
|---|---|---|---|
| id | bigint | PK, identité |  |
| actor_id / actor_role | uuid / varchar(12) | FK→users | Vide pour une tâche automatique |
| action | varchar(64) | NN | gerant.verified, listing.status_changed, conversation.read_by_staff, setting.changed, terms.accepted… |
| target_type / target_id | varchar(32) / uuid |  |  |
| metadata | jsonb | NN, DEF '{}' | Avant/après, motif, ancienne et nouvelle valeur |
| ip / user_agent | inet / varchar(255) |  |  |
| created_at | timestamptz | NN | Index (created_at), (actor_id, created_at), (target_type, target_id) ; partitionnement mensuel au palier 3 (purge par détachement de partition) |

### 9.19 app_settings — Paramètres, drapeaux et plans

Valeurs de l'annexe A modifiables sans redéploiement ; lues avec un cache court. Les plans d'abonnement y sont stockés (clé `PLANS`).

| Champ | Type | Contraintes | Description |
|---|---|---|---|
| key | varchar(64) | PK | Par exemple CONTACT_LEAK_MODE |
| value | jsonb | NN |  |
| description | varchar(255) | NN |  |
| updated_by / updated_at | uuid / timestamptz | FK→users / NN |  |

### 9.20 subscriptions — Abonnements (inactif)

| Champ | Type | Contraintes | Description |
|---|---|---|---|
| id | uuid | PK |  |
| gerant_id | uuid | NN, FK→gerant_profiles |  |
| plan_code | varchar(32) | NN | Code d'un plan de `app_settings.PLANS` (free_v1…) |
| status | varchar(10) | NN, CK(trialing, active, past_due, canceled, expired) |  |
| current_period_start / current_period_end | timestamptz | NN |  |
| cancel_at_period_end / canceled_at | boolean / timestamptz | NN, DEF false / — |  |
| created_at / updated_at | timestamptz | NN | Un seul abonnement non expiré par gérant (index unique partiel) |

### 9.21 payments — Paiements (inactif)

Contient aussi les événements de webhook reçus.

| Champ | Type | Contraintes | Description |
|---|---|---|---|
| id | uuid | PK |  |
| subscription_id / gerant_id | uuid | FK / NN, FK |  |
| amount / currency | integer / char(3) | NN, CK(≥ 0) / DEF 'XOF' | FCFA |
| provider | varchar(10) | NN, CK(sandbox, fedapay, kkiapay) |  |
| provider_ref | varchar(120) | UQ | Référence chez le fournisseur |
| method / payer_phone_e164 | varchar(12) / varchar(16) | CK(mtn_momo, moov_money) |  |
| status | varchar(10) | NN, DEF 'pending', CK(pending, succeeded, failed, refunded) |  |
| idempotency_key | varchar(64) | UQ, NN | Évite un double débit |
| webhook_events | jsonb | NN, DEF '[]' | Liste {event_id, received_at, signature_valid, payload} ; un événement déjà présent est ignoré |
| paid_at / created_at | timestamptz |  |  |

### 9.22 Requêtes critiques et index

Les huit requêtes qui portent la charge. Chacune est vérifiée avec `EXPLAIN` sur un jeu de 50 000 annonces et 1 million de messages avant la mise en ligne (§4.6).

| Requête | Index | Remarque |
|---|---|---|
| Fil et tri par date | listings (published_at DESC, id DESC) partiel où status = 'published' | Pagination par curseur (published_at, id), jamais par décalage. |
| Filtres quartier, loyer, distance | listings (district_id, rent_amount) et (distance_to_campus_m), partiels sur published | Index composés selon les filtres les plus fréquents. |
| Recherche texte | GIN sur search_vector ; GIN trigramme sur title | unaccent appliqué à l'enregistrement. |
| Liste des conversations | conversations (client_id, last_message_at DESC) et (gerant_id, last_message_at DESC) | Aucune lecture de messages ; non-lus = last_seq − position de lecture. |
| Historique d'une conversation | messages UQ (conversation_id, seq) | Lecture par `before_seq` ou `after_seq`. |
| Notifications non lues et liste | notifications partiel (user_id) où read_at est nul ; (user_id, created_at DESC) | Compteur par `COUNT` borné à 100. |
| Correspondance des alertes | alerts GIN (district_ids) ; filtre sur is_active | Table petite (environ 25 000 lignes au maximum). |
| Tâches planifiées (fraîcheur, rattrapage) | listings partiel (last_confirmed_at) où status = 'published' ; messages partiel (created_at) où notified_at est nul | Index partiels : coût proportionnel au travail à faire. |

### 9.23 Règles d'intégrité transverses

- Un locataire ne possède pas de `gerant_profiles` ; un gérant ne peut avoir qu'un profil et un seul abonnement non expiré.
- Une annonce ne passe à `published` que si le gérant est `verified` et actif, tous les champs obligatoires sont renseignés, une vidéo est `ready` et au moins 3 photos sont `ready`.
- La suppression d'un utilisateur anonymise `users` (nom, numéro, e-mail, photo remplacés), vide `otp_codes.phone_e164`, `payments.payer_phone_e164` et `devices.last_ip`, supprime ses appareils et conserve les lignes de modération et de journal (dont `ip` et `user_agent` sont vidés après 90 jours).
- `audit_logs` est résistant à la modification (§9.18) ; l'application se connecte avec un rôle sans droit de structure. Django exécute lui-même les suppressions en cascade : les purges passent par l'ORM, et les `ON DELETE` SQL sont posés en complément par migration.
- Les purges (OTP à 90 jours, envois expirés, originaux de plus de 24 h, pièces arrivées à échéance) sont des tâches planifiées (§11.10) qui laissent une trace dans `audit_logs`.
- Tables de django-otp, django-axes et de sessions : gérées par leurs paquets, hors du périmètre des 19 tables.

## 10. API et temps réel

Le mobile utilise l'API REST décrite ici. Le site n'appelle pas cette API : ses vues Django invoquent les mêmes services que l'API (§4.4), ce qui garantit les mêmes règles. Le détail des schémas de requête et de réponse est généré par OpenAPI (drf-spectacular) et fait foi. Chemins relatifs à `https://api.<domaine>/v1`. Accès : *public*, *client* (locataire), *pro* (gérant), *jeton OTP* (jeton court délivré après vérification d'un code), *participant* (d'une conversation).

### 10.1 Conventions

- **Authentification :** `Authorization: Bearer <jeton>` ; l'audience (client ou gerant) est contrôlée à chaque requête (`403 wrong_audience`). En-têtes attendus : `X-App-Version`, `X-Installation-Id`.
- **Pagination :** par curseur (`?cursor=`, `?limit=` ; 10 par défaut, 50 au plus) ; réponse `{results, next}`.
- **Idempotence :** `Idempotency-Key` sur les créations sensibles ; `client_msg_id` pour les messages.
- **Limites de débit :** `429` avec `Retry-After` ; plafonds par catégorie (annexe A).
- **Cache :** lectures publiques avec `ETag` et `Cache-Control` court ; réponses `304` acceptées par le mobile.
- **Compatibilité :** changements additifs seulement dans `/v1` (§6.1) ; champs inconnus ignorés par les clients.
Format d'erreur unique :

```
{
  "error": {
    "code": "otp_expired",
    "message": "Ce code a expiré. Demandez un nouveau code.",
    "fields": { "code": ["Code expiré"] },
    "request_id": "7c1f0c52-0d1e-4b36-a2a4-0f6f0d1e9c11"
  }
}
```

| Statut HTTP | Usage |
|---|---|
| 400 | Données invalides (`validation_error`), détail dans `fields` |
| 401 | Jeton absent, expiré ou invalide ; identifiants incorrects ou connexion temporairement verrouillée (`invalid_credentials`, avec `Retry-After` : réponse identique pour un numéro inconnu) |
| 403 | Droits insuffisants, mauvaise audience, compte suspendu (`account_suspended`) |
| 404 | Ressource introuvable ou non visible par l'appelant (on ne distingue pas les deux) |
| 409 | Conflit d'état (`listing_not_publishable`, `conversation_exists`) |
| 413 / 415 | Fichier trop gros ou format refusé |
| 426 | Version de l'application trop ancienne (mise à jour obligatoire) |
| 429 | Limite de débit atteinte |
| 503 | Maintenance ou coupe-circuit OTP (`otp_unavailable`) |

### 10.2 Configuration, authentification et compte

| Méthode et chemin | Accès | Description |
|---|---|---|
| GET /app-config | public | Version minimale, drapeaux actifs, maintenance, avis, constantes utiles (§6.2). |
| POST /auth/otp/request | public | Demande un OTP (numéro, usage). Réponse identique que le numéro existe ou non ; plafonds et coupe-circuit (§5.3). |
| POST /auth/otp/verify | public | Vérifie le code ; renvoie un jeton OTP valable 10 minutes. |
| POST /auth/register | jeton OTP | Crée le compte locataire : nom, mot de passe, CGU ; renvoie les jetons. |
| POST /auth/login | public | Numéro, mot de passe, identifiant d'installation ; renvoie le rôle, les jetons et crée l'appareil. |
| POST /auth/refresh | rafraîchissement | Rotation du jeton ; un ancien jeton rejoué après plus de 60 s révoque l'appareil, dans les 60 s il renvoie la même paire. |
| POST /auth/logout | connecté | Révoque l'appareil courant. |
| POST /auth/password/reset | jeton OTP | Nouveau mot de passe ; révoque tous les appareils. |
| POST /auth/password/change | connecté | Changement avec l'ancien mot de passe. |
| POST /ws-ticket | connecté | Ticket à usage unique de 30 s pour ouvrir le WebSocket. |
| GET · PATCH · DELETE /me | connecté | Profil, modification, demande de suppression. |
| POST /me/phone/change | connecté + jeton OTP | Changement de numéro : mot de passe actuel et OTP du nouveau numéro ; révoque les autres appareils et prévient l'ancien numéro. |
| GET · PUT /me/preferences | connecté | Préférences de notification (`users.notif_prefs`). |
| GET /devices · DELETE /devices/{id} | connecté | Liste et révocation des appareils. |
| PUT /devices/current/push-token | connecté | Enregistre le jeton de notification de l'appareil. |

### 10.3 Référentiels, fil, recherche et fiches

| Méthode et chemin | Accès | Description |
|---|---|---|
| GET /districts | public | Quartiers actifs. |
| GET /listings | public | Fil et recherche. Paramètres : `q`, `district`, `type`, `rent_min`, `rent_max`, `bathroom`, `water`, `meter`, `fenced`, `available_before`, `max_distance_m`, `sort` (recent, rent_asc, rent_desc, distance), `cursor`. Cartes légères (4 Ko au plus chacune). |
| GET /listings/{id} | public | Fiche : médias (URL de lecture), `description_md`, distance, gérant (nom, badge, délai de réponse). Ni numéro ni adresse privée. |
| POST /listings/{id}/views | public | Compte une vue (déduplication en cache). |
| POST /listings/{id}/report-rented | client | « Déjà louée » (EF-ANN-15). |
| GET /me/favorites · PUT · DELETE /me/favorites/{listing_id} | client | Favoris. |
| GET · POST /me/alerts · PATCH · DELETE /me/alerts/{id} | client | Alertes (5 au plus). |

### 10.4 Espace gérant (/pro)

| Méthode et chemin | Accès | Description |
|---|---|---|
| GET /pro/dashboard | pro | Indicateurs et liste « à faire ». |
| GET · POST /pro/listings | pro | Liste ; création d'un brouillon. |
| GET · PATCH · DELETE /pro/listings/{id} | pro | Lecture complète (dont adresse privée), modification, suppression d'un brouillon. |
| POST /pro/listings/{id}/publish | pro | Vérifie les règles du §9.23 ; `409 listing_not_publishable` avec les manques sinon. |
| POST /pro/listings/{id}/confirm | pro | Confirme la disponibilité (réinitialise la fraîcheur, réactive). |
| POST /pro/listings/{id}/mark-rented · …/undo-rented | pro | Passe à louée ; annule tant que la vidéo existe. |
| GET /pro/listings/{id}/stats | pro | Courbe de 30 jours. |
| POST /pro/markdown/preview | pro | Rend un texte en HTML assaini (aperçu de l'éditeur). |
| POST /pro/listings/{id}/media | pro | Crée un média et son envoi (type, taille, durée) ; renvoie `media_id` et `upload_url`. |
| HEAD · PATCH /uploads/{media_id} | pro | Protocole tus : décalage de reprise ; envoi d'un morceau (`Upload-Offset`, `Tus-Resumable`). Accepte le jeton (APP) ou la session + CSRF (WEB). Fin automatique quand `received_bytes` = taille déclarée. |
| GET /pro/listings/{id}/media | pro | États de traitement. |
| PATCH /pro/listings/{id}/media/order · DELETE …/media/{media_id} | pro | Ordre, couverture, suppression. |

### 10.5 Messagerie, notifications, signalements

| Méthode et chemin | Accès | Description |
|---|---|---|
| GET /conversations | client, pro | Liste (aperçu, non-lus, tri par activité) ; filtre `listing` pour le gérant. |
| POST /conversations | client | Ouvre ou retrouve la conversation d'une annonce et envoie le premier message : `listing_id`, `body`, `client_msg_id`. |
| GET /conversations/{id} | participant | Détail (annonce, participants, statut, adresse privée). |
| GET /conversations/{id}/messages | participant | Historique : `before_seq` ou `after_seq`, 50 par page. |
| POST /conversations/{id}/messages | participant | Envoi ; idempotent par `client_msg_id` ; renvoie le message avec `seq`. |
| POST /conversations/{id}/read | participant | Lecture jusqu'à `up_to_seq`. |
| PATCH /conversations/{id} | participant | Silence temporaire. |
| POST /conversations/{id}/block · …/unblock | participant | Blocage de la conversation par un participant. |
| GET /notifications · GET /notifications/unread-count | connecté | Centre et compteur. |
| POST /notifications/{id}/read · POST /notifications/read-all | connecté | Marquage comme lu. |
| POST /reports | client, pro | Signale une annonce, un message, une conversation ou un utilisateur. |

### 10.6 Abonnement (désactivé tant que le drapeau est faux)

| Méthode et chemin | Accès | Description |
|---|---|---|
| GET /pro/plans · GET /pro/subscription | pro | Plans (lus dans `app_settings`) ; abonnement courant. |
| POST /pro/subscription/checkout | pro | Démarre un paiement Mobile Money (clé d'idempotence obligatoire). |
| POST /pro/subscription/cancel | pro | Annule à la fin de la période. |
| POST /webhooks/payments/{provider} | signature | Reçoit les événements ; signature vérifiée, événement enregistré dans `payments.webhook_events`, traitement asynchrone. |

Tant que `SUBSCRIPTION_ENABLED` est faux, ces points d'entrée répondent `404 feature_disabled` et sont absents du schéma public.

### 10.7 Technique

| Méthode et chemin | Accès | Description |
|---|---|---|
| GET /healthz · GET /readyz | public | Vivacité ; disponibilité (base, Redis, disque). |
| GET /schema/ · GET /schema/docs/ | local seulement | OpenAPI et documentation interactive (désactivées en production). |

### 10.8 Protocole WebSocket

Une connexion par appareil sur `wss://…/ws/v1/?ticket=…` (ticket de `POST /ws-ticket`, usage unique, 30 s). L'origine est contrôlée. Chaque utilisateur rejoint son groupe `user.{id}` : tous ses appareils reçoivent les mêmes événements. **Le WebSocket ne sert qu'à recevoir** (et à signaler la conversation ouverte) ; l'envoi des messages passe par HTTP (§4.5). Enveloppe : `{ "type": "…", "data": { … } }`.

| Sens | Événement | Contenu et comportement |
|---|---|---|
| Client → serveur | conversation.focus | `conversation_id` ou nul : conversation ouverte à l'écran (supprime le push pour cet appareil tant que la connexion vit ; effacée à la déconnexion, au passage en arrière-plan et sans `ping` pendant 60 s). |
| Client → serveur | ping | Toutes les 25 s. |
| Serveur → client | message.new | Message complet, envoyé aux deux participants. |
| Serveur → client | conversation.read | `conversation_id`, `by`, `up_to_seq`. |
| Serveur → client | conversation.updated | Statut (annonce louée, lecture seule, blocage). |
| Serveur → client | notification.new | `unread_count` et résumé. |
| Serveur → client | error | Fermeture applicative : 4401 ticket invalide, 4403 compte suspendu, 4429 trop d'événements. |

- **Reconnexion :** temporisation 1, 2, 4, 8, 15 puis 30 s avec variation aléatoire ; à chaque reconnexion le client rattrape par `GET …/messages?after_seq=`.
- **Garanties :** le WebSocket livre au mieux (expiration et capacité des canaux Redis) ; la garantie est portée par HTTP : `after_seq` à la reconnexion et toutes les 30 s même connecté, doublons éliminés par `client_msg_id`, ordre par `seq`.
- **Protection :** 5 connexions par utilisateur, trame de 8 Ko, 30 événements entrants par minute, fermeture après 60 s sans `ping`.

### 10.9 Routes du site (WEB)

| Chemin | Accès | Contenu |
|---|---|---|
| / · /chambres · /chambres/{slug} · /quartiers/{slug} | public | Accueil, recherche (HTMX pour filtres et défilement), fiche, page de quartier. |
| /gerant · /cgu · /confidentialite | public | Explication pour les gérants, pages légales. |
| /inscription · /connexion · /mot-de-passe-oublie | public | Flux OTP et connexion par session. |
| /compte/favoris · /alertes · /messages · /notifications · /profil | locataire | Espace locataire ; messagerie liste/détail dès 1024 px. |
| /pro/tableau-de-bord · /annonces · /annonces/nouvelle · /messages · /profil | gérant | Espace gérant ; assistant de création avec aperçu et import de vidéo. |
| /sitemap.xml · /robots.txt · /manifest.webmanifest | public | Référencement et PWA. |

## 11. Règles métier

### 11.1 Cycle de vie d'une annonce

| Transition | Déclencheur | Effets |
|---|---|---|
| draft → processing | Publication alors qu'un média est en traitement, ou première annonce d'un gérant (relecture de sa vidéo par la modération) | En attente ; invisible du public ; passe seule à `published` quand le média est `ready` et la relecture faite. |
| draft / processing → published | Publication avec toutes les conditions du §9.23 | `published_at`, `last_confirmed_at` = maintenant, `reminder_stage` = 0 ; événement `listing.published`. |
| processing → draft | Échec du traitement de la vidéo | Notification avec motif ; le gérant remplace la vidéo. |
| published → hidden | Pas de confirmation à J+14 (`stale`), modération, choix du gérant, suspension du gérant | Retrait du fil et des pages publiques ; conversations ouvertes ; notification. |
| hidden → published | Confirmation, levée de la modération, rétablissement du gérant | Remise en ligne si les conditions sont toujours remplies ; fraîcheur réinitialisée. |
| published → rented | Le gérant marque l'annonce louée | `rented_at` = maintenant ; vidéo programmée pour suppression à J+7 ; conversations en lecture seule à J+30 ; notification aux locataires en conversation et aux favoris. |
| rented → published | Annulation avant suppression de la vidéo | `delete_after` effacé. Après suppression de la vidéo, republier exige une nouvelle vidéo (retour à `draft`). |
| rented → archived | 90 jours après la location | Retrait des pages publiques (les conversations sont en lecture seule depuis 30 jours après la location). |
| tout état → removed | Décision de modération ou d'administration | Retrait définitif de l'affichage ; conservation pour le journal. |

Chaque changement de statut écrit une ligne `listing.status_changed` dans `audit_logs` (ancien statut, nouveau statut, auteur, loyer avant et après).

### 11.2 Cycle de vie d'un média

| Transition | Règle |
|---|---|
| Quotas (création d'un envoi) | 1 vidéo et 10 photos par annonce ; 2 envois ouverts et 500 Mo en attente par gérant ; sinon `429 upload_quota`. Création refusée (`503 storage_full`) quand le disque des médias dépasse 85 %. |
| uploading → uploaded | `received_bytes` atteint `declared_size_bytes` ; fichier présent dans `media_tmp`. Un envoi inactif depuis 24 h est abandonné (`upload_expires_at`). |
| uploaded → processing | worker-media prend la tâche : ffprobe (conteneur mov, mp4 ou webm seulement, durée 10 à 60 s, 480p minimum), SHA-256, génération des dérivés par ffmpeg (format d'entrée forcé, `-protocol_whitelist file`, délai maximal). |
| processing → ready | HLS 360p et 720p avec affiche (vidéo) ; variantes WebP sans EXIF (photo). L'original est supprimé 24 h plus tard. |
| processing → failed | Fichier illisible, hors limites, délai de 10 min dépassé. `error_code` et message lisible ; réessai possible. |
| ready → deleted | Suppression par le gérant ou à `delete_after` : dérivés et original supprimés. |

### 11.3 Vérification d'un gérant

pending (compte créé, pièces déposées) → interview → verified (badge, plan « Gratuit V1 ») ou rejected. La suspension d'un gérant est celle de son compte (`users.status`, `suspended_until`) : ses annonces sont masquées, puis remises en ligne à la levée ; un modérateur peut la prononcer jusqu'à 30 jours. Il ne publie que s'il est verified et actif.

### 11.4 Signalements

open → in_review (attribué) → resolved_actioned ou resolved_dismissed (motif noté). Un signalement automatique (`source = system`) suit le même parcours. Trois signalements « déjà louée » distincts sur une annonce ouvrent un dossier unique.

### 11.5 Abonnement (quand il sera activé)

trialing → active ; active → past_due (grâce de 7 jours) → active ou expired ; active → canceled (fin de période) → expired. À l'expiration, annonces visibles 7 jours puis masquées (`hidden_reason = owner`). Règle à valider avant activation (§17).

### 11.6 Calculs et indicateurs

- **Distance au campus :** formule de haversine entre l'annonce et `CAMPUS_REFERENCE`, calculée par le service d'écriture à chaque changement de position et stockée dans `distance_to_campus_m` ; affichée arrondie à 50 m. Aucune extension géographique n'est nécessaire.
- **Délai de réponse :** temps entre le premier message du locataire et `first_reply_at` ; indicateur = médiane sur 30 jours glissants ; taux de réponse = part des conversations répondues sous 24 h ; recalculés chaque nuit dans `gerant_profiles`.
- **Vues :** clé de visiteur (compte ou installation) + annonce + jour déposée dans Redis avec `SET NX` (expiration 26 h) ; si la clé est neuve, le compteur du jour est incrémenté ; vidage dans `daily_stats` toutes les 5 min. Propriétaire et robots exclus.
- **Locations conclues :** annonces dont `rented_at` est renseigné, hors annulations dans le délai de grâce.

### 11.7 Détection des coordonnées

> **Amendement du 2026-10-18.** Dans la **messagerie**, le mode par défaut est `off` : aucun masquage, rappel ni
> signalement automatique ; les modes `mask`, `flag` et `block` restent activables dans les paramètres. Les **annonces**
> (titre, repère, description) continuent de refuser les coordonnées (EF-ANN-05).

But : garder les échanges dans Logeo sans gêner les conversations normales (les prix contiennent des chiffres). S'applique aux messages, titres, repères, adresses privées et descriptions. Produit un motif ; pour les signaux forts, l'action dépend de `CONTACT_LEAK_MODE` ; les mots-clés sont toujours seulement signalés.

| Signal | Règle | Poids |
|---|---|---|
| Numéro de téléphone | Au moins 8 chiffres à la suite (espaces, points, tirets tolérés) ou précédés de +229 ou 00229 ; montants suivis de FCFA, F ou CFA exclus. | Fort |
| Numéro épelé ou codé | Au moins 6 chiffres écrits en lettres à la suite, ou mélange de chiffres et de lettres de substitution. | Fort |
| Adresse e-mail | Motif `nom@domaine`. | Fort |
| Lien ou domaine | URL, `www.`, noms de domaine, raccourcisseurs, liens de messageries. | Fort |
| Mots-clés | Noms d'applications externes (WhatsApp et variantes, Telegram, Facebook…), « appelle-moi », « mon numéro ». | Faible |

| Mode | Effet |
|---|---|
| mask (défaut) | Messages : séquences détectées remplacées par des étoiles côté destinataire, texte d'origine consultable par la modération, rappel à l'expéditeur, signalement automatique. Annonces : enregistrement refusé avec explication. |
| flag | Messages : livrés tels quels mais marqués (`flag_reason`), rappel à l'expéditeur, signalement automatique. À réserver aux essais : il laisse passer le contact. |
| block | Message non envoyé, motif affiché. Réservé aux récidivistes (faux positifs). |

> **Limite assumée :** aucune détection n'arrête un utilisateur déterminé, et les vidéos et photos ne sont pas analysées automatiquement (numéro dit ou incrusté) : la première vidéo de chaque gérant est relue par la modération, les signalements couvrent le reste. La parade principale est la valeur de rester : réponse rapide, adresse précise donnée dans la conversation, notifications fiables, gérants vérifiés.

### 11.8 Texte enrichi de la description

Sous-ensemble de Markdown identique partout. Le serveur l'analyse (markdown-it-py en liste blanche), assainit le résultat (nh3), enregistre `description_md` et `description_html`. Le site affiche le HTML ; l'application affiche le Markdown avec un moteur natif limité aux mêmes éléments. Un jeu de tests commun (mêmes entrées, rendus attendus) vérifie que les deux rendus restent équivalents.

| Mise en forme | Syntaxe stockée | Remarque |
|---|---|---|
| Gras · italique · barré | `**texte**` · `*texte*` · `~~texte~~` | Boutons G, I, S |
| Titre | `### Titre` | Un seul niveau |
| Listes | `- élément` · `1. élément` | 40 lignes de liste au plus |
| Paragraphes | ligne vide ; deux espaces en fin de ligne |  |
| Interdit | liens, images, HTML, tableaux, code, citations | Retiré à l'enregistrement : bloque aussi les contacts et le contenu actif |

### 11.9 Émission des notifications de message

1. Un message est enregistré ; le destinataire est l'autre participant. Après la transaction (`on_commit`), `message.new` est diffusé par WebSocket (§4.5) et la création de la notification est placée dans la file `notifications`.
2. La présence « conversation ouverte » est portée par la connexion WebSocket : posée par `conversation.focus`, effacée à la déconnexion, au passage de l'application en arrière-plan et après 60 s sans `ping`. Elle ne vit jamais seule.
3. Une notification est créée pour chaque message (`collapse_key` ne sert qu'à l'affichage groupé).
4. Si la catégorie est coupée ou la conversation en silence, la notification est créée avec `delivery_status = skipped`.
5. Si la conversation est ouverte sur un appareil connecté, aucun push n'est envoyé à cet appareil ; les autres appareils actifs reçoivent le push, contenu selon l'aperçu choisi.
6. En cas d'échec : 5 reprises à temporisation croissante ; un jeton invalide est désactivé (`push_invalid_at`).
7. `messages.notified_at` n'est posé qu'après l'envoi du push au fournisseur, ou lorsque le message est constaté lu (position de lecture ≥ `seq`), ou pour un saut motivé (catégorie coupée, silence). Un push supprimé par la présence ne le pose pas.
8. Le rattrapage, chaque minute, relance tout message sans `notified_at` ni lecture depuis plus de 30 s ; si l'application est passée en arrière-plan ou a perdu le réseau, le push part donc quand même.
9. Un message adressé à un gérant resté non lu après 2 h déclenche un rappel (push ; SMS si le drapeau le permet).

### 11.10 Tâches planifiées

| Tâche | Fréquence | Rôle |
|---|---|---|
| sweep_unnotified_messages | Chaque minute | Rattrape les messages sans notification (§11.9). |
| flush_view_counters | 5 minutes | Vide les compteurs Redis dans `daily_stats`. |
| remind_unanswered_messages | 10 minutes | Rappel aux gérants (message non lu depuis 2 h). |
| expire_sanctions | 10 minutes | Lève les suspensions échues et rétablit les annonces. |
| abort_expired_uploads | 15 minutes | Abandonne les envois expirés et libère le disque. |
| remind_stale_listings / hide_stale_listings | Horaire | Relances J+7 et J+10 ; masquage à J+14. |
| delete_rented_videos · delete_originals | Horaire | Supprime les vidéos échues et les originaux de plus de 24 h. |
| subscription_lifecycle | Horaire | Sans effet tant que le drapeau est faux. |
| nightly_aggregates | Quotidien, 02:00 | Recalcule les caches des gérants ; enregistre les compteurs globaux du jour dans `daily_stats` ; passe en lecture seule les conversations des annonces louées depuis 30 jours ; archive les annonces louées depuis 90 jours. |
| purge_retention | Quotidien | Purge OTP (90 jours), pièces échues, conversations échues (messages supprimés par l'ORM), adresses IP anciennes du journal ; trace dans `audit_logs`. |

Les sauvegardes ne passent pas par Celery : elles sont lancées par le conteneur `backup`, pour qu'une panne de Celery ne les interrompe pas. Chaque tâche est idempotente et prend un verrou Redis si elle ne doit pas s'exécuter deux fois en parallèle.

### 11.11 Lecture d'une conversation par le personnel

- Le modérateur ou l'administrateur ouvre une conversation depuis un dossier ou une recherche ; l'interface exige un motif (liste + précision) **avant** l'affichage.
- L'ouverture écrit `conversation.read_by_staff` dans `audit_logs` (auteur, conversation, motif, adresse IP) ; l'affichage reste en lecture seule et met en évidence les messages marqués.
- Au-delà de 20 ouvertures par jour pour un même compte, une alerte est envoyée au porteur du projet. Les participants sont informés de cette possibilité par les CGU (EF-AUT-10).

## 12. Écrans

### 12.1 Principes d'interface

- **Navigation mobile :** barre d'onglets en bas (locataire : Accueil, Recherche, Messages, Alertes, Profil ; gérant : Tableau de bord, Annonces, Messages, Profil). Action principale en bas de l'écran.
- **États systématiques :** chargement (squelettes), vide (avec une action), erreur (message clair et « Réessayer »), hors connexion (bandeau et cache).
- **Design :** jeu de composants unique et de variables de style communes (couleurs, espacements, typographie) pour l'application et le site, afin que les deux surfaces soient reconnues comme une seule marque ; la maquette interactive existante (20 écrans) sert de point de départ.
- **Site sans Node :** CSS pur assemblé par `make css`, composants en gabarits Django réutilisables (`{% include %}`), icônes SVG intégrées, polices du système.

### 12.2 APP — espace locataire

| Écran | Contenu et comportements clés |
|---|---|
| Accueil (fil) | Cartes d'annonces avec affiche ; lecture de la carte visible en connexion rapide, à l'appui en économie de données ; filtres rapides ; tirer pour actualiser. |
| Recherche et filtres | Champ de recherche, feuille de filtres (EF-REC-05), tris, résultat vide avec proposition d'alerte. |
| Fiche annonce | Vidéo, galerie, caractéristiques, description, quartier, distance, badge ; Contacter, Favori, Partager, Signaler, « Déjà louée ». |
| Inscription et connexion | Numéro → OTP → nom et mot de passe ; connexion ; mot de passe oublié ; CGU ; message du coupe-circuit OTP. |
| Messages | Liste (non-lus, aperçu) ; conversation avec carte d'annonce, statuts (en attente, envoyé, lu), bandeau si louée, rappel de sécurité, blocage, signalement. |
| Alertes · Favoris · Notifications | Création et édition d'alertes ; favoris avec état ; centre de notifications avec accès direct. |
| Profil et réglages | Nom, photo, mot de passe, appareils, préférences, économie de données, aide, CGU, suppression du compte. |
| Mise à jour obligatoire · Maintenance | Écrans plein cadre pilotés par `app-config`. |

### 12.3 APP — espace gérant

| Écran | Contenu et comportements clés |
|---|---|
| Connexion | Connexion avec le numéro et le mot de passe attribués par l'administration ; consigne d'exclusion de l'économie de batterie. |
| Tableau de bord | Indicateurs et liste « à faire ». |
| Mes annonces | Liste par statut ; modifier, confirmer, marquer louée, annuler. |
| Assistant de création | Informations clés, localisation (position actuelle, ajustement), équipements, médias (choix de la vidéo, compression, envoi avec progression et reprise, photos), description (barre de mise en forme, aperçu, détection de coordonnées), publication. Brouillon enregistré à chaque étape. |
| Statistiques d'une annonce | Courbe de 30 jours : vues, conversations, favoris. |
| Messages · Notifications · Profil | Mêmes écrans que le locataire avec filtre par annonce, adresse précise visible, statut de vérification. |
| Mon abonnement (masqué) | Visible seulement si le drapeau est actif. |

### 12.4 WEB — site

| Zone | Contenu et comportements clés |
|---|---|
| Pages publiques | Accueil, recherche, fiche, quartier, « Je suis gérant », pages légales ; rendu serveur, Open Graph, sitemap. |
| Espace locataire (/compte) | Connexion et inscription, favoris, alertes, messages (liste et conversation côte à côte dès 1024 px, WebSocket), notifications, profil. |
| Espace gérant (/pro) | Tableau de bord, annonces, assistant de création sur une page avec éditeur à barre d'outils et aperçu, import de vidéo avec envoi reprenable, messages, profil. |
| PWA | Manifeste, icônes, installation proposée, page minimale hors connexion. |

### 12.5 ADM — administration

| Écran | Contenu et comportements clés |
|---|---|
| Connexion | E-mail + mot de passe puis TOTP ; configuration de la 2FA au premier accès ; messages neutres. |
| Tableau de pilotage | Indicateurs du §2 et résumé du jour (inscriptions, annonces, conversations, signalements ouverts, alertes techniques). |
| Statistiques | Catalogue du §7.10 : filtres de période, courbes, tableaux triables, export CSV. |
| Gérants | Création, pièces justificatives (affichage déchiffré à la demande, journalisé), entretien, statut, badge, suspension. |
| Utilisateurs · Annonces | Recherche, fiche complète, sanctions, appareils, masquage, retrait, restauration. |
| File de modération | Signalements et détections ; attribution ; ouverture d'une conversation avec motif (§11.11) ; actions et notifications. |
| Journal d'activité | Filtres par acteur, action, cible, période ; export CSV. |
| Paramètres et drapeaux | Annexe A ; chaque modification journalisée avec ancienne et nouvelle valeur. |
| Personnel | Comptes modérateur et administrateur, réinitialisation de 2FA, désactivation. |
| Abonnements (inactif) | Plans et configuration ; aucune action de facturation tant que le drapeau est faux. |

## 13. Environnement, déploiement et exploitation

Tout le développement se fait en local avec les mêmes services qu'en production. Le passage à un serveur ne demande que de la configuration, grâce à un seul fichier Compose et à des services externes derrière des interfaces.

### 13.1 Services locaux (Docker Compose)

| Service | Image ou commande | Port | Rôle |
|---|---|---|---|
| db | postgres:16 | 5432 | PostgreSQL ; extensions pg_trgm et unaccent activées par migration ; rôles `app`, `admin_app` et `migrate` |
| redis-cache · redis-queue | redis:7 (deux instances) | 6379 · 6380 | Cache et limites · files Celery et canaux |
| web-api | image serveur, réglages `public`, `runserver` avec rechargement | 8000 | Site et API ; documentation OpenAPI locale |
| realtime | image serveur, Uvicorn | 8001 | WebSocket |
| admin | image serveur, réglages `admin` | 8002 | Administration (hôte `pilotage.localhost`) |
| worker · worker-media · beat | image serveur (Celery, ffmpeg inclus) | — | Tâches, médias, planification |
| caddy (facultatif en local) | caddy:2 | 80 | Reproduit le routage par hôte (`www.localhost`, `api.localhost`, `pilotage.localhost`) |
| tailwind (profil `dev`) | exécutable autonome, mode surveillance | — | Compile la CSS du site |

L'application mobile ne tourne pas dans Docker : le serveur de développement Expo s'exécute sur l'ordinateur et l'application joint l'API par l'adresse du réseau local (`http://192.168.x.x:8000`). Les notifications push réelles exigent un appareil physique et Internet ; en local, le fournisseur `console` les écrit dans les journaux. Node n'est nécessaire que sur les postes de développement et en CI mobile, jamais dans les images de production.

### 13.2 Démarrage

```
cp .env.example .env     # valeurs locales prêtes à l'emploi
make up                  # db, redis x2, web-api, realtime, admin, workers, beat
make migrate             # migrations (extensions, tables, déclencheur d'audit)
make seed                # quartiers, paramètres, comptes de test
make css                 # assemble la CSS
make test                # tests du serveur, import-linter, contrôles de schéma
cd mobile && npx expo start    # application (appareil réel ou émulateur)
```

### 13.3 Variables d'environnement

| Variable | Valeur locale | Production |
|---|---|---|
| DJANGO_SETTINGS_MODULE | config.settings.local | config.settings.public ou config.settings.admin selon le conteneur |
| SECRET_KEY · JWT_SIGNING_KEY | valeurs de développement | secrets longs et uniques ; **différents** pour public et admin |
| DATABASE_URL (app) · DATABASE_URL_ADMIN · DATABASE_URL_MIGRATE | postgres://app:app@db/logeo · postgres://admin_app:… · postgres://migrate:… | trois rôles distincts ; connexion interne uniquement ; chaque URL n'est injectée que dans les conteneurs qui en ont besoin |
| REDIS_CACHE_URL · REDIS_QUEUE_URL | redis://redis-cache:6379/0 · redis://redis-queue:6379/0 | idem, avec mot de passe |
| DOMAIN · ADMIN_HOST · ALLOWED_HOSTS · ADMIN_ALLOWED_IPS | localhost, pilotage.localhost, vide | domaines réels ; liste blanche d'IP ou VPN obligatoire pour l'administration |
| MEDIA_ROOT_PUBLIC · MEDIA_ROOT_TMP · MEDIA_ROOT_PRIVATE | volumes locaux | volumes du serveur (§4.3) ; clé de chiffrement `PRIVATE_FILES_KEY` hors base, injectée seulement dans admin et backup |
| STORAGE_PROVIDER · VIDEO_PROVIDER | local · local_ffmpeg | local (puis s3) · local_ffmpeg |
| SMS_PROVIDER · PUSH_PROVIDER | console · console | agrégateur retenu · expo ou fcm |
| OTP_ALLOWED_COUNTRIES · OTP_DAILY_BUDGET | BJ · 300 | BJ · valeur validée avec le devis SMS |
| PAYMENT_PROVIDER · SUBSCRIPTION_ENABLED | sandbox · false | fedapay ou kkiapay · false jusqu'au lancement |
| CONTACT_LEAK_MODE | off | off (modifiable ensuite en base) |
| OTP_DEBUG_CODE | 123456 (local seulement) | interdit : le démarrage échoue s'il est défini |
| SENTRY_DSN · TURNSTILE_SECRET | vides | valeurs de production |
| EXPO_PUBLIC_API_URL | http://192.168.x.x:8000/v1 | https://api.<domaine>/v1 |
| TIME_ZONE | Africa/Porto-Novo | Africa/Porto-Novo |

Un fichier d'environnement par service, sans les secrets des autres. Pour les paramètres marqués « base » à l'annexe A (par exemple `OTP_ALLOWED_COUNTRIES`, `OTP_DAILY_BUDGET`, `CONTACT_LEAK_MODE`, `SUBSCRIPTION_ENABLED`), la variable d'environnement n'est que la valeur initiale chargée au premier démarrage ; ensuite la valeur de `app_settings` fait foi.

### 13.4 Déploiement et exploitation

| Sujet | Dispositif |
|---|---|
| Serveur | VPS Linux de 4 vCPU, 8 Go, 160 Go SSD ; script d'installation `infra/bootstrap.sh` : Docker, utilisateur non-root, SSH par clé sans connexion root, pare-feu (80 et 443 en TCP, 443 en UDP pour HTTP/3, SSH restreint), fail2ban, mises à jour de sécurité automatiques, conteneurs non-root avec `no-new-privileges` et capacités retirées, PostgreSQL et Redis sans port publié. Région choisie après mesure de latence (§15.2). |
| Livraison | Intégration continue : tests, construction de l'image, publication sur un registre. Déploiement par un script : tirer l'image, exécuter la tâche `migrate` (rôle `migrate`), redémarrer web-api, realtime, admin, workers, vérifier `/readyz`. Retour arrière : relancer l'étiquette précédente (migrations compatibles, §6.1). |
| Sauvegardes | Conteneur `backup` : archivage continu des journaux de transaction PostgreSQL (WAL, outil retenu en phase 0) vers un stockage externe d'un autre fournisseur, chaque nuit `pg_dump`, et sauvegarde incrémentale des volumes `media_public` et `media_private` avec restic (chiffré) ; rétention 14 jours quotidiens et 8 hebdomadaires. Les secrets (`PRIVATE_FILES_KEY`, clés JWT, fichiers d'environnement, état des certificats) sont conservés chiffrés hors du serveur, dans un coffre de l'équipe, et font partie du test de restauration. Script de restauration testé sur serveur vierge (ENF-DISP-05). Alerte si une sauvegarde manque. |
| Supervision | Sonde externe sur `/readyz` toutes les minutes ; Sentry sans données personnelles ; alertes disque, mémoire, file Celery, coupe-circuit OTP, échecs de push ; journaux Docker avec rotation (10 Mo × 5) ; `pg_stat_statements` ; Netdata en option. |
| Environnements | Local ; préproduction (même Compose sur un petit serveur ou temporaire, avant chaque version majeure) ; production. |
| Application mobile | Builds Expo (EAS, ou builds locaux) par environnement ; compte développeur Google Play ; versions et canaux ; mises à jour JavaScript à distance pour les correctifs (§6.2). |

### 13.5 Liste de contrôle « prêt pour l'hébergement »

- Dockerfile de production multi-étapes, `docker-compose.prod.yml` avec Caddy et HTTPS automatique, limites de CPU et de mémoire par conteneur, un fichier d'environnement par service.
- Aucun chemin local ni adresse figée dans le code : tout vient des variables d'environnement.
- Fichiers statiques et médias servis par Caddy, jamais par Django ; `collectstatic` à la construction de l'image.
- Migrations exécutées avant le démarrage des nouvelles versions ; compatibilité avec la version précédente vérifiée par le linter.
- `/healthz` et `/readyz` branchés sur les contrôles de santé Docker et sur la sonde externe.
- Sauvegarde automatique et restauration testée ; alertes actives.
- En-têtes de sécurité, CSP, HSTS, `ALLOWED_HOSTS`, cookies `__Host-` configurés pour les domaines réels.
- Durcissement du serveur appliqué comme décrit au §13.4 (pare-feu, SSH, conteneurs non-root, aucun port de base publié).
- Application : variables de build par environnement, signature des builds, fiche du magasin.
- Procédure de déploiement et de retour arrière écrite et répétée au moins une fois sur un serveur de test.

## 14. Tests, qualité et livraison

### 14.1 Stratégie de tests

| Niveau | Outils | Portée |
|---|---|---|
| Services et règles (serveur) | pytest, pytest-django, factory_boy | Règles métier (fraîcheur, détection, OTP, statuts), permissions ; couverture d'au moins 80 % sur comptes, messagerie, annonces. |
| API et autorisations | pytest, schemathesis sur OpenAPI | Tous les endpoints ; matrice endpoint × rôle ; idempotence ; absence de numéro et d'adresse privée dans les réponses publiques. |
| Requêtes SQL | `assertNumQueries`, EXPLAIN sur jeu volumineux | Plafonds du §4.6 ; plans des huit requêtes du §9.22. |
| Temps réel | channels.testing | Ordre, doublons, reprise, accusés de lecture, multi-appareils, ticket, limites. |
| Site | Django test client, Playwright, axe | Vues et gabarits, parcours de bout en bout sur Chrome, accessibilité, CSP (aucune violation), XSS. |
| Application | Jest, React Native Testing Library, Maestro | Composants, parcours sur émulateur et sur l'appareil de référence. |
| Architecture | import-linter, oasdiff, django-migration-linter | Frontières, compatibilité d'API, migrations sûres. |
| Charge et performance | k6 (HTTP et WebSocket), Lighthouse | Trois fois la capacité (ENF-CAP-01) ; cibles du §8.1. |
| Sécurité | pip-audit, bandit, détection de secrets, ZAP passif, scénarios d'abus | Dépendances, code, en-têtes, ASVS niveau 1, pompage d'OTP, force brute. |

### 14.2 Scénarios de recette de bout en bout

Automatisés quand c'est possible, joués à la main sur appareils réels avant la mise en ligne ; ils valident que les surfaces communiquent et que l'architecture tient.

| N° | Scénario |
|---|---|
| 1 | Un visiteur s'inscrit par OTP sur APP, définit son mot de passe, se déconnecte, puis se connecte avec son numéro sur WEB. |
| 2 | L'administration crée un gérant ; il active son compte sur APP et voit l'espace gérant ; un compte locataire ne l'ouvre pas ; un compte du personnel ne peut se connecter ni à APP ni à WEB ; un gérant ne peut pas se connecter à ADM. |
| 3 | Le gérant publie une annonce avec une vidéo de 40 Mo depuis la galerie sur APP ; le réseau est coupé en cours d'envoi, l'envoi reprend sans repartir de zéro ; même parcours depuis WEB ; l'annonce devient visible quand la vidéo est prête. |
| 4 | Le gérant édite la description sur WEB (gras, italique, liste) avec aperçu ; le rendu est équivalent sur APP et sur le site. |
| 5 | Un locataire sur WEB trouve l'annonce par filtres, contacte le gérant ; le gérant reçoit le push sur APP, répond ; le locataire voit la réponse en temps réel et l'accusé de lecture. WebSocket coupé : le repli par interrogation livre le message sans perte ni doublon ; application du gérant passée en arrière-plan ou réseau coupé puis rétabli : le push part quand même. |
| 6 | Un message contenant un numéro est marqué, l'expéditeur reçoit le rappel, un dossier apparaît dans ADM ; le modérateur ouvre la conversation avec un motif (ligne dans `audit_logs`) et masque le message. |
| 7 | Un locataire crée une alerte ; la publication d'une annonce correspondante déclenche une seule notification, même après une republication. |
| 8 | Le gérant marque l'annonce louée ; la vidéo disparaît 7 jours plus tard (horloge avancée) ; une annulation avant l'échéance la conserve. |
| 9 | Fraîcheur : relances à J+7 et J+10, masquage à J+14, confirmation qui remet en ligne. |
| 10 | Suspension d'un gérant : annonces masquées, écriture refusée, levée qui les rétablit. |
| 11 | Abonnement inactif : aucun écran ni endpoint ; en test, l'activation du drapeau refuse la publication sans abonnement actif et la permet après un paiement factice. |
| 12 | Réseau dégradé (3G simulée, appareil de référence) : fil, vidéo et messagerie respectent le §8.1. |
| 13 | Sécurité de l'administration : la route d'administration est introuvable sur www et api ; 5 échecs verrouillent le compte ; changer d'adresse IP ne donne aucun essai de plus ; un compte sans 2FA ne peut que la configurer ; hors liste blanche, l'hôte répond 404. |
| 14 | Abus d'OTP : le dépassement d'un plafond est refusé ; le coupe-circuit répond `otp_unavailable` et déclenche l'alerte. |
| 15 | Une version d'application inférieure au minimum affiche l'écran de mise à jour obligatoire ; un champ inconnu dans une réponse ne casse pas l'application. |
| 16 | Restauration : un serveur vierge est remis en service depuis les sauvegardes et le coffre des secrets en moins de 4 h, avec une perte de données inférieure à 5 min. |
| 17 | Charge : à trois fois la capacité, p95 de l'API et des messages dans les cibles ; un transcodage en cours ne dégrade pas l'API. |

### 14.3 Intégration continue et livraison

- **À chaque demande de fusion :** ruff, ESLint, TypeScript strict ; tests unitaires et d'API ; import-linter ; schéma OpenAPI généré et comparé (oasdiff) ; migrations contrôlées ; plafonds de requêtes SQL ; audit des dépendances ; compilation de la CSS ; construction des images.
- **Sur la branche principale :** tests de bout en bout du site (Playwright), publication des images, déploiement sur la préproduction.
- **Avant chaque version :** tests de charge, recette du §14.2, restauration de sauvegarde, builds mobiles signés.
- **Branches :** courtes, fusion après revue par l'autre développeur ; commits « type: description ».

### 14.4 Définition de « terminé »

Une exigence est terminée quand : le code est fusionné après revue ; ses cas nominaux, d'erreur et d'autorisation sont testés ; elle fonctionne sur toutes ses surfaces (§7) ; les textes sont en français ; les états de chargement, vide et erreur sont traités ; elle respecte les budgets de latence et de poids ; les contrôles de sécurité du §5 s'y appliquent ; OpenAPI et ADR sont à jour ; elle a été essayée sur l'appareil de référence.

## 15. Plan de réalisation

*(Les sprints d'origine sont remplacés par les phases du prompt, §12 ; seules les vérifications techniques sont conservées.)*

### 15.2 Vérifications techniques de la phase 0

Ces points reposent sur des composants dont la compatibilité ou la performance doit être constatée sur du matériel réel avant d'engager le reste. Chacun a un critère de réussite et un repli, de sorte qu'un échec change un module, pas l'architecture.

| Vérification | Critère de réussite | Repli |
|---|---|---|
| tus-js-client dans Expo, à travers Caddy et Django : fichier de la galerie de 50 Mo, morceaux de 1 Mo, 3G simulée, coupure réseau en cours d'envoi | Reprise au bon décalage, sans repartir de zéro ; aucun refus 413 | Envoi par morceaux avec l'API de fichiers d'Expo et `PATCH` tus écrit à la main |
| Compression vidéo sur un Android d'entrée de gamme (react-native-compressor, build de développement) | Vidéo de 40 s en 1080p ramenée sous 30 Mo en moins de 2 minutes | Envoi sans compression (limite 150 Mo) et transcodage serveur seul |
| Push : Expo Push contre FCM direct | Livraison sous 10 s sur 3 téléphones, application fermée | L'autre fournisseur (interface `PushProvider`) |
| Thème d'administration (django-unfold ou équivalent) | Compatible avec la version de Django retenue ; tableaux de bord et 2FA fonctionnels | Administration standard et feuille de style maison |
| Latence depuis Parakou vers 3 régions d'hébergement (MTN, Moov, Celtiis) | Région la plus rapide retenue ; objectif de RTT mesuré consigné | — |
| Devis SMS (au moins 2 agrégateurs) : prix, délai d'identifiant d'expéditeur, délivrabilité | Coût par OTP et budget quotidien (`OTP_DAILY_BUDGET`) chiffrés | Second agrégateur ; repli vocal pour le code (§17) |
| Transcodage sur le serveur choisi (60 s en 1080p) | Moins de 5 minutes avec l'API sous charge | Serveur plus gros ou vidéo managée |
| Channels derrière Caddy : 500 connexions et 200 messages par minute | p95 sous 1 s | Interrogation seule en attendant correction |
| Attestation d'appareil (Play Integrity) pour l'OTP et défi Turnstile sur le site | Une installation falsifiée est refusée ; l'inscription légitime passe en moins de 30 s | Plafonds réduits sans attestation, défi anti-robot seul |
| Archivage continu des WAL et restauration à un instant donné | Perte inférieure à 5 min constatée sur un serveur vierge | Copie logique plus fréquente (toutes les heures) en attendant |
| Calendrier de support de Django et versions des paquets | Version retenue et figée dans les fichiers de verrouillage | — |

## 17. Points à confirmer

Hypothèses retenues faute de décision ou d'information complète. Chacune se change sans refaire le reste, sauf mention contraire.

| N° | Point | Hypothèse retenue et conséquence |
|---|---|---|
| 1 | Rôle du modérateur | Il peut lire toutes les conversations avec motif obligatoire et accès journalisé. À confirmer : toutes, ou seulement celles qui ont été signalées. Une lecture limitée protège mieux la vie privée mais empêche de repérer une fraude non signalée. |
| 2 | Un compte = un rôle | Un gérant qui cherche aussi une chambre utilise un autre numéro. Autoriser un double rôle est possible mais complique l'espace d'application et la matrice de permissions. |
| 3 | Android seul au lancement | Le code React Native permet iOS ; la publication demande un compte développeur payant et des vérifications supplémentaires. À décider selon le public réel. |
| 4 | Fournisseur et coût des SMS | Pas de service gratuit : Firebase Phone Auth est écarté (plan Blaze requis, sans quota SMS gratuit). Tarifs relevés auprès de sources tierces : environ 0,15 € par SMS international (soit 95 à 113 FCFA) contre 8 à 25 FCFA via des opérateurs locaux ; l'enregistrement d'un identifiant d'expéditeur prend environ 4 semaines. **À confirmer par devis** avant de fixer `OTP_DAILY_BUDGET` ; l'enregistrement de l'identifiant est à lancer dès la phase 0. |
| 5 | Repli de l'OTP | Aucun repli au départ (pas de WhatsApp). Un appel vocal pour dicter le code sera évalué si la délivrabilité mesurée est insuffisante. |
| 6 | Hébergeur et région | Non décidés : choix après mesure de latence depuis Parakou (§15.2). Une région africaine n'est retenue que si son fournisseur offre un SLA et des sauvegardes comparables. |
| 7 | Liste blanche d'IP de l'administration | Obligatoire en production : liste blanche d'adresses ou, si elles ne sont pas stables, VPN (WireGuard) dont l'adresse sert de liste blanche. Le nom d'hôte n'est pas secret ; la 2FA et le verrouillage par compte s'y ajoutent. |
| 8 | Durées de conservation | Valeurs proposées : conversations 12 mois après la dernière activité, journaux 24 mois, pièces des gérants 12 mois après la fin de la relation, OTP 90 jours. À valider avec un juriste. |
| 9 | Détection des coordonnées | Mode « masquer » par défaut pour les signaux forts (numéro, e-mail, lien) ; mots-clés seulement signalés ; « bloquer » prêt, pas de blocage automatique (faux positifs sur les prix). Vidéos et photos non analysées : première vidéo de chaque gérant relue. |
| 10 | Publication des annonces | Immédiate pour un gérant vérifié, modération a posteriori, sauf la première annonce de chaque gérant (relecture de la vidéo) ; pré-modération générale activable. |
| 11 | Adresse précise de la chambre | Visible seulement dans la conversation, pour garder un rôle à la plateforme. |
| 12 | Web Push sur le site | Priorité C : les notifications fiables passent par l'application ; le site affiche compteur et messages en direct tant qu'il est ouvert. |
| 13 | Valeurs chiffrées | Durées, tailles, plafonds et délais de l'annexe A sont des valeurs de départ à ajuster avec le démarcheur et d'après les mesures. |
| 14 | Nom et domaine | « Logeo » est un nom de travail ; le nom de domaine reste à acheter (le document utilise `<domaine>`). |

## Annexe A. Constantes de configuration

Valeurs de départ. Celles marquées « base » sont lues dans `app_settings` et modifiables sans redéploiement ; les autres sont des constantes de configuration.

| Paramètre | Valeur par défaut | Où | Remarque |
|---|---|---|---|
| OTP : longueur, validité, essais | 6 chiffres, 5 min, 5 essais | code | §5.3 |
| OTP : renvoi, plafonds | 60 s ; 3 par heure et par numéro, 10 par jour et par appareil, 60 par jour et par plage /24 | base |  |
| OTP : pays autorisés · budget quotidien | BJ · 300 envois, répartis par usage | base | `OTP_ALLOWED_COUNTRIES`, `OTP_DAILY_BUDGET` ; friction à 80 %, arrêt à 100 % (§5.3) |
| Mot de passe : longueur minimale | 8 caractères | code | EF-AUT-03 |
| Verrouillage de connexion | 5 échecs par (numéro, IP ou appareil) → 15 min, doublé à chaque récidive ; 30 échecs par heure et par numéro | base | EF-AUT-05 |
| Administration : verrouillage (par compte) · sessions | 5 échecs · inactivité 30 min, durée 8 h | base | §5.1 |
| Jeton d'accès · rafraîchissement · ticket WebSocket | 15 min · 30 jours (grâce de rotation 60 s) · 30 s | code | §5.2 |
| Vidéo : durée · taille d'origine | 10 à 60 s · 150 Mo | base | EF-ANN-06 |
| Vidéo : résolution minimale · qualités · segments | 480p · 360p et 720p · 2 s | code |  |
| Vidéo : formats acceptés | MP4, MOV, WebM | code |  |
| Photos : nombre · taille maximale | 3 à 10 · 10 Mo | base | EF-ANN-08 |
| Envoi tus : morceau · expiration d'un envoi inactif | 1 Mo · 24 h | code |  |
| Quotas d'envoi | 1 vidéo et 10 photos par annonce ; 2 envois ouverts et 500 Mo en attente par gérant ; refus au-delà de 85 % de disque | base | EF-ANN-19 |
| Originaux conservés après traitement | 24 h | code | §11.2 |
| Suppression de la vidéo après location | 7 jours | base | EF-ANN-13 |
| Fraîcheur : relances · masquage · archivage | J+7 et J+10 · J+14 · 90 jours après location | base | EF-ANN-14 |
| Signalements « déjà louée » avant dossier | 3 distincts | base | EF-ANN-15 |
| Annonces actives par gérant | 20 | base | EF-ANN-17 |
| Description · titre | 4 000 caractères · 5 à 120 caractères | code |  |
| Position publique d'une annonce | arrondie à 3 décimales (environ 110 m) | code | EF-ANN-10 |
| Alertes par compte | 5 | base |  |
| Message : longueur · fréquence | 2 000 caractères · 30 par minute | base | EF-MSG-02, EF-MSG-11 |
| Nouvelles conversations par locataire | 20 par jour | base | EF-MSG-11 |
| Conversation en lecture seule après location | 30 jours | base | EF-MSG-08 |
| WebSocket : connexions par utilisateur · trame · événements | 5 · 8 Ko · 30 par minute | code | §10.8 |
| Rappel au gérant pour message non lu | 2 h | base | EF-NTF-08 |
| SMS de repli au gérant | désactivé | base | `SMS_FALLBACK_ENABLED` |
| Détection des coordonnées | off | base | `CONTACT_LEAK_MODE` : off, mask, flag, block |
| Pré-modération des annonces | désactivée | base | `LISTING_PREMODERATION` |
| Lectures de conversation par jour avant alerte | 20 par compte | base | §11.11 |
| Suspension maximale par un modérateur | 30 jours | base | Au-delà : administrateur |
| Abonnement | désactivé | base | `SUBSCRIPTION_ENABLED`, `SUBSCRIPTION_GRACE_DAYS` = 7, `PLANS` |
| Défi anti-robot du site | activé | base | `TURNSTILE_ENABLED` ; obligatoire dès 80 % du budget OTP |
| Cache du fil · cache des statistiques | 60 s · 5 min | code | §4.6, §7.10 |
| Pages de liste | 10 par défaut, 50 au plus | code | §10.1 |
| Point de référence du campus | à renseigner | base | `CAMPUS_REFERENCE` |

## Annexe B. Catalogue des notifications

| Événement (`kind`) | Destinataire | Canaux | Règle |
|---|---|---|---|
| message.received | Locataire ou gérant | Centre, push | Une par message reçu ; push sauf vers l'appareil où la conversation est ouverte (§11.9). |
| message.unanswered_reminder | Gérant | Push (SMS si drapeau) | Message non lu depuis 2 h. |
| alert.match | Locataire | Centre, push | Une fois par couple alerte/annonce (`dedupe_key`). |
| favorite.unavailable | Locataire | Centre, push | Un favori devient loué ou masqué. |
| listing.published | Gérant | Centre | Annonce en ligne après traitement de la vidéo. |
| listing.media_failed | Gérant | Centre, push | Échec du traitement avec motif lisible. |
| listing.reminder | Gérant | Centre, push | « Cette chambre est-elle toujours libre ? » à J+7 et J+10. |
| listing.hidden | Gérant | Centre, push | Masquée (fraîcheur, modération, suspension) avec le motif. |
| listing.rented_video_scheduled | Gérant | Centre | Suppression de la vidéo à J+7, avec possibilité d'annuler. |
| listing.reported_rented | Gérant | Centre, push | Trois locataires la signalent comme déjà louée. |
| report.outcome | Auteur du signalement | Centre | Décision prise (sans détailler la sanction). |
| account.sanction | Utilisateur concerné | Centre, push | Avertissement, suspension, bannissement, rétablissement ; non désactivable. |
| gerant.verified | Gérant | Centre, push | Compte vérifié et activé. |
| subscription.* | Gérant | Centre, push | Seulement si le drapeau d'abonnement est actif. |

## Annexe C. Données de départ

Données chargées par `make seed` en local et par une commande de gestion en production. Les éléments entre crochets sont à fournir par l'équipe : ils ne doivent pas être inventés.

| Jeu de données | Contenu |
|---|---|
| Quartiers | Liste fournie par le démarcheur partenaire avec un point central par quartier [liste et coordonnées à valider sur le terrain]. |
| Campus de référence | Université de Parakou : paramètre `CAMPUS_REFERENCE` [coordonnées à relever]. |
| Plans | `free_v1` : prix 0, sans limite, actif, dans `app_settings.PLANS`. |
| Paramètres | Toutes les valeurs « base » de l'annexe A. |
| Comptes de test (local seulement) | Un administrateur, un modérateur, deux gérants vérifiés (dont un avec annonces et conversations), trois locataires ; numéros fictifs, mot de passe de développement. |
| Annonces d'exemple (local seulement) | Une vingtaine d'annonces avec vidéos courtes et photos libres de droits, dans plusieurs quartiers et fourchettes de loyer. |
| Jeu de volume (tests de performance) | Générateur de 50 000 annonces et 1 million de messages pour les plans de requêtes et la charge. |
| Textes légaux | CGU et politique de confidentialité, version initiale [à rédiger et valider juridiquement]. |


<!-- FIN CDC -->
