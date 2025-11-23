#!/usr/bin/env python3
"""
Sync custom agents between Claude Code and GitHub Copilot.

This script synchronizes agent definitions between Claude Code (.md) and 
GitHub Copilot (.agent.md) formats, handling conversions and tracking 
changes to maintain consistency across both systems.
"""

import argparse
import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

try:
    import yaml
except ImportError:
    print("Error: PyYAML is required. Install with: pip install pyyaml")
    sys.exit(1)


class AgentSyncError(Exception):
    """Base exception for agent sync operations."""
    pass


class SyncState:
    """Manages sync state tracking in ~/.agent_sync_state.json"""
    
    def __init__(self, state_file: Path = Path.home() / ".agent_sync_state.json"):
        self.state_file = state_file
        self.state = self._load_state()
    
    def _load_state(self) -> Dict:
        """Load sync state from file."""
        if self.state_file.exists():
            try:
                with open(self.state_file, 'r') as f:
                    return json.load(f)
            except json.JSONDecodeError:
                return {"sync_pairs": {}}
        return {"sync_pairs": {}}
    
    def save_state(self):
        """Save sync state to file."""
        with open(self.state_file, 'w') as f:
            json.dump(self.state, f, indent=2)
    
    def get_pair_key(self, claude_dir: Path, copilot_dir: Path) -> str:
        """Generate unique key for sync pair."""
        return f"{claude_dir.resolve()}|{copilot_dir.resolve()}"
    
    def get_pair_state(self, claude_dir: Path, copilot_dir: Path) -> Dict:
        """Get state for specific sync pair."""
        key = self.get_pair_key(claude_dir, copilot_dir)
        if key not in self.state["sync_pairs"]:
            self.state["sync_pairs"][key] = {
                "last_sync": None,
                "files": {}
            }
        return self.state["sync_pairs"][key]
    
    def update_file_state(self, claude_dir: Path, copilot_dir: Path, 
                         agent_name: str, claude_mtime: Optional[float],
                         copilot_mtime: Optional[float], action: str):
        """Update state for a specific file."""
        pair_state = self.get_pair_state(claude_dir, copilot_dir)
        pair_state["files"][agent_name] = {
            "claude_mtime": claude_mtime,
            "copilot_mtime": copilot_mtime,
            "last_action": action,
            "last_sync_time": datetime.now().isoformat()
        }
        pair_state["last_sync"] = datetime.now().isoformat()
    
    def get_file_state(self, claude_dir: Path, copilot_dir: Path, 
                       agent_name: str) -> Optional[Dict]:
        """Get state for a specific file."""
        pair_state = self.get_pair_state(claude_dir, copilot_dir)
        return pair_state["files"].get(agent_name)
    
    def remove_file_state(self, claude_dir: Path, copilot_dir: Path, agent_name: str):
        """Remove state for a specific file."""
        pair_state = self.get_pair_state(claude_dir, copilot_dir)
        if agent_name in pair_state["files"]:
            del pair_state["files"][agent_name]


