"""
Copilot permission config type handler.

Copilot doesn't have an explicit permission model like Claude,
so this handler provides a way to represent that lack of support
or potentially store/retrieve permissions from metadata.
"""

from typing import Any, Dict, Optional
from core.canonical_models import CanonicalPermission, ConfigType
from adapters.shared.config_type_handler import ConfigTypeHandler


class CopilotPermissionHandler(ConfigTypeHandler):
    """Handler for Copilot permission (mostly placeholder)."""

    @property
    def config_type(self) -> ConfigType:
        return ConfigType.PERMISSION

    def to_canonical(self, content: str) -> CanonicalPermission:
        """Copilot doesn't have permission files, so this shouldn't be called normally."""
        return CanonicalPermission(source_format='copilot')

    def from_canonical(self, canonical_obj: Any,
                      options: Optional[Dict[str, Any]] = None) -> str:
        """
        Copilot doesn't support permissions, so we might want to warn or return empty.
        For now, we'll return a commented-out JSON or similar to show it's unsupported.
        """
        if not isinstance(canonical_obj, CanonicalPermission):
            raise ValueError("Expected CanonicalPermission for PERMISSION config type")
        
        return "# Permissions are not explicitly supported by Copilot format\n"
