# No-Vector RAG Personal Knowledge Base System

A sophisticated personal knowledge base system implementing Andrej Karpathy's no-vector RAG approach. This system uses Claude LLM to maintain a structured, interconnected wiki of markdown files rather than relying on vector databases.

## Core Concept

Instead of traditional RAG (retrieve and re-answer), this system implements **persistent wiki compilation**:

1. **Raw Sources** - Immutable collection of articles, PDFs, documents
2. **The Wiki** - LLM-maintained markdown files organized by entities, topics, and decisions
3. **Smart Queries** - LLM synthesizes answers from the wiki instead of raw sources

Knowledge compounds over time as the wiki becomes richer with each ingestion.

## Architecture

```
┌─────────────────────────────────────────────┐
│    Obsidian Web UI (Markdown Viewer)        │
│   Docker container on port 3000/3001        │
│  (Selkies remote desktop via linuxserver)   │
└─────────────────────────────────────────────┘
                      ↑
      ┌───────────────┴───────────────┐
      │                               │
┌─────────────────────┐   ┌──────────────────────┐
│  RAG Backend API    │   │   CLI Tools          │
│  (FastAPI/Uvicorn) │   │  (ingest/query)      │
│  Port 8000          │   │  (maintenance)       │
│  Auto-selects models│   │  (model management)  │
└─────────────────────┘   └──────────────────────┘
      ↓ ↓ ↓                    ↓
  Claude API         Vault directory (/vault)
  (Anthropic)        Raw sources (/raw_sources)
  Configurable       Config (/config)
  model selection    
   
  Notion API (optional)
  for technology watch sync
```

## System Components

### 1. Backend API (`backend/`)
- **FastAPI** application providing REST endpoints
- **Wiki Manager** - Vault structure and page operations
- **Ingestion Service** - Claude-powered source processing
- **Query Engine** - Wiki-based Q&A synthesis
- **Notion Sync** - Bi-directional Notion integration

### 2. CLI Tools (`scripts/`)
- `ingest.py` - Add new sources to wiki
- `query.py` - Query the wiki from command line
- `maintenance.py` - Lint, statistics, health checks
- `notion-sync.py` - Sync Notion database

### 3. Docker Setup
- **Obsidian container** - Web interface for browsing vault
- **Backend container** - Python API server
- **CLI container** - Development environment with all tools

### 4. Configuration
- `config/wiki_schema.yaml` - Wiki structure and conventions
- `config/templates/` - Markdown templates for different page types
- `.env` - Environment variables (API keys, etc.)

## Quick Start

### Prerequisites
- Docker and Docker Compose
- Anthropic API key (for Claude)
- Notion API key (optional, for technology watch integration)

### Setup

1. **Clone and setup**
   ```bash
   cd obsidian-wiki-llm
   cp .env.example .env
   # Edit .env and add your API keys
   ```

2. **Configure Claude models (optional)**
   ```bash
   # List available models on your account
   make list-models
   
   # Edit .env and set CLAUDE_MODELS (defaults to Haiku, Sonnet, Opus)
   CLAUDE_MODELS=claude-sonnet-4-6,claude-opus-4-6,claude-opus-4-1-20250805
   ```

3. **Start services**
   ```bash
   docker compose up -d
   ```

4. **Access Obsidian**
   - Open http://localhost:3000 in your browser
   - Your vault will be synced automatically

5. **Check API health**
   ```bash
   curl http://localhost:8000/health
   ```

### First Ingestion

