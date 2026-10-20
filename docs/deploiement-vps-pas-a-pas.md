# Mettre Immo+ en ligne, du local à la production, pas à pas

Ce guide part de ton ordinateur et arrive à Immo+ en ligne en HTTPS sur le **VPS partagé rmeolab** (LWS, Ubuntu 24.04),
à côté des autres applications de ce serveur. Chaque étape donne la commande exacte et ce que tu dois voir. Si une
étape ne donne pas le résultat attendu, ne passe pas à la suivante.

> Référence du serveur : `docs/documentation-vps-rmeolab.md` (sécurisation, Caddy central, règles d'or). Ce guide ne
> refait pas ce qui y est déjà fait : le serveur est sécurisé, Docker est installé, le Caddy central tourne.

## 0. Vue d'ensemble

```
Internet ──443──▶ Caddy central (~/apps/proxy, géré par le propriétaire du VPS)
                        │ réseau Docker partagé « web_proxy »
                        ├──▶ presence-web     (système de présence, autre projet)
                        └──▶ immoplus-web     (notre Caddy, sans port public)
                                 │ réseau « interne » (sans accès à Internet)
                                 ├──▶ web-api (site + API)   realtime (messagerie)   admin (pilotage)
                                 ├──▶ worker, worker-media, beat (tâches de fond)
                                 └──▶ postgres, redis-cache, redis-queue, backup
```

- Le **Caddy central** possède les ports 80 et 443 et obtient les certificats HTTPS de `immoplus.bj`, `www.`, `api.`
  et `pilotage.`. Il transmet tout le trafic Immo+ à **notre Caddy**, joignable sous le nom `immoplus-web`.
- **Notre Caddy** garde tout le reste : fichiers statiques et médias, limites de taille, liste blanche de
  l'administration, en-têtes de sécurité. Il ne transmet à Django que l'adresse réelle du visiteur.
- Nos bases et nos files ne sont jamais sur le réseau partagé : seuls le Caddy central et notre Caddy s'y parlent.

Ce mode est activé par la troisième surcharge `infra/compose/docker-compose.vps-partage.yml`. Sur un serveur
**dédié** à Immo+, on s'en passe : notre Caddy prend lui-même les ports 80 et 443 (`MODE=dedie`, dernière section).

### Qui fait quoi

| Action | Toi | Propriétaire du VPS (compte `romaeus`) |
|---|---|---|
| Comptes Cloudflare, Brevo, Expo, stockage des sauvegardes | ✔ | |
| DNS du domaine `immoplus.bj` | ✔ | |
| Créer ton accès au VPS (étape 4) | | ✔ |
| Ajouter le bloc Immo+ au Caddy central (étape 9) | | ✔ |
| Installer la minuterie d'autoguérison (étape 12, `sudo`) | | ✔ |
| Configurer et déployer Immo+ | ✔ | |

## 1. Ce qu'il te faut

| Élément | Détail |
|---|---|
| Le domaine `immoplus.bj` | Accès au panneau du registraire (ou à Cloudflare, étape 3). |
| Une clé SSH sur ton ordinateur | `ssh-keygen -t ed25519 -C "toi@immoplus"` puis `cat ~/.ssh/id_ed25519.pub`. |
| Un compte Cloudflare | Gratuit. Anti-robot Turnstile, et si tu veux le DNS et le stockage des sauvegardes. |
| Un compte Brevo (ou un autre SMTP) | Gratuit jusqu'à 300 courriels par jour : mot de passe oublié, codes de l'administration. |
| Un compte Expo | Gratuit. Notifications push et compilation de l'application. |
| Une adresse IP fixe ou un VPN | L'administration n'est ouverte qu'à des adresses autorisées (étape 6). |
| Un coffre de mots de passe d'équipe | Bitwarden, 1Password… : `.env`, clés Cloudflare, Brevo, sauvegardes. |

Plus aucun fournisseur SMS n'est nécessaire (ADR 0009) : l'inscription se fait par nom d'utilisateur.

## 2. En local : préparer une version à mettre en ligne

Sur ton ordinateur, dans le dossier du projet :

```bash
make verifier              # tous les contrôles (ceux de la CI) : tout doit être ✔
git status                 # rien en attente
```

Fusionne ta branche de travail dans `main` par une demande de fusion sur GitHub (le hook refuse un envoi direct sur
`main`), puis :

```bash
git checkout main && git pull
git tag -a v1.0.0 -m "Première mise en production"     # optionnel : un repère pour revenir en arrière
git push && git push --tags
```

Si `origin` pousse vers deux dépôts (ton dépôt et celui de romeolontchedji), les deux reçoivent la version.

**Résultat attendu :** la CI GitHub est verte sur `main`.

## 3. Le compte Cloudflare

### 3.1 Créer et sécuriser le compte

1. Va sur **dash.cloudflare.com**, crée un compte avec l'adresse e-mail de l'équipe (pas une adresse personnelle qui
   pourrait disparaître).
2. **Profil › Authentification › Double authentification** : active-la (application TOTP), garde les codes de secours
   dans le coffre de l'équipe.
3. Si plusieurs personnes gèrent Immo+ : **Gérer le compte › Membres** et invite-les avec le rôle strictement
   nécessaire, plutôt que de partager le mot de passe.

### 3.2 Turnstile (anti-robot de l'inscription et du mot de passe oublié)

1. Menu **Turnstile › Ajouter un widget**.
2. Nom : `Immo+ site`. Noms d'hôte : `immoplus.bj` et `www.immoplus.bj`.
3. Mode : **Géré** (Cloudflare n'affiche une case à cocher qu'aux visiteurs suspects).
4. Valide : Cloudflare affiche la **clé du site** (publique) et la **clé secrète**. Copie les deux dans le coffre.
   Elles iront dans `.env` à l'étape 6 (`TURNSTILE_SITE_KEY`, `TURNSTILE_SECRET`).

En développement, on garde les clés de test du modèle `.env.example`, qui réussissent toujours. En production, les clés
de test sont signalées comme une erreur dans l'administration (page **Erreurs**).

Si la clé secrète fuit : Turnstile › le widget › **Faire tourner la clé secrète**, puis mets la nouvelle dans `.env`
et relance `bash infra/vps/deployer.sh`.

### 3.3 Le DNS du domaine (deux possibilités)

**Possibilité A, la plus simple : chez le registraire du `.bj`.** Garde le DNS où il est et crée les quatre
enregistrements de l'étape 3.4.

**Possibilité B : confier le DNS à Cloudflare** (gratuit, propagation rapide, enregistrements SPF et DKIM faciles) :

1. **Ajouter un domaine** › `immoplus.bj` › offre **Free**.
2. Cloudflare donne deux serveurs de noms (`xxx.ns.cloudflare.com`). Chez le registraire du `.bj`, remplace les
   serveurs de noms par ceux-là. Certains registraires `.bj` le font sur demande par courriel ; la bascule prend de
   quelques heures à 48 h.
3. Crée les enregistrements de l'étape 3.4 dans **DNS › Enregistrements**.

> ⚠️ **Nuage gris (« DNS uniquement »), pas orange.** Avec le nuage orange, Cloudflare s'interposerait devant le
> serveur. Le Caddy central ne pourrait plus obtenir les certificats aussi simplement, et Immo+ verrait l'adresse de
> Cloudflare au lieu de celle des visiteurs : verrouillage des connexions et liste blanche de l'administration seraient
> faussés. Reste en gris.

### 3.4 Les enregistrements DNS

Quatre enregistrements de type **A** vers l'adresse du VPS (`213.156.133.76`), durée de vie 300 s au début :

| Nom | Sert à |
|---|---|
| `@` (domaine nu) | redirige vers `www` |
| `www` | le site |
| `api` | l'application mobile |
| `pilotage` | l'administration |

**Résultat attendu** (sur ton ordinateur, après propagation) : `dig +short www.immoplus.bj` affiche `213.156.133.76`,
de même pour `immoplus.bj`, `api` et `pilotage` (sous Windows : `nslookup www.immoplus.bj 8.8.8.8`).

## 4. Les autres comptes

### 4.1 Courriels : Brevo (SMTP)

Immo+ envoie des courriels pour le **mot de passe oublié**, la **confirmation d'une adresse e-mail**, les **codes de
connexion à l'administration** et les **alertes d'erreurs**. Sans SMTP, personne ne peut se connecter à
l'administration.

1. Crée un compte sur **brevo.com** (offre gratuite).
2. **Expéditeurs, domaines › Domaines › Ajouter** `immoplus.bj`. Brevo donne des enregistrements DNS (TXT pour la
   vérification, **DKIM**, **SPF**, et un **DMARC** conseillé) : ajoute-les à l'étape 3.4. Sans eux, les courriels
   finissent en indésirables.
3. **SMTP et API › Clés SMTP › Générer** : note l'identifiant (adresse de connexion) et la clé.
4. Valeurs pour `.env` : `EMAIL_HOST=smtp-relay.brevo.com`, `EMAIL_PORT=587`, `EMAIL_USE_TLS=1`,
   `EMAIL_HOST_USER=<identifiant>`, `EMAIL_HOST_PASSWORD=<clé>`, `DEFAULT_FROM_EMAIL=Immo+ <no-reply@immoplus.bj>`.

### 4.2 (Facultatif) Copie des sauvegardes hors du serveur : Cloudflare R2

**Les photos, les vidéos et la base restent sur le disque du VPS** (ADR 0007) : Immo+ n'a besoin d'aucun stockage
externe pour fonctionner. R2 (le stockage de fichiers de Cloudflare, 10 Go gratuits) ne sert qu'à garder une **copie
chiffrée des sauvegardes** ailleurs que sur le VPS (ADR 0008). Sans R2, la sauvegarde de chaque nuit continue, mais
sur le même disque : si le VPS est perdu (panne LWS, erreur, piratage), base, photos et sauvegardes disparaissent
ensemble. Tu peux ouvrir sans R2 et l'ajouter plus tard : il suffit de remplir les trois lignes ci-dessous dans
`.env`, puis de relancer `deployer.sh`. Pour t'en passer, laisse-les vides et saute cette étape.

1. Cloudflare › **R2** › activer (10 Go gratuits) › **Créer un compartiment** `immoplus-sauvegardes` (privé).
2. **R2 › Gérer les jetons d'API › Créer un jeton** : permission « Lecture et écriture d'objets », limitée au seul
   compartiment `immoplus-sauvegardes`. Note l'**ID de clé d'accès**, la **clé secrète** et l'adresse
   `https://<compte>.r2.cloudflarestorage.com`.
3. Valeurs pour `.env` : `RESTIC_REPOSITORY=s3:https://<compte>.r2.cloudflarestorage.com/immoplus-sauvegardes`,
   `SAUVEGARDE_CLE_ACCES=<ID>`, `SAUVEGARDE_CLE_SECRETE=<clé>`.

### 4.3 Expo (notifications et compilation)

Crée un compte sur **expo.dev**. Il servira à l'étape 13 (`eas login`, `eas init`, `eas build`). Côté serveur, il
suffit de `PUSH_PROVIDER=expo` dans `.env`.

### 4.4 Surveillance : UptimeRobot (ou Better Stack)

Compte gratuit ; tu y ajouteras la sonde de l'étape 14.

### 4.5 (Facultatif) Cloudinary pour les photos et vidéos

Sans Cloudinary, les médias restent sur le disque du VPS : tout fonctionne. Cloudinary (offre gratuite : 25 crédits
par mois, 1 crédit = 1 Go stocké ou 1 Go diffusé) soulage le disque et surtout la bande passante du VPS partagé, car
les vidéos partent alors de son réseau mondial (ADR 0010). Tu peux l'ajouter plus tard, sans redéployer le code.

1. Crée un compte sur **cloudinary.com** (active la double authentification).
2. **Settings › API Keys** : note le **Cloud name**, l'**API Key** et l'**API Secret**.
3. Valeurs pour `.env` : `CLOUDINARY_CLOUD_NAME`, `CLOUDINARY_API_KEY`, `CLOUDINARY_API_SECRET` (laisse
   `CLOUDINARY_FOLDER=immoplus`).
4. Après le déploiement : Administration › Paramètres › **Photos et vidéos** › « Cloudinary » (détail et retour en
   arrière : `docs/administration.md` §5.8).

## 5. Ton accès au VPS

Le serveur appartient au compte `romaeus`. Pour isoler Immo+, demande-lui de créer un utilisateur dédié membre du
groupe `docker`, avec **ta** clé publique (étape 1) :

```bash
# à lancer par le propriétaire du VPS
sudo adduser --disabled-password --gecos "Immo+" immoplus
sudo usermod -aG docker immoplus
sudo install -d -m 700 -o immoplus -g immoplus /home/immoplus/.ssh
echo "<ta clé publique ssh-ed25519 …>" | sudo tee -a /home/immoplus/.ssh/authorized_keys
sudo chown immoplus:immoplus /home/immoplus/.ssh/authorized_keys && sudo chmod 600 /home/immoplus/.ssh/authorized_keys
```

> Être dans le groupe `docker` donne la main sur **tous** les conteneurs du serveur, y compris ceux des autres
> projets. Tu ne lances donc des commandes que dans le dossier d'Immo+ et jamais `docker system prune`,
> `docker volume rm` ni `docker compose down -v`.

Puis, depuis ton ordinateur :

```bash
ssh immoplus@213.156.133.76
free -h && nproc && df -h /        # mémoire, processeurs, disque libre (garde-les : docs/capacite.md §5)
docker network ls | grep web_proxy # le réseau du Caddy central doit exister
```

**Résultat attendu :** la connexion s'ouvre sans mot de passe. Immo+ a besoin d'environ **3 Go de mémoire** et
**20 Go de disque** au départ (plus les vidéos). Si la mémoire libre est juste, demande au propriétaire d'ajouter un
fichier d'échange de 2 Go (ffmpeg, qui réduit les vidéos, en consomme ponctuellement).

## 6. Récupérer le code et le configurer

### 6.1 Clé de déploiement GitHub (lecture seule)

```bash
ssh-keygen -t ed25519 -C "vps-rmeolab-immoplus" -f ~/.ssh/github_immoplus -N ""
cat ~/.ssh/github_immoplus.pub
```

Sur GitHub : dépôt `Magloireaffokpe/immoplus` › **Settings › Deploy keys › Add deploy key**, titre `VPS rmeolab`,
**sans** cocher « Allow write access ».

```bash
cat >> ~/.ssh/config <<'CONF'
Host github.com
    HostName github.com
    User git
    IdentityFile ~/.ssh/github_immoplus
    IdentitiesOnly yes
CONF
ssh -T git@github.com                       # « Hi Magloireaffokpe/immoplus! … »
mkdir -p ~/apps && git clone git@github.com:Magloireaffokpe/immoplus.git ~/apps/immoplus
cd ~/apps/immoplus && git checkout main
```

### 6.2 Le fichier `.env`

```bash
cd ~/apps/immoplus
python3 outils/creer_env.py
```

Cela crée `.env` avec **tous les secrets générés** : mots de passe des quatre rôles PostgreSQL, clés de signature,
clé des sauvegardes. Ouvre-le (`nano .env`) et renseigne seulement :

| Variable | Valeur |
|---|---|
| `DOMAIN` | `immoplus.bj` (sans `www`) |
| `ADMIN_ALLOWED_IPS` | Ton adresse fixe ou celle de ton VPN, par ex. `203.0.113.7/32`. Une adresse de réseau mobile change souvent : un VPN (WireGuard, Tailscale) est plus fiable. Vide = administration fermée à tous. |
| `PUSH_PROVIDER` | `expo` |
| `CAPTCHA_PROVIDER` | `turnstile` |
| `TURNSTILE_SITE_KEY`, `TURNSTILE_SECRET` | Tes clés (étape 3.2) |
| `EMAIL_BACKEND` | vide (envoi SMTP) |
| `EMAIL_HOST`, `EMAIL_PORT`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`, `EMAIL_USE_TLS`, `DEFAULT_FROM_EMAIL` | Brevo (étape 4.1) |
| `ERREURS_DESTINATAIRES` | Ton adresse : un courriel à chaque nouvelle erreur (au plus un par heure et par erreur) |
| `RESTIC_REPOSITORY`, `SAUVEGARDE_CLE_ACCES`, `SAUVEGARDE_CLE_SECRETE` | Cloudflare R2 (étape 4.2, facultatif : vide = pas de copie hors du VPS) |
| `CLOUDINARY_CLOUD_NAME`, `CLOUDINARY_API_KEY`, `CLOUDINARY_API_SECRET` | Cloudinary (étape 4.5, facultatif : vide = médias sur le disque du VPS) |
| `WEB_CONCURRENCY` | Processus du site et de l'API : `3` pour un VPS de 4 cœurs partagé, `2` pour 2 cœurs (`docs/capacite.md`) |

Ne touche pas aux secrets générés. Régénère ensuite les fichiers des services **sans changer les secrets** :

```bash
python3 outils/creer_env.py --services
grep -o '^[A-Z_]*=' .env | head -40        # liste les noms, jamais les valeurs
```

> ⚠️ N'utilise jamais `--force` sur un serveur en service : il génère de nouveaux mots de passe et la base existante
> ne s'ouvrirait plus.

**Copie `.env` dans le coffre de l'équipe**, sans le coller dans une messagerie. Sans lui, une restauration est
impossible (il contient aussi `RESTIC_PASSWORD`, la clé qui déchiffre les sauvegardes).

**Résultat attendu :** `ls infra/compose/env/*.env` liste les fichiers des services, et
`grep '^DOMAIN' infra/compose/env/web-api.env` affiche ton domaine.

## 7. Premier démarrage

```bash
cd ~/apps/immoplus
bash infra/vps/deployer.sh
```

Le script vérifie que le réseau `web_proxy` existe, met le code à jour, **construit l'image** (10 à 20 minutes la
première fois : ffmpeg et les dépendances Python), puis démarre la pile. Le service `migrer` applique les migrations
et rassemble les fichiers statiques avant que les processus web ne démarrent.

Pour les commandes du quotidien, crée un raccourci (ajoute-le aussi à `~/.bashrc`) :

```bash
alias immoplus='docker compose --env-file .env -f infra/compose/docker-compose.yml -f infra/compose/docker-compose.prod.yml -f infra/compose/docker-compose.vps-partage.yml --profile prod'
```

**Résultat attendu :** dans `immoplus ps`, `migrer` est « exited (0) » et les autres services sont « running
(healthy) » au bout d'une minute. Si un service redémarre en boucle : `immoplus logs <service> --tail 50`.

À ce stade, Immo+ tourne mais n'est pas encore joignable depuis Internet : le Caddy central ne le connaît pas.

## 8. Contrôle interne avant d'ouvrir

```bash
docker run --rm --network web_proxy curlimages/curl:8.10.1 -s -o /dev/null -w "%{http_code}\n" -H "Host: www.immoplus.bj" http://immoplus-web/healthz
```

**Résultat attendu :** `200`. Le Caddy central pourra donc joindre Immo+ par le réseau partagé.

## 9. Brancher Immo+ sur le Caddy central

Ordre obligatoire, comme pour toute application du serveur : **DNS en place (étape 3.4) → bloc ajouté → certificat**.

Le propriétaire du VPS ajoute au Caddyfile central le bloc fourni dans le dépôt
(`infra/caddy/central-immoplus.caddy`) :

```
immoplus.bj, www.immoplus.bj, api.immoplus.bj, pilotage.immoplus.bj {
	reverse_proxy immoplus-web:80
}
```

```bash
# par le propriétaire du VPS
cd ~/apps/proxy && nano Caddyfile        # coller le bloc
docker compose up -d                      # recharge le Caddy central
docker compose logs -f caddy              # attendre « certificate obtained successfully » pour les 4 noms (Ctrl+C)
```

Les autres applications du serveur ne sont pas touchées.

## 10. Vérifier depuis Internet

Depuis ton ordinateur :

```bash
curl -fsS https://api.immoplus.bj/healthz     # {"status": "ok"} : le processus répond
curl -fsS https://api.immoplus.bj/readyz      # base, cache, file et disque prêts
curl -sI https://immoplus.bj | head -3         # 301 vers https://www.immoplus.bj/
BASE_WWW=https://www.immoplus.bj BASE_ADMIN=https://pilotage.immoplus.bj make fumee
```

Ouvre `https://www.immoplus.bj` dans un navigateur : le cadenas doit être présent.
`https://pilotage.immoplus.bj` doit répondre **404** depuis une adresse non autorisée (c'est voulu), et la page de
connexion depuis une adresse de `ADMIN_ALLOWED_IPS`. Le test de fumée vérifie aussi l'administration : lance-le
depuis une adresse autorisée.

## 11. Données de base et premier administrateur

Ce qui existe **dès le premier démarrage**, sans rien lancer :

| Données | D'où elles viennent |
|---|---|
| Types de logement (chambre simple, chambre sanitaire, chambre-salon, entrée-coucher, meublé…) | Créés par les migrations, appliquées automatiquement au démarrage |
| Équipements (eau, électricité, douche, cuisine, cour clôturée…) et leurs choix | Écrits dans le code : rien à créer |
| Images du site (logos, illustrations, photos de l'accueil, image de partage, polices) | Incluses dans l'image Docker (`web/static/design/`) |
| Textes légaux (conditions, confidentialité) | Inclus dans le code |

Ce qu'il faut créer **une fois**, avec la commande `seed` :

| Données | Remarque |
|---|---|
| Paramètres par défaut (tous ceux de `docs/administration.md`) | Une valeur déjà modifiée dans l'administration n'est jamais écrasée |
| Les 12 quartiers de Parakou (Banikanni, Titirou, Zongo, Albarika, Madina, Arafat, Ganou, Kpébié, Guéma, Ladjifarani, Tourou, Wansirou) | Positions **approximatives** : à corriger dans Administration › Quartiers après un relevé sur le terrain ; d'autres quartiers s'y ajoutent |

`seed` peut être relancée sans risque (elle ne crée que ce qui manque). Les comptes et annonces de démonstration
(`--demo`) sont refusés en production.

```bash
immoplus run --rm admin python manage.py seed      # paramètres par défaut et quartiers de Parakou (sans annonces de démo)
immoplus run --rm admin python manage.py creer_personnel --email toi@immoplus.bj --nom "Ton nom" --role admin
```

Le mot de passe est demandé au clavier : il n'apparaît pas dans l'historique.

Connecte-toi ensuite sur `https://pilotage.immoplus.bj`. Un code de connexion arrive par courriel à chaque
connexion : s'il n'arrive pas, revois l'étape 4.1. Puis, dans **Paramètres** (détail de chaque réglage :
`docs/administration.md`), complète au minimum :

- **Contact et identité légale** : numéro WhatsApp de l'équipe, raison sociale, RCCM, IFU, adresse, puis décoche
  « identité provisoire ».
- **Application et maintenance** : version minimale de l'application.

**Premier gérant :** Administration › Comptes › **Nouveau gérant** (prénom, nom, zone) › copie le **lien
d'activation** affiché, ou envoie-le avec le bouton WhatsApp. Le gérant y choisit son nom d'utilisateur et son mot de
passe (valable 72 h, une seule fois).

## 12. Conteneurs figés et sauvegardes

### 12.1 Autoguérison

Le propriétaire du VPS installe une fois la minuterie qui redémarre un conteneur Immo+ qui ne répond plus (au plus 3
fois par heure, ensuite il faut intervenir). Elle ne touche **que** les conteneurs du projet Immo+.

```bash
# par le propriétaire du VPS, dans le dossier d'Immo+
sudo bash /home/immoplus/apps/immoplus/infra/vps/installer-autoguerison.sh
journalctl -t immoplus-autoguerison        # historique
```

### 12.2 Sauvegardes

Chaque nuit, le service `backup` (ADR 0008) :

1. sauvegarde la base (`pg_dump`), **vérifie qu'elle est complète**, et en garde 14 sur le serveur ;
2. si `RESTIC_REPOSITORY` est renseigné, envoie une **copie chiffrée** des sauvegardes de la base **et des photos et
   vidéos** vers Cloudflare R2 (conservation : 14 jours puis 8 semaines).

Lance une passe tout de suite et vérifie le message « copie chiffrée hors serveur terminée » :

```bash
immoplus exec backup bash /scripts/boucle.sh une-fois
```

**Test de restauration** (avant l'ouverture, puis chaque trimestre, sur ton ordinateur ou un serveur de test) :

```bash
immoplus exec backup restic restore latest --target /tmp/restauration     # récupère base et médias
gunzip -c /tmp/restauration/backups/immoplus-<date>.sql.gz | immoplus exec -T postgres psql -U postgres -d immoplus
```

Avant toute grosse opération sur le serveur, demande aussi au propriétaire un **instantané LWS** (bouton « annuler »
à court terme ; ce n'est pas une sauvegarde durable).

## 13. L'application mobile

L'application se compile **dans le nuage d'Expo (EAS Build)** : pas besoin d'Android Studio. Le service gratuit suffit
(file d'attente parfois longue). Tout se fait depuis ton ordinateur, dans `mobile/`.

### 13.1 Une seule fois : le projet Expo

```bash
cd mobile
npm install -g eas-cli
eas login                    # compte expo.dev de l'étape 4.3
eas init                     # crée le projet Expo et affiche son identifiant (projectId)
```

`eas init` ne peut pas écrire lui-même l'identifiant (la configuration est dans `app.config.ts`). Copie-le dans
`mobile/eas.json`, dans l'`env` des profils `preview` et `production` : `"EAS_PROJECT_ID": "<identifiant>"`, puis
commite. Sans lui, les notifications push ne fonctionnent pas. Ce n'est pas un secret.

L'adresse du serveur est déjà réglée dans `mobile/eas.json` : `https://api.immoplus.bj` et `www.immoplus.bj` pour
`preview` et `production` (le fichier `mobile/.env` ne sert qu'au développement : il n'est pas envoyé à Expo). Si le
domaine change, c'est là qu'il faut le modifier.

### 13.2 Les trois profils de compilation (`mobile/eas.json`)

| Profil | Produit | Pour quoi |
|---|---|---|
| `development` | APK de développement | Tester des modules natifs en local (rarement utile : Expo Go suffit) |
| `preview` | **APK** à installer directement | Tester sur de vrais téléphones contre la production, avant le Play Store |
| `production` | **AAB** (`.aab`) | Publier sur le Play Store ; numéro de version incrémenté automatiquement |

### 13.3 Tester sur des téléphones (APK)

```bash
eas build --platform android --profile preview
```

À la fin, Expo donne un lien et un code QR : ouvre-le sur le téléphone, télécharge l'APK et installe-le (autoriser
« sources inconnues »). Tu peux envoyer le lien à quelques testeurs.

### 13.4 Publier sur le Play Store

1. Crée un compte **Google Play Console** (25 $ une seule fois) et l'application « Immo+ ». Le nom du paquet
   `bj.immoplus.app` (`app.config.ts`) ne pourra **plus jamais changer** après la première publication.
2. Compile :

   ```bash
   eas build --platform android --profile production
   ```

3. Envoie la version (piste « tests internes », réglée dans `eas.json`) :

   ```bash
   eas submit --platform android --profile production
   ```

   La première fois, Google exige un envoi à la main du fichier `.aab` dans la Play Console, puis `eas submit`
   demande une clé de compte de service Google (la Play Console explique comment la créer).
4. Dans la Play Console : fiche (textes, captures, icône), politique de confidentialité
   (`https://www.immoplus.bj/confidentialite`), questionnaire sur les données, puis passage de « tests internes » à
   « production ».

### 13.5 Ouvrir les liens partagés dans l'application

```bash
eas credentials              # Android › production › affiche l'empreinte SHA-256 du certificat de signature
```

Colle cette empreinte dans `infra/caddy/wellknown/assetlinks.json` (`sha256_cert_fingerprints` ; le paquet
`bj.immoplus.app` y est déjà). Si l'application est publiée sur le Play Store avec la signature gérée par Google,
ajoute aussi l'empreinte affichée dans Play Console › Intégrité de l'application. Commite, pousse, puis
`bash infra/vps/deployer.sh` sur le serveur. Les liens `https://www.immoplus.bj/annonces/…` ouvriront alors
directement l'application.

Vérifie : `curl -s https://www.immoplus.bj/.well-known/assetlinks.json` affiche ton empreinte.

### 13.6 Nouvelles versions

- Change `version` dans `mobile/app.config.ts` (ex. `1.0.0` → `1.1.0`), recompile en `production`, puis
  `eas submit`.
- Pour obliger les anciennes versions à se mettre à jour : Administration › Paramètres › **version minimale de
  l'application**. Ne la monte qu'une fois la nouvelle version disponible sur le Play Store.
- Le serveur se met à jour indépendamment (étape 15) : garde l'API compatible avec les versions encore installées.

## 14. Surveiller

Dans UptimeRobot, crée une sonde HTTP(S) sur `https://api.immoplus.bj/readyz` toutes les 5 minutes, avec une alerte
par e-mail (et SMS si l'offre le permet). Elle te prévient si le site tombe, si la base ne répond plus ou si le disque
se remplit. Les erreurs de l'application arrivent, elles, par courriel (`ERREURS_DESTINATAIRES`) et dans
Administration › **Erreurs**.

## 15. Mettre à jour

À chaque nouvelle version poussée sur `main` (étape 2) :

```bash
ssh immoplus@213.156.133.76
cd ~/apps/immoplus
immoplus exec backup bash /scripts/boucle.sh une-fois      # sauvegarde juste avant (conseillé)
bash infra/vps/deployer.sh
```

Les migrations sont appliquées automatiquement par le service `migrer`. `.env` n'est jamais touché par `git pull`.
Si une version ajoute une variable à `.env.example`, ajoute-la à `.env` puis `python3 outils/creer_env.py --services`.

## 16. Revenir en arrière

```bash
git log --oneline -5             # repère la version précédente (ou un tag : git tag)
git checkout <commit-ou-tag>
immoplus up -d --build
```

Si la version annulée contenait une migration de base, restaure aussi la sauvegarde faite juste avant (étape 12.2).
Pour revenir ensuite à la version courante : `git checkout main && bash infra/vps/deployer.sh`.

## 17. Commandes utiles

```bash
immoplus ps                                  # état des services Immo+
immoplus logs -f web-api                     # journaux en direct (Ctrl+C pour quitter)
immoplus restart caddy                       # après une modification de assetlinks.json
immoplus run --rm admin python manage.py creer_personnel --email … --nom … --role moderator
docker stats --no-stream | grep immoplus     # mémoire et processeur des conteneurs Immo+
```

## 18. Règles d'or sur un serveur partagé

- ⛔ **Jamais `docker compose down -v`**, ni `docker volume rm`, ni `docker system prune` : `-v` efface la base, les
  photos et les vidéos ; `prune` peut supprimer ce qui appartient aux autres projets.
- 🧱 **Ne touche qu'à Immo+** : toujours dans `~/apps/immoplus`, toujours avec le raccourci `immoplus`. Le Caddy
  central et les autres applications relèvent du propriétaire du VPS.
- 🔐 **Secrets hors de Git** : `.env`, clés Cloudflare, Brevo et R2 vivent dans le coffre de l'équipe, jamais dans le
  dépôt ni dans une messagerie.
- 🌐 **DNS en nuage gris** si tu utilises Cloudflare (étape 3.3).
- 📸 **Instantané LWS** avant toute grosse manipulation, **sauvegarde Immo+** avant chaque mise à jour.

## 19. Avant d'ouvrir au public : liste de contrôle

- [ ] Les quatre noms répondent en HTTPS (cadenas), `make fumee` est vert depuis une adresse autorisée.
- [ ] Inscription testée sur le site et dans l'application (nom d'utilisateur, clé de secours affichée).
- [ ] Mot de passe oublié testé : par e-mail (le lien arrive) et par clé de secours.
- [ ] Un gérant activé par son lien, une annonce publiée avec 5 photos.
- [ ] Notifications push testées sur Android et iPhone avec l'application compilée.
- [ ] Identité légale complétée dans les paramètres (« provisoire » décoché).
- [ ] `ADMIN_ALLOWED_IPS` limité à ton adresse ou ton VPN.
- [ ] Courriels testés : code de connexion à l'administration reçu, une erreur reçue par courriel, pas en indésirables.
- [ ] Vraies clés Turnstile (pas les clés de test) : rien dans Administration › Erreurs à ce sujet.
- [ ] Restauration d'une sauvegarde testée (et copie sur R2 si tu as choisi de l'activer).
- [ ] Surveillance externe de `/readyz` active.
- [ ] Capacité mesurée sur le VPS (`docs/capacite.md` §6) et `WEB_CONCURRENCY` adapté au nombre de cœurs.
- [ ] Si Cloudinary est activé : une photo et une vidéo envoyées s'affichent depuis `res.cloudinary.com`.
- [ ] `.env` conservé dans le coffre de l'équipe.
- [ ] Empreinte Android dans `assetlinks.json` : un lien partagé ouvre l'application.
- [ ] Crédits des photos d'ambiance complets (`docs/design/credits-photos.md`).

## Annexe : serveur dédié à Immo+

Sur un VPS qui n'héberge qu'Immo+ (pas de Caddy central) :

1. `scp infra/vps/bootstrap.sh root@<IP>:/root/ && ssh root@<IP> 'bash /root/bootstrap.sh'` : mises à jour, Docker,
   utilisateur `immoplus`, SSH par clé seulement, pare-feu (22, 80, 443), fail2ban, fichier d'échange, autoguérison.
2. Étapes 3, 4, 6 de ce guide (le dépôt dans `~/immoplus`).
3. `MODE=dedie bash infra/vps/deployer.sh` : notre Caddy prend les ports 80 et 443 et obtient seul les certificats
   (HTTP/3 compris). Le raccourci `immoplus` s'écrit alors sans `-f infra/compose/docker-compose.vps-partage.yml`.
4. Étapes 10 à 19.
