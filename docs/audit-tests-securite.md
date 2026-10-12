# Audit des tests et des contrôles de sécurité

Date : 2026-10-11. Base mesurée : 838 tests collectés, 835 passent (3 échecs d'environnement, 1 test
WebSocket ignoré faute de `daphne` — voir `docs/a-verifier.md` A1), couverture 92 % (seuil 85 %).

Ce document classe ce qui est **réellement utile** et ce qui **encombre**, puis propose un plan de
nettoyage priorisé. Il ne retire rien lui-même : les retraits se font en accord avec le propriétaire.

## 1. Points forts (à conserver tels quels)

- Garde-fous automatisés complets : `outils/verifier_tout.sh` module précis (noms, hygiène, branches,
  ruff, format, djlint, contrastes, tests des outils, import-linter, bandit, makemigrations, OpenAPI,
  pytest) ; relancé en `pre-push` et en CI.
- Hooks Git (format des commits, tasse de merge interdite, push direct sur `main` refusé) + CI
  `commits.yml` qui les rejoue côté GitHub.
- Bandeau de posture d'infrastructure très solide : `tests/securite/test_compose.py` (17 tests) vérifie
  que seul Caddy est exposé, que PostgreSQL/Redis ne publient aucun port, que `media_private` ne monte
  que dans admin/backup, que la prod ne monte pas le code, etc.
- Tests de réglages (`tests/securite/test_reglages.py`) : refus de DEBUG/clés de dev en production,
  cookies site ≠ admin, 3 clés distinctes obligatoires.
- Couverture 92 % mesurée et exigée à 85 %.

## 2. Tests : inventaire par dossier

