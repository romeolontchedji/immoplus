# Reste à faire — état au point d'arrêt

Priorité fixée en cours de route : un système complet qui tourne de bout en bout, sans polissage. Ordre imposé : a comptes, b annonces, c médias, d fil et recherche, e messagerie, f notifications, g modération et administration minimales.

**Arrêt demandé après c.** Les lettres d à g n'ont pas été commencées.

## Fait

| | Contenu | Où |
|---|---|---|
| Phase 0 | Dépôt, hooks, Django, Docker/Compose/Caddy écrits, design (jetons, CSS), outils | voir `docs/avancement.md` |
| a. comptes | OTP (plafonds, budget, friction, attestation), connexion à réponse uniforme et verrouillage progressif, JWT 15 min + rotation du refresh avec détection de vol, appareils, inscription, activation gérant, mot de passe oublié, changement de numéro, suppression (anonymisation), préférences. API `/v1/auth/*`, `/v1/me*`, `/v1/devices*`. Pages web : `/inscription`, `/connexion`, `/mot-de-passe-oublie`, `/compte` | `apps/accounts`, `web/views_auth.py` |
| a. administration | Hôte séparé, connexion e-mail + mot de passe + TOTP obligatoire, verrouillage `axes`, liste blanche d'IP (Caddy + Django), sessions dans `admin_sessions`, durée 30 min / 8 h, journal des actions, création de gérants, suspension/bannissement, paramètres, journal en lecture seule, commande `creer_personnel` | `adminsite/` |
| Base de données | Contraintes CHECK, déclencheurs (`users`, `gerant_profiles`, `audit_logs` en ajout seul), droits par colonne pour le rôle `app`, isolation des tables d'administration | migrations `accounts/0002`, `adminsite/0002` |
| b. annonces | Quartiers, annonces, médias (modèles), brouillon, modification, publication avec règles (§9.23), confirmation, masquage, louée/annuler louée, Markdown restreint assaini, détection des coordonnées, distance au campus. API `/v1/districts`, `/v1/pro/listings*`, `/v1/pro/markdown/preview`. Pages `/pro/annonces*` | `apps/listings`, `web/views_pro.py` |
| c. médias | Ouverture d'envoi avec quotas, envoi reprenable (tus minimal, `/uploads/{id}`), traitement photo (variantes WebP, EXIF retiré) et vidéo réel avec ffmpeg (MP4 720p + affiche), ordre, couverture, suppression, nettoyage des envois expirés, script d'envoi du site (`web/static/js/envoi.js`) | `apps/media`, `apps/listings/services/medias.py` |

Mesures du dernier passage : **569 tests passent**, couverture **94 %** (hors e2e). `ruff`, `bandit`, `import-linter` (10 contrats), `djlint`, `makemigrations --check`, OpenAPI valide et à jour : tous verts individuellement. Le script complet `outils/verifier_tout.sh` n'a pas été relancé une dernière fois après les deux derniers correctifs (import-linter, djlint).

## À faire, dans l'ordre

### Bloquant pour que ça tourne de bout en bout
1. **Première annonce bloquée en `processing`** : la relecture de la première annonce d'un gérant n'a aucune action d'approbation. Ajouter dans l'administration (g) un `ListingAdmin` avec l'action « Approuver et publier » qui appelle `apps.listings.services.annonces.mettre_en_ligne`, et « Refuser » (statut `hidden` + `moderation`).
2. **Aucune donnée de départ** : pas de quartiers de Parakou, pas de ligne `app_settings`. Écrire `make seed` (quartiers avec coordonnées réelles, un gérant et quelques annonces de démonstration). `CAMPUS_REFERENCE` vaut un point approximatif (9.337, 2.6303) : **à relever**.
3. **d. Fil, recherche, filtres, fiche** : rien d'écrit côté public. Sont déjà prêts : `search_vector` (tsvector français, GIN), index `unaccent` et `pg_trgm` (extensions créées), `distance_to_campus_m`, indexes de tri. À faire : `GET /v1/listings` (curseur, filtres, tri), `GET /v1/listings/{slug}` (position arrondie 3 décimales, distance arrondie à 50 m, **jamais** `address_private` ni le numéro du gérant), pages `/`, `/annonces`, `/annonces/<slug>`, lecteur vidéo (`playback_url`).
4. **e. Messagerie** : conversations, messages, HTTP d'envoi, WebSocket (Channels est configuré, `config/asgi.py` n'a aucune route), accusés de lecture, ticket WebSocket. Le contrôle des coordonnées (`listings.services.contenu.detecter`) est réutilisable pour les messages (mode `CONTACT_LEAK_MODE`).
5. **f. Notifications** : modèle, création, envoi push avec le fournisseur factice. Les jetons d'appareil sont déjà stockés (`PUT /v1/devices/current/push-token`) ; le fournisseur `PUSH_PROVIDER` n'est pas encore codé (seul SMS, attestation et anti-robot existent dans `apps/core/providers`).
6. **g. Modération** : signalements, actions, tableau de bord minimal dans `adminsite/admin.py` (gérants, annonces, signalements).

