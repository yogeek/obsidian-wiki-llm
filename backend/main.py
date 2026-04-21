"""
RAG Backend API - No-Vector Knowledge Base System
Karpathy's approach: Raw Sources -> Wiki -> LLM Queries
"""

import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import List, Optional

import anthropic
from fastapi import FastAPI, File, HTTPException, UploadFile
from pydantic import BaseModel

from .services.ingestion import IngestionService
from .services.query_engine import QueryEngine
from .services.wiki_manager import WikiManager

# Configure logging
logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Legacy single-vault services (backward compat for /query, /ingest, /stats)
# ---------------------------------------------------------------------------
wiki_manager = WikiManager(vault_path=Path("/app/vault"))
ingestion = IngestionService(wiki_manager)
query_engine = QueryEngine(wiki_manager)

# ---------------------------------------------------------------------------
# Multi-vault services (new architecture)
# ---------------------------------------------------------------------------
vault_manager = None
scheduler = None
url_enricher = None

_sources_config = Path("/app/config/sources.yaml")
_vaults_config = Path("/app/config/vaults.yaml")

if _sources_config.exists() and _vaults_config.exists():
    try:
        import yaml  # noqa: F401 - verify pyyaml is available
        from .services.vault_manager import VaultManager
        from .services.scheduler import WikiScheduler
        from .services.url_enricher import UrlEnricher

        vault_manager = VaultManager(_sources_config, _vaults_config)

        anthropic_client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY", ""))
        needs_enricher = any(
            b.enrich_from_url or b.enrich_from_content
            for b in vault_manager.get_all_bindings()
        )
        url_enricher = UrlEnricher(anthropic_client) if needs_enricher else None

        vaults_raw = yaml.safe_load(_vaults_config.read_text()) or {}
        maintenance_cfg = (vaults_raw.get("scheduler") or {}).get("maintenance", {})
        scheduler = WikiScheduler(vault_manager, url_enricher, maintenance_cfg)

        logger.info("Multi-vault system loaded: %d vault(s)", len(vault_manager.vaults))
    except Exception as e:
        logger.warning("Multi-vault system failed to initialize: %s", e)
        vault_manager = None
        scheduler = None
else:
    logger.info(
        "config/sources.yaml or config/vaults.yaml not found — multi-vault system disabled"
    )

# Legacy Notion sync (backward compat, used only when multi-vault is not available)
_legacy_notion_sync = None
if vault_manager is None and os.getenv("NOTION_API_KEY"):
    try:
        from .services.notion_sync import NotionSync
        _legacy_notion_sync = NotionSync(wiki_manager)
    except Exception as e:
        logger.warning("Legacy Notion sync failed to initialize: %s", e)


# ---------------------------------------------------------------------------
# Lifespan
# ---------------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    if scheduler:
        scheduler.start()
    yield
    if scheduler:
        scheduler.stop()


app = FastAPI(
    title="Wiki RAG Backend",
    description="No-vector RAG system for personal knowledge base",
    version="2.0",
    lifespan=lifespan,
)


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------
class QueryRequest(BaseModel):
    query: str
    max_depth: int = 3
    include_sources: bool = True


class QueryResponse(BaseModel):
    answer: str
    sources: List[str]
    related_entities: List[str]
    confidence: float


class IngestRequest(BaseModel):
    source_name: str
    content: str
    source_url: Optional[str] = None


class WikiStats(BaseModel):
    total_pages: int
    total_entities: int
    total_topics: int
    total_sources: int
    orphaned_pages: int
    stale_pages: int
    last_maintenance: Optional[str]


# ---------------------------------------------------------------------------
# Unchanged legacy endpoints
# ---------------------------------------------------------------------------
@app.get("/health")
async def health_check():
    return {"status": "ok", "service": "wiki-rag-backend"}


@app.get("/stats", response_model=WikiStats)
async def get_wiki_stats():
    try:
        stats = wiki_manager.get_statistics()
        return WikiStats(**stats)
    except Exception as e:
        logger.error("Error getting wiki stats: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/query", response_model=QueryResponse)
async def query_wiki(request: QueryRequest):
    try:
        result = query_engine.query(
            query=request.query,
            max_depth=request.max_depth,
            include_sources=request.include_sources,
        )
        return QueryResponse(**result)
    except Exception as e:
        logger.error("Error processing query: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/ingest")
async def ingest_source(request: IngestRequest):
    try:
        result = ingestion.ingest(
            source_name=request.source_name,
            content=request.content,
            source_url=request.source_url,
        )
        return {
            "status": "success",
            "pages_created": result.get("pages_created", 0),
            "pages_updated": result.get("pages_updated", 0),
            "summary": result.get("summary", ""),
        }
    except Exception as e:
        logger.error("Error during ingestion: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/ingest-file")
