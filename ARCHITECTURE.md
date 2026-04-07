# System Architecture & Data Flow

## High-Level Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                   USER INTERACTION LAYER                            │
├─────────────────────────────────────────────────────────────────────┤
│                                                                       │
│  Web Browser (Obsidian)          CLI Tools              API Clients  │
│  http://localhost:8080           make commands           Curl/HTTP   │
│         │                              │                    │        │
└─────────┼──────────────────────────────┼────────────────────┼────────┘
          │                              │                    │
          │ Read vault files             │ Invoke Python      │ REST calls
          │                              │ scripts            │
          ↓                              ↓                    ↓
┌─────────────────────────────────────────────────────────────────────┐
│                     BACKEND API LAYER                               │
│                  (FastAPI on port 8000)                             │
├─────────────────────────────────────────────────────────────────────┤
│                                                                       │
│  ┌─────────────────┐  ┌──────────────────┐  ┌──────────────────┐  │
│  │  Health/Status  │  │  Query Endpoint  │  │ Ingestion Points │  │
│  │  /health        │  │  /query          │  │ /ingest          │  │
│  │  /stats         │  │  /ingest-file    │  │ /ingest-file     │  │
│  │  /notion/status │  │                  │  │ /sync-notion     │  │
│  └─────────────────┘  └──────────────────┘  └──────────────────┘  │
│           │                    │                       │             │
└───────────┼────────────────────┼───────────────────────┼─────────────┘
            │                    │                       │
            │                    ↓                       ↓
            │         ┌────────────────────┐  ┌─────────────────────┐
            │         │  Query Engine      │  │  Ingestion Service  │
            │         │ - Traverse wiki    │  │ - Claude processes  │
            │         │ - BFS links (3hop) │  │ - Updates 10-15 pgs │
            │         │ - Synthesize       │  │ - Cross-references  │
            │         └────────────────────┘  └─────────────────────┘
            │                    │                       │
            └────────────────────┼───────────────────────┘
                                 ↓
                    ┌────────────────────────┐
                    │    Wiki Manager        │
                    │ - CRUD operations      │
                    │ - Frontmatter parsing  │
                    │ - Statistics           │
                    │ - Linting & maintenance│
                    └────────────────┬───────┘
                                     │
                                     ↓
                    ┌────────────────────────┐
                    │   LLM Integration      │
                    │   Anthropic Claude     │
                    │ (Ingestion & Querying) │
                    └────────────────────────┘

            │                    ↑
            └────────────────────┘ Writes/Reads
                                 │
                    ┌────────────▼─────────┐
                    │   Notion Sync        │
                    │ - Query Notion API   │
                    │ - Map properties     │
                    │ - Track sync state   │
                    └────────────────────┬─┘
                                         │
                                         ↓
                            ┌────────────────────┐
                            │  Notion Database   │
                            │  (External)        │
                            └────────────────────┘

            │
            ↓ Reads/Writes
┌─────────────────────────────────────────────────────────────────────┐
│                      STORAGE LAYER                                  │
├─────────────────────────────────────────────────────────────────────┤
│                                                                       │
│  vault/                    raw_sources/         config/              │
│  ├── entities/             ├── docs.pdf         ├── wiki_schema.yaml│
│  ├── topics/               ├── article.md       └── templates/      │
│  ├── sources/              └── research.txt     │  ├── entity.md    │
│  ├── technology_watch/                         │  ├── topic.md     │
│  ├── decisions/                                │  └── tech-watch.md│
│  └── .obsidian/                                                    │
│      (Markdown files)      (Input docs)        (Config)            │
│                                                                       │
│  All git-friendly, version-controllable, locally owned              │
└─────────────────────────────────────────────────────────────────────┘
```

## Data Flow Diagrams

### Ingestion Flow (Raw Source → Wiki)

```
Source Document
      │
      ↓
┌─────────────────────────┐
│  Read & Parse Content   │
│  (Handle PDF, TXT, MD)  │
└───────────┬─────────────┘
            │
            ↓
