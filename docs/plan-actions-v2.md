# Plan d'actions v2 — anomalies web et mobile (2026-10-17)

Source : relevé du porteur de projet du 2026-10-17, vérifié dans le code et sur la pile locale.
Règles qui s'appliquent à tout le plan : `AGENTS.md` (pas de champ ni de migration sans validation, pas de
dépendance sans ADR, CSP stricte, API additive sous `/v1`), `docs/design/DESIGN.md`, `docs/design/ECARTS.md`.

Légende : **S** serveur · **W** web · **M** mobile · ⚠️ décision à valider avant de coder.

---

## 0. Diagnostic : ce qui a été vérifié

| # | Question / constat | Réponse vérifiée | Preuve |
|---|---|---|---|
| D1 | L'envoi des photos est refusé | **Bug serveur.** L'envoi réussit (POST 201, PATCH 204) mais le traitement plante : `select_related("gerant__user")` charge toutes les colonnes de `gerant_profiles`, dont les colonnes réservées à l'administration que le rôle PostgreSQL `app` ne peut pas lire → `permission denied for table gerant_profiles` → média `erreur_interne` puis supprimé. 6 photos perdues le 15/10. | `apps/listings/services/medias.py:232`, journaux `worker-media` |
| D2 | Même défaut ailleurs | `apps/listings/services/annonces.py:428` (`select_related("gerant")`) : la remise en ligne après suspension d'un gérant plantera aussi. | lecture du code |
| D3 | « Bloquer cet interlocuteur » marche ? | **Oui côté serveur et web** (`chat.bloquer` / `debloquer`, seul celui qui bloque peut débloquer, diffusion temps réel). L'écran mobile n'a pas de bouton. | `apps/chat/services.py:356` |
| D4 | « Chambres similaires » se base sur quoi ? | Même quartier, triées par date (3 maximum), complétées par les plus récentes de la ville. **Ni le prix ni le type ne comptent** : c'est fonctionnel mais pauvre. | `web/views_public.py:159` |
| D5 | La suppression de compte marche ? | **Oui** : anonymisation + suppression des appareils, mot de passe exigé (web : page Compte ; mobile : `SupprimerCompteScreen`). | `apps/accounts/services/compte.py:139` |
| D6 | Comment marchent les « appareils connectés » ? | Un appareil = une installation de l'**application mobile** (jeton de renouvellement propre, révocable). Les sessions du **site web ne sont pas listées**, d'où une page qui semble vide côté web. | `apps/accounts/models.py:186` |
| D7 | Les vues sont réelles ? | **Oui** : une vue par visiteur et par jour (déduplication Redis 26 h), versée dans les statistiques toutes les 5 min par `beat`. Les conteneurs `beat` et `worker` sont *unhealthy* en local : à vérifier, sinon les compteurs restent figés. | `apps/listings/services/vues.py`, `config/celery.py:16` |
| D8 | Réactions ou avis sur les gérants ? | **Aucun** modèle d'avis. Seuls existent le délai et le taux de réponse calculés. | `apps/*/models.py` |
| D9 | Un gérant peut-il aussi louer une chambre ? | **Non** : les rôles sont exclusifs (`client` / `gerant`), une vingtaine de contrôles `role == "client"` (favoris, alertes, prise de contact). | `apps/accounts/enums.py` |
| D10 | Les notifications marchent du web au mobile ? | Dans l'application (cloche, liste) : **oui**. Push et SMS : fournisseurs `console` en local (rien ne part) ; sous **Expo Go** le push est désactivé (limite d'Expo depuis le SDK 53) : il faut un *dev build*. | `infra/compose/env/*.env`, `mobile/src/features/notifications/push.ts` |
| D11 | Pages Conditions / Confidentialité | Liens présents dans le pied de page mais **404**. | `curl /conditions` |
| D12 | Lien « Contacter l'équipe » WhatsApp | Présent mais **numéro faux** : `wa.me/22901562014000` (un 0 de trop). | `web/templates/web/base.html:71` |
| D13 | Inscription mobile : le nom est demandé deux fois | Le « Prénom » et le statut « Tu es » de l'étape 1 **ne sont envoyés nulle part** (perdus) ; seul le « Nom complet » de l'étape finale est stocké (`users.full_name`). | `TelephoneStep.tsx`, `FinalSteps.tsx` |
| D14 | Type de chambre figé | Énumération en dur (`TypeChambre` : 4 valeurs) validée par le serveur. | `apps/listings/enums.py` |
| D15 | Latitude / longitude dans l'éditeur web | Champs saisis à la main, exigés par l'API. | `web/templates/web/pro/editeur.html:118` |
| D16 | FAQ « Combien coûte la publication ? » | Renvoie vers un abonnement payant : contradictoire avec « tout est gratuit » en v1. | `web/templates/web/accueil.html:412` |
| D17 | Marquer une chambre louée (web) | L'action existe (« Marquer louée ») mais seulement dans la liste, pas sur le tableau de bord, et le libellé est peu clair. | `web/views_pro.py:55` |
| D18 | Algorithmes de filtres | Validation et filtres centralisés (`services/filtres.py`), communs API et site ; recherche tolérante aux fautes vérifiée (`stdio` → studios). Couverture de tests à étendre (un seul fichier). | `apps/listings/tests/test_fil_public.py` |
| D19 | Mobile : « Contacter le gérant » | **Bloquant** : l'écran `NouvelleConversationScreen` est un squelette (« Écran à construire »). Un locataire ne peut démarrer **aucune** conversation depuis l'application. | `mobile/src/features/messaging/NouvelleConversationScreen.tsx` |
| D20 | Mobile : autres écrans squelettes | Espace gérant : `MesAnnoncesScreen`, `AnnonceGerantScreen`, `AnnonceModifierScreen`, `AnnonceStatsScreen`. | `grep "Écran à construire" mobile/src` |
| D21 | Paiement | L'application `billing` est **vide** alors que le CDC (§7.11, EF-ABO-01 à 08) exige l'architecture complète désactivée. L'écran mobile « Paiement Mobile Money » **simule** un paiement (`setTimeout`) : interdit (aucun paiement fictif présenté comme réel). | `serveur/apps/billing/`, `PaiementMobileMoneyScreen.tsx:35` |
| D22 | Push Android | L'application crée des canaux (Messages en priorité haute, Alertes, Rappels) mais le serveur n'envoie **ni `channelId` ni `priority`** : tout tombe dans le canal par défaut, sans bannière ni vibration de message. | `apps/core/providers/push.py:74` |
| D23 | Demande d'autorisation des notifications | Seulement si l'utilisateur active lui-même l'option dans Préférences : la plupart des comptes ne recevront jamais de push. | `mobile/src/features/notifications/push.ts:52` |
| D24 | Textes des notifications | Montant brut (`15000 FCFA` au lieu de `15 000 F`), pluriels `jour(s)` / `message(s)`, titres vagues (« Une annonce a changé »), pas de quartier dans l'alerte, motif technique possible dans « média non traité ». | `apps/*/services*.py` (11 appels à `notifications.creer`) |
| D25 | Correspondance des alertes | **Correcte** (SQL : quartier, type, budget, distance, douche ; sans doublon par alerte et annonce ; redéclenchée à chaque remise en ligne). Manque : plafond quotidien / regroupement si beaucoup de correspondances. | `apps/listings/selectors.py:466` |

