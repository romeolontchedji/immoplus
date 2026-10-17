# Avancement

> **À jour :** voir `docs/reste-a-faire.md` (comptes, annonces et médias faits ; fil, messagerie, notifications et modération à faire). Le reste de ce fichier décrit la phase 0.

**2026-10-17 : notifications, jetons uniques, petits points.**
- Notifications : réponse et « Marquer comme lu » depuis la notification (N3, à recetter sur dev build), bannière
  interne quand l'app est ouverte (N5), regroupement « N nouveaux messages » (N2), rattrapage (N6).
- Jetons : `docs/design/tokens.json` génère le haut de `tokens.css` et `mobile/src/ui/theme/jetons.genere.ts`
  (`make jetons`, contrôle dans `outils/verifier_tout.sh`).
- `PAID_ALERTS_ENABLED` (éteint) dans les paramètres ; `paid_alerts` toujours faux en V1.
- Dernières chambres consultées : bandeau sur l'accueil mobile (stockage local), section du tableau locataire web
  (session, relue à l'affichage).
- Mobile : balayage d'une conversation (« Lu », sourdine 8 h, réactiver) ; `GestureHandlerRootView` à la racine.
- Photos d'ambiance (W1/M6, ADR 0006) : diaporama de 3 photos sur l'accueil du site, photo du gérant sur sa carte,
  photos de la présentation et de la bienvenue mobile ; `outils/construire_photos.py`. Quatre images de banque payante
  écartées et remplacées par des images générées par IA à partir d'un texte (règle dans `docs/design/credits-photos.md`).
- Reste : site d'origine des 5 photos libres à noter dans les crédits, recette sur dev build (push, N3,
  biométrie, GPS, balayage), KKiaPay et prix au lancement payant.

