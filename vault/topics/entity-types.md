---
confidence_level: high
created_date: '2026-04-07T15:16:52.589883'
last_updated: '2026-04-07T15:16:52.589887'
related_entities:
- entities
- topics
- sources
- decisions
source: getting-started.md
status: published
tags:
- wiki
- structure
- entities
- categories
type: topic
---

# Entity Types

The wiki organizes all knowledge into four core page categories. Each category serves a distinct purpose in the knowledge base.

## Categories

### Entities
Represents discrete real-world or conceptual objects:
- **People** — Individuals relevant to the knowledge base
- **Technologies** — Tools, frameworks, platforms, languages
- **Concepts** — Abstract ideas, methodologies, principles

### Topics
Thematic collections that group related knowledge and cross-reference entities. Topics provide the narrative and synthesis layer of the wiki.

### Sources
References to original content — documents, articles, books, conversations — that were ingested into the wiki. Sources provide provenance and traceability.

### Decisions
Recorded rationales and choices, capturing *why* something was done or chosen. Useful for preserving context that might otherwise be lost.

## File Organization

Each category maps to a directory in the wiki:
```
wiki/
  entities/
  topics/
  sources/
  decisions/
```

## Related Pages

- [[personal-wiki-overview]] — System overview
- [[ingestion-process]] — How new pages are created