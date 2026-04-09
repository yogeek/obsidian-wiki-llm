"""
Wiki Manager - Handles vault structure, page creation, and maintenance
"""

from pathlib import Path
from typing import Dict, List, Optional
import frontmatter
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class WikiManager:
    def __init__(self, vault_path: Path):
        self.vault_path = vault_path
        self._ensure_structure()

    def _ensure_structure(self):
        """Ensure wiki directory structure exists"""
        dirs = [
            "entities",
            "topics",
            "sources",
            "technology_watch",
            "decisions",
            ".obsidian"
        ]
        for dir_name in dirs:
            (self.vault_path / dir_name).mkdir(parents=True, exist_ok=True)

    def create_page(self, category: str, filename: str, frontmatter_data: Dict,
                   content: str) -> Path:
        """Create or update a wiki page"""
        page_path = self.vault_path / category / f"{filename}.md"
        page_path.parent.mkdir(parents=True, exist_ok=True)

        # Ensure required metadata
        frontmatter_data.setdefault("created_date", datetime.now().isoformat())
        frontmatter_data["last_updated"] = datetime.now().isoformat()

        # Write page
        post = frontmatter.Post(content, **frontmatter_data)
        with open(page_path, 'w', encoding='utf-8') as f:
            f.write(frontmatter.dumps(post))

        logger.info(f"Created/updated page: {page_path}")
        return page_path

    def get_page(self, category: str, filename: str) -> Optional[frontmatter.Post]:
        """Retrieve a page's content and metadata"""
        page_path = self.vault_path / category / f"{filename}.md"
        if not page_path.exists():
            return None

        with open(page_path, 'r', encoding='utf-8') as f:
            return frontmatter.load(f)

    def list_pages(self, category: Optional[str] = None) -> List[Path]:
        """List all pages, optionally filtered by category"""
        if category:
            search_path = self.vault_path / category
            if not search_path.exists():
                return []
            return list(search_path.glob("*.md"))
        else:
            return list(self.vault_path.glob("*/*.md"))

    def get_statistics(self) -> Dict:
        """Get wiki statistics"""
        stats = {
            "total_pages": 0,
            "total_entities": 0,
            "total_topics": 0,
            "total_sources": 0,
            "orphaned_pages": 0,
            "stale_pages": 0,
            "last_maintenance": None
        }

        for page in self.list_pages():
            stats["total_pages"] += 1

            post = self.get_page(page.parent.name, page.stem)
            if not post:
                continue

            page_type = post.metadata.get("type", "unknown")
            if page_type == "entity":
                stats["total_entities"] += 1
            elif page_type == "topic":
                stats["total_topics"] += 1
            elif page_type == "source":
                stats["total_sources"] += 1

            # Check if stale (not updated in 30 days)
            if "last_updated" in post.metadata:
                try:
                    last_updated = datetime.fromisoformat(
                        post.metadata["last_updated"]
                    )
                    if (datetime.now() - last_updated).days > 30:
                        stats["stale_pages"] += 1
                except:
                    pass

        return stats

    def find_orphaned_pages(self) -> List[str]:
        """Find pages with no backlinks"""
        orphaned = []
        all_pages = self.list_pages()
        all_links = set()

        # Collect all links
        for page in all_pages:
            content = page.read_text(encoding='utf-8')
            # Simple link extraction: [[link]] and [text](link)
            import re
            wiki_links = re.findall(r'\[\[([^\]]+)\]\]', content)
            md_links = re.findall(r'\[([^\]]+)\]\(([^\)]+)\)', content)
            all_links.update(wiki_links)
            all_links.update(link[1] for link in md_links if link[1].startswith('.'))

        # Find pages not referenced
        for page in all_pages:
            page_stem = page.stem
            if page_stem not in all_links:
                orphaned.append(str(page))

        return orphaned

    def lint(self) -> Dict:
        """Run maintenance checks on the wiki"""
        return {
            "orphaned_pages": self.find_orphaned_pages(),
            "broken_links": self._find_broken_links(),
            "contradictions": [],
            "recommendations": []
        }

    def _find_broken_links(self) -> List[str]:
        """Find broken links in the wiki"""
        broken = []
        all_pages = self.list_pages()

        for page in all_pages:
            content = page.read_text(encoding='utf-8')
            # Find markdown links to local files
            import re
            md_links = re.findall(r'\[([^\]]+)\]\(([^\)]+)\)', content)

            for text, link in md_links:
                if link.startswith('.'):
                    target = (page.parent / link).resolve()
                    if not target.exists():
                        broken.append(f"{page.name}: {link}")

        return broken
