"""
JIRA Connector - implements BaseConnector for JIRA Server / Data Center (PAT auth).

Field mapping (JIRA issue -> wiki frontmatter):
  key                  -> filename (e.g. cdsfgtp-123)
  summary              -> title
  description          -> content body
  status.name          -> status
  issuetype.name       -> issue_type tag
  priority.name        -> priority
  assignee.displayName -> assignee
  labels               -> tags
  components[].name    -> additional tags
  customfield_10020    -> sprint (name extracted from sprint object list)
  customfield_10014    -> epic link key
  created/updated      -> created_date/last_updated

Graph links generated:
  - [[tag-slug]] for each label/component tag (topic hubs)
  - [[sprint-name-slug]] hub linking all issues in the same sprint
  - [[epic-key]] if the issue belongs to an epic
"""

import logging
from datetime import datetime
from typing import Dict, List, Optional

from .base_connector import BaseConnector, ConnectorBinding, ConnectorFilter, SourceItem
from ..connector_registry import ConnectorRegistry

logger = logging.getLogger(__name__)


class JiraConnector(BaseConnector):
    def __init__(self, credentials: Dict[str, str]):
        super().__init__(credentials)
        self.api_key = credentials.get("api_key", "")
        self.base_url = credentials.get("base_url", "")
        self.username = credentials.get("username", "")
        self.client = None

    def authenticate(self) -> bool:
        if not self.api_key or not self.base_url:
            raise ValueError("JIRA credentials not fully configured")
        try:
            from jira import JIRA
            # PAT token auth (JIRA Server / Data Center)
            self.client = JIRA(server=self.base_url, token_auth=self.api_key)
            return True
        except ImportError:
            raise RuntimeError("jira package is not installed (pip install jira)")

    def fetch_updates(
        self,
        since: Optional[datetime],
        filter: ConnectorFilter,
    ) -> List[SourceItem]:
        if not self.client:
            return []
        try:
            jql = filter.jql if filter.jql else self._build_jql(filter, since)
            issues = self.client.search_issues(jql, maxResults=500)
            items = [self._issue_to_source_item(issue) for issue in issues]
            logger.info("Fetched %d issues from JIRA", len(items))
            return items
        except Exception as e:
            logger.error("Error fetching from JIRA: %s", e)
            return []

    def _build_jql(self, filter: ConnectorFilter, since: Optional[datetime]) -> str:
        parts = []
        if filter.project_key:
            parts.append(f"project = {filter.project_key}")
        if since:
            parts.append(f"updated >= '{since.strftime('%Y-%m-%d %H:%M')}'")
        parts.append("ORDER BY updated DESC")
        return " AND ".join(parts[:-1]) + " " + parts[-1] if len(parts) > 1 else parts[-1]

    def _issue_to_source_item(self, issue) -> SourceItem:
        fields = issue.fields
        tags = list(fields.labels or [])
        for component in (fields.components or []):
            if component.name and component.name not in tags:
                tags.append(component.name)

        return SourceItem(
            source_id=issue.key,
            title=fields.summary or issue.key,
            content=fields.description or "",
            metadata={
                "status": fields.status.name if fields.status else None,
                "issue_type": fields.issuetype.name if fields.issuetype else None,
                "priority": fields.priority.name if fields.priority else None,
                "assignee": fields.assignee.displayName if fields.assignee else None,
                "tags": tags,
                "sprint": self._extract_sprint_name(fields),
                "epic": self._extract_epic_key(fields),
                "created": str(fields.created) if fields.created else None,
                "updated": str(fields.updated) if fields.updated else None,
            },
            fetched_at=datetime.now(),
        )

    @staticmethod
    def _extract_sprint_name(fields) -> Optional[str]:
        # Try known field IDs in order (varies by JIRA instance)
        for attr in ("customfield_10020", "customfield_10004"):
            sprint_field = getattr(fields, attr, None)
            if not sprint_field:
                continue
            try:
                sprints = sprint_field if isinstance(sprint_field, list) else [sprint_field]
                last = sprints[-1]
                if isinstance(last, dict):
                    return last.get("name")
                if hasattr(last, "name"):
                    return last.name
                # Parse the Greenhopper string representation: name=Foo,
                raw = str(last)
                for part in raw.split(","):
                    part = part.strip()
                    if part.startswith("name="):
                        return part[5:].split("]")[0].strip()
            except Exception:
                continue
        return None

    @staticmethod
    def _extract_epic_key(fields) -> Optional[str]:
        for attr in ("customfield_10014", "customfield_10008", "customfield_10200", "epic"):
            val = getattr(fields, attr, None)
            if val:
                if isinstance(val, str):
                    return val
                if hasattr(val, "key"):
                    return val.key
        return None

    def _transform_to_wiki_page(self, item: SourceItem, vault_category: str) -> Dict:
        filename = item.source_id.lower()
        tags = item.metadata.get("tags", [])
        status = item.metadata.get("status", "")
        issue_type = item.metadata.get("issue_type", "")
        priority = item.metadata.get("priority", "")
        assignee = item.metadata.get("assignee", "")
        sprint = item.metadata.get("sprint")
        epic = item.metadata.get("epic")

        # Build topic hub links (tag + sprint + epic)
        hub_links: List[str] = [f"[[{self._slugify(t)}]]" for t in tags if t]
        if sprint:
            hub_links.append(f"[[{self._slugify(sprint)}]]")
        if epic:
            hub_links.append(f"[[{epic.lower()}]]")
        topics_section = (
            "## Topics\n" + "  ".join(hub_links) if hub_links else ""
        )

        content = f"""## Summary
{item.content or "No description provided"}

## Details
- **Status:** {status}
- **Type:** {issue_type}
- **Priority:** {priority}
- **Assignee:** {assignee or "Unassigned"}
- **Sprint:** {sprint or "None"}
- **Epic:** {epic or "None"}

{topics_section}

## Notes
<!-- Add your observations -->

## Source
Synced from JIRA ({item.source_id})"""

        return {
            "category": vault_category,
            "filename": filename,
            "frontmatter_data": {
                "type": "jira_ticket",
                "jira_key": item.source_id,
                "status": status,
                "priority": priority,
                "assignee": assignee,
                "sprint": sprint,
                "epic": epic,
                "tags": tags,
                "created_date": item.metadata.get("created"),
                "last_updated": item.metadata.get("updated"),
                "jira_sync": True,
            },
            "content": content,
        }

    def _post_sync_hook(
        self, wiki_manager, items: List[SourceItem], binding: ConnectorBinding
    ):
        """Create tag hub pages and sprint hub pages for graph clustering."""
        tags_index: Dict[str, List[str]] = {}
        sprint_index: Dict[str, List[str]] = {}

        for item in items:
            filename = item.source_id.lower()
            for tag in item.metadata.get("tags", []):
                tags_index.setdefault(tag, []).append(filename)
            sprint = item.metadata.get("sprint")
            if sprint:
                sprint_index.setdefault(sprint, []).append(filename)

        for tag, filenames in tags_index.items():
            try:
                self._create_hub_page(
                    wiki_manager, binding.vault_category, tag, filenames,
                    hub_type="jira_tag_hub",
                    description=f"All JIRA issues tagged **{tag}**.",
                )
            except Exception as e:
                logger.error("Error creating tag hub %s: %s", tag, e)

        for sprint, filenames in sprint_index.items():
            try:
                self._create_hub_page(
                    wiki_manager, binding.vault_category, sprint, filenames,
                    hub_type="jira_sprint_hub",
                    description=f"All JIRA issues in sprint **{sprint}**.",
                )
            except Exception as e:
                logger.error("Error creating sprint hub %s: %s", sprint, e)


ConnectorRegistry.register("jira", JiraConnector)