1. **Place source file in raw_sources/**
   ```bash
   echo "Your document content here" > raw_sources/example.md
   ```

2. **Ingest via API**
   ```bash
   curl -X POST http://localhost:8000/ingest \
     -H "Content-Type: application/json" \
     -d '{
       "source_name": "example.md",
       "content": "Your document content...",
       "source_url": "https://example.com"
     }'
   ```

3. **Or use CLI in container**
   ```bash
   docker exec wiki-cli python scripts/ingest.py /workspace/raw_sources/example.md
   ```

4. **Check Obsidian** - New pages will appear in vault/entities/, vault/topics/, etc.

## Usage Examples

### Query the Wiki

```bash
# Via CLI
docker exec wiki-cli python scripts/query.py "What is Kubernetes?"

# Via API
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{"query": "What is Kubernetes?"}'
```

### Ingest Multiple Sources

```bash
# Add research articles
for file in raw_sources/*.pdf; do
  docker exec wiki-cli python scripts/ingest.py "$file"
done
```

### Run Maintenance

```bash
# Get wiki statistics
docker exec wiki-cli python scripts/maintenance.py --action stats

# Find orphaned pages
docker exec wiki-cli python scripts/maintenance.py --action lint

# Find stale pages
docker exec wiki-cli python scripts/maintenance.py --action stale
```

### Sync from Notion

```bash
# One-time sync
docker exec wiki-cli python scripts/notion-sync.py

# Check sync status
docker exec wiki-cli python scripts/notion-sync.py --status
```

## Wiki Structure

```
vault/
├── entities/                 # Concepts, people, technologies
│   └── kubernetes.md
│   └── docker.md
├── topics/                   # Thematic hubs with connections
│   └── container-orchestration.md
├── sources/                  # Imported content references
│   └── karpathy-rag-gist.md
├── technology_watch/         # Synced from Notion
│   └── new-ai-framework.md
├── decisions/                # Decisions and rationales
│   └── chose-claude-api.md
└── .obsidian/               # Obsidian configuration
```

## Notion Integration Study

See [NOTION_INTEGRATION.md](NOTION_INTEGRATION.md) for comprehensive analysis of how to connect your Notion technology watch database to this system.

## API Endpoints

### Health & Status
- `GET /health` - Service health check
- `GET /stats` - Wiki statistics
- `GET /notion/status` - Notion sync status

### Core Operations
- `POST /query` - Query the wiki
- `POST /ingest` - Ingest source content
- `POST /ingest-file` - Ingest uploaded file

### Maintenance
- `POST /maintenance/lint` - Run wiki linting
- `POST /sync-notion` - Sync from Notion database

## Configuration

### Customizing Wiki Schema

Edit `config/wiki_schema.yaml` to:
- Change directory structure
- Add new page types
- Configure ingestion behavior
- Adjust maintenance checks

### Environment Variables

```bash
# Required
ANTHROPIC_API_KEY=sk-...

# Model Configuration (optional)
# Comma-separated list of models to try in order (defaults to Haiku, Sonnet, Opus)
# Run 'make list-models' to see all available models on your account
CLAUDE_MODELS=claude-sonnet-4-6,claude-opus-4-6,claude-opus-4-1-20250805

# Optional (for Notion integration)
NOTION_API_KEY=ntn_...
NOTION_DATABASE_ID=123456...

# System
DEBUG=false
LOG_LEVEL=INFO
```

### Model Selection

The system automatically detects and uses the first available model from the `CLAUDE_MODELS` list:

```bash
# See all available models on your account
make list-models

# Test a specific model
make test-model MODEL=claude-sonnet-4-6

# Update .env with your preferred models
CLAUDE_MODELS=claude-sonnet-4-6,claude-opus-4-6

# Restart to apply
docker compose restart
```

**Recommended configurations:**
- **Development/Testing**: `claude-haiku-4-5-20251001` (cheapest)
- **Balanced**: `claude-sonnet-4-6` (fast, good quality, lower cost)
- **High Quality**: `claude-opus-4-6` (most capable, higher cost)

## Portability

This system is designed for easy deployment across environments:

1. **All data in vault/** - Git-friendly markdown files
2. **Docker Compose** - Consistent across machines
3. **Config in config/** - Easily customizable
4. **Stateless API** - No database dependencies
5. **Environment-based secrets** - Use .env files

### Deploy to Production

```bash
# Build images
docker compose build

# Push to registry (optional)
docker tag obsidian-wiki-llm:latest registry.example.com/wiki:latest

# Deploy with docker compose on target machine
docker compose -f docker compose.yml up -d
```

## Advanced Usage

### Custom Page Types

Add new types to `config/wiki_schema.yaml`:

```yaml
structure:
  directories:
    research_papers:
      description: "Academic papers"
      template: "research-template.md"
```

Create template in `config/templates/research-template.md`.

### Batch Ingestion

```bash
# Process multiple files
for file in raw_sources/*.md; do
  docker exec wiki-cli python scripts/ingest.py "$file" \
    --url "file://$(basename $file)"
done
```

### Export Wiki

```bash
# Copy vault to external location
cp -r vault/ ~/backup/wiki-backup-$(date +%Y%m%d)

# Or sync to Git
cd vault && git push origin main
```

## Performance Considerations

- **Query depth**: Limited to 3 hops by default (configurable) to control context
- **Page limit**: Ingestion limited to 15 pages per source for focused updates
- **Wiki size**: Filesystem-based, suitable for ~100-500 pages
- **API concurrency**: Single-threaded by default, can scale with Uvicorn workers

## Troubleshooting

### Obsidian can't access vault
```bash
# Check vault exists
docker exec obsidian-wiki ls -la /workspace/vault

# Check permissions
docker exec obsidian-wiki ls -la /workspace
```

### API errors
```bash
# Check logs
docker logs rag-backend

# Test connectivity
docker exec rag-backend curl localhost:8000/health
```

### Notion sync not working
```bash
# Verify credentials
echo $NOTION_API_KEY

# Check database ID
docker exec cli-tools python scripts/notion-sync.py --status
```

## Next Steps

1. [Set up Notion integration](NOTION_INTEGRATION.md)
2. Configure your first wiki schema in `config/wiki_schema.yaml`
3. Start ingesting sources with `docker exec wiki-cli python scripts/ingest.py`
4. Open Obsidian and browse your knowledge base
5. Run queries with `docker exec wiki-cli python scripts/query.py`

## References

- [Karpathy's No-Vector RAG Gist](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f)
- [LLM Wiki Repository](https://github.com/Ss1024sS/LLM-wiki)
- [Obsidian Documentation](https://help.obsidian.md/)
- [Claude API Documentation](https://docs.anthropic.com/)
- [Notion API Documentation](https://developers.notion.com/)

## License

MIT

## Contributing

Contributions welcome! Please open issues or PRs for improvements.
