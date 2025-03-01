#!/usr/bin/env python3
"""
Command: ezjq

Generate and document jq filters using natural language descriptions.
Uses LLM to understand the desired transformation and generate the appropriate jq filter.
Creates a markdown document with the filter, example data, and results.

Usage:
    ezjq [--file FILE] [--query QUERY] [--output OUTPUT]
    ezjq --interactive
    
Examples:
    # Generate filter and save documentation
    ezjq --file data.json --query "get all user names" --output filter.md
    
    # Interactive mode with automatic output
    ezjq --interactive
    
    # Read JSON from stdin and specify output
    cat data.json | ezjq --query "extract emails" --output result.md
    
    # Complex transformations
    ezjq --file data.json --query "get users where age > 25 and group by city"
    ezjq --file logs.json --query "count errors by severity and sort by count"
    ezjq --file metrics.json --query "calculate average response time per endpoint"
"""

import argparse
import json
import os
import sys
import time
from datetime import datetime
from typing import Optional, Dict, Any, Tuple, List

from augments.lib.llm import OllamaClient, ModelType
from augments.lib.utils import (
    run_command, get_desktop_path, save_artifact,
    sanitize_filename
)
from augments.lib.progress import track_progress, LoaderStyle

def read_json_input(file: Optional[str] = None) -> Tuple[Optional[Dict[Any, Any]], str]:
    """Read JSON input from file or stdin."""
    with track_progress("Reading JSON input", LoaderStyle.DOTS):
        try:
            if file:
                with open(file, 'r') as f:
                    content = f.read()
                    data = json.loads(content)
                    return data, content
            else:
                if sys.stdin.isatty():
                    return None, ""
                content = sys.stdin.read()
                data = json.loads(content)
                return data, content
        except json.JSONDecodeError as e:
            print(f"❌ Error: Invalid JSON input - {e}", file=sys.stderr)
            return None, ""
        except Exception as e:
            print(f"❌ Error reading input: {e}", file=sys.stderr)
            return None, ""

def generate_jq_filter(json_str: str, query: str) -> Optional[str]:
    """Generate a jq filter using LLM."""
    with track_progress("Generating jq filter", LoaderStyle.PULSE):
        try:
            # Initialize Ollama client with code-focused model
            client = OllamaClient(model=ModelType.CODE.value)
            
            # Prepare prompt with examples
            prompt = f"""Given this JSON content:
```json
{json_str}
```

Generate a jq filter to: {query}

Here are some example transformations:
1. Get all names: .[]?.name
2. Extract emails: [.[].email]
3. Count items by type: group_by(.type) | map({{key: .[0].type, count: length}})
4. Filter and transform: map(select(.age > 25) | {{name, city}})
5. Calculate averages: [.[].value] | add / length
6. Complex grouping: group_by(.category) | map({{category: .[0].category, items: map(.name)}})

Requirements:
1. Return ONLY the jq filter, nothing else
2. The filter must be valid jq syntax
3. Do not include backticks or quotes around the filter
4. Keep the filter as simple as possible while meeting the requirements
5. Handle potential null values safely

jq filter:"""

            # Generate filter
            response = client.generate(prompt)
            if not response:
                return None
                
            # Clean up response
            filter_str = response.strip().strip('`').strip()
            return filter_str
            
        except Exception as e:
            print(f"❌ Error generating filter: {e}", file=sys.stderr)
            return None

def test_jq_filter(json_str: str, filter_str: str) -> Tuple[bool, Optional[str]]:
    """Test if a jq filter is valid and works with the input."""
    with track_progress("Testing jq filter", LoaderStyle.BAR):
        try:
            result = run_command(f"echo '{json_str}' | jq '{filter_str}'")
            if result is None:
                return False, None
            
            # Try to parse result as JSON to validate it
            try:
                json.loads(result)
            except json.JSONDecodeError:
                # Result might be a simple string or number, which is fine
                pass
                
            return True, result
            
        except Exception as e:
            print(f"❌ Error testing filter: {e}", file=sys.stderr)
            return False, None

def generate_markdown(
    query: str,
    filter_str: str,
    input_json: str,
    output_json: str,
    input_file: Optional[str] = None
) -> str:
    """Generate markdown documentation for the jq filter."""
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    source = input_file if input_file else "stdin"
    
    return f"""# jq Filter Documentation
Generated on: {now}

## Query
> {query}

## Source
Input from: `{source}`

## jq Filter
```jq
{filter_str}
```

## Input Data (sample)
```json
{json.dumps(json.loads(input_json), indent=2)}
```

## Output
```json
{output_json}
```

## Usage Examples
1. Using a file:
   ```bash
   jq '{filter_str}' input.json
   ```

2. Using pipeline:
   ```bash
   cat input.json | jq '{filter_str}'
   ```

3. With compact output:
   ```bash
   jq -c '{filter_str}' input.json
   ```

## Notes
- The filter handles null values safely
- Use `-c` for compact output
- Use `--arg` for variable substitution if needed
"""

