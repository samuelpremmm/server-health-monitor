#!/usr/bin/env bash
# Schedule the health monitor to run every 5 minutes with cron.
# Usage:  bash scripts/install_cron.sh [minutes]
set -euo pipefail

MINUTES="${1:-5}"
PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
PYTHON="$(command -v python3)"
JOB="*/${MINUTES} * * * * cd ${PROJECT_DIR} && ${PYTHON} -m health_monitor --quiet >> ${PROJECT_DIR}/logs/cron.log 2>&1"

# Replace any earlier entry for this project, then add the new one.
( crontab -l 2>/dev/null | grep -v "${PROJECT_DIR} && ${PYTHON} -m health_monitor" || true; echo "${JOB}" ) | crontab -

echo "Installed cron job:"
echo "  ${JOB}"
echo "Reports will be appended to ${PROJECT_DIR}/logs/health_report.log"
