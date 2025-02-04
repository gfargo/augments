import json
import os
import random
import re
import shlex
import subprocess
from typing import Dict, List, Optional, Tuple, Union

from dotenv import load_dotenv

try:
    import openai
except ImportError:
    openai = None

# Load environment variables
load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if OPENAI_API_KEY and openai is not None:
    openai.api_key = OPENAI_API_KEY

# Text Processing Utilities
def extract_urls(text: str) -> List[str]:
    """
    Extract URLs from text using a comprehensive regex pattern.
    
    Args:
        text: Input text to process
    
    Returns:
        List of found URLs
    """
    url_pattern = r'https?://(?:[-\w.]|(?:%[\da-fA-F]{2}))+'
    return re.findall(url_pattern, text)

def extract_code_blocks(text: str) -> List[Tuple[str, str]]:
    """
    Extract code blocks from markdown or plain text.
    
    Args:
        text: Input text to process
    
    Returns:
        List of tuples (language, code)
    """
    # Match both ``` and indented code blocks
    fenced_pattern = r'```(\w+)?\n(.*?)\n```'
    indented_pattern = r'(?:^[ ]{4}|\t)(.+)(?:\n|$)'
    
    blocks = []
    
    # Find fenced code blocks
    for match in re.finditer(fenced_pattern, text, re.MULTILINE | re.DOTALL):
        lang = match.group(1) or 'text'
        code = match.group(2).strip()
        blocks.append((lang, code))
    
    # Find indented code blocks
    current_block = []
    for line in text.split('\n'):
        if re.match(indented_pattern, line):
            current_block.append(line[4:])  # Remove indentation
        elif current_block:
            blocks.append(('text', '\n'.join(current_block)))
            current_block = []
    
    if current_block:
        blocks.append(('text', '\n'.join(current_block)))
    
    return blocks

def format_duration(seconds: int) -> str:
    """
    Format duration in seconds to HH:MM:SS.
    
    Args:
        seconds: Duration in seconds
    
    Returns:
        Formatted duration string
    """
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    seconds = seconds % 60
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}"

def format_date(date_str: str, input_format: str = '%Y%m%d', output_format: str = '%Y-%m-%d') -> str:
    """
    Format date string from one format to another.
    
    Args:
        date_str: Input date string
        input_format: Input date format
        output_format: Desired output format
    
    Returns:
        Formatted date string
    """
    from datetime import datetime
    try:
        dt = datetime.strptime(date_str, input_format)
        return dt.strftime(output_format)
    except ValueError:
        return date_str

# Artifact Management
def get_artifacts_dir() -> str:
    """
    Get the path to the artifacts directory, creating it if necessary.
    
    The structure will be:
    ~/.config/augments/artifacts/
    ├── transcripts/          # Video transcripts (.vtt, .srt, etc.)
    ├── audio/               # Generated audio files
    ├── downloads/           # Downloaded files
    └── temp/               # Temporary files
    
    Returns:
        Path to artifacts directory
    """
    base_dir = os.path.join(os.path.expanduser('~'), '.config', 'augments', 'artifacts')
    subdirs = ['transcripts', 'audio', 'downloads', 'temp']
    
    for subdir in subdirs:
        path = os.path.join(base_dir, subdir)
        ensure_dir(path)
    
    return base_dir

def get_artifact_path(category: str, filename: str, create_dirs: bool = True) -> str:
    """
    Get the full path for an artifact file.
    
    Args:
        category: Artifact category (transcripts, audio, downloads, temp)
        filename: Name of the file
        create_dirs: Whether to create directories if they don't exist
    
    Returns:
        Full path to the artifact file
    """
    base_dir = get_artifacts_dir() if create_dirs else os.path.join(os.path.expanduser('~'), '.config', 'augments', 'artifacts')
    return os.path.join(base_dir, category, sanitize_filename(filename))

