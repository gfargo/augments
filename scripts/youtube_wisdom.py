#!/usr/bin/env python3
"""
Command: youtube_wisdom

Extract transcripts from YouTube, run Fabric patterns, enhance with Ollama or OpenAI,
create TTS, and output a Markdown file with frontmatter.
"""

import argparse
import concurrent.futures
import os
from typing import Optional, Tuple

from augments.lib.llm import ChatMessage, ModelType, OllamaClient, Role
from augments.lib.progress import (LoaderStyle, show_parallel_progress,
                                   track_progress, with_progress)
from augments.lib.utils import (generate_tts, get_desktop_path, get_transcript,
                                get_video_metadata, openai_completion,
                                run_fabric_pattern)

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")

# Initialize Ollama client with configured or default model
OLLAMA_DEFAULT_MODEL = os.getenv('OLLAMA_DEFAULT_MODEL', ModelType.MEDIUM.value)
try:
    ollama = OllamaClient(model=OLLAMA_DEFAULT_MODEL)
    OLLAMA_AVAILABLE = True
    print(f"🤖 Using Ollama model: {OLLAMA_DEFAULT_MODEL}")
except (ImportError, ConnectionError) as e:
    print(f"⚠️  Ollama not available: {e}")
    OLLAMA_AVAILABLE = False

# Prompt templates
LINK_EXTRACTION_PROMPT = """
Please analyze the following text and extract all relevant links and resources mentioned.
Include both explicit URLs and references to resources (like books, tools, websites, etc.).
For each link or resource, provide a brief description of what it is.

Also consider these additional sources:
Video URL: {video_url}
Video Description: {description}

Format the output as a markdown list with categories.
Example:
## Direct Links
- [Example.com](https://example.com) - Main website discussed
- [GitHub Repo](https://github.com/example) - Source code repository

## Mentioned Resources
- "Clean Code" by Robert Martin - Book recommended for software design
- Visual Studio Code - Recommended IDE for development

Text to analyze:
{text}
"""

FRONTMATTER_PROMPT = """
Generate YAML frontmatter for a markdown document about a YouTube video.
Use the following information to create comprehensive, well-organized frontmatter.

Title: {title}
Author: {author}
Video URL: {video_url}
Duration: {duration}
Views: {views}
Upload Date: {upload_date}
Description: {description}

The frontmatter should include:
- Basic video metadata (title, author, url, etc.)
- Topics/tags extracted from the content
- Type of content (tutorial, review, discussion, etc.)
- Skill level (beginner, intermediate, advanced)
- Key technologies or concepts mentioned
- Estimated reading time

Format as YAML between triple dashes (---).
Example:
---
title: "Example Video"
author: "John Doe"
type: "tutorial"
skill_level: "intermediate"
topics: ["python", "web development"]
---

PLEASE ONLY RETURN VALID FRONTMATTER YAML, TERMINATED BY triple dashes at the start AND end.  Don't forget the --- at the end!
"""

def extract_links_ollama(transcript: str, metadata) -> Optional[str]:
    """
    Use Ollama to extract links and resources from transcript and metadata.
    """
    if not OLLAMA_AVAILABLE:
        return None
        
    # Format prompt with video information
    prompt = LINK_EXTRACTION_PROMPT.format(
        text=transcript,
        video_url=f"https://youtube.com/watch?v={metadata.id}",
        description=metadata.description,
    )
    
    try:
        return ollama.generate(prompt)
    except Exception as e:
        print(f"Warning: Ollama link extraction failed: {e}")
        return None

def generate_frontmatter_ollama(metadata) -> Optional[str]:
    """
    Use Ollama to generate frontmatter from video metadata.
    """
    if not OLLAMA_AVAILABLE:
        return None
    
    # Format duration as HH:MM:SS
    duration_str = f"{metadata.duration//3600:02d}:{(metadata.duration%3600)//60:02d}:{metadata.duration%60:02d}"
    
    # Format upload date
    upload_date = f"{metadata.upload_date[:4]}-{metadata.upload_date[4:6]}-{metadata.upload_date[6:]}"
    
    # Format prompt with video information
    prompt = FRONTMATTER_PROMPT.format(
        title=metadata.title,
        author=metadata.author,
        video_url=f"https://youtube.com/watch?v={metadata.id}",
        duration=duration_str,
        views=f"{metadata.view_count:,}",
        upload_date=upload_date,
        description=metadata.description
    )
    
    try:
        return ollama.generate(prompt)
    except Exception as e:
        print(f"Warning: Ollama frontmatter generation failed: {e}")
        return None

def parallel_process(transcript: str, metadata) -> Tuple[Optional[str], Optional[str], Optional[str], Optional[str], Optional[str]]:
    """
    Run multiple operations in parallel:
    - Generate summary
    - Extract wisdom
    - Extract links (Fabric)
    - Extract links (Ollama)
    - Generate frontmatter (Ollama)
    
    Returns:
        Tuple of (summary, wisdom, fabric_links, ollama_links, frontmatter)
    """
    print("\n📝 Processing content in parallel...")
    
    operations = [
        ("Generating summary...", lambda: run_fabric_pattern(transcript, "summarize")),
        ("Extracting insights...", lambda: run_fabric_pattern(transcript, "extract_wisdom")),
        ("Finding pattern-based references...", lambda: run_fabric_pattern(transcript, "extract_references")),
        ("Analyzing content with Ollama...", lambda: extract_links_ollama(transcript, metadata)),
        ("Generating AI-enhanced frontmatter...", lambda: generate_frontmatter_ollama(metadata))
    ]
    
    results = show_parallel_progress(operations)
    print("✓ Content processing complete\n")
    return tuple(results)  # summary, wisdom, fabric_links, ollama_links, frontmatter