async def ingest_file(file: UploadFile = File(...)):
    try:
        content = await file.read()
        filename = file.filename or "unknown"
        result = ingestion.ingest(
            source_name=filename,
            content=content.decode("utf-8", errors="ignore"),
            source_url=None,
        )
        return {
            "status": "success",
            "filename": filename,
            "pages_created": result.get("pages_created", 0),
            "pages_updated": result.get("pages_updated", 0),
        }
    except Exception as e:
        logger.error("Error during file ingestion: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/maintenance/lint")
async def run_maintenance():
    try:
        result = wiki_manager.lint()
        return {
            "status": "success",
            "orphaned_pages": result.get("orphaned_pages", []),
            "broken_links": result.get("broken_links", []),
            "contradictions": result.get("contradictions", []),
            "recommendations": result.get("recommendations", []),
        }
    except Exception as e:
        logger.error("Error during maintenance: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


# ---------------------------------------------------------------------------
# Backward-compat Notion wrappers (delegate to multi-vault when available)
# ---------------------------------------------------------------------------
@app.post("/sync-notion")
async def sync_notion():
    if vault_manager:
        notion_vault = vault_manager.find_notion_vault()
        if notion_vault and scheduler:
            try:
                result = scheduler.trigger_sync("notion", notion_vault)
                return {
                    "status": "success",
                    "items_synced": result.get("items_synced", 0),
                    "items_updated": result.get("items_updated", 0),
                    "summary": (
                        f"Synced {result.get('items_synced', 0)} new, "
                        f"updated {result.get('items_updated', 0)} items"
                    ),
                }
            except Exception as e:
                logger.error("Error syncing from Notion: %s", e)
                raise HTTPException(status_code=500, detail=str(e))

    if _legacy_notion_sync:
        try:
            result = _legacy_notion_sync.sync_to_wiki()
            return {
                "status": "success",
                "items_synced": result.get("synced", 0),
                "items_updated": result.get("updated", 0),
                "summary": result.get("summary", ""),
            }
        except Exception as e:
            logger.error("Error syncing from Notion (legacy): %s", e)
            raise HTTPException(status_code=500, detail=str(e))

    raise HTTPException(status_code=400, detail="Notion integration not configured")


@app.get("/notion/status")
async def notion_sync_status():
    if vault_manager:
        notion_vault = vault_manager.find_notion_vault()
        if notion_vault:
            connector = vault_manager.connectors.get("notion")
            wm = vault_manager.get_wiki_manager(notion_vault)
            status = connector.get_sync_status(wm.vault_path) if connector else {}
            return {"enabled": True, "vault": notion_vault, **status}

    if _legacy_notion_sync:
        try:
            status = _legacy_notion_sync.get_sync_status()
            return {"enabled": True, **status}
        except Exception as e:
            logger.error("Error getting Notion status: %s", e)
            raise HTTPException(status_code=500, detail=str(e))

    return {"enabled": False}


# ---------------------------------------------------------------------------
# New multi-vault endpoints
# ---------------------------------------------------------------------------
def _require_vault_manager():
    if vault_manager is None:
        raise HTTPException(
            status_code=503,
            detail="Multi-vault system not initialized (check config/sources.yaml and config/vaults.yaml)",
        )


@app.get("/vaults")
async def list_vaults():
    _require_vault_manager()
    return {"vaults": vault_manager.list_vaults()}


@app.get("/vaults/{vault_name}")
async def get_vault(vault_name: str):
    _require_vault_manager()
    try:
        wm = vault_manager.get_wiki_manager(vault_name)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Vault not found: {vault_name}")

    vault_bindings = [
        b for b in vault_manager.get_all_bindings() if b.vault_name == vault_name
    ]
    sources = []
    for binding in vault_bindings:
        connector = vault_manager.connectors.get(binding.source_name)
        sync_status = {}
        if connector:
            try:
                sync_status = connector.get_sync_status(wm.vault_path)
            except Exception:
                sync_status = {"last_sync": None}
        sources.append({
            "source": binding.source_name,
            "vault_category": binding.vault_category,
            "sync_interval": binding.sync_interval,
            "enrich_from_url": binding.enrich_from_url,
            **sync_status,
        })

    stats = wm.get_statistics()
    return {
        "name": vault_name,
        "path": str(wm.vault_path),
        "stats": stats,
        "sources": sources,
    }


@app.post("/vaults/{vault_name}/sync/{source_name}")
async def trigger_vault_sync(vault_name: str, source_name: str):
    _require_vault_manager()
    if vault_name not in vault_manager.vaults:
        raise HTTPException(status_code=404, detail=f"Vault not found: {vault_name}")
    if source_name not in vault_manager.connectors:
        raise HTTPException(status_code=404, detail=f"Source not found: {source_name}")
    if scheduler is None:
        raise HTTPException(status_code=503, detail="Scheduler not initialized")
    try:
        result = scheduler.trigger_sync(source_name, vault_name)
        return {"status": "success", **result}
    except Exception as e:
        logger.error("Error triggering sync %s -> %s: %s", source_name, vault_name, e)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/scheduler/status")
async def get_scheduler_status():
    _require_vault_manager()
    if scheduler is None:
        return {"running": False, "jobs": []}
    return scheduler.get_status()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