def save_artifact(category: str, filename: str, content: Union[str, bytes], mode: str = 'w') -> str:
    """
    Save content as an artifact file.
    
    Args:
        category: Artifact category (transcripts, audio, downloads, temp)
        filename: Name of the file
        content: Content to save
        mode: File mode ('w' for text, 'wb' for binary)
    
    Returns:
        Path to the saved artifact
    """
    path = get_artifact_path(category, filename)
    try:
        with open(path, mode) as f:
            f.write(content)
        return path
    except Exception as e:
        print(f"Error saving artifact {filename}: {e}")
        return None

def load_artifact(category: str, filename: str, mode: str = 'r') -> Optional[Union[str, bytes]]:
    """
    Load content from an artifact file.
    
    Args:
        category: Artifact category (transcripts, audio, downloads, temp)
        filename: Name of the file
        mode: File mode ('r' for text, 'rb' for binary)
    
    Returns:
        File content, or None if file doesn't exist or can't be read
    """
    path = get_artifact_path(category, filename, create_dirs=False)
    try:
        with open(path, mode) as f:
            return f.read()
    except Exception as e:
        print(f"Error loading artifact {filename}: {e}")
        return None

def cleanup_artifacts(category: str = None, max_age: int = None):
    """
    Clean up old artifact files.
    
    Args:
        category: Specific category to clean, or None for all
        max_age: Maximum age in seconds, or None to keep all
    """
    base_dir = get_artifacts_dir()
    categories = [category] if category else ['transcripts', 'audio', 'downloads', 'temp']
    
    now = time.time()
    for cat in categories:
        cat_dir = os.path.join(base_dir, cat)
        if not os.path.exists(cat_dir):
            continue
            
        for filename in os.listdir(cat_dir):
            filepath = os.path.join(cat_dir, filename)
            if max_age and os.path.getmtime(filepath) < now - max_age:
                try:
                    os.remove(filepath)
                except Exception as e:
                    print(f"Error removing {filepath}: {e}")

# File System Utilities
def ensure_dir(path: str) -> bool:
    """
    Ensure a directory exists, creating it if necessary.
    
    Args:
        path: Directory path
    
    Returns:
        True if directory exists or was created, False otherwise
    """
    try:
        os.makedirs(path, exist_ok=True)
        return True
    except Exception as e:
        print(f"Error creating directory {path}: {e}")
        return False

def get_unique_filename(path: str) -> str:
    """
    Get a unique filename by appending a number if necessary.
    
    Args:
        path: Desired file path
    
    Returns:
        Unique file path
    """
    if not os.path.exists(path):
        return path
    
    base, ext = os.path.splitext(path)
    counter = 1
    
    while os.path.exists(f"{base}_{counter}{ext}"):
        counter += 1
    
    return f"{base}_{counter}{ext}"

def get_file_info(path: str) -> Dict:
    """
    Get detailed information about a file.
    
    Args:
        path: Path to file
    
    Returns:
        Dictionary with file information
    """
    try:
        stat = os.stat(path)
        return {
            'size': stat.st_size,
            'created': format_date(str(int(stat.st_ctime)), '%s', '%Y-%m-%d %H:%M:%S'),
            'modified': format_date(str(int(stat.st_mtime)), '%s', '%Y-%m-%d %H:%M:%S'),
            'type': 'directory' if os.path.isdir(path) else 'file',
            'extension': os.path.splitext(path)[1] if os.path.isfile(path) else None
        }
    except Exception as e:
        print(f"Error getting file info for {path}: {e}")
        return {}

# Network Utilities
def download_file(url: str, output_path: str, show_progress: bool = True) -> bool:
    """
    Download a file with progress indication.
    
    Args:
        url: URL to download from
        output_path: Where to save the file
        show_progress: Whether to show progress bar
    
    Returns:
        True if download successful, False otherwise
    """
    try:
        import requests
        from tqdm import tqdm
        
        response = requests.get(url, stream=True)
        response.raise_for_status()
        
        total_size = int(response.headers.get('content-length', 0))
        block_size = 8192
        
        with open(output_path, 'wb') as f:
            if show_progress:
                with tqdm(total=total_size, unit='B', unit_scale=True) as pbar:
                    for chunk in response.iter_content(chunk_size=block_size):
                        if chunk:
                            f.write(chunk)
                            pbar.update(len(chunk))
            else:
                for chunk in response.iter_content(chunk_size=block_size):
                    if chunk:
                        f.write(chunk)
        
        return True
    except Exception as e:
        print(f"Error downloading {url}: {e}")
        return False

