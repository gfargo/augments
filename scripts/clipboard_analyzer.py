#!/usr/bin/env python3
"""
Command: clipboardAnalyze

Reads clipboard text, optionally tries to derive a title, then runs Fabric patterns
and/or local LLaMA / OpenAI calls to extract code snippets, links, or summary.
"""

import os
import argparse
import pyperclip
import concurrent.futures
from augments.lib.utils import (
    run_fabric_pattern, openai_completion, generate_tts
)

def auto_title_first_line(text):
    """
    Optionally derive a title from the first line of text.
    """
    lines = text.strip().split("\n")
    return lines[0][:50] if lines else "ClipboardContent"

def parallel_patterns(text):
    """
    Parallelize multiple Fabric patterns: summarize, extract_wisdom, extract_links.
    """
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
        fut_summary = executor.submit(run_fabric_pattern, text, "summarize")
        fut_wisdom = executor.submit(run_fabric_pattern, text, "extract_wisdom")
        fut_links  = executor.submit(run_fabric_pattern, text, "extract_links")
        return fut_summary.result(), fut_wisdom.result(), fut_links.result()

def create_markdown(title, summary, wisdom, links, audio_file):
    return f"""# Analysis of: {title}

## Summary
{summary or 'No summary'}

## Key Wisdom
{wisdom or 'No wisdom'}

## Links/References
{links or 'No links'}

## Audio Summary
[Listen here]({audio_file})
"""

def main():
    parser = argparse.ArgumentParser(description="Analyze clipboard text.")
    parser.add_argument("--title", help="Optional title for the analysis")
    args = parser.parse_args()

    clipboard_text = pyperclip.paste()
    if not clipboard_text:
        print("Clipboard is empty.")
        return

    # Derive or use provided title
    title = args.title if args.title else auto_title_first_line(clipboard_text)

    # Fabric patterns in parallel
    summary, wisdom, links = parallel_patterns(clipboard_text)

    # TTS from summary
    audio_filename = f"{title.replace(' ', '_')}-analysis.mp3"
    if summary:
        generate_tts(summary, audio_filename)

    # Build Markdown
    md_output = create_markdown(title, summary, wisdom, links, audio_filename)

    # Save to Desktop
    desktop_path = os.path.join(os.path.expanduser("~"), "Desktop")
    md_filename = os.path.join(desktop_path, f"{title.replace(' ', '_')}-analysis.md")
    with open(md_filename, "w", encoding="utf-8") as f:
        f.write(md_output)

    print(f"Analysis saved to {md_filename}")

if __name__ == "__main__":
    main()