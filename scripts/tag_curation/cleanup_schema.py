#!/usr/bin/env python3
"""
Restrict the Notion `tag` multi_select property to exactly the 24
canonical options, so future manual tagging (via Save to Notion or the
Notion UI) can only pick from the clean vocabulary.

Run this ONLY after apply.py --confirm has succeeded and Task 7 Step 4
shows no unexpected non-canonical tags still in use.

Usage: python scripts/tag_curation/cleanup_schema.py --confirm
"""

import os
import sys
from pathlib import Path

import click
from dotenv import load_dotenv
from notion_client import Client

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from scripts.tag_curation.mapping import CANONICAL_TAGS
from scripts.tag_curation.notion_api import set_tag_schema_options

load_dotenv()


@click.command()
@click.option("--confirm", is_flag=True, help="Actually update the database schema.")
def main(confirm: bool):
    click.echo(f"Target schema: {len(CANONICAL_TAGS)} options: {CANONICAL_TAGS}")
    if not confirm:
        click.echo("Dry run only (no --confirm passed). Nothing was written.")
        return

    api_key = os.environ["NOTION_API_KEY"]
    database_id = os.environ["NOTION_DATABASE_ID"]
    client = Client(auth=api_key)
    set_tag_schema_options(client, database_id, CANONICAL_TAGS)
    click.echo("Schema updated.")


if __name__ == "__main__":
    main()