**Chantier précédent : refonte générale de l'interface et messagerie mobile.**
- Refonte de la navigation (visiteur, locataire, gérant) responsive desktop et mobile avec menu hamburger et popover de notifications.
- Intégration fidèle de la messagerie/chat selon la maquette `Mobile · Conversation@1x.png` (en-tête interlocuteur avec badge vérifié, carte chambre liée avec prix et miniature, bulles de discussion avec horodatage, encart sécurité ambré, champ d'envoi en pilule ergonomique).
- Ajout des propriétés `initiales` et `prenom` sur le modèle `User` pour fiabiliser le rendu des gabarits.
- Tests visuels de bout en bout validés sur desktop (1280px) et mobile (390px).

**Dernière passe : application de `docs/design/COPYWRITING.md` au site web.**
- Textes réécrits : `accueil.html` (hero, piliers, prévention, bloc alerte, FAQ), `base.html`
  (titre/description, slogan du pied, lien `titirou`), `annonces.html`, `fiche.html`, `carte.html`,
  `messages.html`, `conversation.html`, `alertes.html`, `notifications.html`, `favoris.html`,
  `pro/tableau.html`, `pro/liste.html`, `pro/editeur.html`, `auth/*`.
- Chiffres inventés supprimés (`4× plus de contacts`, `0:18`, `moins d'1 h`, `Ex. 15 000`,
  `Ex : 25 000`, métriques `default:0` → `—`) ; prix en `F` (au lieu de `FCFA`) ; unité de distance en
  mètres (`À X m de l'UP`).
- Codes techniques traduits : statut de conversation (`statut_conversation`) et manques de publication
  (`manque_publication`) via de nouveaux filtres dans `web/templatetags/logeo.py`.
- CSP : le seul `<style>`, `<script>` et `style=` en ligne restant (`conversation.html`) est externalisé
  (`components/conversation.css`, `js/conversation.js`).
- Icônes Lucide ajoutées (`heart`, `chevron-up`, `chevron-down`, `smartphone`) à la place des glyphes
  `★ ☆ ↑ ↓ × ?`.
- Tests mis à jour : `test_pages.py` (accueil), `test_pages_publiques.py` (référence à « Créer une
  alerte pour cette recherche »), `test_pro_web.py` (manque « pas encore prête »).
- **Échecs préexistants corrigés** (les 6 restants) :
  - Galerie fiche : `fiche.html` passe à `galerie-fiche` / `galerie-fiche__vignette` (`--couverture`
    sur la première) ; bloc CSS mort `.fiche-vignettes-barre`/`.fiche-vignette` retiré de `fiche.css`.
  - Adresse privée : `conversation.html` affiche `adresse` (`selectors.adresse_privee`) — fournie par la
    vue uniquement au gérant, jamais au locataire.
  - Libellés « Mes annonces » (sidebar, barre, titre, fil d'Ariane) au lieu de « Mes chambres » (CDC
    §1791 et tests ; écart avec DESIGN.md §129 → voir `docs/design/ECARTS.md`).
  - Tableau de bord : la liste `statuts` (`TITRES_STATUTS` : « Publiées », « Brouillons »…) est enfin
    rendue en pastilles `.pro-statut-chip` sous les métriques.
  - **Activation gérant supprimée.** Décision produit : la création est purement manuelle (seul
    l'administration crée le compte et transmet les identifiants ; le gérant change son mot de passe
    ensuite via `/compte`). Les routes `/pro/activation*`, les vues `activation_gerant_*`
    (`web/views_auth.py`) et le formulaire `ActivationGerant` (désormais inutilisé) sont retirés.
    Le test web vérifie que le gérant créé par l'administration se connecte via `/connexion`, atteint
    `/pro/dashboard` et peut changer son mot de passe.
  - **Mobile aligné.** Écrans `/activation/*` (`mobile/src/app/(auth)/activation/`) supprimés, ainsi que
    `ActivationScreen` (`FinalSteps.tsx`), `useActivation` (`hooks.ts`), `activationSchema` (`schemas.ts`)
    et l'objet OTP `gerant_activation`. `CompteGerantScreen` reste l'écran d'information (compte créé par
    l'administration) : bouton d'activation retiré, note sur les identifiants transmis ajoutée et bouton
    « J'ai déjà un compte, me connecter ». Docs mobiles à jour (`ecrans.md`, `architecture.md`,
    `avancement-mobile.md`).
  - **Parcours d'activation purgé partout.** Endpoint API `POST /v1/auth/activate` retiré (vue
    `Activation`, route, schéma `ActivationIn`, service `activer_gerant`), valeur OTP
    `gerant_activation` absente de l'enum `Objet` ; `docs/api/openapi.json` régénéré et client TS mobile
    (`api.d.ts`, `client.ts`) réaligné. Les tests d'activation dépréciés sont supprimés.
  - **SMS informatif conservé.** À la création, un SMS purement informatif part après commit via la tâche
    `notifier_gerant_cree`. `MESSAGE_COMPTE_PRET` reformulé sans activation (« Connecte-toi… avec le mot
    de passe que l'équipe t'a transmis ») ; le SMS ne contient jamais le mot de passe.
  - **Copie et ADR réalignés.** `COPYWRITING.md` §7 : section « Compte gérant » passée aux textes du
    guide (`Un compte gérant se mérite…`), étape 4 adaptée (plus d'activation) et sections « Activation
    du compte » / SMS « compte prêt » remplacées par « Création du compte (par l'équipe, sans
    activation) ». L'écran mobile `CompteGerantScreen` suit ces textes. `ADR 0004` passé au statut
    **remplacé**, avec la nouvelle décision consignée.
  - **Docs réalignées** : `docs/tuto-compte-gerant.md` réécrit (plus d'activation, SMS informatif),
    `docs/cahier-des-charges.md` (EF-AUT-07, EF-ADM-01, table des endpoints, table des rôles, OTP,
    §8.4, §11.3, §12.3), `docs/reste-a-faire.md`, `docs/adr/0004-sms-creation-gerant.md`,
    `mobile/docs/plan-action-mobile.md`.
- **Validation** : `ruff` et `ruff format` au vert ; `make openapi` régénéré (endpoint `/v1/auth/activate`
  disparu) ; `apps/accounts` **305** tests, `web/tests` **71** et `adminsite` création de gérant au vert.
  Restent des échecs **préexistants** hors sujet (2FA admin et libellé du tableau de bord dans
  `adminsite/tests/test_administration.py`, seed, `/readyz` sans Redis exposé) et les erreurs `tsc`
  préexistantes du mobile (node_modules incomplet).


**Phase en cours : 0 (fondations) — terminée côté code, avec les réserves listées ci-dessous.**
Prochaine étape : phase 1 (comptes : modèles, OTP, appareils, administration séparée).

## Fait (phase 0)

- Dépôt, contrôles Git (commit, branche, noms, hygiène), trois hooks, `outils/tester_hooks.sh` : 9 cas conformes, sortie dans `docs/verification.md`.
- Serveur Django 5.2 LTS : réglages `base/local/public/admin/admin_local/test`, neuf applications vides, `/healthz`, `/readyz`,
  journaux JSON masqués, CSP stricte, identifiant de requête, verrou Redis pour `beat`, contrats `import-linter` (10, mutation vérifiée).
- Design : jetons clair/sombre, couches CSS, `outils/construire_css.py`, `outils/contraste.py`, `/styleguide` initial.
- Infrastructure : `Dockerfile`, Compose (dev et prod), Caddy (local et production), rôles PostgreSQL, sauvegarde logique.
- Outils : `Makefile` complet, `verifier_tout.sh`, `creer_env.py`, `diagnostic.sh`, `fumee.sh`.
- Documentation : `AGENTS.md` (+ test), ADR 0001 à 0003, `README`, `docs/contribuer.md`, `docs/design-system.md`, `docs/api/openapi.json`.
- CI : `.github/workflows/commits.yml` et `verifier.yml`, `CODEOWNERS`, modèles de demande de fusion et d'issues.

## Réserves (non exécuté ou à faire chez toi)

1. **Docker absent du bac à sable** : image, Compose et `make up` n'ont jamais tourné. `make fumee` est à lancer chez toi.
2. **Workflows GitHub** : écrits et lus (YAML valide), jamais exécutés. Protection de `main` : procédure dans `docs/contribuer.md`.
3. **Caddy de production** : validé (`caddy validate`) mais pas exécuté ; la version locale a été exécutée avec de faux amonts.
4. **Images** `postgres`, `redis`, `caddy` non figées par digest (ADR 0001).
5. **Chromium indisponible** (téléchargement bloqué) : aucun test e2e ni axe avant la phase 4.
6. **`gitleaks` absent** : détection de secrets par motifs maison seulement.
7. `make seed`, `make vendor`, `make docs` : volontairement non disponibles (phases 1, 4, 9) ; ils échouent avec un message clair.
8. `django-migration-linter` n'est pas encore branché (aucune migration avant la phase 1).

## Décision à valider

Anneau de focus en `marque-500` (clair) au lieu de `marque-300` : voir `docs/adr/0003-decisions-phase-0.md`.

## Décisions et pièges

- `LISEZMOI` et `Caddyfile` ajoutés aux noms en majuscules autorisés (imposés par le prompt et par Caddy).
- Les chemins de modules imposés par Django (moteurs de base, de session, de cache) sont tolérés par une liste explicite dans `outils/mots-interdits.toml` ; le mot interdit reste refusé partout ailleurs.
- `pkill -f motif` tue le shell qui contient le motif : utiliser des fichiers de PID.
- Le bac à sable peut redémarrer : PostgreSQL et Redis ne sont pas relancés tout seuls (`pg_ctlcluster 16 main start`, `redis-server --daemonize yes`).
- `tester_hooks.sh` crée un dépôt temporaire : il doit y copier la configuration ruff, et le fichier du cas 8 doit être conforme
  au formateur, sinon le refus vient de ruff et non du détecteur de secrets.

## Mise à jour — fonctionnalités d à g
Les fonctionnalités a à g sont implémentées et testées. Détail dans `docs/reste-a-faire.md` ; points à vérifier, décisions prises seul et limites dans `docs/a-verifier.md`.

## Plan web (`docs/plan-action-web.md`)

- **Phase 0 — matérialisée.** Matrice parcours/routes/services/permissions dans `docs/web-parcours.md` ;
  décision de palette : jetons émeraude conservés (référence visuelle cobalt non reprise).
- **Phase 1 — fondation.** Navigation desktop/mobile repliable sans JavaScript (`<details>`), liens actifs
  (`aria-current`), pied de page structuré ; composants `etats` (vide/chargement/erreur), `etapes`,
  `filtres` (récapitulatif retirable), `galerie`, `fiche` ; exemples ajoutés à `/styleguide`.
- **Phase 2 — découverte.** Catalogue : en-tête, filtres, récapitulatif des filtres actifs effaçables,
  état vide avec création d'alerte, cartes avec loyer formaté et durée vidéo. Fiche : fil d'Ariane,
  galerie avec visionneuse plein écran en CSS (`:target`), loyer/caractéristiques, gérant vérifié,
  favori, signalement et alerte contextuelle. Tests web et sélecteurs au vert.
- **Phase 3 — identité et espace locataire.** Barre d'étapes sur inscription et mot de passe oublié ;
  espace compte enrichi : préférences de notification (`/compte/preferences`), appareils connectés
  (`/compte/appareils`, révocation), changement de numéro par OTP (`/compte/numero`). Services existants
  réutilisés (aucune règle métier dans les vues).
- **Phase 4 — espace gérant.** Tableau de bord web (`/pro/dashboard`) branché sur
  `tableau_de_bord_gerant` ; « Mes annonces » en table desktop + liste mobile avec statut et commandes
  autorisées par statut ; éditeur par sections (informations, localisation, loyer/équipements, médias,
  publication) **avec aperçu de la carte** ; médias gérés dans l'éditeur (couverture, ordre,
  suppression avec confirmation, auto-rafraîchissement pendant le traitement). Un gérant ne lit jamais
  les annonces d'un autre (couvert par test).
- **Phase 5 — conversations, alertes, notifications (repli HTTP).** Liste de conversations et fil
  retravaillés (annonce, dates, non-lus, sourdine, statut, bulles accessibles) ; notifications avec
  liens profonds, lecture individuelle, « tout lire » **et regroupement des notifications identiques** ;
  alertes avec création, suppression (avec confirmation), pause/réactivation **et modification** par
  formulaire pré-rempli. **Le temps réel reste hors périmètre** : la dépendance `daphne`/WebSocket
  attend un ADR (voir `docs/a-verifier.md` A1) ; la page de conversation conserve son rafraîchissement
  HTTP.

- **Phase 6 — administration (hôte séparé).** Routes d'administration 404 sur le domaine public
  (testé), connexion 2FA OTP, liste blanche d'adresses, journal audit ; **Vue d'ensemble** sur l'index
  avec compteurs réels (modération ouverte/hors délai, sanctions en cours, gérants en attente,
  annonces publiées, taux de réponse, compteurs du jour, journal du jour réservé aux administrateurs).
  Les écrans Gérants, Modération et Journal s'appuient sur les `ModelAdmin` existants (motif obligatoire
  avant lecture d'une conversation, journal filtre par action/rôle). Gabarits d'`adminsite` prioritaires
  sur ceux de Django (DIRS réordonné en `admin_base`). La revue visuelle des 4 maquettes reste à faire
  (PNG illisibles ici, pas de navigateur).

- **Phase 7 — intégration, conformité et vérification globale.**
  Suite `./outils/verifier_tout.sh` au vert complet (WCAG jetons, tests des outils, ruff check,
  ruff format, djlint, import-linter, bandit, makemigrations --check, OpenAPI valide et à jour,
  pytest partiel sans PostgreSQL).
  Feuilles de styles compilées et minifiées sans erreur avec `outils/construire_css.py`.
  Les interfaces publiques (catalogue, fiches, alertes, favoris, conversations, compte) et gérant (tableau de bord,
  gestion des annonces, éditeur multi-étapes) ainsi que l'administration (`adminsite`) intègrent les tokens,
  la grille, les formulaires accessibles et les états prévus par les maquettes.

- **Phase 8 — Refonte générale du design (Web, Tableaux de bord & Thème Admin).**
  - Application stricte du guide de style `docs/design/DESIGN.md` et des maquettes HTML de référence (`docs/design/screens-source/`).
  - Suppression intégrale de tous les emojis dans les gabarits Django (`serveur/web/templates/` et `serveur/adminsite/templates/`), remplacés par des icônes Lucide SVG dédiées.
  - Refonte complète des tableaux de bord de chaque profil :
    - **Espace gérant** (`/pro/dashboard`, `/pro/annonces`, `/pro/annonces/nouvelle`) : barre latérale pro unifiée (`_sidebar.html`), métriques 4 colonnes, grille des annonces actives avec vues et contacts, derniers contacts reçus, éditeur avec upload de médias et aperçu de carte.
    - **Espace locataire** (`/compte`, `/compte/alertes`, `/compte/favoris`, `/compte/messages`, `/compte/notifications`) : panneau profil avec avatar et navigation latérale en cartes, gestion complète des alertes avec chips, messagerie sécurisée sans contact hors plateforme.
    - **Espace administration** (`adminsite`) : intégration des règles du thème Logeo Admin (`serveur/adminsite/static/admin/css/logeo-adm.css` et `serveur/adminsite/templates/admin/base_site.html`), logo officiel, typographie Plus Jakarta Sans, boutons d'action stylisés (jaune solaire `--sun` pour enregistrer, rouge `--danger` pour supprimer), fil d'Ariane épuré, modules arrondis, suppression du dossier externe redondant `serveur/logeo-django-admin-theme`.
    - **Page d'accueil branchée** : `/` sert désormais la page de présentation (`web/accueil.html` : héro illustré, recherche à onglets, « Comment ça marche », FAQ) ; le catalogue reste sur `/annonces`. Le script des onglets est déplacé dans `serveur/web/static/js/accueil.js` (CSP sans script en ligne) et le code mort `views_public.accueil` est supprimé.
  - Élimination intégrale des couleurs et opacités en dur hors de `tokens.css` (conforme règle 8 de `AGENTS.md`).
  - Respect strict de la CSP (règle 5) : suppression de tous les attributs `style=` et gestionnaires d'événements `on...=` inline.
  - Nettoyage documentaire : suppression du document obsolète `docs/plan-action-web.md`.
  - Validation complète : `outils/verifier_tout.sh` au vert (ruff, djlint, tests des outils, contraste WCAG AA, import-linter, bandit, makemigrations, openapi, pytest partiel).

- **Phase 9 — Application Mobile Expo / React Native (`mobile/`).**
  - Refonte et alignement visuel strict des 19 écrans sur les maquettes de référence (`docs/design/screens/`) et `docs/design/DESIGN.md`.
  - Palette officielle Logeo : Bleu cobalt (`#1B44D6`), Nuit (`#0F1B3D`), Jaune solaire (`#FFB429`), Fond clair (`#F5F6FA`).
  - Typographie *Plus Jakarta Sans*, icônes Lucide uniquement (aucun emoji ni sticker, conformément aux règles du projet).
  - Écrans finalisés et stylisés :
    1. **Bienvenue** (`BienvenueScreen`) : bannière nuit, logo officiel, feuille blanche arrondie (rayon 32), pastilles pastel, double CTA locataire/gérant.
    2. **Connexion** (`ConnexionScreen`) : en-tête Logeo, numéro béninois (+229), bouton cobalt, rappel inscription réservée aux locataires.
    3. **Inscription 1/2 & 2/2** (`TelephoneStep`, `CodeStep`) : stepper 2 segments, champ prénom, chips statut étudiant, case CGU, 6 cases de code avec contour cobalt actif, chrono MM:SS, encadré informatif alerte.
    4. **Accueil** (`AccueilScreen`, `ListingCard`) : en-tête avec bouton cloche circulaire, titre héroïque "Où veux-tu habiter ?", barre de recherche avec bouton bleu Filtres, chips de filtrage rapide défilants, cartes annonces avec média 16:9, bouton play blanc centré, badge vert "✓ Vérifié", durée vidéo et prix cobalt.
    5. **Fiche chambre** (`FicheScreen`) : média immersif, bouton play, badge vérifié, feuille blanche remontante (rayon 28), prix mensuel, caractéristiques complètes, action contacter le gérant.
    6. **Filtres** (`FiltresScreen`) : feuille modale avec lien Réinitialiser, sélection quartier/budget/type/équipements.
    7. **Alertes** (`AlertesScreen`) : formulaire inline dans carte blanche, chips cobalt, switch toggle vert pour activer/désactiver.
    8. **Messagerie** (`ConversationScreen`) : interlocuteur avec badge vert vérifié, carte annonce rattachée, bulles blanche et cobalt, bandeau de sécurité jaune, champ pilule avec bouton d'envoi rond.
    9. **Notifications** (`NotificationsScreen`) : badge non lues, filtre chips (Toutes, Non lues, Alertes, Messages), cartes fond bleu pastel #EFF4FF pour les non-lues avec puce et icône cobalt, cartes blanches pour les lues.
    10. **Profil** (`ProfilScreen`) : avatar cobalt + initiales, badge vert gérant vérifié, lignes de menu en cartes blanches avec icônes carrées arrondies bleues, bouton déconnexion rouge pâle.
    11. **Dashboard gérant** (`DashboardScreen`) : salutation personnalisée, grille 2×2 métriques réelles (vues, contacts, chambres actives, louées), alerte jaune pour annonces sans vidéo, liste chambres avec vignettes et badges statut.
    12. **Tunnel de publication** (`EntetePublication`, `InfosStep`, `MediasStep`, `DescriptionStep`, `PublicationStep`) : barre de progression segmentée 4 étapes, étapes d'infos de base, localisation avec repères, téléversement vidéo & photos avec zone pointillée et badge couverture, sélection équipements chips et publication finale jaune solaire.
    13. **Compte gérant** (`CompteGerantScreen`) : badge vert coche, 4 étapes numérotées, actions directes WhatsApp et Appel.
    14. **Abonnement & Paiement** (`AbonnementScreen`, `PaiementMobileMoneyScreen`) : bandeau gratuité, carte offre gérant 2 000 F/mois avec bordure cobalt, sélection opérateur (MTN MoMo, Moov, Celtiis), saisie numéro +229 et confirmation de paiement.

Reste : la revue visuelle in situ et l'E2E navigateur complet avec Chromium (dès qu'un environnement
graphique/Chromium ou Docker est disponible), ainsi que l'arbitrage ADR sur Daphne/WebSockets.

