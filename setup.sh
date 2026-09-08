#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CLIENT_DIR="$ROOT_DIR/assets/web_client/nexus-voice-console"
SERVICE_DIR="$HOME/.config/systemd/user"
SERVICE_FILE="$SERVICE_DIR/nexus-voice-console.service"
RUNTIME_SERVICE_FILE="$SERVICE_DIR/nexus.service"
DASHBOARD_SERVICE_FILE="$SERVICE_DIR/nexus-dashboard.service"

echo "=========================================================="
echo "       NEXUS FULL SYSTEM INSTALLER & SERVICE RUNNER       "
echo "=========================================================="

# 1. Check Node.js and NPM/PNPM
if ! command -v npm >/dev/null 2>&1 && [[ -s "$HOME/.nvm/nvm.sh" ]]; then
	export NVM_DIR="$HOME/.nvm"
	# shellcheck disable=SC1091
	source "$NVM_DIR/nvm.sh"
	if ! command -v npm >/dev/null 2>&1; then
		echo "[INFO] Installing Node.js LTS via nvm..."
		nvm install --lts
		nvm use --lts
	fi
fi

if command -v npm >/dev/null 2>&1; then
	PACKAGE_MANAGER_PATH="$(command -v npm)"
elif command -v pnpm >/dev/null 2>&1; then
	PACKAGE_MANAGER_PATH="$(command -v pnpm)"
else
	echo "[ERROR] Node.js and npm or pnpm are required. Install Node.js (v18+), then rerun this script." >&2
	exit 1
fi
NODE_PATH="$(command -v node)"

# 2. Check Python & Virtual Environment
if [[ ! -d "$ROOT_DIR/.venv" ]]; then
	echo "[INFO] Creating Python virtual environment at .venv..."
	if command -v python3 >/dev/null 2>&1; then
		python3 -m venv "$ROOT_DIR/.venv" 2>/dev/null || true
	fi
fi

if [[ -x "$ROOT_DIR/.venv/bin/python" ]]; then
	PYTHON_PATH="$ROOT_DIR/.venv/bin/python"
	PIP_PATH="$ROOT_DIR/.venv/bin/pip"
else
	PYTHON_PATH="$(command -v python3 || true)"
	PIP_PATH="$(command -v pip3 || command -v pip || true)"
fi

if [[ -z "$PYTHON_PATH" ]]; then
	echo "[ERROR] Python 3 is required but not found. Please install python3." >&2
	exit 1
fi

# 3. Check and Install Python Dependencies
echo "[1/5] Checking and installing Python dependencies..."
if [[ -n "$PIP_PATH" ]]; then
	REQ_FILE="$ROOT_DIR/requirements.txt"
	if [[ ! -f "$REQ_FILE" ]]; then
		REQ_FILE="$ROOT_DIR/assets/requirements.txt"
	fi
	if [[ -f "$REQ_FILE" ]]; then
		"$PIP_PATH" install -r "$REQ_FILE" --quiet || "$PIP_PATH" install --break-system-packages -r "$REQ_FILE" --quiet || echo "[WARN] Python package install encountered a warning, continuing..."
	fi
else
	echo "[WARN] pip not found. Please ensure Python dependencies (faster-whisper, websockets, etc.) are installed."
fi

# 4. Check & Generate SSL Certificates if missing
echo "[2/5] Verifying SSL certificates for Voice Console..."
if [[ ! -f "$ROOT_DIR/nexus-cert.pem" || ! -f "$ROOT_DIR/nexus-key.pem" ]]; then
	echo "[INFO] Generating self-signed SSL certificate (nexus-cert.pem / nexus-key.pem)..."
	if command -v openssl >/dev/null 2>&1; then
		openssl req -x509 -newkey rsa:2048 -nodes -sha256 \
			-keyout "$ROOT_DIR/nexus-key.pem" \
			-out "$ROOT_DIR/nexus-cert.pem" \
			-days 3650 \
			-subj "/CN=nexus-server" 2>/dev/null || true
		chmod 600 "$ROOT_DIR/nexus-key.pem" 2>/dev/null || true
		echo "[OK] Generated self-signed SSL certificates."
	else
		echo "[WARN] openssl not found; unable to auto-generate SSL certs."
	fi
