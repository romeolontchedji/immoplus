# Référencement et aperçus de partage

Ce que le site fait pour être trouvé sur Google et pour s'afficher joliment quand on partage une chambre, et ce
qu'il reste à faire **en dehors du code** (rien ne remplace ces gestes-là).

## 1. L'aperçu d'un lien partagé (WhatsApp, Facebook, Telegram, X…)

Quand on colle le lien d'une chambre (`https://www.immoplus.bj/annonces/<slug>`), la plateforme lit les balises de
la page et affiche une carte :

```
┌────────────────────────────────────────┐
│                                        │
│     photo de couverture (1200 × 630)   │   ← og:image, JPEG fabriqué à la volée
│                                        │
├────────────────────────────────────────┤
│ Chambre-salon lumineuse — 35 000 F/mois · Banikanni, Parakou      ← og:title
│ Chambre-salon · Banikanni, Parakou · à 450 m de l'Université de   ← og:description :
│ Parakou · 35 000 F/mois · douche intérieure · eau : forage ·        les caractéristiques
│ visite en vidéo · gérant vérifié.                                 │
│ www.immoplus.bj                                                   │
└────────────────────────────────────────┘
```

- **Image** : la photo de couverture, convertie en JPEG 1200 × 630 (format que toutes les messageries affichent),
  mise en cache une semaine. Sans photo, l'affiche de la vidéo ; sans rien, l'image générale d'Immo+.
- **Vidéo** : quand la chambre a une visite en vidéo, la page la déclare aussi (`og:video`, MP4). Les plateformes qui
  savent la lire dans l'aperçu (Telegram, Discord…) la proposent ; **WhatsApp, Instagram et X affichent l'image**,
  et Facebook en général aussi. Un clic ouvre la fiche, où la vidéo se lit.
- **Bouton Partager** de la fiche (site et application) : envoie le lien avec un texte court (titre, quartier, loyer).

Vérifier un aperçu : coller le lien dans https://developers.facebook.com/tools/debug/ (bouton « Scrape again »
après une modification) ou s'envoyer le lien sur WhatsApp. WhatsApp garde un aperçu en cache plusieurs jours.

## 2. Ce que voit Google

| Élément | Où | Contenu |
|---|---|---|
| Titre (`<title>`) | Chaque page | Mots-clés en tête : « Chambres à louer à Parakou… », « Chambres à louer à Banikanni, Parakou », « Chambres à louer près de l'Université de Parakou (UP) », fiche : « <titre> — à louer à <quartier>, Parakou » |
| Description | Chaque page | Résumé avec loyer, quartier, distance de l'Université de Parakou, équipements |
| **Page « près de l'université »** | `/pres-de-l-universite` | Chambres à moins de 1,5 km du campus, les plus proches d'abord, avec un titre et un paragraphe ciblés ; liée depuis le pied de page et le plan du site |
| Pages de quartier | `/quartiers/<slug>` | Une page par quartier, liée depuis le pied de page |
| Adresse canonique | Toutes les listes, l'accueil, les fiches | Une seule adresse par sujet ; les listes filtrées, triées ou paginées sont en `noindex, follow` (Google suit leurs liens sans les indexer en double) |
| Données structurées (schema.org) | Fiche : `RealEstateListing`, `Offer` (loyer en XOF par mois), `Accommodation` (quartier, coordonnées, équipements, note des avis), fil d'Ariane ; accueil : `WebSite`, `Organization` | Aident Google à comprendre la page et à l'enrichir dans les résultats |
| Plan du site | `/sitemap.xml` | Accueil, catalogue, page université, chaque quartier, chaque chambre publiée (avec date de mise à jour) |
| `robots.txt` | `/robots.txt` | Tout est ouvert sauf compte, espace gérant, connexion, inscription, mot de passe, activation |
| Technique | Partout | HTTPS, domaine nu redirigé vers `www`, pages rapides (CSS minifié, images WebP, cache), lisibles sur téléphone, `lang="fr"` |

Le texte des pages, lui, vient en grande partie des **gérants** : un titre d'annonce clair (« Chambre sanitaire à
Banikanni, 5 min de l'UP ») et une description complète comptent autant que les balises.

## 3. Ce qu'il faut faire après la mise en ligne (hébergeur)

Le code ne suffit pas : Google doit découvrir le site, et la concurrence (Facebook, groupes WhatsApp, autres sites)
se joue aussi hors du site. Sans ces étapes, une recherche « chambre à louer Parakou » ne fera **pas** sortir
Immo+, même avec des balises parfaites.

1. **Google Search Console** (gratuit) : https://search.google.com/search-console › Ajouter une propriété ›
   **Domaine** `immoplus.bj` › copier l'enregistrement **TXT** proposé › l'ajouter dans Cloudflare › DNS (ou chez le
   bureau d'enregistrement) › Valider.
2. Dans la Search Console : **Sitemaps** › ajouter `https://www.immoplus.bj/sitemap.xml`. Puis **Inspection
   d'URL** › `https://www.immoplus.bj/pres-de-l-universite` › « Demander l'indexation » (idem pour l'accueil).
3. **Bing Webmaster Tools** : importer la propriété depuis la Search Console (deux clics).
4. **Fiche d'établissement Google** (Google Business Profile) « Immo+ — location de chambres à Parakou » : apparaît
   sur Maps et dans les recherches locales ; lien vers le site, numéro WhatsApp de l'équipe.
5. **Des liens vers le site** : page Facebook et compte TikTok d'Immo+ (vidéos des chambres avec le lien), groupes
   d'étudiants de l'UP, associations, annuaires locaux. Chaque lien depuis un site connu augmente la confiance de
   Google.
6. **Patience et suivi** : les premières positions arrivent en général en quelques semaines. La Search Console montre
   les recherches qui affichent Immo+ (« chambre à louer parakou », « chambre près de l'UP »…), la position et les
   clics : regarder chaque mois et adapter les titres si besoin.

## 4. Pour l'équipe et les gérants

- Encourager des **titres d'annonce descriptifs** (type, quartier, repère) plutôt que « Belle chambre ».
- Des **avis** sur les chambres : ils apparaissent dans les données structurées (note moyenne).
- Garder les annonces **à jour** : une chambre louée sort du plan du site ; une annonce récente est mieux vue.

## 5. Fichiers concernés

`serveur/web/views_public.py` (`_seo_liste`, `_partage`, `pres_universite`, `robots`, `sitemap`), `serveur/web/views.py`
(données structurées de l'accueil), `serveur/apps/listings/services/partage.py` (image et résumé), gabarits
`web/public/annonces.html`, `resultats.html`, `fiche.html`, `web/accueil.html`, `web/base.html`. Tests :
`serveur/web/tests/test_referencement.py`, `test_partage.py`.
