#!/bin/bash

# Source logging utilities
source "$(dirname "$0")/scripts/shell/logging.sh"

# Parse arguments
COMMAND_NAME=""
FORCE_SHELL=""

while [[ "$#" -gt 0 ]]; do
    case $1 in
        --shell) FORCE_SHELL="$2"; shift ;;
        --debug) DEBUG=1 ;;
        -*) log_error "Unknown option: $1"; exit 1 ;;
        *) COMMAND_NAME="$1" ;;
    esac
    shift
done

if [ -z "$COMMAND_NAME" ]; then
    log_error "Usage: $0 <command_name> [--shell zsh|bash] [--debug]"
    exit 1
fi

log_header "Creating New Command: $COMMAND_NAME"

# Determine shell config file
log_step 1 4 "Detecting shell configuration"

if [ -n "$FORCE_SHELL" ]; then
    case "$FORCE_SHELL" in
        "zsh") SHELL_CONFIG="$HOME/.zshrc" ;;
        "bash") SHELL_CONFIG="$HOME/.bashrc" ;;
        *) log_error "Unsupported shell: $FORCE_SHELL"; exit 1 ;;
    esac
    log_info "Using forced shell configuration: $FORCE_SHELL"
else
    if [ -n "$ZSH_VERSION" ] || [ "$SHELL" = "/bin/zsh" ] || [ "$SHELL" = "/usr/bin/zsh" ]; then
        SHELL_CONFIG="$HOME/.zshrc"
    elif [ -n "$BASH_VERSION" ] || [ "$SHELL" = "/bin/bash" ] || [ "$SHELL" = "/usr/bin/bash" ]; then
        SHELL_CONFIG="$HOME/.bashrc"
    else
        if [ -f "$HOME/.zshrc" ]; then
            SHELL_CONFIG="$HOME/.zshrc"
        elif [ -f "$HOME/.bashrc" ]; then
            SHELL_CONFIG="$HOME/.bashrc"
        else
            log_error "Could not determine shell configuration file"
            exit 1
        fi
    fi
fi

log_success "Using shell config: $SHELL_CONFIG"

# Create command script
log_step 2 4 "Creating command script"

SCRIPT_PATH="scripts/${COMMAND_NAME}.py"
if [ -f "$SCRIPT_PATH" ]; then
    log_error "Command script already exists: $SCRIPT_PATH"
    exit 1
fi

cat > "$SCRIPT_PATH" <<EOF
#!/usr/bin/env python3
"""
Command: ${COMMAND_NAME}

Brief Description:
    A new Augments CLI command.
"""

import argparse
from augments.lib.utils import (
    run_fabric_pattern, openai_completion, generate_tts,
    get_desktop_path
)

def main():
    parser = argparse.ArgumentParser(description="Description of ${COMMAND_NAME}")
    parser.add_argument("--example", help="Example argument")
    args = parser.parse_args()
    
    print("This is a placeholder for the ${COMMAND_NAME} command.")

if __name__ == "__main__":
    main()
EOF

chmod +x "$SCRIPT_PATH"
log_success "Created command script: $SCRIPT_PATH"

# Create test file
log_step 3 4 "Creating test file"

TEST_PATH="tests/test_${COMMAND_NAME}.py"
if [ -f "$TEST_PATH" ]; then
    log_warning "Test file already exists: $TEST_PATH"
else
    cat > "$TEST_PATH" <<EOF
import pytest
from scripts.${COMMAND_NAME} import main

def test_${COMMAND_NAME}_basic():
    """Basic test for ${COMMAND_NAME} command."""
    # Add your test cases here
    assert True
EOF
    log_success "Created test file: $TEST_PATH"
fi

# Add alias
log_step 4 4 "Adding shell alias"

CONFIG_DIR="$HOME/.config/augments"
ALIAS_LINE="alias ${COMMAND_NAME}='\$HOME/.config/augments/venv/bin/python \$HOME/.config/augments/scripts/${COMMAND_NAME}.py'"

if grep -q "alias ${COMMAND_NAME}=" "$SHELL_CONFIG"; then
    log_warning "Alias already exists in $SHELL_CONFIG"
else
    echo "$ALIAS_LINE" >> "$SHELL_CONFIG"
    log_success "Added alias to $SHELL_CONFIG"
fi

# Copy script to config directory
mkdir -p "$CONFIG_DIR/scripts"
cp "$SCRIPT_PATH" "$CONFIG_DIR/scripts/"
chmod +x "$CONFIG_DIR/scripts/${COMMAND_NAME}.py"

log_header "Command Creation Complete"
log_info "New command '${COMMAND_NAME}' is ready to use!"
log_info "1. Source your shell config: source $SHELL_CONFIG"
log_info "2. Run the command: ${COMMAND_NAME} --help"
log_info "3. Edit the script at: $SCRIPT_PATH"
log_info "4. Add tests in: $TEST_PATH"