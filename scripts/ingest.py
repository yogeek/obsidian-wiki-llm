#!/usr/bin/env python3
"""
CLI tool for ingesting sources into the wiki
Usage: python ingest.py <source_file> [--url <url>]
"""

import click
import sys
from pathlib import Path
from dotenv import load_dotenv

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.services.wiki_manager import WikiManager
from backend.services.ingestion import IngestionService

load_dotenv()


@click.command()
@click.argument('source_file', type=click.Path(exists=True))
@click.option('--url', help='Source URL for reference')
@click.option('--vault', default='/workspace/vault', help='Vault path')
def ingest(source_file, url, vault):
    """Ingest a source file into the wiki"""
    source_path = Path(source_file)
    vault_path = Path(vault)

    # Read source content
    try:
        content = source_path.read_text(encoding='utf-8')
    except UnicodeDecodeError:
        content = source_path.read_bytes().decode('utf-8', errors='ignore')

    # Initialize services
    wiki_manager = WikiManager(vault_path)
    ingestion = IngestionService(wiki_manager)

    # Run ingestion
    click.echo(f"Ingesting {source_path.name}...")
    result = ingestion.ingest(
        source_name=source_path.name,
        content=content,
        source_url=url
    )

    # Report results
    click.echo(f"\nIngestion complete!")
    click.echo(f"Pages created: {result['pages_created']}")
    click.echo(f"Pages updated: {result['pages_updated']}")
    click.echo(f"Summary: {result['summary']}")

    if result.get('contradictions'):
        click.echo("\nContradictions found:")
        for contradiction in result['contradictions']:
            click.echo(f"  - {contradiction}")


if __name__ == '__main__':
    ingest()
