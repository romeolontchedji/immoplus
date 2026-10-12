# Logeo — Guide de style (source de vérité UI)

> Plateforme de logement étudiant à Parakou (Bénin) : chambres présentées en vidéo, gérants vérifiés, alertes.
> **Tout agent (Claude Code, Cursor, Copilot…) doit lire ce fichier avant de créer ou modifier une interface**, web (Django templates) ou mobile (React Native).
> Les maquettes de référence sont dans `docs/design/screens/` (images) et `docs/design/screens-source/` (HTML de référence). En cas de conflit, ce fichier prime sur les maquettes.

## 0. Règles absolues

1. **Aucun emoji, aucun sticker, aucun pictogramme texte** (pas de 🔔 ✓ ▶ ★ ♡ etc. dans l'UI). On utilise uniquement des **icônes vectorielles Lucide** (section 4).
2. **Le logo est conservé tel quel** (section 2). Ne jamais le redessiner, le déformer ni changer ses couleurs.
3. **Une seule famille de police : Plus Jakarta Sans** (500, 700, 800). Pas d'Inter, Roboto ni Arial.
4. **Tutoiement** et français simple dans tous les textes. Prix au format `18 000 F` (espace insécable, `/mois` à part).
5. **Aucun chiffre inventé** (pas de faux « 500 étudiants »). Les valeurs des maquettes sont des exemples.
6. **Aucune couleur hors palette** (section 3). Pas de dégradés décoratifs, sauf le voile sombre sur les illustrations de bannière.
7. **Cibles tactiles ≥ 44 px**, texte courant ≥ 14 px, contraste ≥ 4.5:1.
8. **Rôles** : l'inscription publique est **réservée aux locataires**. Les comptes **gérant** sont créés par l'admin après vérification (jamais d'inscription gérant dans l'UI).

## 1. Marque et ton

- Accroche : « Ta chambre à Parakou, vue en vidéo. »
- Promesses : gérants vérifiés, visite vidéo, alertes dès qu'une chambre se libère, zéro arnaque.
- Ton : chaleureux, direct, rassurant. Verbes d'action courts sur les boutons.
- Boutons types : « Voir les chambres », « Créer une alerte », « Contacter le gérant », « Me prévenir », « Publier la chambre », « Recevoir le code ».
- Rappel anti-arnaque sur conversation et détail : « Ne paie jamais avant d'avoir visité. »

## 2. Logo

Fichier : `docs/design/assets/logo.svg` (icône 48×48).
Construction : carré arrondi bleu `#1B44D6` (rayon 14/48), épingle de localisation blanche contenant une maison bleue, point jaune `#FFB429` en haut à droite.
Wordmark : texte « Logeo » en Plus Jakarta Sans 800, espacement −0,03em, suivi d'un **point jaune** : `Logeo.`

- Hauteur minimale de l'icône : 24 px. Marge autour : au moins la moitié de la hauteur de l'icône.
- Fond bleu `#1B44D6` ou nuit `#0F1B3D` : wordmark blanc, point jaune conservé.
- Barre d'en-tête mobile : icône 28 px + wordmark 19 px. Navbar web : icône 36 px + wordmark 24 px. Pied de page : wordmark 22 px.
- Icône d'application : le carré bleu seul, sans wordmark.

## 3. Design tokens

### Couleurs
| Token | Hex | Usage |
|---|---|---|
| `--blue` | `#1B44D6` | Primaire : CTA, liens, états actifs, prix |
| `--blue-soft` | `#EAF0FF` | Fonds d'icônes, notification non lue, pastille légère |
| `--sun` | `#FFB429` | Accent : CTA principal sur fond sombre/bannière, petits badges de compteur |
| `--night` | `#0F1B3D` | Texte principal, fonds sombres (admin, pied de page) |
| `--text-muted` | `#4A5373` | Texte secondaire |
| `--bg` | `#F5F6FA` | Fond d'écran |
| `--surface` | `#FFFFFF` | Cartes, champs |
| `--border` | `#D5DAEA` | Contours de champs et chips |
| `--divider` | `#EDEFF6` | Séparateurs |
| `--success` / `--success-bg` | `#12805C` / `#DDF3EA` | Vérifié, actif, validé (texte sur fond clair : `#0C6B4A`) |
| `--warning` / `--warning-bg` | `#8A5300` / `#FFF0D2` | Attention, astuce, en attente |
| `--danger` / `--danger-bg` | `#A32218` / `#FBE1DE` | Erreur, signalement, suppression |

Règle d'or : **jaune `--sun` = action principale sur fond sombre ou bannière ; bleu `--blue` = action principale sur fond clair.** Un seul CTA principal par écran.

### Typographie (Plus Jakarta Sans)
| Rôle | Taille / graisse |
|---|---|
| Titre hero web | 60 / 800, interligne 1.05, −0.035em |
| Titre de page web | 30–40 / 800, −0.03em |
| Titre d'écran mobile | 26–28 / 800 |
| Titre de carte | 17–18 / 700 |
| Corps | 15–16 / 500 |
| Secondaire | 13–14 / 500, `--text-muted` |
| Label de champ | 12 / 800, MAJUSCULES, +0.05em |

### Espacement, rayons, ombres
- Échelle 4 : 4, 8, 12, 16, 20, 24, 32, 40, 56. Marges d'écran mobile : 20–24. Conteneur web : max 1160 px, marges 24.
- Rayons : champs et boutons 14–16, cartes 20, grandes cartes 24, feuilles modales 28–32 (haut seulement), pastilles 99 (pilule).
- Ombre carte : `0 4px 16px rgba(15,27,61,.06)`. Ombre menu/popover : `0 12px 40px rgba(15,27,61,.18)`. Pas d'autres ombres.

## 4. Icônes (obligatoires, pas de stickers)

Bibliothèque unique : **Lucide** (trait 2 px, coins arrondis). Tailles : 20 (inline), 24 (navigation, boutons), 28–32 (illustrations d'état vide). Couleur : `currentColor`.
- Web Django : SVG inline via un partial `{% include "partials/icon.html" with name="bell" %}` ou un sprite SVG.
- React Native : `lucide-react-native` + `react-native-svg`.

Les maquettes utilisent des glyphes texte **comme espaces réservés** : remplace-les par ces icônes.

| Glyphe dans la maquette | Icône Lucide | Usage |
|---|---|---|
| ▶ | `play` | Lecture vidéo |
| ⌂ | `house` | Chambres / onglet accueil |
| ◔ | `bell` | Alertes, notifications |
| ✉ | `message-circle` | Messages |
| ☺ | `user` | Profil |
| ✓ | `check` / `badge-check` | Vérifié, coché, lu |
| ⌖ | `map-pin` | Quartier, localisation |
| ← | `arrow-left` | Retour |
| ♡ | `heart` | Favori |
| ➤ | `send` | Envoyer un message |
| ⌕ | `search` | Recherche |
| ▣ | `image` | Photo |
| ▦ | `layout-grid` | Mes chambres |
| ▾ | `chevron-down` | Menu déroulant |
| › | `chevron-right` | Ligne cliquable |
| + | `plus` | Ajouter / créer |
| ✕ | `x` | Retirer un filtre, fermer |
| ↶ | `undo-2` | Annuler (éditeur) |
| **B** / *I* / U | `bold` / `italic` / `underline` | Barre de mise en forme |
| •≡ / 1. | `list` / `list-ordered` | Listes |
| ? | `circle-help` | Aide |
| déconnexion | `log-out` | Se déconnecter |
| filtres | `sliders-horizontal` | Ouvrir les filtres |
| vidéo (ajout) | `video` | Ajouter une visite vidéo |
| paiement | `wallet` | Abonnement, Mobile Money |
| sécurité | `shield-check` | Compte vérifié |

Les logos d'opérateurs (MTN, Moov, Celtiis) sont des **images officielles**, jamais des icônes ou des pastilles de texte.

## 5. Composants

**Boutons** (hauteur 56 mobile, 46–52 web, rayon 14–16, texte 15–16/800) : *primaire* (fond `--blue`, texte blanc), *accent* (fond `--sun`, texte `--night`), *secondaire* (fond `--blue-soft`, texte `--blue`), *contour* (bordure `--border`), *danger* (fond `--danger-bg`, texte `--danger`). Pleine largeur sur mobile quand c'est l'action de l'écran. Barre d'action fixe en bas sur mobile (fond blanc, séparateur haut).
**Champs** : hauteur 52–54, bordure 1.5 `--border`, rayon 14, label MAJUSCULES au-dessus. Numéro de téléphone = préfixe `+229` + champ. Aucun mot de passe : connexion et inscription par **code SMS à 4 chiffres** (cases 58–60 × 64–68, case active bordée `--blue`).
**Chips / pastilles** (filtres, types) : pilule, 13–14/700. Inactive : blanc + bordure `--border`. Active : fond `--blue`, texte blanc. Filtre actif retirable : texte + icône `x`.
**Badge « Vérifié »** : pilule `--success` (texte blanc, 11–13/700) avec icône `badge-check`. Toujours visible sur carte, détail, conversation et profil du gérant.
**Carte chambre** : vignette vidéo (ratio ~2:1) avec bouton `play` blanc rond centré, badge Vérifié en haut à gauche, durée en bas à droite ; dessous titre (type · quartier), distance de l'UP, prix en `--blue` 800.
**Interrupteur** : 50×30, actif `--success`, inactif `#C5CAD9`.
**Statuts** (tableaux/listes) : pilule colorée : Active (success), Sans vidéo / En attente (warning), Louée (gris `#EDEFF6`), Suspendu / Signalé (danger).
**Notifications** : *non lue* = fond `--blue-soft`, icône pleine bleue, titre en 700–800, point bleu, texte « Non lue » en bleu ; *lue* = fond blanc, opacité .85, icône grise, titre en 500, « Lue » avec icône `check`. En-tête : compteur « n non lues », action « Tout marquer comme lu », filtres Toutes / Non lues / Alertes / Messages.
**Éditeur de description** : barre d'outils (gras, italique, souligné, liste à puces, liste numérotée, annuler) au-dessus de la zone de texte. Stockage en HTML nettoyé (balises b, i, u, ul, ol, li, br uniquement).
**FAQ** : accordéon (`<details>`/`<summary>` côté web), fond blanc, rayon 16.
**Tableaux** (dashboards) : lignes séparées par `--divider`, en-têtes 12/800 MAJUSCULES `--text-muted`.

### Navigation
- **Web, visiteur** : logo · Chambres · Comment ça marche · FAQ · Se connecter · Inscris-toi. **Pas d'« Espace gérant » dans la navbar.**
- **Web, locataire connecté** : logo · recherche intégrée · Chambres · Mes alertes · Messages (compteur) · cloche (compteur) · avatar + menu (Chambres, Mes alertes, Mes favoris, Messages, Notifications, Mon profil, Se déconnecter).
- **Web, gérant connecté** : barre latérale claire : Mes chambres, Statistiques, Messages, Notifications, Profil. **Admin** : barre latérale `--night` : Vue d'ensemble, Gérants, Modération, Journal.
- **Pied de page web** : 4 colonnes (marque, raccourcis, quartiers, contact), fond `--night`.
- **Mobile** : barre d'en-tête blanche de 52 px (logo à gauche, cloche à droite) sur tous les écrans sauf accueil, connexion, bienvenue, détail et filtres (plein écran ou feuille). Barre d'onglets du bas (84 px) : Chambres, Alertes, Messages, Profil ; onglet actif en `--blue`. Gérant : Mes chambres, Messages, Notifs, Profil + bouton flottant « Publier ».

## 6. Parcours et écrans (inventaire)

| Écran | Maquette | Notes |
|---|---|---|
| Logo | `Main` | Variantes fond clair / bleu / icône / slogan |
| Accueil web | `Web` | Bannière illustrée, onglets de recherche (Toutes / Entrée-coucher / Chambre-salon / Studio), « Comment ça marche » en 2 colonnes (Locataire / Gérant), FAQ, pied de page |
| Chambres + filtres (web) | `Web-Chambres` | Filtres : quartier, budget, type, distance UP, équipements, caution, disponibilité, gérants vérifiés, avec vidéo ; liste/carte, tri, filtres actifs |
| Détail chambre (web) | `Web-Detail-Chambre` | Vidéo, miniatures, infos, carte gérant fixe |
| Navbar web | `Web-Navbar-Connecte` | Visiteur, connecté, menu, cloche |
| Connexion / Inscription | `Web-Connexion`, `Web-Inscription`, `Mobile-Connexion`, `Mobile-Inscription-1/2` | Code SMS, inscription locataire uniquement |
| Dashboard gérant | `Web-Dashboard-Gerant`, `Mobile-Dashboard-Gerant` | Stats, encart d'incitation vidéo, tableau des chambres |
| Publier une chambre | `Web-Publier` (1 page), `Mobile-Publier-1..4` | Mobile : Infos → Vidéo → Description → Récapitulatif |
| Admin | `Admin-Overview`, `Admin-Gerants`, `Admin-Moderation`, `Admin-Journal` | L'admin valide les pièces et crée les comptes gérant |
| Mobile locataire | `Mobile-Onboarding`, `Mobile-Home`, `Mobile-Filtres`, `Mobile-Detail`, `Mobile-Alertes`, `Mobile-Notifications`, `Mobile-Conversation`, `Mobile-Profil` | |
| Mobile gérant | `Mobile-Compte-Gerant`, `Mobile-Abonnement`, `Mobile-Paiement` | Paiement : MTN MoMo, Moov Money, Celtiis Cash |

Parcours gérant : 1) contacte l'équipe Logeo (WhatsApp/appel) 2) l'admin vérifie pièces + entretien et crée le compte 3) le gérant publie (vidéo + photos). Parcours locataire : 1) filtre 2) visite en vidéo 3) contacte le gérant.

