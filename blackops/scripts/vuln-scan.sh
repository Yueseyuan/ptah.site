#!/usr/bin/env bash
# Usage: vuln-scan.sh <targets-file-or-single-host>
# Runs Nuclei with the current template set. Pass a file (one host per line)
# or a single URL/host.
set -euo pipefail

if [ $# -lt 1 ]; then
  echo "Usage: $0 <targets-file-or-single-host>" >&2
  exit 1
fi

TARGET="$1"
LABEL=$(basename "$TARGET")
OUTDIR="${ENGAGEMENTS_DIR:-/engagements}/nuclei/$(date +%Y%m%d-%H%M%S)-$LABEL"
mkdir -p "$OUTDIR"

if [ -f "$TARGET" ]; then
  TARGET_FLAG="-l"
else
  TARGET_FLAG="-u"
fi

nuclei "$TARGET_FLAG" "$TARGET" -j -o "$OUTDIR/findings.jsonl" | tee "$OUTDIR/findings.txt"

echo "Nuclei findings saved under $OUTDIR"
