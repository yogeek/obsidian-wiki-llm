# PRD: Autonomous Multi-Source Knowledge Base

## 1. Overview

### Problem

The current system is a functional but fully manual knowledge base:
- Notion is the only supported source, and its connector is hard-coded throughout the codebase
- Adding new knowledge requires copy-pasting content into `raw_sources/`, then manually triggering ingestion
- Maintenance (lint, orphaned page detection) must be triggered manually
- All knowledge ends up in a single vault, mixing unrelated domains (tech watch items sit alongside entities, topics, and decisions with no audience separation)
- Notion items in the tech-watch database contain only a URL — the actual knowledge is the target page, which is never fetched or analyzed

### Goal

Transform the system into an **autonomous, multi-source, multi-vault knowledge base** that:
- Pulls from multiple external sources (Notion, JIRA, Confluence, web clipper) without any manual intervention
- Organizes knowledge into isolated vaults by domain/audience (tech watch, project docs, etc.)
- Routes the same source to multiple vaults using configurable filters
- Self-maintains (lint, orphaned page detection) on a schedule
- Optionally enriches sparse records (like Notion tech-watch items) by fetching and analyzing the target URL content to auto-deduce tags

### What Obsidian Does in This System

Obsidian is the **read/explore layer** — it renders the markdown vaults as a navigable knowledge graph. Its graph view visualizes `[[wiki-links]]` between pages, making domain relationships visible. It does not participate in syncing, maintenance, or querying. Each vault is configured as a separate Obsidian vault, keeping domain graphs isolated.

---

## 2. Definitions

| Term | Definition |
|------|-----------|
| **Vault** | A directory of markdown files representing one knowledge domain (e.g., tech-watch, project-docs). Maps 1:1 to an Obsidian vault. |
| **Source** | An external data provider (Notion, JIRA, Confluence). Defined once with its credentials. |
| **Connector** | Python class that authenticates to a source, fetches items, and transforms them to wiki pages. |
| **Binding** | A (vault, source, filter, schedule) tuple — declares that a source writes to a vault, with optional routing rules and sync interval. |
| **Filter** | Routing rules on a binding (e.g., only JIRA tickets from project PROJ, only Confluence pages in space TECH). |
| **Enrichment** | Optional post-processing step: fetch the URL in a sparse record, use Claude to suggest tags, merge with existing tags. |
| **WikiManager** | Existing generic service for vault CRUD (create/update/lint/stats). Already source-agnostic. |

---

## 3. Goals and Non-Goals

### Goals

- Multiple external sources, each implemented once as a connector
- Multiple vaults, one per knowledge domain, each with its own Obsidian graph
- A single connector can write to multiple vaults via filter rules declared per binding
- Fully autonomous operation: sync and maintenance run on schedule without human intervention
- URL enrichment for Notion tech-watch items: fetch target URL, deduce tags with Claude, merge with manually-set tags — happens once per item, not on every sync
- Manual trigger available for any sync via API endpoint (for debugging / on-demand refresh)
- Backward compatibility: existing `/sync-notion` and `/notion/status` endpoints continue to work

### Non-Goals

- Bi-directional sync (writing back to Notion/JIRA/Confluence from the wiki)
- Real-time sync (webhook-driven) — scheduled polling is sufficient
- A web UI for managing vaults or sources
- Vector embeddings or semantic search (the system stays no-vector RAG)
- Conflict resolution across vaults (if the same Confluence page goes to two vaults, both copies are independent)

---

## 4. User Stories

**As a user:**
- I want Notion to sync automatically every 6 hours so I never have to run `make notion-sync` manually
- I want each knowledge domain (tech watch, project documentation) to live in a separate Obsidian vault so graphs are focused and uncluttered
- I want to add a JIRA or Confluence source by editing a config file and adding environment variables, not by writing code
- I want Notion tech-watch items to have their tags automatically enriched from the linked URL content, without me setting them manually every time
- I want a single Confluence integration that can route tech-related pages to my tech-watch vault and project-related pages to my project-docs vault
- I want the wiki to self-maintain weekly (orphaned page detection, broken link checks) without any cron setup on my end

**As a developer maintaining the system:**
- I want to add a new connector (e.g., GitHub Issues) by implementing a 3-method interface and registering it — no changes to the scheduler, vault manager, or API
- I want connector credentials centralized in one file, not scattered across environment variable checks in multiple services
- I want each (vault, source) binding to track its own sync state independently so a failing Confluence sync doesn't affect the Notion sync state

