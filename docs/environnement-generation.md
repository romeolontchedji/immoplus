# Environnement de génération

Inventaire mis à jour le 6 octobre 2026 dans le bac à sable (le précédent, du même jour, signalait un réseau fermé).

| Outil | État |
|---|---|
| Python | 3.12.3, venv `.venv` (ignoré par Git), dépendances de `serveur/requirements/dev.txt` installées |
| PostgreSQL | 16.15 installé par `apt` ; à relancer après un redémarrage : `pg_ctlcluster 16 main start` |
| Redis | 7.0.15 installé par `apt` ; à relancer : `redis-server --daemonize yes` |
| Caddy | 2.11.7, binaire téléchargé dans `/tmp/caddy` (non versionné) |
| ffmpeg / ffprobe | 6.1.1 |
| Node | v22 présent mais **non utilisé** (le projet n'a pas de Node) |
| ruff, pytest, djlint, bandit, import-linter, pip-audit, schemathesis | installés (venv) |
| Docker, gitleaks | **absents** |
| Chromium (Playwright) | **indisponible** : le téléchargement échoue |
| Mémoire / processeurs | environ 4 Go / 1 cœur |

## Réseau

PyPI, GitHub (fichiers de release) et les dépôts `apt` répondent. Le registre npm est autorisé mais inutilisé jusqu'à `make vendor`
(phase 4). Le CDN de Playwright et `deb.nodesource.com` sont refusés. L'API GitHub est limitée en débit : télécharger les
fichiers de release directement.

## Consignes pour reprendre une session

1. Relancer PostgreSQL et Redis (commandes ci-dessus) ; recréer le rôle de test si besoin :
   `su postgres -c "psql -c \"CREATE ROLE logeo_test LOGIN SUPERUSER PASSWORD 'logeo-test'\""` puis `createdb -O logeo_test logeo`.
2. Exporter `DB_USER=logeo_test DB_PASSWORD=logeo-test DB_NAME=logeo` avant `pytest` ou `outils/verifier_tout.sh`.
3. Ne jamais utiliser `pkill -f` avec un motif présent dans la commande en cours : le shell s'arrête (utiliser des fichiers de PID).
