---
confidence_level: high
created_date: '2026-04-07T15:03:14.707301'
last_updated: '2026-04-07T15:03:14.707304'
related_entities:
- personal-wiki-system
source: getting-started.md
status: published
tags:
- wiki-structure
- knowledge-organization
- sources
type: topic
---

# Wiki Sources

## Definition
Sources are references to original content that has been ingested into the wiki system. They maintain the provenance of information and allow tracing knowledge back to its origins.

## Types of Sources
- Documents (PDFs, markdown, text files)
- Web pages and articles
- Books and publications
- Videos and multimedia
- Personal notes and observations
- Conversations and interviews

## Metadata
Each source should include:
- Original location or URL
- Date accessed or created
- Author or creator
- Type of source
- Confidence level
- Key topics covered

## Role in the Wiki
- Provide attribution for facts and claims
- Enable verification of information
- Track the evolution of knowledge
- Support different perspectives on topics

## Storage
Raw sources are stored in the `raw_sources/` directory before being processed and integrated into the wiki.

## Related Pages
- [[wiki-entities]]
- [[wiki-topics]]
- [[wiki-decisions]]
- [[wiki-ingestion-process]]