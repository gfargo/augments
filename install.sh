#!/bin/bash

# Source logging utilities
source "$(dirname "$0")/scripts/shell/logging.sh"

# Parse command line arguments
FORCE_SHELL=""
while [[ "$#" -gt 0 ]]; do
    case $1 in
    --shell)
        FORCE_SHELL="$2"
        shift
        ;;
    --debug) DEBUG=1 ;;
    *)
        log_error "Unknown parameter: $1"
        exit 1
        ;;
    esac
    shift
done

# Ensure we're inside the correct directory
cd "$(dirname "$0")"

log_header "Installing Augments CLI Tools"
log_info "Version: 0.1.0"
log_detail "Installation directory: $HOME/.config/augments"
echo

# Check prerequisites
start_section "Checking Prerequisites"

# Check Python
log_command "checking python3..."
if command -v python3 >/dev/null 2>&1; then
    python_version=$(python3 --version 2>&1)
    status_line "ok" "$python_version found"
else
    status_line "error" "python3 not found"
    exit 1
fi

# Check pip
log_command "checking pip..."
if command -v pip3 >/dev/null 2>&1; then
    pip_version=$(pip3 --version | awk '{print $2}')
    status_line "ok" "pip $pip_version found"
else
    status_line "error" "pip not found"
    exit 1
fi

# Check venv module
log_command "checking venv module..."
if python3 -c "import venv" >/dev/null 2>&1; then
    status_line "ok" "venv module available"
else
    status_line "error" "python3-venv not found"
    log_detail "Ubuntu/Debian: sudo apt-get install python3-venv"
    log_detail "macOS: brew install python3"
    exit 1
fi

# Check git
log_command "checking git..."
if command -v git >/dev/null 2>&1; then
    git_version=$(git --version | awk '{print $3}')
    status_line "ok" "git $git_version found"
else
    status_line "warning" "git not found (optional)"
fi

end_section

# Set up virtual environment
start_section "Setting Up Virtual Environment"

VENV_PATH="$HOME/.config/augments/venv"
log_detail "Location: $VENV_PATH"

if [ ! -d "$VENV_PATH" ]; then
    log_command "creating new virtual environment..."
    python3 -m venv "$VENV_PATH" &
    show_spinner $! "Creating virtual environment"
    status_line "ok" "Virtual environment created"
else
    log_command "checking existing virtual environment..."
    if [ -f "$VENV_PATH/bin/python" ]; then
        status_line "ok" "Using existing virtual environment"
    else
        status_line "warning" "Virtual environment appears corrupted"
        log_command "recreating virtual environment..."
        rm -rf "$VENV_PATH"
        python3 -m venv "$VENV_PATH" &
        show_spinner $! "Recreating virtual environment"
        status_line "ok" "Virtual environment recreated"
    fi
fi

log_command "activating virtual environment..."
source "$VENV_PATH/bin/activate"
status_line "ok" "Virtual environment activated"

end_section

# Install dependencies
start_section "Installing Dependencies"

# Upgrade pip
log_command "upgrading pip..."
python3 -m pip install --upgrade pip &>/dev/null &
show_spinner $! "Upgrading pip"
status_line "ok" "pip upgraded to $(pip --version | awk '{print $2}')"

# Install project
log_command "installing project in development mode..."
if pip install -e . &>/dev/null; then
    status_line "ok" "Project installed successfully"

    # Show installed packages
    log_detail "Installed packages:"
    pip freeze | grep -v "^-e" | while read package; do
        log_detail "  $package"
    done
else
    status_line "error" "Failed to install project"
    exit 1
fi

end_section

# Set up project structure
start_section "Setting Up Project Structure"

CONFIG_DIR="$HOME/.config/augments"
log_detail "Config directory: $CONFIG_DIR"

# Create directories
log_command "creating directory structure..."
if mkdir -p "$CONFIG_DIR/scripts/custom"; then
    status_line "ok" "Directories created"
else
    status_line "error" "Failed to create directories"
    exit 1
fi

