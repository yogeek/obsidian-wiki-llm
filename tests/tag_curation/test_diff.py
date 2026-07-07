import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from scripts.tag_curation.diff import build_diff, render_markdown, DiffEntry

FIXTURE_ITEMS = [
    {"id": "page-1", "title": "Ingress nginx at breaking point", "tags": ["K8S", "Network", "Nginx"]},
    {"id": "page-2", "title": "Terraform check block", "tags": ["terraform"]},
    {"id": "page-3", "title": "No tags here", "tags": []},
    {"id": "page-4", "title": "Also no tags, no suggestion available", "tags": []},
    {
        "id": "page-5",
        "title": "Kitchen sink article",
        "tags": [
            "K8S", "aws", "security", "IA", "productivity", "learning",
        ],
    },
]

UNTAGGED_SUGGESTIONS = {
    "page-3": ["Kubernetes", "Observabilité"],
    "page-4": None,  # insufficient information to suggest a tag
}


def test_build_diff_basic_remap():
    entries = build_diff(FIXTURE_ITEMS, UNTAGGED_SUGGESTIONS)
    e = next(e for e in entries if e.page_id == "page-2")
    assert e.old_tags == ["terraform"]
    assert e.new_tags == ["Terraform", "IaC"]
    assert e.unmapped == []
    assert e.flags == []


def test_build_diff_flags_many_tags():
    entries = build_diff(FIXTURE_ITEMS, UNTAGGED_SUGGESTIONS)
    e = next(e for e in entries if e.page_id == "page-5")
    # K8S, aws, security, IA, productivity, learning -> 6 distinct canonicals
    assert len(e.new_tags) == 6
    assert "many_tags" in e.flags


def test_build_diff_applies_untagged_suggestion():
    entries = build_diff(FIXTURE_ITEMS, UNTAGGED_SUGGESTIONS)
    e = next(e for e in entries if e.page_id == "page-3")
    assert e.old_tags == []
    assert e.new_tags == ["Kubernetes", "Observabilité"]
    assert "untagged_suggested" in e.flags


def test_build_diff_flags_untagged_without_suggestion():
    entries = build_diff(FIXTURE_ITEMS, UNTAGGED_SUGGESTIONS)
    e = next(e for e in entries if e.page_id == "page-4")
    assert e.old_tags == []
    assert e.new_tags == []
    assert "needs_manual_review" in e.flags


def test_build_diff_preserves_order_and_count():
    entries = build_diff(FIXTURE_ITEMS, UNTAGGED_SUGGESTIONS)
    assert len(entries) == len(FIXTURE_ITEMS)
    assert [e.page_id for e in entries] == [it["id"] for it in FIXTURE_ITEMS]


def test_render_markdown_contains_titles_and_tags():
    entries = build_diff(FIXTURE_ITEMS, UNTAGGED_SUGGESTIONS)
    md = render_markdown(entries)
    assert "Terraform check block" in md
    assert "Terraform, IaC" in md
    assert "NEEDS MANUAL REVIEW" in md


def test_render_markdown_summary_counts():
    entries = build_diff(FIXTURE_ITEMS, UNTAGGED_SUGGESTIONS)
    md = render_markdown(entries)
    assert "Total articles: 5" in md
    # page-3 (untagged_suggested), page-4 (needs_manual_review), page-5
    # (many_tags) each carry a flag; page-1 and page-2 carry none.
    assert "Flagged for review: 3" in md
