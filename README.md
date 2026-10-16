# Logeo

Trouver une chambre à Parakou : annonces avec vidéo réelle, gérants vérifiés, messagerie intégrée,
aucun contact hors plateforme.

Le dépôt contient les deux parties du projet :

- **Partie 1 — le serveur** (`serveur/`, `web/`, `adminsite/`, `infra/`, `outils/`) : monolithe
  modulaire Django 5.2 LTS (PostgreSQL, Redis, Celery, Channels, Caddy), site public rendu par le
  serveur, API `/v1` et administration sur un hôte séparé.
- **Partie 2 — l'application mobile** (`mobile/`) : application Expo / React Native (Expo Router)
  qui consomme l'API `/v1` et le temps réel `/ws/`.

## Arborescence

| Chemin              | Contenu                                                                        |
| ------------------- | ------------------------------------------------------------------------------ |
| `serveur/config/`   | réglages (`base`, `local`, `public`, `admin`, `test`), URL, ASGI, Celery       |
| `serveur/apps/`     | applications métier : `core`, `accounts`, `listings`, `media`, `chat`, …       |
| `serveur/web/`      | site public (gabarits, CSS, JS, vues minces)                                   |
| `serveur/adminsite/`| administration séparée (thème, gabarits)                                       |
| `mobile/`           | application mobile Expo / React Native (partie 2)                              |
| `infra/`            | Docker, Compose, Caddy, PostgreSQL, sauvegarde                                 |
| `outils/`           | scripts de contrôle et de construction                                         |
| `docs/`             | cahier des charges, ADR, avancement, design, API (`openapi.json`)             |

## Démarrer le serveur

Prérequis : Git, Make, Python 3.12 et Docker avec Compose.

```bash
git clone https://github.com/Magloireaffokpe/logeo.git logeo && cd logeo
make up        # installe les hooks, crée .env, construit et démarre la pile
make fumee     # vérifie que tout répond
```

Puis : site <http://www.localhost:8080>, API <http://api.localhost:8080>,
administration <http://pilotage.localhost:8080>.
En cas de panne : `make diagnostic` et colle le résultat dans une IA ou dans une issue.

## Développer le serveur

```bash
make installer   # environnement Python local (.venv)
make test        # tests
make verifier    # tous les contrôles, avant chaque push
```

Les commandes utiles : `make migrate`, `make seed`, `make css`, `make openapi`, `make docs`. Un seul
test : `cd serveur && python -m pytest apps/core/tests/integration/test_sante.py::test_healthz_repond_ok`.

## Développer l'application mobile

Prérequis : Node.js 20 ou plus récent et npm (aucune autre dépendance globale).

```bash
cd mobile
npm install          # installe les dépendances
npm start            # lance Expo (dev client)
npm run android      # ou npm run ios  (build natif via expo run:*)
```

Contrôles mobiles :

```bash
npm run typecheck    # TypeScript (tsc --noEmit)
npm run lint         # ESLint
npm test             # tests Jest
npm run verifier     # les trois d'affilée
```

Le contrat d'API est versionné (`docs/api/openapi.json`) : le client TypeScript se régénère avec
`npm run api:generer` (voir `outils/exporter_client_ts.sh`). Détails dans `mobile/docs/`
(`architecture.md`, `ecrans.md`, `tests.md`) et `mobile/LISEZMOI.md`.

## Vérifications et hooks Git

Les hooks Git (`.githooks/`) sont installés par `make up`/`make hooks` et contrôlent le format des
commits, le nom de branche et l'absence de secrets. Le `pre-push` lance `outils/verifier_tout.sh`,
la CI refait les mêmes contrôles. **Ne jamais utiliser `--no-verify`.**

## Documentation

- Cahier des charges : [`docs/cahier-des-charges.md`](docs/cahier-des-charges.md)
- Décisions d'architecture : [`docs/adr/`](docs/adr/)
- Règles du projet (IA et humains) : [`AGENTS.md`](AGENTS.md)
- Procédure de contribution : [`docs/contribuer.md`](docs/contribuer.md)
- État d'avancement : [`docs/avancement.md`](docs/avancement.md), [`docs/reste-a-faire.md`](docs/reste-a-faire.md)
- Design system : [`docs/design/DESIGN.md`](docs/design/DESIGN.md)
