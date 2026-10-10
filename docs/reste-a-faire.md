# Reste à faire — état au point d'arrêt

Priorité fixée : un système complet qui tourne de bout en bout, sans polissage. Ordre imposé : a comptes, b annonces, c médias, d fil et recherche, e messagerie, f notifications, g modération et administration minimales.

**Les lettres a à g sont toutes implémentées et testées** (PostgreSQL et Redis réels). La liste exhaustive de ce qui reste à vérifier, des décisions prises seul et des limites est dans **`docs/a-verifier.md`** : la lire en premier.

## Fait

| | Contenu | Où |
|---|---|---|
| Phase 0 | Dépôt, hooks, Django, Docker/Compose/Caddy écrits, design (jetons, CSS), outils | `docs/avancement.md` |
| a. comptes | OTP, connexion, JWT + rotation, appareils, inscription, activation gérant, mot de passe oublié, changement de numéro, suppression, préférences | `apps/accounts`, `web/views_auth.py` |
| a. administration | Hôte séparé, 2FA TOTP, verrouillage, liste blanche d'IP, sessions propres, journal, création de gérants, suspension/bannissement, paramètres | `adminsite/` |
| b. annonces | Quartiers, annonces, brouillon, publication avec règles, confirmation, masquage, louée, Markdown assaini, détection des coordonnées, distance au campus | `apps/listings`, `web/views_pro.py` |
| c. médias | Envoi reprenable, photos (WebP, EXIF retiré), vidéo (MP4 720p + affiche), ordre, couverture, nettoyage | `apps/media`, `apps/listings/services/medias.py` |
| d. fil et recherche | `GET /v1/listings` (filtres, tri, curseur, recherche sans accents tolérante aux fautes, cache 60 s), fiche par id ou slug (jamais d'adresse ni de numéro), vues dédupliquées (Redis puis `daily_stats`), favoris, alertes (5 actives), notifications « plus disponible » et « nouvelle correspondance », tableau de bord gérant. Pages `/`, `/annonces`, `/annonces/<slug>`, `/quartiers/<slug>`, `/compte/favoris`, `/compte/alertes`, `robots.txt`, `sitemap.xml` | `apps/listings/{selectors,services/{fil,filtres,vues,favoris,alertes}}`, `web/views_public.py` |
| e. messagerie | Conversations et messages (séquence verrouillée, idempotence `client_msg_id`), ouverture + premier message, contrôle des coordonnées (modes `mask`, `flag`, `block`), lecture, blocage, silence, lecture seule 30 j après location, WebSocket (ticket 30 s, 5 connexions, présence par appareil, 30 événements/min, inactivité 60 s), rattrapage des notifications, rappel au gérant après 2 h, délai et taux de réponse. Pages `/compte/messages*` | `apps/chat`, `web/views_public.py` |
| f. notifications | Centre (liste, non lues bornées à 100, lue, tout lu), unicité par clé, préférences par catégorie, push par appareil avec cinq essais, présence qui supprime le push, jetons invalides désactivés, fournisseurs console / Expo / squelette FCM, diffusion `notification.new` | `apps/notifications`, `apps/core/providers/push.py` |
| g. modération | Signalements (un ouvert par auteur et cible), signalements automatiques, « déjà louée » (3 distincts), actions (message masqué ou supprimé, annonce masquée ou retirée, avertissement, suspension, bannissement, rétablissement), plafonds par rôle, lecture de conversation journalisée avec motif, tableau de bord de file. Administration : relecture des annonces (approuver / refuser), signalements, décisions | `apps/moderation`, `adminsite/admin_moderation.py` |
| Liaisons | Suspension ou bannissement d'un gérant masque ses annonces et les remet à la levée ; suppression d'un compte gérant archive ses annonces | `apps/listings/receivers.py`, `apps/accounts/signals.py` |
| Planification | 12 tâches périodiques dans `config/celery.py` (fraîcheur, vidéos louées, archivage, fin de suspension, OTP, rétention d'audit, indicateurs) | `config/celery.py`, `*/tasks.py` |
| Données de départ | `make seed` (paramètres, 12 quartiers de Parakou) ; `make seed DEMO=1` ajoute un gérant et 6 annonces (développement) | `adminsite/management/commands/seed.py` |

Mesures : voir `docs/a-verifier.md`, section « Résultats ».

## Reste à faire

1. **Tout ce qui est listé dans `docs/a-verifier.md`** (priorités A1 à A4).
2. Coordonnées réelles des quartiers et du campus (relevé terrain).
3. Fournisseurs réels : push (Expo ou FCM), SMS.
4. Client mobile (hors dépôt actuel) : consomme l'API et le WebSocket.
5. Facturation (`apps/billing`) : désactivée au lancement (`SUBSCRIPTION_ENABLED`).
6. Vidéo : une seule variante MP4 ; pas de HLS multi-qualité (reporté volontairement).

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
