#!/usr/bin/env python3
"""
core.py
Core backend module for Multi-Agent Story Generator
Contains shared functionality, constants, and classes used by both CLI and TUI versions.
"""

import json
import re
import pathlib
import datetime as dt
import random
import hashlib
import openai
import time
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from enum import Enum
from model_performance_tracker import model_tracker
from context_manager import ContextWindowManager, TokenCountMethod

# ────────────────────────────  Custom Exceptions  ────────────────────────────
class MultiAgentError(Exception):
    """Base exception class for Multi-Agent Story Generator."""
    pass

class LMStudioConnectionError(MultiAgentError):
    """Raised when unable to connect to LM Studio."""
    pass

class CharacterLoadError(MultiAgentError):
    """Raised when character file cannot be loaded or is invalid."""
    pass

class ModelError(MultiAgentError):
    """Raised when model API call fails."""
    pass

class FileOperationError(MultiAgentError):
    """Raised when file operations fail."""
    pass

class ValidationError(MultiAgentError):
    """Raised when input validation fails."""
    pass

# ────────────────────────────  Configuration  ────────────────────────────
LMSTUDIO_BASE_URL: str = "http://localhost:1234/v1"
DEFAULT_TEMP: float = 0.7

# Directory structure
STORIES_DIR: pathlib.Path = pathlib.Path("stories")
PRESETS_DIR: pathlib.Path = pathlib.Path("presets")
TEMPLATES_DIR: pathlib.Path = pathlib.Path("templates")
CHARACTERS_DIR: pathlib.Path = pathlib.Path("characters")
PROMPTS_DIR: pathlib.Path = pathlib.Path("prompts")
MARKDOWN_DIR: pathlib.Path = pathlib.Path("markdown")
SETTINGS_DIR: pathlib.Path = pathlib.Path("settings")
MODEL_PRESETS_DIR: pathlib.Path = pathlib.Path("model_presets")

# Create all directories with error handling
for directory in [STORIES_DIR, PRESETS_DIR, TEMPLATES_DIR, CHARACTERS_DIR, PROMPTS_DIR, MARKDOWN_DIR, SETTINGS_DIR, MODEL_PRESETS_DIR]:
    try:
        directory.mkdir(exist_ok=True)
        # Ensure generated subdirectory exists for markdown
        if directory == MARKDOWN_DIR:
            (directory / "generated").mkdir(exist_ok=True)
    except PermissionError as e:
        raise FileOperationError(f"Permission denied creating directory {directory}: {e}")
    except OSError as e:
        raise FileOperationError(f"Failed to create directory {directory}: {e}")

# Initialize OpenAI client
client = openai.OpenAI(
    base_url=LMSTUDIO_BASE_URL,
    api_key="lm-studio"
)

# ────────────────────────────  Constants  ────────────────────────────
CHARACTER_EMOJIS: Dict[str, str] = {
    'bot': '🤖', 'ai': '🤖', 'robo': '🤖', 'cyber': '🤖',
    'wizard': '🧙', 'mage': '🧙', 'witch': '🧙', 'magic': '✨',
    'knight': '⚔️', 'warrior': '⚔️', 'fighter': '⚔️', 'guard': '🛡️',
    'cat': '🐱', 'dog': '🐶', 'wolf': '🐺', 'fox': '🦊',
    'dragon': '🐉', 'demon': '👹', 'angel': '👼', 'ghost': '👻',
    'pirate': '🏴‍☠️', 'ninja': '🥷', 'spy': '🕵️', 'detective': '🔍',
    'scientist': '🧬', 'doctor': '👩‍⚕️', 'professor': '👨‍🏫', 'teacher': '📚',
    'chef': '👨‍🍳', 'artist': '🎨', 'musician': '🎵', 'bard': '🎭'
}

