# Implementation Summary: No-Vector RAG Personal Knowledge Base

## What Was Built

A production-ready personal knowledge base system based on Andrej Karpathy's no-vector RAG approach. External sources (Notion, Confluence, JIRA, raw documents) sync automatically into a structured Obsidian markdown vault. Claude maintains the wiki and answers natural language queries by traversing it.

No vector databases. No embeddings. Markdown files + LLM.

## Architecture

```
External Sources (Notion, Confluence, JIRA)
    ↓ [Connectors + APScheduler]
VaultManager (config/vaults.yaml)
    ↓ [WikiManager per vault]
Markdown Vault (Obsidian)
    ↓ [BFS traversal]
QueryEngine → Claude → Answer

Raw Documents
    ↓ [IngestionService]
Markdown Vault
```

## Project Structure

```
obsidian-wiki-llm/
├── backend/
│   ├── main.py                          # FastAPI app + service wiring
│   └── services/
│       ├── wiki_manager.py              # Vault CRUD, lint, stats
│       ├── vault_manager.py             # Multi-vault orchestrator (config-driven)
│       ├── connector_registry.py        # Self-registering connector factory
│       ├── scheduler.py                 # APScheduler: sync + maintenance jobs
│       ├── url_enricher.py              # URL/content → Claude tag deduction
│       ├── ingestion.py                 # Raw source → 10-15 wiki page updates
│       ├── query_engine.py              # BFS traversal + LLM synthesis
│       ├── notion_sync.py               # Legacy fallback connector
│       └── connectors/
│           ├── base_connector.py        # ABC: authenticate, fetch_updates, sync
│           ├── notion_connector.py      # Notion implementation
│           ├── confluence_connector.py  # Confluence with CQL support
│           └── jira_connector.py        # JIRA with JQL + sprint/epic hubs
├── config/
│   ├── sources.yaml                     # Source auth (env-var refs)
│   ├── vaults.yaml                      # Vault bindings + sync schedules
│   ├── wiki_schema.yaml                 # Legacy structure config
│   └── templates/                       # Page templates
├── scripts/                             # CLI tools (Click)
├── vaults/                              # Multi-vault data
├── vault/                               # Legacy single vault
└── docs/adr/                            # Architecture Decision Records
```

## Features Implemented

### 1. Multi-Vault Connector Framework

Config-driven routing from external sources to isolated vaults:

- `config/sources.yaml` — defines sources and credential env-var references
- `config/vaults.yaml` — defines vaults, bindings, filters, sync intervals, enrichment flags
- `VaultManager` loads both files, instantiates connectors and WikiManagers
- Any source can feed any vault with independent filters (same Confluence space can route to multiple vaults with different CQL queries)

### 2. Connectors

All implement `BaseConnector` (template method + strategy pattern):

| Connector | Auth | Filtering | Hub Pages |
|-----------|------|-----------|-----------|
| Notion | API key | Database ID | Tag hubs |
| Confluence | PAT token | CQL queries, space, labels | Label hubs, ancestor links |
| JIRA | PAT token | JQL, project, components | Sprint hubs, epic hubs, tag hubs |

Sync state is persisted per connector at `vault_path/.{connector}.sync_status` for incremental updates.

### 3. Scheduled Background Sync

`WikiScheduler` (APScheduler) manages:
- Per-binding `IntervalTrigger` sync jobs (e.g. "6h", "30m", "1d")
- Per-vault `CronTrigger` maintenance jobs (weekly lint)
- `max_instances=1` prevents overlapping runs
- Manual trigger via `POST /vaults/{vault}/sync/{source}`

### 4. URL and Content Enrichment

`UrlEnricher` adds semantic tags to synced pages:
- `enrich_from_url: true` — fetches the page's URL, Claude Haiku deduces 3-7 tags
- `enrich_from_content: true` — Claude tags from the body text (for Confluence pages)
- Idempotent: skips if `content_fetched: true` already in frontmatter

### 5. No-Vector RAG Query Engine

`QueryEngine`:
1. Finds seed wiki pages matching the question
2. BFS traversal via `[[wiki-links]]` (depth ≤ 3, max 20 pages)
3. Claude synthesizes a grounded answer from gathered content
4. Returns answer + source page list

### 6. Ingestion Pipeline

`IngestionService`: Claude reads a raw source document and produces a structured JSON describing 10-15 wiki page updates (create or amend). Pages are written with frontmatter, cross-references, and `[[wiki-links]]`.

### 7. Wiki Maintenance

`WikiManager` lint detects: orphaned pages, broken links, stale content (>30 days). Stats report: total pages, by type, orphaned, stale.

### 8. REST API

See `AGENTS.md` for full endpoint table. New multi-vault endpoints (`/vaults`, `/scheduler/status`) coexist with legacy endpoints for backward compatibility.

## Configuration Reference

### Minimal .env

```env
ANTHROPIC_API_KEY=sk-ant-...
```

### With Notion

```env
ANTHROPIC_API_KEY=sk-ant-...
NOTION_API_KEY=secret_...
NOTION_DATABASE_ID=...
```

### With Confluence

```env
CONFLUENCE_HOST=https://your-company.atlassian.net
CONFLUENCE_USERNAME=you@company.com
CONFLUENCE_API_TOKEN=...
```

## LLM Models

Default fallback order (cheapest first, auto-detected at startup):

| Priority | Model | Used for |
|----------|-------|---------|
| 1st | `claude-haiku-4-5-20251001` | All tasks by default; URL enrichment (hardcoded) |
| 2nd | `claude-sonnet-4-6` | Fallback |
| 3rd | `claude-opus-4-7` | Last resort |

Override via `CLAUDE_MODELS` env var (comma-separated).

## Quick Start

```bash
cp .env.example .env
# Add ANTHROPIC_API_KEY to .env

make setup
make start

# Browse vault
open http://localhost:8080

# Query
make query Q="What do I know about Kubernetes?"

# Ingest a document
make ingest FILE=raw_sources/article.md
```

## Deployment Checklist

- [ ] `.env` configured with API keys
- [ ] `docker compose up -d` succeeds
- [ ] `curl http://localhost:8000/health` returns 200
- [ ] Obsidian loads at http://localhost:8080
- [ ] `config/sources.yaml` and `config/vaults.yaml` configured
- [ ] First sync completes: `POST /vaults/{vault}/sync/{source}`
- [ ] Query returns grounded answer: `make query Q="..."`

## Key Design Decisions

See `docs/adr/` for the full rationale:
- `001` — Why connector pattern over monolithic NotionSync
- `002` — Graphify knowledge graph integration assessment
