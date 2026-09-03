#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CLIENT_DIR="$ROOT_DIR/assets/web_client/nexus-voice-console"
SERVICE_DIR="$HOME/.config/systemd/user"
SERVICE_FILE="$SERVICE_DIR/nexus-voice-console.service"
RUNTIME_SERVICE_FILE="$SERVICE_DIR/nexus.service"

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
NODE_PATH="$(command -v node)"
if [[ -x "$ROOT_DIR/.venv/bin/python" ]]; then
	PYTHON_PATH="$ROOT_DIR/.venv/bin/python"
else
	PYTHON_PATH="$(command -v python3 || true)"
fi
if [[ -z "$PYTHON_PATH" ]]; then
	echo "python3 or $ROOT_DIR/.venv/bin/python is required." >&2
	exit 1
fi

cd "$CLIENT_DIR"
if [[ ! -f "$ROOT_DIR/nexus-cert.pem" || ! -f "$ROOT_DIR/nexus-key.pem" ]]; then
	echo "HTTPS certificate files are required: $ROOT_DIR/nexus-cert.pem and $ROOT_DIR/nexus-key.pem" >&2
	echo "Copy the certificate and key to the Nexus root, then run this installer again." >&2
	exit 1
fi
echo "[1/4] Installing voice console dependencies..."
if [[ "$PACKAGE_MANAGER_PATH" == */pnpm ]]; then
	"$PACKAGE_MANAGER_PATH" install --frozen-lockfile --fetch-retries=5 --fetch-timeout=120000
else
	"$PACKAGE_MANAGER_PATH" install --no-audit --no-fund --fetch-retries=5 --fetch-retry-factor=2 --fetch-retry-mintimeout=5000 --fetch-retry-maxtimeout=120000 --fetch-timeout=120000
fi
echo "[2/4] Building voice console..."
"$PACKAGE_MANAGER_PATH" run build

echo "[3/4] Installing systemd user service..."
mkdir -p "$SERVICE_DIR"
sed -e "s#%h/Nexus#$ROOT_DIR#" -e "s#__ROOT__#$ROOT_DIR#" -e "s#__PACKAGE_MANAGER__#$PACKAGE_MANAGER_PATH#" -e "s#__NODE__#$NODE_PATH#" "$ROOT_DIR/deploy/nexus-voice-console.service" > "$SERVICE_FILE"
sed -e "s#__ROOT__#$ROOT_DIR#" -e "s#__PYTHON__#$PYTHON_PATH#" "$ROOT_DIR/deploy/nexus.service" > "$RUNTIME_SERVICE_FILE"

systemctl --user daemon-reload
echo "[4/4] Starting voice console service..."
loginctl enable-linger "$USER"
systemctl --user enable --now nexus.service
systemctl --user enable --now nexus-voice-console.service

systemctl --user --no-pager --full status nexus-voice-console.service
