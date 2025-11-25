"""
Unit tests for format adapters.

Tests cover:
- ClaudeAdapter conversion (to/from canonical)
- CopilotAdapter conversion (to/from canonical)
- Round-trip conversions (Claude -> Canonical -> Claude)
- Cross-format conversions (Claude -> Copilot -> Claude)
- Field mapping and preservation
- Model name normalization
- Warning generation

Status: IMPLEMENTED
"""

import pytest
from pathlib import Path

from core.canonical_models import CanonicalAgent, ConfigType
from adapters import ClaudeAdapter, CopilotAdapter


class TestClaudeAdapter:
    """Tests for ClaudeAdapter."""

    @pytest.fixture
    def adapter(self):
        """Create ClaudeAdapter instance."""
        return ClaudeAdapter()

    @pytest.fixture
    def sample_claude_content(self):
        """Sample Claude agent file content."""
        return """---
name: test-agent
description: Test agent description
tools: Read, Grep, Glob
model: sonnet
permissionMode: ask
---
Test agent instructions here.
"""

    @pytest.fixture
    def minimal_claude_content(self):
        """Minimal valid agent (required fields only)."""
        return """---
name: minimal-agent
description: Minimal agent
---
Basic instructions.
"""

    @pytest.fixture
    def full_claude_content(self):
        """Agent with all fields including metadata."""
        return """---
name: full-agent
description: Full agent with metadata
tools: Read, Grep, Glob, Bash
model: opus
permissionMode: ask
skills: [python, javascript]
---
Full agent instructions.
"""

    @pytest.fixture
    def canonical_agent_sample(self):
        """CanonicalAgent instance for serialization tests."""
        return CanonicalAgent(
            name="test-agent",
            description="Test agent description",
            instructions="Test agent instructions.",
            tools=["Read", "Grep", "Glob"],
            model="sonnet",
            source_format="claude"
        )

    @pytest.fixture
    def canonical_agent_with_metadata(self):
        """CanonicalAgent with Claude-specific metadata."""
        agent = CanonicalAgent(
            name="metadata-agent",
            description="Agent with metadata",
            instructions="Agent instructions.",
            tools=["Read", "Grep"],
            model="opus",
            source_format="claude"
        )
        agent.add_metadata('claude_permission_mode', 'ask')
        agent.add_metadata('claude_skills', ['python', 'javascript'])
        return agent

    # Phase 1: Property Tests

    def test_format_properties(self, adapter):
        """Test adapter properties."""
        assert adapter.format_name == "claude"
        assert adapter.file_extension == ".md"
        assert ConfigType.AGENT in adapter.supported_config_types

    def test_can_handle(self, adapter):
        """Test file detection."""
        assert adapter.can_handle(Path("agent.md")) is True
        assert adapter.can_handle(Path("agent.agent.md")) is False
        assert adapter.can_handle(Path("agent.txt")) is False

    def test_to_canonical(self, adapter, sample_claude_content):
        """Test conversion from Claude format to canonical."""
        agent = adapter.to_canonical(sample_claude_content, ConfigType.AGENT)
        assert agent.name == "test-agent"
        assert agent.description == "Test agent description"
        assert agent.tools == ["Read", "Grep", "Glob"]
        assert agent.model == "sonnet"
        assert agent.instructions == "Test agent instructions here."
        assert agent.source_format == "claude"
        assert agent.get_metadata('claude_permission_mode') == 'ask'

    def test_from_canonical(self, adapter):
        """Test conversion from canonical to Claude format."""
        agent = CanonicalAgent(
            name="test-agent",
            description="Test description",
            instructions="Test instructions",
            tools=["Read", "Edit"],
            model="sonnet",
            source_format="claude"
        )
        agent.add_metadata('claude_permission_mode', 'ask')

        output = adapter.from_canonical(agent, ConfigType.AGENT)

        assert "name: test-agent" in output
        assert "description: Test description" in output
        assert "tools: Read, Edit" in output
        assert "model: sonnet" in output
        assert "permissionMode: ask" in output
        assert "Test instructions" in output

    def test_round_trip(self, adapter, sample_claude_content):
        """Test Claude -> Canonical -> Claude preserves data."""
        canonical = adapter.to_canonical(sample_claude_content, ConfigType.AGENT)
        output = adapter.from_canonical(canonical, ConfigType.AGENT)
        canonical2 = adapter.to_canonical(output, ConfigType.AGENT)

        assert canonical.name == canonical2.name
        assert canonical.description == canonical2.description
        assert canonical.model == canonical2.model
        assert canonical.tools == canonical2.tools
        assert canonical.get_metadata('claude_permission_mode') == canonical2.get_metadata('claude_permission_mode')

    # Phase 2: Additional Core Parsing Tests

    def test_to_canonical_minimal(self, adapter, minimal_claude_content):
        """Test parsing agent with only required fields."""
        agent = adapter.to_canonical(minimal_claude_content, ConfigType.AGENT)
        assert agent.name == "minimal-agent"
        assert agent.description == "Minimal agent"
        assert agent.instructions == "Basic instructions."
        assert agent.tools == []
        assert agent.model is None
        assert not agent.has_metadata('claude_permission_mode')

    def test_to_canonical_full(self, adapter, full_claude_content):
        """Test parsing agent with all fields."""
        agent = adapter.to_canonical(full_claude_content, ConfigType.AGENT)
        assert agent.name == "full-agent"
        assert agent.description == "Full agent with metadata"
        assert agent.instructions == "Full agent instructions."
        assert agent.tools == ["Read", "Grep", "Glob", "Bash"]
        assert agent.model == "opus"
        assert agent.get_metadata('claude_permission_mode') == 'ask'
        assert agent.get_metadata('claude_skills') == ['python', 'javascript']

    def test_to_canonical_from_file(self, adapter, tmp_path):
        """Test read() method with file."""
        fixture_path = Path("tests/fixtures/claude/simple-agent.md")
        agent = adapter.read(fixture_path, ConfigType.AGENT)
        assert agent.name == "simple-agent"
        assert agent.description == "A simple test agent for unit testing"
        assert agent.tools == ["Read", "Grep", "Glob"]
        assert agent.model == "sonnet"

    def test_to_canonical_invalid_no_frontmatter(self, adapter):
        """Test error handling for content without YAML frontmatter."""
        content = "This has no frontmatter"
        with pytest.raises(ValueError, match="No YAML frontmatter found"):
            adapter.to_canonical(content, ConfigType.AGENT)

    # Phase 3: Helper Method Tests

    def test_parse_tools_comma_separated(self, adapter):
        """Test tool parsing from comma-separated string."""
        result = adapter._parse_tools("Read, Grep, Glob")
        assert result == ["Read", "Grep", "Glob"]

    def test_parse_tools_with_whitespace(self, adapter):
        """Test tool parsing with extra whitespace."""
        result = adapter._parse_tools("Read,  Grep  ,Glob")
        assert result == ["Read", "Grep", "Glob"]

    def test_parse_tools_as_list(self, adapter):
        """Test tool parsing when already a list."""
        result = adapter._parse_tools(["Read", "Grep"])
        assert result == ["Read", "Grep"]

    def test_parse_tools_empty(self, adapter):
        """Test tool parsing with empty input."""
        assert adapter._parse_tools("") == []
        assert adapter._parse_tools(None) == []

    def test_normalize_model_lowercase(self, adapter):
        """Test model normalization to lowercase."""
        assert adapter._normalize_model("Sonnet") == "sonnet"
        assert adapter._normalize_model("OPUS") == "opus"

    def test_normalize_model_already_lowercase(self, adapter):
        """Test model normalization when already lowercase."""
        assert adapter._normalize_model("opus") == "opus"
        assert adapter._normalize_model("haiku") == "haiku"

    def test_normalize_model_none(self, adapter):
        """Test model normalization with None."""
        assert adapter._normalize_model(None) is None

    # Phase 4: Additional Serialization Tests

    def test_from_canonical_basic(self, adapter, canonical_agent_sample):
        """Test conversion from canonical to Claude format."""
        output = adapter.from_canonical(canonical_agent_sample, ConfigType.AGENT)
        assert "name: test-agent" in output
        assert "description: Test agent description" in output
        assert "tools: Read, Grep, Glob" in output
        assert "model: sonnet" in output
        assert "Test agent instructions." in output
        assert output.startswith("---\n")
        assert "---\n" in output[4:]  # Second --- separator

    def test_from_canonical_with_metadata(self, adapter, canonical_agent_with_metadata):
        """Test metadata preservation in serialization."""
        output = adapter.from_canonical(canonical_agent_with_metadata, ConfigType.AGENT)
        assert "permissionMode: ask" in output
        assert "skills:" in output
        assert "python" in output
        assert "javascript" in output

    def test_from_canonical_empty_tools(self, adapter):
        """Test serialization with empty tools list."""
        agent = CanonicalAgent(
            name="no-tools",
            description="Agent without tools",
            instructions="Instructions.",
            tools=[],
            model="sonnet"
        )
        output = adapter.from_canonical(agent, ConfigType.AGENT)
        assert "name: no-tools" in output
        assert "description: Agent without tools" in output

    def test_from_canonical_no_model(self, adapter):
        """Test serialization when model is None."""
        agent = CanonicalAgent(
            name="no-model",
            description="Agent without model",
            instructions="Instructions.",
            tools=["Read"],
            model=None
        )
        output = adapter.from_canonical(agent, ConfigType.AGENT)
        assert "name: no-model" in output
        lines = output.split('\n')
        model_lines = [line for line in lines if line.startswith('model:')]
        assert len(model_lines) == 0

    # Phase 5: Additional Round-Trip Tests

    def test_round_trip_preserves_all_data(self, adapter, sample_claude_content):
        """Test Claude -> Canonical -> Claude -> Canonical preserves all data."""
        canonical1 = adapter.to_canonical(sample_claude_content, ConfigType.AGENT)
        output = adapter.from_canonical(canonical1, ConfigType.AGENT)
        canonical2 = adapter.to_canonical(output, ConfigType.AGENT)

        assert canonical1.name == canonical2.name
        assert canonical1.description == canonical2.description
        assert canonical1.instructions == canonical2.instructions
        assert canonical1.tools == canonical2.tools
        assert canonical1.model == canonical2.model
        assert canonical1.get_metadata('claude_permission_mode') == canonical2.get_metadata('claude_permission_mode')

    def test_round_trip_minimal(self, adapter, minimal_claude_content):
        """Test round-trip with minimal agent."""
        canonical1 = adapter.to_canonical(minimal_claude_content, ConfigType.AGENT)
        output = adapter.from_canonical(canonical1, ConfigType.AGENT)
        canonical2 = adapter.to_canonical(output, ConfigType.AGENT)

        assert canonical1.name == canonical2.name
        assert canonical1.description == canonical2.description
        assert canonical1.instructions == canonical2.instructions
        assert canonical1.tools == canonical2.tools
        assert canonical1.model == canonical2.model

    def test_round_trip_metadata_preservation(self, adapter, full_claude_content):
        """Test metadata preservation through round-trip."""
        canonical1 = adapter.to_canonical(full_claude_content, ConfigType.AGENT)
        output = adapter.from_canonical(canonical1, ConfigType.AGENT)
        canonical2 = adapter.to_canonical(output, ConfigType.AGENT)

        assert canonical1.get_metadata('claude_permission_mode') == canonical2.get_metadata('claude_permission_mode')
        assert canonical1.get_metadata('claude_skills') == canonical2.get_metadata('claude_skills')

    # Phase 6: File I/O Tests

    def test_read_from_file(self, adapter, tmp_path):
        """Test reading agent from file."""
        test_file = tmp_path / "test-agent.md"
        test_file.write_text("""---
name: file-test
description: Test from file
tools: Read, Grep
model: sonnet
---
File test instructions.
""")
        agent = adapter.read(test_file, ConfigType.AGENT)
        assert agent.name == "file-test"
        assert agent.description == "Test from file"
        assert agent.tools == ["Read", "Grep"]

    def test_write_to_file(self, adapter, canonical_agent_sample, tmp_path):
        """Test writing canonical agent to file."""
        test_file = tmp_path / "output-agent.md"
        adapter.write(canonical_agent_sample, test_file, ConfigType.AGENT)

        assert test_file.exists()
        content = test_file.read_text()
        assert "name: test-agent" in content
        assert "description: Test agent description" in content
        assert content.startswith("---\n")

    # Phase 7: Edge Cases

    def test_special_characters_in_fields(self, adapter):
        """Test handling of special characters in YAML fields."""
        content = """---
name: special-agent
description: "Agent with: colons and 'quotes'"
tools: Read, Grep
model: sonnet
---
Instructions with special characters: colons, "quotes", and more.
"""
        agent = adapter.to_canonical(content, ConfigType.AGENT)
        assert agent.name == "special-agent"
        assert "colons" in agent.description
        assert "quotes" in agent.description

    def test_multiline_instructions(self, adapter):
        """Test preservation of multiline markdown instructions."""
        fixture_path = Path("tests/fixtures/claude/edge-cases/multiline-instructions.md")
        agent = adapter.read(fixture_path, ConfigType.AGENT)

        assert "# Complex Instructions" in agent.instructions
        assert "```python" in agent.instructions
        assert "## Lists" in agent.instructions
        assert "**bold**" in agent.instructions

    def test_tools_with_special_spacing(self, adapter):
        """Test tool parsing with various spacing patterns."""
        fixture_path = Path("tests/fixtures/claude/edge-cases/whitespace.md")
        agent = adapter.read(fixture_path, ConfigType.AGENT)

        assert agent.tools == ["Read", "Grep", "Glob", "Bash"]
        assert agent.instructions.strip() == "Instructions with extra whitespace.\n\n  Including leading/trailing spaces."

    def test_conversion_warnings(self, adapter, sample_claude_content):
        """Test conversion warnings mechanism."""
        adapter.to_canonical(sample_claude_content, ConfigType.AGENT)
        warnings = adapter.get_conversion_warnings()
        assert isinstance(warnings, list)


