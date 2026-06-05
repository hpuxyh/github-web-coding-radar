#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
LABEL="${LABEL:-com.local.github-xhs-daily}"
RUN_HOUR="${RUN_HOUR:-8}"
RUN_MINUTE="${RUN_MINUTE:-30}"
PLIST="$HOME/Library/LaunchAgents/$LABEL.plist"
LOG_DIR="$ROOT_DIR/logs"

xml_escape() {
  python3 -c 'import html, sys; print(html.escape(sys.argv[1], quote=True))' "$1"
}

mkdir -p "$(dirname "$PLIST")" "$LOG_DIR"

ROOT_XML="$(xml_escape "$ROOT_DIR")"
OUT_LOG_XML="$(xml_escape "$LOG_DIR/github-xhs-daily.out.log")"
ERR_LOG_XML="$(xml_escape "$LOG_DIR/github-xhs-daily.err.log")"
TOKEN_BLOCK=""
if [[ -n "${GITHUB_TOKEN:-}" ]]; then
  TOKEN_XML="$(xml_escape "$GITHUB_TOKEN")"
  TOKEN_BLOCK="
    <key>GITHUB_TOKEN</key>
    <string>$TOKEN_XML</string>"
fi

cat > "$PLIST" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>$LABEL</string>
  <key>WorkingDirectory</key>
  <string>$ROOT_XML</string>
  <key>ProgramArguments</key>
  <array>
    <string>/usr/bin/env</string>
    <string>python3</string>
    <string>$ROOT_XML/scripts/github_xhs_daily.py</string>
    <string>run</string>
  </array>
  <key>StartCalendarInterval</key>
  <dict>
    <key>Hour</key>
    <integer>$RUN_HOUR</integer>
    <key>Minute</key>
    <integer>$RUN_MINUTE</integer>
  </dict>
  <key>EnvironmentVariables</key>
  <dict>
    <key>PATH</key>
    <string>/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin</string>$TOKEN_BLOCK
  </dict>
  <key>StandardOutPath</key>
  <string>$OUT_LOG_XML</string>
  <key>StandardErrorPath</key>
  <string>$ERR_LOG_XML</string>
</dict>
</plist>
PLIST

launchctl bootout "gui/$(id -u)" "$PLIST" >/dev/null 2>&1 || true
launchctl bootstrap "gui/$(id -u)" "$PLIST"
launchctl enable "gui/$(id -u)/$LABEL"

echo "Installed $LABEL"
echo "Schedule: daily at $(printf '%02d:%02d' "$RUN_HOUR" "$RUN_MINUTE")"
echo "Plist: $PLIST"
echo "Output: $ROOT_DIR/output/latest.md"