---

## 1. Principes : ce que le web et le mobile partagent

Le web (Django) et le mobile (Expo) restent deux clients séparés, mais **une seule source** pour :

1. **Règles métier** : toujours dans les services serveur, exposées par l'API `/v1`. Le web appelle les services, le mobile l'API. Aucune règle dupliquée côté client.
2. **Référentiels dynamiques servis par l'API** (nouveau) : types de chambre, quartiers populaires, budgets fréquents, textes légaux, configuration (`/v1/app-config` : WhatsApp de l'équipe, drapeaux « abonnement actif », « notifications payantes »).
3. **Jetons de design** : un fichier source unique `docs/design/tokens.json` → généré en `serveur/web/static/css/tokens.css` **et** `mobile/src/ui/theme/tokens.ts` par `outils/construire_tokens.py` (contrôlé par `make verifier`).
4. **Textes** : `docs/design/COPYWRITING.md` reste la référence ; les textes légaux sont en Markdown versionné, rendus par le serveur (page web + `GET /v1/legal/{slug}` pour le mobile).
5. **Drapeaux de fonctionnalité** (`app_settings`) : abonnement gérant et notifications payantes **codés et testés, mais désactivés** en v1.

---

## 2. Décisions à valider avant de coder ⚠️

| # | Décision | Proposition | Impact |
|---|---|---|---|
| V1 | Types de chambre dynamiques | ✅ **Décidé (2026-10-17) : avec validation.** Table `room_types` (libellé, slug, `is_official`, compteur d'usage) remplaçant l'énumération ; un gérant peut proposer un type absent, visible tout de suite pour lui, et dans les filtres après validation par la modération (évite les doublons « Entrée coucher » / « entrée-coucher »). | Migration en deux temps, API additive |
| V2 | Profil « Tu es » | ✅ **Décidé (2026-10-17) : oui (champ `occupation` et « Nom complet » unique).** Champ `occupation` (étudiant UP, autre étudiant, salarié, indépendant, autre) sur `users`, facultatif. Le prénom n'est **plus demandé à part** : un seul champ « Nom complet » (prénom extrait pour la salutation). | Migration |
| V3 | Gérant qui loue | ✅ **Décidé (2026-10-17) : reporté en V2.** Rôles cumulables (`is_tenant` en plus de `role`) **ou** reporter en v2. Recommandation : reporter (touche une vingtaine de contrôles et la modération). | Gros chantier |
| V4 | Avis / réactions | ✅ **Décidé (2026-10-17) : reporté en V2.** Avis après une conversation réelle (note 1–5 + commentaire modéré). | — |
| V5 | Empreinte digitale + « Se souvenir de moi » | ✅ **Décidé (2026-10-17) : oui pour les deux (ADR 0005 à rédiger).** Mobile : la session est **déjà** persistante (jeton de renouvellement). On ajoute un **verrou biométrique** à l'ouverture (`expo-local-authentication`, dépendance → **ADR 0005**). Web : case « Se souvenir de moi » = durée de session 30 jours au lieu de la fermeture du navigateur. | Dépendance + ADR |
| V6 | Éditeur riche (gras, souligné, listes) | ✅ **Décidé (2026-10-17) : sans souligné (gras, italique, listes).** Web : barre d'outils Markdown en JavaScript natif (pas de framework, CSP respectée), aperçu via l'endpoint existant. Mobile : même barre au-dessus du champ. Le souligné n'existe pas en Markdown : à remplacer par le gras, ou à accepter en extension contrôlée. | Aucune dépendance |
| V7 | Latitude / longitude | ✅ **Décidé (2026-10-17) : oui, retirées de l'interface.** Retirées de l'interface ; le serveur les déduit du centre du quartier (ou du GPS du téléphone si autorisé). L'API les rend **facultatives** (changement additif). | API |
| V8 | Identité légale | ✅ **Décidé (2026-10-17) : valeurs fictives provisoires**, centralisées dans un seul fichier de paramètres (`LEGAL_*` dans `app_settings`) et marquées « provisoire » dans les textes, à remplacer avant la mise en ligne publique (point bloquant de la check-list de lancement). | Contenu |
| V10 | Fournisseur de paiement | ✅ **Décidé (2026-10-17) : KKiaPay, intégration plus tard** (un seul adaptateur, plus de squelette FedaPay). FedaPay ou KKiaPay (les deux gèrent MTN MoMo et Moov au Bénin) : squelettes pour les deux, choix au moment de l'activation selon les frais et le contrat. | Aucun tant que le drapeau est faux |
| V11 | Plans et prix | ✅ **Reporté (2026-10-17) : grille fixée au moment de l'activation.** Grille du §7 bis (prix à fixer) ; seul « Gratuit V1 » est actif au lancement. | Paramètres, pas de migration |
| V9 | Images réelles | ✅ **Décidé (2026-10-17) : le porteur télécharge les 13 photos listées au §8** et les dépose dans `photos-brutes/` (non versionné). Images libres (voir §8) : tu télécharges, on les place dans `serveur/web/static/design/photos/` et `mobile/assets/photos/`, compressées en WebP. | Contenu |

---

## 3. Phase 0 — Correctifs bloquants (à faire d'abord)

| # | Action | Où | Critère de réussite |
|---|---|---|---|
| P0.1 | ✅ **Fait (2026-10-17).** `GerantProfile.Meta.base_manager_name = "objects"` (migration d'options sans SQL `accounts.0004`) + retrait des deux `select_related("gerant…")`. Deux tests de régression exécutés **sous le rôle `app`** (échouent sans le correctif avec l'erreur exacte de production). Vérifié en direct dans le conteneur. | S | ✅ 831 tests serveur verts |
| P0.8 | ✅ **Fait (2026-10-17).** « Écrire au gérant » : carte de la chambre, message prérempli modifiable (COPYWRITING §6), réponses rapides, rappel de sécurité, envoi idempotent, erreurs traduites. Vérifié contre l'API locale (création 201, rejeu sans doublon, coordonnées masquées avec avertissement, annonce disparue). | M | ✅ |
| P0.9 | ✅ **Fait (2026-10-17) — paiement débranché totalement en V1** (décision du porteur) : écrans Abonnement et Paiement et leurs routes supprimés de l'app (récupérables depuis le commit `10f7333`), question « Combien coûte la publication ? » retirée de la FAQ web. Aucune mention de paiement, même « bientôt disponible ». Le rebranchement public se fera avec l'application `billing` (§7 bis). | M W | ✅ |
| P0.10 | ✅ **Fait (2026-10-17).** `GET /v1/app-config` livré (public, cache 60 s) : version minimale, maintenance, avis, drapeaux (`subscription` forcé à faux en V1), limites déclarées par chaque application au démarrage (registre `apps.core.configuration`), temps réel, contact. OpenAPI régénéré (ajouts seulement), client TypeScript mobile régénéré. **Reste** : le serveur ne renvoie pas encore `426` sous la version minimale ni `503 maintenance` (le mobile s'appuie sur `app-config`). | S M | ✅ |
| P0.2 | Vérifier pourquoi `beat`, `worker`, `worker-media` sont *unhealthy* (pool PostgreSQL saturé : `couldn't get a connection after 5 s`). | infra | 3 conteneurs *healthy*, vues versées |
| P0.3 | ✅ **Fait (2026-10-17).** Numéro de l'équipe dans un seul paramètre (`TEAM_PHONE`, modifiable dans l'administration) servi au site (processeur de contexte `contact`, liens `tel:` et WhatsApp corrigés) et au mobile (`/v1/app-config` → `contact`, repli local). | S W M | ✅ |
| P0.4 | ✅ **Fait (2026-10-17).** Textes rédigés depuis le CDC (`apps/core/textes_legaux/*.md`), identité de l'éditeur **fictive provisoire** dans les paramètres `LEGAL_*` (bandeau « Version provisoire » tant que `LEGAL_PROVISIONAL` est vrai), pages web `/conditions` et `/confidentialite` au style des captures, `GET /v1/legal/{slug}` et écran mobile ; liens depuis le Profil, l'Aide et l'inscription (case d'acceptation désormais décochée par défaut et obligatoire). **Avant l'ouverture** : vraies valeurs `LEGAL_*`, relecture par un juriste (CDC §8.4), `LEGAL_PROVISIONAL` à faux. | S W M | ✅ |
| P0.5 | ✅ FAQ (D16) : question retirée (voir P0.9). | W | ✅ |
| P0.6 | Bouton « Voir les chambres » de l'accueil non responsive. | W | Lisible et pleine largeur sous 400 px |
| P0.7 | ✅ **Fait (2026-10-17), avec V2.** Étape 1 : numéro et acceptation des conditions (obligatoire avant le SMS). Étape 2 : « Nom complet » demandé une seule fois, « Tu es » facultatif (colonne `users.occupation`, migration `accounts.0005` avec le droit `UPDATE (occupation)` du rôle `app`), mot de passe. Plus aucune saisie perdue : le prénom et le statut de l'étape 1 n'étaient jamais envoyés. « Tu es » aussi sur le site (inscription, page compte) et dans le profil mobile. Vérifié en direct. | S W M | ✅ 862 tests serveur verts |

