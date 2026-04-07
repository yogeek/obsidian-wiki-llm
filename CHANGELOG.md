# Changelog

All notable changes to this project will be documented in this file.

## [1.0.0] - 2026-04-07

### Major Features
- **Complete end-to-end system** - Fully functional no-vector RAG personal knowledge base
- **Docker-based deployment** - Obsidian, FastAPI backend, and CLI tools in containers
- **LLM-powered ingestion** - Claude automatically processes sources and creates wiki pages
- **Wiki-based querying** - BFS traversal and LLM synthesis for intelligent answers
- **Notion integration** - Sync technology watch database to wiki
- **Configurable model selection** - Support for multiple Claude models with auto-detection

### New in This Release

#### Model Configuration System
- Added `scripts/get_models.py` - Fetch and test available models from Anthropic API
- Added `CLAUDE_MODELS` environment variable - Specify models as comma-separated list
- Auto-detection - System tries models in order, uses first available
- New Make targets: `make list-models` and `make test-model MODEL=<name>`
- Default fallback chain: Haiku → Sonnet → Opus (cheapest to most capable)

#### Infrastructure Updates
- Updated Obsidian to use `linuxserver/obsidian` image with Selkies remote desktop
- Changed Obsidian port from 8080 to 3000/3001 (web streaming)
- Added proper environment variable passing to Docker containers
- Updated docker-compose.yml to pass CLAUDE_MODELS to both backend and CLI containers

#### Bug Fixes
- Fixed JSON parsing for Claude responses wrapped in markdown code blocks
- Increased ingestion max_tokens from 4000 to 8000 to prevent truncation
- Updated Anthropic SDK version (>=0.25.0) to support corporate proxy bypass
- Removed non-existent pathlib-glob dependency
- Added httpx certificate verification bypass for corporate proxy environments

#### Documentation
- Updated README.md with model configuration section
- Added model selection guide and recommended configurations
- Updated architecture diagram to reflect current ports and features
- Documented all environment variables and their purposes

### Technical Details

#### Supported Models
Access to 9 Claude models:
- claude-sonnet-4-6 (recommended for balance)
- claude-opus-4-6 (most capable)
- claude-opus-4-5-20251101
- claude-haiku-4-5-20251001 (cheapest)
- claude-sonnet-4-5-20250929
- claude-opus-4-1-20250805
- claude-opus-4-20250514
- claude-sonnet-4-20250514
- claude-3-haiku-20240307

#### Performance
- First successful ingestion: 10 pages created from sample document
- Model detection: ~2-3 seconds per startup
- Query synthesis: BFS up to depth 3 with configurable context limits

### Known Limitations
- Filesystem-based wiki suitable for ~100-500 pages
- Ingestion limited to 15 pages per source (by design, for focused updates)
- Query depth limited to 3 hops (configurable in query_engine.py)

### Files Changed
- `backend/services/ingestion.py` - Model configuration, JSON parsing fix
- `backend/services/query_engine.py` - Model configuration, JSON parsing fix
- `scripts/get_models.py` - New script for model discovery
- `docker-compose.yml` - Obsidian image update, environment variable passing
- `Makefile` - New targets for model management
- `.env` - CLAUDE_MODELS configuration
- `README.md` - Updated documentation

### Breaking Changes
- Obsidian now runs on port 3000/3001 instead of 8080 (localhost:3000)
- Docker containers now require `docker compose down && docker compose up` for clean start

### Testing
- Verified ingestion creates wiki pages correctly
- Tested query synthesis with multi-page knowledge base
- Confirmed model auto-detection works as expected
- Tested API endpoints: /health, /stats, /ingest, /query

## [0.1.0] - Initial Setup
- Project initialization with Docker Compose
- Basic backend API with FastAPI
- CLI tools for ingestion and querying
- Notion integration framework
