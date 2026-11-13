# Avancement

> **À jour :** la plateforme (comptes, annonces, médias, fil, messagerie, notifications, modération, administration, paiements KKiaPay) est construite et **tourne en production** sur le VPS. Voir `docs/reste-a-faire.md` (état et reste à faire), `docs/a-verifier.md` (section D : ce qui est à confirmer) et `docs/decisions.md` (décisions de novembre 2026). Les entrées ci-dessous vont du plus récent au plus ancien ; les plus anciennes décrivent la phase 0.

**2026-11-25 : messages entre l'équipe et les utilisateurs.**
- Administrateurs et modérateurs écrivent à un locataire ou à un gérant (réponse à une question, à un avis, suite à une décision de
  modération) et lisent leurs questions : boîte « Messages de l'équipe », tuile « Messages à traiter », actions depuis les avis, les
  signalements et les comptes. Côté utilisateur : page « Équipe Immo+ » (fil, écrire à l'équipe, 5 par 24 h), notification et courriel.
  Table `team_messages` (migration moderation 0006). Pas dans l'API ni dans l'application mobile.

**2026-11-24 : rappels, résumé hebdomadaire, réponse aux avis, suppression des comptes de test.**
- Rappel de fin d'abonnement : notification et courriel au gérant, 7 jours puis 1 jour avant (`SUBSCRIPTION_REMINDER_DAYS`), une fois par étape.
- Résumé hebdomadaire par courriel à l'équipe (lundi 7 h) : nouvelles annonces, signalements ouverts, paiements (`EMAIL_RESUME_HEBDOMADAIRE`).
- Réponse publique du gérant à un avis (page « Avis reçus », migration 0014) ; l'auteur est prévenu ; visible sur la fiche et le profil public.
- Commande `supprimer_comptes_test` (service `migrer`) : suppression définitive en cascade, journal du compte effacé sauf une ligne de trace
  sans donnée personnelle ; simulation par défaut. Décision : les lignes du journal d'un compte de test sont effacées (voir `administration.md`).

**2026-11-23 : l'administrateur a la main sur tout.**
- Audit des pouvoirs de l'administrateur (tableau « Les deux rôles » de `docs/administration.md`) et ajout de ce qui manquait :
  ajouter et supprimer des types de logement, corriger / rétablir / marquer louée / supprimer une annonce, supprimer un avis,
  déconnecter un compte partout, passer le personnel modérateur ↔ administrateur, prolonger ou terminer un abonnement, marquer un
  paiement remboursé. Page de confirmation commune (`admin/confirmer-action.html`). Restent impossibles volontairement : modifier
  le journal, supprimer physiquement un compte, changer le rôle d'un gérant ou d'un locataire.
- Corrigé : « Types de logement » n'avait pas de bouton « Ajouter » (réservé aux propositions des gérants).

**2026-11-22 : masquer ou retirer une annonce depuis la liste.**
- Administrateurs et modérateurs : actions « Masquer », « Retirer » (définitif) et « Remettre en ligne » (masquage de modération)
  sur la liste des annonces, avec motif obligatoire, notification au gérant et journal (`adminsite/admin_moderation.py`).
- Accueil de l'administration : carte « Nouvelles annonces » (7 derniers jours), liste triée par mise en ligne.

**2026-11-21 : documentation remise à jour.**
- Mis à jour pour refléter l'état réel : `administration.md` (publication directe, page Statistiques, paiements et mise en service de
  KKiaPay, paramètres), `cahier-des-charges.md` (EF-ANN-11 et 13, EF-ABO-02 à 07, table `transactions`, cycle de vie, annexes),
  `comprendre-immoplus.md` (modèle économique, annonces, médias, paiements, notifications, statistiques, cache statique),
  `reste-a-faire.md`, `a-verifier.md` (section D), `decisions.md`, `code-mort.md`, `tuto-compte-gerant.md`,
  `web-parcours.md`, `deploiement-vps-pas-a-pas.md` (variables KKiaPay, plages d'adresses, pièges de `creer_env.py`).
- Pièges rencontrés depuis le premier jour de production (à connaître) :
  - `/static/` est en cache d'un an chez Caddy : sans empreinte dans l'adresse, un script corrigé n'arrivait pas aux navigateurs
    (corrigé, `config/stockage.py`) ;
  - `creer_env.py --services` ne complète pas `.env` (il lit `.env`) et réécrit `caddy.env` et `admin.env` : revérifier
    `ADMIN_ALLOWED_IPS` ensuite ;
  - toute variable **obligatoire** ajoutée aux réglages « public » doit figurer dans les gabarits de **tous** les services Python
    (`web-api`, `realtime`, `worker`, `admin`), sinon un service redémarre en boucle (arrivé avec `LIENS_SIGNING_KEY`) ;
  - un `{# ... #}` de gabarit Django ne peut pas s'étendre sur plusieurs lignes (il s'affiche tel quel) : utiliser `{% comment %}` ;
  - les contrats `lint-imports` interdisent d'importer les modèles d'une autre application : passer par ses sélecteurs ;
  - la CI ne démarre que si une pull request est ouverte.

