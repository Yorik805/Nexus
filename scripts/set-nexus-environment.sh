#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CONFIG_FILE="$ROOT_DIR/nexus.config.json"

if ! command -v python3 >/dev/null 2>&1; then
  echo "python3 is required to read nexus.config.json" >&2
  exit 1
fi

mapfile -t CONFIG_VALUES < <(python3 - "$CONFIG_FILE" <<'PY'
import json
import sys
from pathlib import Path

config = json.loads(Path(sys.argv[1]).read_text())
print(config.get("protocol", "http"))
print(config["host"])
print(config.get("runtime_port", 8765))
print(config.get("dashboard_port", 11882))
PY
)

export NEXUS_HOST="${CONFIG_VALUES[1]}"
export NEXUS_URL="${CONFIG_VALUES[0]}://${CONFIG_VALUES[1]}:${CONFIG_VALUES[2]}"
export NEXUS_RUNTIME_URL="$NEXUS_URL"
export NEXUS_DASHBOARD_PORT="${CONFIG_VALUES[3]}"
export NEXUS_DASHBOARD_BACKEND_URL="http://${CONFIG_VALUES[1]}:${CONFIG_VALUES[3]}"

ENV_FILE="$ROOT_DIR/.env"
if [[ -f "$ENV_FILE" ]]; then
  set -a
  # shellcheck disable=SC1090
  source "$ENV_FILE"
  set +a
  echo "Loaded private provider settings from .env."
else
  echo "No .env found; provider settings were not loaded."
fi

echo "Nexus host: $NEXUS_HOST"
echo "Runtime URL: $NEXUS_RUNTIME_URL"
echo "Dashboard backend: $NEXUS_DASHBOARD_BACKEND_URL"
echo "Dashboard port: $NEXUS_DASHBOARD_PORT"
echo "Environment applied to this shell."
