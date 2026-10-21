# Plan de conception et refonte de l'application mobile Immo+

Ce document décrit la stratégie d'implémentation et de refonte visuelle de l'application mobile React Native / Expo (`mobile/`), en stricte conformité avec le guide de style `docs/design/DESIGN.md`, les maquettes visuelles `docs/design/screens/` et l'architecture technique existante (`mobile/docs/architecture.md`).

---

## 1. Principes directeurs

1. **Source de vérité du design :** `docs/design/DESIGN.md` et les captures `docs/design/screens/`.
   - Palette : Bleu cobalt (`#1B44D6`), Nuit (`#0F1B3D`), Jaune solaire (`#FFB429`), fond clair (`#F5F6FA`).
   - Typographie : *Plus Jakarta Sans* (800 pour les titres, 700 pour les sous-titres, 500 pour le corps).
   - Iconographie : icônes Lucide uniquement (aucun emoji, aucun sticker décoratif).
   - Ergonomie : Cibles tactiles ≥ 48 dp (`CIBLE_MIN`), contraste WCAG AA, un seul CTA principal par écran.
2. **Source de vérité des données :** L'API Django `/v1` (`docs/api/openapi.json`), sans inventer de modèle ni de règle métier côté client.
3. **Architecture logicielle :** Expo Router (routes minces dans `src/app/`, logique métier et écrans dans `src/features/`, composants et thèmes dans `src/ui/`).
4. **Hors-ligne et résilience :** Cache local TanStack Query, file d'attente d'envoi idempotente (`outbox.ts`), reconnexion temps réel WebSocket automatique.

---

## 2. Découpage en phases

### Phase 1 : Système de Design Mobile & Composants de base
- [x] **Dépendances :** Installation locale (`npm install`) pour activer le linting, le typage TypeScript et les tests Jest.
- [x] **Jetons de design (`mobile/src/ui/theme/tokens.ts`) :**
  - Remplacement de l'ancienne palette verte par la charte officielle Immo+ (`--blue`, `--sun`, `--night`, `--bg`, etc.).
  - Configuration des rayons (cartes 20, champs 14, pilule 999) et des ombres douces.
- [x] **Typographie :** Chargement de la police Google Font *Plus Jakarta Sans* via `expo-font`.
- [x] **Composants d'interface (`mobile/src/ui/components/`) :**
  - `Button` : CTA primaire bleu ou jaune solaire, secondaire outline, désactivé, cibles ≥ 48 dp.
  - `Card` : surface blanche, bordure subtile, ombre douce 4px/16px.
  - `Chip` : pastille sélectionnable avec bordure et fond contrasté (fond bleu cobalt + texte blanc actif).
  - `TextField` : label majuscule 12px 800, contour arrondi, préfixe +229 séparé.
  - `ListingCard` : carte d'annonce conforme à `Mobile · Accueil@1x.png` (visuel haut, bouton play blanc, badge vert "✓ Vérifié", durée vidéo, prix cobalt à droite).
  - Intégration de wrappers d'icônes Lucide (`lucide-react-native`).

---

### Phase 2 : Authentification & Bienvenue (Locataire & Gérant)
- [x] **Écran de bienvenue / Onboarding (`Mobile · Bienvenue@1x.png`) :**
  - Bannière nuit avec logo Immo+, feuille blanche arrondie, promesse de valeur, pastilles claires, CTA bleu locataire, CTA crème gérant.
- [x] **Connexion (`Mobile · Connexion@1x.png`) :**
  - Identifiant (numéro de téléphone béninois `+229`), mot de passe, bouton cobalt, mention explicative gérant.
- [x] **Inscription Locataire multi-étapes (`Mobile · Inscription 1 2@1x.png` & `2 2@1x.png`) :**
  - Étape 1 : Logo, jauge 2 segments, prénom, numéro de téléphone, puces statut étudiant, case CGU, bouton "Recevoir le code".
  - Étape 2 : Jauge 2 segments bleus, 6 cases de code avec contour bleu cobalt actif, chrono MM:SS, encadré "Ensuite, ta première alerte", bouton "Créer mon compte", lien "Modifier mon numéro".
  - *Règle :* Inscription publique réservée aux locataires/étudiants. Les gérants sont créés par l'équipe, qui leur transmet leurs identifiants.
