# Claude Code Project Instructions

This is a personal knowledge base system implementing Karpathy's no-vector RAG approach with Obsidian and Docker.

## Project Overview

**No-Vector RAG Personal Knowledge Base** — An LLM-maintained wiki for building and querying persistent knowledge. External sources (Notion, Confluence, JIRA, raw documents) sync automatically into a structured Obsidian markdown vault. Claude maintains the wiki and answers natural language queries by traversing it.

Key files:
- `README.md` — Full system documentation
- `AGENTS.md` — AI agent navigation guide (repo layout, extension points, endpoints)
- `IMPLEMENTATION_SUMMARY.md` — Feature overview and architecture
- `SETUP.md` — Step-by-step setup guide
- `docker-compose.yml` — Container orchestration
- `backend/` — FastAPI backend with connectors, scheduling, ingestion, querying
- `config/` — YAML config (sources, vaults, wiki schema, templates)
- `vaults/` — Multi-vault data (one dir per vault)
- `vault/` — Legacy single vault
- `docs/adr/` — Architecture Decision Records

## Architecture

```
External Sources (Notion / Confluence / JIRA)
    ↓ [Connectors + APScheduler]
VaultManager (config/vaults.yaml)
    ↓ [WikiManager per vault]
Markdown Vault → Obsidian UI

Raw Documents
    ↓ [IngestionService]
Markdown Vault

User Query → QueryEngine (BFS) → Claude → Answer
```

## Development Workflow

1. **Start services**: `docker compose up -d`
2. **Browse vault**: http://localhost:8080 (Obsidian)
3. **Query**: `make query Q="Question"` or `docker exec wiki-cli python scripts/query.py "Question"`
4. **Ingest**: `make ingest FILE=raw_sources/file.md`
5. **Maintain**: `make maintenance ACTION=lint`
6. **Manual sync**: `curl -X POST http://localhost:8000/vaults/tech-watch/sync/notion`

Or use Makefile: `make help`

## Key Components

### Backend Services (`backend/services/`)

- **WikiManager** — Vault CRUD, page lifecycle, statistics, linting
- **VaultManager** — Loads `config/vaults.yaml`, owns all WikiManagers, wires connectors
- **ConnectorRegistry** — Self-registering factory for connectors
- **WikiScheduler** — APScheduler daemon: per-binding sync jobs + per-vault maintenance jobs
- **UrlEnricher** — Fetches URLs or content, Claude Haiku deduces 3-7 tags (idempotent)
- **IngestionService** — Claude processes raw sources → creates/updates 10-15 wiki pages
- **QueryEngine** — BFS traversal of wiki, LLM synthesis of answers
- **Connectors** (`connectors/`) — Notion, Confluence (CQL), JIRA (JQL, sprint/epic hubs)

### Configuration

- `config/sources.yaml` — Source definitions with env-var credential references
- `config/vaults.yaml` — Vault definitions, source bindings, sync intervals, enrichment flags
- `config/wiki_schema.yaml` — Legacy wiki structure (directories, templates, ingestion rules)
- `config/templates/` — Markdown templates for page types (entity, topic, tech-watch, decision)

### CLI Tools (`scripts/`)

- `ingest.py` — Add sources to wiki
- `query.py` — Query the wiki
- `maintenance.py` — Lint, stats, health checks
- `notion-sync.py` — Manual Notion sync trigger

## Important Notes for Future Work

### Modifying Core Logic

- `backend/services/wiki_manager.py` — Changes affect all vault operations
- `backend/services/ingestion.py` — Changes how raw sources are processed (10-15 pages per source)
- `backend/services/query_engine.py` — Changes how wiki is queried (BFS depth 3, max 20 pages)
- `backend/services/scheduler.py` — Changes sync timing and job management
- `backend/services/connectors/base_connector.py` — Changes the sync lifecycle for all connectors

### Adding a New Connector

1. Create `backend/services/connectors/myservice_connector.py`
2. Inherit `BaseConnector`, implement `authenticate()`, `fetch_updates()`, `_transform_to_wiki_page()`
3. Add `ConnectorRegistry.register("myservice", MyServiceConnector)` at module level
4. Add source entry in `config/sources.yaml`
5. Add binding in `config/vaults.yaml`

### Adding Features

- New page types: Add to `config/wiki_schema.yaml` + create template in `config/templates/`
- New endpoints: Add to `backend/main.py` following existing patterns
- New CLI commands: Add to `scripts/` using Click framework

### Testing Changes

```bash
make test

docker exec wiki-cli python scripts/maintenance.py --action stats
docker logs rag-backend
curl http://localhost:8000/scheduler/status
curl http://localhost:8000/vaults
```

## Environment Setup

Required in `.env`:
- `ANTHROPIC_API_KEY` — Claude API access

Optional:
- `NOTION_API_KEY` + `NOTION_DATABASE_ID`
- `CONFLUENCE_HOST` + `CONFLUENCE_USERNAME` + `CONFLUENCE_API_TOKEN`
- `JIRA_HOST` + `JIRA_USERNAME` + `JIRA_API_TOKEN`
- `CLAUDE_MODELS` — override model fallback list (comma-separated, cheapest first)

## Common Tasks

```bash
make setup && make start

make ingest FILE=raw_sources/article.md
make query Q="Your question?"

make maintenance ACTION=lint
make maintenance ACTION=stats

make notion-sync
make notion-status
```

## Debugging

```bash
docker exec -it wiki-cli /bin/bash
docker logs -f rag-backend

curl http://localhost:8000/health
curl http://localhost:8000/stats
curl http://localhost:8000/vaults
curl http://localhost:8000/scheduler/status
```

## Architecture Decision Records

Design decisions are documented in `docs/adr/`:
- `001-multi-vault-connector-architecture.md` — Why connector pattern over monolithic NotionSync
- `002-graphify-integration.md` — Graphify knowledge graph assessment (adopted for dev tooling)

## References

- Karpathy's gist: https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f
- Claude API: https://docs.anthropic.com/
- Notion API: https://developers.notion.com/
- Graphify: https://graphify.net/

## Project Status

✓ Core no-vector RAG system implemented and tested
✓ Multi-vault connector framework (Notion, Confluence, JIRA)
✓ APScheduler background sync daemon
✓ URL and content enrichment (Claude-powered tagging)
✓ Docker setup for portability
✓ Complete documentation and ADRs

Ready for: Adding content, activating JIRA connector, deploying to production
