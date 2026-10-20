# ADR 0007 — Stockage des médias derrière `StorageProvider`

- Statut : **accepté** ; complété par l'ADR 0010 (Cloudinary activable depuis l'administration)
- Date : 2026-10-18

## Contexte

Le CDC (§6, palier 2) prévoit de passer les médias du disque du serveur à un stockage objet (S3, R2) « sans changer le
code métier ». Le réglage `STORAGE_PROVIDER` existait, mais le code écrivait directement dans `MEDIA_ROOT` à une
vingtaine d'endroits : la bascule aurait demandé de reprendre le traitement des médias, les sélecteurs et le jeu d'essai.

## Décision

- Interface `StorageProvider` dans `apps/core/providers/stockage.py`, comme les fournisseurs SMS, push et paiement.
  Quatre opérations : dossier de travail du traitement, publication, URL publique, suppression (plus un contrôle
  d'espace).
- Le code métier ne manipule que des **clés** (`listings/<annonce>/<média>/<fichier>`), déjà enregistrées en base sous
  ce format : aucune migration, aucune modification de l'API ni de l'application.
- `apps/media/stockage.py` est la seule porte d'entrée du code métier (originaux en cours d'envoi en local, dérivés
  publics via le fournisseur).
- Fournisseurs : `local` (disque servi par Caddy, par défaut) et `s3` (squelette : URL par `MEDIA_PUBLIC_BASE_URL`,
  publication et suppression à écrire). Un test branche un faux stockage objet de bout en bout pour le prouver.

## Conséquences

- Passage à Cloudflare R2 (recommandé : pas de frais de sortie, décisif pour la vidéo) ou à un autre stockage
  compatible S3 : compléter `S3StorageProvider`, ajouter le client S3 (nouvelle dépendance, donc un ADR), migrer les
  fichiers existants, puis changer `STORAGE_PROVIDER`.
- Le conteneur `worker-media` n'a pas accès à Internet (choix de sécurité) : au passage au stockage objet, lui ouvrir
  l'accès au seul point de terminaison du stockage.
- Les originaux en cours d'envoi restent sur le disque local (ffmpeg lit un fichier) ; au palier 2 avec plusieurs
  serveurs, ils iront sur un volume partagé ou dans le stockage objet (CDC §6.3).
