# Logeo

Trouver une chambre à Parakou : annonces avec vidéo réelle, gérants vérifiés, messagerie intégrée.

Ce dépôt contient la **partie 1** : le serveur (`serveur/`), le site web, l'API `/v1`, l'administration et l'infrastructure.
L'application mobile (`mobile/`) est la partie 2.

## Démarrer

Prérequis : Git, Make, Python 3.12 et Docker avec Compose.

```bash
git clone <adresse-du-depot> logeo && cd logeo
make up        # installe les hooks, crée .env, construit et démarre la pile
make fumee     # vérifie que tout répond
```

Puis : site <http://www.localhost:8080>, API <http://api.localhost:8080>, administration <http://pilotage.localhost:8080>.
En cas de panne : `make diagnostic` et colle le résultat dans une IA ou dans une issue.

## Développer

```bash
make installer   # environnement Python local (.venv)
make test        # tests
make verifier    # tous les contrôles, avant chaque push
```

Les règles du projet sont dans [`AGENTS.md`](AGENTS.md) ; la procédure de contribution dans
[`docs/contribuer.md`](docs/contribuer.md) ; l'état d'avancement dans [`docs/avancement.md`](docs/avancement.md).
