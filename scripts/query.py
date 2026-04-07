#!/usr/bin/env python3
"""
CLI tool for querying the wiki
Usage: python query.py "Your question here" [--max-depth 3]
"""

import click
import sys
from pathlib import Path
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.services.wiki_manager import WikiManager
from backend.services.query_engine import QueryEngine

load_dotenv()


@click.command()
@click.argument('query')
@click.option('--max-depth', default=3, help='Max depth for traversing wiki links')
@click.option('--vault', default='/workspace/vault', help='Vault path')
def query(query, max_depth, vault):
    """Query the wiki"""
    vault_path = Path(vault)

    # Initialize services
    wiki_manager = WikiManager(vault_path)
    query_engine = QueryEngine(wiki_manager)

    click.echo(f"Querying wiki: '{query}'")
    click.echo("Processing...\n")

    result = query_engine.query(query, max_depth=max_depth)

    # Display results
    click.echo("Answer:")
    click.echo("-" * 80)
    click.echo(result['answer'])
    click.echo("-" * 80)

    if result.get('sources'):
        click.echo(f"\nSources: {', '.join(result['sources'])}")

    if result.get('related_entities'):
        click.echo(f"Related entities: {', '.join(result['related_entities'])}")

    click.echo(f"\nConfidence: {result.get('confidence', 0):.2%}")


if __name__ == '__main__':
    query()