## 7. Implémentation Django Templates (web)

- Pas de framework JS. HTML sémantique + **un fichier CSS** `static/css/logeo.css` basé sur des variables CSS. JS minimal (menus, accordéon, aperçu du média). HTMX accepté pour filtres et notifications.
- Structure : `templates/base.html` (head, polices, navbar, messages, footer), `partials/navbar.html` (3 variantes selon `request.user` et rôle), `partials/footer.html`, `partials/icon.html`, `partials/room_card.html`, `partials/badge_verified.html`, `partials/notification_item.html`. Un template par écran : `home.html`, `rooms/list.html`, `rooms/detail.html`, `accounts/login.html`, `accounts/signup.html`, `manager/dashboard.html`, `manager/room_form.html`, `admin_panel/*.html`.
- Les filtres de la page Chambres sont des paramètres GET : `?quartier=&budget=&type=&distance=&equipements=&caution=&dispo=&verifies=1&video=1&tri=`.
- Variables à reprendre telles quelles :

```css
:root{
  --blue:#1B44D6; --blue-soft:#EAF0FF; --sun:#FFB429; --night:#0F1B3D;
  --text-muted:#4A5373; --bg:#F5F6FA; --surface:#fff; --border:#D5DAEA; --divider:#EDEFF6;
  --success:#12805C; --success-bg:#DDF3EA; --warning:#8A5300; --warning-bg:#FFF0D2;
  --danger:#A32218; --danger-bg:#FBE1DE;
  --r-field:14px; --r-card:20px; --r-pill:99px;
  --shadow-card:0 4px 16px rgba(15,27,61,.06); --shadow-pop:0 12px 40px rgba(15,27,61,.18);
  font-family:"Plus Jakarta Sans",system-ui,sans-serif; color:var(--night);
}
```
- Responsive : les pages web doivent rester utilisables sur téléphone (la navbar passe en menu, la grille de cartes en 1 colonne, les tableaux défilent horizontalement).
- Bannières : image d'arrière-plan en CSS (`background: linear-gradient(100deg, rgba(15,27,61,.88) 30%, rgba(15,27,61,.05)), url(...) center/cover`). Les illustrations fournies sont des **substituts** : les remplacer par des photos réelles du quartier étudiant en gardant le voile sombre.