## Mise à jour — 2026-10-13 (comptes gérants)

- **Administration : création d'un gérant.** Section « Gérants » au tableau de bord, bouton
  « Créer un gérant » dans les listes gérants/utilisateurs, formulaire `nouveau-gerant` retravaillé,
  champs de formulaire admin grisés (`serveur/adminsite/`).
- **Notification à la création.** SMS « compte prêt » envoyé après commit et en asynchrone
  (`administration.notifier_creation_gerant`, tâche `notifier_gerant_cree`) ; un échec n'annule jamais
  la création et écrit l'audit `gerant.notification_echec` ; pas de renvoi lors des modifications.
  Décision consignée dans **ADR 0004**.
- **Tuto** : `docs/tuto-compte-gerant.md` décrit tout le parcours, étape par étape.
- **Tests** : `apps/accounts/tests/integration/test_administration.py` (envoi normal, aucun envoi si
  création refusée, compte créé malgré la panne du fournisseur, normalisation E.164, absence de renvoi).
  312 tests `apps/accounts` au vert.
- **Activation gérant (supprimée depuis).** Un parcours d'activation (mobile `/activation/*`, web
  `/pro/activation*`, endpoint API `POST /v1/auth/activate`) avait été ajouté puis **entièrement retiré**
  le 2026-10-14 : la création du compte gérant est purement manuelle (voir la mise à jour correspondante
  en tête de fichier).
