#!/usr/bin/env bash
# Runs once on the VM (as a sudoer, through IAP SSH): updates, Docker, the repo, secrets, the stack.
# Not run yet.
set -euo pipefail

REPO=${REPO:-https://github.com/ArielSivkov/esh27-core.git}
BRANCH=${BRANCH:-claude/ecosystem-management-service-7yu9yk}
DIR=/opt/crown

sudo apt-get update
sudo DEBIAN_FRONTEND=noninteractive apt-get -y upgrade
sudo DEBIAN_FRONTEND=noninteractive apt-get -y install unattended-upgrades docker.io docker-compose-v2 git ufw
sudo dpkg-reconfigure -f noninteractive unattended-upgrades

# Host firewall as a second layer: nothing in except SSH from IAP.
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow from 35.235.240.0/20 to any port 22 proto tcp
sudo ufw --force enable

[ -d "$DIR/.git" ] || sudo git clone --branch "$BRANCH" "$REPO" "$DIR"
sudo "$DIR/deploy/vm/fetch-secrets.sh"
cd "$DIR/deploy/vm" && sudo docker compose up -d --build
sudo docker compose ps
