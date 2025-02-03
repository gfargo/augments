#!/usr/bin/env python3
"""
Command: youtube_wisdom

Extract transcripts from YouTube, run Fabric patterns, optionally enhance with OpenAI,
create TTS, and output a Markdown file.
"""

import argparse
import concurrent.futures
import os

from augments.lib.utils import (
    generate_tts, get_transcript, get_video_metadata,
    openai_completion, run_fabric_pattern, get_desktop_path
)

def parallel_process(transcript):
    """
    Demonstrate concurrent extraction of summary, wisdom, links.
    """
    results = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
        tasks = {
            executor.submit(run_fabric_pattern, transcript, "summarize"): "summary",
            executor.submit(run_fabric_pattern, transcript, "extract_wisdom"): "wisdom",
            executor.submit(run_fabric_pattern, transcript, "extract_references"): "links",
        }
        for fut in concurrent.futures.as_completed(tasks):
            key = tasks[fut]
            results[key] = fut.result()
    return results.get("summary"), results.get("wisdom"), results.get("links")

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

def main():
    parser = argparse.ArgumentParser(description="Extract wisdom from YouTube videos.")
    parser.add_argument("url", help="YouTube video URL")
    args = parser.parse_args()

    url = args.url
    
    # Get video metadata
    metadata = get_video_metadata(url)
    if not metadata:
        print("Could not retrieve video metadata.")
        return

    # Get transcript
    transcript = get_transcript(url)
    if not transcript:
        print("No transcript available, exiting.")
        return

    print(f"\nProcessing video: {metadata}")
    summary, wisdom, links = parallel_process(transcript)

    # Optionally enhance wisdom with OpenAI
    if wisdom:
        prompt = f"Enhance and refine this text:\n\n{wisdom}"
        improved_wisdom = openai_completion(prompt)
        if improved_wisdom:
            wisdom = improved_wisdom

    # Generate audio from the summary
    if summary:
        print("\nGenerating audio summary...")
        audio_filename = f"{metadata.get_filename_prefix()}-summary.mp3"
        audio_path = get_desktop_path(audio_filename)
        
        if generate_tts(summary, audio_path):
            # Use relative path in markdown for better portability
            audio_file = audio_filename
        else:
            print("Warning: Audio generation failed, skipping audio section in markdown")
            audio_file = None
    else:
        audio_file = None

    # Create Markdown
    markdown = create_markdown(metadata, summary, wisdom, links, audio_file)

    # Write the output to Desktop
    output_filename = get_desktop_path(f"{metadata.get_filename_prefix()}.md")
    with open(output_filename, "w", encoding="utf-8") as f:
        f.write(markdown)

    print(f"\nMarkdown output saved to {output_filename}")

if __name__ == "__main__":
    main()