┌──────────────────────────────────────────┐
│ Claude LLM Analysis                      │
│ - Understand material                    │
│ - Extract entities & concepts            │
│ - Identify relationships                 │
│ - Find contradictions with existing wiki │
└───────────┬────────────────────────────┬─┘
            │                            │
            ↓                            ↓
    ┌───────────────┐        ┌──────────────────────┐
    │ Create Pages  │        │ Track Contradictions │
    │ (10-15 pages) │        │ & Anomalies          │
    │ - Entities    │        └──────────────────────┘
    │ - Topics      │
    │ - Decisions   │
    └───────┬───────┘
            │
            ↓
┌──────────────────────────┐
│ Wiki Manager             │
│ - Write frontmatter      │
│ - Add cross-references   │
│ - Create markdown files  │
└───────────┬──────────────┘
            │
            ↓
    ┌───────────────────┐
    │ vault/            │
    │ ├── entities/     │
    │ ├── topics/       │
    │ └── ...           │
    └───────────────────┘
            │
            ↓
    ┌───────────────────┐
    │ Obsidian renders  │
    │ pages + links     │
    └───────────────────┘
```

### Query Flow (Question → Answer)

```
User Question
      │
      ↓
┌──────────────────────────┐
│ Query Engine             │
│ - Parse query            │
│ - Find relevant pages    │
└───────────┬──────────────┘
            │
            ↓
    ┌──────────────────────────────────┐
    │ BFS Traversal (max depth 3)      │
    │ - Start: matching pages          │
    │ - Expand: follow [[links]]       │
    │ - Gather: related content        │
    │ - Limit: ~20 pages max           │
    └────────────┬─────────────────────┘
                 │
                 ↓
    ┌───────────────────────────────┐
    │ Compile Context               │
    │ (Combine gathered pages)      │
    └────────────┬──────────────────┘
                 │
                 ↓
    ┌──────────────────────────────────┐
    │ Claude LLM Synthesis             │
    │ - Read context                   │
    │ - Find answer                    │
    │ - List sources                   │
    │ - Score confidence               │
    └────────────┬─────────────────────┘
                 │
                 ↓
        ┌────────────────┐
        │ Return Answer  │
        │ + Sources      │
        │ + Entities     │
        │ + Confidence   │
        └────────────────┘
```

### Notion Sync Flow

```
Notion Database (Technology Watch)
      │
      ↓
┌─────────────────────────────────────┐
│ Notion API Query                    │
│ - Fetch all items                   │
│ - Paginate results                  │
│ - Get properties                    │
└──────────────┬──────────────────────┘
               │
               ↓
    ┌──────────────────────────┐
    │ Property Extraction      │
    │ - Title                  │
    │ - Description            │
    │ - Category               │
    │ - URL                    │
    │ - Date Discovered        │
    │ - Status                 │
    └──────────┬───────────────┘
               │
               ↓
    ┌───────────────────────────────┐
    │ Transform to Wiki Format      │
    │ - Generate frontmatter        │
    │ - Create markdown content     │
    │ - Map fields to sections      │
    └──────────┬────────────────────┘
               │
               ↓
    ┌──────────────────────────────┐
    │ Wiki Manager                 │
    │ - Create/Update page         │
    │ - technology_watch/filename  │
    │ - Store Notion ID            │
    └──────────┬───────────────────┘
               │
               ↓
    ┌────────────────────────────────┐
    │ vault/technology_watch/        │
    │ ├── item1.md                   │
    │ ├── item2.md                   │
    │ └── ...                        │
    └────────────┬───────────────────┘
                 │
                 ↓
         ┌───────────────┐
         │ Obsidian View │
         │ + Browsable   │
         │ + Searchable  │
         │ + Linkable    │
         └───────────────┘
```

## Component Interactions

### Wiki Manager (Central Hub)

```
Wiki Manager
├── create_page()
│   ├── Frontmatter validation
│   ├── Directory structure
│   └── File I/O
├── get_page()
│   ├── YAML parsing
│   └── Content extraction
├── list_pages()
│   ├── Directory scanning
│   └── Filtering
├── get_statistics()
│   ├── Counting pages
│   ├── Type classification
│   └── Staleness detection
└── lint()
    ├── Orphan detection
    ├── Link validation
    └── Contradiction checks
