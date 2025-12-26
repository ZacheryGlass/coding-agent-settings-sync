# Architecture

## Overview

Hub-and-spoke architecture with canonical data models enabling N-way sync with 2N converters instead of N².

## Core Concept

```
Format A → Canonical Model ← Format B
                ↓
            Format C
```

Adding format N+1 requires only 2 converters (to/from canonical), not 2N.

## Modules

### Core Architecture

#### core/canonical_models.py
Universal data representations:
- `CanonicalAgent`: Universal agent model
- `CanonicalPermission`: Universal permission model
- `CanonicalSlashCommand`: Universal slash command model
- Metadata dictionary preserves format-specific fields for round-trip fidelity

#### core/adapter_interface.py
Abstract base class defining converter contract:
- `FormatAdapter`: Base class for all format converters
- `to_canonical()`: Convert format-specific to canonical
- `from_canonical()`: Convert canonical to format-specific
- Each format implements this interface once

#### core/registry.py
Central format directory:
- `FormatRegistry`: Manages available adapters
- Auto-detects format from file paths
- Validates format/config-type compatibility

#### core/orchestrator.py
Sync coordination:
- `UniversalSyncOrchestrator`: Coordinates sync operations
- Works with any source/target format pair
- Handles conflicts, state tracking, dry-run mode

#### core/state_manager.py
Sync state tracking:
- `SyncStateManager`: Tracks sync history
- Storage: `~/.agent_sync_state.json`
- Enables intelligent change detection

### Format Adapters

#### adapters/shared/
Shared utilities and handler interface

#### adapters/claude/
Claude Code adapter with coordinator + handlers

#### adapters/copilot/
GitHub Copilot adapter with coordinator + handlers

#### adapters/example/
Template for new adapter implementations

## Conversion Flow

```
Source Format
    ↓
Adapter.read()
    ↓
to_canonical()
    ↓
CanonicalAgent/Permission/SlashCommand
    ↓
from_canonical()
    ↓
Adapter.write()
    ↓
Target Format
```

## Key Design Decisions

### Canonical Model
All formats convert to/from universal representation. No direct format-to-format conversions.

### Information Preservation
Metadata dict stores format-specific fields not in canonical model. Enables round-trip conversions without data loss.

### Scalability
Linear growth: N formats = 2N converters, not N².

### File Matching
Agents matched by base name:
- `planner.md` ↔ `planner.agent.md`
- `debugger.md` ↔ `debugger.agent.md`

### Conflict Resolution
- Without `--force`: Prompts user for manual resolution
- With `--force`: Uses newest file based on mtime

### State Tracking
Stored in `~/.agent_sync_state.json` to work across projects. Tracks last sync time and content hashes.

### Layered Validation
- **CLI**: Validates paths exist and are accessible (fail fast at user boundary)
- **Orchestrator**: Validates format/config type compatibility (business logic)

## Adapter Responsibilities

Each adapter handles:
- Parsing format-specific structure (frontmatter, sections, etc.)
- Normalizing field names and types
- Model name mapping (e.g., Claude models to Copilot models)
- Tool format conversion
- Preserving unique fields in metadata dictionary

## Extension Points

### Adding New Config Types
1. Add canonical model to `core/canonical_models.py`
2. Create handler in each adapter's `handlers/` directory
3. Register handler in adapter coordinator's `__init__()`

### Adding New Formats
1. Copy `adapters/example/` template
2. Implement adapter coordinator
3. Implement handlers for each config type
4. Register in application

See `adding-formats.md` for detailed guide.
