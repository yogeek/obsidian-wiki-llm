#!/bin/bash
# Pre-seed Obsidian graph config before the app starts.
# This script runs as the container entrypoint, copies graph.json
# into the vault's .obsidian/ directory, then hands off to the
# original entrypoint (/init).

VAULT_DIR="/config/workspace/tech-watch"
OBSIDIAN_DIR="${VAULT_DIR}/.obsidian"
SEED_FILE="/app/graph-seed.json"

if [ -f "$SEED_FILE" ]; then
    mkdir -p "$OBSIDIAN_DIR"
    cp "$SEED_FILE" "$OBSIDIAN_DIR/graph.json"
    echo "[graph-seed] Copied graph.json to $OBSIDIAN_DIR"
fi

exec /init "$@"
