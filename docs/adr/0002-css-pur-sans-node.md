# ADR 0002 — CSS pur, sans Node

- Statut : accepté (phase 0)
- Date : 2026-10-06

## Contexte

Le site est rendu par le serveur. Les appareils visés sont des téléphones d'entrée de gamme sur réseau lent : peu de
JavaScript, un CSS léger, aucune chaîne de construction lourde à maintenir.

## Décision

- Le CSS est écrit à la main, en **couches** (`@layer tokens, base, layout, components, utilities`).
- `outils/construire_css.py` (bibliothèque standard) assemble, minifie et ajoute une empreinte au nom du fichier,
  puis écrit `manifest.json`. La balise `{% css_logeo %}` lit ce manifeste.
- **Toutes** les valeurs de couleur, taille, ombre et mouvement viennent de `tokens.css`. Un test refuse toute couleur
  écrite en dur ailleurs.
- `outils/contraste.py` vérifie les contrastes WCAG AA des jetons en thème clair et sombre.
- Aucun style ni script en ligne : la CSP n'autorise que `'self'` (plus le widget anti-robot pour les scripts et cadres).
- Le JavaScript (htmx, Alpine.js en build CSP, hls.js, tus-js-client) est fourni en fichiers figés (`make vendor`, phase 4).

## Conséquences

- Pas de Tailwind, pas de Sass, pas de `node_modules`.
- Le build CSS est déterministe (même entrée, même empreinte) et s'exécute dans l'image Docker.
- Les couleurs de l'administration (django-unfold) suivront les mêmes jetons en phase 1.
