# Matrice de vérification

Légende : Exécuté ✅ · Simulé ⚠️ · Non exécuté ⛔ — mesures du 6 octobre 2026, PostgreSQL 16.15 et Redis 7.0.15 réels.

## Phase 0

| Composant | État | Preuve |
|---|---|---|
| Contrôles Git (commit, branche, noms, hygiène) et trois hooks | Exécuté ✅ | `bash outils/tester_hooks.sh` : 9 cas, 10 verdicts conformes (sortie ci-dessous) |
| Scripts d'outils | Exécuté ✅ | `python3 -m unittest discover -s outils/tests` : 38 tests, OK |
| Serveur Django (unitaires, intégration, sécurité) | Exécuté ✅ | `pytest` : 79 tests passés à la phase 0 ; 816 en fin de session (voir `docs/a-verifier.md`), couverture 92 % (seuil 85 %) |
| Réglages `public` et `admin` refusent DEBUG, OTP_DEBUG_CODE, secret `dev-` | Exécuté ✅ | `serveur/tests/securite/test_reglages.py`, sous-processus |
| `manage.py check` (local, test, admin_local) et `check --deploy` (public, admin) | Exécuté ✅ | aucune erreur |
| `/healthz`, `/readyz` (base, cache, file, disque ; 503 si Redis coupé ou disque plein) | Exécuté ✅ | `apps/core/tests/integration/test_sante.py` |
| CSP sans `unsafe-inline`, pas de style ni script en ligne, pas de route d'administration sur le site | Exécuté ✅ | `test_en_tetes.py`, `web/tests/test_pages.py` |
| Contrats `import-linter` | Exécuté ✅ | 10 contrats ; violation volontaire → 3 contrats cassés, puis rétablie |
| Contrastes WCAG des jetons (19 paires × 2 thèmes) | Exécuté ✅ | `python3 outils/contraste.py` |
| Build CSS déterministe, empreinte, aucune couleur en dur hors jetons | Exécuté ✅ | `outils/tests/test_contraste_css.py` |
| Verrou Redis de `beat` | Exécuté ⚠️ | testé avec `fakeredis` ; le processus `beat_unique` lui-même n'a pas tourné |
| OpenAPI valide et à jour (`docs/api/openapi.json`, vide pour l'instant) | Exécuté ✅ | `make openapi`, comparaison dans `verifier_tout.sh` |
| `ruff`, `djlint`, `bandit`, `makemigrations --check` | Exécuté ✅ | `outils/verifier_tout.sh` : 14 contrôles, 0 sauté |
| `pip-audit` sur `base.txt` | Exécuté ✅ | « No known vulnerabilities found » |
| Caddy local : liste blanche d'administration | Exécuté ✅ | Caddy 2.11.7 : variable absente, vide ou non listée → 404 ; listée → amont |
| Caddy local : limites de corps | Exécuté ✅ | site : 0,5 Mo → 200, 1,5 Mo → 413 ; `/uploads` : 1,5 Mo → 200, 2,5 Mo → 413 |
| Caddy de production | Exécuté ⚠️ | `caddy validate` seulement |
| Structure du Compose (réseaux, volumes, ports) | Exécuté ⚠️ | `test_compose.py` lit le YAML (mutation vérifiée) ; **aucun démarrage** |
| `Dockerfile`, `docker-compose`, `make up`, `make fumee` | Non exécuté ⛔ | Docker absent |
| Script d'init PostgreSQL (`01-roles.sh`), sauvegarde (`boucle.sh`) | Non exécuté ⛔ | `bash -n` seulement |
| Workflows GitHub Actions | Non exécuté ⛔ | YAML valide, jamais lancés |
| Tests e2e, axe | Non exécuté ⛔ | Chromium non téléchargeable |

### Sortie de `outils/tester_hooks.sh`

```
9 files already formatted
Contrôles Immo+ :
  ✔ noms et mots interdits
  ✔ hygiène (secrets, débogage, tailles)
  ✔ nom de la branche courante
  ✔ ruff check (serveur)
  ✔ ruff check (outils)
  ✔ ruff format --check
  ⏭ contrôles Django — sautés (Django non installé)
✔ Contrôles réussis (1 sauté(s)).
Cas 1 — message sans format
9 files already formatted

✗ Message de commit refusé :
  - En-tête invalide : « ajout truc ».
    Format attendu : type(portée): sujet
    Exemple :
    feat(messagerie): ajouter l'envoi de message

    Refs: EF-MSG-03

  Exemple valide :
    feat(messagerie): ajouter l'envoi de message

    Refs: EF-MSG-03

  ✔ cas 1 — commit « ajout truc » : refus comme attendu
Cas 2 — feat sans Refs
9 files already formatted

✗ Message de commit refusé :
  - Les commits feat/fix exigent une ligne « Refs: EF-XXX-NN[, ENF-XXX-NN] » ou « Refs: n/a ».

  Exemple valide :
    feat(messagerie): ajouter l'envoi de message

    Refs: EF-MSG-03

  ✔ cas 2 — feat sans Refs : refus comme attendu
Cas 3 — feat avec Refs
9 files already formatted
  ✔ cas 3 — feat avec Refs : succes comme attendu
Cas 4 — dossier interdit
10 files already formatted

✗ Contrôle des noms : refusé
  - backend/x.py : le chemin contient un mot interdit (« backend »). Le dossier s'appelle « serveur/ ».

  ✔ cas 4 — fichier dans un dossier interdit : refus comme attendu
Cas 5 — mauvaise branche
      ✗ Push annulé : nom de branche refusé (voir ci-dessus).
  ✔ cas 5 — push de Feat/Mauvais_Nom : refus comme attendu
Cas 6 — push direct sur main
      ✗ Push annulé : push direct sur « main » interdit. Crée une branche (ex. feat/mon-changement) et ouvre une demande de fusion.
  ✔ cas 6 — push direct sur main : refus comme attendu
Cas 7 — commit wip poussé
      ✗ Push annulé : le commit d590d7c8 ne respecte pas le format (voir ci-dessus).
  ✔ cas 7 — commit « wip » poussé : refus comme attendu
Cas 8 — secret
10 files already formatted

✗ Contrôle d'hygiène : refusé
  - c.py:1 : clé d'accès AWS détecté. Les secrets vont dans l'environnement, jamais dans le dépôt.

  ✔ cas 8 — fausse clé secrète (commit) : refus comme attendu
      ✗ Push annulé : les contrôles complets ont échoué (voir ci-dessus).
  ✔ cas 8 — fausse clé secrète (push après --no-verify) : refus comme attendu
Cas 9 — série valide
9 files already formatted
9 files already formatted
  ✔ cas 9 — série valide poussée : succes comme attendu

Résultat : 10 conforme(s), 0 non conforme(s).
```
