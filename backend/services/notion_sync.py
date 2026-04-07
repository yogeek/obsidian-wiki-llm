"""
Notion Sync Service - Synchronizes Notion database items to wiki
Bridges Notion technology watch database to Obsidian vault
"""

from typing import Dict, Optional
import logging
from pathlib import Path
from datetime import datetime, timedelta
import os

logger = logging.getLogger(__name__)


class NotionSync:
    def __init__(self, wiki_manager):
        self.wiki_manager = wiki_manager
        self.api_key = os.getenv("NOTION_API_KEY")
        self.database_id = os.getenv("NOTION_DATABASE_ID")
        self.sync_status_file = Path("/app/config/.notion_sync_status")

        if not self.api_key or not self.database_id:
            logger.warning("Notion API key or database ID not configured")
            self.client = None
        else:
            try:
                from notion_client import Client
                self.client = Client(auth=self.api_key)
            except ImportError:
                logger.error("notion-client not installed")
                self.client = None

    def sync_to_wiki(self) -> Dict:
        """Sync items from Notion database to wiki"""
        if not self.client:
            return {
                "synced": 0,
                "updated": 0,
                "summary": "Notion client not configured"
            }

        try:
            items = self._fetch_notion_items()
            synced_count = 0
            updated_count = 0

            for item in items:
                try:
                    if self._sync_item_to_wiki(item):
                        synced_count += 1
                    else:
                        updated_count += 1
                except Exception as e:
                    logger.error(f"Error syncing item: {e}")

            self._update_sync_status("success", synced_count + updated_count)

            return {
                "synced": synced_count,
                "updated": updated_count,
                "summary": f"Synced {synced_count} new items, updated {updated_count} existing items"
            }

        except Exception as e:
            logger.error(f"Error during Notion sync: {e}")
            self._update_sync_status("error", 0)
            return {
                "synced": 0,
                "updated": 0,
                "summary": f"Error during sync: {e}"
            }

    def _fetch_notion_items(self) -> list:
        """Fetch items from Notion database"""
        try:
            response = self.client.databases.query(self.database_id)
            return response.get("results", [])
        except Exception as e:
            logger.error(f"Error fetching from Notion: {e}")
            return []

    def _sync_item_to_wiki(self, item: Dict) -> bool:
        """Sync a single Notion item to wiki. Returns True if created, False if updated"""
        properties = item.get("properties", {})

        # Extract properties (field mapping configurable in wiki_schema.yaml)
        title = self._extract_property(properties, "Name", "title")
        description = self._extract_property(properties, "Description", "rich_text")
        category = self._extract_property(properties, "Category", "select")
        url = self._extract_property(properties, "URL", "url")
        date_discovered = self._extract_property(properties, "Date Discovered", "date")
        status = self._extract_property(properties, "Status", "select")

        if not title:
            logger.warning(f"Skipping Notion item without title: {item}")
            return False

        # Convert title to filename
        filename = title.lower().replace(" ", "-").replace("/", "-")

        # Check if page already exists
        existing = self.wiki_manager.get_page("technology_watch", filename)
        is_new = existing is None

        # Prepare frontmatter
        frontmatter_data = {
            "type": "technology_watch",
            "category": category or "uncategorized",
            "source_url": url,
            "date_discovered": date_discovered or datetime.now().isoformat(),
            "status": status or "new",
            "notion_sync": True,
            "notion_id": item.get("id", ""),
            "tags": [category] if category else []
        }

        # Prepare content
        content = f"""## Summary
{description or "No description provided"}

## Category
`{category or "uncategorized"}`

## Key Details
- **URL:** [{url}]({url}) if url else "No URL"
- **Discovered:** {date_discovered or "Unknown"}
- **Status:** {status or "New"}

## Why This Matters
<!-- Add analysis of relevance and potential impact -->

## Related Technologies/Entities
<!-- Add related pages using [[]] links -->

## Action Items
- [ ] Evaluate for adoption
- [ ] Research further
- [ ] Prototype integration

## Notes
<!-- Add your observations and insights -->

## Source
Synced from Notion database"""

        # Create/update page
        try:
            self.wiki_manager.create_page(
                category="technology_watch",
                filename=filename,
                frontmatter_data=frontmatter_data,
                content=content
            )
            return is_new
        except Exception as e:
            logger.error(f"Error creating wiki page for Notion item: {e}")
            raise

    def _extract_property(self, properties: Dict, field_name: str, prop_type: str) -> Optional[str]:
        """Extract a property value from Notion properties"""
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
        elif prop_type == "url":
            return prop.get("url")
        elif prop_type == "date":
            date_obj = prop.get("date", {})
            return date_obj.get("start") if date_obj else None

        return None

    def _update_sync_status(self, status: str, count: int):
        """Update sync status file"""
        try:
            self.sync_status_file.parent.mkdir(parents=True, exist_ok=True)
            self.sync_status_file.write_text(
                f"{status}|{datetime.now().isoformat()}|{count}"
            )
        except Exception as e:
            logger.error(f"Error updating sync status: {e}")

    def get_sync_status(self) -> Dict:
        """Get last sync status"""
        if not self.sync_status_file.exists():
            return {
                "status": "never",
                "last_sync": None,
                "item_count": 0
            }

        try:
            content = self.sync_status_file.read_text()
            status, timestamp, count = content.split("|")
            return {
                "status": status,
                "last_sync": timestamp,
                "item_count": int(count)
            }
        except Exception as e:
            logger.error(f"Error reading sync status: {e}")
            return {"status": "error", "last_sync": None, "item_count": 0}
