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
- **Première annonce d'un gérant** : passe en `processing` et attend l'approbation de la modération (action à écrire).
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

