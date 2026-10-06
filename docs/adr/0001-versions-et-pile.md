# ADR 0001 — Versions et pile technique

- Statut : accepté (phase 0)
- Date : 2026-10-06

## Contexte

Le cahier des charges impose une pile sobre : monolithe modulaire Django, PostgreSQL, Redis, Celery, Channels, Caddy,
sans Node. Les versions exactes sont figées pour que chaque environnement construise la même chose.

## Décision

| Brique | Choix | Note |
|---|---|---|
| Python | 3.12 | image `python:3.12-slim-bookworm` |
| Django | **5.2.17 LTS** | support étendu jusqu'en avril 2028 (djangoproject.com, relevé le 2026-10-06) |
| API | djangorestframework 3.18.1, drf-spectacular 0.30.0 | schéma OpenAPI versionné |
| Temps réel | channels 4.3.2, channels-redis 4.3.0 | |
| Tâches | celery 5.6.3, redis (client) 8.1.0 | files `default`, `notifications`, `media` |
| Base | PostgreSQL 16 (`psycopg` 3.3.6, pool) | trois rôles : `app`, `admin_app`, `migrate` |
| Serveurs | gunicorn 26.2.0 + `uvicorn-worker` 0.4.0 (uvicorn 0.54.0) | voir « Écarts » |
| Sécurité | argon2-cffi 25.1.0, PyJWT 2.15.1, django-otp 1.7.3, django-axes 8.3.1, cryptography 50.0.2 | |
| Contenu | nh3 0.3.7, markdown-it-py 4.2.0, phonenumbers 9.0.40 | |
| Médias | Pillow 12.3.0, pillow-heif 1.8.0, ffmpeg (paquet Debian) | |
| Administration | django-unfold 0.108.0 | thème de l'administration, phase 1 |
| Observabilité | sentry-sdk 2.71.0 | installé, non branché (phase 9) |
| Qualité | ruff 0.16.10, pytest 9.1.1, schemathesis 4.29.3, hypothesis 6.168.5, import-linter, bandit, djlint, pip-audit | |
| Proxy | Caddy 2.11.7 (image `caddy:2` à figer) | |

Les versions complètes et transitives sont dans `serveur/requirements/base.txt` et `dev.txt`
(générés par `pip freeze` à partir de `base.in` et `dev.in`).

## Écarts assumés par rapport au prompt

1. **`uvicorn-worker`** est ajouté : le module `uvicorn.workers` est déprécié (avertissement vérifié).
2. **Cache Redis intégré à Django** (`django.core.cache.backends.redis.RedisCache`) au lieu de `django-redis` : une dépendance en moins.
3. **Images Docker non figées par digest** (`postgres:16-bookworm`, `redis:7-alpine`, `caddy:2`) : le registre n'était pas
   consultable pendant l'écriture. À figer au premier déploiement.

## Conséquences

- Migration vers Django 6.2 LTS (attendu en avril 2027) à planifier : ADR dédié le moment venu.
- Toute dépendance nouvelle exige un ADR (AGENTS.md §12).
