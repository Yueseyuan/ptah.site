#!/usr/bin/env bash
set -euo pipefail

mkdir -p "${ENGAGEMENTS_DIR:-/engagements}"

if command -v nuclei >/dev/null 2>&1; then
  nuclei -update-templates -silent || echo "warning: nuclei template update failed (offline?)"
fi

exec "$@"
