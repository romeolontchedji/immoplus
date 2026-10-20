# Tuto — Créer un compte gérant

Ce document décrit, étape par étape, le parcours réel d'un gérant chez Immo+ :
de la création dans l'administration jusqu'à l'ouverture de son espace
professionnel. Il est écrit en suivant le code : à chaque étape, on indique ce
qui est **fait**, ce qui reste **manuel**, et le fichier concerné.

Règle directrice : **pas d'inscription publique de gérant**. Les comptes sont
créés par l'équipe après vérification, **sans mot de passe ni numéro de
téléphone** (ADR 0009). Le gérant reçoit un **lien d'activation** et choisit
lui-même son nom d'utilisateur et son mot de passe.

## Vue d'ensemble

| # | Étape | Qui | État |
| - | ----- | --- | ---- |
| 1 | Contact + vérification (pièces, entretien) | gérant → équipe | manuel, hors plateforme |
| 2 | Création du compte dans l'administration | administrateur | **fait** |
| 3 | Création et envoi du lien d'activation (WhatsApp, e-mail) | administrateur | **fait** (envoi manuel) |
| 4 | Activation : nom d'utilisateur, mot de passe, clé de secours | gérant | **fait** (site) |
| 5 | Badge Vérifié + première annonce | administrateur / modérateur | **fait** (modération) |

## Étape 1 — Contact et vérification (hors plateforme)

Le gérant n'a aucun moyen de s'inscrire seul. Il prend contact avec l'équipe
(appel ou WhatsApp depuis la page « Je suis gérant »). L'équipe vérifie ses
pièces et mène un court entretien.

> Cette étape est entièrement hors plateforme : aucune trace côté serveur.

## Étape 2 — Création du compte dans l'administration

Depuis l'administration (`https://pilotage.<domaine>`, ou
`http://pilotage.localhost:8080` en local), un administrateur :

1. ouvre **Comptes → Nouveau gérant** ;
2. remplit le formulaire (`NouveauGerantForm`, `serveur/adminsite/admin.py`) :

   | Champ | Obligatoire | Remarque |
   | ----- | ----------- | -------- |
   | Prénom | oui | |
   | Nom | oui | |
   | Nom affiché | non | nom public de l'agence ; sinon prénom et nom |
   | Zone d'activité | oui | |

Ce qui se passe côté serveur (`creer_gerant`,
`serveur/apps/accounts/services/administration.py`) :

- création d'un `User` avec `role = gerant`, **sans mot de passe utilisable** et
  sans nom d'utilisateur (il le choisira) ;
- création d'un `GerantProfile` (zone, nom affiché, `created_by`, statut de
  vérification `pending`) ;
- événement d'audit **`gerant.cree`**.

> Piège : la vérification (badge Vérifié) est une action **séparée**
> (`GerantProfile → verification_status`, service `definir_verification`,
> audit `gerant.verification`). Créer le compte ne donne pas le badge.

## Étape 3 — Lien d'activation

Sur la fiche du compte, le bloc **Accès au compte** propose **Lien
d'activation** (vue `accounts_user_lien`). La page affiche :

- le lien `https://www.<domaine>/activer/<jeton>`, **valable 72 h** et
  **utilisable une seule fois** ;
- un bouton **Envoyer par WhatsApp** (le message est pré-rempli, l'équipe
  choisit le destinataire dans WhatsApp) ; le lien peut aussi être copié pour un
  e-mail.

Chaque lien créé est audité (**`gerant.lien_activation`**). Si le lien expire,
il suffit d'en créer un nouveau. Une fois le compte activé, le bouton disparaît
(erreur `already_active` si on insiste).

> Le lien est signé avec la clé du site : impossible à fabriquer. Il ne contient
> aucun mot de passe. Ne le transmettre qu'au gérant concerné.

## Étape 4 — Activation par le gérant

Le gérant ouvre le lien (`/activer/<jeton>`, vue `activer_gerant`,
`serveur/web/views_auth.py`) et :

1. choisit son **nom d'utilisateur** (3 à 30 caractères : lettres, chiffres,
   point, tiret bas ; unique) ;
2. choisit son **mot de passe** (10 caractères au moins, différent de son nom) ;
3. reçoit sa **clé de secours** (16 caractères, affichée une seule fois), à
   noter ou à capturer avant de continuer.

La session s'ouvre, l'événement **`gerant.active`** est audité. Il se connecte
ensuite, sur le site comme dans l'application, avec son nom d'utilisateur et son
mot de passe. Dans son profil, il peut ajouter un e-mail (recommandé : c'est le
moyen le plus simple de retrouver son compte).

**Mot de passe oublié plus tard** : lien par e-mail, sinon clé de secours,
sinon l'équipe crée un **lien de réinitialisation** depuis la même fiche (24 h,
usage unique) après avoir vérifié son identité. Voir `docs/administration.md`.

## Étape 5 — Après l'activation

- publier une annonce exige le badge **Vérifié** : l'administrateur passe
  `verification_status` à `verified` ;
- la **première annonce** passe par la modération avant publication (CDC §9.23).

## État

- [x] Créer le gérant sans mot de passe ni numéro.
- [x] Lien d'activation signé, 72 h, usage unique, envoi WhatsApp en un geste.
- [x] Clé de secours donnée à l'activation.
- [x] Lien de réinitialisation créé par l'équipe.
- [ ] Courriel d'activation automatique (aujourd'hui l'équipe transmet le lien).

## Références

- Décision : `docs/adr/0009-identification-par-nom-d-utilisateur.md` (remplace
  l'ADR 0004).
- Création et liens : `serveur/apps/accounts/services/administration.py`
  (`creer_gerant`, `lien_activation`, `activer_gerant`, `lien_reinitialisation`),
  `serveur/adminsite/admin.py`, gabarit `admin/lien-compte.html`.
- Signature des liens : `serveur/apps/accounts/services/identifiants.py`.
- Web : `serveur/web/views_auth.py`, `serveur/web/forms.py` (`Activation`).
- Mobile : `mobile/src/features/pro/CompteGerantScreen.tsx`,
  `mobile/src/app/(auth)/compte-gerant.tsx`.
