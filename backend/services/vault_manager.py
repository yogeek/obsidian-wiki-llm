"""
Vault Manager - owns all WikiManager instances and ConnectorBinding list.
Loads from config/sources.yaml and config/vaults.yaml.
"""

import logging
import os
from pathlib import Path
from typing import Dict, List, Optional

import yaml

from .wiki_manager import WikiManager
from .connector_registry import ConnectorRegistry
from .connectors.base_connector import ConnectorBinding, ConnectorFilter, BaseConnector

# Import connectors to trigger self-registration
from .connectors import notion_connector  # noqa: F401
from .connectors import jira_connector  # noqa: F401
from .connectors import confluence_connector  # noqa: F401

logger = logging.getLogger(__name__)


class VaultManager:
    def __init__(self, sources_config: Path, vaults_config: Path):
        self.vaults: Dict[str, WikiManager] = {}
        self.connectors: Dict[str, BaseConnector] = {}
        self.bindings: List[ConnectorBinding] = []
        self._vault_descriptions: Dict[str, str] = {}
        self._load(sources_config, vaults_config)

    def _load(self, sources_config: Path, vaults_config: Path):
        sources_raw = yaml.safe_load(sources_config.read_text()) or {}
        vaults_raw = yaml.safe_load(vaults_config.read_text()) or {}

        # 1. Instantiate connectors from sources.yaml
        for source_name, source_cfg in (sources_raw.get("sources") or {}).items():
            connector_type = source_cfg.get("connector_type", source_name)
            raw_creds = source_cfg.get("credentials", {})
            credentials = self._resolve_credentials(raw_creds)
            try:
                connector = ConnectorRegistry.create(connector_type, credentials)
                self.connectors[source_name] = connector
                logger.info("Connector loaded: %s (type=%s)", source_name, connector_type)
            except Exception as e:
                logger.warning("Could not load connector %s: %s", source_name, e)

        # 2. Instantiate WikiManagers and build bindings from vaults.yaml
        for vault_name, vault_cfg in (vaults_raw.get("vaults") or {}).items():
            vault_path = Path(vault_cfg["path"])
            vault_path.mkdir(parents=True, exist_ok=True)
            wiki_manager = WikiManager(vault_path=vault_path, vault_name=vault_name)
            self.vaults[vault_name] = wiki_manager
            self._vault_descriptions[vault_name] = vault_cfg.get("description", "")
            logger.info("Vault loaded: %s -> %s", vault_name, vault_path)

            for binding_cfg in (vault_cfg.get("sources") or []):
                source_name = binding_cfg["source"]
                if source_name not in self.connectors:
                    logger.warning(
                        "Vault %s references unknown source %s, skipping binding",
                        vault_name,
                        source_name,
                    )
                    continue

                filter_cfg = binding_cfg.get("filter") or {}
                connector_filter = ConnectorFilter(
                    space_keys=filter_cfg.get("space_keys"),
                    labels=filter_cfg.get("labels"),
                    project_key=filter_cfg.get("project_key"),
                    jql=filter_cfg.get("jql"),
                    cql=filter_cfg.get("cql"),
                )
                binding = ConnectorBinding(
                    source_name=source_name,
                    vault_name=vault_name,
                    vault_category=binding_cfg.get("vault_category", "sources"),
                    sync_interval=binding_cfg.get("sync_interval", "6h"),
                    filter=connector_filter,
                    enrich_from_url=binding_cfg.get("enrich_from_url", False),
                    enrich_from_content=binding_cfg.get("enrich_from_content", False),
                )
                self.bindings.append(binding)
                logger.info(
                    "Binding registered: %s -> %s (interval=%s, enrich_url=%s, enrich_content=%s)",
                    source_name,
                    vault_name,
                    binding.sync_interval,
                    binding.enrich_from_url,
                    binding.enrich_from_content,
                )

    @staticmethod
    def _resolve_credentials(raw_creds: Dict) -> Dict[str, str]:
        """Resolve env-var-name references to actual values."""
        resolved = {}
        for key, env_name in raw_creds.items():
            resolved_key = key[:-4] if key.endswith("_env") else key
            resolved[resolved_key] = os.getenv(str(env_name), "")
        return resolved

    def get_all_bindings(self) -> List[ConnectorBinding]:
        return list(self.bindings)

    def get_wiki_manager(self, vault_name: str) -> WikiManager:
        if vault_name not in self.vaults:
            raise KeyError(f"Unknown vault: {vault_name}")
        return self.vaults[vault_name]

    def get_connector(self, source_name: str) -> BaseConnector:
        if source_name not in self.connectors:
            raise KeyError(f"Unknown source: {source_name}")
        return self.connectors[source_name]

    def list_vaults(self) -> List[Dict]:
        result = []
        for vault_name, wiki_manager in self.vaults.items():
            vault_bindings = [b for b in self.bindings if b.vault_name == vault_name]
            sources_status = []
            for binding in vault_bindings:
                connector = self.connectors.get(binding.source_name)
                status = {}
                if connector:
                    try:
                        status = connector.get_sync_status(wiki_manager.vault_path)
                    except Exception:
                        status = {"last_sync": None}
                sources_status.append({
                    "source": binding.source_name,
                    "vault_category": binding.vault_category,
                    "sync_interval": binding.sync_interval,
                    "enrich_from_url": binding.enrich_from_url,
                    "enrich_from_content": binding.enrich_from_content,
                    **status,
                })
            result.append({
                "name": vault_name,
                "path": str(wiki_manager.vault_path),
                "description": self._vault_descriptions.get(vault_name, ""),
                "sources": sources_status,
            })
        return result

    def find_notion_vault(self) -> Optional[str]:
        """Return the first vault name that has a Notion binding (for backward compat)."""
        for binding in self.bindings:
            if binding.source_name == "notion":
                return binding.vault_name
        return None
