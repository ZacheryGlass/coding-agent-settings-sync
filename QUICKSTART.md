# Quick Start Guide

## Installation

```bash
# Install dependencies
pip install -r requirements.txt

# Make script executable
chmod +x sync_custom_agents.py
```

## Common Usage Patterns

### 1. First-Time Setup (One-Way Migration)

If you're starting fresh and want to migrate all your Claude Code agents to Copilot:

```bash
python sync_custom_agents.py \
  --claude-dir ~/.claude/agents \
  --copilot-dir ./.github/agents \
  --direction claude-to-copilot \
  --add-argument-hint \
  --verbose
```

### 2. Preview Changes Before Applying

Always a good idea to see what will happen:

```bash
python sync_custom_agents.py \
  --claude-dir ~/.claude/agents \
  --copilot-dir ./.github/agents \
  --dry-run
```

### 3. Regular Sync (Recommended for Automation)

Set this up in a cron job or scheduler:

```bash
python sync_custom_agents.py \
  --claude-dir ~/.claude/agents \
  --copilot-dir ./.github/agents \
  --force
```

The `--force` flag automatically uses the newest file when both are modified.

### 4. Manual Sync with Conflict Resolution

If you want to manually choose which version to keep when there are conflicts:

```bash
python sync_custom_agents.py \
  --claude-dir ~/.claude/agents \
  --copilot-dir ./.github/agents \
  --verbose
```

When conflicts occur, you'll be prompted to choose.

## Directory Structure

### Claude Code Agents
Location: `~/.claude/agents/` (user-level) or `.claude/agents/` (project-level)

Format:
```
~/.claude/agents/
├── planner.md
├── code-reviewer.md
└── debugger.md
```

### GitHub Copilot Agents
Location: `.github/agents/` in your VS Code workspace

Format:
```
.github/agents/
├── planner.agent.md
├── code-reviewer.agent.md
└── debugger.agent.md
```

## File Name Matching

The sync tool matches agents by base name:
- `planner.md` ↔ `planner.agent.md`
- `code-reviewer.md` ↔ `code-reviewer.agent.md`

## What Gets Synced?

✅ **Synced in both directions:**
- Agent name
- Description
- Instructions/body content
- Tools (with format conversion)
- Model (with name mapping)

⚠️ **Dropped when converting Claude → Copilot:**
- `permissionMode` (no Copilot equivalent)
- `skills` (no Copilot equivalent)

⚠️ **Dropped when converting Copilot → Claude:**
- `argument-hint` (no Claude equivalent)
- `handoffs` (no Claude equivalent)
- `target` (no Claude equivalent)
- `mcp-servers` (no Claude equivalent)

## Sync State

The tool maintains state in `~/.agent_sync_state.json` to track:
- Last sync time
- File modification times
- Last sync action

This allows intelligent syncing - only changed files are processed.

## Troubleshooting

### "Directory does not exist"
Create the directories first:
```bash
mkdir -p ~/.claude/agents
mkdir -p .github/agents
```

### Sync state corruption
Delete the state file to reset:
```bash
rm ~/.agent_sync_state.json
```

### Conflicts keep appearing
Use `--force` to automatically resolve, or manually edit files to align them.

## Tips

1. **Start with dry-run**: Always preview changes first
2. **Use version control**: Keep your `.github/agents` in git
4. **Review conversions**: Check converted files for dropped fields
5. **Automate wisely**: Hourly sync is usually sufficient

## Getting Help

View all options:
```bash
python sync_custom_agents.py --help
```

## File Locations

- **Script**: `sync_custom_agents.py`
- **Dependencies**: `requirements.txt`
- **Documentation**: `README.md`
- **Sync State**: `~/.agent_sync_state.json` (created automatically)
