#!/usr/bin/env bash
# Site Clone Tool — desktop launcher
# Works on Linux and macOS. Double-click or run directly.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# ── prompt for URL ─────────────────────────────────────────────────────────
if command -v zenity &>/dev/null; then
  # Linux with GTK (GNOME/XFCE)
  URL=$(zenity \
    --entry \
    --title="Site Clone Tool" \
    --text="Enter the website URL to clone:" \
    --entry-text="https://" \
    --width=420)

elif command -v kdialog &>/dev/null; then
  # Linux with KDE
  URL=$(kdialog --inputbox "Enter the website URL to clone:" "https://")

elif command -v osascript &>/dev/null; then
  # macOS
  URL=$(osascript -e 'Tell application "System Events" to display dialog "Enter the website URL to clone:" default answer "https://" with title "Site Clone Tool"' \
                  -e 'text returned of result' 2>/dev/null)

else
  # Fallback: plain terminal prompt
  echo ""
  echo "╔══════════════════════════════════╗"
  echo "║       SITE CLONE TOOL            ║"
  echo "╚══════════════════════════════════╝"
  echo ""
  printf "  Enter URL to clone: "
  read -r URL
fi

# cancelled or empty
[[ -z "$URL" || "$URL" == "https://" ]] && exit 0

# ── pick mode ──────────────────────────────────────────────────────────────
MODE="standard"
if command -v zenity &>/dev/null; then
  zenity --question \
    --title="Clone Mode" \
    --text="Use DEEP mode?\n\nDeep mode captures:\n• Rendered DOM (post-JavaScript)\n• All API calls and responses\n• Auto-generated local mock server\n• Cookies and localStorage\n\nStandard mode downloads HTML/CSS/JS/assets only." \
    --ok-label="Deep" --cancel-label="Standard" 2>/dev/null \
    && MODE="deep"

elif command -v osascript &>/dev/null; then
  ANSWER=$(osascript -e 'button returned of (display dialog "Clone mode?\n\nDeep = captures JS rendering + all API calls + mock server\nStandard = downloads HTML/CSS/JS/assets" buttons {"Standard", "Deep"} default button "Deep" with title "Site Clone Tool")')
  [[ "$ANSWER" == "Deep" ]] && MODE="deep"

else
  echo ""
  echo "  Mode: [1] Standard (HTML/CSS/JS/assets)  [2] Deep (+ API capture, mock server)"
  printf "  Choose [1/2]: "
  read -r CHOICE
  [[ "$CHOICE" == "2" ]] && MODE="deep"
fi

# ── run ────────────────────────────────────────────────────────────────────
echo ""
echo "  Cloning: $URL  ($MODE mode)"
echo ""

if [[ "$MODE" == "deep" ]]; then
  node "$SCRIPT_DIR/clone.js" "$URL" --deep
else
  node "$SCRIPT_DIR/clone.js" "$URL"
fi

EXIT_CODE=$?

# ── open results ───────────────────────────────────────────────────────────
if [[ $EXIT_CODE -eq 0 ]]; then
  LATEST=$(ls -td "$SCRIPT_DIR/cloned"/*/ 2>/dev/null | head -1)
  if [[ -n "$LATEST" ]]; then
    if command -v xdg-open &>/dev/null; then
      xdg-open "$LATEST" 2>/dev/null &
    elif command -v open &>/dev/null; then
      open "$LATEST" 2>/dev/null &
    fi
  fi

  if command -v zenity &>/dev/null; then
    zenity --info --title="Done" --text="Clone complete!\n\nOutput folder:\n$LATEST" 2>/dev/null
  elif command -v osascript &>/dev/null; then
    osascript -e "display dialog \"Clone complete!\n\n$LATEST\" buttons {\"OK\"} with title \"Site Clone Tool\""
  else
    echo ""
    echo "  Done → $LATEST"
    echo ""
  fi
fi
