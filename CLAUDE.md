# Claude Code Project Instructions

This is a personal knowledge base system implementing Karpathy's no-vector RAG approach with Obsidian and Docker.

## Project Overview

**No-Vector RAG Personal Knowledge Base** - An LLM-maintained wiki for building and querying persistent knowledge.

Key files:
- `README.md` - Full system documentation
- `NOTION_INTEGRATION.md` - Notion sync analysis and implementation
- `SETUP.md` - Step-by-step setup guide
- `docker compose.yml` - Container orchestration
- `backend/` - FastAPI backend with ingestion, querying, maintenance
- `scripts/` - CLI tools for ingest, query, maintenance, notion-sync
- `config/` - Wiki schema, templates
- `vault/` - Obsidian vault (markdown files)

## Architecture

```
Notion API → NotionSync → Wiki Manager → Markdown Vault → Obsidian
Raw Sources → Ingestion → Page Creation
User Query → Query Engine → LLM Synthesis
```

## Development Workflow

1. **Start services**: `docker compose up -d`
2. **Browse vault**: http://localhost:8080 (Obsidian)
3. **Query**: `docker exec wiki-cli python scripts/query.py "Question"`
4. **Ingest**: `docker exec wiki-cli python scripts/ingest.py raw_sources/file.md`
5. **Maintain**: `docker exec wiki-cli python scripts/maintenance.py --action lint`

Or use Makefile: `make help`

## Key Components

### Backend Services (`backend/services/`)

- **WikiManager** - Vault operations, page CRUD, statistics, linting
- **IngestionService** - Claude processes sources → updates wiki pages (10-15 pages per source)
- **QueryEngine** - BFS traversal of wiki, synthesize answers using LLM
- **NotionSync** - Sync Notion database items to technology_watch/ directory

### CLI Tools (`scripts/`)

- `ingest.py` - Add sources to wiki
- `query.py` - Query the wiki
- `maintenance.py` - Lint, stats, health checks
- `notion-sync.py` - Sync from Notion

### Configuration

- `wiki_schema.yaml` - Structure, ingestion rules, maintenance settings, Notion mapping
- `templates/` - Markdown templates for different page types (entity, topic, tech-watch, decision)

## Important Notes for Future Work

### Modifying Core Logic

When editing:
- `backend/services/wiki_manager.py` - Changes affect all vault operations
- `backend/services/ingestion.py` - Changes how sources are processed (currently 10-15 pages per source)
- `backend/services/query_engine.py` - Changes how wiki is queried (BFS up to depth 3)

### Adding Features

Use existing patterns:
- New page types: Add to `wiki_schema.yaml` + create template in `config/templates/`
- New endpoints: Add to `backend/main.py` following existing patterns
- New CLI commands: Add to `scripts/` using Click framework

### Testing Changes

```bash
# Quick test
make test

# Test specific service
docker exec wiki-cli python scripts/maintenance.py --action stats

# Check logs
docker logs rag-backend
```

## Environment Setup

Required in `.env`:
- `ANTHROPIC_API_KEY` - Claude API access
- `NOTION_API_KEY` (optional) - Notion database integration
- `NOTION_DATABASE_ID` (optional) - Notion tech watch database

## Common Tasks

```bash
# Setup
make setup && make start

# Ingest & Query
make ingest FILE=raw_sources/article.md
make query Q="Your question?"

# Maintenance
make maintenance ACTION=lint
make maintenance ACTION=stats

# Notion
make notion-sync
make notion-status
```

## Git Workflow

Vault is designed for git:
```bash
cd vault
git add -A
git commit -m "Wiki update: $(date)"
git push
```

## Debugging

```bash
# Shell into container
docker exec -it wiki-cli /bin/bash

# View logs
docker logs -f rag-backend

# Test components
curl http://localhost:8000/health
curl http://localhost:8000/stats
```

## Future Enhancements

Possible improvements documented in NOTION_INTEGRATION.md:
- Bi-directional Notion sync
- Incremental sync (only changed items)
- Custom field mapping in schema
- Web UI for management
- Automated evaluation workflows

## References

- Karpathy's gist: https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f
- LLM Wiki: https://github.com/Ss1024sS/LLM-wiki
- Claude API: https://docs.anthropic.com/
- Notion API: https://developers.notion.com/

## Project Status

✓ Core system implemented and tested
✓ Docker setup for portability
✓ Notion integration implemented
✓ Complete documentation

Ready for: Adding content, customizing schema, deploying to production
