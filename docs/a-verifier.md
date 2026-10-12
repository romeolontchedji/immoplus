# À vérifier et à corriger après cette session

Ce fichier liste, par ordre d'importance, ce que **je n'ai pas pu vérifier**, ce que j'ai **décidé seul**
(et que vous pouvez contester) et les **limites connues**. Rien ici n'est caché : tout ce qui n'est pas listé
est couvert par un test qui passe (mesure de fin de session : voir « Résultats »).

## Résultats de la session
- `pytest` (PostgreSQL 16 et Redis réels, exécution en série) : **835 tests passent, 3 échecs
  d'environnement, 1 ignoré**, couverture 92 % (seuil 85 %) (WebSocket, voir A1).
  Base de départ : 569 tests.
- `ruff check`, `ruff format --check`, `djlint --check`, `lint-imports` (10 contrats), `makemigrations --check`,
  `verifier_noms.py`, `verifier_hygiene.py`, `contraste.py` : conformes.
- `docs/api/openapi.json` régénéré (`--validate --fail-on-warn`) : à jour.
- **Rien n'a tourné dans Docker**, ni dans un navigateur, ni avec un vrai fournisseur (push, SMS).

## Session web (`docs/plan-action-web.md`) — à revérifier
- **Phases 0 à 6 entamées** : matrice des parcours (`docs/web-parcours.md`), navigation/composants,
  catalogue et fiche, identité/espace locataire (préférences, appareils, changement de numéro),
  tableau de bord gérant (`/pro/dashboard`), refonte de « Mes annonces » et de l'éditeur,
  conversations/alertes/notifications côté web (repli HTTP).
- **Administration (Phase 6)** : l'index du site admin (hôte séparé, 2FA) affiche une **Vue d'ensemble**
  avec des compteurs réels (modération ouverte/hors délai, signalements par motif, sanctions en cours,
  gérants en attente, annonces publiées, taux de réponse, compteurs du jour, journal du jour réservé
  aux administrateurs). Gabarits d'`adminsite` prioritaires sur ceux de Django : l'ordre des `DIRS`
  est réordonné dans `config/settings/admin_base.py`. Piste à revoir : le gabarit d'index vit dans
  `serveur/adminsite/templates/admin/index.html` (normalement trouvé avant celui de `django.contrib.admin`).
  Les maquettes ADM (PNG) n'ont **pas** pu être lues (aucun navigateur/visionneuse) : la fidélité visuelle
  des 4 écrans reste à confirmer.
- **Médias gérants** : l'éditeur expose désormais la couverture, l'ordre (monter/descendre), la
  suppression (avec confirmation) et une auto-rafraîchissement pendant le traitement ; l'aperçu de la
  carte est rendu dans l'éditeur. La **reprise d'envoi** reste via `envoi.js` (TUS minimal) ; pas de
  glisser-déposer ni de sélection multiple de couverture.
- **Phase 5 sans temps réel** : le WebSocket dépend d'un ADR sur `daphne` (A1) ; la page de conversation
  garde un `meta refresh` de 60 s. Alertes : création, suppression, pause/réactivation **et
  modification** exposés. Notifications : lecture individuelle, « tout lire » **et regroupement
  visuel des notifications identiques**.
- **Écart d'environnement, non un bug** : hors Docker, `make test` complet échoue sur 3 tests :
  `test_readyz_ok_quand_tout_repond` (le disque `/home` est à ~91 %, au-dessus du seuil
  `MEDIA_DISK_REFUS_POURCENT=85`, et `REDIS_QUEUE_URL` pointe un Redis non joignable hors pile),
  et `TestClesDeSecurite::test_absente` (les variables `JWT_SIGNING_KEY`/`OTP_HMAC_KEY` sont exportées
  dans le shell de session). Un `env -u JWT_SIGNING_KEY -u OTP_HMAC_KEY` fait repasser ces deux derniers.
- **B10/B11 partiellement périmés** : le tableau de bord web `/pro/dashboard` existe ; l'espace gérant web
  utilise toujours `/compte/messages` (pas de page messages dédiée au gérant), ce qui n'empêche pas les
  parcours actuels mais mérite un point d'attention selon les maquettes.
- **Toujours non vérifié** : aucun navigateur réel (Chromium absent), donc contrastes à l'œil,
  navigation clavier de bout en bout, 360/390 px et CSP réelle restent à contrôler (A1/A3).


## A. À faire en premier (bloquant ou risqué)