STORY_GENRES: Dict[str, List[str]] = {
    'adventure': ['🗺️', '⚔️', '🏰', '🌋', '🦄'],
    'mystery': ['🔍', '🕵️', '🔐', '📰', '🌙'],
    'romance': ['💕', '🌹', '💖', '🌅', '✨'],
    'horror': ['👻', '🦇', '🌙', '⚰️', '💀'],
    'sci-fi': ['🚀', '👽', '🛸', '🌌', '🤖'],
    'fantasy': ['🧙', '🐉', '⚔️', '🏰', '✨'],
    'comedy': ['😂', '🎭', '🎪', '🤡', '🎈']
}

# Filename template variables
FILENAME_VARIABLES: Dict[str, str] = {
    '{mode}': 'Mode (chat/story)',
    '{initials}': 'Character initials (AB, ABC, etc)',
    '{char1}': 'First character name',
    '{char_count}': 'Number of characters',
    '{turns}': 'Number of turns (chat only)',
    '{parts}': 'Number of parts (story only)',
    '{YYYY}': 'Year (2025)',
    '{MM}': 'Month (01-12)',
    '{DD}': 'Day (01-31)',
    '{HH}': 'Hour (00-23)',
    '{mm}': 'Minute (00-59)',
    '{MMDD}': 'Month-Day (0122)',
    '{HHMM}': 'Hour-Minute (1430)',
    '{timestamp}': 'Unix timestamp',
    '{session}': 'Session ID (8 chars)',
    '{genre}': 'Detected genre (story only)',
    '{random}': 'Random 4-digit number'
}

# Default filename templates
DEFAULT_FILENAME_TEMPLATES: Dict[str, str] = {
    'chat': '{initials}_{mode}_{MMDD}_{HHMM}',
    'story': '{initials}_{mode}_{MMDD}_{HHMM}'
}

# ────────────────────────────  Data Classes  ────────────────────────────
class Mode(Enum):
    CHAT = "chat"
    STORY = "story"

class Tab(Enum):
    MAIN = "main"
    QUEUE = "queue"
    CHARACTERS = "characters"
    PRESETS = "presets"
    SETTINGS = "settings"

@dataclass
class Character:
    name: str
    model: str
    system_prompt: str
    params: Dict = field(default_factory=dict)
    cot: bool = False
    emoji: str = "🎭"
    context_limit: int = 4096

@dataclass
class SessionConfig:
    mode: Mode
    characters: List[Character]
    turns: Optional[int] = None
    parts: Optional[int] = None
    scene: Optional[str] = None
    prompt: Optional[str] = None
    editor: Optional[Character] = None

@dataclass
class Task:
    type: str
    config: SessionConfig
    id: str = field(default_factory=lambda: hashlib.md5(str(dt.datetime.now()).encode()).hexdigest()[:8])
    status: str = "queued"
    progress: float = 0.0
    created_at: dt.datetime = field(default_factory=dt.datetime.now)
    completed_at: Optional[dt.datetime] = None
    result: Optional[str] = None

# ────────────────────────────  Helper Functions  ────────────────────────────
def get_character_emoji(name: str) -> str:
    """Get emoji for character based on name.
    
    Searches through CHARACTER_EMOJIS dictionary for keywords that match
    the character name. If no match is found, returns a random fallback emoji.
    
    Args:
        name: The character name to analyze
        
    Returns:
        A single emoji character appropriate for the character
    """
    name_lower = name.lower()
    for keyword, emoji in CHARACTER_EMOJIS.items():
        if keyword in name_lower:
            return emoji
    fallbacks = ['🎭', '👤', '🌟', '💫', '🎪', '🎨', '🎯', '🎲']
    return random.choice(fallbacks)

def strip_thought(text: str) -> str:
    """Remove THOUGHT: sections from Chain of Thought (CoT) model responses.
    
    Parses CoT responses that contain both THOUGHT: and SAY: sections,
    extracting only the SAY: portion for display to users.
    
    Args:
        text: Raw model response that may contain CoT formatting
        
    Returns:
        Cleaned text with only the speaking portion
    """
    if "thought:" in text.lower() and "say:" in text.lower():
        text = re.sub(r"(?is)thought:.*?say:\s*", "", text)
    return re.sub(r"(?i)^say:\s*", "", text).strip()

