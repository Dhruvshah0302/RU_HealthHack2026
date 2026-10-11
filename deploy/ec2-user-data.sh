#!/bin/bash
# Call Bell Router: first-boot setup for an Amazon Linux 2023 EC2 instance.
# Paste this whole file into "Advanced details > User data" when launching the instance.
# It installs the app, builds the React frontend and runs it on port 80 as a service.
# Secrets are NOT in here: add them to /opt/callbell/src/.env afterwards (see deploy/DEPLOY.md).
set -euxo pipefail
exec > >(tee /var/log/callbell-setup.log) 2>&1

REPO=https://github.com/Dhruvshah0302/RU_HealthHack2026.git
BRANCH=main
APP=/opt/callbell

dnf install -y git python3.11 python3.11-pip nodejs npm

id callbell &>/dev/null || useradd --system --home-dir "$APP" --shell /sbin/nologin callbell
mkdir -p "$APP"
[ -d "$APP/src/.git" ] || git clone --depth 1 -b "$BRANCH" "$REPO" "$APP/src"

python3.11 -m venv "$APP/venv"
"$APP/venv/bin/pip" install -U pip
"$APP/venv/bin/pip" install -r "$APP/src/requirements.txt"
"$APP/venv/bin/pip" install -U boto3 botocore          # Bedrock API keys need a recent version

cd "$APP/src/frontend"
npm ci --no-audit --no-fund || npm install --no-audit --no-fund
npm run build

touch "$APP/src/.env"
chmod 600 "$APP/src/.env"
chown -R callbell:callbell "$APP"

cat > /etc/systemd/system/callbell.service <<UNIT
[Unit]
Description=Call Bell Router
After=network-online.target

[Service]
User=callbell
WorkingDirectory=$APP/src
# One worker only: tickets live in memory, so every request must reach the same process.
ExecStart=$APP/venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 80 --workers 1 --proxy-headers --forwarded-allow-ips=*
AmbientCapabilities=CAP_NET_BIND_SERVICE
Restart=always

[Install]
WantedBy=multi-user.target
UNIT

systemctl daemon-reload
systemctl enable --now callbell
