#!/bin/bash

# Parse command line arguments
FORCE_SHELL=""
CLEAN=0

while [[ "$#" -gt 0 ]]; do
    case $1 in
        --shell) FORCE_SHELL="$2"; shift ;;
        --clean) CLEAN=1 ;;
        *) echo "Unknown parameter: $1"; exit 1 ;;
    esac
    shift
done

# Ensure we're inside the correct directory
cd $(dirname $0)

if [ $CLEAN -eq 1 ]; then
    echo "Performing clean reinstall..."
    
    # Remove existing installation
    if [ -d "$HOME/.config/augment" ]; then
        echo "Removing existing installation..."
        rm -rf "$HOME/.config/augment"
    fi
    
    # Remove aliases from shell config
    if [ -n "$FORCE_SHELL" ]; then
        case "$FORCE_SHELL" in
            "zsh") CONFIG="$HOME/.zshrc" ;;
            "bash") CONFIG="$HOME/.bashrc" ;;
            *) echo "Unsupported shell: $FORCE_SHELL"; exit 1 ;;
        esac
    else
        CONFIG="$HOME/.$(basename "$SHELL")rc"
    fi
    
    if [ -f "$CONFIG" ]; then
        echo "Cleaning up aliases from $CONFIG..."
        # Create a temporary file
        TEMP_RC=$(mktemp)
        # Remove our aliases, keeping all other lines
        grep -v "alias youtubeWisdom=" "$CONFIG" | grep -v "alias clipboardAnalyze=" > "$TEMP_RC"
        # Replace the original file
        mv "$TEMP_RC" "$CONFIG"
    fi
    
    echo "Starting fresh installation..."
    ./install.sh ${FORCE_SHELL:+--shell "$FORCE_SHELL"}
    exit 0
fi

# Check if virtual environment exists
if [ ! -d ~/.config/augments/venv ]; then
    echo "Virtual environment not found. Running full install..."
    ./install.sh ${FORCE_SHELL:+--shell "$FORCE_SHELL"}
    exit 0
fi

echo "Updating installation..."

# Activate virtual environment
source ~/.config/augments/venv/bin/activate

# Update pip and reinstall package
python -m pip install --upgrade pip
pip install -e .

# Update scripts
rm -rf ~/.config/augments/scripts
cp -r "$(pwd)/scripts" ~/.config/augments/
chmod +x ~/.config/augments/scripts/*.py

echo "Update complete! Your scripts are now up to date."