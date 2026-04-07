---
confidence_level: high
created_date: '2026-04-07T15:16:52.591725'
last_updated: '2026-04-07T15:16:52.591728'
related_entities:
- personal-wiki-overview
- ingestion-process
- llm
source: getting-started.md
status: published
tags:
- decision
- architecture
- search
- wiki
type: decision
---

# Decision: Wiki Over Raw Document Search

## Decision

Use a pre-processed, LLM-maintained wiki as the knowledge layer rather than performing raw document search at query time.

## Rationale

| Approach | Characteristics |
|---|---|
| **Raw document search** | Fast setup, but queries require re-processing documents each time; relationships are not explicit |
| **LLM-maintained wiki** | Higher setup cost, but knowledge is structured, cross-referenced, and compounds over time |

## Benefits of This Approach

- **Structured knowledge** — Entities and relationships are explicit, not inferred at query time
- **Compounding value** — Each ingestion enriches the whole knowledge base
- **Faster queries** — The synthesis work is done during ingestion, not retrieval
- **Browsability** — The wiki can be explored by a human in Obsidian, not just queried by an LLM

## Trade-offs

- Requires an ingestion step before new sources are queryable
- LLM may introduce errors or omissions during ingestion
- Wiki pages may become stale if sources are updated

## Related Pages

- [[personal-wiki-overview]] — System overview
- [[ingestion-process]] — The ingestion mechanism
- [[knowledge-compounding]] — The key benefit of this approach