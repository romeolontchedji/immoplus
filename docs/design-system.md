# Système de design

## Principes

Chaleureux, sobre, lisible sur un téléphone d'entrée de gamme. Mobile d'abord (360 px), puis 640, 768, 1024 et 1280 px.
Cible tactile : 44 px au minimum (48 px pour l'action principale). Mouvement réduit respecté (`prefers-reduced-motion`).

## Jetons

Tout est défini dans `serveur/web/static/css/tokens.css` :

- **Marque** bleu cobalt (`--marque-50` à `-900`), **accent** terre cuite / ambre (`--accent-…`), **neutres** ardoise / slate (`--sable-0` à `-950`).
- **Sémantiques** : `--succes` (vert émeraude vérifié), `--avertissement`, `--danger`, `--information`, avec fond et texte associés.
- **Rôles** (changent avec le thème) : `--bg`, `--surface`, `--text`, `--text-muted`, `--primary`, `--focus`, `--link`, etc.
- Typographie (`--fs-12` à `--fs-60`), espacement sur 4 px (`--sp-1` à `--sp-20`), rayons, ombres, durées (150, 200, 250 ms).

**Règle** : une couleur, une taille ou une ombre ne s'écrit jamais en dur hors de `tokens.css`
(`outils/tests/test_contraste_css.py` le vérifie pour les couleurs).

## Thèmes

Clair par défaut, sombre selon la préférence du système, ou forcé par `data-theme="light|dark"` sur `<html>`.
Les deux définitions sombres doivent rester identiques ; `outils/contraste.py` le contrôle, ainsi que les contrastes WCAG AA
(4,5:1 pour le texte, 3:1 pour le focus et les éléments d'interface).

Écart documenté : l'anneau de focus utilise `marque-500` en clair (voir `docs/adr/0003-decisions-phase-0.md`).

## CSS

Couches `tokens, base, layout, components, utilities`. Composants dans `serveur/web/static/css/components/` (BEM léger :
`.bouton`, `.bouton--primaire`, `.carte__titre`). Après modification : `make css`.

## Ajouter un composant

1. Écris son CSS dans `components/<nom>.css`, uniquement avec des jetons.
2. Présente-le dans `serveur/web/templates/web/styleguide.html` (tous ses états : survol, focus, désactivé, erreur).
3. Vérifie `/styleguide` en clair et en sombre, au clavier et à 360 px de large.
4. `make verifier`.

## État

Phase 0 : jetons, base, mise en page, boutons, champs, badges et puces, alertes, cartes. Le sprite d'icônes, les
illustrations et les autres composants arrivent en phase 4.
