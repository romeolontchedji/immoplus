# ADR 0010 — Photos et vidéos chez Cloudinary, activables depuis l'administration

- Statut : **accepté**
- Date : 2026-10-21

## Contexte

Les médias des annonces sont rangés sur le disque du VPS et servis par Caddy (ADR 0007). Sur le VPS partagé, le disque
et la bande passante sont communs à plusieurs applications ; les vidéos en consomment le plus. L'équipe veut pouvoir
basculer vers **Cloudinary** (stockage et réseau de diffusion, offre gratuite de 25 crédits par mois) **depuis
l'administration**, sans redéploiement, et revenir en arrière.

Contraintes : `worker-media` (ffmpeg, Pillow) n'a volontairement aucun accès à Internet ; les secrets ne doivent pas
être modifiables depuis une page web ; un changement de réglage ne doit casser aucun média déjà en ligne.

## Décision

- **Aucune nouvelle dépendance** : l'API HTTP de Cloudinary (envoi signé SHA-1, suppression par préfixe) est appelée
  avec `urllib`, comme Turnstile et les notifications push. `CloudinaryStorageProvider` dans
  `apps/core/providers/stockage.py`.
- **Notre propre traitement reste la source** : `worker-media` produit toujours les variantes WebP et le MP4 ; Cloudinary
  ne stocke et ne diffuse que ces fichiers (aucune transformation facturée).
- **Clé auto-descriptive** : une clé rangée chez Cloudinary est enregistrée avec le préfixe `cloudinary:`
  (`cloudinary:listings/<annonce>/<média>/960.webp`). L'URL de chaque média dépend de sa clé, pas du réglage : disque et
  Cloudinary cohabitent, et basculer n'affecte que les nouveaux envois. Aucune migration de schéma.
- **Interrupteur** : paramètre `MEDIA_STORAGE` (`local` ou `cloudinary`) dans Administration › Paramètres › Photos et
  vidéos. La page refuse `cloudinary` si le compte n'est pas renseigné.
- **Secrets dans `.env`** : `CLOUDINARY_CLOUD_NAME` (non secret) va au site, à l'API, à l'administration et à
  `worker-media` ; `CLOUDINARY_API_KEY` et `CLOUDINARY_API_SECRET` vont au **seul `worker`**.
- **Envoi par le worker** : `worker-media` prépare les fichiers sur le volume `media_public` et laisse le média « en
  traitement » ; la tâche `apps.listings.publier_media_distant` (file `default`, worker avec Internet) les envoie, rend
  le média prêt puis efface la copie locale. Quatre nouveaux essais espacés (1, 2, 4, 8 min), puis échec propre et
  notification au gérant. Le worker monte désormais `media_tmp` et `media_public`.
- **Suppression asynchrone** : effacer un média rangé chez Cloudinary passe par la tâche
  `apps.stockage_distant.supprimer` (file `default`), réessayée en cas de panne.
- **Existant** : `manage.py transferer_medias --vers cloudinary|disque` déplace les médias déjà en ligne, un par un.
- **CSP** : `img-src` et `media-src` autorisent `https://res.cloudinary.com` quand le compte est renseigné.

## Conséquences

- Les médias rangés chez Cloudinary ne sont pas dans la sauvegarde restic du serveur : Cloudinary en est le dépositaire.
  Retirer les clés de `.env` tant que des médias y sont rangés casserait leurs adresses : rapatrier d'abord
  (`transferer_medias --vers disque`).
- Le quota gratuit (25 crédits : 1 crédit = 1 Go stocké ou 1 Go diffusé par mois) suffit pour démarrer ; le suivre dans
  le tableau de bord Cloudinary.
- `S3StorageProvider` reste un squelette (ADR 0007) : Cloudinary couvre le besoin sans client S3.