else
	echo "[OK] SSL certificates found."
fi

# 5. Install Voice Console Dependencies & Build
echo "[3/5] Installing Voice Console web dependencies..."
cd "$CLIENT_DIR"
if [[ "$PACKAGE_MANAGER_PATH" == */pnpm ]]; then
	"$PACKAGE_MANAGER_PATH" install --frozen-lockfile --fetch-retries=5 --fetch-timeout=120000
else
	"$PACKAGE_MANAGER_PATH" install --no-audit --no-fund --fetch-retries=5 --fetch-retry-factor=2 --fetch-retry-mintimeout=5000 --fetch-retry-maxtimeout=120000 --fetch-timeout=120000
fi

echo "[4/5] Building Voice Console Next.js application..."
"$PACKAGE_MANAGER_PATH" run build

# 6. Install & Configure Systemd User Services
echo "[5/5] Configuring systemd user services for all 3 components..."
mkdir -p "$SERVICE_DIR"
sed -e "s#%h/Nexus#$ROOT_DIR#" -e "s#__ROOT__#$ROOT_DIR#" -e "s#__PACKAGE_MANAGER__#$PACKAGE_MANAGER_PATH#" -e "s#__NODE__#$NODE_PATH#" "$ROOT_DIR/deploy/nexus-voice-console.service" > "$SERVICE_FILE"
sed -e "s#__ROOT__#$ROOT_DIR#" -e "s#__PYTHON__#$PYTHON_PATH#" "$ROOT_DIR/deploy/nexus.service" > "$RUNTIME_SERVICE_FILE"
sed -e "s#__ROOT__#$ROOT_DIR#" -e "s#__PYTHON__#$PYTHON_PATH#" "$ROOT_DIR/deploy/nexus-dashboard.service" > "$DASHBOARD_SERVICE_FILE"

systemctl --user daemon-reload
loginctl enable-linger "$USER" 2>/dev/null || true

# Enable all 3 services for auto-start
systemctl --user enable nexus.service
systemctl --user enable nexus-dashboard.service
systemctl --user enable nexus-voice-console.service

# Cleanly restart all 3 services with latest updates
systemctl --user restart nexus.service
systemctl --user restart nexus-dashboard.service
systemctl --user restart nexus-voice-console.service

echo ""
echo "=========================================================="
echo "               NEXUS ALL SERVICES ACTIVE                  "
echo "=========================================================="
systemctl --user --no-pager --full status nexus.service | grep -E 'Active:|Loaded:' || true
systemctl --user --no-pager --full status nexus-dashboard.service | grep -E 'Active:|Loaded:' || true
systemctl --user --no-pager --full status nexus-voice-console.service | grep -E 'Active:|Loaded:' || true
echo "----------------------------------------------------------"
echo "  1. Nexus Main Core:         http://127.0.0.1:8765"
echo "  2. Debugging Dashboard:     http://127.0.0.1:11882"
echo "  3. Voice Console (Local):   https://127.0.0.1:3001"
if command -v tailscale >/dev/null 2>&1; then
	TS_STATUS="$(tailscale serve status 2>/dev/null || true)"
	if [[ -n "$TS_STATUS" ]]; then
		echo "  4. Tailscale HTTPS URL:     $TS_STATUS"
	fi
fi
echo "=========================================================="
echo "Logs: journalctl --user -u nexus.service -f"
echo "      journalctl --user -u nexus-dashboard.service -f"
echo "      journalctl --user -u nexus-voice-console.service -f"
echo "=========================================================="
