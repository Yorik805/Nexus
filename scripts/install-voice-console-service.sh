#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CLIENT_DIR="$ROOT_DIR/assets/web_client/nexus-voice-console"
SERVICE_DIR="$HOME/.config/systemd/user"
SERVICE_FILE="$SERVICE_DIR/nexus-voice-console.service"

command -v npm >/dev/null 2>&1 || { echo "npm is required." >&2; exit 1; }
NPM_PATH="$(command -v npm)"

cd "$CLIENT_DIR"
npm install
npm run build

mkdir -p "$SERVICE_DIR"
sed -e "s#%h/Nexus#$ROOT_DIR#" -e "s#__NPM__#$NPM_PATH#" "$ROOT_DIR/deploy/nexus-voice-console.service" > "$SERVICE_FILE"

systemctl --user daemon-reload
systemctl --user enable --now nexus-voice-console.service
loginctl enable-linger "$USER"

systemctl --user --no-pager --full status nexus-voice-console.service