**2026-11-20 : statistiques en page dédiée, parcours du gérant.**
- Administration : page « Statistiques » (`/statistiques/`, lien dans « Comptes ») : chiffres clés, tableau par gérant (annonces,
  conversations, note, formule) et par locataire (conversations, favoris, alertes, total payé).
- Après connexion, un gérant arrive sur son tableau de bord (plus sur le profil). Après « Marquer louée » depuis l'éditeur, retour
  sur « Mes annonces » (plus sur l'étape 7).

**2026-11-19 : suppression de compte, gérant parti, statistiques.**
- Suppression sur le site en deux temps : mot de passe, puis page de confirmation (`/compte/supprimer`) qui dit ce qui est
  perdu : abonnement payé en cours (« ni remboursé, ni transférable, ni récupérable », case à cocher obligatoire), alertes
  payées non créées, annonces en ligne. L'API mobile reste en une étape.
- Profil public d'un gérant supprimé : page « Ce gérant n'est plus sur Immo+ » (410) au lieu de « page introuvable ».
- Administration : fiche d'un gérant et d'un locataire avec leurs statistiques (annonces, audience, réputation, abonnement et
  paiements ; conversations, favoris, alertes, avis, paiements) : `adminsite/statistiques.py`.
- Profil : les navigateurs ne remplissent plus les mots de passe (`new-password`) ; seule la connexion l'autorise.
- Correction des règles d'import : `billing` passe par les sélecteurs de `accounts` (plus d'import de ses modèles).

**2026-11-18 : scripts à jour chez tous, médias sans rechargement.**
- Cause racine : Caddy sert `/static/` avec `Cache-Control: immutable` pendant un an et les fichiers n'avaient pas de version :
  un navigateur qui avait déjà chargé `paiement.js` ou `envoi.js` gardait l'ancienne copie (le paiement de l'alerte ne s'ouvrait
  pas, l'ancien rechargement automatique des médias persistait). Les adresses portent maintenant `?v=<empreinte>`
  (`config/stockage.py`) : toute modification d'un script ou d'une feuille de style atteint les navigateurs au déploiement.
- Étape médias : plus de rechargement de page. Le navigateur relit la page (GET) et remplace seulement le récapitulatif, les
  vignettes, « Suivant » et l'étape Publication ; la zone d'envoi n'est jamais touchée. Les actions de l'éditeur (enregistrer,
  médias, statut) répondent par une redirection : plus de « renvoyer les données ».

**2026-11-17 : chambre louée, avis liés au gérant.**
- Chambre marquée louée : photos et vidéo supprimées aussitôt (fichiers compris) et annonce archivée (plus d'attente de 7 ou
  90 jours). La fiche reste ouverte pour dire « louée » et renvoyer vers les chambres libres ; « Reproposer » repart d'un
  brouillon (il faut de nouvelles photos). Confirmation demandée avant de marquer louée (action irréversible pour les médias).
- Avis : liés au gérant en plus de la chambre (`Review.gerant`, migration 0013, rattrapage des avis existants). La note du gérant ne
  dépend plus de la vie de chaque annonce ; un locataire peut encore noter une chambre louée.
- Les chambres libres passent avant les louées (favoris) ; « dernières chambres consultées » n'affiche que des chambres libres.

**2026-11-16 : paiements KKiaPay (éteints par défaut).**
- Fenêtre de paiement KKiaPay sur le site ; le serveur vérifie chaque transaction avec la clé privée (statut réussi, montant,
  identifiant jamais réutilisé) : `apps/billing/transactions.py`, table `transactions`, visible dans l'administration.
