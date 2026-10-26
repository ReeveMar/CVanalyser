#!/bin/bash
# ==============================================================================
# CV Analyser - Ubuntu Server Provisioning & Deployment Script
# Target OS: Ubuntu 22.04 LTS / 24.04 LTS
# ==============================================================================

set -euo pipefail

echo "=========================================================="
echo " Starting CV Analyser Server Setup on Ubuntu Linux"
echo "=========================================================="

# Check root privileges
if [ "$EUID" -ne 0 ]; then
  echo "[-] Please run this script with sudo: sudo ./setup_ubuntu_server.sh"
  exit 1
fi

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_DIR"

echo "[+] Project Directory: $PROJECT_DIR"

# 1. Update OS Packages
echo "[+] Updating system packages..."
apt-get update -y
apt-get install -y --no-install-recommends \
    ca-certificates \
    curl \
    gnupg \
    lsb-release \
    ufw \
    openssl

# 2. Install Docker & Docker Compose Plugin
if ! command -v docker &> /dev/null; then
    echo "[+] Installing Docker Engine & Compose..."
    install -m 0755 -d /etc/apt/keyrings
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
    chmod a+r /etc/apt/keyrings/docker.asc

    echo \
      "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu \
      $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | \
      tee /etc/apt/sources.list.d/docker.list > /dev/null

    apt-get update -y
    apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
    systemctl enable docker
    systemctl start docker
    echo "[+] Docker installed successfully."
else
    echo "[*] Docker is already installed."
fi

# 3. Configure UFW Firewall
echo "[+] Configuring UFW Firewall..."
ufw allow OpenSSH || true
ufw allow 80/tcp comment 'HTTP Web Port'
ufw allow 443/tcp comment 'HTTPS SSL Port'
# Enable UFW without prompting
ufw --force enable
echo "[+] Firewall rules configured (Ports 22, 80, 443 open)."

# 4. Generate Production Secrets if .env.prod does not exist
if [ ! -f .env.prod ]; then
    echo "[+] Creating .env.prod with secure random secrets..."
    cp .env.prod.example .env.prod
    
    # Generate random 32-byte hex secrets
    RAND_SECRET_KEY=$(openssl rand -hex 32)
    RAND_DB_PASS=$(openssl rand -hex 20)
    RAND_REDIS_PASS=$(openssl rand -hex 20)

    sed -i "s/REPLACE_WITH_A_SECURE_64_CHAR_HEX_KEY/$RAND_SECRET_KEY/g" .env.prod
    sed -i "s/REPLACE_WITH_A_STRONG_DB_PASSWORD/$RAND_DB_PASS/g" .env.prod
    sed -i "s/REPLACE_WITH_A_STRONG_REDIS_PASSWORD/$RAND_REDIS_PASS/g" .env.prod

    chmod 600 .env.prod
    echo "[+] Generated random SECRET_KEY, DB password, and Redis password in .env.prod."
    echo "[!] IMPORTANT: Edit .env.prod now to add your AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, and S3_BUCKET_NAME!"
else
    echo "[*] .env.prod already exists. Preserving current secrets."
fi

# 5. Create Systemd Service for Auto-Start on Boot
echo "[+] Creating Systemd Service (cvanalyser.service)..."
cat <<EOF > /etc/systemd/system/cvanalyser.service
[Unit]
Description=CV Analyser Full Stack Production Container Suite
Requires=docker.service
After=docker.service network.target

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=$PROJECT_DIR
ExecStart=/usr/bin/docker compose --env-file .env.prod -f docker-compose.prod.yml up -d --build
ExecStop=/usr/bin/docker compose --env-file .env.prod -f docker-compose.prod.yml down
ExecReload=/usr/bin/docker compose --env-file .env.prod -f docker-compose.prod.yml restart
TimeoutStartSec=600

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable cvanalyser.service
echo "[+] Systemd service enabled for auto-start."

echo ""
echo "=========================================================="
echo " Setup Complete!"
echo "=========================================================="
echo "Next Steps:"
echo "1. Edit .env.prod with your AWS S3 credentials:"
echo "   nano .env.prod"
echo "2. Edit nginx/nginx.conf if you have a specific domain name:"
echo "   nano nginx/nginx.conf"
echo "3. Start the application:"
echo "   sudo systemctl start cvanalyser"
echo "   OR"
echo "   docker compose --env-file .env.prod -f docker-compose.prod.yml up -d --build"
echo "4. Check logs anytime:"
echo "   docker compose -f docker-compose.prod.yml logs -f"
echo "=========================================================="
