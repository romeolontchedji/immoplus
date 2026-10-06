# Avancement

**Phase en cours : 0 (fondations), environ 25 % réalisée.**

Fait : dépôt Git, extraction du cahier des charges (`docs/cahier-des-charges.md`, 2 070 lignes, extraite par script),
contrôles Git (commit, branche, noms, hygiène), trois hooks, `tester_hooks.sh` (9 cas, tous conformes), 13 tests unitaires des outils.

Reste en phase 0 : `AGENTS.md`, ADR 0001 et 0002, Makefile complet, Docker Compose, Caddy, réglages Django, import-linter,
workflows CI, `construire_css.py`, jetons de design, `/styleguide`, `/healthz` `/readyz`.

**Blocage** : le réseau du bac à sable refuse PyPI, npm et GitHub (403). Django ne peut être ni installé ni exécuté.
Détail et remède : `docs/environnement-generation.md`.

Décision prise : `LISEZMOI` ajouté aux noms en majuscules autorisés (le prompt l'impose pour `vendor/LISEZMOI.md` et `mobile/`
mais ne l'inclut pas dans sa liste du §6.2).
