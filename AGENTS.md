# AGENTS.md — AI Agent Navigation Guide

This file helps AI agents (Claude Code, Cursor, etc.) understand the repo structure and how to work effectively within it.

## What This Project Does

A **personal knowledge base system** implementing Andrej Karpathy's no-vector RAG approach. External sources (Notion, Confluence, JIRA, raw documents) are automatically synced and processed by Claude into a structured Obsidian markdown vault. Users query the vault in natural language; Claude does BFS traversal and synthesizes answers from the actual notes.

No vector databases. No embeddings. Just markdown + LLM.

## Repo Layout

```
obsidian-wiki-llm/
├── backend/
│   ├── main.py                          # FastAPI app, all endpoints, service wiring
│   └── services/
│       ├── wiki_manager.py              # Vault CRUD, lint, stats — one instance per vault
│       ├── vault_manager.py             # Loads config/vaults.yaml, owns all WikiManagers
│       ├── connector_registry.py        # Self-registering factory for connectors
│       ├── scheduler.py                 # APScheduler daemon, per-binding sync + maintenance jobs
│       ├── url_enricher.py              # Fetch URL → Claude deduces tags (idempotent)
│       ├── ingestion.py                 # Claude reads raw source → creates/updates 10-15 wiki pages
│       ├── query_engine.py              # BFS wiki traversal → Claude synthesis
│       ├── notion_sync.py               # Legacy fallback (used if multi-vault init fails)
│       └── connectors/
│           ├── base_connector.py        # Abstract base: authenticate, fetch_updates, sync template
│           ├── notion_connector.py      # Notion → wiki pages
│           ├── confluence_connector.py  # Confluence CQL → wiki pages
│           └── jira_connector.py        # JIRA JQL → wiki pages
├── config/
│   ├── sources.yaml                     # Source auth definitions (refs env vars for credentials)
│   ├── vaults.yaml                      # Vault definitions, source bindings, sync schedules
│   ├── wiki_schema.yaml                 # Legacy wiki structure config (templates, directories)
│   └── templates/                       # Markdown page templates (entity, topic, tech-watch)
├── scripts/                             # CLI tools (Click-based)
│   ├── ingest.py                        # Add raw source → wiki
│   ├── query.py                         # Query the wiki
│   ├── maintenance.py                   # Lint, stats, stale detection
│   └── notion-sync.py                   # Manual Notion sync trigger
├── vaults/                              # Active multi-vault data (gitignored content)
│   └── tech-watch/                      # technology_watch + confluence_pages
├── vault/                               # Legacy single vault (still used as default)
├── docs/adr/                            # Architecture Decision Records
└── docker-compose.yml                   # Three containers: backend, cli, obsidian
```

## How to Run

```bash
# Start everything
docker compose up -d

# Check health
curl http://localhost:8000/health

# Query
make query Q="What do I know about Kubernetes?"

# Ingest a document
make ingest FILE=raw_sources/article.md

# Manual Notion sync
make notion-sync

# Maintenance
make maintenance ACTION=lint
make maintenance ACTION=stats
```

Obsidian UI: http://localhost:8080
Backend API: http://localhost:8000

## Architecture: How Services Wire Together

### Startup (backend/main.py lifespan)

```
main.py
  └── If config/sources.yaml + config/vaults.yaml exist:
        VaultManager._load()
          ├── ConnectorRegistry → instantiates connectors per source type
          ├── WikiManager per vault
          └── ConnectorBinding list (source → vault → category)
        UrlEnricher (if any binding uses enrich_from_url/enrich_from_content)
        WikiScheduler.start()
          ├── IntervalTrigger per binding (sync jobs)
          └── CronTrigger per vault (weekly maintenance)
      Else: fallback to legacy NotionSync
```

### Sync Flow (per scheduled job)

```
scheduler.py → connector.sync(wiki_manager, binding, enricher)
  base_connector.py template method:
    1. authenticate()
    2. fetch_updates(since=last_sync, filter=binding.filter)
    3. For each item:
       a. _transform_to_wiki_page(item, vault_category)
       b. enricher.enrich() if enrich_from_url
       c. enricher.tag_from_content() if enrich_from_content
       d. wiki_manager.create_page(...)
    4. _post_sync_hook() → hub pages (tags, sprints, epics)
    5. _save_last_sync_time()
```

