# Plan d'action — expérience web Logeo

**Périmètre :** site public, parcours locataire, espace gérant et, dans une phase séparée, interface
d'administration. **L'application mobile est hors périmètre** : aucune navigation, livraison ou promesse
APP ne doit bloquer ce chantier web.

Ce document est un plan de réalisation, pas la déclaration que toutes les fonctions sont déjà disponibles.
Les pages existantes restent la source de vérité pour le comportement actuel ; les maquettes sont des
références visuelles, pas des sources de données ni des contrats métier.

## Résultat attendu

Une personne peut découvrir une chambre, vérifier ses informations, créer un compte, contacter le gérant
dans Logeo et suivre l'échange. Un gérant peut créer un brouillon, envoyer ses médias, publier et gérer ses
annonces et ses conversations. Les opérations réellement proposées à l'écran sont persistées et contrôlées
par le serveur ; aucune donnée fictive ne donne l'illusion qu'une action ou un paiement a réussi.

## Périmètre et architecture

- **WEB public et locataire :** accueil/catalogue, quartiers, fiche, authentification, compte, favoris,
  alertes, messages et notifications.
- **WEB gérant :** tableau de bord, annonces, création/édition, médias, publication, messages et profil.
- **ADM :** interface navigateur sur son hôte, processus, réglages et accès séparés. Les maquettes Admin
  sont planifiées comme une phase dédiée, jamais comme des pages ajoutées à l'hôte public.
- **APP mobile :** explicitement reportée après l'acceptation du WEB.
- Le projet est rendu par Django et ses gabarits. Les vues WEB appellent les mêmes services/sélecteurs que
  l'API : ne pas créer un deuxième métier dans le navigateur et ne pas transformer le site en SPA.
- L'exception d'intégration côté navigateur est l'envoi de médias déjà raccordé à l'API : conserver CSRF,
  session, autorisation serveur, reprise et retours de progression. Les opérations ne nécessitant pas l'API
  passent par les formulaires et vues Django existants.
- CSS pur, sans Node ni CDN, construit par `make css`. Toute valeur visuelle passe par les jetons de
  `serveur/web/static/css/tokens.css`. Pas de règles métier, d'autorisation ou de données sensibles dans JS.

## Références visuelles