def is_url_accessible(url: str, timeout: int = 5) -> bool:
    """
    Check if a URL is accessible.
    
    Args:
        url: URL to check
        timeout: Timeout in seconds
    
    Returns:
        True if URL is accessible, False otherwise
    """
    try:
        import requests
        response = requests.head(url, timeout=timeout)
        return response.status_code == 200
    except Exception:
        return False

# System Commands
def run_command(command: Union[str, List], input_text: Optional[str] = None, check: bool = True) -> Optional[str]:
    """
    Universal helper to run subprocess commands safely.
    
    Args:
        command: Command to run (string or list)
        input_text: Optional text to pass to STDIN
        check: Whether to raise an exception on command failure
    
    Returns:
        Command output as string, or None if command failed
    """
    try:
        if isinstance(command, str):
            command = shlex.split(command)
        result = subprocess.run(
            command,
            input=input_text,
            capture_output=True,
            text=True,
            check=check
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        print(f"Error running command '{' '.join(command)}': {e}")
        return None
    except FileNotFoundError as e:
        print(f"Command not found: {e}")
        return None

# AI/ML Functions
def run_fabric_pattern(text: str, pattern: str) -> Optional[str]:
    """
    Run a Fabric pattern on input text.
    
    Args:
        text: Input text to process
        pattern: Name of the Fabric pattern to run
    
    Returns:
        Processed text output, or None if processing failed
    """
    return run_command(["fabric", "-p", pattern], input_text=text)

def openai_completion(prompt: str, model: str = "gpt-3.5-turbo", 
                     max_tokens: int = 512, temperature: float = 0.7) -> Optional[str]:
    """
    Call OpenAI chat completion if OPENAI_API_KEY is set and openai is installed.
    
    Args:
        prompt: Text prompt for completion
        model: OpenAI model to use
        max_tokens: Maximum tokens in the response
        temperature: Sampling temperature (0.0 to 1.0)
    
    Returns:
        Completion text, or None if API call failed
    """
    if openai is None or OPENAI_API_KEY is None:
        print("OpenAI library or API key not found. Skipping OpenAI completion.")
        return None
    
    try:
        # Using the new chat completion API
        response = openai.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "You are a helpful assistant that enhances and refines text."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=max_tokens,
            temperature=temperature
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"OpenAI API Error: {e}")
        return None

