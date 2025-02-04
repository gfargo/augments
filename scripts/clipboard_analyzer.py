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
    run_fabric_pattern, openai_completion, generate_tts, get_desktop_path
)
from augments.lib.progress import (
    track_progress, show_parallel_progress, LoaderStyle, with_progress
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
    operations = [
        ("Generating summary", lambda: run_fabric_pattern(text, "summarize")),
        ("Extracting insights", lambda: run_fabric_pattern(text, "extract_wisdom")),
        ("Finding references", lambda: run_fabric_pattern(text, "extract_links"))
    ]
    
    results = show_parallel_progress(operations)
    return results[0], results[1], results[2]  # summary, wisdom, links

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

@with_progress("Initializing Clipboard Analyzer", LoaderStyle.MOON)
def main():
    parser = argparse.ArgumentParser(description="Analyze clipboard text.")
    parser.add_argument("--title", help="Optional title for the analysis")
    args = parser.parse_args()

    with track_progress("Reading clipboard", LoaderStyle.PULSE):
        clipboard_text = pyperclip.paste()
        if not clipboard_text:
            print("❌ Clipboard is empty.")
            return

    # Derive or use provided title
    with track_progress("Processing title", LoaderStyle.DOTS):
        title = args.title if args.title else auto_title_first_line(clipboard_text)
        safe_title = title.replace(' ', '_')

    print(f"\n📋 Analyzing: {title}")
    
    # Fabric patterns in parallel
    summary, wisdom, links = parallel_patterns(clipboard_text)

    # TTS from summary
    audio_file = None
    if summary:
        audio_filename = f"{safe_title}-analysis.mp3"
        audio_path = get_desktop_path(audio_filename)
        if generate_tts(summary, audio_path):
            audio_file = audio_filename

    # Build and save markdown
    with track_progress("Creating markdown document", LoaderStyle.BAR):
        md_output = create_markdown(title, summary, wisdom, links, audio_file or "No audio available")
        md_filename = get_desktop_path(f"{safe_title}-analysis.md")
        with open(md_filename, "w", encoding="utf-8") as f:
            f.write(md_output)
        print(f"\n✨ Analysis saved to {md_filename}")

if __name__ == "__main__":
    main()