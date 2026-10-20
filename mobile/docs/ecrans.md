# Carte des écrans

Générée à partir des fichiers de `src/app` (une ligne par route). **43 routes** : 15 réelles, 28 squelettes.
« Réel » = l'écran fonctionne avec les crochets de données ; « squelette » = fichier en place, route branchée, en-tête de commentaire
qui décrit la route, l'API, les états à gérer et les références du cahier des charges (à remplacer par l'écran final).

Les groupes de routes entre parenthèses (`(auth)`, `(locataire)`, `(partage)`, `(onglets)`) n'apparaissent pas dans l'URL.

| Route | Écran | État | API | Fichier |
|---|---|---|---|---|
| `/connexion` | ConnexionScreen | réel | POST /v1/auth/login | `src/features/auth/ConnexionScreen.tsx` |
| `/inscription/code` | CodeStep | réel | POST /v1/auth/otp/verify | `src/features/auth/CodeStep.tsx` |
| `/inscription/profil` | InscriptionProfilScreen | réel | POST /v1/auth/register | `src/features/auth/FinalSteps.tsx` |
| `/inscription/telephone` | TelephoneStep | réel | POST /v1/auth/otp/request | `src/features/auth/TelephoneStep.tsx` |
| `/mot-de-passe/code` | CodeStep | réel | POST /v1/auth/otp/verify | `src/features/auth/CodeStep.tsx` |
| `/mot-de-passe/nouveau` | MotDePasseNouveauScreen | réel | POST /v1/auth/password/reset | `src/features/auth/FinalSteps.tsx` |
| `/mot-de-passe/telephone` | TelephoneStep | réel | POST /v1/auth/otp/request | `src/features/auth/TelephoneStep.tsx` |
| `/alertes` | AlertesScreen | squelette | GET /v1/me/alerts ; PATCH\|DELETE /v1/me/alerts/{id} | `src/features/alerts/AlertesScreen.tsx` |
| `/` | AccueilScreen | réel | GET /v1/listings | `src/features/listings/AccueilScreen.tsx` |
| `/messages` | ConversationsScreen | réel | GET /v1/conversations | `src/features/messaging/ConversationsScreen.tsx` |
| `/profil` | ProfilScreen | squelette | GET /v1/me ; POST /v1/auth/logout | `src/features/profile/ProfilScreen.tsx` |
| `/recherche` | RechercheScreen | réel | GET /v1/listings | `src/features/listings/RechercheScreen.tsx` |
| `/favoris` | FavorisScreen | réel | GET /v1/me/favorites | `src/features/listings/FavorisScreen.tsx` |
| `/modifier-alerte/[id]` | AlerteFormScreen | squelette | POST /v1/me/alerts ; PATCH /v1/me/alerts/{id} | `src/features/alerts/AlerteFormScreen.tsx` |
| `/nouvelle-alerte` | AlerteFormScreen | squelette | POST /v1/me/alerts ; PATCH /v1/me/alerts/{id} | `src/features/alerts/AlerteFormScreen.tsx` |
| `/annonces/[ident]` | FicheScreen | squelette | GET /v1/listings/{ident} ; POST /v1/listings/{ident}/views ; PUT\|DELETE /v1/me/favorites/{id} | `src/features/listings/FicheScreen.tsx` |
| `/conversation/[id]` | ConversationScreen | réel | GET /v1/conversations/{id}, GET\|POST …/messages, POST …/read ; WebSocket | `src/features/messaging/ConversationScreen.tsx` |
| `/conversation/nouvelle` | NouvelleConversationScreen | squelette | POST /v1/conversations | `src/features/messaging/NouvelleConversationScreen.tsx` |
| `/filtres` | FiltresScreen | squelette | GET /v1/districts (quartiers) | `src/features/listings/FiltresScreen.tsx` |
| `/notifications` | NotificationsScreen | réel | GET /v1/notifications, POST …/read, POST …/read-all | `src/features/notifications/NotificationsScreen.tsx` |
| `/parametres/aide` | AideScreen | squelette | (statique) | `src/features/profile/AideScreen.tsx` |
| `/parametres/appareils` | AppareilsScreen | squelette | GET /v1/devices ; DELETE /v1/devices/{id} | `src/features/profile/AppareilsScreen.tsx` |
| `/parametres/economie-donnees` | EconomieDonneesScreen | squelette | (local) `usePreferences()` | `src/features/profile/EconomieDonneesScreen.tsx` |
| `/parametres/mot-de-passe` | MotDePasseScreen | squelette | POST /v1/auth/password/change | `src/features/profile/MotDePasseScreen.tsx` |
| `/parametres/nom` | NomScreen | squelette | PATCH /v1/me | `src/features/profile/NomScreen.tsx` |
| `/parametres/preferences` | PreferencesNotificationsScreen | squelette | GET\|PUT /v1/me/preferences ; PUT /v1/devices/current/push-token (via `activerPush`) | `src/features/profile/PreferencesNotificationsScreen.tsx` |
| `/parametres/supprimer` | SupprimerCompteScreen | squelette | DELETE /v1/me | `src/features/profile/SupprimerCompteScreen.tsx` |
| `/parametres/telephone` | TelephoneScreen | squelette | POST /v1/auth/otp/request (change_phone) ; POST /v1/auth/otp/verify ; POST /v1/me/phone/change | `src/features/profile/TelephoneScreen.tsx` |
| `/signaler` | SignalerScreen | squelette | POST /v1/reports ; POST /v1/listings/{id}/report-rented | `src/features/listings/SignalerScreen.tsx` |
| `/+not-found` | NotFound | réel | — | `src/app/+not-found.tsx` |
| `/pro/annonces` | MesAnnoncesScreen | squelette | GET /v1/pro/listings | `src/features/pro/MesAnnoncesScreen.tsx` |
| `/pro/messages` | ConversationsScreen | réel | GET /v1/conversations | `src/features/messaging/ConversationsScreen.tsx` |
| `/pro/profil` | ProfilScreen | squelette | GET /v1/me ; POST /v1/auth/logout | `src/features/profile/ProfilScreen.tsx` |
| `/pro/tableau-de-bord` | DashboardScreen | squelette | GET /v1/pro/dashboard | `src/features/pro/DashboardScreen.tsx` |
| `/pro/annonce/[id]` | AnnonceGerantScreen | squelette | GET /v1/pro/listings/{id} ; POST …/confirm\|hide\|mark-rented\|undo-rented\|publish | `src/features/pro/AnnonceGerantScreen.tsx` |
| `/pro/annonce/[id]/modifier` | AnnonceModifierScreen | squelette | PATCH /v1/pro/listings/{id} | `src/features/pro/AnnonceModifierScreen.tsx` |
| `/pro/annonce/[id]/stats` | AnnonceStatsScreen | squelette | (aucun point d'entrée serveur pour l'instant — voir docs/a-verifier.md) | `src/features/pro/AnnonceStatsScreen.tsx` |
| `/pro/nouvelle-annonce/description` | DescriptionStep | squelette | POST /v1/pro/markdown/preview ; PATCH /v1/pro/listings/{id} | `src/features/pro/DescriptionStep.tsx` |
| `/pro/nouvelle-annonce/equipements` | EquipementsStep | squelette | POST /v1/pro/listings (crée le brouillon serveur quand `champsManquants()` est vide) | `src/features/pro/EquipementsStep.tsx` |
| `/pro/nouvelle-annonce/infos` | InfosStep | squelette | (local) `useBrouillon()` | `src/features/pro/InfosStep.tsx` |
| `/pro/nouvelle-annonce/localisation` | LocalisationStep | squelette | GET /v1/districts ; `expo-location` (position facultative) ; (local) `useBrouillon()` | `src/features/pro/LocalisationStep.tsx` |
| `/pro/nouvelle-annonce/medias` | MediasStep | squelette | GET\|POST /v1/pro/listings/{id}/media ; PATCH …/media/order ; DELETE …/media/{mid} ; envoi tus (`envoyerFichier`) | `src/features/pro/MediasStep.tsx` |
| `/pro/nouvelle-annonce/publication` | PublicationStep | squelette | POST /v1/pro/listings/{id}/publish | `src/features/pro/PublicationStep.tsx` |

## Navigation

| Espace | Structure | Garde |
|---|---|---|
| Sans compte | `(auth)` : pile (connexion, inscription, mot de passe oublié, présentation du compte gérant) | une session ouverte renvoie vers son espace |
| Locataire (et visiteur) | `(locataire)/(onglets)` : Accueil · Recherche · Messages · Alertes · Profil ; pile : favoris, alertes | un compte gérant est renvoyé vers `/pro/tableau-de-bord` |
| Partagé | `(partage)` : fiche d'annonce, conversation, notifications, réglages, modales (filtres, signaler, nouvelle conversation) | aucune ; les écrans personnels affichent `AuthRequired` |
| Gérant | `pro/(onglets)` : Tableau de bord · Annonces · Messages · Profil ; pile : détail/modification d'annonce, assistant de création (6 étapes) | sans session → `/connexion` ; compte locataire → `/` |

Liens profonds : `immoplus://annonces/<slug>` et `https://<EXPO_PUBLIC_WEB_HOST>/annonces/<slug>` ouvrent `/annonces/[ident]`
(le même identifiant que le site). Un appui sur une notification passe par `features/notifications/routage.ts`.
