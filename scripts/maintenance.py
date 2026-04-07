#!/usr/bin/env python3
"""
CLI tool for wiki maintenance (linting, health checks)
Usage: python maintenance.py [--action lint|stale|broken-links]
"""

import click
import sys
from pathlib import Path
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.services.wiki_manager import WikiManager

load_dotenv()


@click.command()
@click.option('--action', type=click.Choice(['lint', 'stale', 'broken-links', 'stats']),
              default='lint', help='Maintenance action')
@click.option('--vault', default='/workspace/vault', help='Vault path')
def maintenance(action, vault):
    """Run wiki maintenance tasks"""
    vault_path = Path(vault)
    wiki_manager = WikiManager(vault_path)

    if action == 'lint':
        click.echo("Running wiki lint...\n")
        result = wiki_manager.lint()

        if result['orphaned_pages']:
            click.echo("Orphaned pages (no backlinks):")
            for page in result['orphaned_pages']:
                click.echo(f"  - {page}")

        if result['broken_links']:
            click.echo("\nBroken links:")
            for link in result['broken_links']:
                click.echo(f"  - {link}")

        if not result['orphaned_pages'] and not result['broken_links']:
            click.echo("Wiki is clean!")

    elif action == 'stale':
        stats = wiki_manager.get_statistics()
        click.echo(f"Stale pages (not updated in 30 days): {stats['stale_pages']}")

    elif action == 'broken-links':
        result = wiki_manager.lint()
        for link in result['broken_links']:
            click.echo(link)

    elif action == 'stats':
        stats = wiki_manager.get_statistics()
        click.echo("Wiki Statistics:")
        click.echo(f"  Total pages: {stats['total_pages']}")
        click.echo(f"  Entities: {stats['total_entities']}")
        click.echo(f"  Topics: {stats['total_topics']}")
        click.echo(f"  Sources: {stats['total_sources']}")
        click.echo(f"  Stale pages: {stats['stale_pages']}")


if __name__ == '__main__':
    maintenance()
