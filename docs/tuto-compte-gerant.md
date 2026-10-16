# Tuto — Créer un compte gérant

Ce document décrit, étape par étape, le parcours réel d'un gérant chez Logeo :
de la commande manuelle dans l'administration jusqu'à l'ouverture de son espace
professionnel. Il est écrit en suivant le code, pas une intention : à chaque
étape, on indique ce qui est **fait**, ce qui est **à faire**, et le fichier
concerné.

Règle directrice : **pas d'inscription publique de gérant et pas de parcours
d'activation**. Les comptes sont créés par l'équipe après vérification ; le
gérant reçoit ses identifiants, se connecte, puis peut changer son mot de passe
quand il veut.

## Vue d'ensemble

| # | Étape | Qui | État |
| - | ----- | --- | ---- |
| 1 | Contact + vérification (pièces, entretien) | gérant → équipe | manuel, hors plateforme |
| 2 | Création du compte dans l'administration | administrateur | **fait** (ADM) |
| 3 | Remise des identifiants au gérant (hors plateforme) | équipe | manuel, hors plateforme |
| 4 | Première connexion et modification du mot de passe | gérant | **fait** (mobile + web) |
| 5 | Vérification du badge + première annonce | administrateur / modérateur | fait (modération) |

## Étape 1 — Contact et vérification (hors plateforme)

Le gérant n'a aucun moyen de s'inscrire seul. Il prend contact avec l'équipe (par appel/WhatsApp depuis la page « Je suis gérant »). L'équipe procède à la vérification manuelle des pièces et à un court entretien.

> Cette étape est entièrement hors plateforme. Aucune trace côté serveur (pas d'audit, pas de fiche de candidature).

## Étape 2 — Création du compte dans l'administration

Depuis l'administration (`http://pilotage.localhost:8080`), un administrateur :

1. ouvre **Gérants → Créer un gérant** (ou le bouton équivalent dans la liste des utilisateurs) ;
2. remplit le formulaire :

   | Champ | Obligatoire | Remarque |
   | ----- | ----------- | -------- |
   | Numéro de téléphone | oui | normalisé E.164, pays imposés par `OTP_ALLOWED_COUNTRIES` |
   | Prénom et nom | oui | 2 à 120 caractères |
   | Nom affiché | non | sinon le nom complet est utilisé |
   | Zone d'activité | oui | |
   | Mot de passe (à attribuer par défaut) | oui | à communiquer au gérant par le canal choisi (hors plateforme) |

   Formulaire : `serveur/adminsite/admin.py:41` (`NouveauGerantForm`).

Ce qui se passe côté serveur (`serveur/apps/accounts/services/administration.py`) :

- le numéro est normalisé ; **409** si un compte existe déjà avec ce numéro ;
- création d'un `User` avec `role = gerant`, mot de passe haché (utilisable) et `phone_verified_at` positionné ;
- création d'un `GerantProfile` avec la zone, le nom affiché, `created_by = administrateur`, statut de vérification par défaut (`pending`) ;
- écriture d'un événement d'audit **`gerant.cree`** ;
- planification d'un **SMS informatif** « compte prêt » (voir étape 3).

Message affiché à l'administrateur après création :
« Compte gérant créé pour {nom}. Mot de passe attribué ; à communiquer par le canal choisi (hors plateforme). »

> Piège : la vérification (badge Vérifié) est une action **séparée**
> (`GerantProfile → verification_status`, service `administration.definir_verification`,
> audit `gerant.verification`). Créer le compte ne donne pas le badge.

## Étape 3 — Remise des identifiants au gérant (hors plateforme)

L'administrateur communique au gérant, **hors plateforme** (WhatsApp, appel, SMS ou tout autre canal), son numéro de téléphone et le mot de passe attribué par défaut. Il lui indique de se connecter sur la plateforme et de modifier son mot de passe dès sa première connexion.

En complément, un **SMS automatique purement informatif** part vers le numéro
enregistré à la création du compte (ADR 0004) :

> Logeo : ton compte gérant est créé. Connecte-toi dans l'application avec le
> mot de passe que l'équipe t'a transmis. Ne le communique jamais.

Fonctionnement (`serveur/apps/accounts/services/administration.py`) :

- l'envoi est planifié **après le commit** (`transaction.on_commit`) puis exécuté
  **en asynchrone** par la tâche `notifier_gerant_cree`
  (`serveur/apps/accounts/tasks.py`) ;
- **un échec du SMS n'annule jamais la création** : l'erreur est journalisée et
  un événement d'audit **`gerant.notification_echec`** est écrit ;
- le SMS **ne contient pas** le mot de passe : l'équipe le transmet elle-même ;
- **pas de renvoi** lors des modifications du compte (vérification, nom,
  statut) : la notification n'a lieu qu'à la création.

## Étape 4 — Première connexion et modification du mot de passe

**Depuis l'application ou le site web** :

1. Le gérant se connecte avec son numéro de téléphone et le mot de passe attribué par défaut.
2. À sa première connexion (ou dès qu'il le souhaite), il modifie son mot de passe depuis son espace (profil / paramètres). Tous les appareils et sessions sont révoqués lors du changement de mot de passe (comportement existant : `reinitialiser_mot_de_passe` invalide jetons et appareils).

> Il n'y a **aucune activation par OTP** pour le gérant : rien à valider côté
> plateforme. Les vérifications se font manuellement, hors plateforme.

## Étape 5 — Après la première connexion

- le compte a un mot de passe utilisable : le gérant peut se connecter
  (`POST /v1/auth/login`) et retrouver son espace gérant ;
- publier une annonce exige le badge **Vérifié**
  (`serveur/apps/listings/services/annonces.py:259`) → l'administrateur doit
  passer `verification_status` à `verified` ;
- la **première annonce** passe par la modération avant publication (CDC §9.23).

## À faire / à confirmer

- [x] Créer le gérant directement avec un mot de passe attribué par l'administration.
- [x] Supprimer tout parcours d'activation (web et mobile).
- [x] Envoyer un SMS informatif « compte prêt » à la création.
- [ ] Remplacer l'agrégateur SMS `[À FOURNIR]` et vérifier l'encodage réel.

## Références

- CDC : `docs/cahier-des-charges.md` — EF-ADM-01 (création d'un gérant), §5.3 (OTP), §7 (administration).
- Décision : `docs/adr/0004-sms-creation-gerant.md` (SMS informatif à la création).
- Création : `serveur/apps/accounts/services/administration.py` (`creer_gerant`),
  `serveur/adminsite/admin.py:41`.
- Web : `serveur/web/views_auth.py`, `serveur/web/urls.py`, `serveur/web/forms.py`,
  tests `serveur/web/tests/test_comptes_web.py`.
- Mobile : `mobile/src/features/auth/`, `mobile/src/features/pro/CompteGerantScreen.tsx`,
  `mobile/src/app/(auth)/compte-gerant.tsx`.
