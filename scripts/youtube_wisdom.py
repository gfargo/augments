#!/usr/bin/env python3
"""
Command: youtube_wisdom

Extract transcripts from YouTube, run Fabric patterns, optionally enhance with OpenAI,
create TTS, and output a Markdown file.
"""

import argparse
import concurrent.futures
import os

from augments.lib.progress import (LoaderStyle, show_parallel_progress,
                                   track_progress, with_progress)
from augments.lib.utils import (generate_tts, get_desktop_path, get_transcript,
                                get_video_metadata, openai_completion,
                                run_fabric_pattern)

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")

def parallel_process(transcript):
    """
    Demonstrate concurrent extraction of summary, wisdom, links.
    """
    operations = [
        ("Generating summary", lambda: run_fabric_pattern(transcript, "summarize")),
        ("Extracting wisdom", lambda: run_fabric_pattern(transcript, "extract_wisdom")),
        ("Finding references", lambda: run_fabric_pattern(transcript, "extract_references"))
    ]
    
    results = show_parallel_progress(operations)
    return results[0], results[1], results[2]  # summary, wisdom, links

def create_markdown(metadata, summary, wisdom, links, audio_file):
    """
    Create a Markdown output.
    
    Args:
        metadata: YouTubeMetadata object containing video information
        summary: Generated summary text
        wisdom: Extracted wisdom text
        links: Extracted links text
        audio_file: Path to the generated audio file, or None if not available
    """
    # Format duration as HH:MM:SS
    duration_str = f"{metadata.duration//3600:02d}:{(metadata.duration%3600)//60:02d}:{metadata.duration%60:02d}"
    
    # Format upload date as YYYY-MM-DD
    upload_date = f"{metadata.upload_date[:4]}-{metadata.upload_date[4:6]}-{metadata.upload_date[6:]}"
    
    # Format audio section
    audio_section = "🔊 [Listen to summary]({})".format(audio_file) if audio_file else "🔇 Audio summary not available"
    
    return f"""# {metadata.title}

## Video Information
- **Author:** {metadata.author}
- **Video ID:** [{metadata.id}](https://youtube.com/watch?v={metadata.id})
- **Duration:** {duration_str}
- **Views:** {metadata.view_count:,}
- **Upload Date:** {upload_date}

## Summary
{summary or 'No summary available'}

## Key Insights
{wisdom or 'No insights extracted'}

## Referenced Links
{links or 'No links found'}

## Audio Summary
{audio_section}

## Original Description
```
{metadata.description}
```"""

@with_progress("Initializing YouTube Wisdom", LoaderStyle.MOON)
def main():
    parser = argparse.ArgumentParser(description="Extract wisdom from YouTube videos.")
    parser.add_argument("url", help="YouTube video URL")
    args = parser.parse_args()

    url = args.url
    
    # Get video metadata
    with track_progress("Fetching video metadata", LoaderStyle.DOTS):
        metadata = get_video_metadata(url)
        if not metadata:
            print("❌ Could not retrieve video metadata.")
            return

    # Get transcript
    with track_progress("Downloading transcript", LoaderStyle.PULSE):
        transcript = get_transcript(url)
        if not transcript:
            print("❌ No transcript available, exiting.")
            return

    print(f"\n📽️  Processing video: {metadata.title}")
    summary, wisdom, links = parallel_process(transcript)

    # Optionally enhance wisdom with OpenAI
    if wisdom and OPENAI_API_KEY:
        with track_progress("Enhancing insights with AI", LoaderStyle.BRAILLE):
            prompt = f"Enhance and refine this text:\n\n{wisdom}"
            improved_wisdom = openai_completion(prompt)
            if improved_wisdom:
                wisdom = improved_wisdom

    # Generate audio from the summary
    audio_file = None
    if summary:
        audio_filename = f"{metadata.get_filename_prefix()}-summary.mp3"
        audio_path = get_desktop_path(audio_filename)
        
        if generate_tts(summary, audio_path):
            # Use relative path in markdown for better portability
            audio_file = audio_filename

    # Create and save markdown
    with track_progress("Creating markdown document", LoaderStyle.BAR):
        markdown = create_markdown(metadata, summary, wisdom, links, audio_file)
        output_filename = get_desktop_path(f"{metadata.get_filename_prefix()}.md")
        with open(output_filename, "w", encoding="utf-8") as f:
            f.write(markdown)
        print(f"\n✨ Markdown output saved to {output_filename}")

if __name__ == "__main__":
    main()