## 8. Implémentation React Native (mobile)

- Expo ou RN CLI, `react-navigation` (onglets du bas + piles), `lucide-react-native`, `react-native-svg`, `expo-font` avec `@expo-google-fonts/plus-jakarta-sans` (500, 700, 800).
- Un seul fichier de thème `src/theme.ts` :

```ts
export const colors = {
  blue:'#1B44D6', blueSoft:'#EAF0FF', sun:'#FFB429', night:'#0F1B3D',
  textMuted:'#4A5373', bg:'#F5F6FA', surface:'#FFFFFF', border:'#D5DAEA', divider:'#EDEFF6',
  success:'#12805C', successBg:'#DDF3EA', warning:'#8A5300', warningBg:'#FFF0D2',
  danger:'#A32218', dangerBg:'#FBE1DE',
};
export const radius = { field:14, button:16, card:20, sheet:28, pill:99 };
export const space = [0,4,8,12,16,20,24,32,40,56];
export const font = { medium:'PlusJakartaSans_500Medium', bold:'PlusJakartaSans_700Bold', black:'PlusJakartaSans_800ExtraBold' };
```
- Composants à créer d'abord : `Logo`, `Button`, `Chip`, `Badge`, `Field`, `OtpInput`, `RoomCard`, `Toggle`, `Header`, `TabBar`, `NotificationItem`, `FilterSheet`, `RichTextToolbar`, `StepProgress`.
- Mobile = priorité au design : grandes cartes vidéo, feuilles de filtres plein écran, barre d'action fixe en bas, `SafeAreaView` partout, retour haptique léger sur les actions principales, états de chargement en squelettes (pas de spinner plein écran).
- Zones sûres : l'en-tête de 52 px s'ajoute à l'inset haut du téléphone.