---

## 4. Phase 1 — Socle de design partagé (« épuré »)

Le style des captures s'appelle couramment une **interface épurée de type fintech** (*clean / soft minimal UI*) :
grands titres très gras, **listes groupées en cartes** (*inset grouped lists*, comme les Réglages d'iOS), icônes
dans des pastilles teintées, une **carte d'en-tête colorée** (*hero card*) et un **motif de fond en filigrane**
(*subtle background pattern* : ligne courbe avec points, formes diagonales très pâles).

| # | Action | Où |
|---|---|---|
| P1.1 | `tokens.json` unique + génération web/mobile (voir §1.3) ; ajout des jetons : fonds teintés `--blue-25/50`, bordures 1 px très pâles, rayons 20/24, ombres très douces. | S W M |
| P1.2 | Motif de fond SVG (courbe + points cobalt et solaire, opacité ≤ 8 %) : en `background` CSS sur le web, composant `FondMotif` sur mobile. | W M |
| P1.3 | Composants communs (même nom, même rendu) : `CarteHero`, `GroupeListe` + `LigneListe` (icône pastille, titre, sous-titre, chevron ou interrupteur), `EnTeteEcran` (retour en carte, titre, sous-titre, action), `ChampIcone` (icône à gauche, œil à droite), `ListeDeroulante`. Présentés dans `/styleguide`. | W M |
| P1.4 | Appliquer d'abord à : Profil, Compte/Sécurité, Préférences, Appareils, Légal (là où les captures s'appliquent directement). | W M |