- Gérants : `SUBSCRIPTION_ENABLED` coché → le plan Gratuit ne suffit plus pour créer ou publier ; page `/pro/abonnement`
  (formules de `PLANS`). Les annonces déjà en ligne restent visibles.
- Locataires : `PAID_ALERTS_ENABLED` coché → chaque nouvelle alerte se paie une fois (`ALERT_PRICE`, réglable). Un paiement
  = un crédit ; supprimer l'alerte ne le rend pas. L'API mobile répond 402 `payment_required` (paiement sur le site).
- Parcours : locataire = options choisies, puis paiement au clic sur « Créer l'alerte » (le formulaire part après paiement) ;
  pas d'alerte sans e-mail confirmé. Gérant sans abonnement (paiement actif) : « Publier une chambre » mène à la page des
  formules avec un message aimable. Page `/compte/abonnement` (formule, dates, historique) pour les deux rôles, lien « Abonnement »
  dans le menu et le profil, bandeaux avec bouton partout où l'abonnement est demandé.
- Variables `.env` : `KKIAPAY_PUBLIC_KEY`, `KKIAPAY_PRIVATE_KEY`, `KKIAPAY_SECRET` (clé secrète API), `KKIAPAY_WEBHOOK_SECRET` (hash secret inventé), `KKIAPAY_SANDBOX` ; la CSP autorise `*.kkiapay.me`.
- Webhook KKiaPay : `POST /paiement/webhook/kkiapay`, authentifié par l'en-tête `x-kkiapay-secret` (= `KKIAPAY_WEBHOOK_SECRET`,
  aussi saisi comme « hash secret » dans le tableau de bord KKiaPay). Le corps n'est pas cru : le serveur revérifie la
  transaction auprès de KKiaPay. Il rattrape un paiement dont le navigateur s'est fermé, et KKiaPay réessaie 5 fois si le
  serveur répond autre chose que 2xx. L'association se fait par `stateData` (notre référence) : forme à confirmer en sandbox.

**2026-11-15 : publication directe, courriels habillés.**
- Un gérant vérifié publie en direct, y compris sa première annonce (plus de relecture préalable) ; administrateurs et
  modérateurs reçoivent un courriel à chaque première mise en ligne. Les annonces déjà « en relecture » restent
  approuvables depuis l'administration.
- Après « Publier », retour sur « Mes annonces » avec un message, plus sur l'étape des médias.
- Tous les courriels partent aussi en HTML (bandeau bleu Immo+, boutons), le texte brut est conservé.
- Correctif : un commentaire de gabarit sur plusieurs lignes s'affichait sous le champ « Disponible à partir du ».

