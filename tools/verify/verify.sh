#!/usr/bin/env sh
set -eu

root="${1:-$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd)}"
for file in AGENTS.md README.md docs/INDEX.md docs/refs/VERIFICATION.md; do
  test -f "$root/$file" || { echo "VER-001: missing $file" >&2; exit 1; }
done
for file in ARCHITECTURE.md BACKLOG.md COMPOSITION.md CONVENTIONS.md Dockerfile docker-compose.yml; do
  test ! -e "$root/$file" || { echo "VER-002: forbidden root artifact $file" >&2; exit 1; }
done
echo '{"status":"passed","repository_type":"methodology","methodology_version":"development","checks":[]}'
