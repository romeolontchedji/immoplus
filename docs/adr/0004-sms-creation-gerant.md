# ADR 0004 — SMS de notification à la création d'un gérant

- Statut : **accepté**, amendé le 2026-10-14 (le parcours d'activation OTP est supprimé ; le SMS à la création reste, purement informatif)
- Date : 2026-10-13

## Contexte

Le CDC (EF-AUT-07) prévoit que l'administration crée le compte gérant et que le
gérant l'active ensuite par OTP depuis l'application. Rien n'indique comment le
gérant apprend que son compte est prêt : aucune notification automatique n'était
émise à la création (`administration.creer_gerant` ne prévient personne). C'est un
appel humain (WhatsApp/appel) qui devait combler le trou — sans trace et à la
merci d'un oubli.

## Décision

- À la création d'un gérant, un **SMS « compte prêt »** est envoyé au numéro
  enregistré : « Immo+ : ton compte gérant est créé. Ouvre l'application et
  active-le avec ce numéro. Ne communique jamais ton code. » (texte GSM-7, un
  seul segment).
- L'envoi est planifié **après le commit** (`transaction.on_commit`) et exécuté
  **en asynchrone** (tâche Celery). Un échec du fournisseur **n'annule jamais**
  la création du compte : l'exception est journalisée et auditée
  (`gerant.notification_echec`).
- Le SMS **ne contient pas** le code d'activation : celui-ci est demandé depuis
  l'application (preuve de possession du numéro, validité 5 minutes).
- **Aucun renvoi automatique** lors des modifications du compte (vérification,
  changement de nom, statut) : la notification n'a lieu qu'à la création, pour
  éviter les doublons.

## Conséquences

- Un SMS supplémentaire par gérant créé, hors budget OTP (volume faible).
- Le gérant peut être prévenu sans dépendre d'un appel, avec une trace d'audit en
  cas d'échec.
- L'infrastructure SMS existante (`apps.core.providers.sms`,
  `apps.accounts.tasks`) est réutilisée, sans nouvelle dépendance.
- Décision hors CDC : à reporter dans `docs/cahier-des-charges.md` si elle est
  retenue durablement.

## Amendement — 2026-10-14 : suppression du parcours d'activation

Décision produit : **l'activation d'un gérant n'existe plus**. Tout est manuel.
Seule l'administration crée le compte gérant, puis transmet ses identifiants au
gérant (WhatsApp/appel). Le gérant se connecte avec son numéro et son mot de
passe, et peut changer son mot de passe par la suite.

Conséquences sur le présent ADR :

- Le passage « le gérant l'active ensuite par OTP depuis l'application » et la
  contrainte « le SMS ne contient pas le code d'activation » sont **sans objet**.
- Le SMS « compte prêt » reste envoyé à la création, mais devient **purement
  informatif** : il ne déclenche plus aucun parcours d'activation. Son texte
  exact vit dans `apps/accounts/services/administration.py`
  (`MESSAGE_COMPTE_PRET`).
- Le web (`/pro/activation*`) et le mobile (`/activation/*`, écran d'activation)
  ont été retirés ; voir `docs/avancement.md`.
- Le reste (envoi après commit, asynchrone, sans renvoi automatique, échec
  journalisé et audité) est **conservé**.