### Query Flow

```
POST /query → QueryEngine.query(question)
  1. Find seed pages matching question keywords
  2. BFS traversal via [[wiki-links]] (depth ≤ 3, max 20 pages)
  3. Claude synthesizes answer from gathered page content
  4. Return answer + source page list
```

## Configuration Files

### config/sources.yaml

Defines external sources and how to authenticate. Credentials are env-var references resolved at runtime:

```yaml
sources:
  notion:
    connector_type: "notion"
    credentials:
      api_key_env: "NOTION_API_KEY"
      database_id_env: "NOTION_DATABASE_ID"
  confluence:
    connector_type: "confluence"
    credentials:
      api_key_env: "CONFLUENCE_API_TOKEN"
      base_url_env: "CONFLUENCE_HOST"
      username_env: "CONFLUENCE_USERNAME"
```

### config/vaults.yaml

Defines vaults and which sources feed them, with filters and enrichment:

```yaml
vaults:
  tech-watch:
    path: "/app/vaults/tech-watch"
    sources:
      - source: notion
        vault_category: "technology_watch"
        sync_interval: "6h"
        enrich_from_url: true
      - source: confluence
        vault_category: "confluence_pages"
        filter:
          cql: "ancestor = 412450994 AND space = DEVOPS"
        sync_interval: "6h"
        enrich_from_content: true
```

## API Endpoints

### Legacy (backward-compatible)

| Method | Path | Purpose |
|--------|------|---------|
| GET | /health | Service health |
| GET | /stats | Wiki statistics |
| GET | /notion/status | Notion sync status |
| POST | /query | Query the wiki |
| POST | /ingest | Ingest source text |
| POST | /ingest-file | Upload and ingest file |
| POST | /sync-notion | Trigger Notion sync |
| POST | /maintenance/lint | Run lint checks |

### Multi-vault (new)

| Method | Path | Purpose |
|--------|------|---------|
| GET | /vaults | All vaults + sources + last sync times |
| GET | /vaults/{vault} | Vault details + stats + bindings |
| POST | /vaults/{vault}/sync/{source} | Manual sync trigger |
| GET | /scheduler/status | Jobs + next run times |

## Environment Variables

Required:
- `ANTHROPIC_API_KEY` — Claude API access

Optional (for connectors):
- `NOTION_API_KEY` + `NOTION_DATABASE_ID`
- `CONFLUENCE_HOST` + `CONFLUENCE_USERNAME` + `CONFLUENCE_API_TOKEN`
- `JIRA_HOST` + `JIRA_USERNAME` + `JIRA_API_TOKEN`

Override default LLM model fallback list:
- `CLAUDE_MODELS` — comma-separated model IDs (cheapest first)

## Extension Points

### Add a new connector

1. Create `backend/services/connectors/myservice_connector.py`
2. Inherit from `BaseConnector` (base_connector.py)
3. Implement: `authenticate()`, `fetch_updates()`, `_transform_to_wiki_page()`
4. Add self-registration: `ConnectorRegistry.register("myservice", MyServiceConnector)`
5. Add source definition to `config/sources.yaml`
6. Add binding to `config/vaults.yaml`

### Add a new vault

Add an entry to `config/vaults.yaml` with `path`, `description`, and `sources` bindings.

### Add a new page type

1. Add directory entry to `config/wiki_schema.yaml`
2. Create template in `config/templates/`

## Key Design Decisions

See `docs/adr/` for Architecture Decision Records:
- `001-multi-vault-connector-architecture.md` — Why connector pattern over monolithic sync
- `002-graphify-integration.md` — Graphify assessment and decision

## LLM Models Used

Default fallback order (cheapest first, auto-detected at startup):
1. `claude-haiku-4-5-20251001` — URL enrichment (hardcoded), default for all tasks
2. `claude-sonnet-4-6` — fallback
3. `claude-opus-4-7` — last resort

Override via `CLAUDE_MODELS` env var.
