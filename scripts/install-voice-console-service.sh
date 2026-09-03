#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CLIENT_DIR="$ROOT_DIR/assets/web_client/nexus-voice-console"
SERVICE_DIR="$HOME/.config/systemd/user"
SERVICE_FILE="$SERVICE_DIR/nexus-voice-console.service"

if ! command -v npm >/dev/null 2>&1 && [[ -s "$HOME/.nvm/nvm.sh" ]]; then
	export NVM_DIR="$HOME/.nvm"
	# shellcheck disable=SC1091
	source "$NVM_DIR/nvm.sh"
	if ! command -v npm >/dev/null 2>&1; then
		nvm install --lts
		nvm use --lts
	fi
fi

if command -v npm >/dev/null 2>&1; then
	PACKAGE_MANAGER_PATH="$(command -v npm)"
elif command -v pnpm >/dev/null 2>&1; then
	PACKAGE_MANAGER_PATH="$(command -v pnpm)"
else
	echo "Node.js and npm or pnpm are required. Install Node.js, then run this script again." >&2
	exit 1
fi

cd "$CLIENT_DIR"
if [[ "$PACKAGE_MANAGER_PATH" == */pnpm ]]; then
	"$PACKAGE_MANAGER_PATH" install --frozen-lockfile --fetch-retries=5 --fetch-timeout=120000
else
	"$PACKAGE_MANAGER_PATH" install --fetch-retries=5 --fetch-retry-factor=2 --fetch-retry-mintimeout=5000 --fetch-retry-maxtimeout=120000 --fetch-timeout=120000
fi
"$PACKAGE_MANAGER_PATH" run build

mkdir -p "$SERVICE_DIR"
sed -e "s#%h/Nexus#$ROOT_DIR#" -e "s#__PACKAGE_MANAGER__#$PACKAGE_MANAGER_PATH#" "$ROOT_DIR/deploy/nexus-voice-console.service" > "$SERVICE_FILE"

systemctl --user daemon-reload
systemctl --user enable --now nexus-voice-console.service
loginctl enable-linger "$USER"

systemctl --user --no-pager --full status nexus-voice-console.service
