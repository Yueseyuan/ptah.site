#!/usr/bin/env bash
# Usage: cloud-audit.sh [aws-profile]
# Runs CloudFox against the AWS credentials available in the environment or
# the named profile. Requires AWS credentials to already be configured
# (mounted ~/.aws or AWS_* env vars) — this script doesn't manage those.
set -euo pipefail

PROFILE="${1:-${AWS_PROFILE:-default}}"
OUTDIR="${ENGAGEMENTS_DIR:-/engagements}/cloudfox/$(date +%Y%m%d-%H%M%S)-$PROFILE"
mkdir -p "$OUTDIR"

cloudfox aws -p "$PROFILE" all-checks -o "$OUTDIR"
echo "CloudFox output saved under $OUTDIR"
