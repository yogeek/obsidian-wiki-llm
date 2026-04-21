# ADR 001: Multi-Vault Connector Architecture

**Status**: Accepted
**Date**: 2026-04-21

## Context

The initial system had a single monolithic `NotionSync` service hardcoded to sync one Notion database into one vault directory. As requirements grew to include Confluence and JIRA, replicating the sync logic per source would have led to duplication and made it impossible to route the same source to multiple vaults with different filters.

## Decision

Replace the monolithic `NotionSync` with a connector framework:

- `BaseConnector` — abstract base class with a template method for the sync lifecycle (authenticate → fetch → enrich → write → save state). Subclasses implement `authenticate()`, `fetch_updates()`, and `_transform_to_wiki_page()`.
- `ConnectorRegistry` — self-registering factory. Each connector module registers itself (`ConnectorRegistry.register("notion", NotionConnector)`), so adding a new connector requires no changes to the wiring code.
- `VaultManager` — loads `config/sources.yaml` (auth) and `config/vaults.yaml` (routing) at startup. Instantiates connectors and WikiManagers, builds the binding list.
- `WikiScheduler` — APScheduler daemon that runs per-binding sync jobs (IntervalTrigger) and per-vault maintenance jobs (CronTrigger).
- `UrlEnricher` — optional post-sync tag enrichment, instantiated once and shared across bindings that opt in.

The original `NotionSync` is retained as a fallback if the YAML configs are absent, preserving backward compatibility.

## Consequences

**Positive:**
- Adding a new source (e.g. GitHub, Linear) requires only one new file in `connectors/` with no changes elsewhere.
- The same source can feed multiple vaults with independent filters (e.g. two Confluence spaces → two vaults).
- Sync state is persisted per connector per vault (`.{connector}.sync_status`), enabling incremental syncs.
- Hub page generation (tag hubs, sprint hubs, epic hubs) is per-connector via `_post_sync_hook()`.
- Enrichment is opt-in per binding, not global.

**Negative:**
- Slightly more indirection at startup (VaultManager → ConnectorRegistry → connector instances).
- Two code paths exist (multi-vault and legacy) until the legacy path is removed.
- YAML config must be maintained alongside `.env` for credentials.
