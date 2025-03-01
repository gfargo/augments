"""Tests for ezjq command."""

import json
import os
import tempfile
from unittest.mock import patch, MagicMock
import pytest

from scripts.ezjq import (
    generate_jq_filter, test_jq_filter, read_json_input,
    generate_markdown, save_markdown
)

# Test data
SAMPLE_JSON = {
    "users": [
        {"id": 1, "name": "Alice", "email": "alice@example.com", "age": 28},
        {"id": 2, "name": "Bob", "email": "bob@example.com", "age": 22},
        {"id": 3, "name": "Charlie", "email": "charlie@example.com", "age": 35}
    ],
    "settings": {
        "theme": "dark",
        "notifications": True
    },
    "metrics": [
        {"endpoint": "/api/users", "response_time": 120, "status": 200},
        {"endpoint": "/api/users", "response_time": 180, "status": 200},
        {"endpoint": "/api/settings", "response_time": 50, "status": 200},
        {"endpoint": "/api/metrics", "response_time": 90, "status": 500}
    ]
}

COMPLEX_JSON = {
    "logs": [
        {"timestamp": "2024-01-01", "level": "ERROR", "message": "Failed to connect"},
        {"timestamp": "2024-01-01", "level": "WARN", "message": "Slow response"},
        {"timestamp": "2024-01-02", "level": "ERROR", "message": "Invalid input"},
        {"timestamp": "2024-01-02", "level": "INFO", "message": "Request processed"}
    ],
    "products": [
        {"id": "P1", "category": "Electronics", "price": 299.99, "stock": 10},
        {"id": "P2", "category": "Books", "price": 19.99, "stock": 50},
        {"id": "P3", "category": "Electronics", "price": 499.99, "stock": 5},
        {"id": "P4", "category": "Books", "price": 29.99, "stock": 20}
    ]
}

@pytest.fixture
def sample_json():
    return json.dumps(SAMPLE_JSON, indent=2)

@pytest.fixture
def complex_json():
    return json.dumps(COMPLEX_JSON, indent=2)

@pytest.fixture
def temp_json_file(sample_json):
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        f.write(sample_json)
        path = f.name
    yield path
    os.unlink(path)

@pytest.fixture
def mock_ollama():
    with patch('scripts.ezjq.OllamaClient') as mock:
        client = MagicMock()
        client.generate.return_value = ".users[].name"
        mock.return_value = client
        yield mock

def test_read_json_input_file(temp_json_file):
    """Test reading JSON from file."""
    data, content = read_json_input(temp_json_file)
    assert data == SAMPLE_JSON
    assert "Alice" in content
    assert "Bob" in content