def format_speaker_dialog(text: str, speaker_name: str) -> str:
    """Format dialog text to use consistent markdown speaker formatting.
    
    If the text starts with 'SpeakerName:', converts it to bold markdown
    formatting: **SpeakerName:** text
    
    Args:
        text: The dialog text to format
        speaker_name: Name of the character speaking
        
    Returns:
        Formatted text with consistent speaker name styling
    """
    pattern = rf"^{re.escape(speaker_name)}\s*:\s*"
    if re.match(pattern, text, re.IGNORECASE):
        cleaned_text = re.sub(pattern, "", text, flags=re.IGNORECASE).strip()
        return f"**{speaker_name}:** {cleaned_text}"
    return text

def detect_story_genre(prompt: str) -> List[str]:
    """Detect story genre from prompt text and return appropriate emojis.
    
    Analyzes the story prompt for genre-specific keywords and returns
    corresponding emojis from the STORY_GENRES dictionary.
    
    Args:
        prompt: The story prompt text to analyze
        
    Returns:
        List of emoji strings representing detected genres (max 3),
        defaults to ['📖', '✨'] if no genres detected
    """
    prompt_lower = prompt.lower()
    detected_emojis = []
    
    genre_keywords: Dict[str, List[str]] = {
        'adventure': ['adventure', 'quest', 'journey', 'explore', 'treasure', 'mountain', 'forest'],
        'mystery': ['mystery', 'detective', 'murder', 'clue', 'secret', 'hidden', 'investigate'],
        'romance': ['love', 'romance', 'heart', 'wedding', 'date', 'kiss', 'romantic'],
        'horror': ['horror', 'scary', 'ghost', 'demon', 'dark', 'nightmare', 'haunted'],
        'sci-fi': ['space', 'alien', 'robot', 'future', 'technology', 'spaceship', 'cyber'],
        'fantasy': ['magic', 'wizard', 'dragon', 'kingdom', 'spell', 'enchanted', 'fairy'],
        'comedy': ['funny', 'comedy', 'laugh', 'joke', 'silly', 'humor', 'comic']
    }
    
    for genre, keywords in genre_keywords.items():
        if any(keyword in prompt_lower for keyword in keywords):
            detected_emojis.extend(STORY_GENRES[genre][:2])  # Take first 2 emojis
    
    return detected_emojis[:3] if detected_emojis else ['📖', '✨']  # Default book emojis

