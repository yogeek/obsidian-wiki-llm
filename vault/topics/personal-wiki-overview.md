---
confidence_level: high
created_date: '2026-04-07T15:16:52.589108'
last_updated: '2026-04-07T15:16:52.589138'
related_entities:
- entities
- topics
- sources
- decisions
source: getting-started.md
status: published
tags:
- wiki
- knowledge-management
- llm
- getting-started
type: topic
---

# Personal Wiki System Overview

A system for building a personal knowledge base using Large Language Models (LLMs). Rather than searching raw documents directly, the LLM maintains a growing, interconnected wiki where knowledge compounds over time as new sources are added.

## Core Philosophy

Instead of querying raw documents at lookup time, this system **pre-processes source material into structured wiki pages**. This means:

- Knowledge is organized and cross-referenced ahead of time
- Relationships between concepts are made explicit
- Synthesis happens during ingestion, not just at query time
- The knowledge base grows richer with each new source added

## Workflow

1. **Add sources** — Place raw documents into `raw_sources/`
2. **Run ingestion** — The LLM processes sources and populates the wiki
3. **Query the wiki** — Synthesize and retrieve structured knowledge
4. **Browse in Obsidian** — Navigate the wiki visually using Obsidian's graph view

## Related Pages

- [[entity-types]] — The four core page categories
- [[ingestion-process]] — How sources are processed
- [[obsidian-integration]] — Browsing the wiki in Obsidian