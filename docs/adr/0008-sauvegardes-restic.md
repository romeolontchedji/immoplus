# ADR 0008 — Sauvegardes hors du serveur avec restic

- Statut : **accepté** (outil en place, désactivé tant que le dépôt distant n'est pas renseigné)
- Date : 2026-10-19

## Contexte

Le conteneur `backup` écrit chaque nuit une sauvegarde de la base dans un volume **du même serveur**. Si le VPS est
perdu (panne du fournisseur, erreur, piratage), base et sauvegardes disparaissent ensemble. Le CDC (§13.4) prévoit une
copie chiffrée chez un autre fournisseur, avec les médias, et un test de restauration.

## Décision

- **restic** (paquet Debian, logiciel libre) dans une petite image dédiée (`infra/backup/Dockerfile`, basée sur
  l'image PostgreSQL déjà utilisée pour `pg_dump`).
- Chaque nuit, après la sauvegarde locale : `restic backup` des sauvegardes de la base et des volumes de médias
  (`media_public`, `media_private`), puis `restic forget --keep-daily 14 --keep-weekly 8 --prune`.
- **Chiffrement côté serveur** avant l'envoi (clé `RESTIC_PASSWORD`) : le fournisseur de stockage ne peut rien lire.
- Dépôt distant de **n'importe quel stockage compatible S3** d'un autre fournisseur que le VPS (Backblaze B2 ou
  Cloudflare R2 recommandés : quelques gigaoctets gratuits ou presque).
- Tant que `RESTIC_REPOSITORY` est vide, la copie est sautée avec un message ; la sauvegarde locale continue.

## Conséquences

- `RESTIC_PASSWORD` doit être conservé **hors du serveur** (coffre de l'équipe) : sans lui, les sauvegardes sont
  illisibles, y compris pour nous.
- Test de restauration à faire avant l'ouverture, puis chaque trimestre (guide de déploiement, étape 10).
- Étape suivante possible : archivage continu des journaux PostgreSQL (WAL) pour revenir à n'importe quelle minute.