def estimate_reading_time(text: str) -> str:
    """Estimate reading time based on word count using 200 WPM average.
    
    Calculates approximate reading time for generated content,
    useful for content metadata and user expectations.
    
    Args:
        text: The text content to analyze
        
    Returns:
        Formatted string like '~5 min read' or '~1h 30m read'
    """
    words = len(text.split())
    minutes = max(1, words // 200)
    if minutes == 1:
        return "~1 min read"
    elif minutes < 60:
        return f"~{minutes} min read"
    else:
        hours = minutes // 60
        remaining_mins = minutes % 60
        if remaining_mins == 0:
            return f"~{hours}h read"
        else:
            return f"~{hours}h {remaining_mins}m read"

def generate_session_id() -> str:
    """Generate a unique session ID based on current timestamp.
    
    Creates an 8-character hexadecimal ID using MD5 hash of current datetime.
    Used for session tracking and file naming.
    
    Returns:
        8-character unique session identifier
    """
    return hashlib.md5(str(dt.datetime.now()).encode()).hexdigest()[:8]

def test_connection() -> bool:
    """Test connection to LM Studio API server.
    
    Attempts to list available models to verify the connection is working.
    
    Returns:
        True if connection successful, False otherwise
        
    Raises:
        LMStudioConnectionError: If connection fails and error handling is strict
    """
    try:
        client.models.list()
        return True
    except (ConnectionError, TimeoutError) as e:
        # Network-related connection failures
        return False
    except Exception as e:
        # Other API-related failures
        return False

def check_duplicate_response(new_response: str, last_response: str) -> bool:
    """Check if the new response is identical to the previous one.
    
    Compares stripped versions of responses to detect when models
    are generating identical content, which may indicate generation issues.
    
    Args:
        new_response: The newly generated response text
        last_response: The previous response for comparison
        
    Returns:
        True if responses are identical (after stripping whitespace)
    """
    if not last_response:
        return False
    
    # Strip whitespace and compare
    new_clean = new_response.strip()
    last_clean = last_response.strip()
    
    return new_clean == last_clean

# ────────────────────────────  Character Loading  ────────────────────────────
def load_character_sheet(path: pathlib.Path) -> Character:
    """Load character configuration from a JSON file.
    
    Parses character JSON files containing model, lore, and sampling parameters.
    Automatically generates system prompts from lore data and adds CoT formatting
    if enabled.
    
    Args:
        path: Path to the character JSON file
        
    Returns:
        Character object with loaded configuration
        
    Raises:
        CharacterLoadError: If file doesn't exist, is invalid JSON, or missing required fields
    """
    if not path.exists():
        raise CharacterLoadError(f"Character sheet not found: {path}")
    
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise CharacterLoadError(f"Invalid JSON in {path}: {e}")
    except Exception as e:
        raise CharacterLoadError(f"Failed to read {path}: {e}")
    
    if "model" not in data:
        raise CharacterLoadError(f'"model" key missing in {path}')
    
    # Extract character name
    char_name = path.stem
    if "lore" in data and isinstance(data["lore"], dict):
        char_name = data["lore"].get("name", data["lore"].get("Name", char_name))
    
    # Build system prompt
    lore = json.dumps({k: v for k, v in data.items() if k not in ["model", "sampling", "cot"]}, 
                      indent=2, ensure_ascii=False)
    system_prompt = lore
    
    if data.get("cot", False):
        system_prompt += "\n\n---\nWhen you answer, use EXACTLY this template:\n\nTHOUGHT:\n<your private reasoning here>\n\nSAY:\n<what your character says aloud>"
    
    return Character(
        name=char_name,
        model=data["model"],
        system_prompt=system_prompt,
        params=data.get("sampling", {}),
        cot=data.get("cot", False),
        emoji=get_character_emoji(char_name),
        context_limit=data.get("context_limit", 4096)
    )

# ────────────────────────────  Filename Generation  ────────────────────────────
def create_filename_from_template(template: str, mode: str, char_names: List[str], meta: Dict[str, Any]) -> str:
    """Create a filename using a template string and session metadata.
    
    Replaces template variables with actual values from the current session.
    Supports date/time formatting, character info, and content metadata.
    
    Args:
        template: Template string with variables like {mode}, {initials}, etc.
        mode: Generation mode ('chat' or 'story')
        char_names: List of character names participating
        meta: Dictionary containing session metadata (turns, parts, prompt, etc.)
        
    Returns:
        Filename string with variables replaced and illegal characters cleaned
    """
    now = dt.datetime.now()
    # Filter out empty names and get valid character names
    valid_names = [name for name in (char_names or []) if name and name.strip()]
    initials = "".join([name[0].upper() for name in valid_names[:4]]) if valid_names else "ANON"
    char1 = valid_names[0] if valid_names else "Anonymous"
    char_count = str(len(valid_names))
    turns = str(meta.get('turns', '')) if meta.get('turns') is not None else ""
    parts = str(meta.get('parts', '')) if meta.get('parts') is not None else ""
    genre = ""
    if mode == "story":
        genre_emojis = detect_story_genre(meta.get('prompt', ''))
        genre = "".join(genre_emojis)
    
    filename = template
    filename = filename.replace("{mode}", mode)
    filename = filename.replace("{initials}", initials)
    filename = filename.replace("{char1}", char1)
    filename = filename.replace("{char_count}", char_count)
    filename = filename.replace("{turns}", turns)
    filename = filename.replace("{parts}", parts)
    filename = filename.replace("{YYYY}", now.strftime("%Y"))
    filename = filename.replace("{MM}", now.strftime("%m"))
    filename = filename.replace("{DD}", now.strftime("%d"))
    filename = filename.replace("{HH}", now.strftime("%H"))
    filename = filename.replace("{mm}", now.strftime("%M"))
    filename = filename.replace("{MMDD}", now.strftime("%m%d"))
    filename = filename.replace("{HHMM}", now.strftime("%H%M"))
    filename = filename.replace("{timestamp}", str(int(now.timestamp())))
    filename = filename.replace("{session}", generate_session_id())
    filename = filename.replace("{genre}", genre)
    filename = filename.replace("{random}", str(random.randint(1000, 9999)))
    
    # Remove any forbidden filename characters
    filename = re.sub(r'[\\/*?:"<>|]', '_', filename)
    return filename

# ────────────────────────────  AI Processing  ────────────────────────────
def chat_call(character: Character, history: List[Dict[str, str]], user_msg: str) -> str:
    """Make a chat completion API call with proper parameter handling.
    
    Sends a request to the LM Studio API with the character's configuration,
    conversation history, and new user message. Handles both standard OpenAI
    parameters and LM Studio-specific parameters. Uses context window management
    to ensure the conversation fits within the model's token limits.
    
    Args:
        character: Character object containing model and parameters
        history: List of previous messages in conversation format
        user_msg: New user message to add to conversation
        
    Returns:
        Generated response text from the model
        
    Raises:
        ModelError: If API call fails or returns empty response
    """
    # Create context window manager with character's context limit
    context_manager = ContextWindowManager(
        max_tokens=character.context_limit,
        reserve_tokens=500,  # Reserve tokens for response generation
        method=TokenCountMethod.SIMPLE
    )
    
    # Prepare all messages including the new user message
    all_messages = history + [{"role": "user", "content": user_msg}]
    
    # Use context manager to prepare messages that fit within token limits
    msgs, token_info = context_manager.prepare_messages(all_messages, character.system_prompt)
    
    # Log context management info for debugging
    if token_info.truncated:
        print(f"Context truncated: {token_info.original_count} -> {token_info.count} tokens")
    else:
        print(f"Context usage: {token_info.count} tokens (limit: {character.context_limit})")
    
    # Build request parameters with only supported OpenAI API params
    params: Dict[str, Any] = {
        "model": character.model,
        "messages": msgs,
        "temperature": character.params.get("temperature", DEFAULT_TEMP),
    }
    
    # Add other standard OpenAI API parameters if they exist
    supported_params = ["top_p", "max_tokens", "frequency_penalty", "presence_penalty", "stop"]
    for key in supported_params:
        if key in character.params:
            params[key] = character.params[key]
    
    # Handle LM Studio specific params via extra_body if any unsupported params exist
    unsupported_params: Dict[str, Any] = {}
    lm_studio_params = ["top_k", "repeat_penalty", "min_p", "typical_p"]
    for key in lm_studio_params:
        if key in character.params:
            unsupported_params[key] = character.params[key]
    
    if unsupported_params:
        params["extra_body"] = unsupported_params
    
    # Start timing the generation
    start_time = time.time()
    
    try:
        response = client.chat.completions.create(**params)
        generation_time = time.time() - start_time
        
        result = response.choices[0].message.content
        if result is None:
            # Track failed generation
            model_tracker.track_generation(
                model_name=character.model,
                generation_time=generation_time,
                response_text="",
                success=False,
                error_message="Model returned empty response",
                model_params=params
            )
            raise ModelError("Model returned empty response")
        
        # Extract token usage if available
        token_usage = None
        if hasattr(response, 'usage') and response.usage:
            token_usage = {
                'prompt_tokens': response.usage.prompt_tokens,
                'completion_tokens': response.usage.completion_tokens,
                'total_tokens': response.usage.total_tokens
            }
        
        # Track successful generation
        model_tracker.track_generation(
            model_name=character.model,
            generation_time=generation_time,
            response_text=result,
            success=True,
            model_params=params,
            token_usage=token_usage
        )
        
        return result.strip()
    except Exception as e:
        generation_time = time.time() - start_time
        
        # Track failed generation
        model_tracker.track_generation(
            model_name=character.model,
            generation_time=generation_time,
            response_text="",
            success=False,
            error_message=str(e),
            model_params=params
        )
        
        raise ModelError(f"Error calling model '{character.model}': {e}")

def editor_clean(editor_char: Character, text: str) -> str:
    """Clean text using an editor character with specific sanitization instructions.
    
    Uses a low-temperature model call to remove repetitive content, meta-commentary,
    and other issues while preserving the original creative content and style.
    
    Args:
        editor_char: Character configured to act as text editor
        text: Raw text content to clean
        
    Returns:
        Cleaned text with problems removed, or original text if cleaning fails
    """
    prompt = f"""You are a careful text sanitizer. Your job is to clean the following text by:
- Removing repetitive loops where the model repeats itself
- Removing meta-commentary or breaking character
- Removing nonsensical gibberish
- DO NOT change the actual story content, plot, or creative elements
- DO NOT rewrite or improve the story - only remove problematic parts
- Preserve the original creative voice and style

Return only the cleaned text with problems removed.

===
{text}
==="""
    
    # Start timing the generation
    start_time = time.time()
    
    try:
        response = client.chat.completions.create(
            model=editor_char.model,
            messages=[
                {"role": "system", "content": "You are a careful, low-temperature text sanitizer. Only remove problems, do not rewrite."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.2
        )
        generation_time = time.time() - start_time
        
        result = response.choices[0].message.content
        cleaned_text = result.strip() if result else text
        
        # Extract token usage if available
        token_usage = None
        if hasattr(response, 'usage') and response.usage:
            token_usage = {
                'prompt_tokens': response.usage.prompt_tokens,
                'completion_tokens': response.usage.completion_tokens,
                'total_tokens': response.usage.total_tokens
            }
        
        # Track successful editor generation
        model_tracker.track_generation(
            model_name=editor_char.model,
            generation_time=generation_time,
            response_text=cleaned_text,
            success=True,
            model_params={"temperature": 0.2, "task": "text_sanitization"},
            token_usage=token_usage
        )
        
        return cleaned_text
    except Exception as e:
        generation_time = time.time() - start_time
        
        # Track failed editor generation
        model_tracker.track_generation(
            model_name=editor_char.model,
            generation_time=generation_time,
            response_text="",
            success=False,
            error_message=str(e),
            model_params={"temperature": 0.2, "task": "text_sanitization"}
        )
        
        return text  # Return original if editing fails

# ────────────────────────────  File Operations  ────────────────────────────
def save_conversation_analysis(chars: List[Character], content: str, filename: str) -> None:
    """Save statistical analysis of generated conversation or story content.
    
    Creates a JSON file with word count, character count, estimated reading time,
    and basic sentiment analysis alongside the main content file.
    
    Args:
        chars: List of characters that participated in generation
        content: The generated text content to analyze
        filename: Base filename for the analysis file (without extension)
    """
    try:
        word_count = len(content.split())
        char_count = len(content)
        
        # Simple sentiment words
        positive_words = ['good', 'great', 'happy', 'love', 'wonderful', 'amazing', 'excellent']
        negative_words = ['bad', 'terrible', 'hate', 'awful', 'horrible', 'angry', 'sad']
        
        content_lower = content.lower()
        positive_score = sum(content_lower.count(word) for word in positive_words)
        negative_score = sum(content_lower.count(word) for word in negative_words)
        
        analysis: Dict[str, Any] = {
            'generated_at': dt.datetime.now().isoformat(),
            'characters': [c.name for c in chars],
            'stats': {
                'word_count': word_count,
                'character_count': char_count,
                'reading_time': estimate_reading_time(content),
                'sentiment_positive': positive_score,
                'sentiment_negative': negative_score
            }
        }
        
        analysis_dir = MARKDOWN_DIR / "generated"
        analysis_dir.mkdir(exist_ok=True)
        analysis_file = analysis_dir / f"{filename}_analysis.json"
        with open(analysis_file, 'w', encoding='utf-8') as f:
            json.dump(analysis, f, indent=2, ensure_ascii=False)
            
    except Exception:
        pass  # Fail silently for analysis

def load_config() -> Dict[str, Any]:
    """Load application configuration from settings directory.
    
    Loads configuration from config.json if it exists, otherwise returns
    default configuration. Merges loaded config with defaults to ensure
    all required keys are present.
    
    Returns:
        Dictionary containing complete application configuration
    """
    config_file = SETTINGS_DIR / "config.json"
    default_config: Dict[str, Any] = {
        "lm_studio": {
            "base_url": LMSTUDIO_BASE_URL,
            "api_key": "lm-studio"
        },
        "defaults": {
            "temperature": DEFAULT_TEMP,
            "max_tokens": 500,
            "turns": 6,
            "parts": 4
        },
        "filename_templates": DEFAULT_FILENAME_TEMPLATES.copy()
    }
    
    if config_file.exists():
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                loaded_config = json.load(f)
                # Merge with defaults
                for key, value in loaded_config.items():
                    if isinstance(value, dict) and key in default_config:
                        default_config[key].update(value)
                    else:
                        default_config[key] = value
        except Exception:
            pass  # Use defaults if config loading fails
    
    return default_config

def save_config(config: Dict[str, Any]) -> None:
    """Save application configuration to settings directory.
    
    Writes the complete configuration dictionary to config.json in the
    settings directory. Fails silently if write operation fails.
    
    Args:
        config: Complete configuration dictionary to save
    """
    config_file = SETTINGS_DIR / "config.json"
    try:
        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
    except Exception:
        pass  # Fail silently

# ────────────────────────────  Model Preset System  ────────────────────────────
def get_deleted_presets() -> set:
    """Get the set of deleted default presets."""
    deleted_file = MODEL_PRESETS_DIR / ".deleted_defaults"
    if deleted_file.exists():
        try:
            with open(deleted_file, 'r', encoding='utf-8') as f:
                content = f.read().strip()
                return set(content.split('\n')) if content else set()
        except Exception:
            return set()
    return set()

def add_deleted_preset(preset_id: str) -> None:
    """Mark a default preset as deleted."""
    deleted_presets = get_deleted_presets()
    deleted_presets.add(preset_id)
    deleted_file = MODEL_PRESETS_DIR / ".deleted_defaults"
    try:
        with open(deleted_file, 'w', encoding='utf-8') as f:
            f.write('\n'.join(sorted(deleted_presets)))
    except Exception:
        pass  # Fail silently

def create_default_model_presets() -> None:
    """Create default model presets if they don't exist and haven't been intentionally deleted."""
    deleted_presets = get_deleted_presets()
    default_presets = {
        "balanced": {
            "name": "Balanced",
            "description": "Well-balanced settings for most characters",
            "model": "default-model",
            "cot": False,
            "context_limit": 4096,
            "sampling": {
                "temperature": 0.7,
                "top_k": 40,
                "top_p": 0.9,
                "repeat_penalty": 1.1,
                "max_tokens": 500
            },
            "response_format": None
        },
        "creative": {
            "name": "Creative",
            "description": "High creativity for storytelling and artistic characters",
            "model": "default-model",
            "cot": False,
            "context_limit": 8192,
            "sampling": {
                "temperature": 0.9,
                "top_k": 60,
                "top_p": 0.95,
                "repeat_penalty": 1.05,
                "max_tokens": 750
            },
            "response_format": None
        },
        "analytical": {
            "name": "Analytical",
            "description": "Low temperature for logical and precise characters",
            "model": "default-model",
            "cot": True,
            "context_limit": 4096,
            "sampling": {
                "temperature": 0.3,
                "top_k": 20,
                "top_p": 0.8,
                "repeat_penalty": 1.15,
                "max_tokens": 400
            },
            "response_format": None
        },
        "conversational": {
            "name": "Conversational",
            "description": "Optimized for natural dialogue and chat",
            "model": "default-model",
            "cot": False,
            "context_limit": 4096,
            "sampling": {
                "temperature": 0.6,
                "top_k": 35,
                "top_p": 0.85,
                "repeat_penalty": 1.2,
                "max_tokens": 300
            },
            "response_format": None
        },
        "chaotic": {
            "name": "Chaotic",
            "description": "High randomness for unpredictable characters",
            "model": "default-model",
            "cot": False,
            "context_limit": 6144,
            "sampling": {
                "temperature": 1.2,
                "top_k": 80,
                "top_p": 0.98,
                "repeat_penalty": 1.0,
                "max_tokens": 600
            },
            "response_format": None
        }
    }
    
    for preset_id, preset_data in default_presets.items():
        preset_file = MODEL_PRESETS_DIR / f"{preset_id}.json"
        # Only create if file doesn't exist AND preset hasn't been intentionally deleted
        if not preset_file.exists() and preset_id not in deleted_presets:
            try:
                with open(preset_file, 'w', encoding='utf-8') as f:
                    json.dump(preset_data, f, indent=2, ensure_ascii=False)
            except Exception:
                pass  # Fail silently

def load_model_presets() -> Dict[str, Dict[str, Any]]:
    """Load all model presets from the model_presets directory.
    
    Returns:
        Dictionary mapping preset IDs to preset data
    """
    presets = {}
    
    # Ensure default presets exist
    create_default_model_presets()
    
    # Load all preset files
    for preset_file in MODEL_PRESETS_DIR.glob("*.json"):
        try:
            with open(preset_file, 'r', encoding='utf-8') as f:
                preset_data = json.load(f)
                presets[preset_file.stem] = preset_data
        except Exception:
            continue  # Skip invalid files
    
    return presets

def save_model_preset(preset_id: str, preset_data: Dict[str, Any]) -> bool:
    """Save a model preset to disk.
    
    Args:
        preset_id: Unique identifier for the preset
        preset_data: Preset configuration data
        
    Returns:
        True if saved successfully, False otherwise
    """
    preset_file = MODEL_PRESETS_DIR / f"{preset_id}.json"
    try:
        with open(preset_file, 'w', encoding='utf-8') as f:
            json.dump(preset_data, f, indent=2, ensure_ascii=False)
        return True
    except Exception:
        return False

def apply_model_preset_to_character(character_data: Dict[str, Any], preset_id: str) -> Dict[str, Any]:
    """Apply a model preset to character data.
    
    Args:
        character_data: Character JSON data
        preset_id: ID of the model preset to apply
        
    Returns:
        Character data with model preset applied
        
    Raises:
        FileOperationError: If preset doesn't exist or can't be loaded
    """
    presets = load_model_presets()
    
    if preset_id not in presets:
        raise FileOperationError(f"Model preset '{preset_id}' not found")
    
    preset = presets[preset_id]
    result = character_data.copy()
    
    # Apply model preset fields
    if "model" in preset:
        result["model"] = preset["model"]
    if "cot" in preset:
        result["cot"] = preset["cot"]
    if "sampling" in preset:
        result["sampling"] = preset["sampling"].copy()
    if "response_format" in preset:
        result["response_format"] = preset["response_format"]
    
    return result

def extract_model_config_from_character(character_data: Dict[str, Any]) -> Dict[str, Any]:
    """Extract model configuration from character data.
    
    Args:
        character_data: Character JSON data
        
    Returns:
        Dictionary containing only model-related configuration
    """
    model_config = {}
    
    if "model" in character_data:
        model_config["model"] = character_data["model"]
    if "cot" in character_data:
        model_config["cot"] = character_data["cot"]
    if "sampling" in character_data:
        model_config["sampling"] = character_data["sampling"]
    if "response_format" in character_data:
        model_config["response_format"] = character_data["response_format"]
    
    return model_config