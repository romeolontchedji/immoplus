# Capacité d'Immo+ : combien d'utilisateurs en même temps ?

> Mesuré le 21 octobre 2026 sur la branche `feat/refonte-design-web`. À refaire sur le VPS réel avant l'ouverture
> (section 6) : les chiffres ci-dessous viennent d'un ordinateur de développement.

## 1. La réponse courte

| Configuration | Utilisateurs **actifs** en même temps, confortablement | Pointe supportée | Connectés sans rien faire (application ouverte) |
|---|---|---|---|
| Avant ce changement (2 processus) | ~250 | ~450 | plusieurs milliers |
| **Réglage livré (3 processus, `WEB_CONCURRENCY=3`)** | **~400** | **~700** | plusieurs milliers |
| Serveur dédié de 8 cœurs (9 processus) | ~1 200 | ~2 000 | plusieurs milliers |

Ces chiffres valent **pour le site et l'application ensemble** : les deux passent par le même serveur (`web-api`).
Un « utilisateur actif » fait une action toutes les 10 secondes environ (ouvrir une fiche, filtrer, envoyer un
message). Avec en général 2 à 5 % des inscrits actifs au même moment, cela correspond à **10 000 à 20 000 comptes**,
largement de quoi lancer Immo+ à Parakou. Le nombre total d'inscrits n'est pas une limite : la base les range sans
peine.

**Plus important que le processeur** : jusqu'ici, les limites de débit étaient comptées **par adresse IP**. Au Bénin,
des centaines d'abonnés d'un opérateur mobile ou d'étudiants sur le Wi-Fi du campus sortent par la même adresse
(CGNAT). Tout un campus aurait été bloqué à 30 connexions par minute. C'est corrigé (section 4).

## 2. Ce qui a été mesuré

Pages réelles, base de démonstration, mode développement (plus lent que la production : débogage actif), ordinateur
de 4 cœurs qui faisait tourner en même temps le générateur de charge. Outil : `outils/mesurer_charge.py`.

| Page | Requêtes SQL | Temps d'une requête seule | 2 processus | 3 processus |
|---|---|---|---|---|
| Accueil `/` | 1 | 7 ms | 114 req/s | 154 req/s |
| Catalogue `/annonces` | 4 | 14 ms | 54 à 75 req/s | 102 req/s |
| Recherche `/annonces?q=ba` | 4 | 15 ms | 50 req/s | — |
| Fiche d'une chambre | 12 | 44 ms | 24 req/s | 41 req/s |

Aucun problème de requêtes en cascade : chaque page fait un petit nombre de requêtes fixes.

## 3. D'où viennent les chiffres

**Un processus traite une requête à la fois.** Le site et l'API sont du Django synchrone servi par Gunicorn et
Uvicorn : chaque processus exécute les vues l'une après l'autre. Le débit maximal est donc environ
`nombre de processus ÷ temps moyen d'une requête`. Les mesures le confirment : passer de 2 à 3 processus fait passer
le catalogue de ~60 à ~100 requêtes par seconde.

**Calcul.** Pour un usage typique (50 % catalogue et recherche, 30 % fiches, 10 % accueil, 10 % messages, favoris et
notifications), 3 processus tiennent environ **70 requêtes par seconde en mode développement**, 90 à 140 en
production. À une requête toutes les 10 secondes par utilisateur actif, cela fait ~700 utilisateurs à saturation. On
vise 60 % d'occupation pour garder de la marge, d'où ~400 « confortablement ».

**Ce qui ne coûte rien à Django** : les photos, les vidéos, les feuilles de style et les scripts sont servis
directement par Caddy (ou par Cloudinary), sans passer par un processus Python. Le fil des annonces est en cache
60 secondes.

## 4. Les autres limites, une par une

