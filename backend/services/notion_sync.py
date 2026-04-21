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
                "summary": "Notion client not configured",
            }

        try:
            items = self._fetch_notion_items()
            synced_count = 0
            updated_count = 0
            tag_items = {}  # Track items by tag for creating hub pages

            # First pass: sync all items and collect tags
            for item in items:
                try:
                    properties = item.get("properties", {})

                    # Get title first
                    title = self._extract_property(
                        properties, "Nom", "title"
                    ) or self._extract_property(properties, "Name", "title")
                    if not title:
                        continue

                    # Get all tags (multi-tag support)
                    tags = self._extract_tags(properties)

                    if self._sync_item_to_wiki(item):
                        synced_count += 1
                    else:
                        updated_count += 1

                    # Collect items by tag
                    filename = title.lower().replace(" ", "-").replace("/", "-")
                    for tag in tags:
                        if tag not in tag_items:
                            tag_items[tag] = []
                        tag_items[tag].append(filename)
                except Exception as e:
                    logger.error(f"Error syncing item: {e}")

            # Second pass: create tag hub pages and link items
            for tag, item_filenames in tag_items.items():
                try:
                    self._create_tag_hub(tag, item_filenames)
                except Exception as e:
                    logger.error(f"Error creating tag hub for {tag}: {e}")

            self._update_sync_status("success", synced_count + updated_count)

            return {
                "synced": synced_count,
                "updated": updated_count,
                "summary": f"Synced {synced_count} new items, updated {updated_count} existing items",
            }

        except Exception as e:
            logger.error(f"Error during Notion sync: {e}")
            self._update_sync_status("error", 0)
            return {"synced": 0, "updated": 0, "summary": f"Error during sync: {e}"}

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

        # Extract properties (field mapping - supports both English and French property names)
        title = self._extract_property(
            properties, "Nom", "title"
        ) or self._extract_property(properties, "Name", "title")
        description = self._extract_property(properties, "Description", "rich_text")
        tags = self._extract_tags(properties)
        primary_tag = tags[0] if tags else "uncategorized"
        url = self._extract_property(properties, "URL", "url")
        date_discovered = self._extract_property(
            properties, "Date", "date"
        ) or self._extract_property(properties, "Date Discovered", "date")
        status = self._extract_property(
            properties, "État", "select"
        ) or self._extract_property(properties, "Status", "select")

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
            "category": primary_tag,
            "source_url": url,
            "date_discovered": date_discovered or datetime.now().isoformat(),
            "status": status or "new",
            "notion_sync": True,
            "notion_id": item.get("id", ""),
            "tags": tags if tags else [],
        }

        # Prepare content with links to all tag hubs
        tag_links = " ".join(
            [f"[[{tag.lower().replace(' ', '-').replace('/', '-')}]]" for tag in tags]
        )
        url_section = (
            f"- **URL:** [{url}]({url})" if url else "- **URL:** No URL provided"
        )

        # Build related items section with links to all tags
        related_tags = "\n".join(
            [
                f"- See [[{tag.lower().replace(' ', '-').replace('/', '-')}]]"
                for tag in tags
            ]
        )

        content = f"""## Summary
{description or "No description provided"}

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

        # Create/update page
        try:
            self.wiki_manager.create_page(
                category="technology_watch",
                filename=filename,
                frontmatter_data=frontmatter_data,
                content=content,
            )
            return is_new
        except Exception as e:
            logger.error(f"Error creating wiki page for Notion item: {e}")
            raise

    def _extract_tags(self, properties: Dict) -> list:
        """Extract all tags from Notion item (supports multi_select)"""
        # Try French property name first, then English
        tags_prop = properties.get("tag") or properties.get("Category")

        if not tags_prop:
            return []

        # Handle multi_select (list of tags)
        if "multi_select" in tags_prop:
            items = tags_prop.get("multi_select", [])
            return [item.get("name") for item in items if item.get("name")]

        # Handle select (single tag)
        if "select" in tags_prop:
            select = tags_prop.get("select", {})
            tag_name = select.get("name")
            return [tag_name] if tag_name else []

        return []

    def _extract_property(
        self, properties: Dict, field_name: str, prop_type: str
    ) -> Optional[str]:
        """Extract a property value from Notion properties"""
        if field_name not in properties:
            return None

        prop = properties[field_name]

        if prop_type == "title":
            text_list = prop.get("title", [])
            return (
                "".join(t.get("plain_text", "") for t in text_list)
                if text_list
                else None
            )
        elif prop_type == "rich_text":
            text_list = prop.get("rich_text", [])
            return (
                "".join(t.get("plain_text", "") for t in text_list)
                if text_list
                else None
            )
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

    def _create_tag_hub(self, tag: str, item_filenames: list):
        """Create a hub page for a tag that lists all items with this tag"""
        tag_filename = tag.lower().replace(" ", "-").replace("/", "-")

        # Check if hub already exists
        existing = self.wiki_manager.get_page("technology_watch", tag_filename)
        is_new = existing is None

        # Build items list with internal links
        items_list = "\n".join(
            [f"- [[{filename}]]" for filename in sorted(set(item_filenames))]
        )

        content = f"""# {tag}

Hub for all items tagged as **{tag}**.

## Items in this category

{items_list}

---

_This is an auto-generated hub page linking all items synced from Notion with the "{tag}" tag._
"""

        frontmatter_data = {
            "type": "technology_watch_hub",
            "tag": tag,
            "tags": [tag.lower()],
            "notion_sync": True,
            "created_date": datetime.now().isoformat() if is_new else None,
        }

        try:
            self.wiki_manager.create_page(
                category="technology_watch",
                filename=tag_filename,
                frontmatter_data=frontmatter_data,
                content=content,
            )
            logger.info(
                f"Created tag hub for {tag} with {len(set(item_filenames))} items"
            )
        except Exception as e:
            logger.error(f"Error creating tag hub for {tag}: {e}")

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
            return {"status": "never", "last_sync": None, "item_count": 0}

        try:
            content = self.sync_status_file.read_text()
            status, timestamp, count = content.split("|")
            return {"status": status, "last_sync": timestamp, "item_count": int(count)}
        except Exception as e:
            logger.error(f"Error reading sync status: {e}")
            return {"status": "error", "last_sync": None, "item_count": 0}
