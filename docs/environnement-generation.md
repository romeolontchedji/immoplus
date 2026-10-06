# Environnement de génération

Inventaire réalisé le 6 octobre 2026 dans le bac à sable.

| Outil | État |
|---|---|
| python3 | 3.12.3 |
| pip | 24.0 |
| git | 2.43.0 |
| node | v22.22.2 (`npm` inutilisable : erreur de configuration `.npmrc`) |
| make | GNU Make 4.3 |
| ffmpeg / ffprobe | 6.1.1 |
| Playwright (Python) | 1.56.0 installé ; **aucun navigateur Chromium trouvé** dans le `PATH` (non vérifié ailleurs) |
| docker, psql/postgres, redis-server, chromium | **absents** |
| ruff, pytest, djlint, gitleaks | **absents** |
| Django, DRF, Celery, Channels, psycopg, argon2, etc. | **non installés** (seuls Pillow 12.1.1, PyJWT 2.7.0, markdown-it-py sont présents) |
| Mémoire / processeurs | environ 4 Go / 1 cœur |

## Réseau

Tous les hôtes testés (`pypi.org`, `registry.npmjs.org`, `github.com`) répondent **403 `host_not_allowed`**
(refus par le proxy de sortie). Conséquences :

- impossible d'installer Django et le reste de la pile, donc **impossible d'exécuter ou de tester le code Django** ici ;
- impossible de télécharger `pgserver`, htmx, Alpine.js, hls.js, tus-js-client (`make vendor` reste à lancer chez l'utilisateur) ;
- impossible de figer les « dernières versions stables » (ADR 0001) sans pouvoir les consulter.

Pour changer cela : autoriser `pypi.org`, `files.pythonhosted.org`, `registry.npmjs.org` et `github.com` dans les paramètres réseau du bac à sable.
