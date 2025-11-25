"""
Example format adapter template.

This file serves as a template for implementing new format adapters.
Copy this file and modify it to add support for a new AI coding tool.

To implement a new adapter:
1. Copy this file to adapters/yourformat.py
2. Rename ExampleAdapter to YourFormatAdapter
3. Implement all abstract methods
4. Register in cli/main.py or your application

See ClaudeAdapter and CopilotAdapter for working examples.
"""

from pathlib import Path
from typing import List, Optional, Dict, Any

from core.adapter_interface import FormatAdapter
from core.canonical_models import CanonicalAgent, ConfigType


class ExampleAdapter(FormatAdapter):
    """
    Example adapter template for new format implementations.

    Replace this with your format's description, including:
    - File format (Markdown, JSON, YAML, etc.)
    - File location (e.g., ~/.tool/agents/, .tool/config.json)
    - Unique features or fields
    """

    def __init__(self):
        self.warnings: List[str] = []

    @property
    def format_name(self) -> str:
        """Unique identifier for this format."""
        return "example"

    @property
    def file_extension(self) -> str:
        """Primary file extension for this format."""
        return ".example"

    @property
    def supported_config_types(self) -> List[ConfigType]:
        """Which config types this format supports."""
        return [ConfigType.AGENT]

    def can_handle(self, file_path: Path) -> bool:
        """Check if this adapter can handle the given file."""
        return file_path.suffix == self.file_extension

    def read(self, file_path: Path, config_type: ConfigType) -> CanonicalAgent:
        """Read file and convert to canonical format."""
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        return self.to_canonical(content, config_type)

    def write(self, canonical_obj: CanonicalAgent, file_path: Path, config_type: ConfigType):
        """Write canonical format to file."""
        content = self.from_canonical(canonical_obj, config_type)
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)

    def to_canonical(self, content: str, config_type: ConfigType) -> CanonicalAgent:
        """
        Convert format-specific content to canonical representation.

        Implementation steps:
        1. Parse the content (YAML, JSON, custom format, etc.)
        2. Extract fields and map to canonical fields
        3. Store format-specific fields in metadata for round-trip preservation
        4. Return CanonicalAgent instance
        """
        self.warnings = []

        # TODO: Implement parsing logic
        # Example:
        # parsed = parse_your_format(content)
        # agent = CanonicalAgent(
        #     name=parsed['name'],
        #     description=parsed['description'],
        #     instructions=parsed['body'],
        #     tools=parsed.get('tools', []),
        #     model=self._normalize_model(parsed.get('model')),
        #     source_format=self.format_name
        # )
        # # Preserve format-specific fields
        # if 'unique_field' in parsed:
        #     agent.add_metadata('example_unique_field', parsed['unique_field'])
        # return agent

        raise NotImplementedError("ExampleAdapter is a template - implement to_canonical()")

    def from_canonical(self, canonical_obj: CanonicalAgent, config_type: ConfigType,
                      options: Optional[Dict[str, Any]] = None) -> str:
        """
        Convert canonical representation to format-specific content.

        Implementation steps:
        1. Extract fields from canonical object
        2. Map canonical fields to format-specific fields
        3. Restore format-specific fields from metadata
        4. Generate output string
        """
        self.warnings = []
        options = options or {}

        # TODO: Implement serialization logic
        # Example:
        # output = {
        #     'name': canonical_obj.name,
        #     'description': canonical_obj.description,
        #     'tools': self._format_tools(canonical_obj.tools),
        #     'model': self._denormalize_model(canonical_obj.model)
        # }
        # # Restore format-specific fields from metadata
        # if canonical_obj.get_metadata('example_unique_field'):
        #     output['unique_field'] = canonical_obj.get_metadata('example_unique_field')
        # return serialize_your_format(output, canonical_obj.instructions)

        raise NotImplementedError("ExampleAdapter is a template - implement from_canonical()")

    def get_conversion_warnings(self) -> List[str]:
        """Return warnings about data loss or unsupported features."""
        return self.warnings

    # Helper methods (customize for your format)

    def _normalize_model(self, model: Optional[str]) -> Optional[str]:
        """
        Convert format-specific model names to canonical form.

        Canonical model names: sonnet, opus, haiku
        """
        if not model:
            return None
        # TODO: Add your model mappings
        # model_map = {
        #     'your-sonnet-name': 'sonnet',
        #     'your-opus-name': 'opus',
        # }
        # return model_map.get(model.lower(), model.lower())
        return model.lower()

    def _denormalize_model(self, model: Optional[str]) -> Optional[str]:
        """Convert canonical model names to format-specific names."""
        if not model:
            return None
        # TODO: Add your reverse model mappings
        # model_map = {
        #     'sonnet': 'Your Sonnet Name',
        #     'opus': 'Your Opus Name',
        # }
        # return model_map.get(model.lower(), model)
        return model
