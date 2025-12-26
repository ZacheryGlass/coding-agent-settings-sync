# User Guide

## Overview

Universal synchronization tool for AI coding agent configurations. Sync settings between Claude Code, GitHub Copilot, and other AI tools.

## Installation

```bash
pip install -r requirements.txt
```

## Usage

### Directory Sync

Sync all agent configurations between two directories:

```bash
python -m cli.main \
  --source-dir ~/.claude/agents \
  --target-dir .github/agents \
  --source-format claude \
  --target-format copilot \
  --config-type agent \
  --dry-run
```

Remove `--dry-run` to perform actual sync.

### Single File Conversion

Convert a single configuration file:

```bash
# With explicit output path
python -m cli.main \
  --convert-file ~/.claude/agents/planner.md \
  --target-format copilot \
  --output .github/agents/planner.agent.md

# Auto-generate output filename
python -m cli.main \
  --convert-file my-agent.md \
  --target-format copilot
```

## Parameters

- `--source-dir`: Source directory path
- `--target-dir`: Target directory path
- `--source-format`: Source format (claude, copilot)
- `--target-format`: Target format (claude, copilot)
- `--config-type`: Configuration type (agent, permission, slash-command)
- `--dry-run`: Preview changes without modifying files
- `--force`: Auto-resolve conflicts using newest file
- `--convert-file`: Path to file for single-file conversion
- `--output`: Output path for converted file

## Examples

### Sync Claude to Copilot

```bash
python -m cli.main \
  --source-dir ~/.claude/agents \
  --target-dir .github/agents \
  --source-format claude \
  --target-format copilot \
  --config-type agent
```

### Sync Copilot to Claude

```bash
python -m cli.main \
  --source-dir .github/agents \
  --target-dir ~/.claude/agents \
  --source-format copilot \
  --target-format claude \
  --config-type agent
```

### Preview Changes

Add `--dry-run` to see what would change without modifying files:

```bash
python -m cli.main \
  --source-dir ~/.claude/agents \
  --target-dir .github/agents \
  --source-format claude \
  --target-format copilot \
  --config-type agent \
  --dry-run
```

### Force Sync

Use `--force` to auto-resolve conflicts by choosing the newest file:

```bash
python -m cli.main \
  --source-dir ~/.claude/agents \
  --target-dir .github/agents \
  --source-format claude \
  --target-format copilot \
  --config-type agent \
  --force
```

## Configuration Locations

- **Claude agents**: `~/.claude/agents/` or `.claude/agents/`
- **Copilot agents**: `.github/agents/`
- **Sync state**: `~/.agent_sync_state.json` (auto-created)

## How It Works

1. Reads configuration files from source directory
2. Converts to universal canonical format
3. Converts from canonical to target format
4. Writes to target directory
5. Tracks sync state to detect changes

Files are matched by base name (e.g., `planner.md` matches `planner.agent.md`).

## Conflict Resolution

Without `--force`:
- Tool prompts for manual conflict resolution
- Choose which version to keep

With `--force`:
- Automatically uses newest file based on modification time
