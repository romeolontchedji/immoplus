# ADR 0006 — Photos d'ambiance à licence libre

- Statut : **accepté**
- Date : 2026-10-17 (décision V9 du porteur, `docs/plan-actions-v2.md` §2 et §8)

## Contexte

Le CDC (§9) écarte toute photo : « ni photographe, ni illustrateur, ni banque d'images », le décor repose sur des
illustrations vectorielles et un motif de marque. Le porteur souhaite de vraies photos en arrière-plan, sur le site
et dans l'application, pour un rendu plus chaleureux.

## Décision

- **9 photos d'ambiance** à licence libre (Unsplash, Pexels, Pixabay), choisies et téléchargées par le porteur :
  bannière de l'accueil (3), présentation de l'application (4), écran de bienvenue (1), page gérant (1).
- **Hébergées par Immo+** : originaux dans `photos-brutes/` (non versionné), conversion en WebP par un script du
  dossier `outils/`, tailles 480/960/1600 px servies en fichiers statiques par le site, 960 px embarquée dans
  l'application. Aucun chargement depuis un site tiers : la règle « aucune image externe, aucun CDN » est conservée.
- **Jamais pour représenter une chambre.** Une annonce sans image garde l'affiche vectorielle de repli (CDC §9.3,
  point 2) : une photo de banque d'images ferait croire au locataire qu'il voit la vraie chambre, contraire à la
  promesse « vois ta chambre avant de te déplacer ».
- Licence, auteur et lien de chaque photo consignés dans `docs/design/credits-photos.md`. Pas de visage
  reconnaissable sans autorisation de la personne photographiée (« model release »).

## Conséquences

- CDC amendé (§9 et §9.3, point 8), avec l'accord du porteur.
- Poids : environ 9 × 3 variantes WebP sur le site (quelques centaines de Ko au total, chargement différé hors de
  la bannière) et 9 images dans l'application.
- Le motif de marque et les illustrations vectorielles restent la base du décor ; les photos s'y ajoutent.
