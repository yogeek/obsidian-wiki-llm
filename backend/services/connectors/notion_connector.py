"""
Notion Connector - refactored from NotionSync, implements BaseConnector.
Preserves all existing behavior: French/English field names, multi-tag support, tag hubs.
"""

import logging
import os
from datetime import datetime
from typing import Dict, List, Optional

from .base_connector import (
    BaseConnector,
    ConnectorBinding,
    ConnectorFilter,
    SourceItem,
)
from ..connector_registry import ConnectorRegistry

logger = logging.getLogger(__name__)


class NotionConnector(BaseConnector):
    def __init__(self, credentials: Dict[str, str]):
        super().__init__(credentials)
        self.api_key = credentials.get("api_key", "")
        self.database_id = credentials.get("database_id", "")
        self.client = None

    def authenticate(self) -> bool:
        if not self.api_key or not self.database_id:
            raise ValueError("Notion API key or database ID not configured")
        try:
            from notion_client import Client
            self.client = Client(auth=self.api_key)
            return True
        except ImportError:
            raise RuntimeError("notion-client package is not installed")

    def fetch_updates(
        self,
        since: Optional[datetime],
        filter: ConnectorFilter,
    ) -> List[SourceItem]:
        if not self.client:
            return []
        try:
            items = []
            start_cursor = None
            pages = 0
            while True:
                query_kwargs = {"page_size": 100}
                if start_cursor:
                    query_kwargs["start_cursor"] = start_cursor
                response = self.client.databases.query(
                    self.database_id, **query_kwargs
                )
                pages += 1
                for raw_item in response.get("results", []):
                    try:
                        item = self._raw_to_source_item(raw_item)
                        if item:
                            items.append(item)
                    except Exception as e:
                        logger.error("Error processing Notion item: %s", e)
                if not response.get("has_more"):
                    break
                start_cursor = response.get("next_cursor")
            logger.info(
                "Fetched %d items from Notion (%d API page(s))", len(items), pages
            )
            return items
        except Exception as e:
            logger.error("Error fetching from Notion database: %s", e)
            return []

    def _raw_to_source_item(self, raw_item: Dict) -> Optional[SourceItem]:
        properties = raw_item.get("properties", {})

        title = (
            self._extract_property(properties, "Nom", "title")
            or self._extract_property(properties, "Name", "title")
        )
        if not title:
            return None

        description = self._extract_property(properties, "Description", "rich_text") or ""
        tags = self._extract_tags(properties)
        url = self._extract_property(properties, "URL", "url")
        date_discovered = (
            self._extract_property(properties, "Date", "date")
            or self._extract_property(properties, "Date Discovered", "date")
        )
        status = (
            self._extract_property(properties, "Etat", "select")
            or self._extract_property(properties, "État", "select")
            or self._extract_property(properties, "Status", "select")
        )

        return SourceItem(
            source_id=raw_item.get("id", ""),
            title=title,
            content=description,
            metadata={
                "tags": tags,
                "url": url,
                "date_discovered": date_discovered,
                "status": status,
            },
            fetched_at=datetime.now(),
        )

    def _transform_to_wiki_page(self, item: SourceItem, vault_category: str) -> Dict:
        tags = item.metadata.get("tags", [])
        primary_tag = tags[0] if tags else "uncategorized"
        url = item.metadata.get("url")
        date_discovered = item.metadata.get("date_discovered")
        status = item.metadata.get("status")

        filename = item.title.lower().replace(" ", "-").replace("/", "-")

        tag_links = " ".join(
            [f"[[{t.lower().replace(' ', '-').replace('/', '-')}]]" for t in tags]
        )
        url_section = f"- **URL:** [{url}]({url})" if url else "- **URL:** No URL provided"
        related_tags = "\n".join(
            [f"- See [[{t.lower().replace(' ', '-').replace('/', '-')}]]" for t in tags]
        )

        content = f"""## Summary
{item.content or "No description provided"}

## Tags
{tag_links}

## Key Details
{url_section}
- **Discovered:** {date_discovered or "Unknown"}
- **Status:** {status or "New"}

## Why This Matters
<!-- Add analysis of relevance and potential impact -->

## Related Items by Tag
{related_tags}

## Action Items
- [ ] Evaluate for adoption
- [ ] Research further
- [ ] Prototype integration

## Notes
<!-- Add your observations and insights -->

## Source
Synced from Notion database"""

        return {
            "category": vault_category,
            "filename": filename,
            "frontmatter_data": {
                "type": "technology_watch",
                "category": primary_tag,
                "source_url": url,
                "date_discovered": date_discovered or datetime.now().isoformat(),
                "status": status or "new",
                "notion_sync": True,
                "notion_id": item.source_id,
                "tags": tags,
            },
            "content": content,
        }

    def _post_sync_hook(
        self, wiki_manager, items: List[SourceItem], binding: ConnectorBinding
    ):
        """Create tag hub pages linking all items per tag."""
        tags_index: Dict[str, List[str]] = {}
        for item in items:
            filename = self._slugify(item.title)
            for tag in item.metadata.get("tags", []):
                tags_index.setdefault(tag, []).append(filename)

        for tag, filenames in tags_index.items():
            try:
                self._create_hub_page(
                    wiki_manager, binding.vault_category, tag, filenames,
                    hub_type="technology_watch_hub",
                    description=f"All tech-watch items tagged **{tag}**.",
                )
            except Exception as e:
                logger.error("Error creating tag hub for %s: %s", tag, e)

    def _extract_tags(self, properties: Dict) -> List[str]:
        tags_prop = properties.get("tag") or properties.get("Category")
        if not tags_prop:
            return []
        if "multi_select" in tags_prop:
            return [
                item.get("name")
                for item in tags_prop.get("multi_select", [])
                if item.get("name")
            ]
        if "select" in tags_prop:
            select = tags_prop.get("select", {})
            tag_name = select.get("name")
            return [tag_name] if tag_name else []
        return []

    def _extract_property(
        self, properties: Dict, field_name: str, prop_type: str
    ) -> Optional[str]:
        if field_name not in properties:
            return None
        prop = properties[field_name]

        if prop_type == "title":
            text_list = prop.get("title", [])
            return "".join(t.get("plain_text", "") for t in text_list) if text_list else None
        elif prop_type == "rich_text":
            text_list = prop.get("rich_text", [])
            return "".join(t.get("plain_text", "") for t in text_list) if text_list else None
        elif prop_type == "select":
            select = prop.get("select", {})
            return select.get("name") if select else None
        elif prop_type == "multi_select":
            items = prop.get("multi_select", [])
            return items[0].get("name") if items else None
        elif prop_type == "url":
            return prop.get("url")
        elif prop_type == "date":
            date_obj = prop.get("date", {})
            return date_obj.get("start") if date_obj else None
        return None


ConnectorRegistry.register("notion", NotionConnector)
