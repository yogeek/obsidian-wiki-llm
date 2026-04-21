"""
Connector Registry - maps connector type names to connector classes.
Connectors self-register at module import time.
"""

from typing import Dict, Type, TYPE_CHECKING

if TYPE_CHECKING:
    from .connectors.base_connector import BaseConnector

import logging

logger = logging.getLogger(__name__)


class ConnectorRegistry:
    _registry: Dict[str, Type["BaseConnector"]] = {}

    @classmethod
    def register(cls, name: str, connector_class: Type["BaseConnector"]):
        cls._registry[name] = connector_class
        logger.debug("Registered connector: %s", name)

    @classmethod
    def create(cls, connector_type: str, credentials: Dict[str, str]) -> "BaseConnector":
        if connector_type not in cls._registry:
            raise ValueError(
                f"Unknown connector type: '{connector_type}'. "
                f"Available: {list(cls._registry.keys())}"
            )
        connector_class = cls._registry[connector_type]
        instance = connector_class(credentials)
        instance._name = connector_type
        return instance

    @classmethod
    def available(cls) -> list:
        return list(cls._registry.keys())
