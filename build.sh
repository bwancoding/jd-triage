#!/usr/bin/env bash
#
# Generates the per-platform skill directories from src/.
#
#   ./build.sh          rebuild claude-code/ and openclaw/
#   ./build.sh --check  exit 1 if the generated dirs are out of sync with src/
#
# src/ is the only place to edit. Everything in claude-code/ and openclaw/ is
# overwritten, except the files under platform/<name>/ which are copied in
# verbatim (hub listing pages, publishing metadata).

set -euo pipefail

cd "$(dirname "$0")"

PLATFORMS=(claude-code openclaw)

workspace_for() {
  case "$1" in
    claude-code) echo '~/.claude/jd-triage' ;;
    openclaw)    echo '~/.openclaw/workspace' ;;
    *) echo "unknown platform: $1" >&2; exit 1 ;;
  esac
}

render() {
  local platform="$1" outdir="$2"
  local workspace; workspace="$(workspace_for "$platform")"

  rm -rf "$outdir"
  mkdir -p "$outdir"

  # Copy the tree, substituting tokens in every text file.
  (cd src && find . -type f) | while read -r rel; do
    mkdir -p "$outdir/$(dirname "$rel")"
    sed -e "s|{{WORKSPACE}}|$workspace|g" \
        -e "s|{{PLATFORM}}|$platform|g" \
        "src/$rel" > "$outdir/$rel"
  done

  # Platform-specific extras (README for the hub, publishing metadata).
  if [ -d "platform/$platform" ]; then
    cp -R "platform/$platform/." "$outdir/"
  fi

  # No token should survive.
  if grep -rl '{{[A-Z_]*}}' "$outdir" >/dev/null 2>&1; then
    echo "error: unsubstituted tokens in $outdir:" >&2
    grep -rn '{{[A-Z_]*}}' "$outdir" >&2
    exit 1
  fi
}

if [ "${1:-}" = "--check" ]; then
  status=0
  tmp="$(mktemp -d)"
  trap 'rm -rf "$tmp"' EXIT
  for p in "${PLATFORMS[@]}"; do
    render "$p" "$tmp/$p"
    if ! diff -rq "$tmp/$p" "$p" >/dev/null 2>&1; then
      echo "out of sync: $p (run ./build.sh)" >&2
      diff -rq "$tmp/$p" "$p" >&2 || true
      status=1
    fi
  done
  [ "$status" -eq 0 ] && echo "in sync: ${PLATFORMS[*]}"
  exit "$status"
fi

for p in "${PLATFORMS[@]}"; do
  render "$p" "$p"
  echo "built $p/  (workspace: $(workspace_for "$p"))"
done
