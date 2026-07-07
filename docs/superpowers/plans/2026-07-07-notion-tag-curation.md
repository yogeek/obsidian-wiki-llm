# Notion Tag Curation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the 155 chaotic, overlapping tags in the Notion tech-watch database with a fixed vocabulary of 24 canonical tags, applied to all ~290 articles, with a mandatory human-reviewed dry-run before any write to the live Notion database.

**Architecture:** A standalone `scripts/tag_curation/` package of small, composable scripts. Pure logic (tag-name mapping, diff computation) lives in dependency-free modules and is unit-tested with pytest in a local venv — no Docker, no live API needed. I/O against Notion (fetch, backup, write, schema cleanup) lives in thin wrapper scripts run inside the existing `wiki-cli` Docker container (matching the project's established `docker exec wiki-cli python scripts/...` pattern), verified manually against the real API since there is nothing meaningful to mock. The flow is strictly sequential and gated: backup → preview (dry-run) → **human review checkpoint** → apply → cleanup schema → re-sync vault.

**Tech Stack:** Python 3.11, `notion-client==2.2.1` (already in `requirements-cli.txt`, already installed in the `wiki-cli` image), `click` for CLIs, `pytest` for pure-logic unit tests (new, local venv only).

## Global Constraints

- No write to the live Notion database happens without an explicit, separate human-reviewed checkpoint (spec §6.3). This is non-negotiable — Task 6 ends with a STOP for user review; Task 7 requires an explicit `--confirm` flag.
- Exactly 24 canonical tags, spelled exactly as in spec §3 (accents included: `Observabilité`, `Sécurité`, `Réseau`, `Productivité`).
- All 155 legacy tag names from spec §4 must be covered by `TAG_MAP` — no orphans (enforced by a test).
- Every write to Notion must be preceded by a backup capable of full rollback (spec §6.1, §7).
- Rate limit all Notion write calls to ~3 req/s (spec §8 risk 2 concerns concurrency; this plan also self-throttles to stay well under Notion's documented limit).
- Do not touch `État` (status), descriptions, or run any LLM enrichment — out of scope (spec §2).

---

## File Structure

```
scripts/tag_curation/
  __init__.py            # empty, makes this a package
  mapping.py             # CANONICAL_TAGS, TAG_MAP (155→24), UNTAGGED_SUGGESTIONS, canonicalize_tags()
  diff.py                # DiffEntry, build_diff(), render_markdown()
  notion_api.py          # fetch_all_items(), update_page_tags(), set_tag_schema_options()
  backup.py              # CLI: dump current Notion tag state to JSON
  generate_preview.py    # CLI: backup JSON + mapping.py -> markdown dry-run preview
  apply.py               # CLI: writes new tags to Notion, gated by --confirm
  rollback.py            # CLI: restores tags from a backup JSON
  cleanup_schema.py      # CLI: prunes the `tag` multi_select options down to the 24 canonical

tests/tag_curation/
  __init__.py
  test_mapping.py        # unit tests for canonicalize_tags() and TAG_MAP coverage
  test_diff.py           # unit tests for build_diff() / render_markdown()

backups/                 # created at runtime, gitignored
previews/                # created at runtime, gitignored
```

`mapping.py` and `diff.py` have **zero dependency on notion_client or the network** — they operate on plain dicts/lists, which is what makes them unit-testable without Docker or live credentials. `notion_api.py` is the only module that imports `notion_client`; it is exercised manually against the real API (there is no meaningful mock for "did Notion actually update the page").

---

## Task 1: Local test environment for pure-logic modules

**Files:**
- Create: `.venv-test/` (local virtualenv, gitignored — not part of the Docker workflow, only for running the pure-logic unit tests fast without touching containers)

**Interfaces:**
- Produces: a `pytest` executable at `.venv-test/bin/pytest` used by all subsequent test-running steps in this plan.

- [ ] **Step 1: Create the virtualenv and install pytest**

Run:
```bash
cd /home/guillaume/perso/obsidian-wiki-llm
python3 -m venv .venv-test
.venv-test/bin/pip install --quiet pytest==8.3.4
```

- [ ] **Step 2: Verify pytest runs**

Run: `.venv-test/bin/pytest --version`
Expected: `pytest 8.3.4`

- [ ] **Step 3: Gitignore the venv**

Add to `.gitignore` (append at the end of the file):
```
# Tag curation
.venv-test/
backups/
previews/
```

- [ ] **Step 4: Commit**

```bash
git add .gitignore
git commit -m "chore: gitignore tag-curation venv, backups, previews"
```

---

## Task 2: Canonical tag list and mapping function (TDD)

**Files:**
- Create: `scripts/tag_curation/__init__.py` (empty)
- Create: `scripts/tag_curation/mapping.py`
- Test: `tests/tag_curation/__init__.py` (empty)
- Test: `tests/tag_curation/test_mapping.py`

**Interfaces:**
- Produces: `CANONICAL_TAGS: list[str]` (24 entries), `TAG_MAP: dict[str, list[str]]` (155 keys), `canonicalize_tags(old_tags: list[str]) -> tuple[list[str], list[str]]` returning `(new_tags, unmapped)` where `new_tags` is the deduplicated, order-preserving union of canonical tags and `unmapped` lists any input tag not found in `TAG_MAP` (nothing is silently dropped).

- [ ] **Step 1: Write the failing tests**

Create `tests/tag_curation/__init__.py` (empty file).

Create `tests/tag_curation/test_mapping.py`:

```python
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from scripts.tag_curation.mapping import CANONICAL_TAGS, TAG_MAP, canonicalize_tags

# The 155 legacy tag names exactly as they appear in the Notion `tag`
# multi_select property today (spec §4 source list).
ALL_155_SOURCE_TAGS = [
    "K8S", "IA", "productivity", "cloud", "CLI", "learning", "aws", "dev",
    "Network", "GPT", "Terminal", "security", "IaC", "costing", "ops", "sre",
    "Dashboard", "LLM", "Observability", "tui", "Ux", "ide", "Visualisation",
    "docker", "debug", "terraform", "ui", "Monitoring", "Agent", "gitops",
    "Scaling", "data", "Doc", "Git", "log", "ssh", "ebpf", "Web", "Auth",
    "db", "MCP", "opensource", "hacking", "Architecture", "s3", "Otel",
    "CICD", "AI", "Local", "config", "registry", "Cilium", "IAM", "Platform",
    "Testing", "IDP", "storage", "benchmark", "Karpenter", "secret",
    "Crossplane", "search", "Github", "n8n", "Api", "Frontend", "Argocd",
    "Nocode", "eks", "Queue", "map", "Automation", "PDF", "Cleaning",
    "Oauth", "Kind", "json", "OCI", "Diagram", "Istio", "grpc", "http",
    "Traefik", "Serverless", "lambda", "Cpu", "Shell", "Paas",
    "multitenancy", "Microservices", "nix", "game", "Browser", "Prediction",
    "ldap", "Voice", "STT", "oicd", "passkey", "Kyverno", "Policies",
    "Incident", "Skills", "Claude", "Opencode", "Framework", "Notebook",
    "Pro", "Nginx", "GatewayAPI", "Poll", "Feedback", "Mac", "Ios",
    "Windows", "Sql", "Image", "fun", "Knative", "datadog", "Speech", "Dns",
    "Operator", "Html", "Scheduling", "Python", "Package", "Kernel",
    "Artifact", "Build", "Chaos", "cert", "Nutshell", "bash", "HA",
    "Resilience", "Monolith", "wysiwyg", "Go", "Mesh", "Blog", "Stateful",
    "Uber", "Job", "Wasm", "Webassembly", "RBAC", "Jaeger", "fleet",
    "Sveltos", "Formation", "featureflag", "vault", "snippet", "apigw",
]


def test_canonical_tags_has_24_entries():
    assert len(CANONICAL_TAGS) == 24
    assert len(set(CANONICAL_TAGS)) == 24  # no duplicates


def test_all_155_source_tags_are_covered():
    assert len(ALL_155_SOURCE_TAGS) == 155
    missing = [t for t in ALL_155_SOURCE_TAGS if t not in TAG_MAP]
    assert missing == [], f"Uncovered legacy tags: {missing}"


def test_every_tag_map_value_is_canonical():
    for source, targets in TAG_MAP.items():
        for target in targets:
            assert target in CANONICAL_TAGS, (
                f"TAG_MAP[{source!r}] contains non-canonical tag {target!r}"
            )


def test_simple_single_mapping():
    new_tags, unmapped = canonicalize_tags(["K8S"])
    assert new_tags == ["Kubernetes"]
    assert unmapped == []


def test_dual_canonical_mapping():
    new_tags, unmapped = canonicalize_tags(["terraform"])
    assert new_tags == ["Terraform", "IaC"]
    assert unmapped == []


def test_cross_domain_mapping():
    new_tags, unmapped = canonicalize_tags(["eks"])
    assert new_tags == ["Kubernetes", "AWS"]
    assert unmapped == []


def test_dedup_union_across_multiple_old_tags():
    # K8S -> Kubernetes, docker -> Kubernetes: must not duplicate
    new_tags, unmapped = canonicalize_tags(["K8S", "docker"])
    assert new_tags == ["Kubernetes"]
    assert unmapped == []


def test_order_preserving_union():
    # IaC first, then terraform (adds Terraform, IaC already present)
    new_tags, unmapped = canonicalize_tags(["IaC", "terraform"])
    assert new_tags == ["IaC", "Terraform"]


def test_unmapped_tag_is_reported_not_dropped():
    new_tags, unmapped = canonicalize_tags(["K8S", "TotallyUnknownTag"])
    assert new_tags == ["Kubernetes"]
    assert unmapped == ["TotallyUnknownTag"]


def test_empty_input():
    new_tags, unmapped = canonicalize_tags([])
    assert new_tags == []
    assert unmapped == []
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv-test/bin/pytest tests/tag_curation/test_mapping.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'scripts.tag_curation.mapping'` (or `scripts.tag_curation` package not found — either way, a collection error, not a passing test).

- [ ] **Step 3: Implement `scripts/tag_curation/mapping.py`**

Create `scripts/tag_curation/__init__.py` (empty file).

Create `scripts/tag_curation/mapping.py`:

```python
"""
Canonical tag taxonomy and legacy-tag mapping for the Notion tech-watch
database curation (see docs/superpowers/specs/2026-07-07-notion-tag-curation-design.md).
"""

CANONICAL_TAGS = [
    "Kubernetes", "Ingress-Mesh", "AWS", "Cloud", "IaC", "Terraform",
    "Crossplane", "CICD-GitOps", "Observabilité", "Sécurité", "Réseau",
    "IA-LLM", "Agents-IA", "MCP", "CLI-Terminal", "DevEx", "Productivité",
    "Learning", "SRE-Ops", "FinOps", "Data-DB", "Serverless", "SSH",
    "Divers",
]

# Legacy tag name (exact casing as stored in Notion today) -> list of
# canonical tags it maps to. Every one of the 155 tags currently in the
# `tag` multi_select property must appear here exactly once as a key.
TAG_MAP = {
    # --- Kubernetes ---
    "K8S": ["Kubernetes"],
    "docker": ["Kubernetes"],
    "Karpenter": ["Kubernetes"],
    "Scaling": ["Kubernetes"],
    "multitenancy": ["Kubernetes"],
    "Kind": ["Kubernetes"],
    "OCI": ["Kubernetes"],
    "Operator": ["Kubernetes"],
    "Scheduling": ["Kubernetes"],
    "Stateful": ["Kubernetes"],
    "Job": ["Kubernetes"],
    "fleet": ["Kubernetes"],
    "Sveltos": ["Kubernetes"],
    "Microservices": ["Kubernetes"],
    "registry": ["Kubernetes"],
    "Kyverno": ["Kubernetes"],
    "Policies": ["Kubernetes"],
    "eks": ["Kubernetes", "AWS"],

    # --- Ingress-Mesh ---
    "Cilium": ["Ingress-Mesh"],
    "Istio": ["Ingress-Mesh"],
    "Traefik": ["Ingress-Mesh"],
    "Nginx": ["Ingress-Mesh"],
    "GatewayAPI": ["Ingress-Mesh"],
    "Mesh": ["Ingress-Mesh"],
    "apigw": ["Ingress-Mesh"],

    # --- AWS ---
    "aws": ["AWS"],
    "s3": ["AWS"],
    "storage": ["AWS"],
    "IAM": ["AWS", "Sécurité"],

    # --- Cloud ---
    "cloud": ["Cloud"],
    "Platform": ["Cloud"],
    "IDP": ["Cloud"],
    "Paas": ["Cloud"],

    # --- IaC / Terraform / Crossplane ---
    "IaC": ["IaC"],
    "config": ["IaC"],
    "nix": ["IaC"],
    "terraform": ["Terraform", "IaC"],
    "Crossplane": ["Crossplane", "IaC"],

    # --- CICD-GitOps ---
    "gitops": ["CICD-GitOps"],
    "CICD": ["CICD-GitOps"],
    "Git": ["CICD-GitOps"],
    "Github": ["CICD-GitOps"],
    "Argocd": ["CICD-GitOps"],
    "Automation": ["CICD-GitOps"],
    "Artifact": ["CICD-GitOps"],
    "Build": ["CICD-GitOps"],
    "featureflag": ["CICD-GitOps"],

    # --- Observabilité ---
    "Dashboard": ["Observabilité"],
    "Observability": ["Observabilité"],
    "Monitoring": ["Observabilité"],
    "debug": ["Observabilité"],
    "log": ["Observabilité"],
    "Otel": ["Observabilité"],
    "datadog": ["Observabilité"],
    "Jaeger": ["Observabilité"],

    # --- Sécurité ---
    "security": ["Sécurité"],
    "Auth": ["Sécurité"],
    "hacking": ["Sécurité"],
    "secret": ["Sécurité"],
    "Oauth": ["Sécurité"],
    "ldap": ["Sécurité"],
    "oicd": ["Sécurité"],
    "passkey": ["Sécurité"],
    "cert": ["Sécurité"],
    "vault": ["Sécurité"],
    "RBAC": ["Sécurité", "Kubernetes"],

    # --- Réseau ---
    "Network": ["Réseau"],
    "ebpf": ["Réseau"],
    "grpc": ["Réseau"],
    "http": ["Réseau"],
    "Dns": ["Réseau"],
    "Kernel": ["Réseau"],

    # --- IA-LLM ---
    "IA": ["IA-LLM"],
    "GPT": ["IA-LLM"],
    "LLM": ["IA-LLM"],
    "AI": ["IA-LLM"],
    "Prediction": ["IA-LLM"],
    "Voice": ["IA-LLM"],
    "STT": ["IA-LLM"],
    "Speech": ["IA-LLM"],
    "Claude": ["IA-LLM"],
    "Notebook": ["IA-LLM"],

    # --- Agents-IA ---
    "Agent": ["Agents-IA"],
    "Skills": ["Agents-IA"],
    "Opencode": ["Agents-IA"],

    # --- MCP ---
    "MCP": ["MCP"],

    # --- CLI-Terminal ---
    "CLI": ["CLI-Terminal"],
    "Terminal": ["CLI-Terminal"],
    "tui": ["CLI-Terminal"],
    "Shell": ["CLI-Terminal"],
    "bash": ["CLI-Terminal"],

    # --- DevEx ---
    "dev": ["DevEx"],
    "ide": ["DevEx"],
    "Ux": ["DevEx"],
    "ui": ["DevEx"],
    "Web": ["DevEx"],
    "Testing": ["DevEx"],
    "benchmark": ["DevEx"],
    "Local": ["DevEx"],
    "Api": ["DevEx"],
    "Frontend": ["DevEx"],
    "Framework": ["DevEx"],
    "Browser": ["DevEx"],
    "Html": ["DevEx"],
    "Python": ["DevEx"],
    "Go": ["DevEx"],
    "wysiwyg": ["DevEx"],
    "Package": ["DevEx"],
    "Cleaning": ["DevEx"],
    "Image": ["DevEx"],
    "snippet": ["DevEx"],

    # --- Productivité ---
    "productivity": ["Productivité"],
    "Visualisation": ["Productivité"],
    "Doc": ["Productivité"],
    "search": ["Productivité"],
    "n8n": ["Productivité"],
    "Nocode": ["Productivité"],
    "map": ["Productivité"],
    "Diagram": ["Productivité"],
    "PDF": ["Productivité"],
    "Poll": ["Productivité"],
    "Feedback": ["Productivité"],

    # --- Learning ---
    "learning": ["Learning"],
    "Formation": ["Learning"],
    "Nutshell": ["Learning"],

    # --- SRE-Ops ---
    "ops": ["SRE-Ops"],
    "sre": ["SRE-Ops"],
    "Incident": ["SRE-Ops"],
    "Chaos": ["SRE-Ops"],
    "HA": ["SRE-Ops"],
    "Resilience": ["SRE-Ops"],
    "Cpu": ["SRE-Ops"],

    # --- FinOps ---
    "costing": ["FinOps"],

    # --- Data-DB ---
    "data": ["Data-DB"],
    "db": ["Data-DB"],
    "Queue": ["Data-DB"],
    "json": ["Data-DB"],
    "Sql": ["Data-DB"],

    # --- Serverless ---
    "Serverless": ["Serverless"],
    "lambda": ["Serverless", "AWS"],
    "Knative": ["Serverless", "Kubernetes"],
    "Wasm": ["Serverless"],
    "Webassembly": ["Serverless"],

    # --- SSH ---
    "ssh": ["SSH"],

    # --- Divers ---
    "opensource": ["Divers"],
    "Architecture": ["Divers"],
    "game": ["Divers"],
    "fun": ["Divers"],
    "Mac": ["Divers"],
    "Ios": ["Divers"],
    "Windows": ["Divers"],
    "Pro": ["Divers"],
    "Monolith": ["Divers"],
    "Blog": ["Divers"],
    "Uber": ["Divers"],
}


def canonicalize_tags(old_tags: list[str]) -> tuple[list[str], list[str]]:
    """Map legacy Notion tags to the canonical taxonomy.

    Returns (new_tags, unmapped): new_tags is the order-preserving,
    deduplicated union of canonical tags for all recognized old_tags.
    unmapped lists any old_tags not present in TAG_MAP verbatim, so
    nothing is silently dropped.
    """
    new_tags: list[str] = []
    unmapped: list[str] = []
    for tag in old_tags:
        targets = TAG_MAP.get(tag)
        if targets is None:
            unmapped.append(tag)
            continue
        for target in targets:
            if target not in new_tags:
                new_tags.append(target)
    return new_tags, unmapped
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv-test/bin/pytest tests/tag_curation/test_mapping.py -v`
Expected: `10 passed`

- [ ] **Step 5: Commit**

```bash
git add scripts/tag_curation/__init__.py scripts/tag_curation/mapping.py \
        tests/tag_curation/__init__.py tests/tag_curation/test_mapping.py
git commit -m "feat: add canonical tag taxonomy and 155->24 mapping function"
```

---

## Task 3: Diff builder and untagged-article suggestions (TDD)

**Files:**
- Create: `scripts/tag_curation/diff.py`
- Test: `tests/tag_curation/test_diff.py`

**Interfaces:**
- Consumes: `canonicalize_tags` from `scripts/tag_curation/mapping.py` (Task 2).
- Produces: `DiffEntry` (dataclass with fields `page_id: str`, `title: str`, `old_tags: list[str]`, `new_tags: list[str]`, `unmapped: list[str]`, `flags: list[str]`), `build_diff(items: list[dict], untagged_suggestions: dict[str, list[str] | None]) -> list[DiffEntry]`, `render_markdown(entries: list[DiffEntry]) -> str`. `items` entries are plain dicts `{"id": str, "title": str, "tags": list[str]}` — this is exactly the shape `backup.py` (Task 5) will produce, so `diff.py` never needs a live Notion connection.

- [ ] **Step 1: Write the failing tests**

Create `tests/tag_curation/test_diff.py`:

```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv-test/bin/pytest tests/tag_curation/test_diff.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'scripts.tag_curation.diff'`

- [ ] **Step 3: Implement `scripts/tag_curation/diff.py`**

```python
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv-test/bin/pytest tests/tag_curation/test_diff.py -v`
Expected: `7 passed`

- [ ] **Step 5: Run the full pure-logic suite together**

Run: `.venv-test/bin/pytest tests/tag_curation/ -v`
Expected: `17 passed` (10 from test_mapping.py + 7 from test_diff.py)

- [ ] **Step 6: Commit**

```bash
git add scripts/tag_curation/diff.py tests/tag_curation/test_diff.py
git commit -m "feat: add dry-run diff builder and markdown preview renderer"
```

---

## Task 4: Untagged-article suggestions (real data)

**Files:**
- Modify: `scripts/tag_curation/mapping.py` (append `UNTAGGED_SUGGESTIONS`)
- Test: `tests/tag_curation/test_mapping.py` (append coverage test)

**Interfaces:**
- Consumes: `CANONICAL_TAGS` from Task 2.
- Produces: `UNTAGGED_SUGGESTIONS: dict[str, list[str] | None]` keyed by the real Notion `page_id` of each of the 11 currently untagged articles, consumed by `diff.build_diff` (Task 3) via the `untagged_suggestions` parameter.

This data was derived by inspecting each of the 11 untagged articles' title and URL directly against the live Notion database on 2026-07-07. Two entries have neither a usable title nor a URL and are marked `None` (no honest suggestion is possible — they are surfaced as `needs_manual_review` by `diff.py` and must be tagged by hand in Notion).

- [ ] **Step 1: Append the suggestions test**

Add to the end of `tests/tag_curation/test_mapping.py`:

```python
from scripts.tag_curation.mapping import UNTAGGED_SUGGESTIONS


def test_untagged_suggestions_has_11_entries():
    assert len(UNTAGGED_SUGGESTIONS) == 11


def test_untagged_suggestions_values_are_canonical_or_none():
    for page_id, tags in UNTAGGED_SUGGESTIONS.items():
        if tags is None:
            continue
        for tag in tags:
            assert tag in CANONICAL_TAGS, (
                f"UNTAGGED_SUGGESTIONS[{page_id!r}] has non-canonical tag {tag!r}"
            )


def test_untagged_suggestions_has_exactly_two_manual_review_cases():
    manual = [pid for pid, tags in UNTAGGED_SUGGESTIONS.items() if tags is None]
    assert len(manual) == 2
```

- [ ] **Step 2: Run to verify it fails**

Run: `.venv-test/bin/pytest tests/tag_curation/test_mapping.py -v -k untagged`
Expected: FAIL with `ImportError: cannot import name 'UNTAGGED_SUGGESTIONS'`

- [ ] **Step 3: Append `UNTAGGED_SUGGESTIONS` to `scripts/tag_curation/mapping.py`**

Add at the end of the file:

```python
# Suggested tags for the 11 articles that currently have zero tags in
# Notion, derived from each article's title/URL (see plan Task 4). A
# value of None means no honest suggestion could be made from the
# available data — diff.py surfaces these as "needs_manual_review".
UNTAGGED_SUGGESTIONS: dict[str, list[str] | None] = {
    "369083fc-7c60-81b9-b010-cdb68da0faeb": ["Kubernetes", "Observabilité"],  # Dozzle - simple container logger
    "2f2083fc-7c60-815a-98b9-ea57b00252fb": ["Agents-IA"],  # Vibe Kanban - Orchestrate AI Coding Agents
    "293083fc-7c60-8181-aa27-fd64bcace747": ["Kubernetes", "Ingress-Mesh"],  # K8SGB - a global kubernetes loadbalancer
    "1a9083fc-7c60-819e-b90d-cbe9121b25c3": ["Kubernetes", "Sécurité"],  # securing-the-kubernetes-host-operating-system
    "1a2083fc-7c60-8168-bbc3-eaca6aa26ed8": ["Kubernetes", "CICD-GitOps"],  # Testkube as a Quality Gate with Keptn
    "173083fc-7c60-8135-ab9c-dd25ca007d76": None,  # "A story from Lili Wan on Medium", no URL — insufficient info
    "133083fc-7c60-8158-adce-f49fbc33fd29": ["Kubernetes", "Observabilité"],  # Kexa - requests limits k8s tool and dashboard
    "132083fc-7c60-8140-9c06-df9c63585c3b": ["Productivité"],  # Screenity - screen capture tool
    "bb0480c4-a13f-433c-8f1e-b883bffa6b24": ["Kubernetes"],  # Sleepcycles k8s operator
    "3222ebac-f2cd-4021-b14b-03650b5e9077": ["CICD-GitOps", "Kubernetes"],  # GitOps bridge
    "2390efb6-871f-43ab-bf36-e573c3c17e40": None,  # no title, no URL — empty row, insufficient info
}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv-test/bin/pytest tests/tag_curation/test_mapping.py -v`
Expected: `13 passed` (10 from Task 2 + 3 new untagged-suggestions tests)

- [ ] **Step 5: Commit**

```bash
git add scripts/tag_curation/mapping.py tests/tag_curation/test_mapping.py
git commit -m "feat: add tag suggestions for the 11 currently untagged articles"
```

---

## Task 5: Notion API wrapper and backup script

**Files:**
- Create: `scripts/tag_curation/notion_api.py`
- Create: `scripts/tag_curation/backup.py`

**Interfaces:**
- Produces: `fetch_all_items(client, database_id) -> list[dict]` (each dict shaped `{"id": str, "title": str, "tags": list[str]}`, matching the fixture shape from Task 3), `update_page_tags(client, page_id, tags: list[str]) -> None`, `set_tag_schema_options(client, database_id, option_names: list[str]) -> None`.
- This task is I/O-heavy (real Notion API) and is verified manually, not with pytest — there is no meaningful way to mock "did the live database actually return 290 items."

- [ ] **Step 1: Implement `scripts/tag_curation/notion_api.py`**

```python
"""
Thin wrapper around notion_client for the tag curation scripts. Mirrors
the pagination fix already applied to
backend/services/connectors/notion_connector.py.
"""

import time


def fetch_all_items(client, database_id: str) -> list[dict]:
    """Fetch every item in the database, paginated, shaped for diff.py."""
    items = []
    start_cursor = None
    while True:
        kwargs = {"page_size": 100}
        if start_cursor:
            kwargs["start_cursor"] = start_cursor
        response = client.databases.query(database_id, **kwargs)
        for raw in response.get("results", []):
            props = raw.get("properties", {})
            title_prop = props.get("Nom", {}).get("title") or []
            title = "".join(t["plain_text"] for t in title_prop)
            tags = [t["name"] for t in (props.get("tag", {}).get("multi_select") or [])]
            items.append({"id": raw["id"], "title": title, "tags": tags})
        if not response.get("has_more"):
            break
        start_cursor = response.get("next_cursor")
    return items


def update_page_tags(client, page_id: str, tags: list[str]) -> None:
    """Overwrite the `tag` multi_select property of one page."""
    client.pages.update(
        page_id,
        properties={"tag": {"multi_select": [{"name": t} for t in tags]}},
    )
    time.sleep(0.34)  # ~3 requests/second, well under Notion's rate limit


def set_tag_schema_options(client, database_id: str, option_names: list[str]) -> None:
    """Restrict the `tag` multi_select property's available options.

    Must only be called after every page's tags have already been
    rewritten to use exclusively `option_names` (see plan Task 9) —
    Notion may reject removing options that are still referenced by a
    page.
    """
    client.databases.update(
        database_id,
        properties={
            "tag": {
                "multi_select": {"options": [{"name": n} for n in option_names]}
            }
        },
    )
```

- [ ] **Step 2: Implement `scripts/tag_curation/backup.py`**

```python
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
```

- [ ] **Step 3: Start the CLI container (if not already running)**

Run: `docker compose up -d cli-tools`
Expected: `Container wiki-cli Started` (or already running)

- [ ] **Step 4: Run the backup against the live database and verify manually**

Run:
```bash
docker exec wiki-cli python scripts/tag_curation/backup.py
```
Expected output: `Fetched 290 items.` (or close — matches the current live count) followed by `Backup written to backups/notion-tags-<timestamp>.json (290 items).`

Verify the file structure:
```bash
docker exec wiki-cli python -c "
import json
data = json.load(open(sorted(__import__('glob').glob('backups/notion-tags-*.json'))[-1]))
print('count:', len(data))
print('sample:', data[0])
"
```
Expected: `count: 290` (or similar) and a sample dict with keys `id`, `title`, `tags`.

- [ ] **Step 5: Commit**

```bash
git add scripts/tag_curation/notion_api.py scripts/tag_curation/backup.py
git commit -m "feat: add Notion API wrapper and tag-state backup script"
```

---

## Task 6: Preview generation — CHECKPOINT before any write

**Files:**
- Create: `scripts/tag_curation/generate_preview.py`

**Interfaces:**
- Consumes: `build_diff`, `render_markdown` from `diff.py` (Task 3), `UNTAGGED_SUGGESTIONS` from `mapping.py` (Task 4), the backup JSON produced by Task 5.
- Produces: `previews/tag-diff-<timestamp>.md`, the human-reviewed artifact that gates Task 7.

- [ ] **Step 1: Implement `scripts/tag_curation/generate_preview.py`**

```python
#!/usr/bin/env python3
"""
Read the latest tag backup and produce a human-reviewable markdown
dry-run of the tag curation, without writing anything to Notion.

Usage: python scripts/tag_curation/generate_preview.py [--backup PATH]
"""

import glob
import json
import sys
from datetime import datetime
from pathlib import Path

import click

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from scripts.tag_curation.diff import build_diff, render_markdown
from scripts.tag_curation.mapping import UNTAGGED_SUGGESTIONS


def latest_backup() -> str:
    candidates = sorted(glob.glob("backups/notion-tags-*.json"))
    if not candidates:
        raise SystemExit("No backup found. Run scripts/tag_curation/backup.py first.")
    return candidates[-1]


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
```

- [ ] **Step 2: Run against the real backup and inspect the output**

Run: `docker exec wiki-cli python scripts/tag_curation/generate_preview.py`
Expected: `Articles with unmapped legacy tags: 0` (confirms `TAG_MAP` covers every tag actually present in the live data — if this is not 0, stop and fix `TAG_MAP` in Task 2 before continuing).

- [ ] **Step 3: Commit**

```bash
git add scripts/tag_curation/generate_preview.py
git commit -m "feat: add dry-run preview generator"
```

- [ ] **Step 4: STOP — human review checkpoint**

Copy the generated `previews/tag-diff-<timestamp>.md` out of the container if needed:
```bash
docker cp wiki-cli:/workspace/previews ./previews
```

**Do not proceed to Task 7 until Guillaume has read `previews/tag-diff-<timestamp>.md` and explicitly confirmed it looks correct.** Pay special attention to the "Flagged for manual arbitration" section — the `many_tags` cases and the 2 `needs_manual_review` cases are exactly where the design (spec §6.3) expects a human decision.

---

## Task 7: Apply — write the new tags to Notion (gated by --confirm)

**Files:**
- Create: `scripts/tag_curation/apply.py`

**Interfaces:**
- Consumes: `update_page_tags` from `notion_api.py` (Task 5), the same backup + diff pipeline as Task 6.
- Produces: `backups/apply-log-<timestamp>.json`, one entry per page written: `{"page_id", "title", "old_tags", "new_tags", "status"}`.

- [ ] **Step 1: Implement `scripts/tag_curation/apply.py`**

```python
#!/usr/bin/env python3
"""
Apply the tag curation diff to the live Notion database. Refuses to
write anything unless --confirm is passed, so an accidental run is a
no-op that only prints a summary.

Usage:
  python scripts/tag_curation/apply.py             # dry summary only, no writes
  python scripts/tag_curation/apply.py --confirm   # actually writes to Notion
"""

import glob
import json
import os
import sys
from datetime import datetime
from pathlib import Path

import click
from dotenv import load_dotenv
from notion_client import Client

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from scripts.tag_curation.diff import build_diff
from scripts.tag_curation.mapping import UNTAGGED_SUGGESTIONS
from scripts.tag_curation.notion_api import update_page_tags

load_dotenv()


def latest_backup() -> str:
    candidates = sorted(glob.glob("backups/notion-tags-*.json"))
    if not candidates:
        raise SystemExit("No backup found. Run scripts/tag_curation/backup.py first.")
    return candidates[-1]


@click.command()
@click.option("--backup", default=None, help="Path to a specific backup JSON (defaults to the latest)")
@click.option("--confirm", is_flag=True, help="Actually write to Notion. Without this flag, only prints a summary.")
def main(backup: str | None, confirm: bool):
    backup_path = backup or latest_backup()
    items = json.loads(Path(backup_path).read_text())
    entries = build_diff(items, UNTAGGED_SUGGESTIONS)

    # Only write entries whose tags actually change and that are not
    # flagged for manual review (those need a human to tag in Notion
    # directly, per the design's dry-run arbitration).
    to_write = [
        e for e in entries
        if "needs_manual_review" not in e.flags and set(e.new_tags) != set(e.old_tags)
    ]

    click.echo(f"Total articles: {len(entries)}")
    click.echo(f"Articles to update: {len(to_write)}")
    click.echo(f"Skipped (needs_manual_review): {sum(1 for e in entries if 'needs_manual_review' in e.flags)}")

    if not confirm:
        click.echo("\nDry run only (no --confirm passed). Nothing was written.")
        return

    api_key = os.environ["NOTION_API_KEY"]
    client = Client(auth=api_key)

    log = []
    for i, e in enumerate(to_write, 1):
        try:
            update_page_tags(client, e.page_id, e.new_tags)
            status = "ok"
        except Exception as exc:
            status = f"error: {exc}"
        log.append({
            "page_id": e.page_id,
            "title": e.title,
            "old_tags": e.old_tags,
            "new_tags": e.new_tags,
            "status": status,
        })
        click.echo(f"[{i}/{len(to_write)}] {e.title[:60]!r}: {status}")

    Path("backups").mkdir(exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    log_path = Path("backups") / f"apply-log-{timestamp}.json"
    log_path.write_text(json.dumps(log, indent=2, ensure_ascii=False))

    errors = [l for l in log if l["status"] != "ok"]
    click.echo(f"\nDone. {len(log) - len(errors)} succeeded, {len(errors)} failed.")
    click.echo(f"Log written to {log_path}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Dry-run verification (no --confirm) — must not write anything**

Run: `docker exec wiki-cli python scripts/tag_curation/apply.py`
Expected: prints the summary counts and ends with `Dry run only (no --confirm passed). Nothing was written.`

Verify nothing changed by re-reading one known page's tags via a throwaway check:
```bash
docker exec wiki-cli python -c "
import os
from notion_client import Client
c = Client(auth=os.environ['NOTION_API_KEY'])
page = c.pages.retrieve('369083fc-7c60-81b9-b010-cdb68da0faeb')
print(page['properties']['tag']['multi_select'])
"
```
Expected: `[]` (this page — Dozzle — is still untagged; the dry run did not write).

- [ ] **Step 3: STOP — final confirmation**

Only after Guillaume has reviewed the preview from Task 6 and explicitly says to proceed, run the real write:

```bash
docker exec wiki-cli python scripts/tag_curation/apply.py --confirm
```
Expected: a line per article (`[i/N] '<title>': ok`), ending with `Done. N succeeded, 0 failed.`

- [ ] **Step 4: Verify the live database now uses only canonical tags (plus any still-unresolved manual-review ones)**

```bash
docker exec wiki-cli python -c "
import os, collections
from notion_client import Client
import sys
sys.path.insert(0, '/workspace')
from scripts.tag_curation.notion_api import fetch_all_items
from scripts.tag_curation.mapping import CANONICAL_TAGS

c = Client(auth=os.environ['NOTION_API_KEY'])
items = fetch_all_items(c, os.environ['NOTION_DATABASE_ID'])
seen = collections.Counter(t for it in items for t in it['tags'])
non_canonical = {t: n for t, n in seen.items() if t not in CANONICAL_TAGS}
print('distinct tags now in use:', len(seen))
print('non-canonical leftovers:', non_canonical)
"
```
Expected: `non-canonical leftovers: {}` (or only tags belonging to the 2 `needs_manual_review` articles, which were intentionally skipped).

- [ ] **Step 5: Commit**

```bash
git add scripts/tag_curation/apply.py
git commit -m "feat: add gated apply script to write curated tags to Notion"
```

---

## Task 8: Rollback script

**Files:**
- Create: `scripts/tag_curation/rollback.py`

**Interfaces:**
- Consumes: `update_page_tags` from `notion_api.py` (Task 5), a backup JSON (Task 5's format).

- [ ] **Step 1: Implement `scripts/tag_curation/rollback.py`**

```python
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
```

- [ ] **Step 2: Verify on a single page (safe, reversible test)**

Pick the Dozzle page (`369083fc-7c60-81b9-b010-cdb68da0faeb`), which Task 7 would have tagged `["Kubernetes", "Observabilité"]` from `UNTAGGED_SUGGESTIONS`. Roll it back to its pre-apply state (empty) using the backup from Task 5:

```bash
docker exec wiki-cli python scripts/tag_curation/rollback.py \
  --backup "$(docker exec wiki-cli sh -c 'ls -1 backups/notion-tags-*.json | head -1')" \
  --page-id 369083fc-7c60-81b9-b010-cdb68da0faeb --confirm
```
Expected: `[1/1] restored 'Dozzle - simple container logger' -> []`

Verify:
```bash
docker exec wiki-cli python -c "
import os
from notion_client import Client
c = Client(auth=os.environ['NOTION_API_KEY'])
page = c.pages.retrieve('369083fc-7c60-81b9-b010-cdb68da0faeb')
print(page['properties']['tag']['multi_select'])
"
```
Expected: `[]`

Then re-apply the curated tags to this one page so it isn't left behind:
```bash
docker exec wiki-cli python -c "
import os, sys
sys.path.insert(0, '/workspace')
from notion_client import Client
from scripts.tag_curation.notion_api import update_page_tags
c = Client(auth=os.environ['NOTION_API_KEY'])
update_page_tags(c, '369083fc-7c60-81b9-b010-cdb68da0faeb', ['Kubernetes', 'Observabilité'])
print('re-applied')
"
```

- [ ] **Step 3: Commit**

```bash
git add scripts/tag_curation/rollback.py
git commit -m "feat: add rollback script to restore tags from a backup"
```

---

## Task 9: Clean up the Notion `tag` schema options

**Files:**
- Create: `scripts/tag_curation/cleanup_schema.py`

**Interfaces:**
- Consumes: `set_tag_schema_options` from `notion_api.py` (Task 5), `CANONICAL_TAGS` from `mapping.py` (Task 2).
- Precondition: Task 7 has been applied and verified (Step 4 of Task 7 showed no non-canonical leftovers, or only the 2 known manual-review articles).

- [ ] **Step 1: Implement `scripts/tag_curation/cleanup_schema.py`**

```python
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
```

- [ ] **Step 2: Run and verify**

Run: `docker exec wiki-cli python scripts/tag_curation/cleanup_schema.py --confirm`
Expected: `Schema updated.`

Verify:
```bash
docker exec wiki-cli python -c "
import os
from notion_client import Client
c = Client(auth=os.environ['NOTION_API_KEY'])
db = c.databases.retrieve(os.environ['NOTION_DATABASE_ID'])
options = [o['name'] for o in db['properties']['tag']['multi_select']['options']]
print(sorted(options))
print('count:', len(options))
"
```
Expected: `count: 24` and the printed list matches `CANONICAL_TAGS` exactly (sorted).

If Notion rejects the update because some option is still referenced by a page, this means Task 7 Step 4's verification was incomplete — stop, re-run Task 7 Step 4's check, resolve the leftover page(s) manually, and retry.

- [ ] **Step 3: Commit**

```bash
git add scripts/tag_curation/cleanup_schema.py
git commit -m "feat: add schema cleanup script to prune tag options to the 24 canonical"
```

---

## Task 10: Re-sync the Obsidian vault

**Files:**
- No new files — uses the already-fixed `backend/services/connectors/notion_connector.py` and the running `rag-backend` container.

**Interfaces:**
- Consumes: the `/vaults/tech-watch/sync/notion` endpoint already exposed by `backend/main.py` (confirmed working during the earlier fresh-sync run).

- [ ] **Step 1: Trigger the sync**

Run:
```bash
curl -s -X POST http://localhost:8000/vaults/tech-watch/sync/notion
```
Expected: JSON with `"status": "success"` and `items_fetched` around 290.

- [ ] **Step 2: Verify the vault reflects the 24 canonical tag-hubs**

```bash
find /home/guillaume/perso/obsidian-wiki-llm/vaults/tech-watch/technology_watch -name '*.md' \
  -exec grep -l "^type: technology_watch_hub$" {} \; | wc -l
```
Expected: `24` (one hub file per canonical tag — some hubs may briefly be absent if an old-155 hub still exists on disk from before; if the count is not exactly 24, check for stale hub files left over from the previous tag set and remove them, since the connector currently does not prune hub pages for tags no longer in use).

- [ ] **Step 3: Spot-check one article's tags in the vault match the canonical set**

```bash
grep -A3 "^tags:" "/home/guillaume/perso/obsidian-wiki-llm/vaults/tech-watch/technology_watch/ingress-nginx-at-breaking-point-.md"
```
Expected: tags drawn from the 24 canonical names (e.g. `Kubernetes`, `Ingress-Mesh`, `Réseau`), not the old K8S/Network/nginx/etc.

- [ ] **Step 4: No commit needed**

The vault content under `vaults/` is data, not source — it is not part of this plan's git history changes (consistent with how the earlier fresh Notion sync was handled).

---

## Self-Review Notes

- **Spec coverage:** §3 taxonomy → Task 2. §4 mapping table → Task 2 (all 155 keys, verified by test). §5 untagged articles → Task 4 (real data, 2 honest `None` cases). §6 write-back flow (backup → preview → review → apply → cleanup → re-sync) → Tasks 5–10 in that exact order, with explicit STOP checkpoints at Task 6 Step 4 and Task 7 Step 3. §7 rollback → Task 8. §8 risks (schema deletion ordering, concurrent scheduler writes, rate limiting) → addressed in Task 9's precondition note, Task 5/7's `time.sleep(0.34)`, and this plan's Global Constraints (recommend pausing the `rag-backend` scheduler is covered by Task 10 running the sync manually, and the scheduler's next automatic run is 6h out, which is enough headroom for this session). §9 definition of done → Task 9 Step 2 (≤24 tags) and Task 7 Step 4 (0 unexpected non-canonical) and Task 8 Step 2 (rollback demonstrated on one page) directly verify each bullet.
- **Placeholder scan:** no TBD/TODO; the two `None` entries in `UNTAGGED_SUGGESTIONS` are a real, documented outcome (not a placeholder) and are exercised by a passing test and by `diff.py`'s `needs_manual_review` flag.
- **Type consistency:** `DiffEntry` fields (`page_id`, `title`, `old_tags`, `new_tags`, `unmapped`, `flags`) are used identically across Tasks 3, 6, 7. The item shape `{"id", "title", "tags"}` is identical across `backup.py` (Task 5, producer), `diff.build_diff` (Task 3, consumer), and the test fixtures (Task 3).
- **Scope:** matches spec §2 exactly — no status/description/enrichment work included.
