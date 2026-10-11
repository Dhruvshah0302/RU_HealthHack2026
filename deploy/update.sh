#!/bin/bash
# Pull the latest code from GitHub, rebuild and restart. Run on the server: sudo bash /opt/callbell/src/deploy/update.sh
# Note: tickets are kept in memory, so a restart clears the dashboard.
set -euxo pipefail
APP=/opt/callbell
cd "$APP/src"
sudo -u callbell git pull --ff-only
"$APP/venv/bin/pip" install -q -r requirements.txt
cd frontend && (npm ci --no-audit --no-fund || npm install --no-audit --no-fund) && npm run build
chown -R callbell:callbell "$APP"
systemctl restart callbell
sleep 2 && curl -s localhost/api/health && echo