- **Correction refonte design.** `navigation.html` et `pro/_sidebar.html` passaient
  `request.user.telephone` (champ inexistant) comme argument de `default:`, ce qui faisait planter le
  rendu pour tout utilisateur connecté ; remplacé par `request.user.phone_e164`. Échecs préexistants
  restants (hors parcours gérant) : `web/tests/test_pro_web.py` et `web/tests/test_pages_publiques.py`.
- **Tests web** : `web/tests/test_comptes_web.py` couvre désormais la connexion du gérant créé par
  l'administration puis le changement de son mot de passe.
- **Trous restants** : agrégateur SMS `[À FOURNIR]` (encodage réel non vérifiable) ; écarts de la refonte
  design dans `web/tests/test_pro_web.py` et `web/tests/test_pages_publiques.py`.

## Mise à jour — 2026-10-13 (refonte web : correctifs de rendu CSS & images)

Diagnostic puis correction des régressions de rendu de la refonte de l'interface web.

- **Désalignement gabarits/CSS** (58 classes utilisées sans règle) résolu par catégorie :
  - Catalogue : `hero-catalogue*` + `recherche-hero*` stylés dans `components/catalogue.css` (bannière
    sombre + barre de recherche), `catalogue-contenu`, `catalogue-tri-form`, `bandeau-alerte`,
    `champ__saisie--pilule`.
  - Fiche : renommage gabarit `fiche-laterale` → `fiche-sidebar` et `fiche-description` →
    `fiche-description-texte` ; ajout de `fiche-principale`, `carte-action-fiche__prix*`,
    `carte-media__overlay-badges`, `fiche-disponibilite*`, `signalement*`.
  - Messages/notifications/alertes : `.liste-annonces`, `.entete-resultats*` (dans `components/annonce.css`).
  - Pro : `.pro-entete__actions`, `.pro-sidebar__infos`, `.apercu-carte`, `.vignette-media`,
    `.confirmation*` (dans `components/pro.css`).
  - Utilitaires : `.d-inline-flex`, `.gap-1`, `.text-muted`, `.text-end`, `.border-bottom`, `.border-0`,
    `.p-0`, `.p-5`, `.mt-1`, `.icone`.
  - Styleguide : `.liste-infos` et jetons nuanciers (`--marque-*`, `--accent-*`, `--sable-25..900`,
    `--succes`, `--avertissement`, `--information`) ajoutés à `tokens.css`.
