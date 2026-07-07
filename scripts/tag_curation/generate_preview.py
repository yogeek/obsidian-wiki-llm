#!/usr/bin/env python3
"""
Read the latest tag backup and produce a human-reviewable markdown
dry-run of the tag curation, without writing anything to Notion.

Usage: python scripts/tag_curation/generate_preview.py [--backup PATH]
"""

import json
import sys
from datetime import datetime
from pathlib import Path

import click

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from scripts.tag_curation.diff import build_diff, render_markdown
from scripts.tag_curation.mapping import UNTAGGED_SUGGESTIONS
from scripts.tag_curation.utils import latest_backup


@click.command()
@click.option("--backup", default=None, help="Path to a specific backup JSON (defaults to the latest)")
@click.option("--out-dir", default="previews", help="Directory to write the preview file")
def main(backup: str | None, out_dir: str):
    backup_path = backup or latest_backup()
    click.echo(f"Using backup: {backup_path}")
    items = json.loads(Path(backup_path).read_text())

    entries = build_diff(items, UNTAGGED_SUGGESTIONS)
    md = render_markdown(entries)

    Path(out_dir).mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    out_path = Path(out_dir) / f"tag-diff-{timestamp}.md"
    out_path.write_text(md)

    flagged = sum(1 for e in entries if e.flags)
    unmapped = sum(1 for e in entries if e.unmapped)
    click.echo(f"Preview written to {out_path}")
    click.echo(f"  Total articles: {len(entries)}")
    click.echo(f"  Flagged for review: {flagged}")
    click.echo(f"  Articles with unmapped legacy tags: {unmapped}")


if __name__ == "__main__":
    main()
