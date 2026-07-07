"""
Shared helpers for the tag_curation scripts.
"""

import glob


def latest_backup() -> str:
    candidates = sorted(glob.glob("backups/notion-tags-*.json"))
    if not candidates:
        raise SystemExit("No backup found. Run scripts/tag_curation/backup.py first.")
    return candidates[-1]