class AgentConverter:
    """Handles conversion between Claude Code and GitHub Copilot agent formats."""
    
    # Model mappings
    CLAUDE_TO_COPILOT_MODELS = {
        'sonnet': 'Claude Sonnet 4',
        'opus': 'Claude Opus 4',
        'haiku': 'Claude Haiku 4',
        'inherit': None
    }
    
    COPILOT_TO_CLAUDE_MODELS = {
        'claude sonnet 4': 'sonnet',
        'claude opus 4': 'opus',
        'claude haiku 4': 'haiku'
    }
    
    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        self.warnings: List[str] = []
    
    def log(self, message: str):
        """Log verbose message."""
        if self.verbose:
            print(f"  {message}")
    
    def parse_agent_file(self, content: str) -> Tuple[Dict, str]:
        """Parse agent file into frontmatter and body."""
        match = re.match(r'^---\n(.*?)\n---\n(.*)$', content, re.DOTALL)
        if not match:
            raise AgentSyncError("No YAML frontmatter found in agent file")
        
        yaml_content, body = match.groups()
        try:
            frontmatter = yaml.safe_load(yaml_content)
            return frontmatter, body.strip()
        except yaml.YAMLError as e:
            raise AgentSyncError(f"Failed to parse YAML frontmatter: {e}")
    
    def claude_to_copilot(self, content: str, add_argument_hint: bool = False,
                          add_handoffs: bool = False) -> str:
        """Convert Claude Code agent to GitHub Copilot format."""
        self.warnings = []
        claude_agent, body = self.parse_agent_file(content)
        copilot_agent = {}
        
        # Map name
        if 'name' in claude_agent:
            copilot_agent['name'] = claude_agent['name']
            self.log(f"Mapped name: {claude_agent['name']}")
        
        # Map description
        if 'description' in claude_agent:
            copilot_agent['description'] = claude_agent['description']
            self.log("Mapped description")
            
            if add_argument_hint:
                copilot_agent['argument-hint'] = claude_agent['description']
                self.log("Added argument-hint from description")
        
        # Convert tools
        if 'tools' in claude_agent:
            if isinstance(claude_agent['tools'], str):
                copilot_agent['tools'] = [t.strip() for t in claude_agent['tools'].split(',') if t.strip()]
                self.log(f"Converted tools: string → array ({len(copilot_agent['tools'])} tools)")
            elif isinstance(claude_agent['tools'], list):
                copilot_agent['tools'] = claude_agent['tools']
                self.log(f"Tools already in array format ({len(copilot_agent['tools'])} tools)")
        
        # Map model
        if 'model' in claude_agent:
            model_key = claude_agent['model'].lower()
            mapped_model = self.CLAUDE_TO_COPILOT_MODELS.get(model_key, claude_agent['model'])
            if mapped_model:
                copilot_agent['model'] = mapped_model
                self.log(f"Mapped model: {claude_agent['model']} → {mapped_model}")
            else:
                self.log(f"Model set to 'inherit' - will use current model picker selection")
        
        # Add target
        copilot_agent['target'] = 'vscode'
        self.log("Set target: vscode")
        
        # Add handoffs if requested
        if add_handoffs:
            copilot_agent['handoffs'] = [
                {
                    'label': 'Next Step',
                    'agent': 'agent',
                    'prompt': 'Continue with the next step',
                    'send': False
                }
            ]
            self.log("Added handoffs placeholder")
        
        # Note dropped fields
        if 'permissionMode' in claude_agent:
            self.warnings.append(f"Dropped unsupported field: permissionMode={claude_agent['permissionMode']}")
        if 'skills' in claude_agent:
            self.warnings.append(f"Dropped unsupported field: skills={claude_agent['skills']}")
        
        # Generate output
        yaml_output = yaml.dump(copilot_agent, default_flow_style=False, sort_keys=False)
        return f"---\n{yaml_output}---\n{body}\n"
    
    def copilot_to_claude(self, content: str) -> str:
        """Convert GitHub Copilot agent to Claude Code format."""
        self.warnings = []
        copilot_agent, body = self.parse_agent_file(content)
        claude_agent = {}
        
        # Map name
        if 'name' in copilot_agent:
            claude_agent['name'] = copilot_agent['name']
            self.log(f"Mapped name: {copilot_agent['name']}")
        
        # Map description
        if 'description' in copilot_agent:
            claude_agent['description'] = copilot_agent['description']
            self.log("Mapped description")
        
        # Convert tools
        if 'tools' in copilot_agent:
            if isinstance(copilot_agent['tools'], list):
                claude_agent['tools'] = ', '.join(copilot_agent['tools'])
                self.log(f"Converted tools: array → string ({len(copilot_agent['tools'])} tools)")
            elif isinstance(copilot_agent['tools'], str):
                claude_agent['tools'] = copilot_agent['tools']
                self.log("Tools already in string format")
        
        # Map model
        if 'model' in copilot_agent:
            model_key = copilot_agent['model'].lower()
            mapped_model = self.COPILOT_TO_CLAUDE_MODELS.get(model_key, copilot_agent['model'])
            claude_agent['model'] = mapped_model
            self.log(f"Mapped model: {copilot_agent['model']} → {mapped_model}")
        
        # Note dropped fields
        dropped_fields = []
        if 'argument-hint' in copilot_agent:
            dropped_fields.append('argument-hint')
        if 'handoffs' in copilot_agent:
            dropped_fields.append('handoffs')
        if 'target' in copilot_agent:
            dropped_fields.append('target')
        if 'mcp-servers' in copilot_agent:
            dropped_fields.append('mcp-servers')
        
        if dropped_fields:
            self.warnings.append(f"Dropped Copilot-specific fields: {', '.join(dropped_fields)}")
        
        # Generate output
        yaml_output = yaml.dump(claude_agent, default_flow_style=False, sort_keys=False)
        return f"---\n{yaml_output}---\n{body}\n"