**A1. Tests WebSocket non exécutés.** `apps/chat/tests/test_websocket.py` (12 tests : ticket à usage unique, 5 connexions,
présence, événements, trame de 8 Ko, 30 événements/min, inactivité 60 s) est écrit mais **ignoré** : `channels.testing`
exige `daphne`, absent des dépendances. À faire : ajouter `daphne` à `serveur/requirements/dev.in`, recompiler
`dev.txt`, lancer ces tests, corriger ce qui casse. **Le consommateur WebSocket n'a donc jamais tourné.**

**A2. Rôle PostgreSQL `app` réel.** Tous mes tests utilisent un super-utilisateur. Il faut lancer le site et l'API avec les vrais
rôles (`infra/postgres/init/01-roles.sh`) et vérifier qu'aucune requête nouvelle ne tombe sur un droit manquant.
Points précis : (1) `gerants_publics` lit `gerant_profiles` par `.values()` sur des colonnes publiques seulement (voulu) ;
(2) la tâche de nuit écrit `response_rate_30d` et `median_response_min` (colonnes autorisées en UPDATE) ;
(3) `audit.services.purger_selon_retention` fait `SET LOCAL ROLE retention` : il faut que le rôle de connexion du worker
en soit membre (ce n'est le cas que pour `migrate` dans `01-roles.sh`) — sinon la purge échoue ou ne fait rien ;
(4) les nouvelles tables héritent des droits par défaut `app` et `admin_app` (lecture/écriture complètes) : à resserrer
si vous voulez que `app` ne puisse pas modifier `moderation_actions`, `reports` ou `audit`.

**A3. Docker, Compose, Caddy : jamais démarrés.** `config/asgi.py` a changé (routage WebSocket sous `/ws/v1/`).
Vérifier que Caddy transmet bien les en-têtes `Upgrade` et que l'origine autorisée (`AllowedHostsOriginValidator`)
accepte votre domaine. Vérifier aussi que le worker `notifications` écoute la file `notifications` (les tâches
`apps.notifications.*` y sont routées, y compris celles de la messagerie) et que `beat` charge le nouveau planning.

**A4. Premier lancement des tâches planifiées.** `config/celery.py` définit désormais 12 tâches périodiques
(vues 5 min, rattrapage push 1 min, rappels 30 min, fraîcheur 6 h, fin de suspension 1 h, nuit : lecture seule,
archivage, indicateurs gérants, purge OTP, rétention d'audit). Un test vérifie que chaque nom existe, mais **aucune
n'a tourné sous `beat`**. Surveiller la première nuit.

## B. Décisions prises seul (à valider ou à inverser)

**B1. Favoris : contrainte d'unicité `(user, listing)` au lieu d'une clé primaire composite** (CDC §9.11). La clé composite
Django faisait échouer la création de table ; l'effet est équivalent.

**B2. Contrainte de longueur des messages posée en SQL** (`messages_longueur_valide`, 1 à 2000 caractères) dans la
migration, hors du modèle : l'ORM ne sait pas l'exprimer sur un champ texte. `makemigrations --check` reste vide.

**B3. Colonne ajoutée à `messages` : `body_masked`.** Le CDC ne la prévoit pas. En mode `mask`, `body` garde le texte
d'origine (consultable par la modération) et `body_masked` ce que voit le destinataire.

**B4. Adresse privée dans le détail d'une conversation : réservée au gérant.** Le CDC (§10.5) dit « participant ». J'ai jugé
qu'un locataire ne doit pas obtenir l'adresse précise en ouvrant une conversation ; le gérant la donne lui-même.
Si vous voulez l'inverse : `ConversationDetail.get` dans `apps/chat/api/views.py`.

**B5. Blocage : celui qui bloque peut encore écrire**, l'autre non (lecture littérale de EF-MSG). Le blocage ne passe
pas en `read_only`. À confirmer.

**B6. Compte suspendu = ne peut ni écrire, ni ouvrir de conversation, ni se connecter en WebSocket.** Le comportement de
connexion HTTP existant (révocation des appareils à la suspension) est inchangé : un suspendu n'a donc pas de bandeau
explicatif « en consultation seule » comme le prévoit EF-MOD-05 ; il est déconnecté. À trancher.

**B7. Recherche : seuils de tolérance aux fautes** (trigrammes) réglés à 0,30 sur le titre et 0,40 sur le repère, et
désactivés sous 4 caractères. Mesurés sur quelques cas (transposition « chmabre » trouvée). **Non calibrés sur de vraies
annonces de Parakou** : trop de bruit ou trop peu de résultats possibles.

**B8. Un signalement automatique (coordonnées détectées) est créé pour chaque message détecté en mode `mask` ou `flag`**,
un seul dossier ouvert par message. En mode `block` le message est refusé, aucun dossier.

**B9. Sanctions notifiées avec la catégorie `account.sanction`** (non désactivable) pour toutes les actions : message
masqué/supprimé, annonce masquée/retirée, avertissement, suspension, bannissement, rétablissement.
Un gérant dont l'annonce est masquée reçoit donc deux notifications (`listing.hidden` et `account.sanction`).

**B10. Tableau de bord gérant** (`GET /v1/pro/dashboard`) : version minimale (annonces par statut, vues/favoris/conversations
sur 30 jours, à confirmer, non lus, taux et délai de réponse). Pas de page web `/pro/dashboard` ni de statistiques par annonce.

**B11. Le site web n'a pas de temps réel.** La page de conversation se rafraîchit toutes les 60 s (`meta refresh`) et marque
comme lu à l'ouverture. Pas de WebSocket côté navigateur, pas de `messagerie.js`. Les URL du CDC pour l'espace compte
(`/compte/...`) ont été utilisées ; l'espace gérant n'a pas de page messages dédiée au gérant (il utilise `/compte/messages`).

**B12. Données des quartiers (`seed`) : coordonnées approximatives.** Les 12 quartiers de Parakou et leurs points sont
**inventés à partir de ma mémoire** : ils servent à la distance au campus. **À relever sur le terrain avant toute mise
en production.** Idem pour `CAMPUS_REFERENCE` (déjà dans le projet, non revu).

## C. Limites et manques connus

- **Pré-modération** : `LISTING_PREMODERATION` existe en paramètre, mais la règle « première annonce d'un gérant relue »
  reste celle d'avant (statut `processing`) ; l'approbation passe par l'admin (action « Approuver et publier »).
- **Notifications groupées** (« 3 nouveaux messages de X ») : seule la `collapse_key` est posée ; le regroupement visuel
  dépend de l'application mobile. Aucun résumé quotidien.
- **Push** : seul le fournisseur « console » (développement) est testé ; `ExpoPushProvider` n'a jamais parlé à Expo ;
  `FcmPushProvider` est un squelette qui lève `NotImplementedError`. Les jetons invalides sont désactivés (`push_invalid_at`).
- **SMS de repli au gérant** (`SMS_FALLBACK_ENABLED`) : écrit et testé avec un faux fournisseur, désactivé par défaut.
- **Rétention de l'audit** : fonction écrite, jamais exécutée avec le rôle `retention` (voir A2).
- **Fil** : cache de page 60 s invalidé par un compteur de version ; pas de cache HTTP côté Caddy.
- **Vues** : déduplication Redis 26 h par visiteur ; le visiteur anonyme du site web est la session (créée à la volée).
- **Alertes** : une seule valeur par quartier et par type depuis le formulaire web (l'API en accepte plusieurs).
- **Recherche** : pas de suggestion de quartier, pas de tri par pertinence (tri recent/loyer/distance seulement).
- **Admin Django** : les décisions de modération se prennent par le formulaire d'ajout de « Moderation action » (pas de
  boutons sur la fiche du signalement) ; la lecture de conversation passe par un lien dans l'URL
  `/moderation/report/<id>/conversation/` — aucun lien cliquable n'a été ajouté dans la liste. L'index du site
  admin affiche une Vue d'ensemble (voir « Session web ») ; la revue visuelle des 4 maquettes ADM n'a pas pu se faire.
- **Accessibilité et mobile** : pages publiques écrites avec les composants existants, **jamais ouvertes dans un navigateur**.
  Aucun test axe/Lighthouse. Le lecteur vidéo utilise `<video controls>` natif.
- **SEO** : `robots.txt` et `sitemap.xml` simples ; pas de balises Open Graph ni de données structurées.
- **`SITE_URL`** n'est pas défini dans les réglages : le plan du site et `robots.txt` retombent sur l'hôte de la requête.

## D. Pour reprendre

```bash
cd logeo && python3 -m venv .venv && .venv/bin/pip install -r serveur/requirements/dev.txt
# PostgreSQL 16 et Redis démarrés ; rôles app, admin_app, retention créés (voir infra/postgres/init/01-roles.sh)
cd serveur && DB_USER=<superutilisateur> DB_PASSWORD=<mdp> DB_NAME=logeo ../.venv/bin/python -m pytest -q -p no:randomly
```
Exécuter en **série** : le mode parallèle (`-n`) entre en conflit sur la création des rôles de la base de test
(problème antérieur à cette session).
