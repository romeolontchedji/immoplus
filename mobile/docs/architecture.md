# Architecture de l'application mobile

## Principes

1. **Le serveur est la source de vérité.** L'application affiche, met en cache et file des envois ; elle ne décide d'aucune règle métier
   (publiabilité, limites, modération). Les erreurs de champ renvoyées par l'API sont réaffichées telles quelles.
2. **Un contrat typé.** Les chemins, paramètres et réponses viennent de `docs/api/openapi.json` → `src/api/genere/api.d.ts`
   (`npm run api:generer`). Quand l'API change, la compilation TypeScript le dit.
3. **Tout est en ligne par défaut, tolérant au réseau coupé.** Lecture : cache persisté du fil et des fiches. Écriture : file d'envoi
   idempotente pour les messages. Le reste demande le réseau et le dit.
4. **Des routes minces, des fonctionnalités épaisses.** Un fichier de `src/app` ne contient aucune logique.

## Couches et sens des dépendances

```
src/app  ──►  src/features/*  ──►  src/ui · src/api · src/realtime · src/state · src/storage · src/lib
```

- `src/app` importe des `features` ; **jamais l'inverse** (règle ESLint).
- Les `features` ne s'importent pas entre elles, sauf `features/auth/AuthRequired` (garde d'écran partagée) ; ce qui est commun descend dans `ui`, `api`, `lib` ou `state`.
- `api`, `storage`, `realtime`, `lib` ne connaissent ni React Native (écrans) ni les `features` : ils sont testés sous Node, sans appareil.

## Navigation et rôles (Expo Router)

Groupes de routes : `(auth)`, `(locataire)` (onglets), `(partage)` (fiche, conversation, notifications, réglages, modales) et le dossier `pro/`
(onglets du gérant). Le rôle du compte (`client` / `gerant`) choisit l'espace ; les visiteurs sans compte parcourent le fil et les fiches.
Voir la table complète dans `docs/ecrans.md`. Pas de `typedRoutes` pour l'instant (à activer une fois les écrans stabilisés).

Pourquoi `pro/…` et non un second groupe : deux groupes ne peuvent pas définir la même URL (`/messages` locataire et gérant se
chevaucheraient). Le gérant a donc un préfixe d'URL réel ; la conversation, la fiche et les notifications, communes, vivent dans `(partage)`.

## Session et authentification

