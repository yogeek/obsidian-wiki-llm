# ADR 002: Graphify Knowledge Graph Integration

**Status**: Partially accepted (dev tooling only, not wired into sync pipeline)
**Date**: 2026-04-21

## Context

Graphify (https://graphify.net, package `graphifyy`) is an open-source MIT-licensed CLI tool that builds a knowledge graph from any folder of markdown, code, PDFs, and images. It outputs: interactive HTML, JSON graph, markdown wiki (`index.md` + community articles), Obsidian vault export, Neo4j Cypher, and GraphML.

The key integration point with Claude Code is a `PreToolUse` hook in `.claude/settings.json` that feeds Claude a `GRAPH_REPORT.md` (god nodes, communities, surprising connections) before every Glob/Grep call. This causes Claude to navigate by structure rather than raw file search.

Claimed token savings: 6.8x to 49x depending on task complexity.

## Decision

**Adopt for dev tooling. Do not wire into the sync pipeline.**

Concretely:
1. Install graphify (`pip install graphifyy`) locally (not in Docker containers).
2. Run `graphify install` to add the `PreToolUse` hook to `.claude/settings.json` — Claude Code will read `GRAPH_REPORT.md` before searching vault files.
3. Run `graphify ./vaults/tech-watch --wiki` manually after significant sync runs to regenerate `GRAPH_REPORT.md`.
4. Do NOT add graphify as a post-sync step in `scheduler.py` at this time.

## Rationale

**Why adopt it at all:**
- Free, MIT-licensed, no infrastructure cost.
- Aligns with the no-vector RAG philosophy (no embeddings, structural navigation).
- Native Obsidian export and markdown wiki output fit the existing vault format.
- Privacy-first: raw markdown never leaves the machine.
- Token savings are real when Claude navigates a large vault (>200 pages).

**Why not wire into sync pipeline:**
- Graphify has no REST/GraphQL API — only a CLI. Calling it as a subprocess after every sync adds latency and error surface with limited benefit at current vault scale (~100-200 pages).
- The semantic analysis pass (unstructured docs → Claude tags) would consume additional API tokens on every sync, duplicating work already done by `UrlEnricher`.
- The vault is already navigable via `[[wiki-links]]` and the BFS query engine. Graphify adds structural insight for Claude Code sessions, not for end-user queries.
- Graph becomes stale between syncs regardless; on-demand regeneration is sufficient.

**Revisit when:**
- Vault grows beyond 500 pages and BFS query performance degrades.
- A use case emerges for Neo4j-backed queries across multiple vaults.
- Graphify exposes a Python API (removing the subprocess requirement).

## Consequences

**Positive:**
- Claude Code sessions querying or maintaining the vault get structure-first context with no extra infra.
- Zero cost to existing sync pipeline reliability.
- Can be adopted incrementally (run graphify manually when useful).

**Negative:**
- Graph must be regenerated manually; it is not kept current automatically.
- Not useful for end-user `/query` endpoint (that path already uses BFS + Claude).
- Requires local Python install of graphifyy outside Docker.
