# À vérifier et à corriger (application mobile)

## Ce qui a été vérifié
- `tsc --noEmit` (TypeScript strict), `eslint .` : sans erreur ni avertissement.
- `jest` : **92 tests** passent ; couverture de la logique mesurée 88 % (seuil 70 %).
- `expo export --platform android` : le bundle Hermes (4,5 Mo) se construit — **toutes les routes et tous les imports se résolvent**.
- `expo-doctor` : 19 contrôles sur 21 ; les 2 restants (schéma de configuration, annuaire React Native) exigent l'accès à `exp.host`, injoignable dans mon environnement : **à relancer chez vous**.
- Le client temps réel a été testé avec un faux WebSocket, et le côté serveur (uvicorn + client en ligne de commande) de bout en bout ; **jamais application et serveur ensemble**.

## Ce qui n'a jamais tourné
- **Aucun lancement sur émulateur ou téléphone.** Aucun rendu d'écran n'a été vu : mise en page, clavier, zones sûres, mode sombre, tailles de police.
- Les parcours Maestro (`maestro/*.yaml`) sont écrits, **jamais exécutés** ; les libellés ciblés peuvent demander des ajustements.
- Push : jamais testé (émulateur sans push, projet EAS et identifiants FCM absents).
- Envoi tus d'une vraie vidéo : à tester sur appareil (lecture du fichier par `fetch(uri).blob()`, reprise après coupure, jeton expiré en cours d'envoi).

## Dépend du serveur — modifications **non livrées** dans `immoplus-partie2.zip`
Le client généré (`src/api/genere/api.d.ts`) vient d'un schéma qui contient ces points ; ils existent dans mon travail serveur en cours mais **pas dans l'archive précédente** :
1. `GET /v1/app-config` (version minimale, maintenance, avis, drapeaux, limites) et le refus **426** sur `X-App-Version` trop ancienne. Sans eux, l'application fonctionne mais n'impose jamais la mise à jour (la lecture de la configuration échoue en silence).
2. Corps d'API en JSON uniquement.
3. **La bibliothèque `websockets` manque aux dépendances de production du serveur** : sans elle, uvicorn refuse les connexions WebSocket et la messagerie temps réel ne fonctionne pas.
À reporter dans le dépôt serveur avant tout essai complet.

## Trous du contrat d'API (rien à faire côté mobile, à décider côté serveur)
- Pas de **statistiques par annonce** : `AnnonceStatsScreen` reste un squelette.
- Création d'annonce : le serveur exige **tous** les champs obligatoires d'un coup ; l'assistant garde donc un brouillon local jusqu'à la fin de l'étape 3 (voir `docs/architecture.md`). Si vous voulez un brouillon serveur dès l'étape 1, il faut assouplir `POST /v1/pro/listings`.
- `GET /v1/me/preferences` n'a pas de schéma typé (réponse libre).
- Vidéo de la carte lue automatiquement en connexion rapide (cahier des charges) : non faite ; seul le réglage « économie de données » est prévu.

## Décisions et valeurs à confirmer
- Identifiant Android/iOS `bj.immoplus.app`, nom, icône et écran de démarrage : **ceux du modèle Expo** (`assets/` contient des images provisoires).
- Domaine `immoplus.example` (liens profonds, partage) : à remplacer ; il faut aussi servir `https://<domaine>/.well-known/assetlinks.json` côté serveur pour que les liens https ouvrent l'application.
- `eas.json` : adresses d'API de développement, préproduction et production fictives ; `EAS_PROJECT_ID` à renseigner (`eas init`).
- Versions : celles résolues par Expo SDK 57 (React 19.2.3, React Native 0.86.3, TypeScript 6.0). `openapi-typescript@7.9.1` est épinglé dans `outils/exporter_client_ts.sh` (exécuté par `npx`, pas une dépendance du projet) : version non revérifiée.
- Choix à valider (détail dans `docs/architecture.md`) : visiteurs sans compte autorisés, `react-native-render-html` pour la description, MP4 progressif, cache disque limité aux lectures publiques.

## Reste à faire
- Remplacer les **28 squelettes** (liste dans `docs/ecrans.md`, chacun décrit sa route, son API et ses états).
- Tests de composants sur les écrans, premiers parcours Maestro réels, passage accessibilité (lecteur d'écran, contrastes en mode sombre).
- Activer `typedRoutes` une fois les écrans stabilisés ; ajouter la gestion des liens profonds `https` après `assetlinks.json`.
