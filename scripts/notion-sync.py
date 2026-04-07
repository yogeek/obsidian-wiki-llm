#!/usr/bin/env python3
"""
CLI tool for syncing with Notion
Usage: python notion-sync.py [--status]
"""

import click
import sys
from pathlib import Path
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.services.wiki_manager import WikiManager
from backend.services.notion_sync import NotionSync

load_dotenv()


@click.command()
@click.option('--status', is_flag=True, help='Show sync status instead of syncing')
@click.option('--vault', default='/workspace/vault', help='Vault path')
def notion_sync_cmd(status, vault):
    """Sync Notion database with wiki"""
    vault_path = Path(vault)

    wiki_manager = WikiManager(vault_path)
    notion_sync = NotionSync(wiki_manager)

    if status:
        sync_status = notion_sync.get_sync_status()
        click.echo("Notion Sync Status:")
        click.echo(f"  Status: {sync_status['status']}")
        if sync_status['last_sync']:
            click.echo(f"  Last sync: {sync_status['last_sync']}")
        click.echo(f"  Items synced: {sync_status['item_count']}")
    else:
        click.echo("Starting Notion sync...\n")
        result = notion_sync.sync_to_wiki()

        click.echo(f"Sync complete!")
        click.echo(f"Items synced: {result['synced']}")
        click.echo(f"Items updated: {result['updated']}")
        click.echo(f"Summary: {result['summary']}")


if __name__ == '__main__':
    notion_sync_cmd()
