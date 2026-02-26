#!/usr/bin/env bash
set -euo pipefail

BLOCK_DIR="/etc/nginx/blockips.d"
BLOCK_FILE="${BLOCK_DIR}/deny.conf"
SECRET_FILE="${BLOCKLIST_PATH:-/secrets/blocklist/blocklist.txt}"

mkdir -p "$BLOCK_DIR"
: > "$BLOCK_FILE"

render_blocklist() {
  : > "$BLOCK_FILE"
  if [[ -f "$SECRET_FILE" ]]; then
    sed -e 's/\r$//' -e 's/#.*$//' -e '/^[[:space:]]*$/d' "$SECRET_FILE" \
      | awk '{print "deny " $1 ";"}' >> "$BLOCK_FILE"
  fi
}



render_blocklist

# Start a watcher in the background
(
  last_hash=""
  if [[ -f "$SECRET_FILE" ]]; then
    last_hash="$(sha256sum "$SECRET_FILE" | awk '{print $1}')"
  fi
  while true; do
    if [[ -f "$SECRET_FILE" ]]; then
      new_hash="$(sha256sum "$SECRET_FILE" | awk '{print $1}')"
      if [[ "$new_hash" != "$last_hash" ]]; then
        last_hash="$new_hash"
        echo "Blocklist changed, regenerating + reloading nginx..."
        render_blocklist
        nginx -t && nginx -s reload || echo "nginx reload failed"
      fi
    fi
    sleep "${BLOCKLIST_POLL_SECONDS:-60}"
  done
) &

# IMPORTANT: keep nginx in the foreground so the container stays up
exec nginx -c /workspace/nginx.conf -g 'daemon off;'