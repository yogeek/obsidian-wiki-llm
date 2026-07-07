"""
Builds the human-reviewable dry-run diff between legacy Notion tags and
the canonical taxonomy (see mapping.py). No network access — operates on
plain dicts so it can be unit-tested and run against a JSON backup file.
"""

from dataclasses import dataclass, field

from scripts.tag_curation.mapping import canonicalize_tags

MANY_TAGS_THRESHOLD = 5


@dataclass
class DiffEntry:
    page_id: str
    title: str
    old_tags: list[str]
    new_tags: list[str]
    unmapped: list[str] = field(default_factory=list)
    flags: list[str] = field(default_factory=list)


def build_diff(
    items: list[dict],
    untagged_suggestions: dict[str, list[str] | None],
) -> list[DiffEntry]:
    entries = []
    for item in items:
        page_id = item["id"]
        title = item["title"]
        old_tags = item["tags"]

        if old_tags:
            new_tags, unmapped = canonicalize_tags(old_tags)
            flags = []
            if len(new_tags) > MANY_TAGS_THRESHOLD:
                flags.append("many_tags")
        else:
            unmapped = []
            suggestion = untagged_suggestions.get(page_id)
            if suggestion:
                new_tags = suggestion
                flags = ["untagged_suggested"]
            else:
                new_tags = []
                flags = ["needs_manual_review"]

        entries.append(
            DiffEntry(
                page_id=page_id,
                title=title,
                old_tags=old_tags,
                new_tags=new_tags,
                unmapped=unmapped,
                flags=flags,
            )
        )
    return entries


def render_markdown(entries: list[DiffEntry]) -> str:
    flagged = [e for e in entries if e.flags]
    lines = [
        "# Notion tag curation — dry-run preview",
        "",
        f"Total articles: {len(entries)}",
        f"Flagged for review: {len(flagged)}",
        "",
        "## All articles",
        "",
        "| Title | Old tags | New tags | Flags |",
        "|---|---|---|---|",
    ]
    for e in entries:
        old = ", ".join(e.old_tags) if e.old_tags else "(none)"
        new = ", ".join(e.new_tags) if e.new_tags else "(none)"
        flags = ", ".join(e.flags) if e.flags else ""
        lines.append(f"| {e.title} | {old} | {new} | {flags} |")

    if flagged:
        lines += ["", "## Flagged for manual arbitration", ""]
        for e in flagged:
            if "needs_manual_review" in e.flags:
                lines.append(
                    f"- **NEEDS MANUAL REVIEW** — {e.title!r} (page {e.page_id}): "
                    f"no tags, no suggestion available. Tag directly in Notion."
                )
            elif "many_tags" in e.flags:
                lines.append(
                    f"- **many_tags** — {e.title!r}: {len(e.new_tags)} canonical "
                    f"tags ({', '.join(e.new_tags)}). Consider trimming."
                )
            elif "untagged_suggested" in e.flags:
                lines.append(
                    f"- **untagged_suggested** — {e.title!r}: proposed "
                    f"{', '.join(e.new_tags)} from title/URL. Confirm or adjust."
                )

    unmapped_entries = [e for e in entries if e.unmapped]
    if unmapped_entries:
        lines += ["", "## Unmapped legacy tags (should be empty)", ""]
        for e in unmapped_entries:
            lines.append(f"- {e.title!r}: unmapped tags {e.unmapped}")

    return "\n".join(lines)