# Text-to-Speech Functions
# Available voice types and their voices
AVAILABLE_VOICES = {
    'standard': [
        # Australia
        'en-AU-Standard-A', 'en-AU-Standard-B', 'en-AU-Standard-C', 'en-AU-Standard-D',
        # UK
        'en-GB-Standard-A', 'en-GB-Standard-B', 'en-GB-Standard-C', 'en-GB-Standard-D',
        'en-GB-Standard-F', 'en-GB-Standard-N', 'en-GB-Standard-O',
        # India
        'en-IN-Standard-A', 'en-IN-Standard-B', 'en-IN-Standard-C', 'en-IN-Standard-D',
        'en-IN-Standard-E', 'en-IN-Standard-F',
        # US
        'en-US-Standard-A', 'en-US-Standard-B', 'en-US-Standard-C', 'en-US-Standard-D',
        'en-US-Standard-E', 'en-US-Standard-F', 'en-US-Standard-G', 'en-US-Standard-H',
        'en-US-Standard-I', 'en-US-Standard-J'
    ],
    'premium': [
        # Australia
        'en-AU-Neural2-A', 'en-AU-Neural2-B', 'en-AU-Neural2-C', 'en-AU-Neural2-D',
        'en-AU-News-E', 'en-AU-News-F', 'en-AU-News-G',
        'en-AU-Polyglot-1',
        'en-AU-Wavenet-A', 'en-AU-Wavenet-B', 'en-AU-Wavenet-C', 'en-AU-Wavenet-D',
        # UK
        'en-GB-Neural2-A', 'en-GB-Neural2-B', 'en-GB-Neural2-C', 'en-GB-Neural2-D',
        'en-GB-Neural2-F',
        'en-GB-News-G', 'en-GB-News-H', 'en-GB-News-I', 'en-GB-News-J',
        'en-GB-News-K', 'en-GB-News-L', 'en-GB-News-M',
        'en-GB-Wavenet-A', 'en-GB-Wavenet-B', 'en-GB-Wavenet-C', 'en-GB-Wavenet-D',
        'en-GB-Wavenet-F',
        # India
        'en-IN-Neural2-A', 'en-IN-Neural2-B', 'en-IN-Neural2-C', 'en-IN-Neural2-D',
        'en-IN-Wavenet-A', 'en-IN-Wavenet-B', 'en-IN-Wavenet-C', 'en-IN-Wavenet-D',
        'en-IN-Wavenet-E', 'en-IN-Wavenet-F',
        # US
        'en-US-Neural2-A', 'en-US-Neural2-C', 'en-US-Neural2-D', 'en-US-Neural2-E',
        'en-US-Neural2-F', 'en-US-Neural2-G', 'en-US-Neural2-H', 'en-US-Neural2-I',
        'en-US-Neural2-J',
        'en-US-News-K', 'en-US-News-L', 'en-US-News-N',
        'en-US-Polyglot-1',
        'en-US-Wavenet-A', 'en-US-Wavenet-B', 'en-US-Wavenet-C', 'en-US-Wavenet-D',
        'en-US-Wavenet-E', 'en-US-Wavenet-F', 'en-US-Wavenet-G', 'en-US-Wavenet-H',
        'en-US-Wavenet-I', 'en-US-Wavenet-J'
    ],
    'studio': [
        'en-GB-Studio-B', 'en-GB-Studio-C',
        'en-US-Studio-O', 'en-US-Studio-Q'
    ]
}

def get_random_voice(voice_types: List[str] = ['standard']) -> str:
    """
    Return a random TTS voice from specified voice types.
    
    Args:
        voice_types: List of voice types to include. Valid options are:
                    'standard' - Free standard voices
                    'premium' - Premium voices (Neural2, News, Wavenet)
                    'studio' - Studio quality voices
                    Default is ['standard'] for free voices only.
    
    Returns:
        Random voice identifier string
    
    Raises:
        ValueError: If no valid voice types are provided or if specified types don't exist
    """
    # Validate voice types
    valid_types = set(AVAILABLE_VOICES.keys())
    requested_types = set(voice_types)
    invalid_types = requested_types - valid_types
    
    if invalid_types:
        raise ValueError(f"Invalid voice type(s): {', '.join(invalid_types)}. "
                        f"Valid types are: {', '.join(valid_types)}")
    
    # Combine voices from requested types
    available_voices = []
    for voice_type in voice_types:
        available_voices.extend(AVAILABLE_VOICES[voice_type])
    
    if not available_voices:
        raise ValueError("No voices available for the specified types")
    
    return random.choice(available_voices)

