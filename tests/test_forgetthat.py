"""Tests for forgetthat command."""

import os
import tempfile
from unittest.mock import patch

import pytest

from scripts.forget_that import (get_history_file, get_last_command,
                                 remove_last_command)

# Sample history content for different shells
BASH_HISTORY = """ls -la
cd /workspace
git status
python3 script.py
"""

ZSH_HISTORY = """: 1707123456:0;ls -la
: 1707123457:0;cd /workspace
: 1707123458:0;git status
: 1707123459:0;python3 script.py
"""

FISH_HISTORY = """{
    "cmd": "ls -la",
    "when": 1707123456
}
{
    "cmd": "cd /workspace",
    "when": 1707123457
}
{
    "cmd": "git status",
    "when": 1707123458
}
{
    "cmd": "python3 script.py",
    "when": 1707123459
}
"""

@pytest.fixture
def bash_history_file():
    with tempfile.NamedTemporaryFile(mode='w', suffix='.bash_history', delete=False) as f:
        f.write(BASH_HISTORY)
        path = f.name
    yield path
    os.unlink(path)

@pytest.fixture
def zsh_history_file():
    with tempfile.NamedTemporaryFile(mode='w', suffix='.zsh_history', delete=False) as f:
        f.write(ZSH_HISTORY)
        path = f.name
    yield path
    os.unlink(path)

@pytest.fixture
def fish_history_file():
    with tempfile.NamedTemporaryFile(mode='w', suffix='fish_history', delete=False) as f:
        f.write(FISH_HISTORY)
        path = f.name
    yield path
    os.unlink(path)

def test_get_history_file():
    """Test history file detection."""
    # Test with explicit shell
    assert get_history_file('bash').endswith('.bash_history')
    assert get_history_file('zsh').endswith('.zsh_history')
    assert get_history_file('fish').endswith('fish_history')
    
    # Test invalid shell
    assert get_history_file('invalid') is None
    
    # Test auto-detection
    with patch('os.environ', {'SHELL': '/bin/bash'}):
        assert get_history_file().endswith('.bash_history')
    
    with patch('os.environ', {'SHELL': '/usr/bin/zsh'}):
        assert get_history_file().endswith('.zsh_history')

def test_get_last_command_bash(bash_history_file):
    """Test getting last command from bash history."""
    command, error = get_last_command(bash_history_file)
    assert error is None
    assert command == "python3 script.py"

def test_get_last_command_zsh(zsh_history_file):
    """Test getting last command from zsh history."""
    command, error = get_last_command(zsh_history_file)
    assert error is None
    assert command == "python3 script.py"

def test_get_last_command_fish(fish_history_file):
    """Test getting last command from fish history."""
    command, error = get_last_command(fish_history_file)
    assert error is None
    assert command == "python3 script.py"

def test_get_last_command_empty():
    """Test getting last command from empty history."""
    with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
        path = f.name
    
    try:
        command, error = get_last_command(path)
        assert command is None
        assert "empty" in error.lower()
    finally:
        os.unlink(path)

def test_get_last_command_nonexistent():
    """Test getting last command from nonexistent file."""
    command, error = get_last_command("/nonexistent/file")
    assert command is None
    assert "not found" in error.lower()

def test_remove_last_command_bash(bash_history_file):
    """Test removing last command from bash history."""
    # Remove last command
    error = remove_last_command(bash_history_file)
    assert error is None
    
    # Verify removal
    command, _ = get_last_command(bash_history_file)
    assert command == "git status"

def test_remove_last_command_zsh(zsh_history_file):
    """Test removing last command from zsh history."""
    # Remove last command
    error = remove_last_command(zsh_history_file)
    assert error is None
    
    # Verify removal
    command, _ = get_last_command(zsh_history_file)
    assert command == "git status"

def test_remove_last_command_fish(fish_history_file):
    """Test removing last command from fish history."""
    # Remove last command
    error = remove_last_command(fish_history_file)
    assert error is None
    
    # Verify removal
    command, _ = get_last_command(fish_history_file)
    assert command == "git status"

def test_remove_last_command_empty():
    """Test removing last command from empty history."""
    with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
        path = f.name
    
    try:
        error = remove_last_command(path)
        assert "empty" in error.lower()
    finally:
        os.unlink(path)

def test_remove_last_command_nonexistent():
    """Test removing last command from nonexistent file."""
    error = remove_last_command("/nonexistent/file")
    assert "error" in error.lower()
