# Code mort et fonctions non branchées (relevé du 19/10/2026)

Méthode : `vulture` pour le Python (filtré des conventions Django : classes d'administration, commandes, récepteurs,
tâches appelées par leur nom), recherche de chaque candidat dans tout le dépôt (tests et gabarits compris), analyse
maison des fichiers et exports TypeScript (knip ne prend pas encore en charge TypeScript 6), classes CSS cherchées dans
les gabarits, scripts et code, routes de l'API cherchées dans l'application.

Rien n'a été supprimé : chaque ligne est à confirmer avant nettoyage.

## 1. Code mort (rien ne l'appelle)

### Serveur

| Élément | Fichier | Remarque |
|---|---|---|
| `changer_role()` | `apps/accounts/services/administration.py` | Jamais appelée, même par les tests |
| `attendre()` | `apps/core/providers/push.py` | « Point d'extension pour les tests » jamais utilisé |
| `statuts_publics()` | `apps/listings/selectors.py` | Remplacée par `STATUTS_VISIBLES` |
| Filtre `statut_conversation` | `web/templatetags/immoplus.py` | Plus utilisé par les gabarits |
| Icônes `plus`, `log-in` | `web/templates/web/composants/icone.html` | Plus utilisées après la refonte des menus |
| Icônes `user-check`, `map` | `adminsite/templates/admin/includes_icone.html` | Tuile « Gérants à vérifier » retirée |
| Règles CSS de l'ancien gabarit gérant (`pro-layout`, `pro-sidebar*`, `pro-nav*`) | `web/static/css/components/pro.css` | Remplacées par la barre latérale commune (`espace.css`) |
| Règles CSS de l'ancien menu du compte (`compte-sidebar`, `compte-menu*`, `compte-carte-profil*`) | `web/static/css/components/compte.css` | Idem |
| Règles CSS de l'ancienne conversation (`conv-*`, 39 classes) | `web/static/css/components/annonce.css` | Remplacées par `messagerie.css` |
| Autres classes CSS isolées (≈ 40) et 32 utilitaires jamais employés (`mt-4`, `fs-28`, `rounded-lg`…) | `utilities.css`, `catalogue.css`, `etats.css`, `badge.css`… | Liste complète : relancer l'analyse (§4) |

Au total, **118 classes CSS** ne sont utilisées nulle part (une seule fausse alerte : `navigation__lien--actif`,
fabriquée par le code Python).

### Application mobile

| Élément | Fichier | Remarque |
|---|---|---|
| Fichier entier | `src/state/preferences.ts` | Jamais importé |
| `estSessionPerdue` | `src/state/queryClient.ts` | Jamais appelée |
| `lirePreference` | `src/hooks/usePreferences.ts` | Jamais appelée |
| `useMe` | `src/features/profile/queries.ts` | La session fournit déjà le profil |
| `useOuvrirConversation` | `src/features/messaging/queries.ts` | L'écran « Écrire au gérant » utilise un autre chemin |
| `useApercuMarkdown` | `src/features/pro/queries.ts` | L'aperçu du texte enrichi n'est pas proposé sur mobile |
| Types `AppConfig`, `MediaPro`, `TypeChambrePro` | `useAppConfig.ts`, `pro/queries.ts` | Déclarés, jamais utilisés |

Une vingtaine d'autres éléments sont exportés sans raison (utilisés seulement dans leur propre fichier) : sans
conséquence, le mot `export` est simplement de trop.

## 2. Prêt côté serveur mais pas branché

| Fonction | État | Ce qui manque |
|---|---|---|
| Réordonner les photos depuis l'application | Route `PATCH …/media/order` prête, utilisée par le site | Aucun écran mobile (la suppression et le remplacement de la vidéo sont branchés depuis le 19/10/2026) |
| Anti-robot du site (Turnstile) | Interface prête, fournisseur `fake` | Clés Cloudflare et `CAPTCHA_PROVIDER=turnstile` |
| Attestation de l'application (Play Integrity, App Attest) | Interface prête, fournisseur `fake` | Développement des deux fournisseurs |
| Pièces d'identité chiffrées | `PRIVATE_FILES_KEY` et volume `media_private` en place | Aucune fonctionnalité ne les utilise (la vérification des gérants se fait hors plateforme) |
| `VIDEO_PROVIDER` | Réglage déclaré | Aucune interface : le traitement vidéo appelle `ffmpeg` directement |
| Remboursements | `rembourser()` dans les trois fournisseurs de paiement | Jamais appelé : à relier au moment de l'abonnement payant |
| Abonnement, alertes payantes | Complets et testés | Éteints volontairement (`SUBSCRIPTION_ENABLED`, `PAID_ALERTS_ENABLED`) |
| SMS de repli au gérant | Code présent | Éteint (`SMS_FALLBACK_ENABLED`) |
| Push FCM direct | Squelette | Expo suffit pour l'instant |
| Stockage S3 / R2 | Squelette (ADR 0007) | Client S3 et compte |

## 3. Faux positifs écartés

Les outils signalent aussi comme « inutilisés » des éléments que Django ou Celery appellent eux-mêmes : classes
d'administration (`UserAdmin`…), méthodes `has_add_permission`, commandes `seed` et `creer_personnel`, récepteurs de
signaux (`@receiver`), tâches appelées par leur nom dans le planning, gabarits qui remplacent ceux de Django
(`admin/index.html`, `admin/nav_sidebar.html`…), filtre de base `dans_reseau`. Ils sont bien utilisés.

## 4. Relancer l'analyse

```bash
pip install vulture   # dans un environnement temporaire
cd serveur && vulture apps web adminsite config --min-confidence 60 \
  --exclude "*/migrations/*,*/tests/*" | grep -E "unused (function|method|class)"
```

Puis chercher chaque nom dans le dépôt (`grep -rn <nom> serveur`) avant de conclure.
