#!/usr/bin/env bash
# Installe la minuterie qui redémarre les conteneurs Immo+ figés (infra/vps/autoguerison.sh), là où se trouve le
# dépôt. Pour un VPS déjà préparé (VPS partagé) ; un serveur neuf passe par bootstrap.sh, qui l'installe aussi.
#   sudo bash infra/vps/installer-autoguerison.sh
# Ne touche qu'aux conteneurs du projet Compose « immoplus » : les autres applications du VPS ne sont jamais concernées.
set -euo pipefail
[ "$(id -u)" -eq 0 ] || { echo "À lancer avec sudo." >&2; exit 1; }
DEPOT="$(cd "$(dirname "$0")/../.." && pwd)"
SCRIPT="$DEPOT/infra/vps/autoguerison.sh"
[ -f "$SCRIPT" ] || { echo "Introuvable : $SCRIPT" >&2; exit 1; }

cat > /etc/systemd/system/immoplus-autoguerison.service <<CONF
[Unit]
Description=Immo+ : redémarre les conteneurs qui ne répondent plus
ConditionPathExists=$SCRIPT

[Service]
Type=oneshot
ExecStart=/bin/bash $SCRIPT
CONF
cat > /etc/systemd/system/immoplus-autoguerison.timer <<'CONF'
[Unit]
Description=Immo+ : vérification des conteneurs chaque minute

[Timer]
OnBootSec=2min
OnUnitActiveSec=1min

[Install]
WantedBy=timers.target
CONF
systemctl daemon-reload
systemctl enable --now immoplus-autoguerison.timer
echo "Minuterie active. Journal : journalctl -t immoplus-autoguerison"
