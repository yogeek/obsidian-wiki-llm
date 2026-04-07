---
confidence_level: high
created_date: '2026-04-07T15:16:52.590124'
last_updated: '2026-04-07T15:16:52.590127'
related_entities:
- sources
source: getting-started.md
status: published
tags:
- wiki
- ingestion
- llm
- workflow
type: topic
---

# Ingestion Process

Ingestion is the process by which raw source material is transformed into structured wiki pages by an LLM.

## Steps

1. **Source Placement** — Raw documents are added to the `raw_sources/` directory
2. **LLM Analysis** — The LLM reads and analyzes the source material
3. **Page Generation** — New wiki pages are created or existing pages are updated
4. **Cross-Referencing** — Relationships between pages are identified and recorded
5. **Contradiction Detection** — Conflicts with existing knowledge are flagged

## Output Structure

The ingestion system returns a structured JSON object containing:
- `pages` — New or updated wiki pages
- `cross_references` — Relationships between pages
- `contradictions` — Conflicts detected in the knowledge base
- `summary` — A brief description of what was ingested

## Knowledge Compounding

Each ingestion cycle adds to and enriches the existing wiki. Over time, the knowledge base becomes more interconnected and comprehensive, making synthesis queries increasingly powerful.

## Related Pages

- [[personal-wiki-overview]] — System overview
- [[entity-types]] — Page categories produced by ingestion
- [[obsidian-integration]] — Viewing the results