def test_read_json_input_invalid():
    """Test reading invalid JSON."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        f.write("invalid json")
        path = f.name
    
    try:
        data, content = read_json_input(path)
        assert data is None
        assert content == ""
    finally:
        os.unlink(path)

def test_generate_jq_filter_basic(sample_json, mock_ollama):
    """Test basic filter generation."""
    filter_str = generate_jq_filter(sample_json, "get all user names")
    assert filter_str == ".users[].name"
    mock_ollama.return_value.generate.assert_called_once()

def test_generate_jq_filter_complex_queries(complex_json, mock_ollama):
    """Test complex filter generation."""
    queries = [
        "count errors by level",
        "get products where price > 100",
        "calculate average response time per endpoint",
        "group products by category with total stock"
    ]
    
    for query in queries:
        mock_ollama.return_value.generate.return_value = "test_filter"
        filter_str = generate_jq_filter(complex_json, query)
        assert filter_str is not None
        assert len(filter_str) > 0

def test_test_jq_filter_basic(sample_json):
    """Test basic jq filter validation."""
    # Test valid filters
    valid_filters = [
        ".users[].name",
        ".users[] | select(.age > 25) | .name",
        ".metrics[] | select(.status == 200) | .response_time"
    ]
    for filter_str in valid_filters:
        success, result = test_jq_filter(sample_json, filter_str)
        assert success
        assert result is not None

    # Test invalid filters
    invalid_filters = [
        "invalid[filter",
        ".unknown[].field",
        "]broken[syntax"
    ]
    for filter_str in invalid_filters:
        success, result = test_jq_filter(sample_json, filter_str)
        assert not success

def test_test_jq_filter_complex(complex_json):
    """Test complex jq filter validation."""
    filters = [
        # Group and count
        'group_by(.level) | map({key: .[0].level, count: length})',
        # Filter and transform
        '.products[] | select(.price > 100) | {id, price}',
        # Aggregation
        '.metrics | group_by(.endpoint) | map({endpoint: .[0].endpoint, avg_time: (map(.response_time) | add / length)})'
    ]
    
    for filter_str in filters:
        success, result = test_jq_filter(complex_json, filter_str)
        assert success
        assert result is not None

def test_generate_markdown(sample_json):
    """Test markdown generation."""
    query = "get all user names"
    filter_str = ".users[].name"
    result = '["Alice", "Bob", "Charlie"]'
    
    markdown = generate_markdown(query, filter_str, sample_json, result)
    
    # Check markdown content
    assert "# jq Filter Documentation" in markdown
    assert query in markdown
    assert filter_str in markdown
    assert "Alice" in markdown
    assert "```json" in markdown
    assert "```jq" in markdown

def test_save_markdown():
    """Test markdown file saving."""
    content = "# Test Markdown"
    
    # Test with specific path
    with tempfile.NamedTemporaryFile(suffix='.md', delete=False) as f:
        path = f.name
    
    try:
        saved_path = save_markdown(content, path)
        assert saved_path == path
        with open(path) as f:
            assert f.read() == content
    finally:
        os.unlink(path)
    
    # Test without path (should use desktop or artifacts)
    saved_path = save_markdown(content)
    assert saved_path
    assert saved_path.endswith('.md')
    assert os.path.exists(saved_path)
    os.unlink(saved_path)

def test_end_to_end(sample_json, mock_ollama):
    """Test complete filter generation and testing flow."""
    # Mock the filter generation
    mock_ollama.return_value.generate.return_value = ".users[] | select(.age > 25) | {name, email}"
    
    # Generate filter
    filter_str = generate_jq_filter(sample_json, "get users over 25 with their emails")
    assert filter_str is not None
    
    # Test the filter
    success, result = test_jq_filter(sample_json, filter_str)
    assert success
    assert result is not None
    
    # Verify result contains expected users
    result_data = json.loads(result)
    assert any(user.get('name') == 'Alice' for user in result_data)  # Alice is 28
    assert any(user.get('name') == 'Charlie' for user in result_data)  # Charlie is 35
    assert not any(user.get('name') == 'Bob' for user in result_data)  # Bob is 22

def test_generate_jq_filter(sample_json):
    """Test jq filter generation."""
    # Test extracting names
    filter_str = generate_jq_filter(sample_json, "get all user names")
    assert filter_str is not None
    assert test_jq_filter(sample_json, filter_str)
    
    # Test extracting emails
    filter_str = generate_jq_filter(sample_json, "extract all email addresses")
    assert filter_str is not None
    assert test_jq_filter(sample_json, filter_str)

def test_test_jq_filter(sample_json):
    """Test jq filter validation."""
    # Test valid filter
    assert test_jq_filter(sample_json, ".users[].name")
    
    # Test invalid filter
    assert not test_jq_filter(sample_json, "invalid[filter")

def test_generate_jq_filter_invalid():
    """Test handling of invalid inputs."""
    # Invalid JSON
    filter_str = generate_jq_filter("invalid json", "get names")
    assert filter_str is None
    
    # Empty query
    filter_str = generate_jq_filter("{}", "")
    assert filter_str is None
