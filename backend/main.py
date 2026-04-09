"""
RAG Backend API - No-Vector Knowledge Base System
Karpathy's approach: Raw Sources -> Wiki -> LLM Queries
"""

from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional, List
import os
from pathlib import Path
import logging

from .services.wiki_manager import WikiManager
from .services.ingestion import IngestionService
from .services.query_engine import QueryEngine
from .services.notion_sync import NotionSync

# Configure logging
logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Wiki RAG Backend",
    description="No-vector RAG system for personal knowledge base",
    version="1.0"
)

# Initialize services
wiki_manager = WikiManager(vault_path=Path("/app/vault"))
ingestion = IngestionService(wiki_manager)
query_engine = QueryEngine(wiki_manager)
notion_sync = NotionSync(wiki_manager) if os.getenv("NOTION_API_KEY") else None


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


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "ok", "service": "wiki-rag-backend"}


@app.get("/stats", response_model=WikiStats)
async def get_wiki_stats():
    """Get wiki statistics"""
    try:
        stats = wiki_manager.get_statistics()
        return WikiStats(**stats)
    except Exception as e:
        logger.error(f"Error getting wiki stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/query", response_model=QueryResponse)
async def query_wiki(request: QueryRequest):
    """Query the wiki using LLM-assisted synthesis"""
    try:
        result = query_engine.query(
            query=request.query,
            max_depth=request.max_depth,
            include_sources=request.include_sources
        )
        return QueryResponse(**result)
    except Exception as e:
        logger.error(f"Error processing query: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/ingest")
async def ingest_source(request: IngestRequest):
    """Ingest a new source into the wiki"""
    try:
        result = ingestion.ingest(
            source_name=request.source_name,
            content=request.content,
            source_url=request.source_url
        )
        return {
            "status": "success",
            "pages_created": result.get("pages_created", 0),
            "pages_updated": result.get("pages_updated", 0),
            "summary": result.get("summary", "")
        }
    except Exception as e:
        logger.error(f"Error during ingestion: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/ingest-file")
async def ingest_file(file: UploadFile = File(...)):
    """Ingest a file (PDF, TXT, MD, etc.)"""
    try:
        content = await file.read()
        filename = file.filename or "unknown"

        result = ingestion.ingest(
            source_name=filename,
            content=content.decode('utf-8', errors='ignore'),
            source_url=None
        )
        return {
            "status": "success",
            "filename": filename,
            "pages_created": result.get("pages_created", 0),
            "pages_updated": result.get("pages_updated", 0),
        }
    except Exception as e:
        logger.error(f"Error during file ingestion: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/maintenance/lint")
async def run_maintenance():
    """Run wiki maintenance tasks (linting, etc.)"""
    try:
        result = wiki_manager.lint()
        return {
            "status": "success",
            "orphaned_pages": result.get("orphaned_pages", []),
            "broken_links": result.get("broken_links", []),
            "contradictions": result.get("contradictions", []),
            "recommendations": result.get("recommendations", [])
        }
    except Exception as e:
        logger.error(f"Error during maintenance: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/sync-notion")
async def sync_notion():
    """Sync from Notion database to wiki"""
    if not notion_sync:
        raise HTTPException(
            status_code=400,
            detail="Notion integration not configured"
        )

    try:
        result = notion_sync.sync_to_wiki()
        return {
            "status": "success",
            "items_synced": result.get("synced", 0),
            "items_updated": result.get("updated", 0),
            "summary": result.get("summary", "")
        }
    except Exception as e:
        logger.error(f"Error syncing from Notion: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/notion/status")
async def notion_sync_status():
    """Get Notion sync status"""
    if not notion_sync:
        return {"enabled": False}

    try:
        status = notion_sync.get_sync_status()
        return {"enabled": True, **status}
    except Exception as e:
        logger.error(f"Error getting Notion status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