---

## 5. Architecture

### Layer Model

```
┌─────────────────────────────────────────────────────────┐
│  Obsidian (per vault)  ←  Read/explore layer            │
│  Renders markdown, graph view, manual annotations       │
└─────────────────────────────────────────────────────────┘
                         ↑ reads markdown files
┌─────────────────────────────────────────────────────────┐
│  Vault (markdown files on disk)                         │
│  /app/vaults/tech-watch/                               │
│  /app/vaults/project-docs/                             │
└─────────────────────────────────────────────────────────┘
                         ↑ WikiManager.create_page()
┌─────────────────────────────────────────────────────────┐
│  FastAPI Backend  ←  Write/maintain layer               │
│                                                         │
│  VaultManager                                           │
│  ├─ WikiManager (tech-watch)                           │
│  └─ WikiManager (project-docs)                         │
│                                                         │
│  ConnectorRegistry                                      │
│  ├─ NotionConnector                                    │
│  ├─ JiraConnector                                      │
│  └─ ConfluenceConnector                               │
│                                                         │
│  WikiScheduler (APScheduler daemon)                     │
│  ├─ sync jobs: one per (vault, source) binding         │
│  └─ maintenance jobs: one per vault (weekly)           │
│                                                         │
│  UrlEnricher (optional, per binding)                    │
│  └─ fetches URL, deduces tags via Claude               │
└─────────────────────────────────────────────────────────┘
                         ↑ fetches data
┌─────────────────────────────────────────────────────────┐
│  External Sources                                        │
│  Notion API  /  JIRA API  /  Confluence API             │
└─────────────────────────────────────────────────────────┘
```

### Sync Flow (per binding, triggered by scheduler)

```
Scheduler fires "sync_tech-watch_notion"
    → NotionConnector.authenticate()
    → NotionConnector.fetch_updates(since=last_sync_time, filter={})
    → For each SourceItem:
        → _transform_to_wiki_page(item, vault_category="technology_watch")
        → [if enrich_from_url and not content_fetched]:
            → UrlEnricher.enrich(page_dict, existing_tags)
                → fetch URL content (httpx)
                → Claude: suggest tags from content
                → merge suggested tags with manual tags (union)
                → set content_fetched: true in frontmatter
        → WikiManager.create_page(**page_dict)
    → _save_last_sync_time() [per (source, vault) pair]
    → return SyncResult
```

---

## 6. Configuration

### config/sources.yaml

Defines external sources and their credentials. Source definitions are **reusable** — the same source can be bound to multiple vaults with different filters. No routing logic here.

```yaml
sources:
  notion:
    connector_type: "notion"
    credentials:
      api_key_env: "NOTION_API_KEY"
      database_id_env: "NOTION_DATABASE_ID"

  jira:
    connector_type: "jira"
    credentials:
      api_key_env: "JIRA_API_TOKEN"
      base_url_env: "JIRA_HOST"
      username_env: "JIRA_USERNAME"

  confluence:
    connector_type: "confluence"
    credentials:
      api_key_env: "CONFLUENCE_API_TOKEN"
      base_url_env: "CONFLUENCE_HOST"
      username_env: "CONFLUENCE_USERNAME"
```

### config/vaults.yaml

Defines vaults and their source bindings. **This is where routing rules and enrichment flags live.**

```yaml
vaults:
  tech-watch:
    path: "/app/vaults/tech-watch"
    description: "Technology watch items from Notion, Confluence tech spaces"
    sources:
      - source: notion
        vault_category: "technology_watch"
        filter: {}                         # empty = all items
        sync_interval: "6h"
        enrich_from_url: true              # fetch URL target, auto-deduce tags on first sync

      - source: confluence
        vault_category: "confluence_pages"
        filter:
          space_keys: ["TECH", "TOOLS"]    # only these Confluence spaces
          labels: ["tech-watch"]           # OR: pages with this label (any space)
        sync_interval: "12h"
        enrich_from_url: false

  project-docs:
    path: "/app/vaults/project-docs"
    description: "JIRA tickets and Confluence pages for project PROJ"
    sources:
      - source: jira
        vault_category: "jira_tickets"
        filter:
          project_key: "PROJ"
        sync_interval: "1h"
        enrich_from_url: false

      - source: confluence
        vault_category: "confluence_pages"
        filter:
          space_keys: ["PROJ"]
        sync_interval: "12h"
        enrich_from_url: false

scheduler:
  maintenance:
    enabled: true
    day_of_week: "sun"
    hour: 2
```

