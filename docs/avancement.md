# Avancement

**Phase en cours : 0 (fondations) — terminée côté code, avec les réserves listées ci-dessous.**
Prochaine étape : phase 1 (comptes : modèles, OTP, appareils, administration séparée).

## Fait (phase 0)

- Dépôt, contrôles Git (commit, branche, noms, hygiène), trois hooks, `outils/tester_hooks.sh` : 9 cas conformes, sortie dans `docs/verification.md`.
- Serveur Django 5.2 LTS : réglages `base/local/public/admin/admin_local/test`, neuf applications vides, `/healthz`, `/readyz`,
  journaux JSON masqués, CSP stricte, identifiant de requête, verrou Redis pour `beat`, contrats `import-linter` (10, mutation vérifiée).
- Design : jetons clair/sombre, couches CSS, `outils/construire_css.py`, `outils/contraste.py`, `/styleguide` initial.
- Infrastructure : `Dockerfile`, Compose (dev et prod), Caddy (local et production), rôles PostgreSQL, sauvegarde logique.
- Outils : `Makefile` complet, `verifier_tout.sh`, `creer_env.py`, `diagnostic.sh`, `fumee.sh`.
- Documentation : `AGENTS.md` (+ test), ADR 0001 à 0003, `README`, `docs/contribuer.md`, `docs/design-system.md`, `docs/api/openapi.json`.
- CI : `.github/workflows/commits.yml` et `verifier.yml`, `CODEOWNERS`, modèles de demande de fusion et d'issues.

## Réserves (non exécuté ou à faire chez toi)

1. **Docker absent du bac à sable** : image, Compose et `make up` n'ont jamais tourné. `make fumee` est à lancer chez toi.
2. **Workflows GitHub** : écrits et lus (YAML valide), jamais exécutés. Protection de `main` : procédure dans `docs/contribuer.md`.
3. **Caddy de production** : validé (`caddy validate`) mais pas exécuté ; la version locale a été exécutée avec de faux amonts.
4. **Images** `postgres`, `redis`, `caddy` non figées par digest (ADR 0001).
5. **Chromium indisponible** (téléchargement bloqué) : aucun test e2e ni axe avant la phase 4.
6. **`gitleaks` absent** : détection de secrets par motifs maison seulement.
7. `make seed`, `make vendor`, `make docs` : volontairement non disponibles (phases 1, 4, 9) ; ils échouent avec un message clair.
8. `django-migration-linter` n'est pas encore branché (aucune migration avant la phase 1).

## Décision à valider

Anneau de focus en `marque-500` (clair) au lieu de `marque-300` : voir `docs/adr/0003-decisions-phase-0.md`.

## Décisions et pièges

- `LISEZMOI` et `Caddyfile` ajoutés aux noms en majuscules autorisés (imposés par le prompt et par Caddy).
- Les chemins de modules imposés par Django (moteurs de base, de session, de cache) sont tolérés par une liste explicite dans `outils/mots-interdits.toml` ; le mot interdit reste refusé partout ailleurs.
- `pkill -f motif` tue le shell qui contient le motif : utiliser des fichiers de PID.
- Le bac à sable peut redémarrer : PostgreSQL et Redis ne sont pas relancés tout seuls (`pg_ctlcluster 16 main start`, `redis-server --daemonize yes`).
- `tester_hooks.sh` crée un dépôt temporaire : il doit y copier la configuration ruff, et le fichier du cas 8 doit être conforme
  au formateur, sinon le refus vient de ruff et non du détecteur de secrets.
