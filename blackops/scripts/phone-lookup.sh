#!/usr/bin/env bash
# Usage: phone-lookup.sh <phone-number-e164>
set -euo pipefail

if [ $# -lt 1 ]; then
  echo "Usage: $0 <phone-number-e164, e.g. +18645551234>" >&2
  exit 1
fi

NUMBER="$1"
OUTDIR="${ENGAGEMENTS_DIR:-/engagements}/phoneinfoga/$(date +%Y%m%d-%H%M%S)"
mkdir -p "$OUTDIR"

phoneinfoga scan -n "$NUMBER" | tee "$OUTDIR/results.txt"
echo "PhoneInfoga results saved under $OUTDIR/results.txt"