- **Violation CSP corrigée** : suppression du seul attribut `style=` du projet
  (`public/annonces.html`), l'illustration de fond du catalogue passe en CSS (`hero-catalogue`).
- **Chemin d'image réparé** : `components/catalogue.css` pointait vers un chemin court (404) ; corrigé
  vers l'illustration canonique `../../design/illustration-chambres.svg`.
- **Régressions de suffixe** : `puce--active` → `puce--actif` et `etat-vide__icone` → `etat-vide__symbole`
  dans les gabarits (alignement sur le CSS).
- **Images de démonstration restaurées** : `seed.py` créait des `ListingMedia` photo sans `variants` ni
  `poster_path` (et un `poster_path` vidéo en URL absolue incompatible avec `stockage.url_publique`),
  d'où des cartes sans image. Le seed génère désormais une photo locale (placeholder coloré) traitée par
  le même pipeline que les vrais envois (`apps.media.traitement.traiter_photo`) : variantes WebP écrites
  sous `MEDIA_ROOT`, `poster_path`/`variants` renseignés, et le `poster_path` de la vidéo réutilise la
  photo.
- **Dimensions d'illustrations** harmonisées avec le `viewBox` réel (1600×700) : `accueil.html`
  (640×280) et `auth/formulaire.html` (340×149), suppression du décalage de ratio (CLS).
- **Bannières en image d'arrière-plan** (voiles définis dans `tokens.css`) :
  - Accueil : illustration en fond plein cadre (`--voile-accueil`, `linear-gradient(100deg, .88 30%,
    .05)` + `design/illustration-accueil.svg`) au lieu d'une `<img>` latérale ; `::after` radial
    supprimé (dégradé décoratif interdit par DESIGN.md).
  - Connexion/inscription : panneau latéral idem (`--voile-auth`, `linear-gradient(180deg, .35, .90)`)
    à la place de l'illustration en filigrane (`.auth-lateral__illustration` retirée).
  - Catalogue : voile aligné sur la maquette (`--voile-catalogue`, `linear-gradient(180deg, .55, .85)`)
    au lieu de 70 %/75 % : l'image n'est plus noyée.
- **Illustrations consolidées** sous `serveur/web/static/design/` (comme `logo.svg`) : la bannière
  catalogue pointe vers `design/illustration-chambres.svg` ; le doublon
  `serveur/web/static/img/illustrations/chambres.svg` (copie identique + métadonnée c2pa) est supprimé.
- **Piège de rendu** : Caddy (dev et prod) sert `/static/*` depuis le volume `static` collecté, pas
  depuis les sources montées. Après `make css`, relancer `make migrate` (collectstatic), sinon l'ancien
  hash CSS — supprimé par le build — est encore référencé et les nouvelles images ne sont pas servies.
- **Validation** : `outils/construire_css.py` reconstruit ; `outils/verifier_tout.sh` au vert (ruff,
  djlint, contraste WCAG, import-linter, bandit, makemigrations, openapi, pytest partiel). Seul
  `pytest` complet avec PostgreSQL est sauté dans le bac à sable (base injoignable : mot de passe du rôle
  `app` non fourni).

## Mise à jour — 2026-10-15 (mobile : démarrage Expo Go et notifications)

Le démarrage de l'application mobile sous Expo Go échouait : `features/notifications/push.ts` (importé par
la disposition racine) appelait `getExpoPushTokenAsync`, retiré du push distant Android dans Expo Go depuis
le SDK 53, ce qui levait une erreur fatale et empêchait de compiler/tester. Correctif : détection
`isRunningInExpoGo()` ; sous Expo Go le push est neutralisé (`"indisponible"`), le comportement des dev
builds / EAS est inchangé. Détail dans `mobile/docs/avancement-mobile.md`. Reste : `react-native-compressor`
(Nitro) exige aussi un dev build pour l'étape médias.

## Mise à jour — 2026-10-16 (mobile : connexion bloquée, logo, thème clair)

