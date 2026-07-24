#!/usr/bin/env bash
# Usage: recon.sh <domain>
# Runs BBOT's subdomain-enum + cloud-enum + web-basic presets against a
# single authorized domain and stores structured output per engagement.
set -euo pipefail

if [ $# -lt 1 ]; then
  echo "Usage: $0 <domain>" >&2
  exit 1
fi

TARGET="$1"
OUTDIR="${ENGAGEMENTS_DIR:-/engagements}/$TARGET/bbot"
mkdir -p "$OUTDIR"

bbot -t "$TARGET" -p subdomain-enum cloud-enum web-basic -o "$OUTDIR"
echo "BBOT output saved under $OUTDIR"
