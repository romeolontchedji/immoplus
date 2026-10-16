# Écarts entre maquettes et base

Ce document consigne les éléments présents sur les maquettes de référence (`docs/design/DESIGN.md`, `screens/`, `screens-source/`) qui diffèrent du schéma de base de données actuel (`models.py`, migrations) ou de la logique métier du cahier des charges, conformément à la section 12 de `DESIGN.md` (« La base prime »).

---

## 1. Modèle Listing / Annonces

| Élément maquette | État dans la base / serveur | Traitement retenu (sans migration intempestive) |
|---|---|---|
| **Temps à pied / Distance du campus** (ex: *« 7 min à pied de l'UP »*) | La base possède `distance_m` (distance en mètres calculée par rapport au campus). Aucun champ textuel libre de durée à pied. | Affichage dynamique basé sur `distance_m` (ex. *« À X m du campus »*), sans inventer de champ en base. |
| **Durée de la vidéo** (ex: *« 0:18 »*) | Modèle `Media` contient `duration_s` (durée en secondes calculée lors de l'encodage par ffmpeg). | Filtre Django `duree_video` formatant les secondes en `mm:ss` ou `ss s`. |
| **Badge « Carrelé »** | Pas de champ booléen `is_tiled` dans le modèle `Listing`. | Omis de la liste des caractéristiques techniques ou renseigné dans la description Markdown libre. |
| **Bouton « Me prévenir si ça change »** (sur la fiche) | Géré par le système existant d'alertes par critères et quartier (`/compte/alertes?district=...`). | Le bouton renvoie vers la création d'alerte sur le quartier concerné via `alerte_url`. |

---

## 2. Espace Gérant (Dashboard Pro)

| Élément maquette | État dans la base / serveur | Traitement retenu |
|---|---|---|
| **Statistiques « Vues ce mois » et « Contacts reçus »** | Calculées via `apps.listings.selectors.tableau_de_bord_gerant(profil)` à partir de `daily_stats` et des conversations. | Données réelles branchées directement sur le context du template `web/pro/tableau.html`. |
| **Bouton « Ajouter une vidéo » (carte d'alerte chambre sans vue)** | Sélection de la première annonce sans vidéo du gérant. | Redirige vers `/pro/annonces/<slug>/modifier#medias`. |
| **Onglet « Statistiques »** dans la barre latérale | Aucune route dédiée `/pro/statistiques` n'existe (les statistiques sont intégrées au tableau de bord). | Pointé vers `/pro/dashboard` pour éviter toute rupture 404. |
| **Libellé « Mes chambres »** (DESIGN.md §129, barre latérale et accueil de l'espace) | Le CDC (§1791) et les tests `web` attendent « Mes annonces », quel que soit le type de bien. | Renommé partout en « Mes annonces » (barre latérale, barre de navigation, titre de page, fil d'Ariane). |
| **Indicateurs « Publiées » / « Brouillons »** | La maquette ne les montre pas ; le test `test_tableau_de_bord_affiche_les_indicateurs` les exige. La liste `statuts` (`TITRES_STATUTS`) était calculée mais non rendue. | Pastilles `.pro-statut-chip` sous les métriques, à partir des compteurs réels `listings_by_status`. |

---

## 3. Communication et Sécurité

| Élément maquette | État dans la base / serveur | Traitement retenu |
|---|---|---|
| **Téléphone direct ou WhatsApp du gérant** | Strictement interdit par le CDC (§5 de `AGENTS.md`) : zéro contact hors plateforme, masquage des coordonnées. | Aucun numéro de gérant n'est affiché. Les échanges passent exclusivement par la messagerie Logeo (`/compte/messages`). |
| **Paiement direct en ligne** | Le module `billing` est reporté/désactivé au lancement (`SUBSCRIPTION_ENABLED=False`). | Aucun formulaire de paiement fictif. Des messages d'information clairs sont affichés. |