```

### Ingestion Service

```
Ingestion Service
├── ingest()
│   ├── Read source content
│   ├── Call Claude with system prompt
│   ├── Parse Claude response (JSON)
│   ├── For each generated page:
│   │   └── wiki_manager.create_page()
│   └── Return statistics
```

### Query Engine

```
Query Engine
├── query()
│   ├── _find_relevant_pages()
│   │   ├── Text matching
│   │   ├── BFS traversal
│   │   └── Depth limiting
│   ├── _compile_context()
│   │   └── Combine page contents
│   └── Call Claude with context
```

### Notion Sync

```
Notion Sync
├── sync_to_wiki()
│   ├── _fetch_notion_items()
│   │   └── notion_client.databases.query()
│   ├── For each item:
│   │   ├── _extract_property()
│   │   └── _sync_item_to_wiki()
│   │       └── wiki_manager.create_page()
│   └── _update_sync_status()
```

## Database & File Format

### Markdown with Frontmatter

```
---
title: "Entity Name"
type: "entity"
created_date: "2024-04-07T10:30:00"
last_updated: "2024-04-07T10:30:00"
tags: ["tag1", "tag2"]
related_entities: ["entity1", "entity2"]
status: "published"
confidence_level: "high"
---

# Entity Name

## Overview
Brief description of the entity.

## Key Characteristics
- Attribute 1
- Attribute 2

## Related Entities
- [[Entity1]]
- [[Entity2]]

## Sources
- Source reference

## References
Cross-references to other pages

## Notes
Internal observations and metadata
```

### Wiki Link Format

- Internal links: `[[page-name]]`
- Markdown links: `[text](file.md)`
- Both are discovered by regex and traversed during queries

## Configuration Hierarchy

```
System Defaults
    ↓
.env (environment variables)
    ↓
config/wiki_schema.yaml (schema rules)
    ↓
config/templates/*.md (page templates)
    ↓
Page Frontmatter (per-page overrides)
```

## Performance Characteristics

| Operation | Time | Limitation |
|-----------|------|-----------|
| Ingest source | 10-30s | 10-15 pages created |
| Query | 3-5s | BFS depth 3, ~20 pages |
| List pages | <1s | O(n) where n = page count |
| Lint | 2-10s | Full vault scan |
| Notion sync | 5-15s | API rate limited |

## Scalability Considerations

### Small Scale (0-50 pages)
- All operations instant
- Single API worker sufficient
- No optimization needed

### Medium Scale (50-200 pages)
- Query response time ~5s
- Can scale API with Uvicorn workers
- Consider caching frequent queries

### Large Scale (200+ pages)
- Consider splitting into multiple wikis
- Implement caching layer
- Use pagination for Notion sync
- Consider indexing for fast lookup

## Security Considerations

1. **API Key Handling**
   - Stored in .env (never committed)
   - Passed via Docker environment
   - Only read by backend services

2. **Data Privacy**
   - All data local (vault/ directory)
   - No external storage beyond Notion opt-in
   - HTTPS for Notion API calls

3. **Input Validation**
   - Frontend validation in API
   - Sanitization of file names
   - Markdown injection protection

## Deployment Architecture

```
Production Deployment
    │
    ├── Docker Host
    │   ├── obsidian-wiki (Obsidian)
    │   ├── rag-backend (API)
    │   └── wiki-cli (Tools)
    │
    ├── Data Volumes
    │   ├── vault/ (mounted)
    │   ├── raw_sources/ (mounted)
    │   └── config/ (mounted)
    │
    └── External Services
        ├── Notion API (optional)
        └── Anthropic API
```

## Development Workflow

```
Developer Machine
    │
    ├── Edit code in backend/
    ├── Edit config in config/
    ├── Run docker compose up
    ├── Test with CLI tools
    ├── Browse in Obsidian
    └── Commit to git
```

## Monitoring & Observability

Available endpoints for monitoring:
- `GET /health` - Service status
- `GET /stats` - Wiki metrics
- `GET /notion/status` - Last sync time
- Docker logs - Service diagnostics

## Future Architecture Improvements

1. **Caching Layer** - Redis for query results
2. **Search Index** - Full-text search
3. **Web UI** - Admin interface for management
4. **Graph DB** - Notion-like relationship visualization
5. **API Authentication** - Secure endpoints
6. **Rate Limiting** - Protect API from abuse

---

This architecture ensures the system is:
- **Modular**: Components are independent
- **Scalable**: Can grow with use
- **Portable**: Works anywhere with Docker
- **Transparent**: You understand the data flow
- **Testable**: Each component can be tested
