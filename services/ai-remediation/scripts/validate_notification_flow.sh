#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"

echo "Phoenix-Ops AI remediation notification validation"

if [[ ! -f "${ROOT_DIR}/.env.aiops" ]]; then
  echo ".env.aiops is missing at ${ROOT_DIR}/.env.aiops"
  exit 1
fi

PYTHONPATH="${ROOT_DIR}/services/ai-remediation" \
python3 - <<'PY'
from app.config.loader import load_config
from app.config.runtime import load_alerting_settings

config = load_config()
settings = load_alerting_settings(config)
print(
    {
        "provider": settings.provider,
        "dry_run": settings.dry_run,
        "from_email_present": bool(settings.from_email),
        "to_email_present": bool(settings.to_email),
    }
)
PY