| Dossier | Nb | Couvre | Verdict |
|---|---|---|---|
| `apps/core/tests/unitaires` | 54 | requêtes, verrous Redis, fournisseurs, masquage | Utile |
| `apps/core/tests/integration` | 9 | santé, pile, tâches | Utile |
| `apps/accounts/tests/integration` | 257 | OTP, jetons, verrouillage, profils, gérants, appareils | Utile (prix : 1 + 2 facteurs) |
| `apps/accounts/tests/api` | 50 | contrat API `/v1` (comptes, sécurité d'accès) | Utile |
| `apps/listings/tests` | 150 | fil public (54), annonces pro (43), médias (34), entretien (19) | Utile |
| `apps/chat/tests/test_messagerie` | 54 | messagerie, coordonnées, blocage, signalement | Utile |
| `apps/chat/tests/test_websocket` | 12 | temps réel (skippé : daphne absent, ADR A1) | En attente, non exécuté |
| `apps/moderation/tests` | 49 | signalements, sanctions, suspension, lecture journalisée | Utile |
| `apps/notifications/tests` | 32 | création/regroupement/push | Utile |
| `web/tests` | 70 | pages publiques, comptes, espace gérant | Utile |
| `adminsite/tests` | 73 | administration 2FA, accès, tableau de bord, verrouillage | Utile |
| `tests/securite` | 34 | réglages + compose (posture infra) | Utile |
| `tests/test_agents.py` | 6 | AGENTS.md/CLAUDE.md cohérents avec le dépôt | Méta, coût nul, garde-fou |
| `apps/accounts/tests/unitaires/` | 0 | dossier **vide** (seul `__init__.py`) | Encombrant |
| `apps/{media,billing,audit}/tests/` | 0 | dossiers placeholders (aucun test) | Placeholders (audit : à couvrir) |

## 3. Marquers pytest : utilisés ou vides

| Marquers | Tests concernés | Verdict |
|---|---|---|
| `unitaire` (60), `integration` (617), `api` (131), `securite` (103), `pg` (737), `ffmpeg` (4) | réels, utilisés par `make test-*` | Utiles |
| `ws` | 12 tests en attente de `daphne` | En attente |
| `e2e` | 0 test | **Encombrant** (jamais écrit ; le navigateur devient le rôle du propriétaire) |
| `lent` | 0 test | Encombrant (placeholder « phase 9 » jamais alimenté) |
| `exigence(id)` | 0 usage | **Encombrant** (marqueur déclaré, jamais utilisé) |

## 4. Dépendances de développement : utilisées ou inutiles

| Dépendance | Usages réels | Verdict |
|---|---|---|
| `factory_boy`, `pytest-django`, `pytest-cov`, `pytest-asyncio` | partout | Utile |
| `time-machine` | jetons, comptes, admin (tests) | Utile |
| `fakeredis` | `redis_file`, verrous (tests unitaires) | Utile |
| `ruff`, `bandit`, `import-linter`, `djlint`, `pip-audit` | verifier + CI | Utile |
| `playwright`, `axe-playwright-python` | **aucun** (0 test e2e) | **Encombrant** |
| `hypothesis` | **aucun** | **Encombrant** |
| `schemathesis` | **aucun** | **Encombrant** |
| `httpx` | **aucun** (les tests API passent par le client DRF) | **Encombrant** |
| `pytest-xdist` | **aucun** (`-n` jamais utilisé ; la maison exige le tirage en série) | **Encombrant** |
| `pytest-randomly` | plugin actif en CI, mais **toujours** désactivé en manuel (`-p no:randomly`) | Paradoxal, à trancher |
| `django-migration-linter` | installé, **jamais branché** (pourtant des migrations existent) | Soit brancher, soit retirer |

## 5. Cibles Makefile : utiles ou placeholders

| Cible | Verdict |
|---|---|
| `test`, `test-unitaires`, `test-integration`, `test-securite`, `couverture`, `lint`, `verifier`, `hooks`, `css`, `shell`, `migrate`, `seed`, `env`, `up`, `down`, `installer`, `openapi`, `fumee`, `diagnostic`, `nettoyer`, `test-outils`, `tester-hooks`, `aide` | Utiles |
| `test-e2e` (« Aucun test e2e avant la phase 4 »… mais les phases 4-6 sont livrées sans e2e) | Encombrant |
| `test-lent` (placeholder « phase 9 », 0 test) | Encombrant |
| `docs`, `vendor` (deux `exit 1` volontaires) | Encombrant (bruit sonore) |

## 6. Contrôles de sécurité : inventaire complet et état

### Analyse statique et commit-time
- `ruff` (règles S sécurité, B, T20, N, DJ) — actif, `verifier` + hooks.
- `bandit` (SAST) — actif, `verifier`.
- `import-linter` (10 contrats d'architecture, aucun `models` dans les adaptateurs) — actif.
- `djlint` — actif ; `contraste.py` (WCAG) sur `tokens.css` — actif.
- `verifier_hygiene.py` (secrets, `print`/`pdb`, tailles de fichiers) — actif ; remplace le `gitleaks` absent
  par des motifs maison.
- `verifier_noms.py` (mots interdits, noms de modules) — actif.
- `makemigrations --check` (pas de dérive de schéma) et `OpenAPI --validate` (API additive) — actifs.
- `pip-audit` (CVE des dépendances) — CI, **seulement sur `base.txt`** (pas `dev.txt`).

### Exécution — domaine public
- CSP stricte via `EnTetesSecuriteMiddleware` (aucun `script`/`style` en ligne ; scripts : `'self'` +
  Cloudflare Challenges), `Permissions-Policy`, `COOP: same-origin`, `nosniff`, `referrer-policy`,
  `X-Frame-Options: DENY` — active et testée.
- Cookies sécurisés (`__Host-`, Secure, HttpOnly, SameSite=Lax), CSRF cookie distinct, HSTS 1 an
  (incl. sous-domaines via Caddy) — actifs (réglages `public`).
- Mots de passe Argon2 + validators (8 caractères minimum, common interdits) — actifs.
- API : JWT des app avec clés dédiées, permission par défaut **tout refuser**, limitation de débit par
  adresse (`LimiteAuth` 30/min, `LimiteCompte` 60/min, `LimiteLecture` 240/min, en `redis-queue`) —
  actives.
- Numéros de téléphone jamais exposés, journaux JSON avec filtre de masquage (`apps.core.logging`) —
  actifs.

### Exécution — administration (hôte séparé)
- 2FA TOTP obligatoire (`OTPAdminSite`), codes de secours `otp_static` — active.
- Liste blanche d'IP sur l'hôte admin, sessions dans une table dédiée (`admin_sessions`), cookie
  `Strict` de 30 min, `SAVE_EVERY_REQUEST` — actifs.
- Verrouillage bruteforce `axes` : 5 échecs, refroidissement 0,5 h, verrou par adresse OU nom, remise à
  zéro au succès — actif.
- Clés `SECRET_KEY`/`JWT_SIGNING_KEY`/`OTP_HMAC_KEY` distinctes, refus des valeurs `dev-` en
  production (`ImproperlyConfigured`, testé) ; CSP admin (styles du site Django tolérés, jamais de
  scripts en ligne) — actifs.
- Rôles PostgreSQL par processus (`app`, `admin_app`, `migrate`, `retention`) — écrits, **jamais
  réellement exercés** en exécution (voir A2, tests faits en super-utilisateur).

### Infrastructure
- Posture Compose verrouillée et testée (`test_compose.py`) : réseau interne, seul Caddy exposé,
  PG/Redis sans port publié, `media_private` restreint, prod sans montage de code — actif/testé.
- `statement_timeout` 5 s, pool psycopg restreint — actifs.
- Traçabilité : `AuditLog` + purge par rétention (`SET LOCAL ROLE retention`) — code écrit, jamais
  exécuté avec le vrai rôle (même A2).

### En attente d'infrastructure (pas du gaspillage, mais non exercé)
- `daphne` absent → 12 tests WebSocket ignorés (ADR A1) ; le consommateur n'a jamais tourné.
- `pip-audit` hors domaine, rôles PG réels, tâches `beat` de nuit, premier `docker compose up` réel —
  listés A2/A3/A4 dans `docs/a-verifier.md`.

## 7. Plan de nettoyage priorisé

### P1 — retirer sans risque (encombrant, aucun usage, aucun impact sur la qualité)
1. Dépendances jamais utilisées (retirer de `serveur/requirements/dev.in`, régénérer `dev.txt`) :
   `playwright`, `axe-playwright-python`, `hypothesis`, `schemathesis`, `httpx`, `pytest-xdist`.
2. Dossier vide `apps/accounts/tests/unitaires/` (aucun test).
3. Marquers pytest jamais utilisés : `e2e`, `lent`, `exigence(id)`.
4. Cibles Makefile placeholders : `test-e2e`, `test-lent` (les tests ironiques qui font foi restent
   `test-securite`, `test-integration`, etc.), et retraits connexes de `docs/a-verifier.md`/AGENTS.md.
5. CI `verifier.yml` : suppression de l'étape redondante « Tests d'intégration et de sécurité »
   (pytest tourne déjà 2 fois : dans `verifier_tout.sh` puis avec `--cov` ; cette étape le fait une
   3ᵉ fois sans aucun gain).

### P2 — à trancher
6. `django-migration-linter` : **brancher** maintenant (des migrations existent ; complète le cycle
   « migration en deux temps ») **ou** le retirer. Recommandé : brancher une vérification dans
   `verifier_tout.sh`.
7. `pytest-randomly` : le garder actif en CI (déterrement de dépendances inter-tests) et ne plus
   l'éteindre en manuel, **ou** le retirer pour une exécution déterministe. Recommandé : retirer, la
   suite est déjà verrouillée au série (a-verifier exige `-p no:randomly`).
8. Placeholders futurs `make docs`, `make vendor` + dossiers `apps/{media,billing,audit}/tests/` :
   soit les assumer explicitement (une ligne « prévu phase N » dans `make aide`), soit les retirer.
9. `apps/audit` sans aucun test dédié : compléter la couverture (traçabilité critique) avant de
   réduire quoi que ce soit.
10. `pip-audit` : l'étendre à `dev.txt` (ou le laisser sur `base.txt` si le dev est jugé hors périmètre).

## 8. Ce que je recommande de ne **pas** toucher

- Les 835 tests d'applications (couverture métier et contrat), les tests de posture (`securite`), les
  garde-fous de format (`commits.yml`, hooks) et `outils/verifier_tout.sh` : c'est le filet qui rend le
  repo sûr et la reprise possible.
- Les contrôles de sécurité d'exécution (CSP, 2FA, axes, cookies, throttles, rôles PG) : ils sont déjà
  chers mais actifs.