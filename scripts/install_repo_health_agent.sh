#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
COMMAND="${1:-install}"

sha256_text() {
  if command -v sha256sum >/dev/null 2>&1; then
    sha256sum | awk '{print $1}'
    return
  fi

  if command -v shasum >/dev/null 2>&1; then
    shasum -a 256 | awk '{print $1}'
    return
  fi

  printf 'Missing required command: sha256sum or shasum\n' >&2
  exit 1
}

REPO_HASH="$(printf '%s' "$ROOT_DIR" | sha256_text | cut -c1-12)"
LABEL="com.doclingstudio.repo-health.$REPO_HASH"

install_macos() {
  local agent_dir="$HOME/Library/LaunchAgents"
  local plist_path="$agent_dir/$LABEL.plist"

  mkdir -p "$agent_dir" "$ROOT_DIR/.repo-health"
  cat >"$plist_path" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>$LABEL</string>
  <key>ProgramArguments</key>
  <array>
    <string>/bin/bash</string>
    <string>$ROOT_DIR/scripts/write_repo_health_report.sh</string>
  </array>
  <key>WorkingDirectory</key>
  <string>$ROOT_DIR</string>
  <key>RunAtLoad</key>
  <true/>
  <key>StartInterval</key>
  <integer>300</integer>
  <key>StandardOutPath</key>
  <string>$ROOT_DIR/.repo-health/agent.stdout.log</string>
  <key>StandardErrorPath</key>
  <string>$ROOT_DIR/.repo-health/agent.stderr.log</string>
</dict>
</plist>
EOF

  launchctl bootout "gui/$(id -u)/$LABEL" >/dev/null 2>&1 || true
  launchctl bootstrap "gui/$(id -u)" "$plist_path"
  launchctl kickstart -k "gui/$(id -u)/$LABEL"
}

uninstall_macos() {
  local plist_path="$HOME/Library/LaunchAgents/$LABEL.plist"
  launchctl bootout "gui/$(id -u)/$LABEL" >/dev/null 2>&1 || true
  rm -f "$plist_path"
}

status_macos() {
  launchctl print "gui/$(id -u)/$LABEL"
}

install_linux() {
  local systemd_dir="$HOME/.config/systemd/user"
  local service_path="$systemd_dir/$LABEL.service"
  local timer_path="$systemd_dir/$LABEL.timer"

  mkdir -p "$systemd_dir" "$ROOT_DIR/.repo-health"

  cat >"$service_path" <<EOF
[Unit]
Description=Docling Studio repo health report generator

[Service]
Type=oneshot
WorkingDirectory=$ROOT_DIR
ExecStart=/bin/bash $ROOT_DIR/scripts/write_repo_health_report.sh
EOF

  cat >"$timer_path" <<EOF
[Unit]
Description=Run Docling Studio repo health generator every 5 minutes

[Timer]
OnBootSec=1min
OnUnitActiveSec=5min
Unit=$LABEL.service

[Install]
WantedBy=timers.target
EOF

  systemctl --user daemon-reload
  systemctl --user enable --now "$LABEL.timer"
}

uninstall_linux() {
  local systemd_dir="$HOME/.config/systemd/user"
  systemctl --user disable --now "$LABEL.timer" >/dev/null 2>&1 || true
  rm -f "$systemd_dir/$LABEL.service" "$systemd_dir/$LABEL.timer"
  systemctl --user daemon-reload
}

status_linux() {
  systemctl --user status "$LABEL.timer"
}

run_for_platform() {
  local action="$1"
  case "$(uname -s)" in
  Darwin)
    "${action}_macos"
    ;;
  Linux)
    "${action}_linux"
    ;;
  *)
    printf 'Unsupported OS for auto-install: %s\n' "$(uname -s)" >&2
    printf 'Portable fallback: bash ./scripts/run_repo_health_watch.sh 300\n' >&2
    exit 1
    ;;
  esac
}

case "$COMMAND" in
install)
  run_for_platform install
  printf 'Installed repo health scheduler: %s\n' "$LABEL"
  printf 'Report path: %s\n' "$ROOT_DIR/.repo-health/report.json"
  ;;
uninstall)
  run_for_platform uninstall
  printf 'Removed repo health scheduler: %s\n' "$LABEL"
  ;;
status)
  run_for_platform status
  ;;
*)
  printf 'Usage: %s [install|uninstall|status]\n' "$0" >&2
  exit 1
  ;;
esac
