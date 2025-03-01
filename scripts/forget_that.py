#!/usr/bin/env python3
"""
Command: forgetthat

Remove the last command from shell history.
Useful for when you accidentally type a command with a typo or sensitive information.

Usage:
    forgetthat [--yes] [--shell SHELL]
    
Examples:
    # Interactive mode (default)
    forgetthat
    
    # Auto-confirm removal
    forgetthat --yes
    
    # Specify shell
    forgetthat --shell zsh
"""

import argparse
import os
import re
import sys
from pathlib import Path
from typing import Optional, Tuple

from augments.lib.progress import LoaderStyle, track_progress


def get_history_file(shell: Optional[str] = None) -> Optional[str]:
    """Get the path to the shell history file."""
    if not shell:
        # Try to detect shell
        shell = os.environ.get('SHELL', '').split('/')[-1]
    
    if not shell:
        return None
    
    home = str(Path.home())
    shell_files = {
        'bash': os.path.join(home, '.bash_history'),
        'zsh': os.path.join(home, '.zsh_history'),
        'fish': os.path.join(home, '.local/share/fish/fish_history')
    }
    
    return shell_files.get(shell.lower())

def get_last_command(history_file: str) -> Tuple[Optional[str], Optional[str]]:
    """Get the last command from history file."""
    try:
        if not os.path.exists(history_file):
            return None, "History file not found"
        
        with open(history_file, 'r') as f:
            lines = f.readlines()
            
        if not lines:
            return None, "History is empty"
        
        # Different shells have different formats
        if history_file.endswith('zsh_history'):
            # ZSH format: ": timestamp:0;command"
            commands = []
            for line in reversed(lines):
                if match := re.search(r';\s*(.+)$', line):
                    commands.append(match.group(1).strip())
                    if len(commands) >= 2:  # Get second-to-last command
                        return commands[1], None
            return commands[0] if commands else None, "Only one command in history"
        elif history_file.endswith('fish_history'):
            # Fish format: JSON-like format
            commands = []
            for line in reversed(lines):
                if '"cmd"' in line and (match := re.search(r'"cmd"\s*:\s*"(.+?)"', line)):
                    commands.append(match.group(1).strip())
                    if len(commands) >= 2:  # Get second-to-last command
                        return commands[1], None
            return commands[0] if commands else None, "Only one command in history"
        else:
            # Bash and others: simple line format
            commands = [line.strip() for line in reversed(lines) if line.strip()]
            if len(commands) >= 2:
                return commands[1], None
        return None, "No commands found in history"
        
    except Exception as e:
        return None, f"Error reading history: {e}"

def remove_last_command(history_file: str) -> Optional[str]:
    """Remove the last command from history file."""
    try:
        with open(history_file, 'r') as f:
            lines = f.readlines()
        
        if not lines:
            return "History is empty"
        
        # Remove last non-empty line
        while lines and not lines[-1].strip():
            lines.pop()
            
        if lines:
            lines.pop()
            
            # Write back
            with open(history_file, 'w') as f:
                f.writelines(lines)
            
            return None
        
        return "No commands to remove"
        
    except Exception as e:
        return f"Error removing command: {e}"

def main():
    parser = argparse.ArgumentParser(
        description="Remove the last command from shell history",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Interactive mode (default)
    forgetthat
    
    # Auto-confirm removal
    forgetthat --yes
    
    # Specify shell
    forgetthat --shell zsh
        """
    )
    
    parser.add_argument("--yes", "-y", action="store_true",
                      help="Auto-confirm command removal")
    parser.add_argument("--shell", "-s",
                      help="Specify shell (bash, zsh, fish)")
    
    args = parser.parse_args()
    
    # Get history file
    with track_progress("Detecting shell", LoaderStyle.DOTS):
        history_file = get_history_file(args.shell)
        if not history_file:
            print("❌ Could not detect shell or find history file", file=sys.stderr)
            return 1
    
    # Get last command
    with track_progress("Reading history", LoaderStyle.PULSE):
        command, error = get_last_command(history_file)
        if error:
            print(f"❌ {error}", file=sys.stderr)
            return 1
    
    # Show command and confirm
    print(f"\nLast command: {command}")
    
    if not args.yes:
        response = input("\nRemove this command? [y/N] ").lower()
        if response not in ('y', 'yes'):
            print("Operation cancelled.")
            return 0
    
    # Remove command
    with track_progress("Removing command", LoaderStyle.BAR):
        error = remove_last_command(history_file)
        if error:
            print(f"❌ {error}", file=sys.stderr)
            return 1
    
    print("✨ Command removed from history!")
    return 0

if __name__ == "__main__":
    sys.exit(main())
