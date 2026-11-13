# L'administration d'Immo+ (pilotage)

Guide de l'équipe : comment entrer, ce que contient chaque page, les gestes courants et **chaque paramètre** avec sa
valeur par défaut. L'administration est un site à part, sur `https://pilotage.immoplus.bj` (en local :
`http://pilotage.localhost:8080`).

## 1. Entrer dans l'administration

1. **Depuis une adresse autorisée seulement.** Toute autre adresse reçoit une erreur 404, comme si le site
   n'existait pas. La liste est `ADMIN_ALLOWED_IPS` dans le fichier `.env` du serveur ; Caddy la vérifie avant même
   que la page ne s'affiche, y compris derrière le Caddy central du VPS partagé.
2. **Adresse e-mail et mot de passe** du compte du personnel.
3. **Code reçu par courriel**, à chaque connexion : 6 chiffres, valable 10 minutes, 5 essais, 3 renvois au plus. S'il
   n'arrive pas, le serveur SMTP n'est pas configuré (guide de déploiement, étape 4.1).
4. Après plusieurs échecs de mot de passe (`ADMIN_LOCK_THRESHOLD`), le compte est bloqué un moment : la page
   **Sécurité** (django-axes) le montre et permet de débloquer.
5. La session se ferme après `ADMIN_SESSION_IDLE_MIN` minutes d'inactivité (60 par défaut), et dans tous les cas
   après `ADMIN_SESSION_MAX_H` heures (8 par défaut).

Un **administrateur** crée les comptes du personnel depuis l'administration : **Comptes › Tous les comptes › Nouveau
personnel** (nom, adresse e-mail réelle, rôle, mot de passe initial et confirmation). Le mot de passe se transmet par
un canal sûr, jamais par e-mail ; l'action est journalisée (`admin.personnel_cree`). Un modérateur n'y a pas accès.

Le **tout premier** compte administrateur, ou un compte quand plus personne ne peut se connecter, se crée en ligne de
commande, sur le serveur :

```bash
immoplus run --rm admin python manage.py creer_personnel --email awa@immoplus.bj --nom "Awa B." --role moderator
```

Le mot de passe est demandé au clavier. `--role admin` pour un administrateur.

## 2. Les deux rôles

| Ce qu'on peut faire | Administrateur | Modérateur |
|---|---|---|
| Signalements : lire, prendre, classer, sanctionner | ✔ | ✔ |
| Annonces : relire, approuver, refuser, masquer | ✔ | ✔ |
| Avis : masquer, réafficher | ✔ | ✔ |
| Types de logement proposés : valider, rattacher | ✔ | ✔ |
| Gérants : consulter | ✔ | ✔ |
| Comptes : statut, suspension, bannissement, liens d'accès | ✔ | |
| Créer un gérant | ✔ | |
| Paramètres, quartiers, abonnements, paiements | ✔ | |
| Journal d'activité, erreurs, connexions échouées, sécurité | ✔ | |

Un modérateur ne peut pas suspendre plus de `MODERATOR_MAX_SUSPENSION_DAYS` jours. Toute action est inscrite dans le
**journal d'activité**, qui ne se modifie ni ne s'efface.

## 3. Le tableau de bord

La page d'accueil réunit :