### Filter Semantics

| Field | Source | Behavior |
|-------|--------|----------|
| `{}` (empty) | any | Accept all items |
| `space_keys: [A, B]` | Confluence | Include items from space A or B |
| `labels: [x]` | Confluence | Include items tagged with label x |
| `space_keys + labels` | Confluence | OR logic: space match OR label match |
| `project_key: PROJ` | JIRA | Include issues from project PROJ |
| `jql: "..."` | JIRA | Raw JQL override (overrides project_key if both set) |

---

## 7. New Python Modules

### 7.1 BaseConnector (`backend/services/connectors/base_connector.py`)

Abstract base class. All connectors implement these three methods; everything else is handled by the base.

```python
@dataclass
class ConnectorFilter:
    space_keys: List[str] = None
    labels: List[str] = None
    project_key: str = None
    jql: str = None

@dataclass
class SourceItem:
    source_id: str          # External ID (Notion page_id, JIRA issue key, etc.)
    title: str
    content: str            # May be empty for URL-only items (Notion tech-watch)
    metadata: Dict          # Source-specific fields
    fetched_at: datetime
    updated_at: Optional[datetime] = None

@dataclass
class SyncResult:
    source_name: str
    vault_name: str
    items_fetched: int = 0
    items_synced: int = 0
    items_updated: int = 0
    errors: List[str] = field(default_factory=list)
    synced_at: datetime = field(default_factory=datetime.now)

@dataclass
class ConnectorBinding:
    source_name: str
    vault_name: str
    vault_category: str
    sync_interval: str
    filter: ConnectorFilter
    enrich_from_url: bool = False

class BaseConnector(ABC):
    def __init__(self, credentials: Dict[str, str]):
        self.credentials = credentials

    @abstractmethod
    def authenticate(self) -> bool:
        """Verify credentials and connectivity. Raise on failure, return True on success."""

    @abstractmethod
    def fetch_updates(
        self,
        since: Optional[datetime],
        filter: ConnectorFilter
    ) -> List[SourceItem]:
        """
        Fetch new/updated items from the source.
        - Apply filter server-side when the API supports it, otherwise client-side.
        - If since is None, perform initial full sync.
        """

    @abstractmethod
    def _transform_to_wiki_page(
        self,
        item: SourceItem,
        vault_category: str
    ) -> Dict:
        """
        Convert a SourceItem to a wiki page dict:
        {
            "category": str,          # vault subdirectory
            "filename": str,          # slug, no extension
            "frontmatter_data": Dict, # YAML frontmatter fields
            "content": str            # markdown body
        }
        """

    def sync(
        self,
        wiki_manager,
        binding: ConnectorBinding,
        enricher=None
    ) -> SyncResult:
        """
        Template method. Subclasses should not override this.
        fetch → transform → [enrich] → write → save state
        """

    def _status_file_path(self, vault_path: Path) -> Path:
        """Returns: vault_path/.{source_name}.sync_status"""

    def _load_last_sync_time(self, vault_path: Path) -> Optional[datetime]:

    def _save_last_sync_time(self, vault_path: Path):

    def get_sync_status(self, vault_path: Path) -> Dict:
```

### 7.2 NotionConnector (`backend/services/connectors/notion_connector.py`)

Refactored from `backend/services/notion_sync.py`. Identical behavior — French/English property name fallback, multi-tag extraction, tag hub creation. Differences: inherits from `BaseConnector`, status file handling delegated to base, tag hub creation moved to a post-sync hook called from `sync()`.

Key method signatures:
```python
class NotionConnector(BaseConnector):
    def authenticate(self) -> bool: ...
    def fetch_updates(self, since, filter) -> List[SourceItem]: ...
    def _transform_to_wiki_page(self, item, vault_category) -> Dict: ...
    def _extract_tags(self, properties: Dict) -> List[str]: ...       # preserved from NotionSync
    def _extract_property(self, item, field_name, prop_type): ...     # preserved
    def _create_tag_hubs(self, wiki_manager, tags_index: Dict): ...   # post-sync, called from sync()
```

