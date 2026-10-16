# Avancement de l'application mobile Logeo

Ce document suit l'état d'implémentation et de conformité de l'application mobile (`mobile/`).

---

## Synthèse globale

* **Architecture technique :** En place et documentée (`mobile/docs/architecture.md`).
* **Intégration API `/v1` :** Types OpenAPI générés et client configuré.
* **Navigation :** 46 routes déclarées sous Expo Router.
* **Design system & Maquettes :** À aligner sur `docs/design/DESIGN.md` et `docs/design/screens/`.

---

## État d'avancement par phase

### Phase 1 : Système de Design Mobile & Composants de base
* [ ] Dépendances `npm install` installées
* [ ] Tokens de style (`tokens.ts`) alignés sur DESIGN.md (Bleu #1B44D6, Nuit #0F1B3D, Jaune #FFB429)
* [ ] Police *Plus Jakarta Sans* configurée
* [ ] Icônes Lucide intégrées (aucun emoji)
* [ ] Composants de base rafraîchis (`Button`, `Card`, `Chip`, `TextField`, `ListingCard`, `Screen`)

### Phase 2 : Authentification & Bienvenue
* [ ] Écran de bienvenue (`Mobile · Bienvenue@1x.png`)
* [ ] Écran de connexion (`Mobile · Connexion@1x.png`)
* [ ] Tunnel d'inscription locataire en 2 étapes (`Mobile · Inscription 1 2` & `2 2@1x.png`)
* [ ] Réinitialisation de mot de passe

### Phase 3 : Découverte & Recherche
* [ ] Accueil et fil des annonces (`Mobile · Accueil@1x.png`)
* [ ] Fiche détaillée de chambre avec vidéo et galerie (`Mobile · Détail chambre@1x.png`)
* [ ] Modale de filtres avancés (`Mobile · Filtres@1x.png`)
* [ ] Écran de gestion et création d'alertes (`Mobile · Alertes@1x.png`)
* [ ] Liste des favoris

### Phase 4 : Messagerie, Notifications & Profil
* [ ] Liste des conversations
* [ ] Fil de discussion sécurisé (`Mobile · Conversation@1x.png`)
* [ ] Centre de notifications (`Mobile · Notifications@1x.png`)
* [ ] Profil locataire et paramètres du compte (`Mobile · Profil et vérification@1x.png`)

### Phase 5 : Espace Gérant
* [ ] Tableau de bord gérant avec indicateurs réels (`Mobile · Dashboard gérant@1x.png`)
* [ ] Gestion de la liste des annonces du gérant
* [ ] Tunnel de création / publication en 4 étapes (`Mobile · Publier 1 4` à `4 4@1x.png`)
* [ ] Écran compte gérant (`Mobile · Compte gérant@1x.png`)

### Phase 6 : Validation & Tests
* [ ] Compilation TypeScript (`npm run typecheck`)
* [ ] Linter (`npm run lint`)
* [ ] Tests unitaires Jest (`npm test`)
* [ ] Tests d'intégration et scénarios Maestro (`mobile/maestro/`)

---

## Journal des sessions et décisions

* **2026-10-12 :**
  * Établissement de l'état des lieux du mobile et création de la feuille de route `mobile/docs/plan-action-mobile.md`.
  * Création de ce fichier de suivi d'avancement `mobile/docs/avancement-mobile.md`.
  * Décision de prioriser le passage de la palette de couleurs vers le bleu cobalt `#1B44D6`, le jaune solaire `#FFB429` et la police *Plus Jakarta Sans*.
* **2026-10-15 — démarrage impossible sous Expo Go (notifications) :**
  * `features/notifications/push.ts` est importé par la disposition racine (`src/app/_layout.tsx`). Sous Expo Go Android,
    `Notifications.getExpoPushTokenAsync` lève « Android Push notifications … was removed from Expo Go … SDK 53 », ce qui
    faisait échouer le chargement de `_layout.tsx` (et, par ricochet, des routes qui importent `push.ts`).
  * Correctif : détection `isRunningInExpoGo()` (paquet `expo`). Sous Expo Go, le handler de premier plan n'est pas posé,
    `activerPush()` renvoie immédiatement `"indisponible"` et les effets de `usePushBootstrap` sont ignorés. En dev build / EAS,
    le comportement est inchangé.
  * Vérifié : `tsc` sans erreur sur `push.ts`, `eslint` propre, 92 tests Jest au vert, `expo export --platform android` OK.
  * **Reste (hors notifications)** : `react-native-compressor` (Nitro) ne fonctionne pas sous Expo Go et fait échouer l'étape
    médias ; tester l'envoi vidéo exige un dev build (`expo-dev-client` / EAS), comme prévu par `docs/a-verifier.md`.