def create_markdown(
    metadata, summary, wisdom, fabric_links, ollama_links, frontmatter, audio_file
):
    """
    Create a Markdown output with frontmatter.
    
    Args:
        metadata: YouTubeMetadata object containing video information
        summary: Generated summary text
        wisdom: Extracted wisdom text
        fabric_links: Links extracted by Fabric
        ollama_links: Links extracted by Ollama
        frontmatter: Generated YAML frontmatter
        audio_file: Path to the generated audio file, or None if not available
    """
    # Format duration as HH:MM:SS
    duration_str = f"{metadata.duration//3600:02d}:{(metadata.duration%3600)//60:02d}:{metadata.duration%60:02d}"
    
    # Format upload date as YYYY-MM-DD
    upload_date = f"{metadata.upload_date[:4]}-{metadata.upload_date[4:6]}-{metadata.upload_date[6:]}"
    
    # Format audio section
    audio_section = "🔊 [Listen to summary]({})".format(audio_file) if audio_file else "🔇 Audio summary not available"
    
    # Combine frontmatter with content
    return f"""{frontmatter or '---\ntitle: "' + metadata.title + '"\nauthor: "' + metadata.author + '"\n---\n'}

# {metadata.title}

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

## Referenced Links and Resources

### AI-Enhanced Link Analysis
{ollama_links or 'No AI-enhanced link analysis available'}

### Pattern-Matched Links
{fabric_links or 'No pattern-matched links found'}

## Audio Summary
{audio_section}

## Original Description
```
{metadata.description}
```"""

def main():
    """Extract wisdom and insights from YouTube videos."""
    parser = argparse.ArgumentParser(description="Extract wisdom from YouTube videos.")
    parser.add_argument("url", help="YouTube video URL")
    parser.add_argument("--no-ollama", action="store_true", help="Disable Ollama-based enhancements")
    args = parser.parse_args()

    url = args.url
    use_ollama = OLLAMA_AVAILABLE and not args.no_ollama
    
    print("\n🎬 YouTube Wisdom Extractor")
    print("==========================")
    
    # Get video metadata
    with track_progress("Fetching video metadata...", LoaderStyle.DOTS):
        metadata = get_video_metadata(url)
        if not metadata:
            print("\n❌ Could not retrieve video metadata.")
            return

    # Get transcript
    with track_progress("Downloading transcript...", LoaderStyle.PULSE):
        transcript = get_transcript(url)
        if not transcript:
            print("\n❌ No transcript available, exiting.")
            return

    print(f"\n📽️  Processing: {metadata.title}")
    print("=" * (12 + len(metadata.title)))
    
    # Run parallel processing with Ollama enhancements
    summary, wisdom, fabric_links, ollama_links, frontmatter = parallel_process(transcript, metadata)

    # Optionally enhance wisdom with OpenAI
    if wisdom and OPENAI_API_KEY:
        with track_progress("Enhancing insights with OpenAI...", LoaderStyle.BRAILLE):
            prompt = f"Enhance and refine this text:\n\n{wisdom}"
            improved_wisdom = openai_completion(prompt)
            if improved_wisdom:
                wisdom = improved_wisdom

    # Generate audio from the summary
    audio_file = None
    if summary:
        print("\n🔊 Generating Audio Summary")
        print("=========================")
        audio_filename = f"{metadata.get_filename_prefix()}-summary.mp3"
        audio_path = get_desktop_path(audio_filename)
        
        if generate_tts(summary, audio_path):
            audio_file = audio_filename

    # Create and save markdown
    print("\n📄 Creating Final Document")
    print("=======================")
    with track_progress("Generating markdown...", LoaderStyle.BAR):
        markdown = create_markdown(
            metadata=metadata,
            summary=summary,
            wisdom=wisdom,
            fabric_links=fabric_links,
            ollama_links=ollama_links,
            frontmatter=frontmatter,
            audio_file=audio_file
        )
        output_filename = get_desktop_path(f"{metadata.get_filename_prefix()}.md")
        with open(output_filename, "w", encoding="utf-8") as f:
            f.write(markdown)
    
    # Final status
    print("\n✨ Processing Complete!")
    print("====================")
    print(f"📝 Output: {output_filename}")
    
    enhancements = []
    if use_ollama:
        enhancements.append("🤖 Ollama AI analysis")
    if OPENAI_API_KEY:
        enhancements.append("🔮 OpenAI analysis")
    if audio_file:
        enhancements.append("🔊 Audio summary")
    
    if enhancements:
        print("\n🎯 Enhancements Applied:")
        for enhancement in enhancements:
            print(f"   {enhancement}")

if __name__ == "__main__":
    main()