### 7.3 JiraConnector (`backend/services/connectors/jira_connector.py`)

Stub implementation. All methods implemented but returning empty results until credentials are configured and a vault binding is added.

Field mapping (JIRA issue → wiki frontmatter):
- `key` → filename (e.g., `proj-123`)
- `summary` → title
- `description` → content body
- `status.name` → `status`
- `issuetype.name` → `type` tag
- `priority.name` → `priority`
- `assignee.displayName` → `assignee`
- `labels` → `tags`
- `components[].name` → additional `tags`
- `created` / `updated` → `created_date` / `last_updated`

Filter implementation: uses JQL — `project = {project_key} ORDER BY updated DESC` — optionally replacing with raw `jql` field from filter config.

### 7.4 ConfluenceConnector (`backend/services/connectors/confluence_connector.py`)

Stub implementation.

Field mapping (Confluence page → wiki frontmatter):
- `id` → `source_id`
- `title` → title, filename
- `body.storage.value` (HTML stripped) → content body
- `space.key` → `space`
- `metadata.labels[].name` → `tags`
- `version.when` → `last_updated`
- `ancestors[].title` → `breadcrumb` (for graph cross-links)

Filter implementation: queries by `spaceKey` parameter and/or label filter. For label-based routing, fetches pages with matching label from any space.

### 7.5 ConnectorRegistry (`backend/services/connector_registry.py`)

```python
class ConnectorRegistry:
    _registry: Dict[str, Type[BaseConnector]] = {}

    @classmethod
    def register(cls, name: str, connector_class: Type[BaseConnector]): ...

    @classmethod
    def create(cls, connector_type: str, credentials: Dict) -> BaseConnector: ...
```

Connectors self-register at module import time:
```python
# In notion_connector.py
ConnectorRegistry.register("notion", NotionConnector)
```

### 7.6 VaultManager (`backend/services/vault_manager.py`)

Owns the lifecycle of all WikiManager instances and the list of bindings passed to the scheduler.

```python
class VaultManager:
    def __init__(self, sources_config: Path, vaults_config: Path):
        self.vaults: Dict[str, WikiManager] = {}
        self.connectors: Dict[str, BaseConnector] = {}
        self.bindings: List[ConnectorBinding] = []
        self._load(sources_config, vaults_config)

    def _load(self, sources_config: Path, vaults_config: Path):
        # 1. Load sources.yaml → resolve credentials from env → instantiate connectors
        # 2. Load vaults.yaml → instantiate WikiManager per vault
        # 3. Build ConnectorBinding list (one per vault+source entry)

    def get_all_bindings(self) -> List[ConnectorBinding]: ...
    def get_wiki_manager(self, vault_name: str) -> WikiManager: ...
    def get_connector(self, source_name: str) -> BaseConnector: ...
    def list_vaults(self) -> List[Dict]: ...  # names, paths, bound sources, last sync times
```

### 7.7 WikiScheduler (`backend/services/scheduler.py`)

```python
class WikiScheduler:
    def __init__(self, vault_manager: VaultManager, url_enricher=None):
        self.scheduler = BackgroundScheduler(daemon=True)
        self.vault_manager = vault_manager
        self.url_enricher = url_enricher
        self._register_jobs()

    def _register_jobs(self):
        # One IntervalTrigger job per ConnectorBinding
        # One CronTrigger job per vault for weekly maintenance
        # max_instances=1 on all jobs to prevent overlapping runs

    def _sync_job(self, source_name: str, vault_name: str):
        connector = self.vault_manager.get_connector(source_name)
        wiki_manager = self.vault_manager.get_wiki_manager(vault_name)
        binding = self._get_binding(source_name, vault_name)
        enricher = self.url_enricher if binding.enrich_from_url else None
        result = connector.sync(wiki_manager, binding, enricher)
        logger.info("Sync complete: %s → %s: %s", source_name, vault_name, result)

    def _maintenance_job(self, vault_name: str):
        wiki_manager = self.vault_manager.get_wiki_manager(vault_name)
        result = wiki_manager.lint()
        logger.info("Maintenance %s: orphaned=%d, broken_links=%d",
                    vault_name, len(result["orphaned_pages"]), len(result["broken_links"]))

    def start(self): ...
    def stop(self): ...
    def get_status(self) -> Dict: ...  # running, jobs with next_run_time, connector status per vault
```