def save_markdown(content: str, output_path: Optional[str] = None) -> str:
    """Save markdown content to a file."""
    with track_progress("Saving documentation", LoaderStyle.MOON):
        try:
            if not output_path:
                # Generate filename from timestamp
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"jq_filter_{timestamp}.md"
                desktop_path = get_desktop_path()
                output_path = os.path.join(desktop_path, filename)
            
            # Ensure directory exists
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            # Save content
            with open(output_path, 'w') as f:
                f.write(content)
            
            return output_path
            
        except Exception as e:
            print(f"❌ Error saving documentation: {e}", file=sys.stderr)
            # Try to save to artifacts as fallback
            try:
                return save_artifact('docs', f"jq_filter_{int(time.time())}.md", content)
            except Exception:
                return ""

def interactive_mode() -> None:
    """Run in interactive mode."""
    print("\n🔍 ezjq Interactive Mode")
    print("------------------------")
    
    # Get JSON input
    print("\n1. Enter your JSON content (press Ctrl+D when done):")
    json_lines = []
    try:
        while True:
            line = input()
            json_lines.append(line)
    except EOFError:
        json_str = "\n".join(json_lines)
    
    try:
        # Validate JSON
        json.loads(json_str)
    except json.JSONDecodeError as e:
        print(f"\n❌ Error: Invalid JSON - {e}", file=sys.stderr)
        return
    
    # Get query
    print("\n2. Describe what you want to extract/transform:")
    query = input("> ")
    
    # Generate filter
    filter_str = generate_jq_filter(json_str, query)
    if not filter_str:
        print("❌ Failed to generate filter.", file=sys.stderr)
        return
    
    # Test filter
    success, result = test_jq_filter(json_str, filter_str)
    if not success:
        print("❌ Generated filter is invalid.", file=sys.stderr)
        return
    
    # Generate documentation
    print("\n📝 Generating documentation...")
    markdown = generate_markdown(query, filter_str, json_str, result or "")
    
    # Save documentation
    output_path = save_markdown(markdown)
    if not output_path:
        print("❌ Failed to save documentation.", file=sys.stderr)
        return
    
    # Show results
    print("\n✨ Filter generated successfully!")
    print(f"\njq filter: {filter_str}")
    print(f"\nDocumentation saved to: {output_path}")

def main():
    parser = argparse.ArgumentParser(
        description="Generate and document jq filters using natural language descriptions",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Generate filter and save documentation
    ezjq --file data.json --query "get all user names" --output filter.md
    
    # Interactive mode with automatic output
    ezjq --interactive
    
    # Read JSON from stdin and specify output
    cat data.json | ezjq --query "extract emails" --output result.md
    
    # Complex transformations
    ezjq --file data.json --query "get users where age > 25 and group by city"
    ezjq --file logs.json --query "count errors by severity and sort by count"
    ezjq --file metrics.json --query "calculate average response time per endpoint"
        """
    )
    
    parser.add_argument("--file", "-f", help="JSON input file")
    parser.add_argument("--query", "-q", help="Query description")
    parser.add_argument("--output", "-o", help="Output markdown file path")
    parser.add_argument("--interactive", "-i", action="store_true",
                      help="Run in interactive mode")
    
    args = parser.parse_args()
    
    # Handle interactive mode
    if args.interactive:
        interactive_mode()
        return 0
    
    # Validate arguments
    if not args.query and not args.interactive:
        parser.error("--query is required unless using --interactive")
    
    # Read input
    data, json_str = read_json_input(args.file)
    if not data:
        return 1
    
    # Generate filter
    filter_str = generate_jq_filter(json_str, args.query)
    if not filter_str:
        return 1
    
    # Test filter
    success, result = test_jq_filter(json_str, filter_str)
    if not success:
        print("❌ Generated filter is invalid.", file=sys.stderr)
        return 1
    
    # Generate documentation
    print("\n📝 Generating documentation...")
    markdown = generate_markdown(
        args.query, filter_str, json_str, result or "",
        input_file=args.file
    )
    
    # Save documentation
    output_path = save_markdown(markdown, args.output)
    if not output_path:
        print("❌ Failed to save documentation.", file=sys.stderr)
        return 1
    
    # Show results
    print("\n✨ Filter generated successfully!")
    print(f"\njq filter: {filter_str}")
    print(f"\nDocumentation saved to: {output_path}")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