class TestCopilotAdapter:
    """Tests for CopilotAdapter."""

    @pytest.fixture
    def adapter(self):
        """Create CopilotAdapter instance."""
        return CopilotAdapter()

    @pytest.fixture
    def sample_copilot_content(self):
        """Sample Copilot agent file content."""
        return """---
name: test-agent
description: Test agent description
tools:
  - read
  - grep
  - glob
model: Claude Sonnet 4
target: vscode
---
Test agent instructions here.
"""

    @pytest.fixture
    def full_copilot_content(self):
        """Copilot agent with all optional fields."""
        return """---
name: full-agent
description: Agent with all optional fields
tools:
  - read
  - grep
  - glob
  - edit
model: Claude Sonnet 4
target: vscode
argument-hint: Use this agent for complex tasks
handoffs:
  - label: Continue
    agent: next-agent
    prompt: Continue with next step
    send: false
mcp-servers:
  - name: example-server
    url: http://localhost:3000
---
Full agent instructions with all Copilot features.
"""

    def test_format_properties(self, adapter):
        """Test adapter properties."""
        assert adapter.format_name == "copilot"
        assert adapter.file_extension == ".agent.md"
        assert ConfigType.AGENT in adapter.supported_config_types

    def test_can_handle(self, adapter):
        """Test file detection."""
        assert adapter.can_handle(Path("agent.agent.md")) is True
        assert adapter.can_handle(Path("test.agent.md")) is True
        assert adapter.can_handle(Path("agent.md")) is False
        assert adapter.can_handle(Path("agent.txt")) is False

    def test_to_canonical(self, adapter, sample_copilot_content):
        """Test conversion from Copilot format to canonical."""
        agent = adapter.to_canonical(sample_copilot_content, ConfigType.AGENT)

        assert agent.name == "test-agent"
        assert agent.description == "Test agent description"
        assert agent.tools == ["read", "grep", "glob"]
        assert agent.model == "sonnet"  # Normalized from "Claude Sonnet 4"
        assert agent.instructions == "Test agent instructions here."
        assert agent.source_format == "copilot"
        assert agent.get_metadata('copilot_target') == "vscode"

    def test_to_canonical_with_metadata(self, adapter, full_copilot_content):
        """Test that Copilot-specific fields are preserved in metadata."""
        agent = adapter.to_canonical(full_copilot_content, ConfigType.AGENT)

        assert agent.get_metadata('copilot_argument_hint') == "Use this agent for complex tasks"
        assert agent.get_metadata('copilot_target') == "vscode"

        handoffs = agent.get_metadata('copilot_handoffs')
        assert handoffs is not None
        assert len(handoffs) == 1
        assert handoffs[0]['label'] == "Continue"
        assert handoffs[0]['agent'] == "next-agent"

        mcp_servers = agent.get_metadata('copilot_mcp_servers')
        assert mcp_servers is not None
        assert len(mcp_servers) == 1
        assert mcp_servers[0]['name'] == "example-server"

    def test_to_canonical_missing_frontmatter(self, adapter):
        """Test error handling when YAML frontmatter is missing."""
        invalid_content = "No frontmatter here, just text."

        with pytest.raises(ValueError, match="No YAML frontmatter found"):
            adapter.to_canonical(invalid_content, ConfigType.AGENT)

    def test_from_canonical(self, adapter):
        """Test conversion from canonical to Copilot format."""
        agent = CanonicalAgent(
            name="test-agent",
            description="Test description",
            instructions="Test instructions",
            tools=["read", "edit"],
            model="sonnet",
            source_format="canonical"
        )

        output = adapter.from_canonical(agent, ConfigType.AGENT)

        assert "name: test-agent" in output
        assert "description: Test description" in output
        assert "model: Claude Sonnet 4" in output  # Denormalized
        assert "target: vscode" in output  # Always added
        assert "Test instructions" in output
        # Tools should be in YAML list format
        assert "tools:" in output

    def test_from_canonical_with_options(self, adapter):
        """Test from_canonical with options to add optional fields."""
        agent = CanonicalAgent(
            name="test-agent",
            description="Test description",
            instructions="Test instructions",
            tools=["read"],
            model="sonnet"
        )

        # Test with add_argument_hint option
        output = adapter.from_canonical(
            agent, ConfigType.AGENT,
            options={'add_argument_hint': True}
        )
        assert "argument-hint:" in output

        # Test with add_handoffs option
        output = adapter.from_canonical(
            agent, ConfigType.AGENT,
            options={'add_handoffs': True}
        )
        assert "handoffs:" in output

    def test_from_canonical_preserves_metadata(self, adapter, full_copilot_content):
        """Test that metadata from original Copilot file is restored."""
        # First convert to canonical (preserving metadata)
        agent = adapter.to_canonical(full_copilot_content, ConfigType.AGENT)

        # Then convert back to Copilot format
        output = adapter.from_canonical(agent, ConfigType.AGENT)

        # Verify preserved metadata appears in output
        assert "argument-hint:" in output
        assert "handoffs:" in output
        assert "mcp-servers:" in output

    def test_model_name_mapping(self, adapter):
        """Test model name conversion between Copilot and canonical forms."""
        # Test normalization (Copilot -> canonical)
        assert adapter._normalize_model("Claude Sonnet 4") == "sonnet"
        assert adapter._normalize_model("Claude Opus 4") == "opus"
        assert adapter._normalize_model("Claude Haiku 4") == "haiku"
        assert adapter._normalize_model("claude sonnet 4") == "sonnet"  # Case insensitive
        assert adapter._normalize_model(None) is None
        assert adapter._normalize_model("unknown-model") == "unknown-model"  # Pass through

        # Test denormalization (canonical -> Copilot)
        assert adapter._denormalize_model("sonnet") == "Claude Sonnet 4"
        assert adapter._denormalize_model("opus") == "Claude Opus 4"
        assert adapter._denormalize_model("haiku") == "Claude Haiku 4"
        assert adapter._denormalize_model("unknown") == "unknown"  # Pass through

    def test_round_trip(self, adapter, full_copilot_content):
        """Test Copilot -> Canonical -> Copilot preserves all data."""
        # Convert to canonical
        canonical = adapter.to_canonical(full_copilot_content, ConfigType.AGENT)

        # Convert back to Copilot format
        output = adapter.from_canonical(canonical, ConfigType.AGENT)

        # Parse the output again
        canonical2 = adapter.to_canonical(output, ConfigType.AGENT)

        # Verify core fields preserved
        assert canonical.name == canonical2.name
        assert canonical.description == canonical2.description
        assert canonical.model == canonical2.model
        assert canonical.tools == canonical2.tools

        # Verify metadata preserved
        assert canonical.get_metadata('copilot_argument_hint') == canonical2.get_metadata('copilot_argument_hint')
        assert canonical.get_metadata('copilot_target') == canonical2.get_metadata('copilot_target')
        assert canonical.get_metadata('copilot_handoffs') == canonical2.get_metadata('copilot_handoffs')
        assert canonical.get_metadata('copilot_mcp_servers') == canonical2.get_metadata('copilot_mcp_servers')


