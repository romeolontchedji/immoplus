# ADR 0009 — Identification par nom d'utilisateur, sans code SMS

- Statut : **accepté**
- Date : 2026-10-20
- Remplace : ADR 0004 (SMS à la création d'un gérant) et le parcours OTP du CDC (EF-AUT-01, 02, 06, 07)

## Contexte

Les codes envoyés par SMS (inscription, mot de passe oublié, changement de numéro) coûtent cher à chaque envoi,
dépendent d'un fournisseur extérieur et peuvent être déclenchés en masse par des robots. Le porteur demande de
les abandonner complètement.

## Décision

- **Clé du compte : le nom d'utilisateur.** Unique sans tenir compte des majuscules, 3 à 30 caractères (lettres
  minuscules, chiffres, `.` et `_`), noms réservés refusés. Prénom et nom sont demandés séparément.
- **Aucun numéro de téléphone n'est conservé** (amendement du 2026-10-20) : ni demandé à l'inscription, ni gardé
  pour les gérants. Les numéros déjà enregistrés sont supprimés avec la colonne (migration accounts 0011). Seul
  le numéro de paiement Mobile Money, saisi au moment de payer, reste attaché à une transaction.
- **Connexion** : nom d'utilisateur et mot de passe, et rien d'autre.
- **Mot de passe oublié**, sans SMS, dans cet ordre de mise en avant :
  1. lien par **e-mail**, si l'utilisateur en a ajouté un et l'a confirmé (30 min, usage unique) ;
  2. **clé de secours** (16 caractères) affichée une seule fois à l'inscription, à noter ou capturer ; elle se
     régénère depuis le profil et après chaque usage ; seule son empreinte Argon2 est enregistrée ;
  3. **l'équipe**, en dernier recours : vérification de l'identité (questions sur le compte : annonces, messages,
     date d'inscription), puis lien de réinitialisation (24 h) généré dans l'administration et journalisé.
- **Gérants** : l'équipe crée le compte (prénom, nom, zone) sans mot de passe et obtient un **lien
  d'activation** (72 h, usage unique) qu'elle transmet par WhatsApp ou e-mail. Le gérant y choisit son nom
  d'utilisateur et son mot de passe, puis reçoit sa clé de secours. Aucun mot de passe ne circule.
- Les liens (activation, réinitialisation, confirmation d'e-mail) sont **signés** (`django.core.signing`) et
  contiennent l'empreinte du mot de passe ou de l'e-mail courant : ils deviennent invalides dès qu'ils ont servi.
  Aucune table supplémentaire.
- Toute réinitialisation coupe toutes les sessions et tous les appareils (`token_version`).
- **Anti-robots** : Turnstile reste sur l'inscription et le mot de passe oublié du site ; verrouillage progressif
  (Redis) sur la connexion et la clé de secours, par nom d'utilisateur et par appareil ou adresse IP.
- Supprimés : demande et vérification de code (`auth/otp/*`), changement de numéro, SMS « compte prêt », SMS de
  repli au gérant et fournisseur SMS : plus aucun SMS n'est envoyé par Immo+.

## Conséquences

- Plus aucun coût par inscription ni dépendance à un fournisseur SMS.
- Créer un compte de locataire devient plus facile, donc aussi pour un robot : Turnstile, plafonds par adresse et
  limites de conversations des comptes récents compensent. Les gérants restent vérifiés en personne.
- Un utilisateur sans e-mail qui perd sa clé de secours dépend de l'équipe : l'application l'invite à ajouter un
  e-mail dès l'inscription.
