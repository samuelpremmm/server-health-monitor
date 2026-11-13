#!/bin/bash
# Runs ONCE when the server first boots (as root). Log: /var/log/user-data.log
set -euxo pipefail
exec > /var/log/user-data.log 2>&1

# 1. Install Docker and Git
apt-get update -y
apt-get install -y docker.io docker-buildx git curl
systemctl enable --now docker
usermod -aG docker ubuntu          # so the ubuntu user can run docker without sudo

# 2. Get the code
git clone ${repo_url} /home/ubuntu/server-health-monitor
chown -R ubuntu:ubuntu /home/ubuntu/server-health-monitor

# 3. Build and start the dashboard (same command as Part 2)
cd /home/ubuntu/server-health-monitor
docker build -t health-monitor:latest .
docker run -d --name health-monitor -p 5000:5000 --hostname "$(hostname)" \
  -v /:/host:ro -e DISK_PATHS=/host -e APP_VERSION=terraform \
  --restart unless-stopped health-monitor:latest

echo "USER-DATA DONE"
