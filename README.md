# Agent Sync Tool

Bidirectional synchronization tool for custom agents between Claude Code and GitHub Copilot.

## Features

- ✅ **Bidirectional sync** - Sync in both directions automatically
- ✅ **Smart conflict resolution** - Handles conflicts with user prompts or auto-resolution
- ✅ **Deletion tracking** - Removes agents deleted from source
- ✅ **Modification tracking** - Only syncs changed files using `.agent_sync_state.json`
- ✅ **Format conversion** - Automatic conversion between `.md` and `.agent.md` formats
- ✅ **Field mapping** - Intelligent mapping of format-specific fields
- ✅ **Dry-run mode** - Preview changes before applying

## Requirements

```bash
pip install pyyaml
```

## Installation

```bash
chmod +x sync_custom_agents.py
```

## Usage

### Basic Bidirectional Sync

```bash
python sync_custom_agents.py \
  --claude-dir ~/.claude/agents \
  --copilot-dir ./.github/agents
```

### One-Time Migration

**Claude → Copilot:**
```bash
python sync_custom_agents.py \
  --claude-dir ~/.claude/agents \
  --copilot-dir ./.github/agents \
  --direction claude-to-copilot
```

**Copilot → Claude:**
```bash
python sync_custom_agents.py \
  --claude-dir ~/.claude/agents \
  --copilot-dir ./.github/agents \
  --direction copilot-to-claude
```

### Preview Changes (Dry Run)

```bash
python sync_custom_agents.py \
  --claude-dir ~/.claude/agents \
  --copilot-dir ./.github/agents \
  --dry-run
```

### With Enhanced Copilot Features

```bash
python sync_custom_agents.py \
  --claude-dir ~/.claude/agents \
  --copilot-dir ./.github/agents \
  --direction claude-to-copilot \
  --add-argument-hint \
  --add-handoffs
```

## Arguments

| Argument | Required | Default | Description |
|----------|----------|---------|-------------|
| `--claude-dir` | Yes | - | Path to Claude Code agents directory |
| `--copilot-dir` | Yes | - | Path to GitHub Copilot agents directory |
| `--direction` | No | `both` | Sync direction: `claude-to-copilot`, `copilot-to-claude`, or `both` |
| `--dry-run` | No | `false` | Show changes without applying them |
| `--force` | No | `false` | Auto-resolve conflicts using newest file |
| `--verbose`, `-v` | No | `false` | Detailed logging output |
| `--add-argument-hint` | No | `false` | Add `argument-hint` field (Claude→Copilot only) |
| `--add-handoffs` | No | `false` | Add `handoffs` placeholder (Claude→Copilot only) |

## How It Works

### File Matching

Agents are matched by base name:
- `planner.md` (Claude) ↔ `planner.agent.md` (Copilot)
- `code-reviewer.md` (Claude) ↔ `code-reviewer.agent.md` (Copilot)

### Sync Logic

1. **First Sync**: Uses the newest file based on modification time
2. **Subsequent Syncs**: Only syncs files modified since last sync
3. **Conflicts**: When both files are modified:
   - Without `--force`: Prompts user to choose
   - With `--force`: Uses newest file automatically
4. **Deletions**: Removes target file when source is deleted

### State Tracking

Sync state is stored in `~/.agent_sync_state.json`:
```json
{
  "sync_pairs": {
    "/home/user/.claude/agents|/home/user/project/.github/agents": {
      "last_sync": "2025-01-15T10:30:00Z",
      "files": {
        "planner": {
          "claude_mtime": 1705315800.0,
          "copilot_mtime": 1705315800.0,
          "last_action": "claude_to_copilot",
          "last_sync_time": "2025-01-15T10:30:00Z"
        }
      }
    }
  }
}
```

## Field Conversions

### Claude → Copilot

| Claude Field | Copilot Field | Conversion |
|--------------|---------------|------------|
| `name` | `name` | Direct |
| `description` | `description` | Direct |
| `description` | `argument-hint` | Optional (with `--add-argument-hint`) |
| `tools` | `tools` | String → Array (`"tool1, tool2"` → `['tool1', 'tool2']`) |
| `model` | `model` | Mapped (`sonnet` → `Claude Sonnet 4`) |
| - | `target` | Added (`vscode`) |
| - | `handoffs` | Optional placeholder (with `--add-handoffs`) |
| `permissionMode` | - | **Dropped** |
| `skills` | - | **Dropped** |

