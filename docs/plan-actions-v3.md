# Plan d'actions v3 (retours du 19/10/2026)

Chaque ligne est cochée seulement après vérification visuelle (captures ordinateur 1366 px et téléphone 390 px)
ou test automatique. Web = site Django ; Mobile = application Expo.

**État au 20/10/2026 : tout est fait et vérifié.** Site : captures de chaque page (locataire, gérant, visiteur,
administration). Mobile : captures de la version web d'Expo (react-native-web installé temporairement, sans toucher
`package.json`) pour l'accueil, la recherche, les filtres, la fiche, le profil du gérant, la discussion, le tableau de
bord, la liste des annonces et les étapes de publication. Tests : serveur 1079, mobile 112.

Choix faits en route :
- « Confirmer la disponibilité » retiré : le masquage automatique « sans confirmation » est coupé par défaut
  (paramètre `STALE_HIDE_DAYS` = 0, bases existantes migrées de 14 à 0).
- Avis : publiés tout de suite, possibles seulement après une vraie discussion (le gérant a répondu) ; la modération
  peut les masquer.
- Quartiers voisins : centres à moins de 3 km, proposés quand le quartier demandé a moins de 3 résultats.
- Contact direct : la discussion s'ouvre vide ; elle n'apparaît chez le gérant qu'au premier message.
- Électricité : compteur personnel, décompteur, partagé. Eau : compteur personnel, décompteur, eau courante partagée,
  forage, puits. Cuisine : interne, commune, aucune.

## A. Recherche de chambres

| # | Demande | Web | Mobile |
|---|---|---|---|
| A1 | Filtres en listes déroulantes (type de chambre, quartier, budget…), plus de longues rangées de puces | [x] | [x] |
| A2 | Page Chambres : colonne de filtres qui défile seule, résultats toujours visibles | [x] | — |
| A3 | Filtres en temps réel : chaque choix met la liste à jour, sans bouton « Rechercher » | [x] | [x] |
| A4 | Quartiers voisins : si peu ou pas de résultats, proposer clairement les chambres des quartiers proches | [x] | [x] |
| A5 | La recherche par mots lit aussi les « Autres détails » des annonces | [x] | [x] |

## B. Détail d'une chambre

| # | Demande | Web | Mobile |
|---|---|---|---|
| B1 | Galerie : images de même taille, flèche « suivante » pour voir les autres | [x] | [x] |
| B2 | Quartier mis en avant en premier, favori en haut | [x] | [x] |
| B3 | Avis des locataires en haut (note moyenne, nombre) | [x] | [x] |
| B4 | Équipements : électricité, eau, cuisine, douche | [x] | [x] |
| B5 | Prix « à débattre » affiché | [x] | [x] |
| B6 | Un seul bouton « Contacter » qui ouvre directement la discussion (plus de message type) | [x] | [x] |

## C. Publication (gérant)

| # | Demande | Web | Mobile |
|---|---|---|---|
| C1 | Plus de grand champ à mise en forme (gras, italique…) : champs précis + « Autres détails » en texte simple | [x] | [x] |
| C2 | Électricité : compteur personnel, décompteur, partagé ; Eau : compteur personnel, décompteur, forage, puits ; Cuisine | [x] | [x] |
| C3 | Case « Prix à débattre » | [x] | [x] |
| C4 | Publication en étapes (stepper) sur téléphone | [x] | [x] |
| C5 | Brouillon clairement signalé comme brouillon | [x] | [x] |
| C6 | Supprimer une annonce ou un brouillon | [x] | [x] |

## D. Tableau de bord gérant

| # | Demande | Web | Mobile |
|---|---|---|---|
| D1 | Retirer « Confirmer la disponibilité » | [x] | [x] |
| D2 | Nombre de vues par chambre, total dans les indicateurs | [x] | [x] |

## E. Mise en page du site

| # | Demande |
|---|---|
| E1 | Locataire : ses informations quittent le tableau de bord pour l'onglet Profil (comme le gérant) | [x] |
| E2 | Barre latérale fixe sur toutes les pages sauf l'accueil ; en haut, seul l'avatar reste ; menus de l'accueil inchangés | [x] |
| E3 | Téléphone : plus de rangée d'onglets défilante en haut de page (le menu la remplace) | [x] |
| E4 | Pages de connexion : textes centrés, illustrations remplacées | [x] |
| E5 | Code SMS (site) : plus joli, envoi automatique au 6e chiffre, effacé et vibration en cas d'erreur | [x] |
| E6 | Changer de numéro : formulaire dans le profil, sans renvoyer vers les pages d'inscription | [x] |
| E7 | Recette visuelle de toutes les pages, corrections de responsivité | [x] |

## F. Profil public du gérant

| # | Demande | Web | Mobile |
|---|---|---|---|
| F1 | Page profil du gérant : informations (sans numéro), chambres publiées | [x] | [x] |
| F2 | Accès depuis l'en-tête de la discussion | [x] | [x] |

## G. Avis des locataires

| # | Demande | Web | Mobile |
|---|---|---|---|
| G1 | Laisser un avis (note 1 à 5 et commentaire) après une vraie discussion | [x] | [x] |
| G2 | Avis visibles sur la chambre et le profil du gérant | [x] | [x] |
| G3 | Administration : liste des avis, masquer un avis | [x] | — |

## H. Alertes et notifications

| # | Demande | Web | Mobile |
|---|---|---|---|
| H1 | Les alertes préviennent vraiment quand une chambre correspondante est publiée (vérifié de bout en bout) | [x] | [x] |
| H2 | La cloche reflète la réalité (compteur, lu / non lu) | [x] | [x] |
| H3 | Créer une alerte exige d'être connecté | [x] | [x] |
| H4 | Après un signalement : « Ton signalement a été pris en compte et sera traité » | [x] | [x] |

## I. Application mobile

| # | Demande |
|---|---|
| I1 | En-tête : les initiales à droite remplacées par « Créer une alerte » et « Publier une chambre » | [x] |

## J. Administration

| # | Demande |
|---|---|
| J1 | Une note sous chaque paramètre (Pilotage › Paramètres) qui explique le champ | [x] |
| J2 | « Connexions échouées » et « Tentatives de connexion » remplies réellement | [x] |
| J3 | Ajouter, modifier, désactiver des quartiers | [x] |
| J4 | Voir et masquer les avis | [x] |