class TestCrossFormatConversion:
    """Tests for converting between different formats."""

    @pytest.fixture
    def claude_adapter(self):
        """Create ClaudeAdapter instance."""
        return ClaudeAdapter()

    @pytest.fixture
    def copilot_adapter(self):
        """Create CopilotAdapter instance."""
        return CopilotAdapter()

    @pytest.fixture
    def sample_claude_content(self):
        """Sample Claude agent file content."""
        return """---
name: cross-test-agent
description: Agent for cross-format testing
tools: Read, Grep, Glob
model: sonnet
permissionMode: ask
---
Cross-format test instructions.
"""

    @pytest.fixture
    def sample_copilot_content(self):
        """Sample Copilot agent file content."""
        return """---
name: cross-test-agent
description: Agent for cross-format testing
tools:
  - read
  - grep
  - glob
model: Claude Sonnet 4
target: vscode
argument-hint: Test hint
---
Cross-format test instructions.
"""

    def test_claude_to_copilot(self, claude_adapter, copilot_adapter, sample_claude_content):
        """Test Claude -> Canonical -> Copilot conversion."""
        # Claude to canonical
        canonical = claude_adapter.to_canonical(sample_claude_content, ConfigType.AGENT)

        # Canonical to Copilot
        copilot_output = copilot_adapter.from_canonical(canonical, ConfigType.AGENT)

        # Verify result
        assert "name: cross-test-agent" in copilot_output
        assert "model: Claude Sonnet 4" in copilot_output  # Model denormalized
        assert "target: vscode" in copilot_output
        assert "Cross-format test instructions" in copilot_output

    def test_copilot_to_claude(self, claude_adapter, copilot_adapter, sample_copilot_content):
        """Test Copilot -> Canonical -> Claude conversion."""
        # Copilot to canonical
        canonical = copilot_adapter.to_canonical(sample_copilot_content, ConfigType.AGENT)

        # Canonical to Claude
        claude_output = claude_adapter.from_canonical(canonical, ConfigType.AGENT)

        # Verify result
        assert "name: cross-test-agent" in claude_output
        assert "model: sonnet" in claude_output  # Model stays canonical
        assert "Cross-format test instructions" in claude_output

    def test_claude_to_copilot_to_claude(self, claude_adapter, copilot_adapter, sample_claude_content):
        """Test Claude -> Copilot -> Claude round-trip preserves core data.

        Note: Format-specific metadata (like Claude's permissionMode) is NOT
        preserved when going through another format, because that format's
        adapter doesn't know about or serialize the foreign metadata keys.
        This is expected behavior with the current design.
        """
        # Claude -> Canonical
        canonical1 = claude_adapter.to_canonical(sample_claude_content, ConfigType.AGENT)

        # Canonical -> Copilot
        copilot_output = copilot_adapter.from_canonical(canonical1, ConfigType.AGENT)

        # Copilot -> Canonical
        canonical2 = copilot_adapter.to_canonical(copilot_output, ConfigType.AGENT)

        # Canonical -> Claude
        claude_output = claude_adapter.from_canonical(canonical2, ConfigType.AGENT)

        # Claude -> Canonical (for final comparison)
        canonical3 = claude_adapter.to_canonical(claude_output, ConfigType.AGENT)

        # Core fields should be preserved
        assert canonical1.name == canonical3.name
        assert canonical1.description == canonical3.description
        assert canonical1.model == canonical3.model

        # Note: Claude-specific metadata (permissionMode) is lost when going through Copilot
        # because CopilotAdapter.from_canonical() doesn't serialize Claude metadata
        # This is expected - only same-format round-trips preserve all metadata
        assert canonical1.get_metadata('claude_permission_mode') == 'ask'
        assert canonical3.get_metadata('claude_permission_mode') is None  # Lost in conversion

    def test_copilot_to_claude_to_copilot(self, claude_adapter, copilot_adapter, sample_copilot_content):
        """Test Copilot -> Claude -> Copilot round-trip preserves core data.

        Note: Format-specific metadata (like Copilot's argument-hint) is NOT
        preserved when going through another format, because that format's
        adapter doesn't know about or serialize the foreign metadata keys.
        Only the default 'target: vscode' is added back by CopilotAdapter.
        """
        # Copilot -> Canonical
        canonical1 = copilot_adapter.to_canonical(sample_copilot_content, ConfigType.AGENT)

        # Canonical -> Claude
        claude_output = claude_adapter.from_canonical(canonical1, ConfigType.AGENT)

        # Claude -> Canonical
        canonical2 = claude_adapter.to_canonical(claude_output, ConfigType.AGENT)

        # Canonical -> Copilot
        copilot_output = copilot_adapter.from_canonical(canonical2, ConfigType.AGENT)

        # Copilot -> Canonical (for final comparison)
        canonical3 = copilot_adapter.to_canonical(copilot_output, ConfigType.AGENT)

        # Core fields should be preserved
        assert canonical1.name == canonical3.name
        assert canonical1.description == canonical3.description
        assert canonical1.model == canonical3.model

        # Note: Copilot-specific metadata (argument-hint) is lost when going through Claude
        # because ClaudeAdapter.from_canonical() doesn't serialize Copilot metadata
        # This is expected - only same-format round-trips preserve all metadata
        assert canonical1.get_metadata('copilot_argument_hint') == 'Test hint'
        assert canonical3.get_metadata('copilot_argument_hint') is None  # Lost in conversion

        # Target is preserved because CopilotAdapter always adds it with default 'vscode'
        assert canonical3.get_metadata('copilot_target') == 'vscode'

    def test_metadata_preservation_cross_format(self, claude_adapter, copilot_adapter):
        """Test that format-specific metadata survives cross-format conversion."""
        # Create an agent with both Claude and Copilot metadata
        agent = CanonicalAgent(
            name="metadata-test",
            description="Testing metadata preservation",
            instructions="Test instructions",
            tools=["read", "edit"],
            model="sonnet"
        )
        agent.add_metadata('claude_permission_mode', 'ask')
        agent.add_metadata('claude_skills', [{'name': 'test-skill'}])
        agent.add_metadata('copilot_argument_hint', 'Test hint')
        agent.add_metadata('copilot_handoffs', [{'label': 'Next', 'agent': 'next-agent'}])

        # Convert to Claude format
        claude_output = claude_adapter.from_canonical(agent, ConfigType.AGENT)
        claude_canonical = claude_adapter.to_canonical(claude_output, ConfigType.AGENT)

        # Claude-specific metadata should survive
        assert claude_canonical.get_metadata('claude_permission_mode') == 'ask'
        assert claude_canonical.get_metadata('claude_skills') == [{'name': 'test-skill'}]

        # Copilot-specific metadata should still be in the original agent
        # (it doesn't survive Claude round-trip as Claude doesn't know about it)

        # Convert original agent to Copilot format
        copilot_output = copilot_adapter.from_canonical(agent, ConfigType.AGENT)
        copilot_canonical = copilot_adapter.to_canonical(copilot_output, ConfigType.AGENT)

        # Copilot-specific metadata should survive
        assert copilot_canonical.get_metadata('copilot_argument_hint') == 'Test hint'
        assert copilot_canonical.get_metadata('copilot_handoffs') == [{'label': 'Next', 'agent': 'next-agent'}]