---

## 5. Phase 2 — Mobile

| # | Action | Détail | Critère |
|---|---|---|---|
| M1 | Logo animé au démarrage | Écran de démarrage natif blanc, puis animation du logo (épingle qui tombe, maison qui apparaît, point solaire qui pulse ; `Animated` de React Native, sans dépendance), 1,2 s maximum. | Fluide, pas de saut entre écran natif et animation |
| M2 | Onboarding 4 étapes | 1) Des vraies chambres en vidéo 2) Gérants vérifiés par l'équipe 3) Écris sans donner ton numéro 4) Sois prévenu (alertes). Illustrations/photos, points de progression, « Passer », motif de fond. En dev : **toujours affiché** (déjà en place dans `src/app/index.tsx`). | Visible au 1er lancement en prod, à chaque lancement en dev |
| M3 | Connexion | Case « Se souvenir de moi » (session persistante ou effacée à la fermeture) ; verrou par empreinte si activé (V5). | Réouverture sans mot de passe si coché |
| M4 | Inscription | « Tu es » en liste déroulante élargie (V2) ; un seul champ nom. | Données saisies = données stockées |
| M5 | Alertes | Quartier : liste déroulante triée par **fréquence d'usage** (quartiers les plus recherchés en tête). Budget : liste déroulante de montants fréquents + « Autre montant » qui fait apparaître un champ. Fréquences calculées par le serveur (§7.2). | Listes servies par l'API, triées |
| M6 | Images de fond | Photos réelles (§8) sur Bienvenue, Onboarding, Accueil, fiche sans média. | Aucune illustration générique restante |
| M7 | Profil façon captures | Carte identité (avatar, nom, numéro, « Compte vérifié »), groupes « Compte et sécurité », « Préférences et assistance » (WhatsApp de l'équipe), « Informations légales », déconnexion, version. | Conforme à P1.3 |
| M8 | Conversation | Bouton « Bloquer / Débloquer » (D3) ; bulles plus compactes (voir W5). | Blocage effectif depuis le mobile |

### 5 bis. Fonctionnalités manquantes ou incomplètes du mobile

Parité attendue avec le web : tout ce qu'un locataire ou un gérant fait sur le site doit être faisable dans l'app.

| # | Fonctionnalité | État actuel | À faire |
|---|---|---|---|
| MM1 | Écrire au gérant | Squelette (D19) | Voir P0.8 |
| MM2 | Liste des conversations | Liste simple sans design | Façon WhatsApp : avatar (initiales), nom, chambre liée, extrait du dernier message, heure, pastille de non-lus, conversation en sourdine grisée, glisser pour archiver/sourdine ; recherche dans les conversations |
| MM3 | Conversation | Fonctionnelle (envoi hors ligne, temps réel) | Menu « ⋮ » : bloquer / débloquer, signaler, sourdine 8 h / 1 semaine / toujours ; bannière « conversation bloquée / lecture seule » ; coches envoyé / lu (`other_read_seq`) ; séparateurs de jour ; saisie multiligne ; ouverture depuis une notification directement au bon message |
| MM4 | Mes annonces (gérant) | Squelette | Liste par statut (en ligne, brouillons, masquées, louées) avec actions : confirmer disponible, marquer louée / remettre en ligne, masquer, modifier |
| MM5 | Fiche annonce gérant | Squelette | Aperçu, statut, ce qui manque pour publier (`manques_a_la_publication`), médias en cours de traitement |
| MM6 | Modifier une annonce | Squelette | Réutiliser les étapes du tunnel en mode édition (PATCH) |
| MM7 | Statistiques d'une annonce | Squelette | Vues, favoris, contacts sur 7 / 30 jours (`daily_stats`), même source que le web |
| MM8 | Messages gérant | Onglet partagé | Filtre « à répondre », délai de réponse affiché |
| MM9 | Notifications | Écran présent | Regroupement par jour, actions rapides (ouvrir la conversation, voir la chambre), « tout marquer comme lu » |
| MM10 | Abonnement / paiement | Retirés de l'app (P0.9) | Rebranchés sur l'API de §7 bis seulement au lancement payant |
| MM11 | Pages légales, aide, WhatsApp de l'équipe | Absents | Écrans « Conditions », « Confidentialité », « Aide » servis par l'API (§1.4) ; ligne « WhatsApp Logeo » dans le Profil |

---

## 6. Phase 3 — Web

| # | Action | Détail |
|---|---|---|
| W1 | Bannière de l'accueil | Diaporama de 3 à 5 photos réelles (§8) en fondu, CSS seul (`@keyframes`, sans script), `prefers-reduced-motion` respecté, voile pour le contraste du texte. |
| W2 | Types de chambre dynamiques | Liste déroulante + « Autre type… » dans l'éditeur (V1) ; filtres alimentés par l'API. |
| W3 | Éditeur d'annonce | Retirer latitude/longitude (V7) ; barre d'outils de texte (V6) ; envoi de médias redessiné (zone de dépôt, vignettes, progression, erreurs lisibles). |
| W4 | Tableau de bord gérant | Responsive (cartes empilées sous 768 px) ; sur chaque chambre, interrupteur explicite **« Chambre encore disponible »** : le décocher appelle `marquer_louee` et retire la chambre du fil et de la recherche ; le recocher la remet en ligne (`undo-rented`). |
| W5 | Messagerie façon WhatsApp | Liste à gauche (avatar, nom, extrait, heure, pastille non lus), fil à droite ; bulles compactes (largeur max 75 %, coins arrondis asymétriques, heure et coches dans la bulle), séparateurs de jour, en-tête avec la chambre liée (photo, prix), menu (bloquer, signaler, sourdine). Mobile aligné. |
| W6 | Tableau de bord locataire | Refonte : en-tête de salutation, raccourcis (favoris, alertes, messages, notifications) en cartes avec compteurs, dernières chambres consultées, alertes actives. |
| W7 | Appareils connectés | Expliquer ce qu'est un appareil (D6) ; lister aussi la **session web en cours** ; bouton de déconnexion des autres appareils. |
| W8 | Changer de numéro | Écran en 2 étapes avec barre d'étapes, `ChampIcone`, code en 6 cases (même composant que l'inscription). |
| W9 | Contacter l'équipe | Lien WhatsApp direct (P0.3) partout où « Contacte l'équipe » apparaît. |

