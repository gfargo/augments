#!/usr/bin/env python3
"""
Command: yt

A collection of YouTube utilities for quick access to video information.
"""

import argparse
import json
import os
import sys
import time

from augments.lib.utils import (get_transcript, get_video_id,
                                get_video_metadata, run_command,
                                get_artifact_path, get_file_info,
                                save_artifact, format_duration)


def print_json(data):
    """Print data as formatted JSON."""
    print(json.dumps(data, indent=2, ensure_ascii=False))

def handle_transcript(url, format='text', save=True):
    """Get video transcript in various formats."""
    # Get video info for better output
    metadata = get_video_metadata(url)
    if metadata:
        print(f"\nProcessing: {metadata.title}")
        print(f"Author: {metadata.author}")
        print(f"Duration: {format_duration(metadata.duration)}\n")
    
    # Get transcript
    transcript = get_transcript(url, detailed=True)  # We want detailed output for VTT format
    if not transcript:
        print("No transcript available.", file=sys.stderr)
        return 1
        
    # Save transcript if requested
    if save:
        video_id = metadata.id if metadata else get_video_id(url)
        save_artifact('transcripts', f"{video_id}.vtt", transcript)
    
    # Handle different output formats
    if format == 'json':
        print_json({
            'video_id': metadata.id if metadata else get_video_id(url),
            'title': metadata.title if metadata else 'Unknown',
            'transcript': transcript
        })
    elif format == 'text':
        print(transcript)
    elif format == 'srt':
        # TODO: Convert to SRT format
        print("SRT format not yet implemented")
        return 1
    
    # Show artifact location if saved
    if save:
        artifact_path = get_artifact_path('transcripts', f"{metadata.id if metadata else get_video_id(url)}.vtt")
        print(f"\nTranscript saved: {artifact_path}")
    
    return 0

def handle_info(url):
    """Get video metadata."""
    metadata = get_video_metadata(url)
    if not metadata:
        print("Could not retrieve video metadata.", file=sys.stderr)
        return 1
    
    print_json({
        'id': metadata.id,
        'title': metadata.title,
        'author': metadata.author,
        'duration': metadata.duration,
        'views': metadata.view_count,
        'upload_date': metadata.upload_date,
        'description': metadata.description
    })
    return 0

def handle_download(url, format='mp4'):
    """Download video in specified format."""
    # Get video info
    metadata = get_video_metadata(url)
    if metadata:
        print(f"\nDownloading: {metadata.title}")
        print(f"Author: {metadata.author}")
        print(f"Duration: {format_duration(metadata.duration)}\n")
        
        # Create filename
        filename = f"{metadata.get_filename_prefix()}.{format if format != 'audio' else 'mp3'}"
    else:
        video_id = get_video_id(url)
        if not video_id:
            return 1
        filename = f"{video_id}.{format if format != 'audio' else 'mp3'}"
    
    # Get artifact path
    output_path = get_artifact_path('downloads', filename)
    
    # Build command
    if format == 'audio':
        cmd = f'yt-dlp -x --audio-format mp3 -o "{output_path}" {url}'
    else:
        cmd = f'yt-dlp -f "bestvideo[ext={format}]+bestaudio/best[ext={format}]/best" -o "{output_path}" {url}'
    
    # Run download
    print(f"Downloading to: {output_path}")
    result = run_command(cmd)
    
    if result is None:
        return 1
        
    print(f"\nDownload complete: {output_path}")
    file_info = get_file_info(output_path)
    print(f"File size: {file_info['size'] / 1024 / 1024:.1f} MB")
    
    return 0

def parse_duration(duration: str) -> int:
    """Parse duration string (e.g., '7d', '24h', '30m') to seconds."""
    if not duration:
        return None
        
    units = {
        'd': 86400,  # days
        'h': 3600,   # hours
        'm': 60,     # minutes
        's': 1       # seconds
    }
    
    unit = duration[-1].lower()
    if unit not in units:
        print(f"Invalid duration unit: {unit}")
        return None
        
    try:
        value = int(duration[:-1])
        return value * units[unit]
    except ValueError:
        print(f"Invalid duration value: {duration[:-1]}")
        return None

