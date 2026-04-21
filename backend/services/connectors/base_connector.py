"""
Base Connector - abstract interface all connectors must implement.
Provides the sync() template method and shared state management.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
import json
import logging

logger = logging.getLogger(__name__)


@dataclass
class ConnectorFilter:
    space_keys: Optional[List[str]] = None
    labels: Optional[List[str]] = None
    project_key: Optional[str] = None
    jql: Optional[str] = None
    cql: Optional[str] = None


@dataclass
class SourceItem:
    source_id: str
    title: str
    content: str
    metadata: Dict
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

    def to_dict(self) -> Dict:
        return {
            "source_name": self.source_name,
            "vault_name": self.vault_name,
            "items_fetched": self.items_fetched,
            "items_synced": self.items_synced,
            "items_updated": self.items_updated,
            "errors": self.errors,
            "synced_at": self.synced_at.isoformat(),
        }


@dataclass
class ConnectorBinding:
    source_name: str
    vault_name: str
    vault_category: str
    sync_interval: str
    filter: ConnectorFilter
    enrich_from_url: bool = False
    enrich_from_content: bool = False


class BaseConnector(ABC):
    _name: str = "unknown"

    def __init__(self, credentials: Dict[str, str]):
        self.credentials = credentials

    @abstractmethod
    def authenticate(self) -> bool:
        """Verify credentials and connectivity. Raise on failure."""

    @abstractmethod
    def fetch_updates(
        self,
        since: Optional[datetime],
        filter: ConnectorFilter,
    ) -> List[SourceItem]:
        """
        Fetch new/updated items from the source.
        - since=None means full initial sync.
        - Apply filter server-side when the API supports it, else client-side.
        """

    @abstractmethod
    def _transform_to_wiki_page(self, item: SourceItem, vault_category: str) -> Dict:
        """
        Convert a SourceItem to a wiki page dict with keys:
            category, filename, frontmatter_data, content
        """

    def sync(
        self,
        wiki_manager,
        binding: ConnectorBinding,
        enricher=None,
    ) -> SyncResult:
        """
        Template method: authenticate -> fetch -> transform -> [enrich] -> write -> save state.
        Subclasses should not override this; override _post_sync_hook for extras.
        """
        result = SyncResult(
            source_name=binding.source_name, vault_name=binding.vault_name
        )
        try:
            self.authenticate()
            last_sync = self._load_last_sync_time(wiki_manager.vault_path)
            items = self.fetch_updates(since=last_sync, filter=binding.filter)
            result.items_fetched = len(items)

            for item in items:
                try:
                    page_dict = self._transform_to_wiki_page(
                        item, binding.vault_category
                    )
                    existing = wiki_manager.get_page(
                        page_dict["category"], page_dict["filename"]
                    )
                    is_new = existing is None

                    if enricher is not None:
                        existing_tags = page_dict.get("frontmatter_data", {}).get(
                            "tags", []
                        )
                        if binding.enrich_from_url:
                            page_dict = enricher.enrich(page_dict, existing_tags)
                        if binding.enrich_from_content:
                            already_tagged = existing is not None and existing.get(
                                "content_tagged"
                            )
                            if not already_tagged and item.content:
                                current_tags = page_dict.get(
                                    "frontmatter_data", {}
                                ).get("tags", [])
                                new_tags = enricher.tag_from_content(
                                    item.content, current_tags
                                )
                                page_dict = dict(page_dict)
                                page_dict["frontmatter_data"] = dict(
                                    page_dict.get("frontmatter_data", {})
                                )
                                page_dict["frontmatter_data"]["tags"] = new_tags
                                page_dict["frontmatter_data"]["content_tagged"] = True
                                # Update item metadata so _post_sync_hook sees enriched tags
                                item.metadata["tags"] = new_tags

                    wiki_manager.create_page(**page_dict)

                    if is_new:
                        result.items_synced += 1
                    else:
                        result.items_updated += 1

                except Exception as e:
                    logger.error("Error syncing item %s: %s", item.source_id, e)
                    result.errors.append(f"{item.source_id}: {e}")

            self._post_sync_hook(wiki_manager, items, binding)
            self._save_last_sync_time(wiki_manager.vault_path)

        except Exception as e:
            logger.error(
                "Sync failed for %s -> %s: %s",
                binding.source_name,
                binding.vault_name,
                e,
            )
            result.errors.append(str(e))

        return result

    def _post_sync_hook(
        self, wiki_manager, items: List[SourceItem], binding: ConnectorBinding
    ):
        """Override in subclasses for post-sync actions (tag hubs, digests, etc.)."""

    @staticmethod
    def _slugify(text: str) -> str:
        """Convert text to a safe filename slug."""
        import re

        return re.sub(r"[^\w\-]", "-", text.lower()).strip("-")

    def _create_hub_page(
        self,
        wiki_manager,
        category: str,
        hub_name: str,
        item_filenames: List[str],
        hub_type: str = "hub",
        description: str = "",
    ):
        """Create or update a hub page that links all items sharing a common attribute."""
        slug = self._slugify(hub_name)
        items_list = "\n".join(f"- [[{f}]]" for f in sorted(set(item_filenames)))
        desc_line = f"\n{description}\n" if description else ""
        content = f"""# {hub_name}
{desc_line}
## Items

{items_list}

---
_Auto-generated hub. All items linked to **{hub_name}**._
"""
        wiki_manager.create_page(
            category=category,
            filename=slug,
            frontmatter_data={
                "type": hub_type,
                "hub_name": hub_name,
                "tags": [hub_name.lower()],
                "auto_generated": True,
            },
            content=content,
        )
        logger.info("Hub updated: %s (%d items)", hub_name, len(set(item_filenames)))

    def _status_file_path(self, vault_path: Path) -> Path:
        return vault_path / f".{self._name}.sync_status"

    def _load_last_sync_time(self, vault_path: Path) -> Optional[datetime]:
        path = self._status_file_path(vault_path)
        if not path.exists():
            return None
        try:
            data = json.loads(path.read_text())
            ts = data.get("last_sync")
            return datetime.fromisoformat(ts) if ts else None
        except Exception as e:
            logger.warning("Could not read sync status from %s: %s", path, e)
            return None

    def _save_last_sync_time(self, vault_path: Path):
        path = self._status_file_path(vault_path)
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps({"last_sync": datetime.now().isoformat()}))
        except Exception as e:
            logger.warning("Could not save sync status to %s: %s", path, e)

    def get_sync_status(self, vault_path: Path) -> Dict:
        ts = self._load_last_sync_time(vault_path)
        return {"last_sync": ts.isoformat() if ts else None}
