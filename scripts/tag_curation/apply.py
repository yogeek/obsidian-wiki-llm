#!/usr/bin/env python3
"""
Apply the tag curation diff to the live Notion database. Refuses to
write anything unless --confirm is passed, so an accidental run is a
no-op that only prints a summary.

Usage:
  python scripts/tag_curation/apply.py             # dry summary only, no writes
  python scripts/tag_curation/apply.py --confirm   # actually writes to Notion
"""

import glob
import json
import os
import sys
from datetime import datetime
from pathlib import Path

import click
from dotenv import load_dotenv
from notion_client import Client

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from scripts.tag_curation.diff import build_diff
from scripts.tag_curation.mapping import UNTAGGED_SUGGESTIONS
from scripts.tag_curation.notion_api import update_page_tags

load_dotenv()


def latest_backup() -> str:
    candidates = sorted(glob.glob("backups/notion-tags-*.json"))
    if not candidates:
        raise SystemExit("No backup found. Run scripts/tag_curation/backup.py first.")
    return candidates[-1]


@click.command()
@click.option("--backup", default=None, help="Path to a specific backup JSON (defaults to the latest)")
@click.option("--confirm", is_flag=True, help="Actually write to Notion. Without this flag, only prints a summary.")
def main(backup: str | None, confirm: bool):
    backup_path = backup or latest_backup()
    items = json.loads(Path(backup_path).read_text())
    entries = build_diff(items, UNTAGGED_SUGGESTIONS)

    # Only write entries whose tags actually change and that are not
    # flagged for manual review (those need a human to tag in Notion
    # directly, per the design's dry-run arbitration).
    to_write = [
        e for e in entries
        if "needs_manual_review" not in e.flags and set(e.new_tags) != set(e.old_tags)
    ]

    click.echo(f"Total articles: {len(entries)}")
    click.echo(f"Articles to update: {len(to_write)}")
    click.echo(f"Skipped (needs_manual_review): {sum(1 for e in entries if 'needs_manual_review' in e.flags)}")

    if not confirm:
        click.echo("\nDry run only (no --confirm passed). Nothing was written.")
        return

    api_key = os.environ["NOTION_API_KEY"]
    client = Client(auth=api_key)

    log = []
    for i, e in enumerate(to_write, 1):
        try:
            update_page_tags(client, e.page_id, e.new_tags)
            status = "ok"
        except Exception as exc:
            status = f"error: {exc}"
        log.append({
            "page_id": e.page_id,
            "title": e.title,
            "old_tags": e.old_tags,
            "new_tags": e.new_tags,
            "status": status,
        })
        click.echo(f"[{i}/{len(to_write)}] {e.title[:60]!r}: {status}")

    Path("backups").mkdir(exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    log_path = Path("backups") / f"apply-log-{timestamp}.json"
    log_path.write_text(json.dumps(log, indent=2, ensure_ascii=False))

    errors = [l for l in log if l["status"] != "ok"]
    click.echo(f"\nDone. {len(log) - len(errors)} succeeded, {len(errors)} failed.")
    click.echo(f"Log written to {log_path}")


if __name__ == "__main__":
    main()