### 7.8 UrlEnricher (`backend/services/url_enricher.py`)

Only instantiated when at least one binding has `enrich_from_url: true`.

```python
class UrlEnricher:
    def __init__(self, anthropic_client):
        self.client = anthropic_client

    def enrich(self, page_dict: Dict, existing_tags: List[str]) -> Dict:
        """
        Idempotent. If content_fetched: true in frontmatter, returns page_dict unchanged.
        Otherwise:
          1. Fetch URL (httpx, 10s timeout, follow redirects)
          2. Strip HTML to plain text
          3. Claude: suggest 3-7 concise tags from the content
          4. Merge: existing_tags + suggested_tags (union, order-preserving dedup)
          5. Add content_fetched: true to frontmatter
          6. Append a "## Content Summary" section to the page body
        Returns modified page_dict.
        """

    def _fetch_url(self, url: str) -> Optional[str]:
        # httpx GET, 10s timeout, returns stripped plain text
        # Returns None on error (404, timeout, non-text content type)

    def _deduce_tags(self, content: str) -> List[str]:
        # Claude API call with truncated content (first 3000 tokens)
        # Prompt: "Given this content, suggest 3-7 concise lowercase tags..."
        # Returns list of strings
```

---

## 8. API Changes

### New Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/vaults` | List all configured vaults, their sources, and last sync times |
| `GET` | `/vaults/{vault}` | Status for one vault: source bindings, sync states, page counts |
| `POST` | `/vaults/{vault}/sync/{source}` | Manually trigger one (vault, source) binding |
| `GET` | `/scheduler/status` | APScheduler job list with next run times |

### Backward-Compatible Wrappers (no change to behavior)

| Method | Path | Delegates to |
|--------|------|-------------|
| `POST` | `/sync-notion` | `POST /vaults/{first_vault_with_notion}/sync/notion` |
| `GET` | `/notion/status` | `GET /vaults/{first_vault_with_notion}` filtered to notion source |

### Unchanged Endpoints

`GET /health`, `GET /stats`, `POST /query`, `POST /ingest`, `POST /ingest-file`, `POST /maintenance/lint`

---

## 9. File Inventory

### Create

```
backend/services/connectors/
    __init__.py
    base_connector.py         # Abstract base, ConnectorFilter, SourceItem, SyncResult, ConnectorBinding
    notion_connector.py       # Refactored from notion_sync.py
    jira_connector.py         # Stub
    confluence_connector.py   # Stub
backend/services/connector_registry.py
backend/services/vault_manager.py
backend/services/scheduler.py
backend/services/url_enricher.py
config/sources.yaml
config/vaults.yaml
```

### Modify

```
backend/main.py               # VaultManager + WikiScheduler init, new endpoints, backward compat
backend/services/wiki_manager.py  # Add vault_name param to constructor (logging only)
docker-compose.yml            # Mount config/, add vault volume mounts, restart backend
requirements.txt              # Add: apscheduler>=3.10, pyyaml, httpx
.env.example                  # Add JIRA_*, CONFLUENCE_* variables
```

### Deprecate (keep for backward compat)

```
backend/services/notion_sync.py   # Replaced by notion_connector.py; keep as thin wrapper if needed
scripts/notion-sync.py            # Replaced by POST /vaults/{vault}/sync/notion
```

---

## 10. URL Enrichment: Isolation Guarantee

The enrichment step is explicitly opt-in and invisible to connectors that do not need it:

1. `enrich_from_url` defaults to `false` in the binding config — it must be explicitly enabled
2. `UrlEnricher` is only instantiated when at least one binding has `enrich_from_url: true`
3. The enricher is passed as `None` to `connector.sync()` when not needed — the template method skips it
4. The enricher operates on the page dict after `_transform_to_wiki_page()` — it is never called inside any connector method
5. JIRA tickets and Confluence pages have self-contained content and are never configured with `enrich_from_url: true`
6. `content_fetched: true` in frontmatter makes enrichment idempotent — the URL is not re-fetched on subsequent syncs

---

## 11. Phased Delivery

### Phase 1: Core Infrastructure

**Scope:** Full multi-vault architecture with Notion only. Autonomous scheduling. No new sources yet.