# Copy scripts
log_command "copying scripts..."
rm -rf "$CONFIG_DIR/scripts"
if cp -r "$(pwd)/scripts" "$CONFIG_DIR/"; then
    status_line "ok" "Scripts copied"

    # List installed scripts
    log_detail "Installed scripts:"
    for script in "$CONFIG_DIR/scripts"/*.py; do
        if [ -f "$script" ]; then
            script_name=$(basename "$script")
            script_desc=$(head -n 5 "$script" | grep "Brief Description:" | cut -d: -f2- || echo "No description")
            log_detail "  ${script_name%.*}:${script_desc}"
        fi
    done
else
    status_line "error" "Failed to copy scripts"
    exit 1
fi

# Set permissions
log_command "setting permissions..."
if chmod +x "$CONFIG_DIR/scripts"/*.py; then
    status_line "ok" "Scripts are now executable"
else
    status_line "error" "Failed to set permissions"
    exit 1
fi

end_section

# Configure shell
start_section "Configuring Shell Environment"

# Determine shell config file
log_command "detecting shell configuration..."
if [ -n "$FORCE_SHELL" ]; then
    case "$FORCE_SHELL" in
    "zsh")
        SHELL_CONFIG="$HOME/.zshrc"
        SHELL_NAME="Zsh"
        ;;
    "bash")
        SHELL_CONFIG="$HOME/.bashrc"
        SHELL_NAME="Bash"
        ;;
    *)
        status_line "error" "Unsupported shell: $FORCE_SHELL"
        exit 1
        ;;
    esac
    status_line "ok" "Using forced shell: $SHELL_NAME"
else
    if [ -n "$ZSH_VERSION" ] || [ "$SHELL" = "/bin/zsh" ] || [ "$SHELL" = "/usr/bin/zsh" ]; then
        SHELL_CONFIG="$HOME/.zshrc"
        SHELL_NAME="Zsh"
    elif [ -n "$BASH_VERSION" ] || [ "$SHELL" = "/bin/bash" ] || [ "$SHELL" = "/usr/bin/bash" ]; then
        SHELL_CONFIG="$HOME/.bashrc"
        SHELL_NAME="Bash"
    else
        if [ -f "$HOME/.zshrc" ]; then
            SHELL_CONFIG="$HOME/.zshrc"
            SHELL_NAME="Zsh"
        elif [ -f "$HOME/.bashrc" ]; then
            SHELL_CONFIG="$HOME/.bashrc"
            SHELL_NAME="Bash"
        else
            status_line "error" "Could not determine shell configuration file"
            exit 1
        fi
    fi
    status_line "ok" "Detected shell: $SHELL_NAME"
fi

log_detail "Config file: $SHELL_CONFIG"

# Add aliases
log_command "configuring aliases..."
{
    echo -e "\n# Augments CLI Tools"
    echo "alias youtubeWisdom='\$HOME/.config/augments/venv/bin/python \$HOME/.config/augments/scripts/youtube_wisdom.py'"
    echo "alias clipboardAnalyze='\$HOME/.config/augments/venv/bin/python \$HOME/.config/augments/scripts/clipboard_analyzer.py'"
    echo "alias yt='\$HOME/.config/augments/venv/bin/python \$HOME/.config/augments/scripts/yt.py'"
    echo "alias ezjq='\$HOME/.config/augments/venv/bin/python \$HOME/.config/augments/scripts/ezjq.py'"
    echo "alias forgetThat='\$HOME/.config/augments/venv/bin/python \$HOME/.config/augments/scripts/forget_that.py'"
} >>"$SHELL_CONFIG"

status_line "ok" "Aliases configured"

# List configured aliases
log_detail "Available commands:"
log_detail "  youtubeWisdom - Analyze YouTube videos"
log_detail "  clipboardAnalyze - Process clipboard content"
log_detail "  yt - YouTube utilities (transcript, info, download)"
log_detail "  ezjq - Generate and document jq filters using natural language descriptions"
log_detail "  forgetThat - Removes last shell command from history"

# Try to source the shell configuration
log_command "activating aliases..."
if [ -n "$ZSH_VERSION" ]; then
    if source "$SHELL_CONFIG" 2>/dev/null || . "$SHELL_CONFIG" 2>/dev/null; then
        status_line "ok" "Shell configuration sourced"
    else
        status_line "warning" "Could not automatically source configuration"
    fi
elif [ -n "$BASH_VERSION" ]; then
    if . "$SHELL_CONFIG" 2>/dev/null; then
        status_line "ok" "Shell configuration sourced"
    else
        status_line "warning" "Could not automatically source configuration"
    fi
fi

end_section

# Verify installation
start_section "Verifying Installation"

# Check virtual environment
log_command "checking virtual environment..."
if [ -f "$CONFIG_DIR/venv/bin/python" ]; then
    python_version=$("$CONFIG_DIR/venv/bin/python" --version 2>&1)
    status_line "ok" "Virtual environment: $python_version"
else
    status_line "error" "Virtual environment not installed correctly"
    exit 1
fi

# Check package installation
log_command "checking package installation..."
if "$CONFIG_DIR/venv/bin/pip" list | grep -q "^augments"; then
    package_version=$("$CONFIG_DIR/venv/bin/pip" list | grep "^augments" | awk '{print $2}')
    status_line "ok" "Package installed: v$package_version"
else
    status_line "error" "Package not installed in virtual environment"
    exit 1
fi

# Check shell configuration
log_command "checking shell configuration..."
missing_aliases=()
for alias in "youtubeWisdom" "clipboardAnalyze" "yt"; do
    if ! grep -q "alias $alias=" "$SHELL_CONFIG"; then
        missing_aliases+=("$alias")
    fi
done

if [ ${#missing_aliases[@]} -eq 0 ]; then
    status_line "ok" "All aliases configured correctly"
else
    status_line "error" "Missing aliases: ${missing_aliases[*]}"
    exit 1
fi

# Check command availability
log_command "checking commands..."
for cmd in "youtubeWisdom" "clipboardAnalyze" "yt" "ezjq" "forgetThat"; do
    if type "$cmd" &>/dev/null; then
        status_line "ok" "Command available: $cmd"
    else
        status_line "warning" "Command not available yet: $cmd (restart shell)"
    fi
done

end_section

# Installation Summary
log_header "Installation Complete"

log_subheader "Installation Details"
log_detail "Config Directory: $CONFIG_DIR"
log_detail "Virtual Environment: $CONFIG_DIR/venv"
log_detail "Shell Config: $SHELL_CONFIG"
log_detail "Python Version: $("$CONFIG_DIR/venv/bin/python" --version 2>&1)"
log_detail "Package Version: $("$CONFIG_DIR/venv/bin/pip" list | grep "^augments" | awk '{print $2}')"

log_subheader "Available Commands"
log_detail "youtubeWisdom - Analyze YouTube videos"
log_detail "clipboardAnalyze - Process clipboard content"
log_detail "yt - YouTube utilities (transcript, info, download)"

log_subheader "Next Steps"
log_info "To start using Augments, either:"
log_detail "1. Start a new terminal session, or"
log_detail "2. Run: source $SHELL_CONFIG"

log_subheader "Getting Started"
log_detail "Try these commands:"
log_detail "  yt --help"
log_detail "  youtubeWisdom --help"
log_detail "  clipboardAnalyze --help"
log_detail "  ezjq --help"
log_detail "  forgetThat --help"

echo
