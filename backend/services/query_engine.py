"""
Query Engine - Handles querying the wiki and synthesizing answers
Uses the wiki as a persistent knowledge base instead of raw sources
"""

from typing import Dict, List
import logging
import httpx
from anthropic import Anthropic
from pathlib import Path

logger = logging.getLogger(__name__)


class QueryEngine:
    # Models to try in order of cost/capability (cheapest first)
    # Can be overridden via CLAUDE_MODELS env var (comma-separated: "model1,model2,model3")
    DEFAULT_MODELS = [
        "claude-haiku-4-5-20251001",
        "claude-sonnet-4-5-20250929",
        "claude-sonnet-4-6",
        "claude-opus-4-1-20250805",
    ]

    def __init__(self, wiki_manager):
        import os
        self.wiki_manager = wiki_manager
        # Use insecure client for corporate proxy environments
        http_client = httpx.Client(verify=False)
        self.client = Anthropic(http_client=http_client)

        # Load models from env or use defaults
        models_env = os.getenv("CLAUDE_MODELS")
        if models_env:
            self.available_models = [m.strip() for m in models_env.split(",")]
            logger.info(f"Using models from CLAUDE_MODELS: {self.available_models}")
        else:
            self.available_models = self.DEFAULT_MODELS

        self.model = self._get_available_model()

    def _get_available_model(self) -> str:
        """Try to get an available model, return first one that works"""
        for model in self.available_models:
            try:
                # Quick test to see if model is available
                self.client.messages.create(
                    model=model,
                    max_tokens=10,
                    messages=[{"role": "user", "content": "test"}]
                )
                logger.info(f"Using model: {model}")
                return model
            except Exception as e:
                if "not_found" not in str(e).lower():
                    # Some other error, just log and continue
                    logger.debug(f"Model {model} check failed: {e}")

        # Fallback to first in list (will fail with clear error)
        logger.warning(f"No models available, defaulting to {self.available_models[0]}")
        return self.available_models[0]

    def query(self, query: str, max_depth: int = 3, include_sources: bool = True) -> Dict:
        """
        Query the wiki by synthesizing information from wiki pages.
        Uses BFS to follow cross-references up to max_depth.
        """
        logger.info(f"Processing query: {query}")

        # Get relevant pages
        relevant_pages = self._find_relevant_pages(query, max_depth)

        # Compile context from relevant pages
        context = self._compile_context(relevant_pages)

        # Use Claude to synthesize answer
        response = self.client.messages.create(
            model=self.model,
            max_tokens=2000,
            system="""You are answering questions using a personal wiki knowledge base.
Synthesize information from the provided wiki pages to answer the user's question.
Be accurate and cite which pages you're drawing from.
Return your response as JSON:
{
    "answer": "Your synthesized answer",
    "sources": ["page1", "page2"],
    "related_entities": ["entity1", "entity2"],
    "confidence": 0.8
}""",
            messages=[
                {
                    "role": "user",
                    "content": f"""Question: {query}

Wiki context:
{context}

Please synthesize an answer using the provided wiki pages."""
                }
            ]
        )

        # Parse response
        import json
        import re
        try:
            response_text = response.content[0].text
            # Strip markdown code block wrapper if present
            if response_text.startswith("```"):
                response_text = re.sub(r'^```(?:json)?\n', '', response_text)
                response_text = re.sub(r'\n```$', '', response_text)
            result = json.loads(response_text)
        except (json.JSONDecodeError, IndexError) as e:
            logger.error(f"Failed to parse query response: {e}")
            result = {
                "answer": "Could not synthesize an answer from the wiki.",
                "sources": [],
                "related_entities": [],
                "confidence": 0.0
            }

        return result

    def _find_relevant_pages(self, query: str, max_depth: int) -> Dict[str, str]:
        """Find pages relevant to query using BFS"""
        from collections import deque
        import re

        relevant_pages = {}
        visited = set()
        queue = deque()

        # Find pages matching query terms
        query_terms = query.lower().split()
        all_pages = self.wiki_manager.list_pages()

        for page_path in all_pages:
            page = self.wiki_manager.get_page(page_path.parent.name, page_path.stem)
            if not page:
                continue

            # Simple relevance check
            content_lower = (page.content + page.metadata.get("title", "")).lower()
            if any(term in content_lower for term in query_terms):
                relevant_pages[page_path.stem] = page.content
                queue.append((page_path.stem, 0))
                visited.add(page_path.stem)

        # BFS to find related pages
        while queue and len(relevant_pages) < 50:
            current_page, depth = queue.popleft()

            if depth >= max_depth:
                continue

            # Extract links from current page
            page_content = relevant_pages.get(current_page, "")
            links = re.findall(r'\[\[([^\]]+)\]\]', page_content)

            for link in links:
                if link not in visited:
                    visited.add(link)
                    # Try to load linked page
                    for page_path in all_pages:
                        if page_path.stem == link or page_path.stem == link.replace(" ", "-"):
                            page = self.wiki_manager.get_page(
                                page_path.parent.name, page_path.stem
                            )
                            if page:
                                relevant_pages[link] = page.content
                                queue.append((link, depth + 1))

        return relevant_pages

    def _compile_context(self, pages: Dict[str, str]) -> str:
        """Compile relevant pages into context string"""
        context_parts = []
        for page_name, content in list(pages.items())[:20]:  # Limit to 20 pages
            context_parts.append(f"\n## {page_name}\n{content}")
        return "\n".join(context_parts)