def generate_tts(text: str, output_filename: str, voice_types: List[str] = ['standard'], use_google_cloud: bool = True) -> bool:
    """
    Generate Text-to-Speech audio file using either Google Cloud Text-to-Speech (preferred) or gTTS (fallback).
    
    Args:
        text: Text to convert to speech
        output_filename: Path to save the audio file
        voice_types: List of voice types to use. Options:
                    'standard' - Free standard voices (default)
                    'premium' - Premium voices (Neural2, News, Wavenet)
                    'studio' - Studio quality voices
        use_google_cloud: Whether to try Google Cloud TTS first (defaults to True)
    
    Returns:
        True if successful, False otherwise
    """
    print(f"Generating audio file: {output_filename}")

    if use_google_cloud:
        try:
            from google.cloud import texttospeech
            print("Using Google Cloud Text-to-Speech")
            print(f"Using voice types: {', '.join(voice_types)}")
            
            # Get a random voice from specified types
            try:
                voice_name = get_random_voice(voice_types)
                print(f"Selected voice: {voice_name}")
                
                # Parse voice name to get language code and voice name
                # Format is like 'en-US-Standard-A'
                lang_code = '-'.join(voice_name.split('-')[:2])  # e.g., 'en-US'
                
            except ValueError as e:
                print(f"Error selecting voice: {e}")
                return False
            
            # Instantiate the client
            client = texttospeech.TextToSpeechClient()
            
            # Set the text input to be synthesized
            synthesis_input = texttospeech.SynthesisInput(text=text)
            
            # Build the voice request
            voice = texttospeech.VoiceSelectionParams(
                language_code=lang_code,
                name=voice_name
            )
            
            # Select the type of audio file
            audio_config = texttospeech.AudioConfig(
                audio_encoding=texttospeech.AudioEncoding.MP3,
                speaking_rate=1.1  # Slightly faster than default
            )
            
            # Perform the text-to-speech request
            response = client.synthesize_speech(
                input=synthesis_input,
                voice=voice,
                audio_config=audio_config
            )
            
            # Write the binary audio content to file
            with open(output_filename, "wb") as out:
                out.write(response.audio_content)
                
            if os.path.exists(output_filename):
                print(f"✓ Audio file created successfully ({os.path.getsize(output_filename)} bytes)")
                return True
                
        except Exception as e:
            print(f"Error with Google Cloud TTS: {e}")
            if "google.api_core" in str(e):
                print("⚠️  Google Cloud credentials not properly configured")
            print("Falling back to gTTS...")
    else:
        print("Google Cloud TTS disabled, using gTTS")
    
    # Fallback to gTTS
    try:
        from gtts import gTTS
        print("Using gTTS (fallback TTS engine)")
        
        # Create TTS
        tts = gTTS(text=text, lang='en', slow=False)
        
        # Save to file
        tts.save(output_filename)
        
        if os.path.exists(output_filename):
            print(f"✓ Audio file created successfully using gTTS ({os.path.getsize(output_filename)} bytes)")
            return True
        else:
            print("✗ Failed to create audio file")
            return False
            
    except Exception as e:
        print(f"Error with fallback gTTS: {e}")
        return False

# File and Path Utilities
def sanitize_filename(filename: str) -> str:
    """
    Convert a string into a safe filename by removing or replacing invalid characters.
    
    Args:
        filename: Original filename string
    
    Returns:
        Sanitized filename safe for all operating systems
    """
    # Replace spaces with underscores
    filename = filename.replace(' ', '_')
    
    # Remove or replace invalid characters
    invalid_chars = '<>:"/\\|?*'
    for char in invalid_chars:
        filename = filename.replace(char, '')
    
    # Limit length and remove trailing periods/spaces
    filename = filename[:255].rstrip('. ')
    
    return filename

def get_desktop_path(filename: str) -> str:
    """
    Get the full path to save a file on the user's desktop.
    
    Args:
        filename: Name of the file (will be sanitized)
    
    Returns:
        Full path to the file on the desktop
    """
    # Try common Desktop folder names
    possible_desktop_paths = [
        os.path.join(os.path.expanduser('~'), 'Desktop'),
        os.path.join(os.path.expanduser('~'), 'desktop'),
        # Add more potential paths if needed
    ]
    
    desktop_path = None
    for path in possible_desktop_paths:
        if os.path.exists(path) and os.path.isdir(path):
            desktop_path = path
            break
    
    if desktop_path is None:
        print(f"Warning: Could not find Desktop directory. Using home directory instead.")
        desktop_path = os.path.expanduser('~')
    
    full_path = os.path.join(desktop_path, sanitize_filename(filename))
    
    # Ensure the parent directory exists
    os.makedirs(os.path.dirname(full_path), exist_ok=True)
    
    print(f"File will be saved to: {full_path}")
    return full_path