| Ressource | Limite | Ce qui se passe à la limite | Levier |
|---|---|---|---|
| Processus du site et de l'API | `WEB_CONCURRENCY` (3) | Temps de réponse qui s'allongent, puis erreurs 502/504 de Caddy | Monter `WEB_CONCURRENCY` tant qu'il reste du processeur et ~100 Mo de mémoire par processus |
| **Limites de débit** | **Par compte** pour les connectés (240 lectures, 60 écritures par minute) ; **par adresse IP** pour les anonymes : 60 × `RATE_IP_FACTOR` (3), et 240 × 3 pour le fil ; connexions et inscriptions : `AUTH_RATE_PER_MIN_IP` (60 par minute) | « Trop de requêtes » (429) | Administration › Paramètres › Sécurité, effet en 30 s (`docs/administration.md` §5.9) |
| Messagerie en direct (WebSocket) | 1 processus asynchrone (`realtime`) : quelques Ko par connexion | Au-delà de plusieurs milliers de connexions, mémoire | Ajouter des processus `realtime` (les messages passent par Redis) |
| Bande passante (photos, vidéos) | Celle du VPS (à vérifier chez LWS) | Pages lentes à s'afficher, vidéos qui coupent | **Cloudinary** (ADR 0010) : les médias partent de son réseau, plus du VPS |
| Traitement des médias | 1 à la fois (`worker-media`) : une photo ~1 s, une vidéo quelques dizaines de secondes | Les gérants attendent quelques minutes un jour d'affluence ; rien n'est perdu | Accepté : c'est rare, et cela protège le serveur |
| Base de données | 100 connexions ; 10 par processus | Aucune à cette échelle | — |
| Mémoire | ~0,9 Go au repos pour toute la pile ; jusqu'à +1,5 Go pendant une vidéo ; +100 Mo par processus web | Le système tue un conteneur, qui redémarre | Prévoir **3 Go** pour Immo+ sur le VPS partagé |

Les comptes connectés ne partagent jamais leur compteur, même derrière la même adresse. Les visiteurs anonymes, eux,
le partagent : `RATE_IP_FACTOR` triple déjà les plafonds historiques, et se monte depuis l'administration un jour de
rentrée ou de lancement.

## 5. Sur le VPS partagé rmeolab

Le processeur et la mémoire sont **partagés avec les autres applications** du serveur (système de présence, etc.) :
leur activité réduit la nôtre. Vérifie la machine (étape 5 du guide de déploiement) :

```bash
nproc          # nombre de cœurs
free -h        # mémoire totale et disponible
df -h /        # disque
```

| Cœurs du VPS | `WEB_CONCURRENCY` conseillé |
|---|---|
| 2 | 2 |
| 4 (cas probable d'un VPS M) | 3 |
| 6 et plus, ou serveur dédié | cœurs + 1 |

Après modification de `WEB_CONCURRENCY` dans `.env` : `python3 outils/creer_env.py --services`, puis
`bash infra/vps/deployer.sh`.

## 6. Refaire la mesure sur le VPS

Avant l'ouverture, une fois le site en ligne, depuis le VPS (hors heures d'usage des autres applications) :

```bash
cd ~/apps/immoplus
python3 outils/mesurer_charge.py https://www.immoplus.bj/ --fils 10 --duree 15
python3 outils/mesurer_charge.py https://www.immoplus.bj/annonces --fils 10 --duree 15
python3 outils/mesurer_charge.py "https://www.immoplus.bj/annonces?q=ba" --fils 20 --duree 15
docker stats --no-stream      # dans un second terminal pendant la mesure : processeur et mémoire
```

Lecture : le **débit** (requêtes par seconde) divisé par 0,1 donne le nombre d'utilisateurs actifs à saturation ; en
prendre 60 % pour le confort. Les pages du site ne sont pas plafonnées par adresse ; l'API (`api.immoplus.bj`) l'est
pour les anonymes : un « 429 » mesure la limite, pas le serveur.

## 7. Signes qu'il faut agir, et dans quel ordre

Signes : réponses de plus d'une seconde, erreurs 502 ou 504, `docker stats` qui montre `immoplus-web-api` à 100 %
de processeur de façon durable, plaintes « Trop de requêtes ».

1. « Trop de requêtes » seulement : monter `RATE_IP_FACTOR` ou `AUTH_RATE_PER_MIN_IP` (administration).
2. Processeur libre mais réponses lentes : monter `WEB_CONCURRENCY`.
3. Bande passante ou disque qui saturent : activer Cloudinary (`docs/administration.md` §5.8).
4. Processeur du VPS saturé : VPS plus grand, ou serveur dédié à Immo+ (annexe du guide de déploiement).
5. Au-delà (plusieurs milliers d'actifs) : base de données sur une machine à part, plusieurs serveurs derrière Caddy
   (palier 2 du cahier des charges).
