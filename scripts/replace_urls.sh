#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  replace_urls.sh [-n] <path> <search> <replace>

Where:
  <path>   A file or a directory.
           - If file: edits that file.
           - If dir : edits all *.txt files recursively under it.
  <search> Text to find
  <replace>Replacement text

Options:
  -n       Dry-run (show what would change, do not modify files)

Examples:
  ./replace_urls.sh ./data 'URL_STRING' 'CUSTOM_URL_STRING'
  ./replace_urls.sh ./one.txt 'URL_STRING' 'CUSTOM_URL_STRING'
  ./replace_urls.sh -n ./data 'http://old' 'https://new'
EOF
}

DRY_RUN=0
if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then usage; exit 0; fi
if [[ "${1:-}" == "-n" ]]; then DRY_RUN=1; shift; fi

PATH_ARG="${1:?Missing <path>}"
SEARCH="${2:?Missing <search>}"
REPLACE="${3:?Missing <replace>}"

# Detect GNU sed vs BSD/macOS sed
is_gnu_sed() { sed --version >/dev/null 2>&1; }

apply_replace_inplace() {
  local file="$1"
  if is_gnu_sed; then
    sed -i.bak "s|${SEARCH}|${REPLACE}|g" "$file"
  else
    sed -i .bak "s|${SEARCH}|${REPLACE}|g" "$file"
  fi
}

dry_run_file() {
  local file="$1"
  # Print matching lines with line numbers
  if grep -nF -- "$SEARCH" "$file" >/dev/null 2>&1; then
    echo "Would update: $file"
    grep -nF -- "$SEARCH" "$file" || true
  fi
}

process_file() {
  local file="$1"
  if [[ $DRY_RUN -eq 1 ]]; then
    dry_run_file "$file"
  else
    apply_replace_inplace "$file"
    echo "Updated: $file (backup: $file.bak)"
  fi
}

if [[ -f "$PATH_ARG" ]]; then
  process_file "$PATH_ARG"
elif [[ -d "$PATH_ARG" ]]; then
  find "$PATH_ARG" -type f -name '*.txt' -print0 |
    while IFS= read -r -d '' f; do
      process_file "$f"
    done
else
  echo "Error: path not found or not a file/dir: $PATH_ARG" >&2
  usage >&2
  exit 1
fi