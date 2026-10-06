# ADR 0003 — Décisions de la phase 0

- Statut : accepté, **point 1 à valider par le porteur du projet**
- Date : 2026-10-06

## 1. Anneau de focus : `marque-500` en clair

Le prompt demande un anneau `marque-300`. Sur fond clair (`#FCFAF6`), `marque-300` donne environ 1,9:1, sous les 3:1
exigés par WCAG 2.2 pour un indicateur de focus. Décision : `--focus` vaut `marque-500` en thème clair et `marque-300`
en thème sombre. `outils/contraste.py` impose 3:1 contre le fond et la surface.

## 2. Réglages d'administration scindés

`admin_base.py` (commun), `admin.py` (production : refuse `DEBUG`, `OTP_DEBUG_CODE`, secret absent ou `dev-…`) et
`admin_local.py` (développement, HTTP). Même logique côté site : `public.py` strict, `local.py` pour le développement.

## 3. Couverture mesurée

Sont exclus de la mesure : `config/settings/*` (vérifiés par sous-processus dans `tests/securite/test_reglages.py`),
`asgi.py`, `celery.py`, `beat_unique.py` (amorces de processus) et `urls_admin.py` (phase 1). Seuil : 85 %.

## 4. Une seule instance de `beat`

`config/beat_unique.py` prend un verrou Redis à jeton (`apps/core/verrou.py`, testé) avant de lancer `celery beat`
et l'arrête s'il perd le verrou.

## 5. Réseaux Docker

`interne` (sans Internet), `sortie` (Internet, réservé à `web-api`, `worker`, `backup`), `exposition` (Caddy seul).
`worker-media` n'est que sur `interne` ; `media_private` n'est monté que dans `admin` et `backup`.

## 6. Hôte d'administration fermé par défaut

Si `ADMIN_ALLOWED_IPS` est vide, Caddy utilise `192.0.2.1/32` (adresse de documentation, RFC 5737) : l'hôte répond 404 à
tout le monde. Comportement vérifié avec Caddy 2.11.7 (variable absente, vide, non listée, listée).

## 7. Qualité du code

`ruff` : règle `E501` désactivée (le formateur gère le code ; les docstrings en français peuvent dépasser 100 caractères).
`bandit` ignore les tests (assertions) ; les deux alertes justifiées (`subprocess` à commande constante, secret factice
de test) sont annotées `nosec` avec leur raison.