### Copilot → Claude

| Copilot Field | Claude Field | Conversion |
|---------------|--------------|------------|
| `name` | `name` | Direct |
| `description` | `description` | Direct |
| `tools` | `tools` | Array → String (`['tool1', 'tool2']` → `"tool1, tool2"`) |
| `model` | `model` | Mapped (`Claude Sonnet 4` → `sonnet`) |
| `argument-hint` | - | **Dropped** |
| `handoffs` | - | **Dropped** |
| `target` | - | **Dropped** |
| `mcp-servers` | - | **Dropped** |

## Examples

### Example 1: Initial Setup

```bash
# First time sync from Claude to Copilot
python sync_custom_agents.py \
  --claude-dir ~/.claude/agents \
  --copilot-dir ~/projects/myapp/.github/agents \
  --direction claude-to-copilot \
  --add-argument-hint \
  --verbose
```

Output:
```
🔄 Syncing agents: claude-to-copilot
   Claude:  /home/user/.claude/agents
   Copilot: /home/user/projects/myapp/.github/agents

→ planner: Claude → Copilot (New Claude agent)
  Mapped name: planner
  Mapped description
  Added argument-hint from description
  Converted tools: string → array (4 tools)
  Mapped model: sonnet → Claude Sonnet 4
  Set target: vscode

→ code-reviewer: Claude → Copilot (New Claude agent)
  ...

============================================================
Summary:
  Claude → Copilot: 2
  Copilot → Claude: 0
  Deletions:        0
  Conflicts:        0
  Skipped:          0
  Errors:           0
============================================================
```

### Example 2: Ongoing Sync with Conflicts

```bash
# Run periodically (e.g., via cron)
python sync_custom_agents.py \
  --claude-dir ~/.claude/agents \
  --copilot-dir ~/projects/myapp/.github/agents \
  --force
```

Output (with conflict):
```
🔄 Syncing agents: both
   Claude:  /home/user/.claude/agents
   Copilot: /home/user/projects/myapp/.github/agents

→ planner: Claude → Copilot (Claude agent modified)
← debugger: Copilot → Claude (Copilot agent modified)

⚠️  CONFLICT: Both files modified for agent 'code-reviewer'
  Claude:  /home/user/.claude/agents/code-reviewer.md (modified: 2025-01-15 10:30:00)
  Copilot: /home/user/projects/myapp/.github/agents/code-reviewer.agent.md (modified: 2025-01-15 11:00:00)

Conflict resolved (--force): Using Copilot version (newer)
← code-reviewer: Copilot → Claude (Both files modified since last sync)
```

### Example 3: Dry Run

```bash
python sync_custom_agents.py \
  --claude-dir ~/.claude/agents \
  --copilot-dir ./.github/agents \
  --dry-run
```

Output:
```
🔄 Syncing agents: both
   Claude:  /home/user/.claude/agents
   Copilot: /home/user/projects/myapp/.github/agents
   Mode: DRY RUN (no changes will be made)

→ new-agent: Claude → Copilot (New Claude agent)
🗑️ old-agent: Delete Copilot agent (Claude agent deleted)

============================================================
Summary:
  Claude → Copilot: 1
  Copilot → Claude: 0
  Deletions:        1
  Conflicts:        0
  Skipped:          0
  Errors:           0
============================================================

💡 This was a dry run. Use without --dry-run to apply changes.
```

## Troubleshooting

### "No YAML frontmatter found"

Ensure your agent files have proper YAML frontmatter:
```markdown
---
name: agent-name
description: Agent description
---

Body content here
```

### "Directory does not exist"

Make sure both directories exist before running:
```bash
mkdir -p ~/.claude/agents
mkdir -p .github/agents
```

### Conflicts Keep Appearing

Use `--force` to automatically resolve conflicts, or manually review and edit the files to resolve differences.

### State File Issues

If sync state gets corrupted, you can safely delete it:
```bash
rm ~/.agent_sync_state.json
```

The next sync will treat all files as new.

## Tips

1. **Use dry-run first**: Always preview changes with `--dry-run` before actual sync
2. **Backup important agents**: Keep backups of critical agents before first sync
3. **Review conversions**: Check converted agents for any dropped fields that matter to you
4. **Use version control**: Keep your `.github/agents` directory in git
5. **Schedule wisely**: Don't sync too frequently - hourly is usually sufficient

