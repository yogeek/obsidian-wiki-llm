#!/usr/bin/env python3
"""
Dump the current Notion tag-curation database state (id, title, tags) to
a timestamped JSON file, before any tag rewrite. This is the rollback
source of truth (see rollback.py).

Usage: python scripts/tag_curation/backup.py
"""

import json
import os
import sys
from datetime import datetime
from pathlib import Path

import click
from dotenv import load_dotenv
from notion_client import Client

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from scripts.tag_curation.notion_api import fetch_all_items

load_dotenv()


@click.command()
@click.option("--out-dir", default="backups", help="Directory to write the backup file")
def main(out_dir: str):
    api_key = os.environ["NOTION_API_KEY"]
    database_id = os.environ["NOTION_DATABASE_ID"]
    client = Client(auth=api_key)

    click.echo("Fetching all items from Notion...")
    items = fetch_all_items(client, database_id)
    click.echo(f"Fetched {len(items)} items.")

    Path(out_dir).mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    out_path = Path(out_dir) / f"notion-tags-{timestamp}.json"
    out_path.write_text(json.dumps(items, indent=2, ensure_ascii=False))
    click.echo(f"Backup written to {out_path} ({len(items)} items).")


if __name__ == "__main__":
    main()