class AgentSyncer:
    """Main sync orchestration class."""
    
    def __init__(self, claude_dir: Path, copilot_dir: Path, 
                 direction: str = 'both', dry_run: bool = False,
                 force: bool = False, verbose: bool = False,
                 add_argument_hint: bool = False, add_handoffs: bool = False):
        self.claude_dir = claude_dir
        self.copilot_dir = copilot_dir
        self.direction = direction
        self.dry_run = dry_run
        self.force = force
        self.verbose = verbose
        self.add_argument_hint = add_argument_hint
        self.add_handoffs = add_handoffs
        
        self.converter = AgentConverter(verbose=verbose)
        self.state = SyncState()
        
        self.stats = {
            'claude_to_copilot': 0,
            'copilot_to_claude': 0,
            'deletions': 0,
            'conflicts': 0,
            'skipped': 0,
            'errors': 0
        }
    
    def validate_directories(self):
        """Validate that directories exist and are accessible."""
        if not self.claude_dir.exists():
            raise AgentSyncError(f"Claude directory does not exist: {self.claude_dir}")
        if not self.claude_dir.is_dir():
            raise AgentSyncError(f"Claude path is not a directory: {self.claude_dir}")
        
        if not self.copilot_dir.exists():
            raise AgentSyncError(f"Copilot directory does not exist: {self.copilot_dir}")
        if not self.copilot_dir.is_dir():
            raise AgentSyncError(f"Copilot path is not a directory: {self.copilot_dir}")
    
    def get_agent_pairs(self) -> Dict[str, Dict]:
        """Get all agent file pairs by matching base names."""
        pairs = {}
        
        # Find all Claude agents
        for claude_file in self.claude_dir.glob("*.md"):
            base_name = claude_file.stem
            pairs[base_name] = {
                'claude': claude_file,
                'copilot': None,
                'claude_mtime': claude_file.stat().st_mtime
            }
        
        # Find all Copilot agents
        for copilot_file in self.copilot_dir.glob("*.agent.md"):
            base_name = copilot_file.stem.replace('.agent', '')
            if base_name not in pairs:
                pairs[base_name] = {
                    'claude': None,
                    'copilot': copilot_file,
                    'copilot_mtime': copilot_file.stat().st_mtime
                }
            else:
                pairs[base_name]['copilot'] = copilot_file
                pairs[base_name]['copilot_mtime'] = copilot_file.stat().st_mtime
        
        return pairs
    
    def should_sync(self, agent_name: str, claude_file: Optional[Path], 
                   copilot_file: Optional[Path], claude_mtime: Optional[float],
                   copilot_mtime: Optional[float]) -> Tuple[Optional[str], str]:
        """
        Determine sync action needed.
        
        Returns:
            Tuple of (action, reason) where action is one of:
            'claude_to_copilot', 'copilot_to_claude', 'conflict', 'delete_copilot', 
            'delete_claude', 'skip'
        """
        file_state = self.state.get_file_state(self.claude_dir, self.copilot_dir, agent_name)
        
        # New file cases
        if claude_file and not copilot_file:
            if self.direction in ['claude-to-copilot', 'both']:
                return 'claude_to_copilot', 'New Claude agent'
            else:
                return 'skip', 'Direction does not include Claude→Copilot'
        
        if copilot_file and not claude_file:
            if self.direction in ['copilot-to-claude', 'both']:
                return 'copilot_to_claude', 'New Copilot agent'
            else:
                return 'skip', 'Direction does not include Copilot→Claude'
        
        # Deletion cases
        if not claude_file and file_state and file_state.get('claude_mtime'):
            if self.direction in ['claude-to-copilot', 'both']:
                return 'delete_copilot', 'Claude agent deleted'
            else:
                return 'skip', 'Direction does not include Claude→Copilot'
        
        if not copilot_file and file_state and file_state.get('copilot_mtime'):
            if self.direction in ['copilot-to-claude', 'both']:
                return 'delete_claude', 'Copilot agent deleted'
            else:
                return 'skip', 'Direction does not include Copilot→Claude'
        
        # Both files exist - check for changes
        if not file_state:
            # First sync - use newest file
            if claude_mtime > copilot_mtime:
                if self.direction in ['claude-to-copilot', 'both']:
                    return 'claude_to_copilot', 'First sync - Claude is newer'
                else:
                    return 'skip', 'Direction does not include Claude→Copilot'
            elif copilot_mtime > claude_mtime:
                if self.direction in ['copilot-to-claude', 'both']:
                    return 'copilot_to_claude', 'First sync - Copilot is newer'
                else:
                    return 'skip', 'Direction does not include Copilot→Claude'
            else:
                return 'skip', 'Files have same modification time'
        
        # Check if files changed since last sync
        last_claude_mtime = file_state.get('claude_mtime')
        last_copilot_mtime = file_state.get('copilot_mtime')
        
        claude_changed = last_claude_mtime is None or claude_mtime > last_claude_mtime
        copilot_changed = last_copilot_mtime is None or copilot_mtime > last_copilot_mtime
        
        if claude_changed and copilot_changed:
            # Both changed - conflict
            return 'conflict', 'Both files modified since last sync'
        
        if claude_changed:
            if self.direction in ['claude-to-copilot', 'both']:
                return 'claude_to_copilot', 'Claude agent modified'
            else:
                return 'skip', 'Direction does not include Claude→Copilot'
        
        if copilot_changed:
            if self.direction in ['copilot-to-claude', 'both']:
                return 'copilot_to_claude', 'Copilot agent modified'
            else:
                return 'skip', 'Direction does not include Copilot→Claude'
        
        return 'skip', 'No changes detected'
    
    def resolve_conflict(self, agent_name: str, claude_file: Path, 
                        copilot_file: Path, claude_mtime: float,
                        copilot_mtime: float) -> Optional[str]:
        """
        Resolve sync conflict.
        
        Returns:
            'claude_to_copilot', 'copilot_to_claude', or None (cancel)
        """
        if self.force:
            # Use newest file
            if claude_mtime > copilot_mtime:
                print(f"  Conflict resolved (--force): Using Claude version (newer)")
                return 'claude_to_copilot'
            else:
                print(f"  Conflict resolved (--force): Using Copilot version (newer)")
                return 'copilot_to_claude'
        
        # Prompt user
        print(f"\n⚠️  CONFLICT: Both files modified for agent '{agent_name}'")
        print(f"  Claude:  {claude_file} (modified: {datetime.fromtimestamp(claude_mtime)})")
        print(f"  Copilot: {copilot_file} (modified: {datetime.fromtimestamp(copilot_mtime)})")
        print("\nChoose action:")
        print("  1. Use Claude version (Claude → Copilot)")
        print("  2. Use Copilot version (Copilot → Claude)")
        print("  3. Skip this agent")
        
        while True:
            choice = input("Enter choice (1/2/3): ").strip()
            if choice == '1':
                return 'claude_to_copilot'
            elif choice == '2':
                return 'copilot_to_claude'
            elif choice == '3':
                return None
            else:
                print("Invalid choice. Please enter 1, 2, or 3.")
    
    def sync_agent(self, agent_name: str, action: str, 
                   claude_file: Optional[Path], copilot_file: Optional[Path],
                   claude_mtime: Optional[float], copilot_mtime: Optional[float]):
        """Perform sync action for a single agent."""
        try:
            if action == 'claude_to_copilot':
                if not copilot_file:
                    copilot_file = self.copilot_dir / f"{agent_name}.agent.md"
                
                with open(claude_file, 'r') as f:
                    content = f.read()
                
                converted = self.converter.claude_to_copilot(
                    content, 
                    add_argument_hint=self.add_argument_hint,
                    add_handoffs=self.add_handoffs
                )
                
                if not self.dry_run:
                    with open(copilot_file, 'w') as f:
                        f.write(converted)
                    # Update copilot mtime after writing
                    copilot_mtime = copilot_file.stat().st_mtime
                
                self.stats['claude_to_copilot'] += 1
                
                for warning in self.converter.warnings:
                    print(f"    ⚠️  {warning}")
            
            elif action == 'copilot_to_claude':
                if not claude_file:
                    claude_file = self.claude_dir / f"{agent_name}.md"
                
                with open(copilot_file, 'r') as f:
                    content = f.read()
                
                converted = self.converter.copilot_to_claude(content)
                
                if not self.dry_run:
                    with open(claude_file, 'w') as f:
                        f.write(converted)
                    # Update claude mtime after writing
                    claude_mtime = claude_file.stat().st_mtime
                
                self.stats['copilot_to_claude'] += 1
                
                for warning in self.converter.warnings:
                    print(f"    ⚠️  {warning}")
            
            elif action == 'delete_copilot':
                if not self.dry_run and copilot_file and copilot_file.exists():
                    copilot_file.unlink()
                    copilot_mtime = None
                self.stats['deletions'] += 1
            
            elif action == 'delete_claude':
                if not self.dry_run and claude_file and claude_file.exists():
                    claude_file.unlink()
                    claude_mtime = None
                self.stats['deletions'] += 1
            
            # Update state
            if not self.dry_run:
                if action.startswith('delete'):
                    if action == 'delete_copilot' or action == 'delete_claude':
                        self.state.remove_file_state(self.claude_dir, self.copilot_dir, agent_name)
                else:
                    self.state.update_file_state(
                        self.claude_dir, self.copilot_dir, agent_name,
                        claude_mtime, copilot_mtime, action
                    )
        
        except Exception as e:
            print(f"    ❌ Error: {e}")
            self.stats['errors'] += 1
    
    def sync(self):
        """Main sync operation."""
        print(f"🔄 Syncing agents: {self.direction}")
        print(f"   Claude:  {self.claude_dir}")
        print(f"   Copilot: {self.copilot_dir}")
        if self.dry_run:
            print("   Mode: DRY RUN (no changes will be made)")
        print()
        
        pairs = self.get_agent_pairs()
        
        if not pairs:
            print("No agents found in either directory.")
            return
        
        for agent_name, pair in sorted(pairs.items()):
            claude_file = pair.get('claude')
            copilot_file = pair.get('copilot')
            claude_mtime = pair.get('claude_mtime')
            copilot_mtime = pair.get('copilot_mtime')
            
            action, reason = self.should_sync(
                agent_name, claude_file, copilot_file, 
                claude_mtime, copilot_mtime
            )
            
            if action == 'skip':
                if self.verbose:
                    print(f"⏭️  {agent_name}: {reason}")
                self.stats['skipped'] += 1
                continue
            
            # Handle conflicts
            if action == 'conflict':
                self.stats['conflicts'] += 1
                resolved_action = self.resolve_conflict(
                    agent_name, claude_file, copilot_file,
                    claude_mtime, copilot_mtime
                )
                if not resolved_action:
                    print(f"⏭️  {agent_name}: Skipped by user")
                    self.stats['skipped'] += 1
                    continue
                action = resolved_action
            
            # Display action
            action_symbols = {
                'claude_to_copilot': '→',
                'copilot_to_claude': '←',
                'delete_copilot': '🗑️',
                'delete_claude': '🗑️'
            }
            symbol = action_symbols.get(action, '•')
            
            action_descriptions = {
                'claude_to_copilot': 'Claude → Copilot',
                'copilot_to_claude': 'Copilot → Claude',
                'delete_copilot': 'Delete Copilot agent',
                'delete_claude': 'Delete Claude agent'
            }
            description = action_descriptions.get(action, action)
            
            print(f"{symbol} {agent_name}: {description} ({reason})")
            
            # Perform sync
            self.sync_agent(agent_name, action, claude_file, copilot_file, 
                          claude_mtime, copilot_mtime)
        
        # Save state
        if not self.dry_run:
            self.state.save_state()
        
        # Print summary
        print("\n" + "="*60)
        print("Summary:")
        print(f"  Claude → Copilot: {self.stats['claude_to_copilot']}")
        print(f"  Copilot → Claude: {self.stats['copilot_to_claude']}")
        print(f"  Deletions:        {self.stats['deletions']}")
        print(f"  Conflicts:        {self.stats['conflicts']}")
        print(f"  Skipped:          {self.stats['skipped']}")
        print(f"  Errors:           {self.stats['errors']}")
        print("="*60)
        
        if self.dry_run:
            print("\n💡 This was a dry run. Use without --dry-run to apply changes.")


