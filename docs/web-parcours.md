# Parcours web : matrice commandes → routes → services → permissions

Source de vérité du plan `docs/plan-action-web.md` (phase 0). Toute action visible à l'écran doit
figurer ici : route, méthode, service propriétaire, permission, succès et erreurs. Les données
affichées viennent de la base (sélecteurs et services), jamais de valeurs codées en dur.

## Décision de palette (phase 0)

Les jetons actuels (**marque émeraude**, accent **terre cuite**, succès vert) sont conservés. Les
maquettes utilisent un bleu cobalt ; il servira uniquement de référence de **composition**, pas de
couleur. Aucune couleur n'est écrite en dur hors de `serveur/web/static/css/tokens.css` et les
contrastes WCAG AA clair/sombre restent contrôlés par `outils/contraste.py`. Un passage au cobalt,
s'il est décidé plus tard, se fait en modifiant les jetons, le guide de design et les tests de
contraste, en une seule fois.

## Découverte et fiche (public)

| Commande | Route | Méthode | Vue | Service / sélecteur | Permission | Succès | Erreurs |
|---|---|---|---|---|---|---|---|
| Voir le catalogue | `/`, `/annonces` | GET | `views_public._liste` | `listings.services.fil.rechercher`, `listings.selectors` | public | page de résultats | `ErreurMetier` (tri/curseur) → message |
| Filtrer / trier | `/annonces?…` | GET | idem | idem | public | filtres récapitulés | idem |
| Voir un quartier | `/quartiers/<slug>` | GET | `quartiers` | `selectors.quartier_par_slug` | public | page quartier | 404 si inactif |
| Voir une fiche | `/annonces/<slug>` | GET | `fiche` | `selectors.fiche_publique`, `services.vues.enregistrer` | public | fiche (sans adresse ni numéro) | 404 si masquée/inconnue |
| Ajouter/retirer un favori | `/annonces/<slug>/favori` | POST | `basculer_favori` | `services.favoris` | client connecté | message | 302 connexion ; `ErreurMetier` |
| Signaler | `/annonces/<slug>/signaler` | POST | `signaler` | `moderation.services.signaler(_deja_louee)` | client connecté | message « transmis » | 302 ; `ErreurMetier` |
| Contacter le gérant | `/annonces/<slug>/contacter` | POST | `contacter` | `chat.services.ouvrir` | client connecté | 302 conversation | 302 ; message (vide, coordonnées) |

## Favoris, alertes, messages, notifications (locataire connecté)

| Commande | Route | Méthode | Vue | Service / sélecteur | Permission | Succès | Erreurs |
|---|---|---|---|---|---|---|---|
| Voir ses favoris | `/compte/favoris` | GET | `mes_favoris` | `selectors.favoris_de` | client/gerant connecté | liste | 302 connexion |
| Voir/créer/supprimer une alerte | `/compte/alertes` | GET/POST | `mes_alertes` | `services.alertes`, `selectors.alertes_de` | client | message | 404 si gérant ; plafond d'alertes |
| Voir ses conversations | `/compte/messages` | GET | `mes_conversations` | `chat.selectors` | client/gerant | liste | 302 |
| Lire/écrire/bloquer | `/compte/messages/<id>` | GET/POST | `conversation` | `chat.services.{envoyer,bloquer,debloquer,lire}` | participant | message | 404 tiers ; `ErreurMetier` |
| Voir ses notifications | `/compte/notifications` | GET | `mes_notifications` | `notifications.selectors` | client/gerant | liste | 302 |
| Tout marquer comme lu | `/compte/notifications` | POST | `mes_notifications` | `notifications.services.tout_marquer_lu` | client/gerant | 302 | — |

## Authentification et compte

| Commande | Route | Méthode | Vue | Service | Permission | Succès | Erreurs |
|---|---|---|---|---|---|---|---|
| Se connecter | `/connexion` | GET/POST | `views_auth.connexion` | `accounts.services.authentification` | public | 302 `next` sûr | `ErreurMetier` liée au champ |
| Se déconnecter | `/deconnexion` | POST | `deconnexion` | `django.contrib.auth.logout` | connecté | 302 `/` | — |
| S'inscrire (téléphone) | `/inscription` | GET/POST | `inscription_telephone` | `accounts.services.otp.demander` | public | 302 code | `ErreurMetier` |
| Saisir le code | `/inscription/code` | GET/POST | `inscription_code` | `otp.verifier` | public | 302 profil | code invalide/expiré |
| Finaliser le profil | `/inscription/profil` | GET/POST | `inscription_profil` | `inscription.inscrire_client` | public | session ouverte | `otp_token_invalid` |
| Mot de passe oublié | `/mot-de-passe-oublie[/code\|/nouveau]` | GET/POST | `oubli_*` | `otp`, `inscription.reinitialiser_mot_de_passe` | public | 302 | `ErreurMetier` |
| Espace compte | `/compte` | GET/POST | `espace_compte` | `compte.{modifier_profil,changer_mot_de_passe,supprimer}` | connecté | message | `ErreurMetier` liée au champ |

## Espace gérant

| Commande | Route | Méthode | Vue | Service / sélecteur | Permission | Succès | Erreurs |
|---|---|---|---|---|---|---|---|
| Lister ses annonces | `/pro/annonces` | GET | `views_pro.liste` | `selectors.annonces_du_gerant` | gérant | table/liste | 302 ; 404 si rôle ≠ gérant |
| Créer/éditer | `/pro/annonces[/nouvelle\|/<id>]` | GET/POST | `editeur` | `services.annonces.{creer_brouillon,modifier}` | gérant propriétaire | 302 / message | `ErreurMetier` liée au champ |
| Publier / confirmer / masquer / louer / annuler | idem | POST | `editeur` | `services.annonces.*` | gérant propriétaire | message | `listing_not_publishable` (manques) |
| Supprimer un brouillon | idem | POST | `editeur` | `services.annonces.supprimer_brouillon` | gérant propriétaire | 302 liste | `ErreurMetier` |
| Envoyer des médias | `/v1/...` (API) | POST | `envoi.js` | `media`, `services.medias` | gérant propriétaire | progression | format/taille ; propriété |

## Référencement

`/robots.txt` et `/sitemap.xml` : vues `robots` et `sitemap`, publiques, sans donnée privée.

## Hors périmètre de cette matrice

- **ADM** (hôte et administration séparés) : phase 6, sur le processus `admin` uniquement.
- **APP mobile** : hors Web.
- **Facturation** : désactivée (`SUBSCRIPTION_ENABLED`), aucun paiement simulé.
