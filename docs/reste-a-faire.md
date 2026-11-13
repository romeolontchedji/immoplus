# Reste à faire — état au point d'arrêt

Priorité fixée : un système complet qui tourne de bout en bout, sans polissage. Ordre imposé : a comptes, b annonces, c médias, d fil et recherche, e messagerie, f notifications, g modération et administration minimales.

**Les lettres a à g sont toutes implémentées et testées** (PostgreSQL et Redis réels). La liste exhaustive de ce qui reste à vérifier, des décisions prises seul et des limites est dans **`docs/a-verifier.md`** : la lire en premier.

## Fait

| | Contenu | Où |
|---|---|---|
| Phase 0 | Dépôt, hooks, Django, Docker/Compose/Caddy écrits, design (jetons, CSS), outils | `docs/avancement.md` |
| a. comptes | Nom d'utilisateur (ADR 0009), connexion, JWT + rotation, appareils, inscription, clé de secours, gérants par lien d'activation, mot de passe oublié (e-mail, clé, équipe), e-mail ajouté au profil, suppression, préférences | `apps/accounts`, `web/views_auth.py` |
| a. administration | Hôte séparé, double authentification par code courriel, verrouillage, liste blanche d'IP, sessions propres, journal, création de gérants, suspension/bannissement, paramètres | `adminsite/` |
| b. annonces | Quartiers, annonces, brouillon, publication directe d'un gérant vérifié (courriel à l'équipe), confirmation, masquage, **louée = médias supprimés et annonce archivée aussitôt**, avis liés au gérant, Markdown assaini, détection des coordonnées, distance au campus | `apps/listings`, `web/views_pro.py` |
| c. médias | Envoi reprenable, photos (WebP, EXIF retiré), vidéo (MP4 720p + affiche), ordre, couverture, nettoyage | `apps/media`, `apps/listings/services/medias.py` |
| d. fil et recherche | `GET /v1/listings` (filtres, tri, curseur, recherche sans accents tolérante aux fautes, cache 60 s), fiche par id ou slug (jamais d'adresse ni de numéro), vues dédupliquées (Redis puis `daily_stats`), favoris, alertes (5 actives), notifications « plus disponible » et « nouvelle correspondance », tableau de bord gérant. Pages `/`, `/annonces`, `/annonces/<slug>`, `/quartiers/<slug>`, `/compte/favoris`, `/compte/alertes`, `robots.txt`, `sitemap.xml` | `apps/listings/{selectors,services/{fil,filtres,vues,favoris,alertes}}`, `web/views_public.py` |
| e. messagerie | Conversations et messages (séquence verrouillée, idempotence `client_msg_id`), ouverture + premier message, contrôle des coordonnées (modes `mask`, `flag`, `block`), lecture, blocage, silence, lecture seule 30 j après location, WebSocket (ticket 30 s, 5 connexions, présence par appareil, 30 événements/min, inactivité 60 s), rattrapage des notifications, rappel au gérant après 2 h, délai et taux de réponse. Pages `/compte/messages*` | `apps/chat`, `web/views_public.py` |
| f. notifications | Centre (liste, non lues bornées à 100, lue, tout lu), unicité par clé, préférences par catégorie, push par appareil avec cinq essais, présence qui supprime le push, jetons invalides désactivés, fournisseurs console / Expo / squelette FCM, diffusion `notification.new` | `apps/notifications`, `apps/core/providers/push.py` |
| Paiements | KKiaPay (fenêtre du site, vérification serveur, webhook), abonnement des gérants et alertes payantes des locataires (cases séparées, prix réglables), activation en espèces, page Abonnement, table `transactions`. **Éteints par défaut** | `apps/billing`, `web/views_paiement.py`, `docs/administration.md` |
| Administration | Statistiques : page dédiée (chiffres clés, tableaux par gérant et par locataire) et bloc sur chaque fiche | `adminsite/statistiques.py` |
| g. modération | Signalements (un ouvert par auteur et cible), signalements automatiques, « déjà louée » (3 distincts), actions (message masqué ou supprimé, annonce masquée ou retirée, avertissement, suspension, bannissement, rétablissement), plafonds par rôle, lecture de conversation journalisée avec motif, tableau de bord de file. Administration : relecture des annonces (approuver / refuser), signalements, décisions | `apps/moderation`, `adminsite/admin_moderation.py` |
| Liaisons | Suspension ou bannissement d'un gérant masque ses annonces et les remet à la levée ; suppression d'un compte gérant archive ses annonces | `apps/listings/receivers.py`, `apps/accounts/signals.py` |
| Planification | 12 tâches périodiques dans `config/celery.py` (fraîcheur, vidéos louées, archivage, fin de suspension, rétention d'audit, indicateurs) | `config/celery.py`, `*/tasks.py` |
| Données de départ | `make seed` (paramètres, 12 quartiers de Parakou) ; `make seed DEMO=1` ajoute un gérant et 6 annonces (développement) | `adminsite/management/commands/seed.py` |

Mesures : voir `docs/a-verifier.md`, section « Résultats ».

## Reste à faire

1. **Tout ce qui est listé dans `docs/a-verifier.md`** (priorités A1 à A4).
2. Coordonnées réelles des quartiers et du campus (relevé terrain).
3. Fournisseurs réels : push (Expo), serveur SMTP (Brevo), vraies clés Turnstile. Plus de SMS (ADR 0009).
4. Client mobile (hors dépôt actuel) : consomme l'API et le WebSocket.
5. Paiements : **essai complet en sandbox KKiaPay**, vérification de la forme de `stateData` dans le webhook (sert à relier un paiement fermé trop tôt à sa transaction), puis activation (`PAID_ALERTS_ENABLED` d'abord, `SUBSCRIPTION_ENABLED` ensuite). Pas encore de remboursement ni de renouvellement automatique : un abonnement se rachète.
6. Vidéo : une seule variante MP4 ; pas de HLS multi-qualité (reporté volontairement). Durée maximale gardée à 60 s.
7. Application mobile : retirer la caution du loyer (`AnnonceModifierScreen`, `InfosStep`, `brouillon`, `FicheScreen`) avec une version de l'API ; « marquer louée » répond maintenant `archived` ; l'e-mail confirmé et le paiement des alertes ne sont exigés que sur le site (l'API répond 402 `payment_required` quand les alertes sont payantes).
8. Notification push des alertes sur téléphone : demande `PUSH_PROVIDER=expo` (aujourd'hui `console` sur le VPS) et une application compilée avec jetons push.
9. Suppression définitive de comptes de test : non construite (les lignes d'audit ne se suppriment pas ; les comptes sont anonymisés).
10. Sécurité des dépendances : les alertes Dependabot de GitHub sont à traiter.

## Jamais exécuté ou jamais testé
- **Docker, Compose** : la pile **tourne en production** sur le VPS partagé depuis novembre 2026 (déploiement par `infra/vps/deployer.sh`) ; elle n'a jamais été lancée dans le bac à sable de développement, où `make up` et `make fumee` n'ont pas été exécutés. Le script `infra/postgres/init/01-roles.sh` a servi sur le VPS (un droit manquant, `GRANT retention TO app`, y a été découvert et corrigé).
- **Tests automatiques** : pytest, `djlint` et `lint-imports` ne sont pas installés sur le poste de développement Windows ; ils ne s'exécutent que dans la CI GitHub, qui **ne démarre que lorsqu'une pull request est ouverte** (la branche `chore/integration` accumule les travaux). Deux tests de `outils/tests/test_creer_env.py` échouent sur Windows (encodage), indépendamment du code.
- **Navigateur** : les pages et les scripts (`envoi.js`, `paiement.js`) sont essayés à la main sur téléphone par le porteur ; aucun test automatisé en navigateur, et la fenêtre KKiaPay n'a pas été vue en test automatique. L'administration Django standard nécessite `style-src 'unsafe-inline'` (réglage admin uniquement).
- **Cache des fichiers statiques** : Caddy sert `/static/` en cache d'un an ; depuis le 2026-11-18 les adresses portent une empreinte (`?v=…`, `config/stockage.py`). Avant, un script corrigé pouvait ne jamais atteindre un navigateur qui l'avait déjà chargé.
- **Redis réel** : les tests utilisent `fakeredis` pour les compteurs de sécurité et un cache en mémoire ; le `readyz` seul parle à un vrai Redis. Le comportement sous éviction réelle n'est pas testé.
- **Fournisseurs réels** : Cloudflare Turnstile (branché, testé avec les clés de test officielles), SMTP (des courriels réels arrivent depuis le VPS), KKiaPay (clés réelles fournies ; premier paiement d'alerte réussi, confirmation par webhook vue dans les journaux ; essai complet en sandbox à faire), notifications push Expo (non essayées sur un vrai téléphone, `PUSH_PROVIDER=console`). SMS et attestation d'appareil supprimés (ADR 0009).
- **Caddy de production** : validé par `caddy validate` seulement. Les limites de corps et la liste blanche ont été vérifiées avec Caddy 2.11.7 sur la configuration locale.
- **Charge, performances, Lighthouse, ZAP, sauvegardes, restauration** : non faits (hors périmètre demandé). `infra/backup/boucle.sh` n'a pas tourné.
- Traitement vidéo : testé avec des vidéos synthétiques (testsrc2) de 11 s en 854×480 ; pas avec des vidéos de téléphone réelles (rotation, HEVC, HDR).

## Pour reprendre
```bash
cd immoplus && python3 -m venv .venv && .venv/bin/pip install -r serveur/requirements/dev.txt
# PostgreSQL 16 et Redis démarrés, puis :
export DB_USER=<superutilisateur> DB_PASSWORD=<mot de passe> DB_NAME=immoplus
cd serveur && ../.venv/bin/python -m pytest -q     # 569 tests attendus
```
Les tests créent leurs rôles `app`, `admin_app`, `retention` (voir `serveur/conftest.py`) : l'utilisateur de test doit être superutilisateur PostgreSQL.