def main():
    parser = argparse.ArgumentParser(
        description='Sync custom agents between Claude Code and GitHub Copilot',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Initial migration (Claude → Copilot)
  %(prog)s --claude-dir ~/.claude/agents --copilot-dir ./.github/agents --direction claude-to-copilot
  
  # Bidirectional sync (default)
  %(prog)s --claude-dir ~/.claude/agents --copilot-dir ./.github/agents --force --verbose
  
  # Dry run to preview changes
  %(prog)s --claude-dir ~/.claude/agents --copilot-dir ./.github/agents --dry-run
        """
    )
    
    parser.add_argument(
        '--claude-dir',
        type=Path,
        required=True,
        help='Path to Claude Code agents directory'
    )
    
    parser.add_argument(
        '--copilot-dir',
        type=Path,
        required=True,
        help='Path to GitHub Copilot agents directory'
    )
    
    parser.add_argument(
        '--direction',
        choices=['claude-to-copilot', 'copilot-to-claude', 'both'],
        default='both',
        help='Sync direction (default: both)'
    )
    
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what would be done without making changes'
    )
    
    parser.add_argument(
        '--force',
        action='store_true',
        help='Auto-resolve conflicts using newest file'
    )
    
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Verbose output'
    )
    
    parser.add_argument(
        '--add-argument-hint',
        action='store_true',
        help='Add argument-hint field when converting Claude → Copilot (uses description)'
    )
    
    parser.add_argument(
        '--add-handoffs',
        action='store_true',
        help='Add handoffs placeholder when converting Claude → Copilot'
    )
    
    args = parser.parse_args()
    
    # Validate argument combinations
    if args.direction == 'copilot-to-claude':
        if args.add_argument_hint or args.add_handoffs:
            print("Warning: --add-argument-hint and --add-handoffs are ignored for copilot-to-claude direction")
    
    try:
        syncer = AgentSyncer(
            claude_dir=args.claude_dir,
            copilot_dir=args.copilot_dir,
            direction=args.direction,
            dry_run=args.dry_run,
            force=args.force,
            verbose=args.verbose,
            add_argument_hint=args.add_argument_hint,
            add_handoffs=args.add_handoffs
        )
        
        syncer.validate_directories()
        syncer.sync()
        
        sys.exit(0 if syncer.stats['errors'] == 0 else 1)
    
    except AgentSyncError as e:
        print(f"❌ Error: {e}", file=sys.stderr)
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user")
        sys.exit(130)
    except Exception as e:
        print(f"❌ Unexpected error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
