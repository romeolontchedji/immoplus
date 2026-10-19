# Mettre Logeo en ligne sur un VPS, pas à pas

Ce guide part d'un serveur vierge et arrive à un site en HTTPS, une API pour l'application et une administration
réservée à l'équipe. Chaque étape donne la commande exacte et ce que tu dois voir. Si une étape ne donne pas le
résultat attendu, ne passe pas à la suivante.

## Pourquoi un VPS et pas un hébergement mutualisé

Logeo fait tourner une base PostgreSQL, deux Redis, des tâches de fond (vidéos, notifications, alertes), une connexion
temps réel pour la messagerie et un serveur web (Caddy). Un hébergement mutualisé (cPanel, « espace web ») ne permet rien
de tout cela. Il faut un **serveur virtuel (VPS)** sur lequel on installe Docker : c'est la même pile que sur ton
ordinateur (`make up`), en version production.

## Ce qu'il te faut avant de commencer

| Élément | Détail |
|---|---|
| Un VPS | Ubuntu 24.04, 4 vCPU, 8 Go de mémoire, 160 Go SSD (CDC §6). Accès root par clé SSH. |
| Un nom de domaine | Tu dois pouvoir créer des enregistrements DNS. Dans ce guide : `logeo.bj`. |
| Une clé SSH | Sur ton ordinateur : `ssh-keygen -t ed25519` puis `cat ~/.ssh/id_ed25519.pub`. |
| Une adresse IP fixe ou un VPN | L'administration n'est ouverte qu'à des adresses autorisées (voir étape 5). |
| Un agrégateur SMS | Adresse, jeton et secret de l'API d'envoi. Sans lui, personne ne peut s'inscrire. |
| Un compte Expo | Pour les notifications push et la compilation de l'application. |

## Étape 1 : choisir le VPS

1. Prends Ubuntu 24.04 et la taille ci-dessus (tu pourras grossir plus tard sans réinstaller).
2. Choisis la région avec la plus faible latence depuis Parakou. Depuis un téléphone sur MTN, Moov et Celtiis, fais
   un `ping` (application « Network Tools » ou équivalent) vers les adresses de test que fournit chaque hébergeur, et
   garde la région la plus rapide (CDC §15.2).
3. À la création, colle ta clé SSH publique. Note l'adresse IP du serveur.

**Résultat attendu :** `ssh root@<IP>` ouvre une session sans demander de mot de passe.

## Étape 2 : le DNS

Chez ton fournisseur de domaine, crée quatre enregistrements de type **A** vers l'IP du serveur :

| Nom | Sert à |
|---|---|
| `@` (domaine nu) | redirige vers `www` |
| `www` | le site |
| `api` | l'application mobile |
| `pilotage` | l'administration |

**Résultat attendu** (sur ton ordinateur, quelques minutes plus tard) : `dig +short www.logeo.bj` affiche l'IP du
serveur, de même pour `api` et `pilotage`.

## Étape 3 : préparer le serveur

Depuis le dossier du projet sur ton ordinateur :

```bash
scp infra/vps/bootstrap.sh root@<IP>:/root/
ssh root@<IP> 'bash /root/bootstrap.sh'
```

Le script met le système à jour, installe Docker, crée l'utilisateur `logeo` (avec ta clé), interdit la connexion root
et les mots de passe, ouvre seulement SSH, 80 et 443, active fail2ban et les mises à jour de sécurité automatiques.

**Résultat attendu :** le script finit par « Serveur prêt ». Dans un **nouveau** terminal, `ssh logeo@<IP>` fonctionne
et `docker ps` répond (liste vide). `ssh root@<IP>` est désormais refusé : c'est voulu.

## Étape 4 : récupérer le code

Connecté en `logeo` :

```bash
ssh-keygen -t ed25519 -C "deploiement-logeo" -f ~/.ssh/deploiement -N ""
cat ~/.ssh/deploiement.pub
```

Sur GitHub : dépôt › Settings › Deploy keys › Add deploy key, colle la clé, **sans** cocher « Allow write access ».

```bash
cat >> ~/.ssh/config <<'CONF'
Host github.com
  IdentityFile ~/.ssh/deploiement
CONF
git clone git@github.com:Magloireaffokpe/logeo.git ~/logeo
cd ~/logeo && git checkout main
```

**Résultat attendu :** le dossier `~/logeo` contient le projet, sur la branche `main`.

## Étape 5 : la configuration

```bash
cd ~/logeo
python3 outils/creer_env.py
```

