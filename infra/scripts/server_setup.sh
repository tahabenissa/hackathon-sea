#!/usr/bin/env bash
# Phase 9: first-time hardening of a fresh Vultr Ubuntu 24.04 instance.
# Run as root ONCE, after adding your SSH public key in the Vultr dashboard.
# Read every line before running it.
set -euo pipefail
NEW_USER="${1:?usage: server_setup.sh <username>}"

apt-get update && apt-get -y upgrade
apt-get -y install ufw fail2ban unattended-upgrades ca-certificates curl

# Non-root sudo user with the same SSH key as root
adduser --disabled-password --gecos "" "$NEW_USER"
usermod -aG sudo "$NEW_USER"
mkdir -p "/home/$NEW_USER/.ssh"
cp /root/.ssh/authorized_keys "/home/$NEW_USER/.ssh/"
chown -R "$NEW_USER:$NEW_USER" "/home/$NEW_USER/.ssh"

# SSH: keys only, no root login
sed -i 's/^#\?PasswordAuthentication .*/PasswordAuthentication no/' /etc/ssh/sshd_config
sed -i 's/^#\?PermitRootLogin .*/PermitRootLogin no/' /etc/ssh/sshd_config
systemctl restart ssh

# Host firewall (also create a Vultr Firewall group in the dashboard)
ufw default deny incoming
ufw default allow outgoing
ufw allow 22/tcp
ufw allow 80/tcp
ufw allow 443/tcp
ufw allow 8883/tcp
ufw --force enable

# Docker (official convenience script)
curl -fsSL https://get.docker.com | sh
usermod -aG docker "$NEW_USER"

echo "Done. Log in again as $NEW_USER before continuing."