## 9. Accessibilité et qualité

- Chaque bouton-icône a un libellé (`aria-label` / `accessibilityLabel`). Les icônes décoratives sont masquées aux lecteurs d'écran.
- Ne jamais signaler un état par la couleur seule : lu/non lu = couleur + graisse + point/icône + mention texte.
- Vidéos : sous-titres si disponibles, lecture non automatique avec le son.
- États à prévoir pour chaque liste : chargement, vide (icône Lucide + phrase + CTA), erreur réseau, hors ligne.

## 10. Checklist de l'agent avant de rendre une interface

1. Aucun emoji ni glyphe décoratif ; icônes Lucide uniquement.
2. Logo intact et bien dimensionné.
3. Couleurs, rayons, polices pris dans les tokens (aucune valeur en dur hors `theme.ts` / `logeo.css`).
4. Un seul CTA principal par écran ; bon jaune/bleu selon le fond.
5. Textes en français, tutoiement, prix `18 000 F`.
6. Pas d'inscription gérant ; pas d'« Espace gérant » dans la navbar publique.
7. Cibles ≥ 44 px, contrastes OK, libellés d'accessibilité.
8. Écran comparé à sa maquette dans `docs/design/screens/`.

## 11. Administration Django (`/admin/`)

Le site Django admin natif est habillé avec le thème Logeo. Il est **accessible depuis le panneau admin du site** (lien « Administration Django » en bas de la barre latérale, réservé aux comptes `is_staff`) et renvoie vers lui par « Retour au panneau admin ».