Cela crée `.env` avec **tous les secrets générés** (mots de passe des bases, clés de signature). Ouvre-le
(`nano .env`) et renseigne seulement :

| Variable | Valeur |
|---|---|
| `DOMAIN` | `logeo.bj` (sans `www`) |
| `ADMIN_ALLOWED_IPS` | Ton adresse fixe ou celle de ton VPN, par ex. `203.0.113.7/32`. Une adresse de réseau mobile change souvent : un VPN (WireGuard, Tailscale) est plus fiable. Vide = administration fermée à tous. |
| `SMS_PROVIDER` | `generic_http` |
| `SMS_HTTP_URL`, `SMS_HTTP_TOKEN`, `SMS_HTTP_SECRET` | Fournis par l'agrégateur SMS |
| `PUSH_PROVIDER` | `expo` |
| `TURNSTILE_SITE_KEY`, `TURNSTILE_SECRET` | Tes clés Cloudflare (dash.cloudflare.com › Turnstile › Ajouter un site, gratuit). Les clés de test du modèle laissent tout passer : elles sont signalées comme erreur en production |
| `EMAIL_BACKEND` | vide (envoi SMTP par défaut) |
| `EMAIL_HOST`, `EMAIL_PORT`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`, `DEFAULT_FROM_EMAIL` | Ton serveur SMTP (Brevo, Gmail avec mot de passe d'application…) : indispensable, les codes de connexion à l'administration partent par courriel |
| `ERREURS_DESTINATAIRES` | Ton adresse : tu reçois un courriel à chaque nouvelle erreur (au plus un par heure et par erreur) |
| `RESTIC_REPOSITORY`, `SAUVEGARDE_CLE_ACCES`, `SAUVEGARDE_CLE_SECRETE` | Le compartiment de stockage des sauvegardes chez un autre fournisseur (étape 10) |

Ne touche pas aux secrets. Régénère ensuite les fichiers des services **sans changer les secrets** :

```bash
python3 outils/creer_env.py --services
```

> ⚠️ N'utilise jamais `--force` sur un serveur en service : il génère de nouveaux mots de passe et la base existante ne
> s'ouvrirait plus.

**Copie `.env` dans un coffre de mots de passe de l'équipe** (Bitwarden, 1Password…). Sans lui, une restauration est
impossible.

**Résultat attendu :** `ls infra/compose/env/*.env` liste dix fichiers, et `grep DOMAIN infra/compose/env/web-api.env`
affiche ton domaine.

## Étape 6 : démarrer

Crée un raccourci (à ajouter aussi dans `~/.bashrc`) :

```bash
alias logeo='docker compose --env-file .env -f infra/compose/docker-compose.yml -f infra/compose/docker-compose.prod.yml --profile prod'
```

Puis :

```bash
logeo build          # construit l'image (5 à 10 minutes la première fois)
logeo up -d          # migrations, fichiers statiques, puis tous les services
logeo ps             # état des services
```

**Résultat attendu :** dans `logeo ps`, `migrer` est « exited (0) » et tous les autres sont « running (healthy) ».
Si un service redémarre en boucle : `logeo logs <service> --tail 50`.

Caddy obtient seul les certificats HTTPS au premier accès (le DNS de l'étape 2 doit être en place).

## Étape 7 : vérifier

```bash
curl -fsS https://api.logeo.bj/healthz     # {"status": "ok"} : le processus répond
curl -fsS https://api.logeo.bj/readyz      # base, cache, file et disque prêts
curl -sI https://logeo.bj | head -3         # 301 vers https://www.logeo.bj/
```

Ouvre `https://www.logeo.bj` dans un navigateur : le cadenas doit être présent.
`https://pilotage.logeo.bj` doit répondre **404** depuis une adresse non autorisée (c'est voulu), et la page de
connexion depuis une adresse de `ADMIN_ALLOWED_IPS`.

## Étape 8 : données de base et premier administrateur

```bash
logeo run --rm admin python manage.py seed      # paramètres par défaut et quartiers de Parakou (sans annonces de démo)
logeo run --rm admin python manage.py creer_personnel --email toi@logeo.bj --nom "Ton nom" --role admin
```

Le mot de passe est demandé au clavier (il n'apparaît pas dans l'historique).

Connecte-toi ensuite sur `https://pilotage.logeo.bj` et, dans **Paramètres**, complète au minimum :

- **Contact et identité légale** : numéro de l'équipe, raison sociale, RCCM, IFU, adresse, puis décoche « identité
  provisoire ».
- **Application et maintenance** : version minimale de l'application.

## Étape 9 : l'application mobile

Dans `mobile/.env` (ou dans les variables du service de compilation Expo) :

```bash
EXPO_PUBLIC_API_URL=https://api.logeo.bj
EXPO_PUBLIC_WEB_HOST=www.logeo.bj
EAS_PROJECT_ID=<identifiant donné par `eas init`>
```

Compile avec `eas build`, puis complète `infra/caddy/wellknown/assetlinks.json` (identifiant du paquet Android et
empreinte de signature donnée par `eas credentials`) pour que les liens `https://www.logeo.bj/annonces/…` ouvrent
l'application. Redémarre Caddy : `logeo restart caddy`.

## Étape 10 : sauvegardes

Chaque nuit, le service `backup` (ADR 0008) :

1. sauvegarde la base (`pg_dump`), **vérifie qu'elle est complète**, et en garde 14 sur le serveur ;
2. si `RESTIC_REPOSITORY` est renseigné, envoie une **copie chiffrée** des sauvegardes de la base **et des photos et
   vidéos** chez un autre fournisseur, avec restic (conservation : 14 jours puis 8 semaines).

**Mettre en place la copie hors du serveur (15 minutes) :**

1. Crée un compte chez Backblaze B2 ou Cloudflare R2 (autre fournisseur que le VPS), un compartiment privé
   `logeo-sauvegardes` et une clé d'accès limitée à ce compartiment.
2. Renseigne dans `.env` : `RESTIC_REPOSITORY` (ex. `s3:https://s3.eu-central-003.backblazeb2.com/logeo-sauvegardes`),
   `SAUVEGARDE_CLE_ACCES`, `SAUVEGARDE_CLE_SECRETE`. `RESTIC_PASSWORD` a été généré à l'étape 5 : **copie-le dans le
   coffre de l'équipe**, sans lui les sauvegardes sont illisibles.
3. `python3 outils/creer_env.py --services && logeo up -d backup`
4. Lance une passe tout de suite et vérifie le message « copie chiffrée hors serveur terminée » :
   `logeo exec backup bash /scripts/boucle.sh une-fois`

**Test de restauration** (avant l'ouverture, puis chaque trimestre, sur un serveur de test) :

```bash
logeo exec backup restic restore latest --target /tmp/restauration     # récupère base et médias
gunzip -c /tmp/restauration/backups/logeo-<date>.sql.gz | logeo exec -T postgres psql -U postgres -d logeo
```

Tant que la copie hors serveur n'est pas configurée, le journal du service `backup` le rappelle chaque nuit.

## Conteneurs figés

`bootstrap.sh` installe une minuterie qui, chaque minute, redémarre un conteneur qui ne répond plus (au plus 3 fois
par heure, ensuite il faut intervenir). Historique : `journalctl -t logeo-autoguerison`.

## Mettre à jour

```bash
cd ~/logeo
git pull
logeo build
logeo up -d          # applique les nouvelles migrations puis redémarre les services modifiés
logeo ps
```

Avant une mise à jour importante, lance une sauvegarde à la main :
`logeo run --rm backup bash /scripts/boucle.sh une-fois`.

## Revenir en arrière

```bash
git log --oneline -5             # repère la version précédente
git checkout <commit>
logeo build && logeo up -d
```

Si la mise à jour contenait une migration de base, restaure aussi la sauvegarde faite juste avant (étape 10).

## Surveiller

Crée une surveillance externe gratuite (UptimeRobot, Better Stack…) sur `https://api.logeo.bj/readyz` avec une alerte
par SMS ou e-mail. Elle te prévient si le site tombe, si la base ne répond plus ou si le disque se remplit.

## Avant d'ouvrir au public : liste de contrôle

- [ ] Agrégateur SMS branché et testé avec ton propre numéro (inscription complète).
- [ ] Notifications push testées sur Android et iPhone avec l'application compilée.
- [ ] Identité légale complétée dans les paramètres (« provisoire » décoché).
- [ ] `ADMIN_ALLOWED_IPS` limité à ton adresse ou ton VPN.
- [ ] Courriels testés : connexion à l'administration (le code arrive), et une erreur reçue par courriel.
- [ ] Vraies clés Turnstile (pas les clés de test) : rien dans Administration › Erreurs à ce sujet.
- [ ] Sauvegardes copiées hors du serveur et restauration testée.
- [ ] Surveillance externe de `/readyz` active.
- [ ] `.env` conservé dans le coffre de l'équipe.
- [ ] Crédits des photos d'ambiance complets (`docs/design/credits-photos.md`).
