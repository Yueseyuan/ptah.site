#!/usr/bin/env bash
# Usage: new-engagement.sh <client-name>
# Scaffolds a new engagement folder: a copy of the authorization template
# (with the client name pre-filled) and, if you end up needing it, a
# phishlet-config skeleton for an authorized Evilginx3 phishing-simulation
# module. Nothing here is pre-configured to run against any target — every
# phishlet still has to be built for this specific client, and testing
# still can't start until AUTHORIZATION_TEMPLATE.md's signature section is
# actually signed.
set -euo pipefail

if [ $# -lt 1 ]; then
  echo "Usage: $0 <client-name>" >&2
  exit 1
fi

CLIENT="$1"
SLUG=$(echo "$CLIENT" | tr '[:upper:] ' '[:lower:]-' | tr -cd 'a-z0-9-')
BASE="${ENGAGEMENTS_DIR:-/engagements}/$SLUG"
TEMPLATE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

if [ -e "$BASE" ]; then
  echo "Engagement folder already exists: $BASE" >&2
  exit 1
fi

mkdir -p "$BASE/evilginx-config/phishlets" "$BASE/evilginx-config/redirectors"

sed "s/\*\*Client (authorizing party):\*\* ______________________/**Client (authorizing party):** $CLIENT/" \
  "$TEMPLATE_DIR/AUTHORIZATION_TEMPLATE.md" > "$BASE/authorization.md"

cat > "$BASE/evilginx-config/README.md" <<EOF
# Evilginx3 config — $CLIENT

Empty skeleton. Nothing runs from this folder until:

1. \`../authorization.md\` is signed, with section 5's phishing/2FA-relay
   checkbox ticked and the exact phishlet domain(s) and target population
   filled in.
2. A phishlet matching those exact domains is written into \`phishlets/\`
   (see https://github.com/kgretzky/evilginx2 for phishlet format/examples —
   there is no generic phishlet that works across clients, each one encodes
   the specific login flow being simulated).
3. You build and run the container manually for this engagement only:
   \`docker build -f docker/Dockerfile.evilginx3 -t blackops/evilginx3-$SLUG ..\`

Delete this engagement's phishlets/config once the engagement ends — don't
let them accumulate across clients.
EOF

touch "$BASE/evilginx-config/phishlets/.gitkeep" "$BASE/evilginx-config/redirectors/.gitkeep"

echo "Engagement scaffolded at $BASE"
echo "Next: fill in and sign $BASE/authorization.md before running anything."
echo "Tip: export ENGAGEMENTS_DIR=$BASE to nest recon/scan output for this client under it."
