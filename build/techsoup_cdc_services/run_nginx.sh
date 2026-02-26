#!/usr/bin/env bash
set -euo pipefail

NGINX_CONF="${NGINX_CONF:-/workspace/nginx.conf}"
FOREGROUND="${NGINX_FOREGROUND:-false}"

BLOCK_DIR="/etc/nginx/blockips.d"
BLOCK_FILE="${BLOCK_DIR}/deny.conf"
SECRET_FILE="${BLOCKLIST_PATH:-}"
#e.g BLOCKLIST_PATH="/secrets/blocklist/blocklist.txt"

mkdir -p "$BLOCK_DIR"
: > "$BLOCK_FILE"

render_blocklist() {
  : > "$BLOCK_FILE"
  if [[ -n "$SECRET_FILE" && -f "$SECRET_FILE" ]]; then
    sed -e 's/\r$//' -e 's/#.*$//' -e '/^[[:space:]]*$/d' "$SECRET_FILE" \
      | awk '{print "deny " $1 ";"}' >> "$BLOCK_FILE"
  fi
}

render_blocklist

# Start a watcher in the background
(
  last_hash=""
  if [[ -n "$SECRET_FILE" && -f "$SECRET_FILE" ]]; then
    last_hash="$(sha256sum "$SECRET_FILE" | awk '{print $1}')"
  fi
  while true; do
    if [[ -n "$SECRET_FILE" && -f "$SECRET_FILE" ]]; then
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

if [[ "$FOREGROUND" == "true" ]]; then
  # For nginx-only container (docker-compose)
  exec nginx -c "$NGINX_CONF" -g "daemon off;"
else
  # For app container (Cloud Run): start nginx and return so run.sh can continue
  nginx -c "$NGINX_CONF"
fi