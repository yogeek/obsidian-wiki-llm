"""
Confluence Connector - stub implementation.
Returns empty results until credentials are configured and a vault binding is added.

Field mapping (Confluence page -> wiki frontmatter):
  id                    -> source_id
  title                 -> title, filename
  body.storage.value    -> content body (HTML stripped)
  space.key             -> space
  metadata.labels[].name -> tags
  version.when          -> last_updated
  ancestors[].title     -> breadcrumb (for graph cross-links)

Filter implementation: queries by spaceKey and/or label.
For label-based routing, fetches pages with matching label from any space.
"""

import logging
import re
from datetime import datetime
from html.parser import HTMLParser
from typing import Dict, List, Optional

from .base_connector import BaseConnector, ConnectorBinding, ConnectorFilter, SourceItem
from ..connector_registry import ConnectorRegistry

logger = logging.getLogger(__name__)


class _HTMLStripper(HTMLParser):
    def __init__(self):
        super().__init__()
        self._parts: List[str] = []

    def handle_data(self, data):
        self._parts.append(data)

    def get_text(self) -> str:
        return " ".join(self._parts)


def _strip_html(html: str) -> str:
    stripper = _HTMLStripper()
    stripper.feed(html)
    return stripper.get_text()


class ConfluenceConnector(BaseConnector):
    def __init__(self, credentials: Dict[str, str]):
        super().__init__(credentials)
        self.api_key = credentials.get("api_key", "")
        self.base_url = credentials.get("base_url", "")
        self.username = credentials.get("username", "")
        self.client = None

    def authenticate(self) -> bool:
        if not self.api_key or not self.base_url:
            raise ValueError("Confluence credentials not fully configured")
        try:
            from atlassian import Confluence
            # PAT token auth (Confluence Server / Data Center)
            self.client = Confluence(url=self.base_url, token=self.api_key)
            return True
        except ImportError:
            raise RuntimeError("atlassian-python-api package is not installed")

    def fetch_updates(
        self,
        since: Optional[datetime],
        filter: ConnectorFilter,
    ) -> List[SourceItem]:
        if not self.client:
            return []
        try:
            pages = self._fetch_pages(filter)
            items = []
            for page in pages:
                try:
                    item = self._page_to_source_item(page)
                    items.append(item)
                except Exception as e:
                    logger.error("Error processing Confluence page: %s", e)
            logger.info("Fetched %d pages from Confluence", len(items))
            return items
        except Exception as e:
            logger.error("Error fetching from Confluence: %s", e)
            return []

    def _fetch_pages(self, filter: ConnectorFilter) -> List[Dict]:
        # CQL takes full precedence — most expressive, supports ancestor, title, date, etc.
        if filter.cql:
            return self._fetch_by_cql(filter.cql)

        pages = []
        space_keys = filter.space_keys or []
        labels = filter.labels or []

        for space_key in space_keys:
            try:
                result = self.client.get_all_pages_from_space(
                    space_key, start=0, limit=500, expand="body.storage,metadata.labels,ancestors"
                )
                for page in result:
                    if labels:
                        page_labels = [
                            lbl["name"]
                            for lbl in page.get("metadata", {}).get("labels", {}).get("results", [])
                        ]
                        if any(lbl in page_labels for lbl in labels):
                            if page not in pages:
                                pages.append(page)
                    else:
                        pages.append(page)
            except Exception as e:
                logger.error("Error fetching pages from space %s: %s", space_key, e)

        if labels and not space_keys:
            for label in labels:
                try:
                    result = self.client.get_all_pages_by_label(label, start=0, limit=500)
                    for page in result:
                        if page not in pages:
                            pages.append(page)
                except Exception as e:
                    logger.error("Error fetching pages by label %s: %s", label, e)

        return pages

    def _fetch_by_cql(self, cql: str) -> List[Dict]:
        """
        Execute a CQL query, collect page IDs, then fetch each page fully expanded.
        CQL results wrap the page under result["content"] and don't expand body/ancestors/labels,
        so we use it only as an ID list and fetch each page individually.
        """
        page_ids = []
        start = 0
        limit = 50
        while True:
            try:
                result = self.client.cql(cql, start=start, limit=limit)
                batch = result.get("results", [])
                for item in batch:
                    # CQL search results nest the page under "content"
                    content = item.get("content") or item
                    pid = content.get("id")
                    if pid:
                        page_ids.append(pid)
                if len(batch) < limit:
                    break
                start += limit
            except Exception as e:
                logger.error("CQL query failed: %s", e)
                break

        logger.info("CQL '%s' returned %d page IDs, fetching full content...", cql, len(page_ids))
        expand = "body.storage,metadata.labels,ancestors,space,version"
        pages = []
        for pid in page_ids:
            try:
                page = self.client.get_page_by_id(pid, expand=expand)
                if page:
                    pages.append(page)
            except Exception as e:
                logger.error("Could not fetch page %s: %s", pid, e)

        logger.info("Fetched %d full pages via CQL", len(pages))
        return pages

    def _page_to_source_item(self, page: Dict) -> SourceItem:
        body_html = page.get("body", {}).get("storage", {}).get("value", "")
        body_text = _strip_html(body_html)

        labels = [
            lbl["name"]
            for lbl in page.get("metadata", {}).get("labels", {}).get("results", [])
        ]
        ancestors = [anc["title"] for anc in page.get("ancestors", [])]

        return SourceItem(
            source_id=page.get("id", ""),
            title=page.get("title", "Untitled"),
            content=body_text,
            metadata={
                "space": page.get("space", {}).get("key", ""),
                "tags": labels,
                "ancestors": ancestors,
                "last_updated": page.get("version", {}).get("when"),
            },
            fetched_at=datetime.now(),
        )

    def _transform_to_wiki_page(self, item: SourceItem, vault_category: str) -> Dict:
        filename = self._slugify(item.title)
        tags = item.metadata.get("tags", [])
        space = item.metadata.get("space", "")
        ancestors = item.metadata.get("ancestors", [])
        synced_slugs = item.metadata.get("synced_slugs", set())
        last_updated = item.metadata.get("last_updated")

        breadcrumb = " > ".join(ancestors + [item.title]) if ancestors else item.title

        # Ancestor links: only emit [[link]] for ancestors that were also synced
        ancestor_slugs = [self._slugify(a) for a in ancestors]
        ancestor_links = "\n".join(
            f"- [[{slug}]]" for slug in ancestor_slugs if slug in synced_slugs
        ) or "_(root page or ancestors not in vault)_"

        # Topic hub links for each label
        tag_links = "  ".join(f"[[{self._slugify(t)}]]" for t in tags if t)
        topics_section = f"## Topics\n{tag_links}" if tag_links else ""

        content = f"""## Content
{item.content[:5000] if item.content else "No content available"}

## Context
- **Space:** {space}
- **Breadcrumb:** {breadcrumb}

## Parent Pages
{ancestor_links}

{topics_section}

## Notes
<!-- Add your observations -->

## Source
Synced from Confluence ({item.source_id})"""

        return {
            "category": vault_category,
            "filename": filename,
            "frontmatter_data": {
                "type": "confluence_page",
                "confluence_id": item.source_id,
                "space": space,
                "tags": tags,
                "last_updated": last_updated,
                "confluence_sync": True,
            },
            "content": content,
        }

    def _post_sync_hook(
        self, wiki_manager, items: List[SourceItem], binding: ConnectorBinding
    ):
        """Create label hub pages for graph clustering, then re-transform with synced slug set."""
        # Build the set of all slugs that were actually synced
        synced_slugs = {self._slugify(item.title) for item in items}

        # Inject synced_slugs into metadata so _transform_to_wiki_page can filter ancestor links.
        # Re-write pages that have ancestors now that we know what's in the vault.
        for item in items:
            if item.metadata.get("ancestors"):
                item.metadata["synced_slugs"] = synced_slugs
                try:
                    page_dict = self._transform_to_wiki_page(item, binding.vault_category)
                    wiki_manager.create_page(**page_dict)
                except Exception as e:
                    logger.error("Error re-writing page with ancestor links %s: %s", item.source_id, e)

        # Label hub pages
        tags_index: Dict[str, List[str]] = {}
        for item in items:
            filename = self._slugify(item.title)
            for tag in item.metadata.get("tags", []):
                tags_index.setdefault(tag, []).append(filename)

        for tag, filenames in tags_index.items():
            try:
                self._create_hub_page(
                    wiki_manager, binding.vault_category, tag, filenames,
                    hub_type="confluence_label_hub",
                    description=f"All Confluence pages labelled **{tag}**.",
                )
            except Exception as e:
                logger.error("Error creating label hub %s: %s", tag, e)


ConnectorRegistry.register("confluence", ConfluenceConnector)
