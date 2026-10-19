#!/usr/bin/env bash
# Prépare un VPS Ubuntu 24.04 vierge pour Logeo (docs/deploiement-vps-pas-a-pas.md, étape 3).
#
#   À lancer une fois, en root, juste après la livraison du serveur :
#     sudo bash infra/vps/bootstrap.sh
#
# Ce qu'il fait (rejouable sans risque) :
#   1. mises à jour du système et mises à jour de sécurité automatiques ;
#   2. Docker et Docker Compose depuis le dépôt officiel de Docker ;
#   3. un utilisateur `logeo` (sans mot de passe, membre du groupe docker) qui reçoit tes clés SSH ;
#   4. SSH par clé uniquement, connexion root interdite ;
#   5. pare-feu : SSH, 80 et 443 (TCP) et 443 (UDP, HTTP/3) seulement ; fail2ban sur SSH ;
#   6. un fichier d'échange de 2 Go si le serveur n'en a pas (marge pour ffmpeg) ;
#   7. une minuterie qui redémarre les conteneurs figés (infra/vps/autoguerison.sh).
#
# Variables : UTILISATEUR (défaut logeo), PORT_SSH (défaut 22).
set -euo pipefail

UTILISATEUR="${UTILISATEUR:-logeo}"
PORT_SSH="${PORT_SSH:-22}"

etape() { printf '\n==> %s\n' "$1"; }
[ "$(id -u)" -eq 0 ] || { echo "À lancer en root (sudo bash infra/vps/bootstrap.sh)." >&2; exit 1; }
# shellcheck source=/dev/null
. /etc/os-release
[ "${ID:-}" = "ubuntu" ] || { echo "Prévu pour Ubuntu (24.04) ; système détecté : ${PRETTY_NAME:-inconnu}." >&2; exit 1; }

# Une session SSH par clé doit exister avant de couper les mots de passe, sinon on s'enfermerait dehors.
CLES_ROOT=/root/.ssh/authorized_keys
if [ ! -s "$CLES_ROOT" ] && [ ! -s "/home/$UTILISATEUR/.ssh/authorized_keys" ]; then
  echo "Aucune clé SSH trouvée : ajoute ta clé publique dans $CLES_ROOT avant de lancer ce script." >&2
  exit 1
fi

export DEBIAN_FRONTEND=noninteractive

etape "Mises à jour du système"
apt-get update -q
apt-get -yq upgrade
apt-get install -yq ca-certificates curl git gnupg ufw fail2ban unattended-upgrades

etape "Mises à jour de sécurité automatiques"
cat > /etc/apt/apt.conf.d/20auto-upgrades <<'CONF'
APT::Periodic::Update-Package-Lists "1";
APT::Periodic::Unattended-Upgrade "1";
CONF

etape "Docker (dépôt officiel)"
if ! command -v docker >/dev/null 2>&1; then
  install -m 0755 -d /etc/apt/keyrings
  curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
  chmod a+r /etc/apt/keyrings/docker.asc
  echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu ${VERSION_CODENAME} stable" \
    > /etc/apt/sources.list.d/docker.list
  apt-get update -q
  apt-get install -yq docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
fi
systemctl enable --now docker
# Journaux des conteneurs bornés (sinon ils remplissent le disque).
if [ ! -f /etc/docker/daemon.json ]; then
  cat > /etc/docker/daemon.json <<'CONF'
{ "log-driver": "json-file", "log-opts": { "max-size": "20m", "max-file": "5" } }
CONF
  systemctl restart docker
fi

etape "Utilisateur $UTILISATEUR"
if ! id "$UTILISATEUR" >/dev/null 2>&1; then
  adduser --disabled-password --gecos "Logeo" "$UTILISATEUR"
fi
usermod -aG docker "$UTILISATEUR"
install -d -m 700 -o "$UTILISATEUR" -g "$UTILISATEUR" "/home/$UTILISATEUR/.ssh"
if [ -s "$CLES_ROOT" ]; then
  cat "$CLES_ROOT" >> "/home/$UTILISATEUR/.ssh/authorized_keys"
  sort -u -o "/home/$UTILISATEUR/.ssh/authorized_keys" "/home/$UTILISATEUR/.ssh/authorized_keys"
fi
chown "$UTILISATEUR:$UTILISATEUR" "/home/$UTILISATEUR/.ssh/authorized_keys"
chmod 600 "/home/$UTILISATEUR/.ssh/authorized_keys"

etape "SSH : clés uniquement, root interdit"
cat > /etc/ssh/sshd_config.d/10-logeo.conf <<CONF
Port $PORT_SSH
PermitRootLogin no
PasswordAuthentication no
KbdInteractiveAuthentication no
PubkeyAuthentication yes
CONF
sshd -t
systemctl reload ssh

etape "Pare-feu et fail2ban"
ufw default deny incoming
ufw default allow outgoing
ufw allow "$PORT_SSH"/tcp
ufw allow 80/tcp
ufw allow 443/tcp
ufw allow 443/udp
ufw --force enable
cat > /etc/fail2ban/jail.d/logeo.conf <<CONF
[sshd]
enabled = true
port = $PORT_SSH
maxretry = 5
bantime = 1h
CONF
systemctl enable --now fail2ban
systemctl restart fail2ban

etape "Fichier d'échange"
if ! swapon --show | grep -q .; then
  fallocate -l 2G /swapfile
  chmod 600 /swapfile
  mkswap /swapfile
  swapon /swapfile
  grep -q '^/swapfile' /etc/fstab || echo '/swapfile none swap sw 0 0' >> /etc/fstab
fi

etape "Redémarrage automatique des conteneurs figés (chaque minute)"
# Le script vit dans le dépôt : la minuterie ne s'exécute qu'une fois le code récupéré (étape 4 du guide).
cat > /etc/systemd/system/logeo-autoguerison.service <<CONF
[Unit]
Description=Logeo : redémarre les conteneurs qui ne répondent plus
ConditionPathExists=/home/$UTILISATEUR/logeo/infra/vps/autoguerison.sh

[Service]
Type=oneshot
ExecStart=/bin/bash /home/$UTILISATEUR/logeo/infra/vps/autoguerison.sh
CONF
cat > /etc/systemd/system/logeo-autoguerison.timer <<'CONF'
[Unit]
Description=Logeo : vérification des conteneurs chaque minute

[Timer]
OnBootSec=2min
OnUnitActiveSec=1min

[Install]
WantedBy=timers.target
CONF
systemctl daemon-reload
systemctl enable --now logeo-autoguerison.timer

etape "Terminé"
cat <<FIN
Serveur prêt. Avant de fermer cette session, ouvre-en une NOUVELLE pour vérifier l'accès :
  ssh -p $PORT_SSH $UTILISATEUR@<adresse-du-serveur>
Puis suis l'étape 4 du guide (récupérer le code) avec cet utilisateur.
FIN
