#!/usr/bin/env python3
"""
Restore tags from a backup JSON, undoing an apply run. Symmetrical to
apply.py: gated by --confirm, supports restoring a single page via
--page-id for testing.

Usage:
  python scripts/tag_curation/rollback.py --backup backups/notion-tags-XXXX.json --confirm
  python scripts/tag_curation/rollback.py --backup backups/notion-tags-XXXX.json --page-id <id> --confirm
"""

import json
import os
import sys
from pathlib import Path

import click
from dotenv import load_dotenv
from notion_client import Client

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from scripts.tag_curation.notion_api import update_page_tags

load_dotenv()


@click.command()
@click.option("--backup", required=True, help="Path to the backup JSON to restore from")
@click.option("--page-id", default=None, help="Restore only this single page (for testing)")
@click.option("--confirm", is_flag=True, help="Actually write to Notion. Without this flag, only prints a summary.")
def main(backup: str, page_id: str | None, confirm: bool):
    items = json.loads(Path(backup).read_text())
    if page_id:
        items = [it for it in items if it["id"] == page_id]
        if not items:
            raise SystemExit(f"page-id {page_id} not found in {backup}")

    click.echo(f"Restoring {len(items)} item(s) from {backup}")
    if not confirm:
        click.echo("Dry run only (no --confirm passed). Nothing was written.")
        return

    api_key = os.environ["NOTION_API_KEY"]
    client = Client(auth=api_key)
    for i, item in enumerate(items, 1):
        update_page_tags(client, item["id"], item["tags"])
        click.echo(f"[{i}/{len(items)}] restored {item['title'][:60]!r} -> {item['tags']}")

    click.echo("Rollback complete.")


if __name__ == "__main__":
    main()