**2026-11-14 : retours du premier jour de production (annonces, médias, notifications).**
- Caution du loyer retirée du formulaire et de la fiche du site (reste en base et dans l'API, à 0 par défaut) ; l'application
  mobile la demande encore (`AnnonceModifierScreen`, `InfosStep`) : à retirer avec une nouvelle version de l'application.
- Étape « Vidéo et photos » : « Suivant » grisé pendant l'envoi et le traitement, ou s'il manque des photos ; plus de
  rechargement toutes les 8 s (suivi par l'API, un seul rechargement à la fin).
- Vidéos : copie du flux si déjà en H.264 720p, sinon `superfast`, 30 images/s, débit plafonné, 2 fils ffmpeg
  (`FFMPEG_THREADS`) ; `worker-media` traite 2 fichiers à la fois (`MEDIA_CONCURRENCY`) ; un traitement bloqué depuis
  20 minutes passe en échec. Les erreurs ffmpeg sont journalisées (`immoplus logs worker-media`).
- Cause de la vidéo perdue (diagnostic du 2026-11-12) : la page se rechargeait toutes les 8 s pendant le traitement et
  interrompait l'envoi de la vidéo suivante (ligne restée « uploading ») ; l'annonce partait sans vidéo. Un envoi sans
  nouveau morceau depuis 5 minutes est désormais « interrompu » : il ne bloque plus « Suivant » et se supprime.
- Courriel aux administrateurs à la première mise en ligne d'une annonce (`EMAIL_NOUVELLES_ANNONCES`).
- Messagerie : une notification non lue par conversation (se met à jour, remonte, sonne à chaque message).
- Aperçu WhatsApp : balises Open Graph et image `/annonces/<slug>/apercu.jpg` vérifiées en ligne (réponse 200, 52 Ko) ; si
  l'aperçu manque encore, c'est le cache de WhatsApp (liens déjà partagés) : tester avec le débogueur de partage de Facebook.
- Piège : `worker` et `realtime` chargent les réglages « public » : toute nouvelle variable exigée au démarrage doit aussi
  figurer dans leurs modèles `infra/compose/env/*.env.example`.

**2026-11-13 : gérant créé par l'équipe vérifié d'emblée.** « Nouveau gérant » est utilisé après l'entretien : le profil est
vérifié à la création (plan Gratuit attribué, ligne `gerant.verification` au journal) et le bandeau « pas encore
vérifié » n'apparaît plus. Un gérant créé avant ce changement reste « en attente » : le passer à « vérifié » dans
Comptes › Profils de gérants.

**2026-11-12 : liens d'activation des gérants invalides (clé de signature).** L'administration (`ADMIN_SECRET_KEY`)
signait les liens, le site (`SITE_SECRET_KEY`) les lisait : signature toujours refusée. Nouvelle clé `LIENS_SIGNING_KEY`,
commune aux deux (obligatoire en production). Sur un serveur existant : `python3 outils/creer_env.py --services`, puis
`immoplus up -d --force-recreate web-api admin` ; les liens déjà envoyés sont à régénérer.

**2026-11-09 : passage sur un nouveau PC et correctif mobile.**
- Mobile : zod 4.6.7 (faille d'épuisement mémoire). Une copie 3.25 reste embarquée par `@expo/cli` jusqu'à Expo 58.
- Piège : `npm install` avec `--legacy-peer-deps` retire `@react-native/jest-preset` du verrou mobile ; utiliser `npm ci`.
- Piège : `make seed DEMO=1` échoue, le conteneur `admin` monte `media_public` en lecture seule et n'a pas `media_tmp`.
- Piège : le double envoi vers `Magloireaffokpe/immoplus` est un réglage local à refaire sur chaque poste
  (voir `docs/flux-et-ci-cd.md`).

**2026-11-05 : mise en ligne sur le VPS rmeolab et défi anti-robot désactivable.**
- Immo+ déployé sur le VPS partagé (`~/apps/immoplus`, compte `romaeus`, clé de déploiement avec alias SSH
  `github-immoplus`, bloc ajouté au Caddy central) sous `imos-plus.com` (`www.`, `api.`, `pilotage.`). Courriels :
  SMTP LWS, nom d'hôte du serveur (`mailNN.lwspanel.com`) et non `mail.<domaine>` dont le certificat ne correspond pas.
- Le réglage `TURNSTILE_ENABLED` existait dans l'administration sans être lu : il est branché (`captcha.actif()`),
  désactivé par défaut ; décoché, ni défi ni widget Cloudflare. À cocher avec les vraies clés. L'alerte « clés de
  test Turnstile en production » ne part plus au démarrage : elle n'est émise que si le défi est actif avec ces clés.
- Piège : le thème sombre du système rendait des textes illisibles ; correctif fusionné (PR n°7).
- Numéro de l'équipe : `+229 01 60 23 92 88`. Piège : `seed` a déjà écrit l'ancien numéro (et `TURNSTILE_ENABLED`
  à vrai, ancien défaut) dans `app_settings` : une valeur existante n'est jamais écrasée, il faut la changer dans
  Administration › Paramètres.
- Création des comptes du personnel depuis l'administration (Comptes › Nouveau personnel, réservé aux administrateurs,
  journalisée) ; la commande `creer_personnel` reste pour le premier compte.
- Textes de l'accueil reformulés (sous-titre, piliers, étapes, FAQ) ; `docs/design/COPYWRITING.md` aligné. Restent à
  revoir dans le même esprit : pages Chambres, fiche, alertes, quartiers.
- Guide de déploiement aligné sur la doc du VPS : compte `romaeus`, alias SSH `github-immoplus`, `caddy validate`.
- Alertes : (1) à la création d'une alerte, les chambres déjà en ligne qui correspondent sont signalées d'un seul coup
  (`alertes.signaler_existantes`, notification `alert.digest`, clé `alert-initial:<alerte>`) ; (2) les alertes
  (`alert.match`, `alert.digest`) partent aussi par courriel si le compte a une adresse confirmée ; la page
  `/compte/alertes` demande l'adresse quand elle manque. Pas de changement d'API ni de schéma. Reste : une pause ou
  une reprise d'alerte ne rejoue pas les chambres déjà en ligne ; l'application mobile n'a pas encore de jeton push,
  donc le courriel est aujourd'hui le seul envoi actif. Tests écrits mais non exécutés en local (CI).

**2026-10-21 : référencement.**
- Page `/pres-de-l-universite` (chambres à moins de 1,5 km du campus, les plus proches d'abord), liée depuis le pied
  de page et le plan du site. Titres et descriptions des listes centrés sur « chambres à louer » et l'Université de
  Parakou ; canonique partout, `noindex, follow` pour les listes filtrées, triées ou paginées ; pied de page vers les
  pages de quartier. Fiche : vidéo déclarée dans l'aperçu (`og:video`), titre « … à louer à <quartier> ». Accueil :
  canonique et données structurées `WebSite` et `Organization`. `robots.txt` ferme aussi mot de passe et activation.
- `docs/referencement.md` : ce que voient les plateformes et Google, gestes hors code (Search Console, fiche
  d'établissement, liens).

**2026-10-21 (matin) : mise en production sur `main` et CI/CD documentée.**
- Demande de fusion n°3 fusionnée dans `main` de `romeolontchedji/immoplus` (dépôt de référence) après CI verte :
  verrou npm complété pour `npm ci`, Pillow 13.0.0 et certifi corrigeant 9 failles (`pip-audit`), test Cloudinary
  rendu déterministe.
- `docs/flux-et-ci-cd.md` : dépôts, flux quotidien, hooks, workflows GitHub Actions, déploiement manuel, sécurité de
  la chaîne. Reste à faire par le propriétaire du dépôt : protection de `main`, branche par défaut `main`,
  CODEOWNERS.

**2026-10-21 : Cloudinary, capacité, session de l'administration.**
- Cloudinary activable depuis Administration › Paramètres › Photos et vidéos (ADR 0010, sans nouvelle dépendance) :
  clés préfixées `cloudinary:` (disque et Cloudinary cohabitent), envoi par le worker (worker-media reste sans
  Internet), 4 nouveaux essais puis échec propre, suppression asynchrone, commande `transferer_medias` dans les deux
  sens, CSP ouverte au CDN seulement si le compte est renseigné. Le worker monte `media_tmp` et `media_public`.
- Capacité mesurée (`docs/capacite.md`, outil `outils/mesurer_charge.py`) : ~400 utilisateurs actifs confortables,
  ~700 en pointe avec 3 processus. `WEB_CONCURRENCY` réglable dans `.env` (3 par défaut, 2 auparavant).
- Limites de débit par compte pour les utilisateurs connectés (adresses partagées : CGNAT, Wi-Fi du campus) ;
  plafonds anonymes réglables dans l'administration (`RATE_IP_FACTOR`, `AUTH_RATE_PER_MIN_IP`, 60 au lieu de 30).
- Session de l'administration : 60 minutes d'inactivité au lieu de 30 (migration core 0011).

**2026-10-20 (fin de nuit) : VPS partagé et documentation.**
- Mode « derrière le Caddy central » du VPS partagé rmeolab : notre Caddy sans port publié, alias `immoplus-web`
  sur le réseau `web_proxy`, seule l'adresse réelle du visiteur transmise à Django, liste blanche par `client_ip`
  (`docker-compose.vps-partage.yml`, `central-immoplus.caddy`, `infra/vps/deployer.sh`, autoguérison).
- Documentation : guide de déploiement réécrit (du local à la production, Cloudflare, Brevo, R2, Expo),
  nouveau guide de l'administration avec chaque paramètre (`docs/administration.md`), `comprendre-immoplus`,
  tuto gérant, parcours web, écrans mobiles et guides de design alignés sur l'ADR 0009 ; ADR 0004 remplacé.

**2026-10-20 (nuit) : identification par nom d'utilisateur, plus aucun SMS ni numéro (ADR 0009).**
- Connexion par nom d'utilisateur et mot de passe ; inscription sur une page (prénom, nom, nom d'utilisateur
  vérifié pendant la frappe, mot de passe de 10 caractères) ; clé de secours affichée une seule fois.
- Mot de passe oublié : lien par e-mail confirmé, clé de secours, puis lien généré par l'équipe (24 h, journalisé).
  E-mail ajouté et confirmé depuis le profil.
- Gérants créés sans mot de passe ; lien d'activation (72 h) où ils choisissent leurs identifiants.
- Numéro de téléphone, codes SMS, fournisseur SMS, SMS de repli et attestation d'appareil supprimés (migrations
  accounts 0009 à 0011, core 0010). Vidéo facultative pour publier.
- Site, API, administration et application mobile mis à jour ; textes légaux alignés.

**2026-10-20 (soir) : retours sur les alertes, la recherche et la publication.**
- Alertes (site et application) : seules les alertes actives sont listées (celles en pause repliées en bas), un
  bouton « Créer une nouvelle alerte » ouvre le formulaire ; tous les critères en listes déroulantes à choix
  multiples, avec l'eau, l'électricité, la cuisine, la douche interne, la cour clôturée et la distance de l'UP ;
  une alerte sans aucune option est refusée (« Choisis d'abord au moins une option »).
- Recherche : chaque lettre affine (début de mot sur le titre, le quartier, le repère, le type et les équipements),
  sans effet de rechargement ; tous les filtres repliés sous « Filtres », y compris sur ordinateur ; l'accueil n'a
  plus qu'un champ de recherche.
- Publication : cautions eau et électricité (montants) distinctes de la caution du loyer (mois) ; 5 photos minimum
  (`PHOTOS_MIN`). Types sanitaires, eau à plusieurs sources (migrations listings 0010 à 0012).
- Fiche : plus de bloc gérant ; contact avant les chambres similaires sur téléphone. Logo réduit sur téléphone.

**2026-10-20 : partage des chambres.**
- Bouton « Partager » très visible sur la fiche (site et application) et pour le gérant sur ses annonces en ligne :
  WhatsApp, Facebook, applications du téléphone (TikTok, Instagram…), lien à copier.
- Un seul lien suffit : balises Open Graph et Twitter (titre, prix, quartier, équipements), image d'aperçu JPEG
  1200 × 630 tirée de la couverture (`/annonces/<slug>/apercu.jpg`, en cache), lien canonique, données structurées
  schema.org (annonce, loyer en XOF, note, fil d'Ariane). Image par défaut pour les autres pages.
- `robots.txt` annonce enfin le plan du site, qui donne la date de mise à jour de chaque annonce. Le robot de
  WhatsApp ne compte plus de vue. `assetlinks.json` porte le paquet `bj.immoplus.app` (empreinte encore à fournir).

**2026-10-20 : nouvelle identité Immo+ (domaine `immoplus.bj`).**
- Nom, logos (site, administration, application, icônes Android et iOS, favicon), PDF de la documentation régénérés.
  Paquet mobile `bj.immoplus.app`, schéma `immoplus`. Palette inchangée.
- Infrastructure : projet Compose, base, rôles, utilisateur des images et variables `IMMOPLUS_*` renommés ; volumes
  de développement copiés vers `immoplus_*`, base renommée.
- Migrations de données : `core.0009` (textes des paramètres), `accounts.0008` (courriels de démonstration).
- Fiche publique : seule la position du quartier est donnée (tests alignés).

**2026-10-20 : plan d'actions v3 (retours du 19/10), voir `docs/plan-actions-v3.md`.**
- Recherche : listes déroulantes, filtres en temps réel, colonne de filtres fixe (site), quartiers voisins, équipements
  indexés. Fiche : quartier d'abord, galerie à diapositives, équipements, prix à débattre, avis, contact direct.
- Publication : électricité, eau, cuisine, prix à débattre, « Autres détails » en texte simple ; éditeur en étapes sur
  le site ; brouillons signalés ; suppression de toute annonce ; vues par chambre et au total (vues du jour comprises).
- Site : barre latérale fixe partout sauf l'accueil, « Mon profil » (numéro changé sur place), code SMS à six cases,
  pages de connexion avec photo. Profil public du gérant (site, API, mobile).
- Administration : note sous chaque paramètre, échecs de connexion du site journalisés, avis, aide des quartiers.
- Correctifs : lien « Voir les chambres » d'une alerte (quartier par identifiant), « Autres détails » jamais affichés
  sur la fiche, couleurs en dur du mobile remplacées par les jetons.
- Migrations : `listings.0009` (cuisine, loyer à débattre, avis, textes simples), `core.0008` (masquage coupé).

**2026-10-19 : solidité avant hébergement.**
- `readyz` passe par le client Redis partagé (tests : disque simulé). Relevé du code mort : `docs/code-mort.md`.
- Administration : double authentification par code envoyé par courriel à chaque connexion (10 min, 5 essais,
  3 renvois). Suivi des erreurs : regroupées dans redis-queue, page « Erreurs » de l'administration, courriel au
  plus une fois par heure et par erreur (`ERREURS_DESTINATAIRES`).
- Sauvegardes : image `immoplus-sauvegarde` (pg_dump vérifié + restic, ADR 0008) ; copie hors serveur inactive tant que
  `RESTIC_REPOSITORY` est vide. Restauration testée en local.
- Anti-robot Turnstile branché dès le développement (clés de test Cloudflare) ; `fake` refusé en production, clés de
  test signalées comme erreur. `.env.example` commenté paramètre par paramètre.
- Développement : page `/dev/boite` (courriels, SMS, push reçus). VPS : minuterie systemd qui redémarre les
  conteneurs figés (`infra/vps/autoguerison.sh`, 3 fois par heure au plus).

**2026-10-18 (fin) : prêt pour l'hébergement.**
- Médias derrière `StorageProvider` (ADR 0007) : disque local par défaut, squelette S3/R2 ; aucune migration.
- CI : nouvelle tâche « mobile » (types, lint, tests, client d'API comparé au contrat) ; TypeScript 6 (attendu par
  Expo 57) ; `verifier_tout.sh` lance aussi ces contrôles quand `mobile/node_modules` existe.
- Production réparée avant tout déploiement : `ALLOWED_HOSTS` réglé sur le domaine (sinon tout en 400), réglages
  `taches` pour beat et worker-media, realtime sans clé OTP ; test qui démarre chaque processus avec son modèle d'env.
- `outils/creer_env.py --services` (régénère les fichiers des services sans changer les secrets), réglages de
  l'agrégateur SMS dans les modèles, redirection du domaine nu vers `www`.
- `infra/vps/bootstrap.sh` et `docs/deploiement-vps-pas-a-pas.md`. Restent : copie des sauvegardes hors du serveur
  (restic), double authentification de l'administration, agrégateur SMS.

**2026-10-18 (suite) : retours sur l'application mobile.**
- Clavier : l'écran commun et la conversation font de la place au clavier sur Android « bord à bord » et iOS.
- Code OTP : envoi au 6e chiffre, vibration et cases vidées en cas de refus ; remplissage SMS déclaré
  (`sms-otp`, `oneTimeCode`) pour les vrais SMS.
- Mot de passe : erreurs du serveur sous le bon champ (mobile), confirmation demandée sur le site.
- Police Plus Jakarta Sans embarquée (`mobile/assets/fonts`, une famille par graisse), hauteur de ligne qui suit la
  taille (jambages du logo et des titres plus coupés), en-tête commun `EnTetePage` sur les onglets et sous-pages.
- Conversation sans en-tête natif superflu ; réglage de l'empreinte toujours visible dans Profil.
- En attente d'accord : nouveaux équipements (champ en base).

**2026-10-18 : retours du porteur sur le site et l'administration.**
- Site : espaces locataire et gérant sur un gabarit commun (`web/espace.html`) avec barre latérale colorée
  (`composants/barre_espace.html`, balise `menu_espace`) et contenu pleine largeur ; rangée d'onglets sur tablette et
  téléphone ; conteneur général porté à 1440 px avec marges fluides.
- Menu mobile du site refait (`composants/menu_mobile.html`) : icônes, groupes, page courante colorée.
- Œil sur tous les champs mot de passe (`js/mot-de-passe.js`) ; page compte passée au composant de champ commun.
- Accueil : section « Cherche par quartier » (vrais quartiers et nombre de chambres) entre prévention et alerte.
- Alertes : bouton « Supprimer » recentré, liste et formulaire côte à côte sur grand écran.
- Administration : menu coloré ordonné par usage avec titres de rubrique, titres de section marqués, section
  « Audience » (vues de fiches site/app sur 14 jours, téléphones actifs), tuile « Gérants à vérifier » retirée.
- Signalements : personne visée (nom, numéro, lien) et accès rapides (compte, annonce, conversation, décision
  pré-remplie). Décision de modération vérifiée de bout en bout (statut, notification, journal).
- Connexions à l'administration : historique des échecs activé (`AXES_ENABLE_ACCESS_FAILURE_LOG`), compte lisible
  dans « Connexions », message d'erreur en clair.
- Vues de fiches : provenance (site ou application) comptée sous les sujets `canal:web` / `canal:app` de
  `daily_stats` (sans migration).

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
  (`manque_publication`) via de nouveaux filtres dans `web/templatetags/immoplus.py`.
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
    - **Espace administration** (`adminsite`) : intégration des règles du thème Immo+ Admin (`serveur/adminsite/static/admin/css/immoplus-adm.css` et `serveur/adminsite/templates/admin/base_site.html`), logo officiel, typographie Plus Jakarta Sans, boutons d'action stylisés (jaune solaire `--sun` pour enregistrer, rouge `--danger` pour supprimer), fil d'Ariane épuré, modules arrondis, suppression du dossier externe redondant `serveur/immoplus-django-admin-theme`.
    - **Page d'accueil branchée** : `/` sert désormais la page de présentation (`web/accueil.html` : héro illustré, recherche à onglets, « Comment ça marche », FAQ) ; le catalogue reste sur `/annonces`. Le script des onglets est déplacé dans `serveur/web/static/js/accueil.js` (CSP sans script en ligne) et le code mort `views_public.accueil` est supprimé.
  - Élimination intégrale des couleurs et opacités en dur hors de `tokens.css` (conforme règle 8 de `AGENTS.md`).
  - Respect strict de la CSP (règle 5) : suppression de tous les attributs `style=` et gestionnaires d'événements `on...=` inline.
  - Nettoyage documentaire : suppression du document obsolète `docs/plan-action-web.md`.
  - Validation complète : `outils/verifier_tout.sh` au vert (ruff, djlint, tests des outils, contraste WCAG AA, import-linter, bandit, makemigrations, openapi, pytest partiel).

- **Phase 9 — Application Mobile Expo / React Native (`mobile/`).**
  - Refonte et alignement visuel strict des 19 écrans sur les maquettes de référence (`docs/design/screens/`) et `docs/design/DESIGN.md`.
  - Palette officielle Immo+ : Bleu cobalt (`#1B44D6`), Nuit (`#0F1B3D`), Jaune solaire (`#FFB429`), Fond clair (`#F5F6FA`).
  - Typographie *Plus Jakarta Sans*, icônes Lucide uniquement (aucun emoji ni sticker, conformément aux règles du projet).
  - Écrans finalisés et stylisés :
    1. **Bienvenue** (`BienvenueScreen`) : bannière nuit, logo officiel, feuille blanche arrondie (rayon 32), pastilles pastel, double CTA locataire/gérant.
    2. **Connexion** (`ConnexionScreen`) : en-tête Immo+, numéro béninois (+229), bouton cobalt, rappel inscription réservée aux locataires.
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
- **Logo unifié.** Composant `Logotype` (`ui/components/Logo.tsx`, icône officielle + « Immo+ » + point
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
  au démarrage (socket de contrôle de gunicorn dans le code monté en lecture pour l'utilisateur `immoplus`) ; sans effet.
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
  (carte cobalt, listes groupées, WhatsApp Immo+, version), logo animé au démarrage (`DemarrageAnime`), présentation
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
- **Administration refondue** : design aligné (jetons, police locale, `adminsite/static/admin/css/immoplus-adm.css`
  réécrit en redirigeant les variables de l'admin Django), accueil « À traiter / Activité / Gérer », page Paramètres par
  thème (`adminsite/parametres_page.py`), quartiers gérables, tout en français (intitulés des applications, modèles,
  champs et valeurs de modération ; migrations d'options et d'intitulés **sans SQL**, vérifiées par `sqlmigrate`),
  noms lisibles, groupes retirés. 984 tests serveur verts (seul `/readyz`).
- **Données locales** : compte administrateur d'essai `admin.essai@immoplus.local` / `AdminEssai2026!` (local seulement).

