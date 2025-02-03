import pytest
import os
import time
from augments.lib.utils import (
    sanitize_filename, format_duration, format_date,
    get_unique_filename, extract_urls, extract_code_blocks,
    get_artifact_path, parse_duration
)

# Test sanitize_filename
@pytest.mark.parametrize("input,expected", [
    ("hello world", "hello_world"),
    ("file/with\\invalid:chars", "filewithinvalidchars"),
    ("..hidden", "hidden"),
    ("a" * 300, "a" * 255),  # Test length limit
    ("file.txt", "file.txt"),  # Test normal filename
    ("file?.txt", "file.txt"),  # Test invalid chars
    ("", ""),  # Test empty string
])
def test_sanitize_filename(input, expected):
    assert sanitize_filename(input) == expected

# Test format_duration
@pytest.mark.parametrize("seconds,expected", [
    (0, "00:00:00"),
    (61, "00:01:01"),
    (3661, "01:01:01"),
    (7322, "02:02:02"),
    (86399, "23:59:59"),  # Test near day boundary
    (86400, "24:00:00"),  # Test exact day
    (-1, "00:00:00"),  # Test negative (should handle gracefully)
])
def test_format_duration(seconds, expected):
    assert format_duration(seconds) == expected

# Test format_date
@pytest.mark.parametrize("date_str,input_format,output_format,expected", [
    ("20240101", "%Y%m%d", "%Y-%m-%d", "2024-01-01"),
    ("2024-01-01", "%Y-%m-%d", "%d/%m/%Y", "01/01/2024"),
    ("invalid", "%Y%m%d", "%Y-%m-%d", "invalid"),  # Test invalid date
])
def test_format_date(date_str, input_format, output_format, expected):
    assert format_date(date_str, input_format, output_format) == expected

# Test extract_urls
@pytest.mark.parametrize("text,expected", [
    (
        "Check out https://example.com and http://test.com",
        ["https://example.com", "http://test.com"]
    ),
    (
        "No URLs here",
        []
    ),
    (
        "Multiple http://url.com/path?q=1 on http://different.com/lines\nhttp://another.com",
        ["http://url.com/path?q=1", "http://different.com/lines", "http://another.com"]
    ),
    (
        "Invalid: htp://wrong.com",
        []
    ),
])
def test_extract_urls(text, expected):
    assert extract_urls(text) == expected

# Test extract_code_blocks
@pytest.mark.parametrize("text,expected", [
    (
        "```python\nprint('hello')\n```",
        [("python", "print('hello')")]
    ),
    (
        "```\nno language\n```",
        [("text", "no language")]
    ),
    (
        "    indented code\n    block here",
        [("text", "indented code\nblock here")]
    ),
    (
        "Mixed:\n```python\ndef test():\n    pass\n```\n    indented\n    block",
        [("python", "def test():\n    pass"), ("text", "indented\nblock")]
    ),
    (
        "No code blocks here",
        []
    ),
])
def test_extract_code_blocks(text, expected):
    assert extract_code_blocks(text) == expected

# Test get_artifact_path
def test_get_artifact_path():
    # Test basic path construction
    path = get_artifact_path("transcripts", "test.txt")
    assert path.endswith("/transcripts/test.txt")
    assert "/.config/augments/artifacts/" in path
    
    # Test with unsafe filename
    path = get_artifact_path("downloads", "unsafe/../../file.txt")
    assert "../" not in path
    assert "unsafe" in path
    assert path.endswith(".txt")

# Test parse_duration
@pytest.mark.parametrize("duration,expected", [
    ("7d", 7 * 24 * 60 * 60),
    ("24h", 24 * 60 * 60),
    ("60m", 60 * 60),
    ("30s", 30),
    ("0d", 0),
    ("invalid", None),
    ("10x", None),
    ("", None),
    (None, None),
])
def test_parse_duration(duration, expected):
    assert parse_duration(duration) == expected

# Test get_unique_filename (requires temporary directory)
def test_get_unique_filename(tmp_path):
    # Test basic unique filename
    first_file = tmp_path / "test.txt"
    first_file.write_text("content")
    
    unique = get_unique_filename(str(first_file))
    assert unique.endswith("_1.txt")
    
    # Test multiple files
    second_file = tmp_path / "test_1.txt"
    second_file.write_text("content")
    
    unique = get_unique_filename(str(first_file))
    assert unique.endswith("_2.txt")