Les références principales pour le WEB sont [Web · Chambres](../maquette/Web%20%C2%B7%20Chambres.png),
[Web · Détail d'une chambre](../maquette/Web%20%C2%B7%20D%C3%A9tail%20d%27une%20chambre.png) et
[Web · Tableau de bord gérant](../maquette/Web%20%C2%B7%20Tableau%20de%20bord%20g%C3%A9rant.png).
Les images [Publier une chambre](../maquette/Publier%20une%20chambre.png),
[Conversation](../maquette/Conversation.png), [Mes alertes](../maquette/Mes%20alertes.png),
[Notifications](../maquette/Notifications.png), [Connexion](../maquette/Connexion.png) et
[Profil & vérification](../maquette/Profil%20%26%20v%C3%A9rification.png) apportent des idées de
composants et de parcours ; plusieurs sont des vues mobiles, donc leur navigation basse ne sera pas
copiée dans le WEB.

Les maquettes utilisent principalement un bleu cobalt, alors que le système actuel définit une marque
émeraude et un accent terre cuite dans [docs/design-system.md](design-system.md). **Décision au démarrage
de la phase 1 :** présenter un prototype avec le bleu cobalt des maquettes comme couleur primaire, conserver
vert pour succès/vérification et terre cuite pour accent, puis valider cette évolution avant de modifier les
jetons. Si la palette actuelle est conservée, garder les mêmes compositions et états sans disperser de
couleurs en dur. Dans les deux cas, contrôler contraste AA en clair et sombre.

Les chiffres, noms, badges, durées vidéo, conversation, pièce d'identité et paiements visibles dans les
maquettes sont illustratifs. Utiliser des données de démonstration explicitement identifiées ou les données
réelles du service ; sinon afficher un état vide. Ne jamais inventer des coordonnées de quartier, un avis,
une vérification ou une transaction réelle.

## État de départ vérifié dans le code

Les routes actuelles sont déclarées dans [serveur/web/urls.py](../serveur/web/urls.py). Les adaptateurs
publics et gérant sont [views_public.py](../serveur/web/views_public.py) et
[views_pro.py](../serveur/web/views_pro.py) ; ils appellent déjà les services métier. Le détail exhaustif
du suivi fonctionnel est dans [docs/reste-a-faire.md](reste-a-faire.md) et les réserves techniques dans
[docs/a-verifier.md](a-verifier.md). Le résumé [docs/avancement.md](avancement.md) est en retard sur ces
documents et ne doit pas servir seul à estimer le WEB.

Écarts WEB à traiter, même si l'API ou les services correspondants existent déjà :

| Parcours | Existant | Travail restant à confirmer puis livrer |
|---|---|---|
| Découverte | Accueil/annonces/quartiers, recherche serveur, filtres de base, curseur, carte, fiche, vidéo/photos. | La page d'accueil est essentiellement le catalogue ; le formulaire n'expose pas tous les filtres métier. Repenser navigation, recherche, filtres récapitulés, tri, résultats/erreurs/vides et fiche mobile/desktop. |
| Fiche et contact | Vue publique, favoris, signalement et ouverture de conversation. | Galerie sélectionnable, retour utilisateur et lien vers alerte pertinente ; vérifier chaque CTA et préserver le masquage des contacts. |
| Authentification/compte | Connexion, inscription locataire par OTP, récupération de mot de passe, profil limité. | Parcours de choix de rôle/activation gérant, appareils, changement de numéro et préférences : vérifier la couverture WEB avant de bâtir des formulaires, réutiliser les services disponibles. |
| Espace gérant | Liste et éditeur de brouillon/publication ; transfert média via `envoi.js`. | Pas de tableau de bord WEB dédié. Contrôles média de l'API (ordre, couverture, suppression) à raccorder ou à rendre découvrables ; améliorer les étapes, erreurs, progression et reprise. |
| Alertes/notifications | Création/suppression d'alertes et lecture globale des notifications. | Pause/réactivation/édition et lecture individuelle ne sont pas exposées dans le WEB ; formulaire d'alerte plus limité que le contrat métier. Confirmer services/endpoints avant d'ajouter les commandes. |
| Messagerie | Liste, lecture, envoi, blocage ; rafraîchissement de page toutes les 60 secondes. | Pas de temps réel côté navigateur. Stabiliser d'abord les tests WebSocket serveur, puis décider WebSocket avec rattrapage HTTP ou repli de rafraîchissement accessible. |
| ADM | Hôte, processus et administration Django séparés ; outils de modération existants. | Les maquettes d'administration appellent une vraie interface opérationnelle. Traiter sa refonte dans une phase isolée, sans réduire ses protections. |

## Phases de réalisation

Chaque phase se termine par une revue visuelle réelle sur ordinateur et téléphone, puis une validation du
parcours complet. Après la revue, les défauts visuels et les problèmes d'usage découverts sont inscrits dans
la phase courante avant d'ouvrir la suivante ; le design n'est pas figé après une seule passe.

### 0. Baseline, règles et décisions

- Inventorier routes, formulaires, services, endpoints API, permissions, migrations, états métier et tests
  par parcours ; confirmer la matrice « État de départ » ci-dessus dans le code courant.
- Décider la palette à partir d'un prototype comparatif ; consigner tout changement de marque dans les
  jetons, le guide de design et les tests de contraste. Confirmer que les trois maquettes WEB principales
  sont les références desktop, les écrans mobiles servant uniquement d'inspiration responsive.
- Écrire pour chaque commande visible sa route POST/GET, son service propriétaire, sa permission, son état
  de succès et ses erreurs. Les données affichées viennent de la base et non de valeurs codées en dur.
- **Acceptation :** aucune action UI sans comportement serveur identifié ; aucun conflit de portée WEB,
  ADM et APP ; checklist de parcours et jeux de données de test prêts.

### 1. Fondation visuelle et navigation WEB

- Mettre à niveau le shell partagé : identité, navigation desktop/mobile, liens actifs, compte,
  notifications non lues, retour, pied de page et accès clavier.
- Créer/ajuster des composants réutilisables : contrôles, puces de filtre, badge de statut, carte annonce,
  galerie, barre d'étapes, toast/alerte, confirmation d'action destructive et états vide/chargement/erreur.
- Ajouter les exemples de tous les états dans `/styleguide`. Respecter les jetons et l'assemblage CSS existant.
- **Acceptation :** navigation complète au clavier, focus visible, contraste AA, cibles tactiles d'au moins
  44 px, pas de débordement à 360/390 px et pas d'erreurs console sur les gabarits représentatifs.

### 2. Découverte de chambres

- Transformer l'accueil en entrée de recherche utile et faire du catalogue la page de comparaison :
  recherche, quartier, budget, type, équipements, distance/disponibilité si pris en charge, tri, filtres
  actifs effaçables, pagination par curseur et résultat total uniquement si le serveur le fournit.
- Concevoir cartes photo/vidéo avec durée réelle si disponible, badge gérant vérifié issu du profil,
  loyer FCFA correctement formaté, quartier/repère public et favori connecté. La vidéo ne démarre pas avec
  le son et ne se télécharge pas inutilement avant l'interaction.
- Développer la fiche : galerie clavier/tactile, détail du loyer et frais, disponibilité, caractéristiques,
  gérant vérifié, signaler, ajouter/retirer favori, créer une alerte et contacter dans Logeo.
- **Sécurité :** aucune adresse privée ni numéro de téléphone dans HTML, attributs, métadonnées ou journaux.
- **Acceptation :** tests WEB pour recherche combinée, curseur, annonce inaccessible/louée, favori,
  signalement et redirection connexion/contact ; les valeurs visibles concordent avec les objets persistés.

### 3. Identité, inscription et espace locataire

- Aligner connexion, OTP, inscription, récupération de mot de passe, changement d'informations et
  suppression de compte sur les maquettes sans modifier les règles OTP/authentification du service.
- Construire des messages d'erreur liés aux champs, états d'attente/réessai/expiration du code, retour
  après authentification et protection contre une URL `next` externe.
- Ajouter les commandes WEB réellement supportées pour appareils, préférences et gestion du compte ; si un
  service manque, le créer au niveau métier avec test avant le formulaire.
- **Acceptation :** scénarios invité/client/gérant testés ; OTP visible uniquement dans le dispositif local
  prévu, jamais dans le HTML de production ; sessions, CSRF et déconnexion restent effectifs.

### 4. Espace gérant et publication

- Ajouter un vrai tableau `/pro/dashboard` branché au service/endpoint dashboard existant : annonces par
  statut, vues/favoris/conversations et indicateurs de réponse uniquement quand les données existent.
- Refaire « Mes chambres » comme table desktop et liste mobile, avec statut explicite et commandes autorisées
  (reprendre, modifier, confirmer, masquer, louer, supprimer brouillon).
- Construire un assistant de publication par sections sauvegardables : informations, localisation publique
  et adresse privée, loyer/frais, équipements, description, médias, aperçu, validation et publication.
- Brancher l'API média existante pour progression, annulation, reprise, erreurs, limite de format/taille,
  ordre, couverture et suppression. Ajouter les commandes serveur manquantes avec tests de propriété/quota.
- **Acceptation :** un gérant de test crée un brouillon, le reprend après rechargement, envoie photo/vidéo,
  réordonne et choisit la couverture, voit les erreurs de validation et publie selon les règles métier ; un
  autre gérant ne peut ni lire ni modifier ses ressources.

### 5. Conversations, alertes et notifications

- Refaire la liste et le fil de conversation : annonce associée, dates, auteur, état de lecture, envoi,
  attente, erreur/réessai, blocage et signalement. Chaque envoi garde l'idempotence serveur.
- Avant le temps réel WEB, installer/valider les tests WebSocket omis (dépendance `daphne` à décider via
  ADR conformément aux règles du dépôt, ou stratégie de test équivalente). Si WebSocket est retenu, utiliser
  ticket court, CSRF/session cohérente et rattrapage HTTP par séquence ; maintenir un repli réseau. Depuis cette session, le code serveur des consommateurs est présent, mais aucun navigateur/WebSocket n'a été
  exécuté (12 tests ws ignorés faute de `daphne`) ; Phase 7 (intégration) devra les activer ou documenter
  l'impossibilité.
- Étendre le WEB des alertes aux actions pause/réactiver/modifier/supprimer uniquement après confirmation
  des services et contraintes ; permettre une alerte depuis les filtres et la fiche.
- Notifications : lecture individuelle et « tout lire », regroupement visuel basé sur les notifications
  réelles, liens profonds vers l'annonce/conversation et préférences disponibles.
- **Acceptation :** deux utilisateurs de test échangent via l'interface ; une reconnexion/réessai ne
  duplique pas le message ; la détection de coordonnées garde le comportement `mask`/`flag`/`block` ; les
  alertes et statuts lus persistent après rechargement.

### 6. Administration navigateur (ADM, hôte séparé)

- Réaliser les maquettes `Admin · Vue d'ensemble`, `Admin · Gérants`, `Admin · Modération` et
  `Admin · Journal d'activité` sur le processus et l'hôte admin existants ; garder réglages, rôle DB,
  cookie, secret, 2FA et liste blanche séparés.
- Relier tableaux, filtres, actions et confirmations aux services d'administration/modération et à l'audit.
  L'accès au contenu de conversation doit demander un motif avant affichage et journaliser l'action.
- **Acceptation :** chaque action est autorisée par rôle côté serveur et auditée ; domaine public = 404 sur
  les routes ADM ; accès non autorisé à l'hôte admin reste fermé. Cette phase ne bloque pas la sortie du WEB
  public si la portée initiale exclut ADM, mais bloque la validation d'une refonte ADM complète.

### 7. Intégration, fiabilité et mise en service WEB

- Parcourir les flux sur l'application montée réellement : vue → service → PostgreSQL → réponse HTML/API,
  et uploads WEB → API → stockage → worker média → statut visible. Tester les vraies permissions `app`,
  `admin_app` et rétention, pas seulement le superutilisateur des tests.
- Ajouter des tests navigateur de bout en bout pour : recherche/fiche, connexion et retour, favori/alerte,
  publication et upload, contact/message, notification lue, et modération selon portée. Couvrir les états
  sans données, refus, réseau lent, expiration de session et validation serveur.
- Vérifier à 360, 390, 768, 1024 et 1280 px, clair/sombre, clavier, zoom, réduction de mouvement et lecteurs
  d'écran. Contrôler WCAG AA, liens/actions, erreurs console, médias, CSRF, cookies, CSP et autorisations.
- Mesurer les budgets du cahier des charges sur les pages importantes ; construire CSS et statiques,
  contrôler le manifeste réellement servi par Caddy. Toute modification API est additive, testée,
  régénère OpenAPI avec `make openapi` et met à jour sa documentation.
- **Acceptation finale :** `make fumee`, `make verifier` et tests WEB/E2E ciblés passent sur PostgreSQL et
  Redis ; les tests ignorés et limitations restantes sont explicitement documentés. Vérifier une session
  après redémarrage et une première exécution des tâches planifiées.

## Ordre recommandé et livrable vertical

Commencer par le flux le plus visible et qui valide tôt la chaîne complète :
**catalogue réel → fiche → connexion si nécessaire → contact → conversation persistée**. Puis livrer le
dashboard et la publication gérant, qui valident la chaîne médias ; enfin compléter alertes, notifications
et ADM. À chaque incrément, améliorer une chose visuelle observée sur une capture réelle avant de passer au
suivant ; ne pas repousser les erreurs fonctionnelles au « polish » final.

## Dépendances et blocages à traiter, pas à maquiller

- Les tests WebSocket serveur sont actuellement consignés comme ignorés ; leur activation passe par une
  décision de dépendance documentée ou une autre stratégie de test conforme.
- SMS, Turnstile et push réels ne sont pas tous configurés. En développement, fournir des états simulés
  clairement réservés aux tests ; la sortie production dépend du choix et de la configuration des
  fournisseurs réellement nécessaires.
- La facturation est désactivée et les maquettes Mobile Money ne prouvent pas qu'un fournisseur est prêt.
  Garder l'abonnement indisponible avec un état honnête jusqu'au choix du fournisseur, ADR, contrat signé,
  traitement idempotent et tests de webhook ; ne jamais simuler un paiement réussi.
- Coordonnées des quartiers et du campus : faire valider les données avant de présenter un calcul de
  proximité comme exact.
- Les tests navigateur exigent un navigateur disponible. Prévoir son installation en CI/environnement
  local avant de rendre les captures et tests E2E obligatoires.

## Règle « terminé » pour chaque parcours

Un parcours est terminé seulement lorsque son rendu est validé dans le navigateur, les données viennent du
service correct, les erreurs et états vides sont traités, la permission est vérifiée côté serveur, les
tests unitaires/intégration/navigateur adaptés passent, le comportement clavier/mobile est vérifié, et toute
API/documentation/migration concernée est à jour. Pas de bouton décoratif, de statistiques inventées ni de
succès visuel avant confirmation serveur.