- Jeton d'accès (15 min) **en mémoire** ; jeton de rafraîchissement (30 jours, lié à l'appareil, à rotation) dans `expo-secure-store`.
- `src/api/client.ts` : en-têtes `X-App-Version`, `X-Installation-Id`, `Authorization` ; sur **401** (hors routes d'authentification) un renouvellement
  **à vol unique** (`session.ts`) puis une seule relance de la requête ; refus du serveur → événement `signed_out` ; panne réseau → la session est conservée.
- **426** → écran de mise à jour obligatoire ; **503 `maintenance`** → écran de maintenance (`features/system/AppGate`). `GET /v1/app-config` reste joignable dans ces deux cas
  et donne version minimale, avis, drapeaux et limites.
- Parcours à code (inscription, mot de passe oublié) : trois étapes génériques (`TelephoneStep`, `CodeStep`, étape finale) ; l'état (numéro, jeton) vit en mémoire dans `AuthFlowProvider`.

## Données

TanStack Query. Clés dans `src/api/keys.ts` (une seule source : le temps réel et les mutations invalident au même endroit). Pagination par curseur
(`useInfiniteQuery`). Seules les lectures **publiques** (`fil`, `fiche`, `districts`, `app-config`) sont persistées sur disque ; jamais les messages ni les données personnelles.
Le gestionnaire de connexion de TanStack suit NetInfo : les requêtes se suspendent hors ligne et reprennent au retour du réseau.

## Messagerie

- **Envoi par HTTP, réception par WebSocket.** `POST /v1/conversations/{id}/messages` est idempotent sur `client_msg_id`.
- **File d'envoi** (`storage/outbox.ts`) : chaque message reçoit son `client_msg_id` **à la création** ; affichage immédiat « en attente » ; reprise automatique au retour du réseau ;
  refus définitif (ex. `contact_detected`) → « échec » avec « Renvoyer » (même identifiant : jamais de doublon). Vidée à la déconnexion.
- **Historique** : dernière page au chargement, plus anciens à la demande (`before_seq`), rattrapage après reconnexion (`after_seq`) ; fusion sans doublon dans `lib/messages.ts`.
- **Lecture** : `POST …/read` dès que le dernier message est à l'écran ; « lu » affiché d'après la position de lecture de l'autre (`other_read_seq`).

## Temps réel (`src/realtime`)

`ClientTempsReel` : ticket à usage unique (`POST /v1/ws-ticket`, 30 s) par connexion ; reconnexion 1 s → 30 s avec aléa ; `ping` toutes les 25 s, connexion jugée morte sans `pong` en 10 s ;
4403 (compte suspendu) → arrêt définitif ; 4429 → attente d'au moins une minute. `conversation.focus` annonce la conversation à l'écran (supprime le push pour cet appareil) et est renvoyé après chaque reconnexion.
`RealtimeProvider` : actif seulement **connecté et au premier plan** (à l'arrière-plan la connexion est coupée, la présence s'efface côté serveur, les push reprennent) ; `realtime/cache.ts` applique les événements au cache.

## Notifications push

`features/notifications/push.ts` : canaux Android (messages, alertes, rappels), demande d'autorisation **au bon moment** (`activerPush`, pas au démarrage), enregistrement du jeton Expo
(`PUT /v1/devices/current/push-token`), gestionnaire de premier plan (pas de bannière pour la conversation déjà à l'écran). `routage.ts` (pur, testé) décide où mène un appui, y compris à froid.

## Envoi de médias (gérant)

`features/pro/envoi.ts` : `react-native-compressor` pour la vidéo, puis protocole **tus** (`tus-js-client`) vers l'`upload_url` créée par `POST …/media` ; morceaux de 1 Mo (le serveur accepte 2 Mo),
reprise par `HEAD`, un renouvellement de jeton si 401 en cours d'envoi. `brouillon.tsx` : le serveur exige tous les champs dès la création de l'annonce, donc les étapes 1 à 3 de l'assistant
s'accumulent **sur l'appareil** (persisté) et l'annonce est créée côté serveur à la fin de l'étape « équipements ».

## Design

`src/ui/theme/tokens.ts` reprend les jetons du site (`serveur/web/static/css/tokens.css`) : une seule marque. Clair/sombre suivent le système. Cible tactile 48 dp minimum, tailles de police du
système respectées, états de chargement par squelettes, bandeau « hors connexion » sur chaque écran (`Screen`), libellés annoncés aux lecteurs d'écran.

## Décisions à valider

| Décision | Pourquoi | Si vous voulez autre chose |
|---|---|---|
| Expo (client de développement) plutôt que React Native nu | Exigé par le cahier des charges ; builds via EAS | — |
| Identifiant Android `bj.logeo.app` | Valeur par défaut raisonnable | À fixer avant la première publication (irréversible) |
| Visiteur sans compte : fil, recherche, fiches ouverts | Le fil de l'API est public ; réduit la friction | Mettre `AuthRequired` au niveau de `(locataire)/_layout` |
| `openapi-fetch` + `openapi-typescript` | Client typé de bout en bout, sans code généré à maintenir | — |
| Rendu de la description : `description_html` du serveur (déjà assaini) via `react-native-render-html` | Même rendu que le site | Rendre `description_md` côté application |
| Vidéo : MP4 progressif (`expo-video`) | C'est ce que sert le serveur aujourd'hui | HLS multi-qualité plus tard |
| Cache disque limité aux lectures publiques | Aucune donnée personnelle en clair sur le disque | — |
