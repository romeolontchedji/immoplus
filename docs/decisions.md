# Décisions

Une ligne par décision ; le détail de la phase 0 est dans `docs/adr/`.

- **Numéros** : forme canonique `+229 01 XXXXXXXX`. La bibliothèque refuse les anciens numéros à 8 chiffres : on les complète par `01`.
- **Django 5.2 LTS** (support jusqu'en avril 2028). Passage au 6.2 LTS à planifier en 2027.
- **Anneau de focus** `marque-500` en clair (le `marque-300` demandé donne 1,9:1, sous WCAG).
- **`django-unfold` retiré** : ses scripts et styles en ligne ne peuvent pas être validés sans navigateur sous une CSP stricte. Administration Django standard.
- **Un seul système d'authentification par surface** : Bearer JWT pour l'application, session pour le site, session séparée (autre table, autre cookie, autre rôle SQL) pour l'administration.
- **Refresh** : rejeu dans les 60 s renvoie la même paire (stockée chiffrée dans Redis 60 s) ; après 60 s, l'appareil est révoqué.
- **OTP** : lignes tracées même sans SMS (compte inexistant) pour les plafonds ; elles ne consomment pas le budget ; réponse identique dans tous les cas.
- **Plafonds divisés par deux** arrondis au supérieur (3 devient 2).
- **Colonne ajoutée** hors du CDC : `devices.rotated_at` (fenêtre de grâce du refresh) et un index sur `devices.prev_refresh_hash`.
- **Détection de coordonnées** : un signal fort (numéro, e-mail, lien, numéro épelé) refuse l'enregistrement de l'annonce ; les mots-clés seuls sont signalés sans refus. Un lien Markdown est refusé comme un lien.
- **Première annonce d'un gérant** : ~~relue avant publication~~ (remplacé le 2026-11, voir plus bas) : elle est en ligne aussitôt comme les suivantes.
- **Médias, version simple** : une seule variante vidéo MP4 720p et des photos WebP 480/960/1600 (sans agrandissement). HLS reporté. Envoi tus minimal sous `/uploads/{id}` (route imposée par la limite de corps de Caddy).
- **Modèles** : `apps.media` ne contient que le traitement pur et le stockage ; les tables et la logique base de données des médias sont dans `apps.listings` (le contrat import-linter interdit qu'une application importe les modèles d'une autre).
- **Marque d'un envoi** : 150 Mo (vidéo), 12 Mo (photo), 2 envois ouverts et 500 Mo en attente par gérant, 10 photos et 1 vidéo par annonce.

## Session de finalisation (d à g)
- **Favoris** : contrainte d'unicité `(user, listing)` plutôt que clé primaire composite (la clé composite Django échouait à la création de table).
- **Messages** : colonne `body_masked` ajoutée (texte montré au destinataire en mode `mask`) ; longueur 1 à 2000 caractères contrôlée par une contrainte SQL de migration.
- **Adresse privée** : visible dans le détail d'une conversation par le gérant seulement.
- **Communication entre applications par signaux** (jamais d'import de modèles) : `listings.statut_annonce_change`, `accounts.statut_compte_change`, `chat.contact_detecte`, `notifications.push_regle`.
- **Notification d'un message** : `notified_at` est posé par un récepteur du signal `push_regle` (push parti ou saut motivé), jamais par le simple fait de supprimer un push pour cause de présence ; le rattrapage chaque minute renvoie les messages restés sans `notified_at`.
- **Tests WebSocket** : écrits, ignorés tant que `daphne` n'est pas une dépendance de développement.

## Novembre 2026 : décisions du porteur après les premiers jours de production
- **Publication directe** : un gérant vérifié publie sans relecture, première annonce comprise (le compte créé par l'équipe est
  vérifié dès sa création, l'entretien ayant eu lieu avant). Administrateurs et modérateurs reçoivent un courriel à la première
  mise en ligne de chaque annonce. L'adresse d'un compte du personnel n'a pas besoin d'être « confirmée » par lien.
- **Chambre louée** : photos et vidéo supprimées aussitôt (confirmation demandée), annonce archivée ; plus de délai de 7 ou 90 jours.
  La fiche reste ouverte avec « déjà louée ». Les chambres libres passent toujours avant. « Reproposer » repart d'un brouillon.
- **Avis liés au gérant** (en plus de la chambre) : sa réputation ne dépend pas de la vie de chaque annonce. Un locataire peut
  noter une chambre louée.
- **Caution du loyer** retirée du site (l'API la garde, à 0 par défaut, pour ne pas casser l'application mobile).
- **Vidéo** : durée maximale gardée à **60 s** (10 à 60 s).
- **Liens signés** (activation, réinitialisation, e-mail) : clé commune `LIENS_SIGNING_KEY`, partagée par l'administration et le site
  (la clé du site seule rendait tout lien créé par l'administration invalide).
- **Suppression de compte** : toujours une **anonymisation** (les lignes d'audit ne se suppriment pas) ; sur le site, en deux temps
  avec avertissement de ce qui est perdu ; un administrateur peut anonymiser des comptes depuis l'administration.
- **Paiements** : **KKiaPay**, fenêtre du site, transaction revérifiée côté serveur, webhook. **Deux cases séparées** : alertes des
  locataires (`PAID_ALERTS_ENABLED`, paiement unique par alerte, prix `ALERT_PRICE`) et abonnement des gérants
  (`SUBSCRIPTION_ENABLED`, formules `PLANS`). Un paiement d'alerte se fait **au clic sur « Créer l'alerte »** ; pas d'alerte sans
  e-mail confirmé. Gérant sans abonnement payant : renvoi vers la page des formules ; ses annonces en ligne restent visibles.
  Activation **en espèces** possible par un administrateur. Les paiements restent éteints par défaut.
- **Messagerie** : une seule notification par conversation (même personne, même chambre).
- **Fichiers statiques** : adresses versionnées par empreinte (`?v=`), car Caddy les met en cache un an.
- **Connexion d'un gérant** : arrivée sur le tableau de bord. **Mots de passe du profil** : jamais remplis par le navigateur.
- **Administration** : accès par plages d'adresses ; page « Statistiques » dédiée.

