#!/usr/bin/env bash
# Install the Ansible collections the Ludus server ships
# (ludus-reference/ansible-requirements.yml, a copy of ludus-server/ansible/requirements.yml)
# plus this source's own collections (ansible/collections/*) into a local collections
# path, so ansible-lint resolves exactly the modules and playbooks a Ludus template build
# would. Prints the ANSIBLE_COLLECTIONS_PATH to export (and sets it for later GitHub
# Actions steps).
#
# Usage: scripts/install_ansible_deps.sh [tools-dir]      (default: <repo>/.tools)
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REFERENCE="${LUDUS_REFERENCE_DIR:-$ROOT/ludus-reference}"
TOOLS="${1:-${LUDUS_CI_TOOLS:-$ROOT/.tools}}"
DEST="$TOOLS/ansible-collections"
mkdir -p "$DEST"

command -v ansible-galaxy >/dev/null 2>&1 || { echo "ansible-galaxy not found; run: python -m pip install -r requirements-ci.txt" >&2; exit 2; }

echo "installing the collections the Ludus server ships (from $REFERENCE/ansible-requirements.yml)"
if ! ansible-galaxy collection install -r "$REFERENCE/ansible-requirements.yml" -p "$DEST"; then
  echo "::warning::could not install the Ludus collection set from Galaxy; ansible-lint may report unknown modules" >&2
fi

shopt -s nullglob
for dir in "$ROOT"/ansible/collections/*/; do
  dir="${dir%/}"
  [ -f "$dir/galaxy.yml" ] || continue
  echo "installing source collection $(basename "$dir")"
  ansible-galaxy collection install --no-deps --force -p "$DEST" "$dir"
done

echo
echo "export ANSIBLE_COLLECTIONS_PATH=\"$DEST\""
if [ -n "${GITHUB_ENV:-}" ]; then echo "ANSIBLE_COLLECTIONS_PATH=$DEST" >> "$GITHUB_ENV"; fi