**Deliverables:**
- `BaseConnector` + `NotionConnector` (behavioral equivalent of current `NotionSync`)
- `ConnectorRegistry`, `VaultManager`, `WikiScheduler`
- `config/sources.yaml` + `config/vaults.yaml` (Notion → tech-watch vault)
- Updated `backend/main.py` with new endpoints and scheduler lifecycle
- Updated `docker-compose.yml` and `requirements.txt`

**Definition of done:**
- `curl http://localhost:8000/vaults` returns tech-watch vault with Notion binding
- `curl -X POST http://localhost:8000/vaults/tech-watch/sync/notion` produces same output as old `/sync-notion`
- `curl http://localhost:8000/scheduler/status` shows Notion job with next run time
- After 6 hours, logs show automatic sync without manual intervention
- Old `/sync-notion` endpoint still works (backward compat)

### Phase 2: URL Enrichment

**Scope:** Auto-tag deduction for Notion tech-watch items from their URL content.

**Deliverables:**
- `UrlEnricher` service
- `enrich_from_url: true` enabled for Notion binding in `vaults.yaml`
- Enricher wired into `BaseConnector.sync()` template method

**Definition of done:**
- A Notion item with a URL and no manual tags: after first sync, has LLM-suggested tags in frontmatter and `content_fetched: true`
- A Notion item with manual tags: after first sync, tags are union of manual + LLM-suggested
- Second sync of same item: frontmatter unchanged (no re-fetch)
- Notion items without a URL field: unaffected

### Phase 3: JIRA and Confluence

**Scope:** Two new connectors with full field mapping and filter support.

**Deliverables:**
- `JiraConnector` with project/JQL filtering and JIRA field mapping
- `ConfluenceConnector` with space/label filtering and content extraction
- `project-docs` vault entry in `vaults.yaml`
- New env vars in `.env.example`

**Definition of done:**
- JIRA issues from project PROJ appear in `vaults/project-docs/jira_tickets/`
- Confluence pages from space PROJ appear in `vaults/project-docs/confluence_pages/`
- Confluence pages from space TECH appear in `vaults/tech-watch/confluence_pages/`
- A Confluence page in space TECH with label `tech-watch` appears in tech-watch vault
- A Confluence page in space PROJ does not appear in tech-watch vault

### Phase 4: Advanced (Future)

- Web clipper connector: watches a directory for dropped `.md` files, auto-enriches via ingestion pipeline
- `GET /vaults/{vault}/graph` returns link graph as JSON (for external visualization)
- Post-sync hooks: tag hub regeneration, digest generation
- Conflict detection: flag items that appear in multiple vaults via the same source

---

## 12. Non-Functional Requirements

| Requirement | Target |
|------------|--------|
| Sync failure isolation | A failure in one (vault, source) job must not affect other jobs |
| Overlapping sync prevention | `max_instances=1` per APScheduler job |
| URL fetch timeout | 10 seconds; gracefully skip on timeout/error |
| URL enrichment idempotency | Never re-fetch a URL already marked `content_fetched: true` |
| Backward compatibility | Existing `/sync-notion`, `/notion/status` endpoints unchanged |
| Log verbosity | Info: sync start/complete with counts. Warning: per-item errors. Error: auth failures |
| Credential security | Credentials resolved from env vars at startup, never written to disk or logs |

---

## 13. Open Questions

1. **HTML stripping for URL enrichment:** Some pages require JS rendering (SPAs). `httpx` fetches raw HTML. Should we use a headless browser (Playwright) for JS-heavy pages, or accept degraded results for SPAs?

2. **Confluence API version:** Confluence Cloud uses REST API v2 (`/wiki/api/v2`). Confluence Server/DC uses v1 (`/rest/api`). Which environment is targeted?

3. **JIRA attachment content:** Should JIRA ticket attachments (e.g., design docs, PDFs) be fetched and ingested via the LLM ingestion pipeline, or only the ticket text?

4. **Tag hub pages across vaults:** Currently, tag hub pages are generated as a post-sync step in NotionSync. With multi-vault, should each vault generate its own tag hubs independently, or should there be a cross-vault hub concept?

5. **Vault path on host:** The current single vault is `./vault` on the host. With multiple vaults, should they all live in `./vaults/{name}/`, or should each be independently configurable?
