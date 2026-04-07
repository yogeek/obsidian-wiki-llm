---
confidence_level: high
created_date: '2026-04-07T15:03:14.707837'
last_updated: '2026-04-07T15:03:14.707839'
related_entities:
- personal-wiki-system
- llm-technology
source: getting-started.md
status: published
tags:
- process
- automation
- wiki-management
type: topic
---

# Wiki Ingestion Process

## Overview
The ingestion process transforms raw source materials into structured wiki pages using LLM technology.

## Steps

### 1. Source Preparation
- Add new sources to the `raw_sources/` directory
- Ensure sources are in readable formats (text, markdown, PDF)
- Include metadata about source origin and context

### 2. LLM Processing
The system uses an LLM to:
- Extract key concepts and entities
- Identify relationships between information
- Generate structured wiki pages
- Create cross-references
- Detect potential contradictions

### 3. Page Generation
For each source, the system creates:
- Entity pages for important people, technologies, or concepts
- Topic pages for themes and subject areas
- Source reference pages
- Decision documentation when applicable

### 4. Integration
- New pages are added to appropriate directories
- Cross-references are established
- Existing pages may be updated with new information
- Contradictions are flagged for review

### 5. Review and Refinement
- Browse generated pages in Obsidian
- Verify accuracy and completeness
- Add manual corrections or enhancements

## Related Pages
- [[personal-wiki-system]]
- [[wiki-sources]]
- [[knowledge-compounding]]