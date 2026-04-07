# Complete Setup Guide

## Prerequisites

- **Docker & Docker Compose** (https://docs.docker.com/compose/install/)
- **Anthropic API Key** (https://console.anthropic.com/)
- **Git** (for version control of your wiki)
- **4GB+ available disk space** (for containers and vault)

## Installation Steps

### 1. Clone Repository

```bash
cd /home/guillaume/perso
# Repository already exists at obsidian-wiki-llm
cd obsidian-wiki-llm
```

### 2. Configure Environment

```bash
# Copy example .env file
cp .env.example .env

# Edit .env with your credentials
nano .env
```

Required variables:
```bash
ANTHROPIC_API_KEY=sk-ant-...  # Get from https://console.anthropic.com/

# Optional (for Notion integration)
NOTION_API_KEY=ntn_...
NOTION_DATABASE_ID=abc123...
```

### 3. Create Directories

```bash
# Create necessary directories
mkdir -p vault raw_sources config/.obsidian
chmod 777 vault raw_sources  # For Docker permissions
```

### 4. Start Services

```bash
# Build and start all containers
docker compose up -d

# Wait for services to start (30-60 seconds)
sleep 30

# Check status
docker compose ps
```

Expected output:
```
NAME                    STATUS
obsidian-wiki           Up 2 seconds
rag-backend             Up 1 second
wiki-cli                Up 1 second
```

### 5. Verify Setup

```bash
# Test API health
curl http://localhost:8000/health
# Should return: {"status":"ok","service":"wiki-rag-backend"}

# Test wiki stats
curl http://localhost:8000/stats
# Should return wiki statistics

# Test Obsidian
open http://localhost:8080
# Or visit in browser: http://localhost:8080
```

### 6. Initialize Git (Optional but Recommended)

```bash
cd /home/guillaume/perso/obsidian-wiki-llm

# Initialize git repository
git init
git config user.email "you@example.com"
git config user.name "Your Name"

# Add to gitignore
cat > .gitignore << 'EOF'
.env
.env.local
.DS_Store
**/node_modules/
vault/.obsidian.plugins.json
vault/.obsidian/workspace.json
vault/.obsidian/cache
__pycache__/
*.pyc
.pytest_cache/
EOF

# Initial commit
git add .
git commit -m "Initial commit: no-vector RAG system with Obsidian"
```

## First Steps

### 1. Create Your First Wiki Page

```bash
# Copy example content
cat > raw_sources/getting-started.md << 'EOF'
# Getting Started with Personal Wiki

This is a system for building a personal knowledge base using LLMs.

## Key Concepts
- **Entities**: People, technologies, concepts
- **Topics**: Thematic collections with cross-references
- **Sources**: Original content references
- **Decisions**: Rationales and choices

## How It Works
Instead of searching raw documents, the LLM maintains a growing wiki.
Knowledge compounds as you add more sources.

## Next Steps
1. Add more sources to raw_sources/
2. Run ingestion to populate wiki
3. Query the wiki to synthesize knowledge
4. Browse in Obsidian
EOF

# Ingest it
docker exec wiki-cli python scripts/ingest.py \
  /workspace/raw_sources/getting-started.md
```

### 2. Query the Wiki

```bash
docker exec wiki-cli python scripts/query.py "What is a personal wiki?"
```

### 3. Browse in Obsidian

Open http://localhost:8080 and explore:
- `entities/` - Extracted concepts
- `topics/` - Thematic hubs
- `sources/` - References to original content
- `decisions/` - Wiki organization decisions

### 4. Check Wiki Statistics

```bash
docker exec wiki-cli python scripts/maintenance.py --action stats
```

## Common Tasks

### Add New Source Documents

```bash
# Copy file to raw_sources/
cp ~/Downloads/research-paper.pdf raw_sources/

# Ingest via CLI
docker exec wiki-cli python scripts/ingest.py \
  /workspace/raw_sources/research-paper.pdf

# Or via API
curl -X POST http://localhost:8000/ingest-file \
  -F "file=@raw_sources/research-paper.pdf"
```

### Query the Wiki

```bash
# Via CLI
docker exec wiki-cli python scripts/query.py "Your question here?"

# Via API
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{"query": "Your question here?"}'
```

### Run Maintenance

```bash
# Find orphaned pages
docker exec wiki-cli python scripts/maintenance.py --action lint

# Find stale pages (>30 days old)
docker exec wiki-cli python scripts/maintenance.py --action stale

# Get comprehensive statistics
docker exec wiki-cli python scripts/maintenance.py --action stats
```

### Sync with Notion

```bash
# One-time sync
docker exec wiki-cli python scripts/notion-sync.py

# Check sync status
docker exec wiki-cli python scripts/notion-sync.py --status
```

## Development Workflow

### Interactive CLI Access

```bash
# Enter CLI container
docker exec -it wiki-cli /bin/bash

# Now you can run commands directly
cd /workspace
python scripts/query.py "Kubernetes"
python scripts/maintenance.py --action stats
ls -la vault/entities/
```

### View Logs

```bash
# Backend logs
docker logs -f rag-backend

# All services
docker compose logs -f
```

### Edit Wiki Manually

Your vault is in `./vault/` on your host machine:

```bash
# Edit a page directly
nano vault/entities/kubernetes.md

# Changes appear immediately in Obsidian
```

### Restart Services

```bash
# Restart all
docker compose restart

# Restart specific service
docker compose restart rag-backend

# Full restart
docker compose down
docker compose up -d
```

## Backup & Migration

### Backup Your Wiki

```bash
# Create timestamped backup
tar -czf vault-backup-$(date +%Y%m%d-%H%M%S).tar.gz vault/

# Or copy to another location
cp -r vault/ ~/backups/wiki-backup-$(date +%Y%m%d)/
```

### Export as Static HTML

```bash
# Use Obsidian publish or export via command line
# For now, your markdown files are in vault/
# You can convert with pandoc or other tools

# Convert single file
pandoc vault/entities/kubernetes.md -o kubernetes.html

# Or use Obsidian export feature (in app)
```

### Git Push (if configured)

```bash
cd vault
git add -A
git commit -m "Wiki update: $(date +%Y-%m-%d)"
git push origin main
```

## Troubleshooting

### Obsidian not loading

```bash
# Check container status
docker ps | grep obsidian

# Restart Obsidian container
docker compose restart obsidian

# Check logs
docker logs obsidian-wiki
```

### API not responding

```bash
# Check if backend is running
docker ps | grep rag-backend

# View logs
docker logs rag-backend

# Test connectivity
docker exec wiki-cli curl http://rag-backend:8000/health
```

### Ingestion fails

```bash
# Check API logs for details
docker logs rag-backend | tail -20

# Try manual test
docker exec wiki-cli python -c "
from backend.services.wiki_manager import WikiManager
from pathlib import Path
wm = WikiManager(Path('/workspace/vault'))
print(wm.get_statistics())
"
```

### File permissions

```bash
# Fix vault permissions
sudo chown -R $(whoami):$(whoami) vault/
chmod -R 755 vault/
```

### API Key issues

```bash
# Verify .env is loaded
docker exec rag-backend env | grep ANTHROPIC_API_KEY

# Check if key is valid
# Try a simple query first
docker exec wiki-cli python scripts/maintenance.py --action stats
```

## Performance Tuning

### Increase API Workers

Edit `docker compose.yml`:

```yaml
rag-backend:
  command: uvicorn backend.main:app --host 0.0.0.0 --port 8000 --workers 4
```

### Limit Query Depth

In `scripts/query.py`:

```python
result = query_engine.query(
    query=query,
    max_depth=2  # Reduce from default 3
)
```

### Adjust Ingestion Size

Edit `config/wiki_schema.yaml`:

```yaml
ingestion:
  max_pages_per_ingest: 10  # Reduce from 15 for faster ingest
```

## Next Steps

1. **Customize Schema** - Edit `config/wiki_schema.yaml` for your categories
2. **Add Content** - Start ingesting your documents
3. **Set Up Notion** - Follow [NOTION_INTEGRATION.md](NOTION_INTEGRATION.md)
4. **Configure Obsidian** - Add plugins and themes in web UI
5. **Automate Sync** - Set up scheduled tasks for Notion/regular maintenance

## Documentation

- [README.md](README.md) - System overview
- [NOTION_INTEGRATION.md](NOTION_INTEGRATION.md) - Notion setup & study
- [config/wiki_schema.yaml](config/wiki_schema.yaml) - Schema configuration

## Getting Help

### Check Logs

```bash
# All logs
docker compose logs

# Specific service
docker logs rag-backend

# Follow logs in real-time
docker logs -f rag-backend
```

### Test Components

```bash
# Test CLI tools
docker exec wiki-cli python scripts/maintenance.py --action stats

# Test API
curl http://localhost:8000/health

# Test wiki manager
docker exec wiki-cli python -c "
from backend.services.wiki_manager import WikiManager
from pathlib import Path
wm = WikiManager(Path('/workspace/vault'))
print('Wiki pages:', wm.list_pages())
"
```

## Clean Up

### Remove Everything

```bash
# Stop containers
docker compose down

# Remove volumes (WARNING: deletes data)
docker compose down -v

# Remove images
docker rmi obsidian-wiki-llm-rag-backend obsidian-wiki-llm-cli-tools
```

### Keep Data, Reset Services

```bash
# Down and up keeps vault data
docker compose down
docker compose up -d
```

## Support

For issues:
1. Check logs: `docker logs <service-name>`
2. Verify environment: Check `.env` file
3. Test components: Use scripts in `scripts/`
4. Review documentation: Check README and specific docs

## Success Indicators

You should see:

✓ Obsidian accessible at http://localhost:8080
✓ API responding at http://localhost:8000/health
✓ Pages created in vault/entities/ and vault/topics/
✓ Queries returning synthesized answers
✓ No errors in Docker logs

Congratulations! Your personal knowledge base is ready.
