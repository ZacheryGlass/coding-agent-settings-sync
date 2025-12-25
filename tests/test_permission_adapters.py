import pytest
import json
from pathlib import Path
from core.canonical_models import CanonicalPermission, ConfigType
from adapters.claude import ClaudeAdapter
from core.registry import FormatRegistry

class TestClaudePermissionAdapter:
    @pytest.fixture
    def adapter(self):
        return ClaudeAdapter()

    def test_supported_config_types(self, adapter):
        assert ConfigType.PERMISSION in adapter.supported_config_types

    def test_can_handle_settings_json(self, adapter):
        assert adapter.can_handle(Path(".claude/settings.json"))
        assert adapter.can_handle(Path("settings.json"))
        # Should still handle agents
        assert adapter.can_handle(Path("my-agent.md"))

    def test_to_canonical_permissions(self, adapter):
        fixture_path = Path("tests/fixtures/claude/permissions/full-settings.json")
        content = fixture_path.read_text()

        perm = adapter.to_canonical(content, ConfigType.PERMISSION)
        
        assert isinstance(perm, CanonicalPermission)
        assert "Bash(ls)" in perm.allow
        assert "Read(.env)" in perm.deny
        assert "Bash(git push)" in perm.ask
        # Verify source format
        assert perm.source_format == "claude"

    def test_from_canonical_permissions(self, adapter):
        perm = CanonicalPermission(
            allow=["Bash(npm test)"],
            deny=["Read(secrets.txt)"],
            ask=[],
            source_format="claude"
        )
        
        content = adapter.from_canonical(perm, ConfigType.PERMISSION)
        data = json.loads(content)
        
        assert "permissions" in data
        assert "allow" in data["permissions"]
        assert "Bash(npm test)" in data["permissions"]["allow"]
        assert "Read(secrets.txt)" in data["permissions"]["deny"]
        # Should not have 'ask' if it's empty, or it can be empty list. 
        # Let's assume we want clean output so maybe omit empty? 
        # But for now, let's just check the present values.

    def test_read_invalid_json(self, adapter):
        fixture_path = Path("tests/fixtures/claude/permissions/invalid.json")
        content = fixture_path.read_text()
        with pytest.raises(ValueError):
            adapter.to_canonical(content, ConfigType.PERMISSION)

    def test_read_missing_permissions_key(self, adapter):
        # Should handle files that are valid JSON but missing permissions key gracefully?
        # Or return empty permissions?
        fixture_path = Path("tests/fixtures/claude/permissions/no-permissions-key.json")
        content = fixture_path.read_text()
        perm = adapter.to_canonical(content, ConfigType.PERMISSION)
        assert isinstance(perm, CanonicalPermission)
        assert perm.allow == []

class TestPermissionRegistry:
    def test_detect_settings_json(self):
        registry = FormatRegistry()
        registry.register(ClaudeAdapter())
        
        adapter = registry.detect_format(Path("settings.json"))
        assert adapter is not None
        assert adapter.format_name == "claude"
        
        adapter = registry.detect_format(Path(".claude/settings.local.json"))
        assert adapter is not None
        assert adapter.format_name == "claude"
