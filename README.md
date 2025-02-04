# Augments

A collection of command-line tools for enhancing your workflow with AI-powered features including YouTube transcript analysis, clipboard content processing, and more.

## Features

- 🎥 **YouTube Video Analysis**
  - Extract and analyze transcripts
  - Generate summaries and key insights
  - Create audio summaries using Text-to-Speech
  - Extract referenced links and resources
  - Save everything in a well-formatted markdown file
  - Cache transcripts for faster reuse

- 📋 **Clipboard Content Analysis**
  - Process text from your clipboard
  - Generate summaries and insights
  - Extract and validate links
  - Create audio summaries
  - Save analysis in markdown format

- 🤖 **AI Integration**
  - Optional OpenAI integration for enhanced analysis
  - Support for local LLaMA models (coming soon)
  - Fabric pattern processing for consistent results

- 📦 **Artifact Management**
  - Organized storage for all generated files
  - Automatic cleanup of old files
  - Cache system for faster processing
  - Easy access to saved content

- 🔧 **Developer-Friendly**
  - Clean, modular Python codebase
  - Easy to extend with new commands
  - Virtual environment isolation
  - Comprehensive logging and error handling
  - Extensive test coverage
  - Well-documented utilities

## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/username/Augments.git
   cd Augments
   ```

2. Run the installation script:
   ```bash
   # For zsh users
   ./install.sh --shell zsh

   # For bash users
   ./install.sh --shell bash

   # Enable debug output
   ./install.sh --shell zsh --debug
   ```

3. Create and configure your environment file:
   ```bash
   cp .env.example .env
   # Edit .env to add your API keys
   ```

4. (Optional) Set up Google Cloud Text-to-Speech for enhanced voice quality:
   - Create a Google Cloud project
   - Enable the Cloud Text-to-Speech API
   - Create a service account and download credentials
   - Set the credentials path in your .env:
     ```bash
     GOOGLE_APPLICATION_CREDENTIALS=/path/to/your/credentials.json
     ```
   Note: If Google Cloud TTS is not configured, the system will automatically fall back to using gTTS (no setup required).

## Available Commands

### youtubeWisdom
Extracts and analyzes YouTube video transcripts:
```bash
# Basic analysis
youtubeWisdom "https://www.youtube.com/watch?v=..."

# The command will:
# 1. Download and process the video transcript
# 2. Generate a summary and extract key insights
# 3. Create an audio version of the summary
# 4. Save everything in a markdown file on your Desktop
```

### clipboardAnalyze
Analyzes text from your clipboard:
```bash
# Analyze with auto-generated title
clipboardAnalyze

# Provide a custom title
clipboardAnalyze --title "My Analysis"
```

### yt
YouTube utilities for quick access to video information:
```bash
# Get video transcript
yt --transcript "https://www.youtube.com/watch?v=..."

# Get transcript in JSON format
yt --transcript "https://..." --format json

# Get transcript without saving
yt --transcript "https://..." --no-save

# Get video information
yt --info "https://..."

# Download video
yt --download "https://..."

# Download audio only
yt --download "https://..." --format audio

# List saved artifacts
yt --list transcripts
yt --list downloads
yt --list all

# Clean up old artifacts
yt --cleanup transcripts --max-age 7d
yt --cleanup downloads --max-age 24h
```

### Artifact Management
All generated files are stored in `~/.config/augments/artifacts/`:
```
~/.config/augments/artifacts/
├── transcripts/          # Video transcripts (.vtt, .srt)
├── audio/               # Generated audio files
├── downloads/           # Downloaded videos/audio
└── temp/               # Temporary files
```

You can manage artifacts using the `yt` command:
```bash
# List all artifacts
yt --list all

# Clean up old files
yt --cleanup all --max-age 7d
```

## Development

### Running Tests
```bash
# Run all tests
pytest tests/

# Run specific test file
pytest tests/test_utils.py

# Run with coverage report
pytest --cov=augments tests/

# Run tests with output
pytest -v tests/
```

### Core Utilities

The project provides several utility functions in `augments.lib.utils`:

#### Text Processing
```python
# Clean filenames
safe_name = sanitize_filename("unsafe/file:name.txt")

# Extract URLs from text
urls = extract_urls("Check out https://example.com")

# Extract code blocks
blocks = extract_code_blocks("```python\nprint('hello')\n```")
```

#### Time and Date
```python
# Format duration
time_str = format_duration(3661)  # "01:01:01"

# Format dates
date_str = format_date("20240101", "%Y%m%d", "%Y-%m-%d")

# Parse duration strings
seconds = parse_duration("7d")  # 604800
```

#### File Management
```python
# Get unique filename
unique = get_unique_filename("existing.txt")  # "existing_1.txt"

# Get artifact path
path = get_artifact_path("transcripts", "video.vtt")

# Save artifact
path = save_artifact("downloads", "video.mp4", content)

# Load artifact
content = load_artifact("transcripts", "video.vtt")

# Clean up old artifacts
cleanup_artifacts("downloads", max_age=7*86400)  # 7 days
```

### Testing

The project includes comprehensive tests for core utilities:

- **Text Processing Tests**
  - Filename sanitization
  - URL extraction
  - Code block parsing

- **Time/Date Tests**
  - Duration formatting
  - Date string conversion
  - Duration string parsing

- **File Management Tests**
  - Unique filename generation
  - Artifact path handling
  - File operations

Run the tests with:
```bash
pytest -v tests/
```

### Project Structure
```
Augments/
├── README.md
├── requirements.txt
├── setup.py              # Package configuration
├── install.sh           # Installation script
├── update.sh           # Update script
├── create_command.sh   # New command generator
├── .env.example        # Environment template
├── augments/           # Main package
│   ├── __init__.py
│   └── lib/
│       ├── __init__.py
│       └── utils.py    # Shared utilities
├── scripts/            # Command scripts
│   ├── youtube_wisdom.py
│   ├── clipboard_analyzer.py
│   ├── yt.py          # YouTube utilities
│   ├── shell/         # Shell utilities
│   │   └── logging.sh
│   ├── custom/        # User scripts
│   └── __init__.py
└── tests/             # Test suite
    ├── test_youtube_wisdom.py
    ├── test_clipboard_analyzer.py
    └── test_utils.py  # Utility tests
```

### Creating New Commands

Use the create_command.sh script to generate new command templates:
```bash
./create_command.sh myNewCommand
```

This will:
1. Create a new Python script from the template
2. Add necessary imports and boilerplate
3. Create a corresponding test file
4. Add the command to your shell configuration

### Updating the Installation

If you've made changes to the codebase:
```bash
# Quick update (reinstall package and update scripts)
./update.sh

# Complete clean reinstall
./update.sh --clean
```

## Configuration

The tools can be configured through environment variables in your `.env` file:

```env
# OpenAI Integration
OPENAI_API_KEY=your-api-key

# LLaMA Integration (coming soon)
LLAMA_MODEL_PATH=/path/to/model

# Custom Configuration
DESKTOP_PATH=/custom/path/to/desktop  # Override default Desktop path
```

## Contributing

1. Fork the repository
2. Create your feature branch
3. Write tests for your changes
4. Ensure all tests pass
5. Submit a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.