---

## 7. Phase 4 — Métier (serveur, partagé)

| # | Action | Détail |
|---|---|---|
| S1 | Types de chambre (V1) | Table, endpoint `GET /v1/room-types` (triés par usage), proposition par le gérant, validation en modération. |
| S2 | Fréquences | Endpoint `GET /v1/search-hints` : quartiers et plafonds de budget les plus utilisés (recherches + alertes, 90 jours), pour les listes de M5 et du web. |
| S3 | Chambres similaires (D4) | Score : même quartier ou quartier voisin, type identique, loyer à ± 25 %, distance à l'UP proche ; repli sur les plus récentes. Partagé : `GET /v1/listings/{ident}/similar` utilisé par le web et le mobile. |
| S4 | Vues (D7) | Une fois `beat` réparé : test de bout en bout vue → statistiques → tableau de bord. |
| S5 | Abonnement prêt mais désactivé | Services, modèles et écrans d'abonnement gérant derrière `SUBSCRIPTION_ENABLED=False` ; aucun prix affiché tant qu'il est faux. Même chose pour les notifications payantes des locataires (`PAID_ALERTS_ENABLED`). |
| S6 | Avis (V4, reporté en V2) et gérant-locataire (V3) | Consignés dans `docs/reste-a-faire.md` pour la V2. |

### 7 bis. Plans et architecture de paiement (CDC §7.11, EF-ABO-01 à 08)

Objectif : le serveur est **codé et testé**, mais rien n'est visible ni facturé. **Décision 2026-10-17 : aucun écran de paiement dans les apps en V1** (même pas « bientôt disponible ») ; les écrans seront rebranchés publiquement au moment opportun.
Le jour de l'activation, on change un paramètre dans l'administration, sans migration ni nouvelle version de l'app.

