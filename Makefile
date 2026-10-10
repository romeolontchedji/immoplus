# Commandes du projet Logeo. `make aide` liste les cibles.
SHELL := /bin/bash
COMPOSE := docker compose --env-file .env -f infra/compose/docker-compose.yml --profile dev
PYTHON := $(if $(wildcard .venv/bin/python),.venv/bin/python,python3)
PYTEST := cd serveur && ../$(PYTHON) -m pytest

.PHONY: aide installer env hooks up down migrate seed css vendor shell \
        test test-unitaires test-integration test-e2e test-securite test-lent couverture \
        lint verifier openapi docs fumee diagnostic nettoyer test-outils tester-hooks

aide: ## Liste les cibles
	@grep -E '^[a-z-]+:.*## ' $(MAKEFILE_LIST) | awk -F':.*## ' '{printf "  make %-18s %s\n", $$1, $$2}'

installer: ## Crée .venv et installe les dépendances de développement
	python3 -m venv .venv
	.venv/bin/pip install -r serveur/requirements/dev.txt

env: ## Crée .env et un fichier d'environnement par service (secrets générés)
	python3 outils/creer_env.py

hooks: ## Installe les hooks Git (format des commits, branches, noms, hygiène)
	git config core.hooksPath .githooks

up: hooks env ## Démarre la pile locale (Docker Compose, profil dev)
	$(COMPOSE) up -d --build
	@echo "Site : http://www.localhost:8080 · API : http://api.localhost:8080 · Administration : http://pilotage.localhost:8080"

down: ## Arrête la pile
	$(COMPOSE) down

migrate: ## Applique les migrations (rôle PostgreSQL `migrate`)
	$(COMPOSE) run --rm migrer

seed: ## Paramètres et quartiers de Parakou ; ajouter DEMO=1 pour des annonces d'exemple (développement)
	$(COMPOSE) run --rm web-api python manage.py seed $(if $(DEMO),--demo,)

css: ## Assemble, minifie et empreinte le CSS
	$(PYTHON) outils/construire_css.py

vendor: ## Télécharge htmx, Alpine.js (build CSP), hls.js et tus-js-client en fichiers figés
	@echo "Non disponible : outils/telecharger_vendor.py arrive en phase 4 (voir docs/avancement.md)."; exit 1

shell: ## Ouvre un shell Django dans le conteneur web-api
	$(COMPOSE) exec web-api python manage.py shell

test: ## Tous les tests sauf `lent` et `e2e`
	$(PYTEST) -q -m "not lent and not e2e"

test-unitaires: ## Tests unitaires
	$(PYTEST) -q -m unitaire

test-integration: ## Tests d'intégration (PostgreSQL réel)
	$(PYTEST) -q -m integration

test-e2e: ## Tests de bout en bout du site (Playwright + axe ; à partir de la phase 4)
	$(PYTEST) -q -m e2e; code=$$?; [ $$code -eq 5 ] && echo "Aucun test e2e avant la phase 4." && exit 0; exit $$code

test-securite: ## Tests de sécurité
	$(PYTEST) -q -m securite

test-lent: ## Tests de charge et de performance
	$(PYTEST) -q -m lent; code=$$?; [ $$code -eq 5 ] && echo "Aucun test lent avant la phase 9." && exit 0; exit $$code

couverture: ## Couverture (rapport HTML dans serveur/htmlcov, seuil 85 %)
	$(PYTEST) -q -m "not lent and not e2e" --cov=apps --cov=web --cov=config --cov-report=term-missing:skip-covered --cov-report=html --cov-fail-under=85

lint: ## ruff (contrôle et format)
	$(PYTHON) -m ruff check serveur
	$(PYTHON) -m ruff format --check serveur
	$(PYTHON) -m ruff check --config outils/ruff.toml outils

verifier: ## Tous les contrôles (ceux du hook pre-push et de la CI)
	outils/verifier_tout.sh

openapi: ## Régénère docs/api/openapi.json
	mkdir -p docs/api
	cd serveur && ../$(PYTHON) manage.py spectacular --format openapi-json --file ../docs/api/openapi.json --validate --fail-on-warn

docs: ## Vérifie la cohérence de la documentation (à partir de la phase 9)
	@echo "Non disponible : outils/verifier_docs.py arrive en phase 9 (voir docs/avancement.md)."; exit 1

fumee: ## Test de fumée de la pile en marche
	outils/fumee.sh

diagnostic: ## Diagnostic de l'environnement (à coller dans une IA en cas de panne)
	outils/diagnostic.sh

nettoyer: ## Supprime caches, CSS construit et rapports (garde les volumes Docker)
	rm -rf serveur/htmlcov serveur/.coverage serveur/web/static/css/dist .pytest_cache serveur/.pytest_cache .ruff_cache
	find . -name __pycache__ -type d -not -path './.venv/*' -prune -exec rm -rf {} +

test-outils: ## Tests unitaires des scripts d'outils
	python3 -m unittest discover -s outils/tests -q

tester-hooks: ## Preuve que les hooks refusent ce qu'ils doivent refuser (9 cas)
	bash outils/tester_hooks.sh
