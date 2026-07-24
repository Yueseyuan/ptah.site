#!/usr/bin/env bash
# Usage: username-search.sh <username>
set -euo pipefail

if [ $# -lt 1 ]; then
  echo "Usage: $0 <username>" >&2
  exit 1
fi

USERNAME="$1"
OUTDIR="${ENGAGEMENTS_DIR:-/engagements}/sherlock/$USERNAME"
mkdir -p "$OUTDIR"

sherlock "$USERNAME" --output "$OUTDIR/results.txt" --print-found
echo "Sherlock results saved under $OUTDIR/results.txt"
