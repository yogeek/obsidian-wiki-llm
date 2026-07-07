"""
Thin wrapper around notion_client for the tag curation scripts. Mirrors
the pagination fix already applied to
backend/services/connectors/notion_connector.py.
"""

import time


def fetch_all_items(client, database_id: str) -> list[dict]:
    """Fetch every item in the database, paginated, shaped for diff.py."""
    items = []
    start_cursor = None
    while True:
        kwargs = {"page_size": 100}
        if start_cursor:
            kwargs["start_cursor"] = start_cursor
        response = client.databases.query(database_id, **kwargs)
        for raw in response.get("results", []):
            props = raw.get("properties", {})
            title_prop = props.get("Nom", {}).get("title") or []
            title = "".join(t["plain_text"] for t in title_prop)
            tags = [t["name"] for t in (props.get("tag", {}).get("multi_select") or [])]
            items.append({"id": raw["id"], "title": title, "tags": tags})
        if not response.get("has_more"):
            break
        start_cursor = response.get("next_cursor")
    return items


def update_page_tags(client, page_id: str, tags: list[str]) -> None:
    """Overwrite the `tag` multi_select property of one page."""
    client.pages.update(
        page_id,
        properties={"tag": {"multi_select": [{"name": t} for t in tags]}},
    )
    time.sleep(0.34)  # ~3 requests/second, well under Notion's rate limit


def set_tag_schema_options(client, database_id: str, option_names: list[str]) -> None:
    """Restrict the `tag` multi_select property's available options.

    Must only be called after every page's tags have already been
    rewritten to use exclusively `option_names` (see plan Task 9) —
    Notion may reject removing options that are still referenced by a
    page.
    """
    client.databases.update(
        database_id,
        properties={
            "tag": {
                "multi_select": {"options": [{"name": n} for n in option_names]}
            }
        },
    )