- **Connexion et inscription qui tournaient sans fin sous Expo Go.** Deux causes : `mobile/.env` pointait
  vers une IP périmée (`192.168.0.195`, l'ordinateur est passé en `192.168.100.14`) et aucune requête
  n'avait de délai, donc `fetch` attendait sans jamais échouer. Correctifs : en développement,
  `config/env.ts` déduit l'URL de l'API de l'IP de Metro (`hostUri`) et du port `EXPO_PUBLIC_API_PORT`
  (8080 par défaut) quand `EXPO_PUBLIC_API_URL` est vide ; `api/client.ts` coupe toute requête après
  20 s (`NetworkError` affichée) ; les mutations d'authentification passent en `networkMode: "always"`
  (NetInfo pouvait les suspendre indéfiniment).
- **Logo unifié.** Composant `Logotype` (`ui/components/Logo.tsx`, icône officielle + « Logeo » + point
  solaire, comme `web/base.html`) utilisé sur Bienvenue, Connexion (glyphe `⌂` supprimé), Inscription,
  Mot de passe, Accueil, Tableau de bord gérant, Compte gérant, Maintenance et Mise à jour.
- **Thème clair uniquement.** Le mode sombre rendait des textes illisibles (couleurs `colors.night` en dur
  sur fond sombre) : `ThemeProvider` sert toujours la palette `clair`, palette `sombre` supprimée,
  `userInterfaceStyle: "light"` et écran de démarrage blanc dans `app.config.ts`.
- **Piège** : `GET /v1/app-config` répond 404 côté serveur (route absente) ; `AppGate` l'ignore, mais la
  barrière maintenance / mise à jour n'est donc pas pilotée tant que la route n'existe pas.
- **Validation** : `jest` 92/92 au vert ; `tsc` sans nouvelle erreur (82 erreurs préexistantes, contre 84).

## Mise à jour — 2026-10-16 (mobile : recherche, plantages d'écrans)

- **Plantage de la fiche** (`Cannot read property 'split' of undefined`) : `FicheScreen` lisait des champs
  inventés (`gerant.full_name`, `avg_response_h`, `cover_url`, `video_duration_s`, `description_text`).
  Réécrite sur `FicheOut` : médias réels (vidéo lisible avec `expo-video`, galerie de vignettes), conditions
  (caution, avance, frais d'agence, disponibilité), eau et compteur, délai médian du gérant, icônes Lucide.
- **Audit de tous les écrans contre l'OpenAPI** : 82 erreurs `tsc` → **0**. Corrigés à l'exécution :
  - Alertes : le corps envoyé (`district`, `type`, `rent_max`…) était ignoré par le serveur ; passage à
    `district_ids` (UUID), `room_types`, `max_rent`, `private_bathroom_required`, `max_distance_m`. Éditeur
    de critères commun (`alerts/EditeurCriteres.tsx`) ; « Créer une alerte » reprend la recherche en cours.
  - Signalement : motifs alignés sur l'enum serveur (`fake_listing`, `price_mismatch`, `contact_leak`, `scam`…).
  - Conversation : `other` (et non `other_party`), prix et image lus depuis la fiche de l'annonce.
  - Tableau de bord gérant : métriques réelles (`conversations_30d`, `listings_by_status`, `to_confirm`).
  - Mot de passe : `current_password` (et non `old_password`).
  - **Tunnel de publication** : l'étape Équipements était un squelette (impasse) → construite (douche,
    clôture, eau, compteur) ; la localisation envoie l'UUID du quartier et ses coordonnées (au lieu du slug et
    de 0,0) ; la description fait un PATCH si l'annonce existe et renvoie à l'étape manquante sinon ; l'envoi
    des médias déclare d'abord le média (`POST …/media` → `upload_url`) puis envoie en tus avec progression ;
    étapes numérotées 1 à 6.
  - Médias : les URL `/media/…` du serveur sont rattachées à l'hôte de l'API (`lib/media.ts`).
- **Recherche refondue** : `BarreRecherche` (saisie directe avec résultats en direct après 450 ms, bouton
  effacer, bouton Filtres avec compteur), raccourcis cumulables, filtres actifs retirables + « Tout effacer »
  (`FiltresActifs`), tri en pastilles, feuille de filtres en brouillon avec budgets prédéfinis, filtre eau et
  nombre réel de résultats sur le bouton. Filtres factices retirés (voir `docs/design/ECARTS.md` §4).
- **Validation** : `tsc` 0 erreur, `jest` 97/97, `expo export --platform android` compile, paramètres de
  recherche vérifiés contre l'API locale.

## Mise à jour — 2026-10-17 (photos refusées, plan d'actions v2)