# YouTube Utilities
class YouTubeMetadata:
    """Class to hold YouTube video metadata."""
    def __init__(self, data: dict):
        self.id: str = data.get('id', '')
        self.title: str = data.get('title', 'Untitled')
        self.author: str = data.get('uploader', 'Unknown')
        self.duration: int = data.get('duration', 0)
        self.view_count: int = data.get('view_count', 0)
        self.description: str = data.get('description', '')
        self.upload_date: str = data.get('upload_date', '')
        
    def get_safe_title(self) -> str:
        """Get a filesystem-safe version of the video title."""
        return sanitize_filename(self.title)
    
    def get_filename_prefix(self) -> str:
        """Get a standard filename prefix using ID and safe title."""
        return f"{self.id}-{self.get_safe_title()}"
    
    def __str__(self) -> str:
        return f"{self.title} by {self.author} ({self.id})"

def get_video_metadata(url: str) -> Optional[YouTubeMetadata]:
    """
    Get metadata for a YouTube video using yt-dlp.
    
    Args:
        url: YouTube video URL
    
    Returns:
        YouTubeMetadata object, or None if retrieval failed
    """
    json_output = run_command(f"yt-dlp --skip-download --print-json {url}")
    if not json_output:
        return None
    
    try:
        data = json.loads(json_output)
        return YouTubeMetadata(data)
    except (json.JSONDecodeError, KeyError) as e:
        print(f"Error parsing video metadata: {e}")
        return None

def get_video_id(url: str) -> Optional[str]:
    """
    Extract video ID from a YouTube URL.
    
    Args:
        url: YouTube video URL
    
    Returns:
        Video ID string, or None if not found
    """
    try:
        return re.search(r"(?<=v=)[^&#]+", url).group(0)
    except (AttributeError, TypeError):
        print("Invalid YouTube URL.")
        return None

def get_transcript(url: str, detailed: bool = False) -> Optional[str]:
    """
    Get the transcript of a YouTube video.
    
    Args:
        url: YouTube video URL
        detailed: If True, returns full subtitle data including timestamps.
                 If False (default), returns a simplified transcript better suited for AI processing.
    
    Returns:
        Video transcript text, or None if not available
    
    Example:
        >>> # Get simple transcript
        >>> transcript = get_transcript("https://youtube.com/watch?v=...")
        >>> print(transcript)
        'This is the video content...'
        
        >>> # Get detailed transcript with timestamps
        >>> detailed = get_transcript("https://youtube.com/watch?v=...", detailed=True)
        >>> print(detailed)
        '[00:00:00] This is the video content...'
    """
    if detailed:
        # Use yt-dlp for detailed transcript with timestamps
        json_output = run_command(f"yt-dlp --write-auto-subs --skip-download --sub-lang en --print-json {url}")
        if not json_output:
            return None
        
        try:
            parsed = json.loads(json_output)
            sub_url = parsed["automatic_captions"]["en"][0]["url"]
            transcript = run_command(f"curl {sub_url}")
            if not transcript:
                return None
            
            # TODO: Parse VTT format into a more readable timestamped format
            # This could be enhanced to return a structured format with timestamps
            return transcript
            
        except (KeyError, IndexError, json.JSONDecodeError):
            print("No English subtitles found.")
            return None
    else:
        # Use simpler transcript format better suited for AI processing
        video_id = get_video_id(url)
        if not video_id:
            return None
            
        # Check if we have a cached version
        cached = load_artifact('transcripts', f"{video_id}.txt")
        if cached:
            return cached
            
        # Get transcript using yt command
        transcript = run_command(f"yt --transcript {url}")
        if transcript:
            # Cache the transcript for future use
            save_artifact('transcripts', f"{video_id}.txt", transcript)
            return transcript
            
        return None