**Modèle de données** (application `billing`, aujourd'hui vide) :

| Table | Rôle |
|---|---|
| `plans` (ou `app_settings` : EF-ABO-01) | Code, libellé, public (`gerant` / `locataire`), prix en FCFA, période (mois), limites (nombre d'annonces en ligne, mise en avant, alertes SMS), actif |
| `subscriptions` | Gérant ou locataire, plan, statut (`trialing`, `active`, `past_due`, `canceled`, `expired`), début / fin de période, fin de grâce |
| `payments` | Abonnement, montant, opérateur (MTN MoMo, Moov Money, Celtiis Cash), référence fournisseur, statut (`pending`, `succeeded`, `failed`, `refunded`), numéro payeur **masqué** |
| `webhook_events` | Identifiant d'événement du fournisseur (unique → idempotence), charge utile, signature vérifiée, date de traitement |

**Services et points d'extension** :
- `PaymentProvider` (`apps/core/providers/paiement.py`) : `initier`, `verifier`, `rembourser`, `traiter_webhook` ; implémentations **Factice** (local et tests, déterministe), **FedaPay** et **KKiaPay** (squelettes, clés `[À FOURNIR]`). Choix du fournisseur : ⚠️ décision V10.
- `can_publish(gerant)` : appelé à la création et à la publication ; toujours vrai si `SUBSCRIPTION_ENABLED=False` (EF-ABO-03).
- Plan **Gratuit V1** (0 F, sans limite) attribué automatiquement à chaque gérant vérifié (EF-ABO-06) : l'activation future n'exige aucune migration de données.
- Tâches : relance avant échéance, passage en `past_due` puis `expired`, masquage des annonces 7 jours après l'expiration (§11.5, règle à valider).
- Webhooks : signature vérifiée, idempotence par identifiant d'événement, traitement asynchrone (EF-ABO-05).

**Parcours de paiement Mobile Money** (web et mobile identiques, piloté par le serveur) :
1. Choix du plan → 2. opérateur + numéro → 3. `POST /v1/billing/payments` (le serveur appelle le fournisseur) →
4. l'utilisateur valide sur son téléphone (USSD / notification de l'opérateur) → 5. webhook → paiement `succeeded` →
abonnement `active` → notification « Paiement reçu » → 6. l'app suit l'état (`GET /v1/billing/payments/{id}`, temps réel si
disponible). Aucun résultat n'est jamais affiché avant la confirmation du serveur.

**Plans proposés** (⚠️ décision V11, prix indicatifs à valider) :

| Public | Plan | Contenu |
|---|---|---|
| Gérant | Gratuit V1 | Tout, sans limite (lancement) |
| Gérant | Standard | Annonces illimitées, statistiques détaillées |
| Gérant | Mise en avant | Annonce en tête du fil de son quartier pendant 7 jours |
| Locataire | Alerte prioritaire | Alertes par SMS en plus du push, dès la publication |

**Drapeaux** : `SUBSCRIPTION_ENABLED` (gérants) et `PAID_ALERTS_ENABLED` (locataires), faux par défaut, exposés à l'app par
`/v1/app-config` ; endpoints en `404 feature_disabled` tant qu'ils sont faux (EF-ABO-02). Tests : toutes les transitions
valides et invalides de la machine à états, idempotence des webhooks, signature refusée.

---

## 8. Images libres proposées (à télécharger par toi)

Sources à licence libre, utilisables sans attribution obligatoire (créditer reste apprécié) :
**Unsplash** (unsplash.com/license), **Pexels** (pexels.com/license), **Pixabay** (pixabay.com/service/license-summary).

**13 photos à télécharger** (décision V9). Dépose-les dans `photos-brutes/` à la racine du dépôt (non versionné),
en les nommant comme ci-dessous ; l'extension n'a pas d'importance (JPG, PNG…).

| Fichier | Où elle sert | Ce qu'on doit voir | Recherches conseillées | Format |
|---|---|---|---|---|
| `accueil-1` | Bannière d'accueil du site (diaporama) | Rue résidentielle d'Afrique de l'Ouest : maisons basses, murs clairs, arbres, lumière du jour | `west africa street houses`, `benin street`, `african residential street` | Paysage, ≥ 1920 px de large |
| `accueil-2` | Bannière d'accueil du site | Jeune étudiant ou étudiante africain(e) souriant(e), téléphone en main, en extérieur | `african student phone`, `young african smiling phone` | Paysage, ≥ 1920 px |
| `accueil-3` | Bannière d'accueil du site | Cour intérieure d'une maison ou d'une petite résidence, avec plantes | `african house courtyard`, `tropical house courtyard` | Paysage, ≥ 1920 px |
| `type-single` | Fiche sans photo : chambre simple | Petite chambre propre : lit, moustiquaire ou ventilateur, fenêtre | `simple bedroom africa`, `small bedroom mosquito net` | 4:3, ≥ 1200 px |
| `type-entree-coucher` | Fiche sans photo : entrée-coucher | Petite pièce d'entrée avec une porte ouverte sur la chambre | `small apartment entrance bedroom`, `small living room door bedroom` | 4:3, ≥ 1200 px |
| `type-chambre-salon` | Fiche sans photo : chambre-salon | Salon simple (canapé, table basse) | `simple living room africa`, `small living room sofa` | 4:3, ≥ 1200 px |
| `type-studio` | Fiche sans photo : studio | Studio avec lit et coin cuisine dans la même pièce | `studio apartment kitchenette`, `small studio interior` | 4:3, ≥ 1200 px |
| `onboarding-1` | Présentation mobile : « Cherche » | Personne qui fait défiler son téléphone, assise | `african woman scrolling phone`, `young african man phone` | Portrait, ≥ 1080 × 1350 |
| `onboarding-2` | Présentation mobile : « Vois en vidéo » | Main qui filme une pièce avec un téléphone | `filming room with phone`, `phone recording video interior` | Portrait, ≥ 1080 × 1350 |
| `onboarding-3` | Présentation mobile : « Discute » | Deux jeunes qui discutent, ou gros plan d'une messagerie | `african friends talking`, `phone chat close up` | Portrait, ≥ 1080 × 1350 |
| `onboarding-4` | Présentation mobile : « Emménage » | Clés remises de main en main, ou personne qui porte des cartons | `handing over keys`, `moving in boxes african` | Portrait, ≥ 1080 × 1350 |
| `bienvenue` | Écran de bienvenue mobile | Ville ouest-africaine vue d'en haut, ou paysage du Bénin au coucher du soleil | `african city aerial`, `benin landscape`, `parakou` | Portrait, ≥ 1080 × 1920 |
| `gerant` | Page « Publie ta chambre » (site et app) | Propriétaire adulte devant une maison ou un portail | `african man in front of house`, `african landlord` | Paysage, ≥ 1600 px |

Critères : lumière naturelle, personnes et lieux d'Afrique de l'Ouest de préférence, aucune marque ni plaque
visible, aucun visage reconnaissable sans autorisation de modèle (*model release*, indiqué sur Unsplash/Pexels).
Une fois les fichiers placés, ils sont convertis en WebP (480 / 960 / 1600) par `outils/` et la licence de chaque
photo est notée dans `docs/design/credits-photos.md`.

---

## 9. Phase 5 — Notifications et alertes de bout en bout

### 9.1 Ce qui est déjà solide (vérifié)

Centre de notifications avec non-lus, déduplication, préférences par catégorie (messages, alertes, rappels), aperçu
des messages masquable, sourdine par conversation, **pas de push si la conversation est déjà ouverte** sur l'appareil,
regroupement par conversation (`collapse_key`), 5 essais en cas d'échec, jetons invalides désactivés, routage des appuis
vers le bon écran (`routage.ts`, testé). Correspondance des alertes correcte (D25).

### 9.2 Notifications « comme WhatsApp », même application fermée

| # | Action | Où |
|---|---|---|
| N1 | Envoyer `channelId` (messages / alertes / rappels / compte) et `priority: "high"` pour les messages (D22) : bannière en haut de l'écran, son et vibration propres aux messages, même téléphone verrouillé. | S |
| N2 | Titre « **Nom** » + sous-titre « Chambre-salon à Banikanni », corps = aperçu du message (ou « Nouveau message » si l'aperçu est désactivé). Regroupement par conversation (`threadId` iOS, groupe Android) : « 3 nouveaux messages ». | S M |
| N3 | **Répondre depuis la notification** (catégorie avec champ texte de `expo-notifications`) et « Marquer comme lu » : la réponse passe par la file d'envoi existante (`outbox`), donc fonctionne même avec un réseau instable. | M S |
| N4 | Pastille du nombre de non-lus sur l'icône de l'app (`badge`), remise à jour à la lecture. | S M |
| N5 | Application ouverte : bannière interne discrète (pas de notification système) sauf si la conversation est à l'écran. | M |
| N6 | Rattrapage : à la reconnexion, les messages manqués arrivent sans doublon (déjà prévu par `seq`) ; test de recette dédié. | S M |

### 9.3 Demande d'autorisation (au bon moment, avec explication)

✅ **Fait (2026-10-17)** : N1 (canaux + priorité), N2 (titre « Nom · chambre »), N4 (pastille), §9.3 (feuille d'explication après le premier message et la première alerte), §9.4 (textes). Corrigé au passage : les préférences de notification du mobile étaient toutes refusées par le serveur (format). **Reste** : N3 (répondre depuis la notification, tâche d'arrière-plan, à tester sur dev build), N5, N6, §9.5 A2 (récapitulatif quotidien), recette §9.6 sur dev build.

Le système ne permet de demander qu'une fois (Android 13+, iOS) : un refus est presque définitif. On affiche donc d'abord
**notre propre écran d'explication**, puis la demande système seulement si la personne accepte :
1. à la fin de l'onboarding (« Sois prévenu dès qu'un gérant te répond ou qu'une chambre correspond ») ;
2. sinon, au premier moment utile : après l'envoi du premier message, ou à la création de la première alerte ;
3. en cas de refus : bandeau doux dans Messages et Alertes avec lien vers les réglages du téléphone ;
4. les autres permissions suivent la même règle (caméra et photos au moment d'ajouter un média, position au moment de
   localiser la chambre) — jamais au démarrage.

Rappel : **le push n'existe pas sous Expo Go** (SDK 53+). La recette push se fait sur un *dev build* EAS, avec
`PUSH_PROVIDER=expo` côté serveur.

### 9.4 Textes des notifications (D24)

Ton : tutoiement, phrase courte, l'information utile d'abord, montants au format `15 000 F`, vrais pluriels.

| Événement | Aujourd'hui | Proposé |
|---|---|---|
| `alert.match` | « Nouvelle chambre pour toi » / « Titre — 15000 FCFA par mois. » | « Nouvelle chambre à Banikanni » / « Entrée-coucher · 15 000 F/mois · à 600 m de l'UP. Vois-la avant les autres. » |
| `message.received` | Nom / aperçu | « Aïcha · Chambre-salon Banikanni » / aperçu (inchangé sur le fond) |
| `message.unanswered_reminder` | « Tu as 2 message(s) non lu(s) depuis plus de 24 h. » | « Koffi attend ta réponse depuis hier » / « 2 messages non lus sur Studio Titirou. Réponds vite : les locataires vont au plus réactif. » |
| `listing.reminder` | « …masquée dans 3 jour(s). » | « Ta chambre est toujours libre ? » / « Confirme Studio Titirou en un geste, sinon elle sera masquée dans 3 jours. » |
| `favorite.unavailable` | « Une annonce en favori a changé » | « Studio Titirou vient d'être louée » / « D'autres chambres t'attendent dans le même quartier. » |
| `listing.published` | « Ton annonce est en ligne » | (inchangé) + « Les locataires qui ont une alerte correspondante sont prévenus. » |
| `listing.media_failed` | Motif brut | Motif traduit en français simple + action (« Réessaie avec une vidéo de moins de 60 s »). |
| `account.sanction` | Titre par action | Inchangé, relu avec la modération. |

Tous ces textes passent dans un seul module (`apps/notifications/textes.py`) avec des tests (pluriels, montants, longueur
maximale d'un titre de notification) et sont copiés dans `docs/design/COPYWRITING.md`.

### 9.5 Alertes

| # | Action |
|---|---|
| A1 | Test de bout en bout : alerte créée (web et mobile) → annonce publiée → notification reçue → appui → bonne fiche. |
| A2 | Plafond : au-delà de 3 correspondances dans la journée pour une même alerte, un seul récapitulatif (« 5 nouvelles chambres correspondent à ton alerte Banikanni »). |
| A3 | Alerte créée depuis une recherche : mêmes critères sur le web et le mobile (le mobile le fait déjà depuis le 2026-10-16). |
| A4 | Pause, reprise et suppression testées des deux côtés ; une alerte en pause ne déclenche rien. |

### 9.6 Matrice de recette

Pour chaque événement (`message.received`, `message.unanswered_reminder`, `alert.match`, `favorite.unavailable`,
`listing.published`, `listing.hidden`, `listing.reminder`, `listing.reported_rented`, `listing.media_failed`,
`account.sanction`) et chaque canal :

| Canal | Local | Recette |
|---|---|---|
| Centre de notifications (web et mobile) | Oui | La cloche s'incrémente, le lien ouvre le bon écran |
| Temps réel (WebSocket) | Oui si `realtime` actif (ADR Daphne en attente, `docs/a-verifier.md` A1) | Message reçu sans rafraîchir |
| Push mobile (app ouverte, en arrière-plan, fermée, téléphone verrouillé) | *Dev build* uniquement | Bannière, son, regroupement, réponse depuis la notification |
| SMS | Console | Agrégateur `[À FOURNIR]` |

Livrable : `docs/verification-notifications.md` (résultat par événement × canal).

---

## 10. Phase 6 — Vérification des filtres et recette

1. Jeu de données de test couvrant chaque critère (quartier, type, loyer min/max, douche, eau, compteur, clôture, distance, disponibilité, tri).
2. Tests serveur paramétrés : chaque filtre seul, combinés deux à deux, valeurs limites, valeurs invalides (erreur 400 lisible), recherche avec fautes et accents.
3. Test de parité : la même recherche sur le web et l'API renvoie les mêmes annonces dans le même ordre.
4. Recette visuelle web (1280 px et 390 px) et mobile (Expo Go puis *dev build*) de chaque écran modifié.

---

## 11. Ordre de réalisation proposé

1. **Phase 0** (correctifs bloquants : P0.1 fait ; P0.8 « Écrire au gérant » et P0.9 paiement simulé en priorité) puis
   validation des décisions restantes (V1, V2, V3, V5, V6, V7, V9, V10, V11).
2. **Notifications N1, N2 et la demande d'autorisation (§9.3)** tôt : peu de code, effet immédiat sur l'usage.
3. **Phase 1** (socle de design partagé), qui conditionne les refontes d'écrans.
4. **Phases 2, 3 et 5 bis** par écran (le même écran est livré web + mobile ensemble).
5. **Phase 4 et §7 bis** au fil des écrans qui en dépendent (S1/S2 avant M5 et W2 ; S3 avant la fiche ; `billing` avant MM10).
6. **Phases 5 et 6** en recette finale ; `docs/avancement.md` mis à jour à chaque lot.