### Tâches planifiées jamais branchées
Aucun `beat_schedule` n'est défini (`config/celery.py`). À planifier :
- `apps.media.nettoyer_envois` (écrite),
- suppression des vidéos dont `delete_after` est passé et des originaux (`media_tmp`) 24 h après `ready` (non écrite),
- relances de fraîcheur des annonces (`reminder_stage`, masquage `stale`) (non écrite),
- réactivation des suspensions échues, purge des `otp_codes` anciens, purge d'audit via le rôle `retention` (non écrites).

### Liaisons manquantes
- Le signal `apps.accounts.signals.compte_supprime` n'a **aucun récepteur** : les annonces d'un gérant supprimé ne sont pas archivées.
- La suspension ou le bannissement d'un gérant ne masque pas ses annonces (`hidden_reason = gerant_suspended` prévu, non appliqué).
- Le coupe-circuit OTP n'alerte que par journal critique et trace d'audit (pas de notification, phase f).
- Vidéo : une seule variante MP4 ; pas de HLS multi-qualité (volontairement reporté).

### Reste de la phase 0 (inchangé)
`make seed`, `make vendor`, `make docs` échouent volontairement. `AGENTS.md`, `docs/verification.md` et `docs/avancement.md` décrivent la phase 0 et ne mentionnent pas les fonctionnalités a à c. `django-unfold` a été retiré (voir `decisions.md`).

## Jamais exécuté ou jamais testé
- **Docker, Compose, `make up`, `make fumee`** : Docker absent du bac à sable. La pile n'a **jamais démarré** ; seul le YAML est lu par des tests. Le script d'initialisation PostgreSQL (`infra/postgres/init/01-roles.sh`) n'a jamais tourné : les droits par colonne sont testés avec `SET ROLE` sur des rôles recréés, pas avec les vrais mots de passe de connexion.
- **GitHub Actions** : workflows jamais exécutés. Protection de la branche `main` : non appliquée (voir `docs/contribuer.md`).
- **Navigateur** : `envoi.js`, l'anneau de focus, la CSP de l'administration et les pages ne sont pas testés dans un navigateur (Chromium indisponible). Seul le HTML rendu est contrôlé. L'administration Django standard nécessite `style-src 'unsafe-inline'` (réglage admin uniquement).
- **Redis réel** : les tests utilisent `fakeredis` pour les compteurs de sécurité et un cache en mémoire ; le `readyz` seul parle à un vrai Redis. Le comportement sous éviction réelle n'est pas testé.
- **Fournisseurs réels** : SMS (`generic_http` testé contre un faux serveur local, agrégateur non choisi), Cloudflare Turnstile (jamais appelé), Play Integrity (squelette, lève une erreur), notifications push (absent).
- **Caddy de production** : validé par `caddy validate` seulement. Les limites de corps et la liste blanche ont été vérifiées avec Caddy 2.11.7 sur la configuration locale.
- **Charge, performances, Lighthouse, ZAP, sauvegardes, restauration** : non faits (hors périmètre demandé). `infra/backup/boucle.sh` n'a pas tourné.
- Traitement vidéo : testé avec des vidéos synthétiques (testsrc2) de 11 s en 854×480 ; pas avec des vidéos de téléphone réelles (rotation, HEVC, HDR).

## Pour reprendre
```bash
cd logeo && python3 -m venv .venv && .venv/bin/pip install -r serveur/requirements/dev.txt
# PostgreSQL 16 et Redis démarrés, puis :
export DB_USER=<superutilisateur> DB_PASSWORD=<mot de passe> DB_NAME=logeo
cd serveur && ../.venv/bin/python -m pytest -q     # 569 tests attendus
```
Les tests créent leurs rôles `app`, `admin_app`, `retention` (voir `serveur/conftest.py`) : l'utilisateur de test doit être superutilisateur PostgreSQL.
