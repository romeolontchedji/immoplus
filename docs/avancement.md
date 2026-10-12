# Avancement

> **À jour :** voir `docs/reste-a-faire.md` (comptes, annonces et médias faits ; fil, messagerie, notifications et modération à faire). Le reste de ce fichier décrit la phase 0.

**Chantier en cours : expérience web (`docs/plan-action-web.md`).** Phase 0 (matrice `docs/web-parcours.md`,
palette conservée), phase 1 (fondation : shell, navigation repliable, composants réutilisables, styleguide)
et phase 2 (découverte : catalogue avec filtres récapitulés, fiche avec galerie et alerte) en cours de
livraison. Voir la section « Plan web » en bas de ce fichier.

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

## Mise à jour — fonctionnalités d à g
Les fonctionnalités a à g sont implémentées et testées. Détail dans `docs/reste-a-faire.md` ; points à vérifier, décisions prises seul et limites dans `docs/a-verifier.md`.

## Plan web (`docs/plan-action-web.md`)

- **Phase 0 — matérialisée.** Matrice parcours/routes/services/permissions dans `docs/web-parcours.md` ;
  décision de palette : jetons émeraude conservés (référence visuelle cobalt non reprise).
- **Phase 1 — fondation.** Navigation desktop/mobile repliable sans JavaScript (`<details>`), liens actifs
  (`aria-current`), pied de page structuré ; composants `etats` (vide/chargement/erreur), `etapes`,
  `filtres` (récapitulatif retirable), `galerie`, `fiche` ; exemples ajoutés à `/styleguide`.
- **Phase 2 — découverte.** Catalogue : en-tête, filtres, récapitulatif des filtres actifs effaçables,
  état vide avec création d'alerte, cartes avec loyer formaté et durée vidéo. Fiche : fil d'Ariane,
  galerie avec visionneuse plein écran en CSS (`:target`), loyer/caractéristiques, gérant vérifié,
  favori, signalement et alerte contextuelle. Tests web et sélecteurs au vert.
- **Phase 3 — identité et espace locataire.** Barre d'étapes sur inscription et mot de passe oublié ;
  espace compte enrichi : préférences de notification (`/compte/preferences`), appareils connectés
  (`/compte/appareils`, révocation), changement de numéro par OTP (`/compte/numero`). Services existants
  réutilisés (aucune règle métier dans les vues).
- **Phase 4 — espace gérant.** Tableau de bord web (`/pro/dashboard`) branché sur
  `tableau_de_bord_gerant` ; « Mes annonces » en table desktop + liste mobile avec statut et commandes
  autorisées par statut ; éditeur par sections (informations, localisation, loyer/équipements, médias,
  publication) **avec aperçu de la carte** ; médias gérés dans l'éditeur (couverture, ordre,
  suppression avec confirmation, auto-rafraîchissement pendant le traitement). Un gérant ne lit jamais
  les annonces d'un autre (couvert par test).
- **Phase 5 — conversations, alertes, notifications (repli HTTP).** Liste de conversations et fil
  retravaillés (annonce, dates, non-lus, sourdine, statut, bulles accessibles) ; notifications avec
  liens profonds, lecture individuelle, « tout lire » **et regroupement des notifications identiques** ;
  alertes avec création, suppression (avec confirmation), pause/réactivation **et modification** par
  formulaire pré-rempli. **Le temps réel reste hors périmètre** : la dépendance `daphne`/WebSocket
  attend un ADR (voir `docs/a-verifier.md` A1) ; la page de conversation conserve son rafraîchissement
  HTTP.

- **Phase 6 — administration (hôte séparé).** Routes d'administration 404 sur le domaine public
  (testé), connexion 2FA OTP, liste blanche d'adresses, journal audit ; **Vue d'ensemble** sur l'index
  avec compteurs réels (modération ouverte/hors délai, sanctions en cours, gérants en attente,
  annonces publiées, taux de réponse, compteurs du jour, journal du jour réservé aux administrateurs).
  Les écrans Gérants, Modération et Journal s'appuient sur les `ModelAdmin` existants (motif obligatoire
  avant lecture d'une conversation, journal filtre par action/rôle). Gabarits d'`adminsite` prioritaires
  sur ceux de Django (DIRS réordonné en `admin_base`). La revue visuelle des 4 maquettes reste à faire
  (PNG illisibles ici, pas de navigateur).

- **Phase 7 — intégration, conformité et vérification globale.**
  Suite `./outils/verifier_tout.sh` au vert complet (WCAG jetons, tests des outils, ruff check,
  ruff format, djlint, import-linter, bandit, makemigrations --check, OpenAPI valide et à jour,
  pytest partiel sans PostgreSQL).
  Feuilles de styles compilées et minifiées sans erreur avec `outils/construire_css.py`.
  Les interfaces publiques (catalogue, fiches, alertes, favoris, conversations, compte) et gérant (tableau de bord,
  gestion des annonces, éditeur multi-étapes) ainsi que l'administration (`adminsite`) intègrent les tokens,
  la grille, les formulaires accessibles et les états prévus par les maquettes.

Reste : la revue visuelle in situ et l'E2E navigateur complet avec Chromium (dès qu'un environnement
graphique/Chromium ou Docker est disponible), ainsi que l'arbitrage ADR sur Daphne/WebSockets.


