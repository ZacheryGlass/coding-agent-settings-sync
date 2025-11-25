"""
Format adapters for converting between tool-specific formats and canonical representation.

This module contains concrete implementations of FormatAdapter for each supported
AI coding tool. Each adapter knows how to:
- Parse the tool's configuration format
- Convert to canonical representation
- Convert from canonical back to tool format
- Preserve format-specific fields via metadata

Available adapters:
- ClaudeAdapter: Claude Code (.md files)
- CopilotAdapter: GitHub Copilot (.agent.md files)
- ExampleAdapter: Template for new implementations

Adding a new adapter:
1. Copy example.py to yourformat.py
2. Implement FormatAdapter interface
3. Register with FormatRegistry in your application
"""

from .claude import ClaudeAdapter
from .copilot import CopilotAdapter
from .example import ExampleAdapter

__all__ = [
    'ClaudeAdapter',
    'CopilotAdapter',
    'ExampleAdapter',
]