- **À traiter** : signalements ouverts, annonces en traitement, **nouvelles annonces** (mises en ligne ces 7 jours : un coup d'œil
  même si elles sont déjà visibles ; la liste s'ouvre triée de la plus récente à la plus ancienne), gérants en attente de vérification, types
  de logement proposés. Chaque chiffre mène à la liste concernée.
- **Activité** : inscriptions, annonces publiées, conversations, vues, et un graphe des 14 derniers jours.
- **Téléphones actifs** sur 7 jours (Android, iOS).
- **Gérer** : raccourcis vers les comptes, les statistiques, les annonces, la modération, la configuration, les paiements
  et le journal, et le bouton **Créer un gérant**.

## 4. Les rubriques

### 4.1 Modération

**Signalements.** Envoyés par les utilisateurs (fiche, conversation, profil) ou par la détection automatique.

- États : *Ouvert*, *En cours d'examen*, *Traité : sanction*, *Classé sans suite*.
- Motifs : fausse annonce, déjà louée, prix différent, coordonnées partagées, harcèlement, arnaque, autre.
- Actions de la liste : **Prendre** (passe en examen à ton nom) et **Classer** (sans suite).
- La fiche d'un signalement donne les liens utiles : compte visé, annonce, conversation, et une décision
  pré-remplie. Lire une conversation demande un **motif**, inscrit au journal. Au-delà de
  `STAFF_READS_ALERT_THRESHOLD` lectures par jour, les administrateurs sont alertés.

**Décisions de modération.** Le formulaire « Ajouter » *est* l'outil de sanction : il applique l'action puis la
journalise. Actions : message masqué, message supprimé, annonce masquée, annonce retirée, avertissement, suspension
(avec une date de fin), bannissement, réhabilitation.

### 4.2 Comptes

**Gérants.** Statut de vérification : *En attente*, *Entretien*, *Vérifié*, *Refusé*. Un gérant ne publie qu'une fois
*Vérifié* : c'est ce qui donne le badge « Vérifié » sur ses annonces.

**Comptes** (locataires, gérants, personnel).

- Recherche par nom d'utilisateur, prénom, nom ou e-mail. Immo+ ne conserve aucun numéro de téléphone (ADR 0009).
- Statuts : *Actif*, *Suspendu* (jusqu'à une date), *Banni*, *Supprimé* (anonymisé). Actions de la liste :
  suspendre, réactiver, bannir.
- **Nouveau gérant** (bouton en haut de la liste) : prénom, nom, nom affiché, zone. Aucun mot de passe : la page
  suivante affiche un **lien d'activation** (72 h, une seule fois) à copier, ou à envoyer avec le bouton **Envoyer par
  WhatsApp** (WhatsApp s'ouvre avec le message prêt, tu choisis le contact). Le gérant y choisit son nom d'utilisateur
  et son mot de passe, puis reçoit sa clé de secours.
- Sur la fiche d'un compte, la ligne **Accès au compte** propose :
  - pour un gérant pas encore activé : **Générer un lien d'activation** (si le premier a expiré) ;
  - pour un compte activé : **Générer un lien de réinitialisation** (24 h, une seule fois), le dernier recours du mot
    de passe oublié (section 5.3).

### 4.3 Annonces

**Annonces.** Filtres : statut, raison du masquage (sans confirmation, modération, gérant, gérant suspendu),
quartier. Un gérant **vérifié publie directement**, y compris sa première annonce : elle est en ligne aussitôt et
l'équipe (administrateurs et modérateurs) reçoit un **courriel à la première mise en ligne** de chaque annonce
(`EMAIL_NOUVELLES_ANNONCES`), avec les liens pour la voir et la modérer. La modération agit après coup : **Masquer**
l'annonce, ou **Refuser** (l'annonce passe masquée, raison « Modération » ; le gérant la voit masquée dans son espace).
Les annonces encore « en traitement » (médias en cours) sont publiées toutes seules quand leurs médias sont prêts.

**Masquer ou retirer une annonce** (administrateurs **et** modérateurs) : dans la liste, cochez une ou plusieurs annonces puis
choisissez l'action :

- **Masquer (modération)** : l'annonce quitte le site ; le gérant peut la corriger. **Remettre en ligne (annonce masquée par la
  modération)** annule le masquage (si l'annonce est encore publiable).
- **Retirer (modération)** : retrait **définitif** (fausse annonce, arnaque, contenu interdit) ; le gérant ne peut ni la modifier ni la
  remettre en ligne.

Une page demande un **motif obligatoire** (10 caractères au moins) : le gérant le reçoit en notification, et la décision est
journalisée dans « Actions de modération » et dans le journal d'activité. Les mêmes décisions existent depuis un signalement.
Une chambre **marquée louée** est archivée aussitôt, photos et vidéo supprimées.

**Avis.** Publiés tout de suite. Actions **Masquer** (l'avis disparaît du public, l'auteur le garde) et
**Réafficher**.

**Types de logement.** Les gérants peuvent proposer un type absent de la liste. Action **Valider** (le type rejoint
la liste officielle) ou **rattacher** la proposition à un type existant depuis sa fiche : les annonces et alertes qui
la portent sont réécrites.

**Quartiers.** Nom, position, ordre d'affichage, actif ou non. Un quartier inactif disparaît des listes mais garde ses
annonces.

### 4.4 Sécurité (django-axes)

Tentatives de connexion à **l'administration** : tentatives en cours, échecs, journal des accès. C'est ici qu'on
débloque un membre du personnel.

### 4.5 Pages réservées aux administrateurs

- **Connexions échouées** (`/connexions-echouees/`) : échecs de connexion des locataires et gérants, sur le site et
  dans l'application. Nom d'utilisateur saisi, compte existant ou non, provenance, adresse IP. Un même nom en
  rafale = tentative de deviner un mot de passe ; le verrouillage automatique (paramètres de la section Sécurité)
  s'en charge.
- **Erreurs** (`/erreurs/`) : erreurs du serveur regroupées, avec leur nombre et leur détail ; bouton **Corrigée**.
  Un courriel part vers `ERREURS_DESTINATAIRES` à la première apparition, puis au plus une fois par heure.
- **Journal d'activité** : tout ce que fait le personnel et tous les événements sensibles (inscriptions,
  réinitialisations avec la porte utilisée, liens générés, sanctions, paramètres modifiés avec l'ancienne et la
  nouvelle valeur). Lecture seule.

### 4.6 Paiements (désactivés par défaut)

**Abonnements** et **Paiements** (ancien circuit Mobile Money) en lecture seule, et **Transactions KKiaPay** : chaque
paiement fait par la fenêtre KKiaPay du site (abonnement d'un gérant, alerte d'un locataire) ou noté à la main pour un
paiement en espèces (référence `especes-…`). Rien n'est facturé tant que les cases de la section « Paiements (KKiaPay) »
des paramètres sont décochées (section 8 et « Paiements : activer pour les locataires ou pour les gérants »).

### 4.7 Statistiques

La page **Statistiques** (`/statistiques/`, lien dans « Comptes » de l'accueil) donne :

- les **chiffres clés** : gérants actifs et vérifiés, locataires actifs, nouveaux comptes (30 jours), annonces en ligne,
  chambres louées, conversations (30 jours), alertes actives, abonnements payants en cours, paiements réussis, total
  encaissé et encaissé sur 30 jours ;
- un **tableau par gérant** (zone, vérifié, annonces en ligne et au total, conversations, note et avis, formule, date de
  fin) et un **tableau par locataire** (inscription, dernière activité, conversations, favoris, alertes actives, total
  payé), les 100 plus actifs ;
- sur la **fiche d'un compte ou d'un gérant**, un bloc « Statistiques » détaillé (annonces par état, vues et favoris sur
  30 jours, taux et délai de réponse, avis, abonnement et paiements ; pour un locataire : conversations, favoris, alertes,
  avis donnés, paiements).

## 5. Gestes courants

### 5.1 Ajouter un gérant

1. Entretien avec le gérant (identité, activité).
2. Comptes › **Nouveau gérant** › prénom, nom, zone › **Créer**.
3. Envoie le lien affiché (bouton WhatsApp ou copie). Préviens-le qu'il est valable 72 heures.
4. Le compte créé par l'équipe est **déjà vérifié** (l'entretien a eu lieu avant) : le gérant publie dès qu'il a activé
   son compte, sans second geste de votre part. Il apparaît aussi dans la page **Statistiques**.

### 5.2 Contrôler une annonce après sa mise en ligne

Le courriel « Immo+ · nouvelle annonce » (envoyé à tous les administrateurs et modérateurs actifs qui ont une adresse)
donne le lien public et le lien de modération. Ouvre l'annonce : si elle pose problème, **Masquer** ou **Refuser**, puis
explique la raison au gérant (WhatsApp ou téléphone de l'équipe) pour qu'il corrige et republie. Les annonces
« En traitement » sont des annonces dont les médias ne sont pas encore prêts ; elles se publient seules.

### 5.3 Un utilisateur a perdu l'accès à son compte

Il doit d'abord essayer seul : **lien par e-mail** (s'il a confirmé une adresse), puis **clé de secours**. S'il n'a
ni l'un ni l'autre et t'écrit :

1. **Vérifie que c'est bien lui.** Immo+ ne garde aucun numéro : pose des questions que seul le titulaire connaît
   (date approximative d'inscription, quartiers de ses alertes, annonces en favori, gérants avec qui il a discuté,
   pour un gérant ses annonces). Dans le doute, refuse.
2. Comptes › sa fiche › **Générer un lien de réinitialisation**. Envoie-le par le canal où il t'a écrit.
3. Le lien vaut 24 heures et une seule fois ; toutes ses sessions sont coupées quand il change son mot de passe.
   Conseille-lui d'ajouter un e-mail et de garder sa nouvelle clé de secours.

### 5.4 Traiter un signalement

Signalements › **Prendre** › ouvre la fiche › consulte annonce, compte ou conversation (motif demandé) ›
Décisions de modération › **Ajouter** la sanction adaptée, ou **Classer** sans suite.

### 5.5 Mettre l'application en maintenance

Paramètres › Application et maintenance › coche `MAINTENANCE_ENABLED`, écris `MAINTENANCE_MESSAGE` (« Retour vers
14 h ») › Enregistrer. L'application affiche l'écran de maintenance ; le site reste ouvert. Décoche après la mise à
jour.

### 5.6 Obliger les utilisateurs à mettre l'application à jour

Une fois la nouvelle version **publiée sur les magasins** : Paramètres › `MIN_SUPPORTED_VERSION` = la nouvelle
version (ex. `1.2.0`).

### 5.7 Changer les conditions d'utilisation

Après avoir modifié les textes (`serveur/apps/core/textes_legaux/`) et déployé : Paramètres › `TERMS_VERSION` + 1 et
`LEGAL_UPDATED_AT` = la date. Chacun devra accepter les nouvelles conditions à sa prochaine connexion.

### 5.8 Ranger les photos et vidéos chez Cloudinary (ou revenir au disque)

Par défaut, les médias sont sur le disque du VPS. Cloudinary (gratuit jusqu'à 25 « crédits » par mois, soit environ
25 Go de stockage et de bande passante cumulés) soulage le disque et la connexion du serveur, surtout pour les
vidéos : elles partent alors d'un réseau de diffusion mondial.

1. **Une seule fois, sur le serveur** : renseigner `CLOUDINARY_CLOUD_NAME`, `CLOUDINARY_API_KEY` et
   `CLOUDINARY_API_SECRET` dans `.env` (cloudinary.com › Settings › API Keys), puis
   `python3 outils/creer_env.py --services` et `bash infra/vps/deployer.sh` (guide de déploiement, étape 4.5).
2. **Ici** : Paramètres › **Photos et vidéos** › choisir « Cloudinary » › Enregistrer. Sans l'étape 1, la page
   refuse avec un message clair.
3. Dès lors, chaque **nouvelle** photo ou vidéo est préparée sur le serveur (tailles, métadonnées EXIF retirées, WebP,
   MP4) puis envoyée chez Cloudinary par le worker ; la copie locale est effacée. Si Cloudinary ne répond pas, le
   worker réessaie quatre fois (1, 2, 4, 8 minutes) avant de marquer le média en échec et de prévenir le gérant.
4. Les médias **déjà en ligne restent sur le disque** et continuent de s'afficher. Pour les déplacer aussi :

   ```bash
   immoplus run --rm worker python manage.py transferer_medias --vers cloudinary --limite 20   # essai
   immoplus run --rm worker python manage.py transferer_medias --vers cloudinary              # le reste
   ```

**Revenir au disque** : choisir « Disque du serveur » ici (effet sur les nouveaux médias), puis, pour rapatrier
l'existant, `transferer_medias --vers disque`. Ne retire **jamais** les clés Cloudinary de `.env` tant que des
médias y sont rangés : leurs adresses ne fonctionneraient plus. Les médias chez Cloudinary ne sont pas dans la
sauvegarde du serveur (Cloudinary en garde ses propres copies).

### 5.9 Jour de forte affluence : « Trop de requêtes »

Chaque compte connecté a son propre compteur de requêtes. Les visiteurs **non connectés**, eux, sont comptés par
adresse IP, et beaucoup partagent la même (abonnés d'un même opérateur mobile, Wi-Fi du campus). Si des visiteurs
signalent « Trop de requêtes » lors d'un lancement ou d'une rentrée : Paramètres › **Sécurité** › monter
`RATE_IP_FACTOR` (ex. 3 → 6) et, pour les connexions et inscriptions, `AUTH_RATE_PER_MIN_IP` (ex. 60 → 120). Effet
en 30 secondes ; redescendre ensuite. Capacité générale du serveur : `docs/capacite.md`.

## 6. Tous les paramètres

Page **Paramètres** : chaque réglage a un champ adapté (case à cocher, nombre, liste) et la note ci-dessous sous son
champ. Un enregistrement prend effet tout de suite (cache vidé) et est inscrit au journal avec l'ancienne et la
nouvelle valeur. Les valeurs par défaut sont posées par `manage.py seed`.

Ce qui ne se règle **pas** ici, mais dans `.env` sur le serveur : domaine, adresses autorisées de l'administration,
clés Turnstile, courriels (SMTP), notifications push, sauvegardes, compte Cloudinary, nombre de processus
(`WEB_CONCURRENCY`) (guide de déploiement, étape 6).

### Application et maintenance

Ce que voient les applications au démarrage.

| Paramètre | Par défaut | À quoi il sert |
|---|---|---|
| `MAINTENANCE_ENABLED` | décoché | Coché : l'application mobile affiche un écran de maintenance au lieu de fonctionner. Le site reste ouvert. À utiliser pendant une mise à jour du serveur. |
| `MAINTENANCE_MESSAGE` | vide | Texte de l'écran de maintenance (ex. « Retour vers 14 h »). Vide : message standard. |
| `APP_NOTICE` | vide | Petit message affiché en haut de l'application pour tous (ex. une nouveauté). Vide : rien n'est affiché. |
| `MIN_SUPPORTED_VERSION` | `1.0.0` | Les applications plus anciennes que cette version doivent se mettre à jour avant de continuer. Format 1.2.0. À monter seulement après publication de la nouvelle version sur les magasins. |

### Contact et identité légale

Affichés sur le site, dans l'app et dans les textes légaux.

| Paramètre | Par défaut | À quoi il sert |
|---|---|---|
| `TEAM_PHONE` | `+2290160239288` | Numéro affiché partout pour joindre l'équipe (appel et WhatsApp). Format international : +229… |
| `LEGAL_PROVISIONAL` | coché | Coché : un bandeau prévient que les mentions légales sont provisoires. À décocher quand l'entreprise est réellement immatriculée et les champs ci-dessous exacts. |
| `LEGAL_COMPANY` | `IMMOPLUS SARL` | Nom officiel de la société qui édite Immo+, repris dans les conditions et la confidentialité. |
| `LEGAL_RCCM` | `RB/PKO/26 B 00001` | Numéro d'immatriculation au registre du commerce (RCCM). |
| `LEGAL_IFU` | `3202600000001` | Identifiant fiscal unique (IFU) de la société. |
| `LEGAL_ADDRESS` | `Banikanni, Parakou, République du Bénin` | Adresse du siège, affichée dans les textes légaux. |
| `LEGAL_EMAIL` | `contact@immoplus.bj` | Adresse où écrire pour une question légale ou sur ses données personnelles. |
| `LEGAL_UPDATED_AT` | `2026-10-17` | Date « mise à jour le » des textes légaux. Format AAAA-MM-JJ. |
| `TERMS_VERSION` | `1` | Changer ce numéro oblige chaque utilisateur à accepter de nouveau les conditions à sa prochaine connexion. Ne le modifier que si les conditions ont réellement changé. |

### Annonces

Publication, fraîcheur et cycle de vie des chambres.

| Paramètre | Par défaut | À quoi il sert |
|---|---|---|
| `LISTING_PREMODERATION` | décoché | **Sans effet pour l'instant** (la relecture préalable a été retirée : un gérant vérifié publie directement et l'équipe est prévenue par courriel). Gardé pour une éventuelle réactivation. |
| `EMAIL_NOUVELLES_ANNONCES` | coché | Coché : à la première mise en ligne d'une annonce, un courriel part à l'équipe (administrateurs et modérateurs). |
| `STALE_REMINDER_DAYS` | `[7, 10]` | Liste de jours sans confirmation après lesquels le gérant reçoit un rappel, ex. [7, 10]. Utilisé seulement si le masquage automatique ci-dessous est actif. |
| `STALE_HIDE_DAYS` | `0` | Nombre de jours sans confirmation avant que l'annonce soit masquée automatiquement. 0 = jamais (recommandé : le gérant marque lui-même une chambre louée). |
| `RENTED_REPORTS_THRESHOLD` | `3` | Nombre de locataires différents qui signalent « déjà louée » avant qu'un dossier s'ouvre dans la modération. |
| `RENTED_VIDEO_DELETE_DAYS` | `7` | **Inutilisé** : dès qu'une chambre est marquée louée, photos et vidéo sont supprimées et l'annonce archivée. |
| `READONLY_AFTER_RENT_DAYS` | `30` | Après « louée », les conversations de la chambre passent en lecture seule au bout de ce nombre de jours. |
| `ARCHIVE_AFTER_RENT_DAYS` | `90` | Ne concerne plus que les annonces marquées louées avant la mise à jour : une annonce marquée louée est désormais archivée aussitôt. |
| `CAMPUS_REFERENCE` | `{"latitude": 9.337, "longitude": 2.6303}` | Position de l'Université de Parakou qui sert à calculer « à 450 m de l'UP ». Format {"latitude": 9.337, "longitude": 2.630}. |

### Messagerie, alertes et notifications

Limites d'envoi et protection des coordonnées.

| Paramètre | Par défaut | À quoi il sert |
|---|---|---|
| `CONTACT_LEAK_MODE` | `off` | Que faire d'un numéro ou d'un lien écrit dans la messagerie : laisser passer, le masquer, prévenir la modération ou bloquer le message. Les annonces refusent toujours les coordonnées. Choix : `off` = Aucun filtrage : numéros et liens s'échangent librement ; `mask` = Masquer les coordonnées ; `flag` = Signaler à la modération ; `block` = Bloquer le message. |
| `MESSAGE_PER_MINUTE` | `30` | Nombre maximum de messages qu'une personne peut envoyer par minute (contre les envois en masse). |
| `NEW_CONVERSATIONS_PER_DAY` | `20` | Nombre maximum de nouveaux gérants qu'un locataire peut contacter par jour. |
| `ALERTS_MAX_PER_USER` | `5` | Nombre maximum d'alertes actives par locataire. |
| `UNANSWERED_REMINDER_H` | `2` | Un gérant qui n'a pas lu un message reçoit un rappel après ce nombre d'heures. |

### Sécurité

Verrouillages et défi anti-robot.

| Paramètre | Par défaut | À quoi il sert |
|---|---|---|
| `LOGIN_LOCK_THRESHOLD` | `5` | Nombre de mauvais mots de passe d'affilée avant de bloquer temporairement la connexion (site et application). |
| `LOGIN_LOCK_MINUTES` | `15` | Durée du premier blocage, en minutes ; elle double à chaque nouveau blocage du même compte. |
| `LOGIN_FAILS_PER_HOUR_PER_PHONE` | `30` | Plafond d'échecs par heure pour un même nom d'utilisateur, tous appareils confondus (contre les attaques réparties). |
| `RATE_IP_FACTOR` | `3` | Les visiteurs non connectés sont comptés par adresse IP ; or des centaines d'abonnés mobiles ou d'étudiants du campus partagent souvent la même. Plafonds anonymes par minute et par adresse = 60 (pages publiques) ou 240 (fil) × ce nombre. Les comptes connectés ont chacun leur propre compteur. À monter un jour de forte affluence si des visiteurs voient « Trop de requêtes ». |
| `AUTH_RATE_PER_MIN_IP` | `60` | Connexions, inscriptions et rafraîchissements de session acceptés par minute depuis une même adresse IP (un campus entier peut en partager une). Chaque compte garde son propre verrouillage après des mots de passe faux. |
| `TURNSTILE_ENABLED` | décoché | Coché : le défi anti-robot (Cloudflare Turnstile) protège l'inscription et le mot de passe oublié sur le site. Décoché (réglage au lancement) : aucun défi et le widget n'est pas chargé ; seules les limites de débit freinent les robots. À cocher quand les vraies clés Cloudflare sont dans `.env`. |
| `ADMIN_LOCK_THRESHOLD` | `5` | Nombre de mauvais mots de passe avant le blocage d'un compte de l'administration. |
| `ADMIN_SESSION_IDLE_MIN` | `60` | Sans activité pendant ce nombre de minutes, la session de l'administration se ferme. |
| `ADMIN_SESSION_MAX_H` | `8` | Une session de l'administration se ferme au bout de ce nombre d'heures, même active. |

### Photos et vidéos

Où sont rangés les médias des annonces.

| Paramètre | Par défaut | À quoi il sert |
|---|---|---|
| `MEDIA_STORAGE` | `local` | S'applique aux photos et vidéos envoyées après l'enregistrement ; celles déjà en ligne restent où elles sont (commande transferer_medias pour les déplacer). Cloudinary exige le compte dans .env (CLOUDINARY_*, voir docs/administration.md). Choix : `local` = Disque du serveur (VPS) ; `cloudinary` = Cloudinary. |

### Modération

Garde-fous du personnel.

| Paramètre | Par défaut | À quoi il sert |
|---|---|---|
| `STAFF_READS_ALERT_THRESHOLD` | `20` | Si un membre du personnel ouvre plus de conversations que ce nombre dans la journée, une alerte est levée (protection de la vie privée). |
| `MODERATOR_MAX_SUSPENSION_DAYS` | `30` | Durée maximale d'une suspension décidée par un modérateur ; au-delà, il faut un administrateur. |

### Paiements (KKiaPay, désactivés par défaut)

Éteints par défaut : cochez pour faire payer les gérants (abonnement) et/ou les locataires (alertes). Les deux cases sont
indépendantes.

| Paramètre | Par défaut | À quoi il sert |
|---|---|---|
| `SUBSCRIPTION_ENABLED` | décoché | Coché : les gérants doivent payer un abonnement pour publier (leurs annonces déjà en ligne restent visibles). Décoché : tout est gratuit. |
| `SUBSCRIPTION_GRACE_DAYS` | `7` | Jours pendant lesquels un gérant garde ses annonces en ligne après la fin de son abonnement. |
| `PLANS` | `[{"code": "free_v1", "label": "Gratuit V1", "price": 0, "period_months": 1, "max_active_listings": null, "active": true}, {"code": "standard", "label": "Standard", "price": null, "period_months": 1, "max_active_listings": null, "active": false}]` | Liste des formules d'abonnement (code, nom, prix en FCFA, durée). Ne sert qu'une fois l'abonnement activé. |
| `PAID_ALERTS_ENABLED` | décoché | Coché : un locataire paie une fois chaque nouvelle alerte (prix ci-dessous). Les alertes déjà créées continuent de fonctionner. Décoché : alertes gratuites. |
| `ALERT_PRICE` | `500` | Prix d'une alerte en FCFA. |

## Supprimer des comptes

Dans **Comptes**, cochez un ou plusieurs comptes (confirmés ou non), puis choisissez l'action **Supprimer (anonymise le compte)**. Une page de confirmation liste les comptes concernés. À la validation, chaque compte est anonymisé : nom, adresse e-mail, nom d'utilisateur et clé de secours effacés, appareils déconnectés, annonces en ligne retirées ; l'adresse e-mail redevient libre. Les messages et le journal restent, sans nom. L'action est inscrite au journal (`compte.supprime`, `par_equipe`). Un administrateur ne se supprime pas lui-même et ne supprime pas un autre administrateur (changer d'abord son rôle).

## Paiements : activer pour les locataires ou pour les gérants

Les deux paiements s'activent séparément dans **Paramètres › Paiements (KKiaPay)** :

- `PAID_ALERTS_ENABLED` : les **locataires** paient chaque nouvelle alerte (`ALERT_PRICE`).
- `SUBSCRIPTION_ENABLED` : les **gérants** paient un abonnement pour publier (formules dans `PLANS`).

Vous pouvez donc commencer par les locataires seuls, puis cocher les gérants plus tard (ou l'inverse).

### Gérant qui paie en espèces

Dans **Gérants**, cochez le ou les gérants, choisissez l'action **Activer un abonnement (paiement en espèces)**, puis la formule et le
nombre de périodes payées. La période s'ajoute à celle en cours ; l'opération apparaît dans **Transactions KKiaPay** (référence
`especes-…`) et dans le journal. Réservé aux administrateurs. Fonctionne même si `SUBSCRIPTION_ENABLED` est encore décoché.

### Ce que voit chaque personne quand un paiement est activé

- **Locataire** : il choisit les options de son alerte puis clique sur « Créer l'alerte » ; la fenêtre KKiaPay s'ouvre, et
  l'alerte se crée toute seule après le paiement. Il faut une **adresse e-mail confirmée** (sinon ni création, ni paiement).
  Un paiement vaut une alerte ; supprimer l'alerte ne rend pas le paiement.
- **Gérant** : sans abonnement payant en cours, « Publier une chambre » mène à la page des formules
  (`/compte/abonnement`) avec un message aimable ; ses annonces déjà en ligne restent visibles. Le plan « Gratuit V1 » ne
  suffit plus.
- **Les deux** : la page **Abonnement** (menu et profil) montre la formule, la date de fin et l'historique des paiements.
- **Suppression de compte** : une page de confirmation prévient que l'abonnement payé (ou les alertes payées non créées) est
  perdu, sans remboursement ni récupération ; une case à cocher est obligatoire.

### Mise en service de KKiaPay

Variables du fichier `.env` du serveur (puis `python3 outils/creer_env.py --services` et un déploiement) :

| Variable | Origine | Rôle |
|---|---|---|
| `KKIAPAY_PUBLIC_KEY` | clé publique du tableau de bord KKiaPay | ouvre la fenêtre de paiement |
| `KKIAPAY_PRIVATE_KEY` | clé privée du tableau de bord | vérifie les transactions côté serveur |
| `KKIAPAY_SECRET` | clé secrète du tableau de bord | envoyée avec chaque vérification |
| `KKIAPAY_WEBHOOK_SECRET` | inventée (`python3 -c "import secrets; print(secrets.token_urlsafe(32))"`) | « hash secret » du webhook |
| `KKIAPAY_SANDBOX` | `true` pour tester, `false` en réel | choisit l'adresse de test ou de production |

Dans le tableau de bord KKiaPay, créer un **webhook** vers `https://www.<domaine>/paiement/webhook/kkiapay` avec le même
« hash secret » et les événements `transaction.success` et `transaction.failed` (l'adresse ne doit pas rediriger : une
redirection compte comme un échec). Le webhook rattrape un paiement dont le navigateur s'est fermé avant la confirmation ;
le serveur revérifie toujours la transaction auprès de KKiaPay. Ensuite : fixer le prix de la formule « standard » dans
`PLANS` (prix et `"active": true`, `free_v1` reste à `"price": 0`), puis cocher `PAID_ALERTS_ENABLED` et/ou
`SUBSCRIPTION_ENABLED`. Tester d'abord en `KKIAPAY_SANDBOX=true`.

