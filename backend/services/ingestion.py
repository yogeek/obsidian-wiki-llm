"""
Ingestion Service - Processes raw sources and updates wiki
Implements Karpathy's approach: read source, update wiki pages, create cross-references
"""

from typing import Dict
import logging
import httpx
from anthropic import Anthropic

logger = logging.getLogger(__name__)


class IngestionService:
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

    def ingest(self, source_name: str, content: str, source_url: str = None) -> Dict:
        """
        Ingest a source and update wiki pages.
        The LLM reads the source and updates 10-15 wiki pages in a single pass.
        """
        logger.info(f"Starting ingestion of source: {source_name}")

        # Use Claude to analyze source and determine wiki updates
        response = self.client.messages.create(
            model=self.model,
            max_tokens=8000,
            system="""You are a wiki ingestion system. Analyze the provided source material and return a JSON object with the following structure:

{
    "pages": [
        {
            "category": "entities|topics|sources|decisions",
            "filename": "kebab-case-name",
            "title": "Page Title",
            "frontmatter": {
                "type": "entity|topic|source|decision",
                "tags": ["tag1", "tag2"],
                "status": "published|draft",
                "related_entities": [],
                "confidence_level": "high|medium|low"
            },
            "content": "Markdown content for the page"
        }
    ],
    "cross_references": [
        {"from": "page1", "to": "page2", "relationship": "describes"}
    ],
    "contradictions": [],
    "summary": "Brief summary of what was ingested"
}

Create or update 10-15 pages maximum. Focus on entities, key concepts, and important relationships.
For each page, include relevant cross-references to other wiki pages.""",
            messages=[
                {
                    "role": "user",
                    "content": f"""Ingest this source material into the wiki:

Source: {source_name}
URL: {source_url or "N/A"}

Content:
{content}

Return the JSON response with wiki updates."""
                }
            ]
        )

        # Parse response and create pages
        import json
        import re
        try:
            response_text = response.content[0].text
            logger.debug(f"Response length: {len(response_text)} chars")

            # Strip markdown code block wrapper if present
            if response_text.startswith("```"):
                response_text = re.sub(r'^```(?:json)?\n', '', response_text)
                response_text = re.sub(r'\n```$', '', response_text)

            result = json.loads(response_text)
        except (json.JSONDecodeError, IndexError) as e:
            logger.error(f"Failed to parse Claude response: {e}")
            logger.error(f"Response length: {len(response.content[0].text) if response.content else 0} chars")
            logger.error(f"First 500 chars: {response.content[0].text[:500] if response.content else 'EMPTY'}")
            logger.error(f"Last 500 chars: {response.content[0].text[-500:] if response.content else 'EMPTY'}")
            return {
                "pages_created": 0,
                "pages_updated": 0,
                "summary": f"Error parsing ingestion response: {e}"
            }

        pages_created = 0
        pages_updated = 0

        # Create/update pages
        for page in result.get("pages", []):
            try:
                self.wiki_manager.create_page(
                    category=page["category"],
                    filename=page["filename"],
                    frontmatter_data={
                        **page["frontmatter"],
                        "source": source_url or source_name
                    },
                    content=page["content"]
                )
                pages_created += 1
            except Exception as e:
                logger.error(f"Error creating page {page['filename']}: {e}")

        return {
            "pages_created": pages_created,
            "pages_updated": pages_updated,
            "summary": result.get("summary", "Ingestion completed"),
            "contradictions": result.get("contradictions", [])
        }
