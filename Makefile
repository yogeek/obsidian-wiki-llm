.PHONY: help setup start stop logs clean query ingest maintenance notion-sync test

help:
	@echo "No-Vector RAG Personal Knowledge Base - Available Commands"
	@echo ""
	@echo "Setup & Installation:"
	@echo "  make setup          - Initial setup (create dirs, build images)"
	@echo "  make start          - Start all containers"
	@echo "  make stop           - Stop all containers"
	@echo "  make restart        - Restart all containers"
	@echo "  make clean          - Remove containers and volumes (keeps vault data)"
	@echo ""
	@echo "Wiki Operations:"
	@echo "  make ingest FILE=<path>     - Ingest source file"
	@echo "  make query Q='<question>'   - Query the wiki"
	@echo "  make maintenance ACTION=<lint|stats|stale> - Run maintenance"
	@echo "  make notion-sync    - Sync from Notion database"
	@echo ""
	@echo "Model Configuration:"
	@echo "  make list-models    - Show available Claude models on your account"
	@echo "  make test-model MODEL=<name> - Test if a model is available"
	@echo "  Edit .env CLAUDE_MODELS to configure which models to use"
	@echo ""
	@echo "Development:"
	@echo "  make logs           - Show all container logs"
	@echo "  make shell          - Enter CLI container shell"
	@echo "  make test           - Run health checks"
	@echo "  make status         - Show container status"
	@echo "  make test-api       - Test Anthropic API key and credits"
	@echo ""
	@echo "URLs:"
	@echo "  Obsidian: http://localhost:3000"
	@echo "  API: http://localhost:8000"
	@echo "  API Docs: http://localhost:8000/docs"

setup:
	@echo "Setting up project structure..."
	mkdir -p vault raw_sources config/.obsidian
	cp .env.example .env
	@echo "✓ Directories created"
	@echo "✓ .env file created - edit with your API keys"
	@echo ""
	@echo "Next: Edit .env and run 'make start'"

build:
	@echo "Building Docker images..."
	docker compose build
	@echo "✓ Build complete"

start:
	@echo "Starting services..."
	docker compose up -d
	@echo "✓ Services starting..."
	@echo ""
	@echo "Waiting for services to be ready..."
	sleep 5
	@make status
	@echo ""
	@echo "URLs:"
	@echo "  Obsidian: http://localhost:8080"
	@echo "  API: http://localhost:8000/health"

stop:
	@echo "Stopping services..."
	docker compose down
	@echo "✓ Services stopped"

restart:
	@echo "Restarting services..."
	docker compose restart
	@echo "✓ Services restarted"

status:
	@echo "Container Status:"
	@docker compose ps
	@echo ""
	@echo "Health check:"
	@curl -s http://localhost:8000/health | python3 -m json.tool || echo "API not ready yet"

logs:
	docker compose logs -f

logs-backend:
	docker logs -f rag-backend

logs-api:
	curl -s http://localhost:8000/docs | head -20

shell:
	docker exec -it wiki-cli /bin/bash

test:
	@echo "Running health checks..."
	@echo "1. API Health:"
	@curl -s http://localhost:8000/health | python3 -m json.tool
	@echo ""
	@echo "2. Wiki Stats:"
	@curl -s http://localhost:8000/stats | python3 -m json.tool
	@echo ""
	@echo "3. Service Status:"
	@docker compose ps

test-api:
	@echo "Testing Anthropic API key and credits..."
	@bash test_api.sh

list-models:
	@echo "Fetching available Claude models from your Anthropic account..."
	docker exec wiki-cli python scripts/get_models.py

test-model:
	@if [ -z "$(MODEL)" ]; then \
		echo "Usage: make test-model MODEL=claude-sonnet-4-6"; \
		echo "Example: make test-model MODEL=claude-sonnet-4-6"; \
	else \
		docker exec wiki-cli python scripts/get_models.py test $(MODEL); \
	fi

clean:
	@echo "Cleaning up containers..."
	docker compose down
	@echo "✓ Containers removed (vault data preserved)"

clean-all:
	@echo "WARNING: This will delete all containers and volumes!"
	@echo "Press Ctrl+C to cancel, or wait 5 seconds..."
	@sleep 5
	docker compose down -v
	@echo "✓ All cleaned up"

ingest:
	@if [ -z "$(FILE)" ]; then \
		echo "Usage: make ingest FILE=/path/to/file"; \
		echo "Example: make ingest FILE=raw_sources/article.md"; \
	else \
		docker exec wiki-cli python scripts/ingest.py $(FILE); \
	fi

query:
	@if [ -z "$(Q)" ]; then \
		echo "Usage: make query Q='Your question here'"; \
		echo "Example: make query Q='What is Kubernetes?'"; \
	else \
		docker exec wiki-cli python scripts/query.py "$(Q)"; \
	fi

maintenance:
	@if [ -z "$(ACTION)" ]; then \
		echo "Usage: make maintenance ACTION=<action>"; \
		echo "Available actions: lint, stats, stale, broken-links"; \
		echo "Example: make maintenance ACTION=lint"; \
	else \
		docker exec wiki-cli python scripts/maintenance.py --action $(ACTION); \
	fi

notion-sync:
	@echo "Syncing from Notion..."
	docker exec wiki-cli python scripts/notion-sync.py

notion-status:
	@echo "Checking Notion sync status..."
	docker exec wiki-cli python scripts/notion-sync.py --status

# Example commands for common workflows
examples:
	@echo "Common Workflows:"
	@echo ""
	@echo "1. Ingest a file:"
	@echo "   make ingest FILE=raw_sources/article.md"
	@echo ""
	@echo "2. Query the wiki:"
	@echo "   make query Q='What technologies are trending in AI?'"
	@echo ""
	@echo "3. Check wiki health:"
	@echo "   make maintenance ACTION=lint"
	@echo ""
	@echo "4. Get statistics:"
	@echo "   make maintenance ACTION=stats"
	@echo ""
	@echo "5. Sync Notion:"
	@echo "   make notion-sync"
	@echo ""
	@echo "6. Interactive shell:"
	@echo "   make shell"

# Development targets
format:
	black backend scripts

lint:
	pylint backend scripts

requirements:
	docker exec wiki-cli pip list

# Backup targets
backup:
	tar -czf vault-backup-$$(date +%Y%m%d-%H%M%S).tar.gz vault/
	@echo "✓ Backup created"

restore:
	@if [ -z "$(FILE)" ]; then \
		echo "Usage: make restore FILE=vault-backup-*.tar.gz"; \
	else \
		tar -xzf $(FILE); \
		echo "✓ Restored from $(FILE)"; \
	fi

.DEFAULT_GOAL := help