- [x] **Compte gérant (écran d'information) :**
  - Comment devenir gérant (contact équipe, pièces, entretien) et bouton de connexion pour un compte déjà créé.

---

### Phase 3 : Découverte & Recherche (Locataire & Visiteur)
- [x] **Accueil (`Mobile · Accueil@1x.png`) :**
  - En-tête avec logo officiel `Immo+.` et cloche de notifications en carte ronde.
  - Titre héroïque "Où veux-tu habiter ?", barre de recherche avec bouton bleu "Filtres".
  - Puces de recherche rapide défilantes et fil infini avec ListingCard fidèle.
- [x] **Fiche détaillée de chambre (`Mobile · Détail chambre@1x.png`) :**
  - Lecteur vidéo intégré avec badge durée, galerie photos, feuille blanche remontante (rayon 28), prix cobalt, caractéristiques complètes, modalité contacter le gérant.
- [x] **Filtres avancés (`Mobile · Filtres@1x.png`) :**
  - Feuille modale avec bouton "Réinitialiser" en lien bleu, labels majuscules, sélection par quartier, budget, type et équipements.
- [x] **Gestion des Alertes (`Mobile · Alertes@1x.png`) :**
  - Formulaire inline dans carte blanche, chips quartier/type bleu cobalt, liste "ALERTES ACTIVES" avec switch vert style toggle.

---

### Phase 4 : Messagerie, Notifications & Profil
- [x] **Messagerie & Conversations (`Mobile · Conversation@1x.png`) :**
  - Header avec badge vert "✓ Vérifié", carte résumé de l'annonce rattachée, bulles de discussion (inbound blanches, outbound cobalt), bandeau jaune de sécurité, champ pilule avec bouton rond bleu d'envoi.
- [x] **Centre de notifications (`Mobile · Notifications@1x.png`) :**
  - Titre avec pastille "N non lues", action "✓ Tout marquer comme lu", filtres chips (Toutes, Non lues, Alertes, Messages), cartes bleues pour non lues avec pastille et icône cobalt, cartes blanches pour lues.
- [x] **Profil Locataire & Paramètres (`Mobile · Profil et vérification@1x.png`) :**
  - Avatar cobalt avec initiales, badge vert vérifié, lignes de menu en cartes blanches avec icônes carrées arrondies bleues, bouton déconnexion rouge pâle.

---

### Phase 5 : Espace Gérant (Tableau de bord & Publication)
- [x] **Tableau de bord Gérant (`Mobile · Dashboard gérant@1x.png`) :**
  - Salutation personnalisée + avatar bleu, grille 2×2 métriques réelles (vues, contacts, chambres actives, louées), alerte jaune pour annonces sans vidéo, liste "Mes chambres" avec vignettes et statuts.
- [x] **Tunnel de publication en 4 étapes (`Mobile · Publier 1 4@1x.png` à `4 4@1x.png`) :**
  - Barre de progression partagée `EntetePublication` à 4 segments cobalt/gris.
  - Étape 1 : Infos de base (titre, type chips, loyer, caution, disponibilité).
  - Étape 2 : Localisation (quartier chips, repère visible, adresse confidentielle).
  - Étape 3 : Médias (zone vidéo pointillée avec play, grille photos avec badges couverture).
  - Étape 4 : Description, équipements chips et aperçu final avec bouton jaune "Publier la chambre".
- [x] **Gestion des annonces & profil gérant (`Mobile · Compte gérant@1x.png`, `Abonnement@1x.png`, `Paiement@1x.png`) :**
  - Écran `CompteGerantScreen` : explications anti-arnaque, 4 étapes numérotées, boutons WhatsApp et Appel direct.
  - Écrans `AbonnementScreen` et `PaiementMobileMoneyScreen` : **retirés le 2026-10-17** (paiement débranché pour la
    V1, tout est gratuit). Récupérables depuis le commit `10f7333` ; à rebrancher sur l'API `billing`
    (`docs/plan-actions-v2.md` §7 bis) le jour du lancement payant.

---

### Phase 6 : Finitions, Tests & Recette globale
- [x] Contrôle de non-régression avec `npm test` : 7/7 suites Jest réussies, 92/92 tests au vert.
- [ ] Validation des flux Maestro (`mobile/maestro/`).
- [ ] Diagnostic de performance et gestion de la mémoire sur les médias vidéo.