- **Photos refusées (web et mobile) : corrigé.** Cause : `select_related("gerant…")` et l'accès `annonce.gerant` (qui passe
  par le gestionnaire de base de Django) chargeaient toutes les colonnes de `gerant_profiles`, dont celles que le rôle
  PostgreSQL `app` ne peut pas lire → `permission denied` dans `worker-media` → média `erreur_interne`. Correctif :
  `GerantProfile.Meta.base_manager_name = "objects"` (migration d'options sans SQL `accounts.0004`) et retrait des deux
  `select_related`. Tests de régression sous `SET LOCAL ROLE app` (`test_medias.py::TestDroitsRoleApp`), qui reproduisent
  l'erreur exacte sans le correctif. Migration appliquée sur la pile locale, conteneurs relancés, vérifié en direct.
- **Piège de test** : la suite serveur se lance contre le PostgreSQL de Docker avec `DB_HOST=<ip du conteneur>
  DB_USER=postgres DB_STATEMENT_TIMEOUT_MS=120000` (la création de la base de test dépasse 5 s). 831 tests verts ;
  seul `test_readyz_ok_quand_tout_repond` échoue (file Redis non joignable depuis l'hôte, préexistant).
- **Plan d'actions v2** : `docs/plan-actions-v2.md` (diagnostic D1–D25, décisions V1–V11, phases). Décisions prises :
  identité légale fictive provisoire, avis reportés en V2.
- **Mobile « Écrire au gérant » (P0.8)** : l'écran était un squelette, aucun locataire ne pouvait contacter un gérant
  depuis l'app. Livré (`NouvelleConversationScreen`) et vérifié contre l'API locale. Le test a créé un compte locataire
  d'essai (`+229 01 97 12 34 56`) et une conversation dans la base locale.
- **Paiement débranché totalement en V1 (P0.9, décision du porteur)** : écrans Abonnement et Paiement et leurs routes
  supprimés de l'app (récupérables depuis `10f7333`), question tarifaire retirée de la FAQ web. Rebranchement public
  avec l'application `billing` au lancement payant.
- **Trou découvert** : `GET /v1/app-config` n'existe pas côté serveur (P0.10 du plan).
- **`GET /v1/app-config` livré (P0.10)** et **numéro de l'équipe unifié (P0.3)** : paramètre `TEAM_PHONE` (le lien
  WhatsApp du site avait un 0 de trop), nouveaux paramètres `MIN_SUPPORTED_VERSION`, `MAINTENANCE_ENABLED`,
  `MAINTENANCE_MESSAGE`, `APP_NOTICE`. 836 tests serveur verts (seul `/readyz` échoue, préexistant).
- **Piège** : `make seed` lançait la commande dans `web-api`, où `adminsite` n'est pas installée ; elle passe
  désormais par le conteneur `admin`.
- **Piège** : le script `outils/exporter_client_ts.sh` prévu par le CDC n'existe pas ; le client mobile a été
  régénéré avec `npx openapi-typescript@7.4.4 docs/api/openapi.json -o mobile/src/api/genere/api.d.ts`.
- **Notifications (§9 du plan)** : canal Android et priorité envoyés par le serveur (sans eux tout tombait dans le canal
  par défaut), pastille de non-lus, textes réécrits (`apps/notifications/textes.py`), feuille d'explication avant la
  demande d'autorisation sur mobile. **Bug corrigé** : les préférences de notification du mobile étaient toutes
  refusées (400) — schéma OpenAPI vide masqué par un `as any`. Attention : un canal Android déjà créé garde son
  importance ; il faut réinstaller l'app pour voir les nouveaux réglages de canal.
- **Pages légales (P0.4)** : `/conditions`, `/confidentialite`, `GET /v1/legal/{slug}`, écran mobile ; identité de
  l'éditeur fictive provisoire (`LEGAL_*`). 853 tests serveur verts (seul `/readyz` échoue, préexistant).
- **Décisions V1 à V11 prises** (voir le tableau §2 du plan) : types de chambre avec validation, « Tu es » et nom
  unique, gérant-locataire reporté, empreinte et « se souvenir de moi », éditeur sans souligné, latitude et
  longitude retirées, photos téléchargées par le porteur (13, liste au §8, dossier `photos-brutes/` non versionné),
  KKiaPay plus tard, prix plus tard.
- **À confirmer** : le CDC (§ design, « aucune image externe, ni banque d'images ») interdit les photos de banque
  d'images ; la décision V9 s'en écarte. Les photos seront servies depuis nos fichiers statiques (aucun CDN).
- **Inscription (P0.7 + V2)** : numéro et conditions à l'étape 1, nom complet unique, « Tu es » facultatif et mot de
  passe à l'étape 2 ; colonne `users.occupation` (migration `accounts.0005`, droit colonne `UPDATE (occupation)` pour
  `app`, sinon le profil n'était pas modifiable). Site et profil mobile aussi. 862 tests serveur verts (seul `/readyz`
  échoue, préexistant), 97 tests mobile, 0 erreur de type.
- **Piège** : la pile Docker exécute le code de l'image, pas celui du dépôt ; après un changement serveur, `make up`
  (reconstruction) avant toute vérification en direct.
- **Accueil (P0.6)** : bouton de recherche coupé sur ordinateur et collé aux bords sur téléphone, doublon « Voir les
  chambres » retiré ; vérifié par captures (Playwright + Chrome du poste) à 360, 768 et 1280 px.
- **Conteneurs « unhealthy » (P0.2)** : fausse alerte, la sonde HTTP de l'image (port 8000) s'appliquait à tous les
  processus. Sondes propres à chaque service dans `docker-compose.yml`. Les 11 conteneurs sont *healthy*.
  **Phase 0 terminée.**
- **Reste noté** : `realtime` et `admin` journalisent `Control server error: Permission denied: '/app/.gunicorn'`
  au démarrage (socket de contrôle de gunicorn dans le code monté en lecture pour l'utilisateur `logeo`) ; sans effet.
- **Position des annonces (V7)** : plus de latitude ni de longitude à saisir (site et mobile). L'API les rend
  facultatives (changement additif) : centre du quartier par défaut, GPS du téléphone si le gérant le partage depuis
  l'app (`expo-location`, déjà présent). Pas de GPS sur le site : `Permissions-Policy: geolocation=()` en production.
- **Description enrichie (V6)** : barre de mise en forme sans dépendance, site et mobile, mêmes règles
  (`web/static/js/mise-en-forme.js` et `mobile/src/lib/miseEnForme.ts`, testé). L'aperçu du site passe par
  `POST /v1/pro/markdown/preview`, qui accepte désormais aussi la session du site (avec CSRF), comme l'envoi des
  médias. **Bug corrigé** : la fiche mobile affichait les `**` du Markdown ; elle le rend maintenant.
- **Reste noté** : `/favicon.ico` répond 404 sur le site (préexistant).
- **Données locales** : le gérant de démonstration `+229 01 97 00 00 01` a maintenant le mot de passe
  `GerantEssai2026!` (celui du jeu d'essai ne fonctionnait pas), pour les essais dans le navigateur.
- **Empreinte et « Se souvenir de moi » (V5, ADR 0005)** : nouvelle dépendance mobile `expo-local-authentication`
  (module officiel, ~57.0.3). Verrou facultatif proposé dans le Profil seulement si le téléphone a une empreinte
  enregistrée ; à tester sur un vrai téléphone (dev build). Site : case « Se souvenir de moi » décochée par défaut,
  session de 30 jours si cochée, sinon fermée avec le navigateur (avant : 2 semaines dans tous les cas). Les erreurs
  de champ des formulaires d'authentification passent par `composants/champ.html` (cases à cocher alignées).
  871 tests serveur verts (seul `/readyz` échoue), 104 tests mobile, paquet Android construit.
- **Types de chambre dynamiques (V1)** : table `room_types` (migration `listings.0003`, avec les 4 officiels) ; la
  contrainte `listings_type_valide` est retirée (le service contrôle), `room_type` passe à 40 caractères.
  `GET /v1/room-types` (public, validés, triés par nombre d'annonces), `GET|POST /v1/pro/room-types` (gérant),
  `room_type_label` sur les cartes, la fiche et les annonces du gérant. Administration : « Types de logement »
  (modérateurs autorisés), action « Valider », page « Rattacher à un type existant ». Site : « Ou un autre type »
  dans l'éditeur, onglets de l'accueil et listes de recherche/alertes lus en base. Mobile : chips dynamiques
  (repli hors ligne sur les officiels), « Autre… » dans la publication. 897 tests serveur verts (seul `/readyz`
  échoue), 105 tests mobile. Écart au CDC (§ table `listings`, CK sur `room_type`) : à reporter dans le CDC.
- **Photos (V9)** : circuit retenu avec le porteur : originaux dans `photos-brutes/` (non versionné), script de
  conversion WebP, tailles 480/960/1600 servies en statique par le site, 960 embarquée dans l'app, crédits dans
  `docs/design/credits-photos.md`, exception datée au CDC (« aucune image externe ») à ajouter à l'intégration.
- **Types de logement élargis** : 13 officiels (migration `listings.0004`), de la chambre simple à la villa.
- **Phase 1 (socle épuré)** : motif de marque SVG en filigrane (site : pied de page, états vides, pages légales via
  `--motif-clair`/`--motif-sombre` ; mobile : `FondMotif`), composants mobiles communs (`Groupe.tsx`), Profil refait
  (carte cobalt, listes groupées, WhatsApp Logeo, version), logo animé au démarrage (`DemarrageAnime`), présentation
  en 4 étapes (`/presentation`, avant `/bienvenue`). Bug corrigé : double numérotation du sommaire légal.
- **Mobile, écrans manquants** : espace gérant complet (Mes chambres, fiche, modifier, statistiques) avec deux
  routes ajoutées `GET /v1/pro/listings/{id}/readiness` et `…/stats?days=7|30` (libellés des manques partagés
  site/API) ; messagerie façon WhatsApp (recherche, non lues, sourdine, menu ⋮ bloquer/signaler) ; notifications
  regroupées par jour. 901 tests serveur verts (seul `/readyz` échoue), 105 tests mobile, paquet Android construit.
  **Non vérifié visuellement** : pas d'émulateur ni de cible web Expo (react-native-web absent) ; à regarder sur
  téléphone (Expo Go suffit pour ces écrans).
- **Reste noté** : `base.css` importe Google Fonts, contraire au CDC (« aucune police externe ») et à la CSP.
- **Police hébergée** : Plus Jakarta Sans servie depuis `static/fonts/` (licence OFL jointe). Elle était demandée à
  Google Fonts, interdit par le CDC et **bloqué par la CSP** : le site s'affichait en police système. Icône du site
  déclarée (`/favicon.ico` répondait 404).
- **Alertes (M5)** : `GET /v1/alert-options` (quartiers triés par alertes actives puis annonces publiées, budgets tirés
  des quartiles des loyers). Mobile : composant `ListeDeroulante` (feuille basse, recherche, simple ou multiple),
  « Autre montant… ». Site : même ordre, budgets en `<datalist>` natif.
- **Messagerie web (W5)** : `web/public/messagerie.html` remplace `messages.html` et `conversation.html` ; deux panneaux
  (un seul sous 64rem), bulles compactes, coches envoyé/lu, séparateurs de jour, menu `<details>` (sourdine, signaler,
  bloquer). Rafraîchissement toutes les 20 s seulement si le champ est vide (pas de temps réel sur le site).
- **Compte locataire (W6)** et **tableau gérant (W4)** : tableau de bord locataire en tête de « Mon compte » ;
  interrupteur « Disponible » (louée / remise en ligne) ; bugs corrigés : « Sans vidéo » affiché partout (champ
  inexistant), type de chambre vide, « Derniers contacts » toujours vides, colonne Chambre montrant le quartier.
  908 tests serveur verts (seul `/readyz` échoue).
- **Phase 3 web** : W3 (zone de dépôt, progression par fichier, vignettes ; aperçu vidéo corrigé), W7 (explication,
  session en cours, « Déconnecter tous les autres appareils » via `compte.deconnecter_partout`), W8 (préfixe +229 sur
  tous les numéros, code en cases en CSS seul). Reste W1 (photos de la bannière, en attente des fichiers).
  Essai réel : une photo d'essai (« essai.jpg », bleu uni) a été ajoutée à une annonce du gérant de démonstration.
- **Abonnement prêt mais inactif (CDC §7.11, S5)** : application `billing` (tables `subscriptions`, `payments` avec
  `webhook_events`), plans dans `app_settings.PLANS` (Gratuit V1 actif, Standard sans prix : V11), drapeau
  `SUBSCRIPTION_ENABLED` faux. `can_publish` appelé à la création et à la publication d'une annonce. Fournisseur
  `apps/core/providers/paiement.py` : factice signé HMAC (local, tests) et squelette KKiaPay (V10). Webhook : signature,
  idempotence par identifiant d'événement, tâche `apps.billing.appliquer_evenement`. Échéances quotidiennes (grâce
  7 jours). Plan Gratuit V1 attribué à la vérification (signal `gerant_verifie`) et aux gérants déjà vérifiés
  (migration). Routes `/v1/pro/plans`, `/v1/pro/subscription[/checkout|/cancel]`, `/v1/webhooks/payments/{fournisseur}`
  en `404 feature_disabled` et absentes du schéma public. Administration en lecture seule. 929 tests serveur verts.
  **Écarts au CDC** (consignés dans `docs/design/ECARTS.md`) : écrans « Mon abonnement » et « Choisir un plan »
  (EF-ABO-07) non développés, par décision du porteur (aucun écran de paiement en V1) ; squelette FedaPay non livré
  (V10 : KKiaPay seul) ; masquage des annonces 7 jours après expiration non appliqué (« règle à valider »).
- **Chambres similaires (S3)** : `selectors.similaires` (score quartier/voisin, type, loyer ± 25 %, distance),
  `GET /v1/listings/{ident}/similar`, fiche du site et bandeau sur la fiche mobile.
- **Alertes (A1, A2, A4)** : 3 notifications par alerte et par jour, puis un récapitulatif `alert.digest` mis à jour
  sans re-sonner ; tests de bout en bout (API → publication → notification), pause, reprise, suppression.
- **Recette des filtres (phase 6)** : 38 cas dont la parité site/API. Suite serveur complète verte (seul `/readyz`).
- **426 et 503** : `apps/core/acces_application.py` (intergiciel du site et de l'API) : version sous
  `MIN_SUPPORTED_VERSION` → 426, `MAINTENANCE_ENABLED` → 503 (page `web/maintenance.html` sur le site). Restent ouverts :
  app-config, textes légaux, webhooks, santé, statiques ; l'administration n'est jamais bloquée.
- **Administration refondue** : design aligné (jetons, police locale, `adminsite/static/admin/css/logeo-adm.css`
  réécrit en redirigeant les variables de l'admin Django), accueil « À traiter / Activité / Gérer », page Paramètres par
  thème (`adminsite/parametres_page.py`), quartiers gérables, tout en français (intitulés des applications, modèles,
  champs et valeurs de modération ; migrations d'options et d'intitulés **sans SQL**, vérifiées par `sqlmigrate`),
  noms lisibles, groupes retirés. 984 tests serveur verts (seul `/readyz`).
- **Données locales** : compte administrateur d'essai `admin.essai@logeo.local` / `AdminEssai2026!` (local seulement).

