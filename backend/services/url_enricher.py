"""
URL Enricher - fetches URL content and uses Claude to suggest tags.
Idempotent: skips items already marked content_fetched: true in frontmatter.
Only instantiated when at least one binding has enrich_from_url: true.
"""

import logging
from html.parser import HTMLParser
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

_FETCH_TIMEOUT = 10
_MAX_CONTENT_CHARS = 12000  # ~3000 tokens


class _HTMLStripper(HTMLParser):
    def __init__(self):
        super().__init__()
        self._parts: List[str] = []
        self._skip = False

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style", "nav", "footer", "header"):
            self._skip = True

    def handle_endtag(self, tag):
        if tag in ("script", "style", "nav", "footer", "header"):
            self._skip = False

    def handle_data(self, data):
        if not self._skip and data.strip():
            self._parts.append(data.strip())

    def get_text(self) -> str:
        return " ".join(self._parts)


def _strip_html(html: str) -> str:
    stripper = _HTMLStripper()
    stripper.feed(html)
    return stripper.get_text()


class UrlEnricher:
    def __init__(self, anthropic_client):
        self.client = anthropic_client

    def enrich(self, page_dict: Dict, existing_tags: List[str]) -> Dict:
        """
        Idempotent enrichment. If content_fetched is already true, returns unchanged.
        Otherwise: fetch URL -> deduce tags -> merge -> mark content_fetched.
        """
        frontmatter = page_dict.get("frontmatter_data", {})

        if frontmatter.get("content_fetched"):
            return page_dict

        url = frontmatter.get("source_url")
        if not url:
            return page_dict

        text = self._fetch_url(url)
        if not text:
            logger.warning("Could not fetch URL content: %s", url)
            return page_dict

        suggested_tags = self._deduce_tags(text)
        merged_tags = self._merge_tags(existing_tags, suggested_tags)

        page_dict = dict(page_dict)
        page_dict["frontmatter_data"] = dict(frontmatter)
        page_dict["frontmatter_data"]["tags"] = merged_tags
        page_dict["frontmatter_data"]["content_fetched"] = True

        summary = text[:500].replace("\n", " ").strip()
        page_dict["content"] = (
            page_dict.get("content", "")
            + f"\n\n## Content Summary\n{summary}..."
        )

        logger.info(
            "Enriched URL %s: added tags %s (merged with %s)",
            url, suggested_tags, existing_tags,
        )
        return page_dict

    def _fetch_url(self, url: str) -> Optional[str]:
        try:
            import httpx
            response = httpx.get(
                url,
                timeout=_FETCH_TIMEOUT,
                follow_redirects=True,
                headers={"User-Agent": "Mozilla/5.0 (wiki-enricher/1.0)"},
            )
            content_type = response.headers.get("content-type", "")
            if "text" not in content_type and "html" not in content_type:
                logger.debug("Skipping non-text content-type: %s for %s", content_type, url)
                return None
            text = _strip_html(response.text)
            return text[:_MAX_CONTENT_CHARS] if text else None
        except Exception as e:
            logger.warning("Failed to fetch URL %s: %s", url, e)
            return None

    def tag_from_content(self, content: str, existing_tags: List[str]) -> List[str]:
        """
        Deduce tags from item content (JIRA description, Confluence body, etc.)
        and merge with existing tags. Idempotency is handled by the caller via
        the content_tagged frontmatter flag.
        """
        suggested = self._deduce_tags(content)
        merged = self._merge_tags(existing_tags, suggested)
        logger.info(
            "Content tagging: existing=%s suggested=%s merged=%s",
            existing_tags, suggested, merged,
        )
        return merged

    def _deduce_tags(self, content: str) -> List[str]:
        try:
            response = self.client.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=150,
                messages=[
                    {
                        "role": "user",
                        "content": (
                            "Given the following content, suggest 3 to 7 concise, lowercase tags "
                            "that best describe the topic. Return only the tags as a comma-separated "
                            "list, no explanation, no numbering.\n\n"
                            f"Content:\n{content[:3000]}"
                        ),
                    }
                ],
            )
            raw = response.content[0].text.strip()
            tags = [t.strip().lower() for t in raw.split(",") if t.strip()]
            return tags[:7]
        except Exception as e:
            logger.error("Claude tag deduction failed: %s", e)
            return []

    @staticmethod
    def _merge_tags(existing: List[str], suggested: List[str]) -> List[str]:
        """Union merge: existing tags first (order-preserving), then new suggested tags."""
        seen = set()
        merged = []
        for tag in existing + suggested:
            if tag and tag not in seen:
                seen.add(tag)
                merged.append(tag)
        return merged
