#!/usr/bin/env bash
# Usage: shodan-search.sh '<shodan-query>'
set -euo pipefail

if [ $# -lt 1 ]; then
  echo "Usage: $0 '<shodan-query>'" >&2
  exit 1
fi

if [ -z "${SHODAN_API_KEY:-}" ]; then
  echo "SHODAN_API_KEY is not set (check .env)" >&2
  exit 1
fi

QUERY="$1"
OUTDIR="${ENGAGEMENTS_DIR:-/engagements}/shodan/$(date +%Y%m%d-%H%M%S)"
mkdir -p "$OUTDIR"

shodan init "$SHODAN_API_KEY" >/dev/null
shodan search --fields ip_str,port,org,hostnames,product "$QUERY" | tee "$OUTDIR/results.txt"
echo "Results saved to $OUTDIR/results.txt"