- Fichiers : `templates/admin/base_site.html` (marque, liens) et `static/admin/css/logeo_admin.css` (surcharge des variables natives `--primary`, `--secondary`, `--accent`, `--link-fg`, `--button-bg`, etc.). **Ne jamais copier ni modifier les templates natifs de Django** : seulement surcharger les variables et quelques sélecteurs.
- Habillage : en-tête `--night` avec logo + « Administration », fil d'Ariane blanc, modules en cartes arrondies (rayon 18) à en-tête `--night`, filtres en carte à droite, tableaux à en-têtes MAJUSCULES, barre d'actions en carte, bouton « Enregistrer » en `--sun`, « Supprimer » en `--danger`.
- Regroupement dans `admin.py` : sections Comptes (Gérants, Locataires, Utilisateurs, Groupes), Chambres (Chambres, Photos et vidéos, Alertes), Paiements (Abonnements gérants, Paiements Mobile Money), Modération (Signalements, Messages, Journal d'activité). Libellés en français via `verbose_name`.
- Mêmes règles qu'ailleurs : aucune icône emoji, tutoiement non requis (interface interne, vouvoiement neutre accepté), statuts en pastilles colorées via `list_display` + `format_html`.
- Action de liste « Valider les comptes sélectionnés » pour les gérants : l'admin valide les pièces puis active le droit de publier.

## 12. Données : la base et le cahier des charges priment

Le design fixe **l'apparence et la disposition**. Il ne fixe **pas** le schéma de données.
**Source de vérité des données = `models.py`, les migrations existantes et le cahier des charges du projet.** En cas de conflit entre une maquette et la base, la base gagne ; le design s'adapte.

Règles pour l'agent :
1. Avant chaque écran, lis les modèles concernés et le cahier des charges, puis établis un tableau « élément de la maquette → champ ou modèle existant ».
2. **N'invente aucun champ, modèle ni migration.** Si un élément de la maquette n'a pas de champ correspondant : masque-le proprement (la mise en page ne doit pas casser), ou propose-le dans `docs/design/ECARTS.md` et attends la validation avant toute migration.
3. Si un champ existe mais a un autre nom, un autre type ou d'autres choix possibles, utilise celui de la base et garde le style de la maquette (pastille, champ, filtre…).
4. Les libellés, valeurs et chiffres des maquettes sont des exemples. Ne les code jamais en dur.
5. Garde strictement le style : tokens, composants, icônes, logo, espacements. Seule la donnée s'adapte.

Éléments de la maquette **ajoutés pendant la refonte** et à confirmer avec le cahier des charges avant de les implémenter :
- Inscription locataire : champ « Nom », statut « Tu es » (Étudiant(e) UP / autre / Autre), conditions acceptées.
- Chambres : filtres par distance de l'UP, équipements, caution, disponibilité, « avec vidéo », « gérants vérifiés » ; favoris ; brouillon d'annonce.
- Gérant : « répond en moins d'1 h », statistiques, « Enregistrer le brouillon », date d'entretien, droit « peut publier », abonnement.
- Paiement : opérateur Celtiis Cash en plus de MTN MoMo et Moov Money.
- Notifications : types et filtres (Toutes / Non lues / Alertes / Messages), lu / non lu.
- Admin Django : regroupement en Comptes, Chambres, Paiements, Modération, et noms des modèles affichés.