def handle_list(category: str):
    """List artifacts in a category."""
    if category == 'all':
        categories = ['transcripts', 'downloads', 'audio']
    else:
        categories = [category]
    
    for cat in categories:
        print(f"\n{cat.title()}:")
        path = get_artifact_path(cat, '', create_dirs=False)
        if not os.path.exists(path):
            print("  No files found")
            continue
            
        files = os.listdir(path)
        if not files:
            print("  No files found")
            continue
            
        for filename in sorted(files):
            filepath = os.path.join(path, filename)
            info = get_file_info(filepath)
            size_mb = info['size'] / 1024 / 1024
            print(f"  {filename}")
            print(f"    Size: {size_mb:.1f} MB")
            print(f"    Modified: {info['modified']}")
    
    return 0

def handle_cleanup(category: str, max_age: str):
    """Clean up old artifacts."""
    seconds = parse_duration(max_age)
    if seconds is None:
        return 1
    
    if category == 'all':
        categories = ['transcripts', 'downloads', 'audio']
    else:
        categories = [category]
    
    for cat in categories:
        print(f"\nCleaning up {cat}...")
        path = get_artifact_path(cat, '', create_dirs=False)
        if not os.path.exists(path):
            print("  No files found")
            continue
            
        files = os.listdir(path)
        if not files:
            print("  No files found")
            continue
            
        removed = 0
        for filename in files:
            filepath = os.path.join(path, filename)
            age = time.time() - os.path.getmtime(filepath)
            
            if age > seconds:
                try:
                    os.remove(filepath)
                    removed += 1
                    print(f"  Removed: {filename}")
                except Exception as e:
                    print(f"  Error removing {filename}: {e}")
        
        print(f"Removed {removed} files")
    
    return 0

def main():
    parser = argparse.ArgumentParser(
        description="YouTube utilities for quick access to video information",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Get video transcript
  yt --transcript "https://www.youtube.com/watch?v=..."
  
  # Get transcript in JSON format and save to artifacts
  yt --transcript "https://..." --format json --save
  
  # Get transcript without saving
  yt --transcript "https://..." --no-save
  
  # Get video information
  yt --info "https://..."
  
  # Download video to artifacts directory
  yt --download "https://..."
  
  # Download audio only
  yt --download "https://..." --format audio
  
  # List saved artifacts
  yt --list transcripts
  yt --list downloads
  
  # Clean up old artifacts
  yt --cleanup transcripts --max-age 7d
"""
    )
    
    parser.add_argument("url", nargs='?', help="YouTube video URL")
    
    # Command groups
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--transcript", action="store_true", help="Get video transcript")
    group.add_argument("--info", action="store_true", help="Get video metadata")
    group.add_argument("--download", action="store_true", help="Download video")
    group.add_argument("--list", choices=['transcripts', 'downloads', 'audio', 'all'],
                      help="List saved artifacts")
    group.add_argument("--cleanup", choices=['transcripts', 'downloads', 'audio', 'all'],
                      help="Clean up artifacts")
    
    # Options
    parser.add_argument(
        "--format",
        choices=['text', 'json', 'srt', 'mp4', 'webm', 'audio'],
        default='text',
        help="Output format (default: text for transcript, mp4 for download)"
    )
    parser.add_argument(
        "--save",
        action="store_true",
        default=True,
        help="Save output to artifacts directory (default: True)"
    )
    parser.add_argument(
        "--no-save",
        action="store_false",
        dest="save",
        help="Don't save output to artifacts directory"
    )
    parser.add_argument(
        "--max-age",
        help="Maximum age for cleanup (e.g., '7d', '24h', '30m')"
    )
    
    args = parser.parse_args()
    
    # Handle list and cleanup commands that don't need URL
    if args.list:
        return handle_list(args.list)
    elif args.cleanup:
        if not args.max_age:
            print("Error: --max-age is required for cleanup", file=sys.stderr)
            return 1
        return handle_cleanup(args.cleanup, args.max_age)
    
    # All other commands need URL
    if not args.url:
        print("Error: URL is required", file=sys.stderr)
        return 1
    
    # Validate URL
    if not get_video_id(args.url):
        print("Error: Invalid YouTube URL", file=sys.stderr)
        return 1
    
    # Handle commands
    if args.transcript:
        return handle_transcript(args.url, args.format, args.save)
    elif args.info:
        return handle_info(args.url)
    elif args.download:
        return handle_download(args.url, args.format)
    
    return 0

if __name__ == "__main__":
    sys.exit(main())