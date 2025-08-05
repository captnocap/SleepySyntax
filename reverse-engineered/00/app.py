#!/usr/bin/env python3
"""
Flask API for Multi-Agent Story Generator
Uses the same core functionality as the TUI
"""

import os
import sys
import json
import pathlib
from datetime import datetime
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from datetime import datetime as dt

# Add parent directory to path to import core module
ROOT_DIR = pathlib.Path(__file__).parent.parent.absolute()
sys.path.append(str(ROOT_DIR))

from core import (
    # Model preset functions
    load_model_presets, save_model_preset, apply_model_preset_to_character,
    create_default_model_presets,
    # Character functions
    Character,
    # Session functions
    test_connection, generate_session_id, chat_call,
    # Exceptions
    FileOperationError,
    # Config
    load_config, save_config,
    # Client for API calls
    client
)

# Use root directories instead of relative ones
CHARACTERS_DIR = ROOT_DIR / "characters"
MODEL_PRESETS_DIR = ROOT_DIR / "model_presets"
PRESETS_DIR = ROOT_DIR / "presets"
TEMPLATES_DIR = ROOT_DIR / "templates"
MARKDOWN_DIR = ROOT_DIR / "markdown"
STORIES_DIR = ROOT_DIR / "stories"
SETTINGS_DIR = ROOT_DIR / "settings"
PROMPTS_DIR = ROOT_DIR / "prompts"

# Import TUI functions for template functionality
import sys
sys.path.append(os.path.dirname(__file__))
# Note: TUI template functions are interactive and not suitable for API use
# Template functionality is implemented directly in the API endpoints

app = Flask(__name__)
CORS(app)  # Enable CORS for React frontend

# Ensure directories exist
directories = [CHARACTERS_DIR, MODEL_PRESETS_DIR, PRESETS_DIR, TEMPLATES_DIR, MARKDOWN_DIR, STORIES_DIR]
for directory in directories:
    directory.mkdir(exist_ok=True)

# Create default model presets on startup
create_default_model_presets()

# Track deleted sanitization presets to prevent recreation
DELETED_SANITIZATION_PRESETS_FILE = SETTINGS_DIR / "deleted_sanitization_presets.json"

def load_deleted_sanitization_presets():
    """Load list of sanitization presets that have been deleted by user"""
    if DELETED_SANITIZATION_PRESETS_FILE.exists():
        try:
            with open(DELETED_SANITIZATION_PRESETS_FILE, 'r', encoding='utf-8') as f:
                return set(json.load(f))
        except Exception:
            pass
    return set()

def save_deleted_sanitization_presets(deleted_presets):
    """Save list of deleted sanitization presets"""
    try:
        SETTINGS_DIR.mkdir(exist_ok=True)
        with open(DELETED_SANITIZATION_PRESETS_FILE, 'w', encoding='utf-8') as f:
            json.dump(list(deleted_presets), f, indent=2)
    except Exception as e:
        print(f"Failed to save deleted sanitization presets: {e}")

def create_sanitization_presets():
    """Create model presets specifically designed for text sanitization tasks"""
    # Load deleted presets to avoid recreating them
    deleted_presets = load_deleted_sanitization_presets()
    
    sanitization_presets = {
        "sanitizer-conservative": {
            "name": "Conservative Sanitizer",
            "description": "Very conservative text sanitizer - only removes obvious problems",
            "model": "default-model",
            "cot": False,
            "sampling": {
                "temperature": 0.1,
                "top_k": 10,
                "top_p": 0.7,
                "repeat_penalty": 1.2,
                "max_tokens": 50000
            },
            "response_format": None
        },
        "sanitizer-balanced": {
            "name": "Balanced Sanitizer", 
            "description": "Balanced sanitizer - removes problems while preserving style",
            "model": "default-model",
            "cot": False,
            "sampling": {
                "temperature": 0.2,
                "top_k": 20,
                "top_p": 0.8,
                "repeat_penalty": 1.15,
                "max_tokens": 50000
            },
            "response_format": None
        },
        "sanitizer-aggressive": {
            "name": "Aggressive Sanitizer",
            "description": "More aggressive sanitizer - removes more problematic content",
            "model": "default-model", 
            "cot": False,
            "sampling": {
                "temperature": 0.3,
                "top_k": 30,
                "top_p": 0.85,
                "repeat_penalty": 1.1,
                "max_tokens": 50000
            },
            "response_format": None
        },
        "sanitizer-editor": {
            "name": "Editor Sanitizer",
            "description": "Editor-style sanitizer with chain-of-thought reasoning",
            "model": "default-model",
            "cot": True,
            "sampling": {
                "temperature": 0.15,
                "top_k": 15,
                "top_p": 0.75,
                "repeat_penalty": 1.25,
                "max_tokens": 75000
            },
            "response_format": None
        }
    }
    
    # Save each sanitization preset (skip if deleted by user)
    for preset_id, preset_data in sanitization_presets.items():
        if preset_id in deleted_presets:
            print(f"Skipping sanitization preset {preset_id} - deleted by user")
            continue
            
        preset_file = MODEL_PRESETS_DIR / f"{preset_id}.json"
        if not preset_file.exists():  # Only create if it doesn't exist
            try:
                with open(preset_file, 'w', encoding='utf-8') as f:
                    json.dump(preset_data, f, indent=2, ensure_ascii=False)
                print(f"Created sanitization preset: {preset_id}")
            except Exception as e:
                print(f"Failed to create sanitization preset {preset_id}: {e}")

# Create sanitization-specific presets on startup
create_sanitization_presets()

def migrate_existing_sessions():
    """Migrate existing sessions to include the is_completed flag"""
    try:
        sessions_dir = STORIES_DIR / "sessions"
        if not sessions_dir.exists():
            return
        
        migrated_count = 0
        for session_file in sessions_dir.glob("*.json"):
            try:
                with open(session_file, 'r', encoding='utf-8') as f:
                    session_data = json.load(f)
                
                # Check if session needs migration
                if session_data.get('status') == 'completed' and 'is_completed' not in session_data:
                    session_data['is_completed'] = True
                    
                    # Save updated session
                    with open(session_file, 'w', encoding='utf-8') as f:
                        json.dump(session_data, f, indent=2, ensure_ascii=False)
                    
                    migrated_count += 1
                    print(f"Migrated session: {session_file.stem}")
                    
            except Exception as e:
                print(f"Failed to migrate session {session_file}: {e}")
                continue
        
        if migrated_count > 0:
            print(f"Successfully migrated {migrated_count} sessions")
    except Exception as e:
        print(f"Migration failed: {e}")

# Run migration on startup
migrate_existing_sessions()

# ────────────────────────────  New API: Session Stats, Filename Templates, Presets, Prompts  ────────────────────────────
import threading

SESSION_STATS_FILE = SETTINGS_DIR / "session_stats.json"
SESSION_STATS_LOCK = threading.Lock()

DEFAULT_SESSION_STATS = {
    "stories_generated": 0,
    "chats_completed": 0,
    "words_written": 0
}

def load_session_stats():
    if SESSION_STATS_FILE.exists():
        try:
            with open(SESSION_STATS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            pass
    return DEFAULT_SESSION_STATS.copy()

def save_session_stats(stats):
    with SESSION_STATS_LOCK:
        with open(SESSION_STATS_FILE, 'w', encoding='utf-8') as f:
            json.dump(stats, f, indent=2, ensure_ascii=False)

@app.route('/api/session-stats', methods=['GET'])
def get_session_stats():
    """Get current session statistics"""
    stats = load_session_stats()
    return jsonify(stats)

@app.route('/api/session-stats/reset', methods=['POST'])
def reset_session_stats():
    """Reset session statistics"""
    stats = DEFAULT_SESSION_STATS.copy()
    save_session_stats(stats)
    return jsonify({"message": "Session statistics reset", "stats": stats})

# Filename template management
@app.route('/api/filename-templates', methods=['GET'])
def get_filename_templates():
    config = load_config()
    templates = config.get("filename_templates", {})
    return jsonify(templates)

@app.route('/api/filename-templates', methods=['POST'])
def set_filename_templates():
    data = request.get_json()
    if not isinstance(data, dict):
        return jsonify({"error": "Invalid data format"}), 400
    config = load_config()
    config["filename_templates"] = data
    save_config(config)
    return jsonify({"message": "Filename templates updated", "filename_templates": data})

# Session preset CRUD
PRESET_EXT = ".json"

@app.route('/api/session-presets', methods=['GET'])
def list_session_presets():
    presets = {}
    for preset_file in PRESETS_DIR.glob(f"*{PRESET_EXT}"):
        try:
            with open(preset_file, 'r', encoding='utf-8') as f:
                presets[preset_file.stem] = json.load(f)
        except Exception:
            continue
    return jsonify(presets)

@app.route('/api/session-presets/<preset_id>', methods=['GET'])
def get_session_preset(preset_id):
    preset_file = PRESETS_DIR / f"{preset_id}{PRESET_EXT}"
    if not preset_file.exists():
        return jsonify({"error": "Preset not found"}), 404
    with open(preset_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return jsonify(data)

@app.route('/api/session-presets', methods=['POST'])
def create_session_preset():
    data = request.get_json()
    if not data.get('name'):
        return jsonify({'error': 'Preset name is required'}), 400
    preset_id = data['name']
    preset_file = PRESETS_DIR / f"{preset_id}{PRESET_EXT}"
    if preset_file.exists():
        return jsonify({'error': 'Preset already exists'}), 400
    with open(preset_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    return jsonify({'message': 'Preset created', 'id': preset_id}), 201

@app.route('/api/session-presets/<preset_id>', methods=['PUT'])
def update_session_preset(preset_id):
    data = request.get_json()
    preset_file = PRESETS_DIR / f"{preset_id}{PRESET_EXT}"
    if not preset_file.exists():
        return jsonify({'error': 'Preset not found'}), 404
    with open(preset_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    return jsonify({'message': 'Preset updated'})

@app.route('/api/session-presets/<preset_id>', methods=['DELETE'])
def delete_session_preset(preset_id):
    preset_file = PRESETS_DIR / f"{preset_id}{PRESET_EXT}"
    if not preset_file.exists():
        return jsonify({'error': 'Preset not found'}), 404
    preset_file.unlink()
    return jsonify({'message': 'Preset deleted'})

# Prompt file listing
@app.route('/api/prompts/<mode>', methods=['GET'])
def list_prompt_files(mode):
    if mode not in ['chat', 'story']:
        return jsonify({'error': 'Invalid mode'}), 400
    
    files = []
    prompt_dir = PROMPTS_DIR / mode
    if prompt_dir.exists():
        files.extend([f.name for f in prompt_dir.glob('*.txt')])
        
    # Also include general templates
    if TEMPLATES_DIR.exists():
        files.extend([f.name for f in TEMPLATES_DIR.glob('*.txt')])
        
    return jsonify({'prompts': sorted(list(set(files)))})

@app.route('/api/prompts/<mode>/<filename>', methods=['GET'])
def get_prompt_file_content(mode, filename):
    if mode not in ['chat', 'story']:
        return jsonify({'error': 'Invalid mode'}), 400
    
    # Basic sanitization
    if '..' in filename or filename.startswith('/'):
        return jsonify({'error': 'Invalid filename'}), 400

    prompt_dir = PROMPTS_DIR / mode
    prompt_file = prompt_dir / filename

    if not prompt_file.is_file():
        template_file = TEMPLATES_DIR / filename
        if template_file.is_file():
            prompt_file = template_file
        else:
            return jsonify({'error': 'Prompt file not found'}), 404

    try:
        content = prompt_file.read_text(encoding='utf-8')
        return jsonify({'content': content})
    except Exception as e:
        return jsonify({'error': f'Error reading file: {str(e)}'}), 500

# Prompt preset CRUD
PROMPT_PRESET_EXT = ".txt"

@app.route('/api/prompt-presets', methods=['GET'])
def list_prompt_presets():
    presets = {'chat': {}, 'story': {}}
    
    for mode in ['chat', 'story']:
        preset_dir = PROMPTS_DIR / mode
        if preset_dir.exists():
            for preset_file in preset_dir.glob(f"*{PROMPT_PRESET_EXT}"):
                try:
                    with open(preset_file, 'r', encoding='utf-8') as f:
                        content = f.read()
                        presets[mode][preset_file.stem] = {
                            'name': preset_file.stem,
                            'content': content,
                            'mode': mode
                        }
                except Exception:
                    continue
    
    return jsonify(presets)

@app.route('/api/prompt-presets/<mode>', methods=['GET'])
def list_prompt_presets_by_mode(mode):
    if mode not in ['chat', 'story']:
        return jsonify({'error': 'Invalid mode'}), 400
    
    presets = {}
    preset_dir = PROMPTS_DIR / mode
    if preset_dir.exists():
        for preset_file in preset_dir.glob(f"*{PROMPT_PRESET_EXT}"):
            try:
                with open(preset_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    presets[preset_file.stem] = {
                        'name': preset_file.stem,
                        'content': content,
                        'mode': mode
                    }
            except Exception:
                continue
    
    return jsonify(presets)

@app.route('/api/prompt-presets/<mode>/<preset_id>', methods=['GET'])
def get_prompt_preset(mode, preset_id):
    if mode not in ['chat', 'story']:
        return jsonify({'error': 'Invalid mode'}), 400
    
    preset_file = PROMPTS_DIR / mode / f"{preset_id}{PROMPT_PRESET_EXT}"
    if not preset_file.exists():
        return jsonify({'error': 'Prompt preset not found'}), 404
    
    with open(preset_file, 'r', encoding='utf-8') as f:
        content = f.read()
    return jsonify({
        'name': preset_id,
        'content': content,
        'mode': mode
    })

@app.route('/api/prompt-presets/<mode>', methods=['POST'])
def create_prompt_preset(mode):
    if mode not in ['chat', 'story']:
        return jsonify({'error': 'Invalid mode'}), 400
    
    data = request.get_json()
    if not data.get('name'):
        return jsonify({'error': 'Preset name is required'}), 400
    
    preset_id = data['name']
    preset_dir = PROMPTS_DIR / mode
    preset_dir.mkdir(parents=True, exist_ok=True)
    preset_file = preset_dir / f"{preset_id}{PROMPT_PRESET_EXT}"
    
    if preset_file.exists():
        return jsonify({'error': 'Preset already exists'}), 400
    
    content = data.get('content', '')
    with open(preset_file, 'w', encoding='utf-8') as f:
        f.write(content)
    
    return jsonify({'message': 'Prompt preset created', 'id': preset_id}), 201

@app.route('/api/prompt-presets/<mode>/<preset_id>', methods=['PUT'])
def update_prompt_preset(mode, preset_id):
    if mode not in ['chat', 'story']:
        return jsonify({'error': 'Invalid mode'}), 400
    
    data = request.get_json()
    preset_file = PROMPTS_DIR / mode / f"{preset_id}{PROMPT_PRESET_EXT}"
    
    if not preset_file.exists():
        return jsonify({'error': 'Prompt preset not found'}), 404
    
    content = data.get('content', '')
    with open(preset_file, 'w', encoding='utf-8') as f:
        f.write(content)
    
    return jsonify({'message': 'Prompt preset updated'})

@app.route('/api/prompt-presets/<mode>/<preset_id>', methods=['DELETE'])
def delete_prompt_preset(mode, preset_id):
    if mode not in ['chat', 'story']:
        return jsonify({'error': 'Invalid mode'}), 400
    
    preset_file = PROMPTS_DIR / mode / f"{preset_id}{PROMPT_PRESET_EXT}"
    if not preset_file.exists():
        return jsonify({'error': 'Prompt preset not found'}), 404
    
    preset_file.unlink()
    return jsonify({'message': 'Prompt preset deleted'})

# Quick Chat History
QUICK_CHATS_DIR = STORIES_DIR / "quick_chats"
QUICK_CHATS_DIR.mkdir(exist_ok=True)

@app.route('/api/quick-chats', methods=['GET'])
def get_quick_chats():
    """Get all saved quick chats"""
    try:
        chats = []
        for chat_file in QUICK_CHATS_DIR.glob("*.json"):
            try:
                with open(chat_file, 'r', encoding='utf-8') as f:
                    chat_data = json.load(f)
                
                messages = chat_data.get('messages', [])
                last_message = ''
                updated_at = chat_data.get('created_at')
                
                # Get last message content and update time
                if messages:
                    last_msg = messages[-1]
                    last_message = last_msg.get('content', '')
                    # Use timestamp from last message as updated_at (keep as ISO string)
                    if last_msg.get('timestamp'):
                        updated_at = last_msg.get('timestamp')
                    else:
                        # Fallback to file modification time as ISO string
                        import os
                        from datetime import datetime
                        mtime = os.path.getmtime(chat_file)
                        updated_at = datetime.fromtimestamp(mtime).isoformat() + 'Z'
                
                chats.append({
                    'id': chat_file.stem,
                    'name': chat_data.get('name', 'Unnamed Chat'),
                    'character': chat_data.get('character', {}),
                    'messages': messages,
                    'message_count': len(messages),
                    'last_message': last_message,
                    'created_at': chat_data.get('created_at'),
                    'updated_at': updated_at,
                    'preset': chat_data.get('preset'),
                    'model': chat_data.get('model'),
                    'modelConfig': chat_data.get('modelConfig'),
                    'file_path': str(chat_file)
                })
            except Exception as e:
                app.logger.warning(f"Failed to load quick chat {chat_file}: {e}")
                continue
        
        # Sort by most recent activity (updated_at), newest first
        chats.sort(key=lambda x: x.get('updated_at', x.get('created_at', '')), reverse=True)
        return jsonify(chats)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/quick-chats/<chat_id>', methods=['GET'])
def get_quick_chat(chat_id):
    """Get a specific saved quick chat"""
    try:
        chat_file = QUICK_CHATS_DIR / f"{chat_id}.json"
        if not chat_file.exists():
            return jsonify({'error': 'Quick chat not found'}), 404
        
        with open(chat_file, 'r', encoding='utf-8') as f:
            chat_data = json.load(f)
        
        return jsonify({
            'id': chat_id,
            'name': chat_data.get('name', 'Unnamed Chat'),
            'character': chat_data.get('character', {}),
            'messages': chat_data.get('messages', []),
            'created_at': chat_data.get('created_at'),
            'preset': chat_data.get('preset'),
            'file_path': str(chat_file)
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/quick-chats', methods=['POST'])
def save_quick_chat():
    """Save a quick chat conversation"""
    try:
        data = request.get_json()
        
        # Validate required fields
        if not data.get('name'):
            return jsonify({'error': 'Chat name is required'}), 400
        if not data.get('messages'):
            return jsonify({'error': 'Messages are required'}), 400
        
        # Generate unique ID
        chat_id = generate_session_id()
        chat_file = QUICK_CHATS_DIR / f"{chat_id}.json"
        
        # Save chat data
        chat_data = {
            'id': chat_id,
            'name': data['name'],
            'character': data.get('character', {}),
            'messages': data['messages'],
            'created_at': data.get('created_at', pathlib.Path().stat().st_mtime),
            'preset': data.get('preset'),
            'model': data.get('model'),
            'modelConfig': data.get('modelConfig'),
        }
        
        with open(chat_file, 'w', encoding='utf-8') as f:
            json.dump(chat_data, f, indent=2, ensure_ascii=False)
        
        return jsonify({
            'id': chat_id,
            'message': 'Quick chat saved successfully',
            'file_path': str(chat_file)
        }), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/quick-chats/<chat_id>', methods=['DELETE'])
def delete_quick_chat(chat_id):
    """Delete a saved quick chat"""
    try:
        chat_file = QUICK_CHATS_DIR / f"{chat_id}.json"
        if not chat_file.exists():
            return jsonify({'error': 'Quick chat not found'}), 404
        
        chat_file.unlink()
        return jsonify({'message': 'Quick chat deleted successfully'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/quick-chats/<chat_id>', methods=['PUT'])
def update_quick_chat(chat_id):
    """Update an existing quick chat"""
    try:
        data = request.get_json()
        
        # Validate required fields
        if not data.get('name'):
            return jsonify({'error': 'Chat name is required'}), 400
        if not data.get('messages'):
            return jsonify({'error': 'Messages are required'}), 400
        
        chat_file = QUICK_CHATS_DIR / f"{chat_id}.json"
        if not chat_file.exists():
            return jsonify({'error': 'Quick chat not found'}), 404
        
        # Update chat data
        chat_data = {
            'id': chat_id,
            'name': data['name'],
            'character': data.get('character', {}),
            'messages': data['messages'],
            'created_at': data.get('created_at', pathlib.Path().stat().st_mtime),
            'preset': data.get('preset'),
            'model': data.get('model'),
            'modelConfig': data.get('modelConfig'),
        }
        
        with open(chat_file, 'w', encoding='utf-8') as f:
            json.dump(chat_data, f, indent=2, ensure_ascii=False)
        
        return jsonify({
            'id': chat_id,
            'message': 'Quick chat updated successfully',
            'file_path': str(chat_file)
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/quick-chat/respond', methods=['POST'])
def quick_chat_respond():
    """Direct quick chat response without creating sessions"""
    try:
        data = request.get_json()
        character = data.get('character')
        messages = data.get('messages', [])
        preset = data.get('preset')
        model = data.get('model')
        sampling = data.get('sampling', {})
        cot = data.get('cot', False)

        if not character:
            return jsonify({'error': 'Character is required'}), 400
        
        if not messages:
            return jsonify({'error': 'Messages are required'}), 400

        # Load full character data if we received a character ID/name
        if isinstance(character, str):
            # Character is just an ID, load the full data
            char_file = find_character_file(character)
            if not char_file:
                return jsonify({'error': f'Character not found: {character}'}), 404
            
            with open(char_file, 'r', encoding='utf-8') as f:
                full_char_data = json.load(f)
            
            char_name = full_char_data.get('lore', {}).get('name', character)
            char_obj = convert_character_data_to_character(full_char_data, char_name)
        elif isinstance(character, dict) and 'id' in character:
            # Character is an object with ID, load the full data
            char_file = find_character_file(character['id'])
            if not char_file:
                return jsonify({'error': f'Character not found: {character["id"]}'}), 404
            
            with open(char_file, 'r', encoding='utf-8') as f:
                full_char_data = json.load(f)
            
            char_name = full_char_data.get('lore', {}).get('name', character.get('name', character['id']))
            char_obj = convert_character_data_to_character(full_char_data, char_name)
        else:
            # Character data is already in full format
            char_obj = convert_character_data_to_character(character, character.get('name', 'Unknown'))
        
        # Apply preset if specified
        if preset:
            try:
                preset_data = load_model_presets().get(preset)
                if preset_data:
                    char_obj.params = preset_data.get('sampling', {})
                    char_obj.model = preset_data.get('model', char_obj.model)
                    char_obj.cot = preset_data.get('cot', char_obj.cot)
                    char_obj.context_limit = preset_data.get('context_limit', char_obj.context_limit)
            except Exception as e:
                print(f"Warning: Failed to apply preset {preset}: {e}")
        
        # Override with direct model settings if provided
        if model:
            char_obj.model = model
        if sampling:
            char_obj.params.update(sampling)
        if cot is not None:
            char_obj.cot = cot

        # Convert messages to the expected format for chat_call
        # chat_call expects history (all messages except the last user message) and current message (last user message)
        if not messages:
            return jsonify({'error': 'No messages provided'}), 400
            
        # The last message should be the user message we want to respond to
        current_message = ""
        conversation_history = []
        
        # Find the last user message
        last_user_msg_idx = -1
        for i in range(len(messages) - 1, -1, -1):
            if messages[i].get('role') == 'user':
                current_message = messages[i].get('content', '')
                last_user_msg_idx = i
                break
        
        if not current_message:
            return jsonify({'error': 'No user message found'}), 400
            
        # Everything before the last user message is conversation history
        conversation_history = messages[:last_user_msg_idx]

        # Generate response using the character
        response = chat_call(char_obj, conversation_history, current_message)
        
        return jsonify({
            'content': response,
            'character': char_obj.name,
            'debug_info': {
                'system_prompt': char_obj.system_prompt,  # This now contains the full injected character data
                'model': char_obj.model,
                'params': char_obj.params
            }
        })

    except Exception as e:
        print(f"Error in quick_chat_respond: {e}")
        # Include debug info even on error for troubleshooting
        debug_info = {}
        if 'char_obj' in locals():
            debug_info = {
                'system_prompt': char_obj.system_prompt,
                'model': char_obj.model,
                'params': char_obj.params
            }
        return jsonify({'error': str(e), 'debug_info': debug_info}), 500

@app.route('/api/quick-chat/settings', methods=['GET'])
def get_quick_chat_settings():
    """Get Quick Chat settings"""
    try:
        config = load_config()
        settings = config.get('quick_chat', {})
        return jsonify({
            'titleGenerationModel': settings.get('titleGenerationModel', ''),
            'enableAutoTitles': settings.get('enableAutoTitles', True)
        })
    except Exception as e:
        print(f"Error getting Quick Chat settings: {e}")
        return jsonify({
            'titleGenerationModel': '',
            'enableAutoTitles': True
        })

@app.route('/api/quick-chat/settings', methods=['POST'])
def set_quick_chat_settings():
    """Set Quick Chat settings"""
    try:
        data = request.get_json()
        config = load_config()
        
        if 'quick_chat' not in config:
            config['quick_chat'] = {}
        
        config['quick_chat'].update({
            'titleGenerationModel': data.get('titleGenerationModel', ''),
            'enableAutoTitles': data.get('enableAutoTitles', True)
        })
        
        save_config(config)
        return jsonify({'success': True})
    except Exception as e:
        print(f"Error setting Quick Chat settings: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/quick-chat/generate-title', methods=['POST'])
def generate_chat_title():
    """Generate a title for a chat conversation"""
    try:
        data = request.get_json()
        character_name = data.get('character', 'Unknown')
        messages = data.get('messages', [])
        model_id = data.get('model', 'default-model')
        
        if not messages:
            return jsonify({'error': 'No messages provided'}), 400

        # Create a simple character for title generation
        title_char = Character(
            name="Title Generator",
            model=model_id,
            system_prompt="You are a helpful assistant that generates concise, descriptive titles for conversations. Titles should be 3-8 words and capture the main topic or theme of the conversation. Respond with only the title, nothing else.",
            params={
                'temperature': 0.7,
                'max_tokens': 50,
                'top_p': 0.9,
                'top_k': 40
            }
        )

        # Create context from messages
        context = f"Character: {character_name}\n\n"
        for msg in messages:
            # Support both 'type' and 'role' field formats
            msg_type = msg.get('type') or msg.get('role')
            if msg_type == 'user':
                context += f"User: {msg.get('content', '')}\n"
            elif msg_type in ['ai', 'assistant']:
                context += f"{character_name}: {msg.get('content', '')}\n"
        
        context += "\nGenerate a concise title for this conversation:"

        # Generate title
        title = chat_call(title_char, [], context)
        
        # Clean up the title
        title = title.strip()
        if title.startswith('"') and title.endswith('"'):
            title = title[1:-1]
        if title.startswith("'") and title.endswith("'"):
            title = title[1:-1]
        
        # Fallback if generation fails
        if not title or len(title) < 3:
            title = f"Chat with {character_name}"
        
        return jsonify({'title': title})

    except Exception as e:
        print(f"Error generating chat title: {e}")
        return jsonify({'error': str(e)}), 500

@app.errorhandler(Exception)
def handle_error(error):
    """Global error handler"""
    app.logger.error(f"Error: {error}")
    return jsonify({
        'error': str(error),
        'type': type(error).__name__
    }), 500

# ────────────────────────────  Connection  ────────────────────────────
@app.route('/api/test-connection', methods=['GET'])
def api_test_connection():
    """Test connection to LM Studio"""
    try:
        connected = test_connection()
        return jsonify({
            'connected': connected,
            'message': 'Connected to LM Studio' if connected else 'Failed to connect to LM Studio'
        })
    except Exception as e:
        return jsonify({
            'connected': False,
            'message': f'Connection error: {str(e)}'
        }), 500

@app.route('/api/models', methods=['GET'])
def get_available_models():
    """Get available models from LM Studio"""
    try:
        import requests
        from core import LMSTUDIO_BASE_URL
        
        # Get models from LM Studio API
        response = requests.get(f'{LMSTUDIO_BASE_URL}/models', timeout=10)
        
        if response.status_code == 200:
            models_data = response.json()
            
            # Extract model names from the response
            models = []
            if 'data' in models_data:
                for model in models_data['data']:
                    models.append({
                        'id': model.get('id', 'unknown'),
                        'name': model.get('id', 'unknown'),
                        'object': model.get('object', 'model'),
                        'created': model.get('created', 0),
                        'owned_by': model.get('owned_by', 'unknown')
                    })
            
            return jsonify({
                'connected': True,
                'models': models,
                'count': len(models)
            })
        else:
            return jsonify({
                'connected': False,
                'models': [],
                'count': 0,
                'error': 'Failed to fetch models from LM Studio'
            }), 500
            
    except requests.exceptions.ConnectionError:
        return jsonify({
            'connected': False,
            'models': [],
            'count': 0,
            'error': 'Cannot connect to LM Studio. Make sure it is running.'
        }), 503
    except Exception as e:
        return jsonify({
            'connected': False,
            'models': [],
            'count': 0,
            'error': f'Error fetching models: {str(e)}'
        }), 500

# ────────────────────────────  Characters  ────────────────────────────
@app.route('/api/characters', methods=['GET'])
def get_characters():
    """Get all characters"""
    try:
        characters = []
        
        # Get characters from main directory
        for char_file in CHARACTERS_DIR.glob("*.json"):
            try:
                with open(char_file, 'r', encoding='utf-8') as f:
                    char_data = json.load(f)
                
                # Construct image URL if image exists
                image_url = None
                if char_data.get('lore', {}).get('image'):
                    image_url = f"/characters/images/{char_data['lore']['image'].split('/')[-1]}"
                
                characters.append({
                    'id': char_file.stem,
                    'name': char_data.get('lore', {}).get('name', char_file.stem),
                    'type': char_data.get('type', 'Unknown'),
                    'model': char_data.get('model', 'Unknown'),
                    'modelPreset': extract_model_preset_id(char_data),
                    'cot': char_data.get('cot', False),
                    'description': char_data.get('lore', {}).get('description', ''),
                    'file_path': str(char_file),
                    'image_url': image_url
                })
            except Exception as e:
                app.logger.warning(f"Failed to load character {char_file}: {e}")
                continue
        
        # Get characters from examples directory
        examples_dir = CHARACTERS_DIR / "examples"
        if examples_dir.exists():
            for char_file in examples_dir.glob("*.json"):
                try:
                    with open(char_file, 'r', encoding='utf-8') as f:
                        char_data = json.load(f)
                    
                    # Construct image URL if image exists
                    image_url = None
                    if char_data.get('lore', {}).get('image'):
                        image_url = f"/characters/images/{char_data['lore']['image'].split('/')[-1]}"
                    
                    characters.append({
                        'id': f"example_{char_file.stem}",
                        'name': char_data.get('lore', {}).get('name', char_file.stem),
                        'type': char_data.get('type', 'Example'),
                        'model': char_data.get('model', 'Unknown'),
                        'modelPreset': extract_model_preset_id(char_data),
                        'cot': char_data.get('cot', False),
                        'description': char_data.get('lore', {}).get('description', ''),
                        'file_path': str(char_file),
                        'is_example': True,
                        'image_url': image_url
                    })
                except Exception as e:
                    app.logger.warning(f"Failed to load example character {char_file}: {e}")
                    continue
        
        return jsonify(characters)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/characters/<character_id>', methods=['GET'])
def get_character(character_id):
    """Get a specific character"""
    try:
        char_file = find_character_file(character_id)
        if not char_file:
            return jsonify({'error': 'Character not found'}), 404
        
        with open(char_file, 'r', encoding='utf-8') as f:
            char_data = json.load(f)
        
        # Construct image URL if image exists
        image_url = None
        if char_data.get('lore', {}).get('image'):
            image_url = f"/characters/images/{char_data['lore']['image'].split('/')[-1]}"
        
        return jsonify({
            'id': character_id,
            'data': char_data,
            'file_path': str(char_file),
            'image_url': image_url
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/characters', methods=['POST'])
def create_character():
    """Create a new character"""
    try:
        data = request.get_json()
        
        # Validate required fields
        if not data.get('name'):
            return jsonify({'error': 'Character name is required'}), 400
        
        # Create character data structure
        # Handle nested lore structure from frontend
        lore_data = data.get('lore', {})
        
        char_data = {
            'lore': {
                'name': data['name'],
                'description': data.get('description', ''),
                # Use nested lore data if provided, otherwise fall back to flat structure
                'personality': lore_data.get('personality', data.get('personality', '')),
                'background': lore_data.get('background', data.get('background', '')),
                'type': data.get('type', ''),
                # Add any additional lore fields from frontend
                **{k: v for k, v in lore_data.items() if k not in ['name', 'description', 'personality', 'background']}
            }
        }
        
        # Only add model-related fields if explicitly provided
        if 'model' in data:
            char_data['model'] = data['model']
        if 'cot' in data:
            char_data['cot'] = data['cot']
        if 'sampling' in data:
            char_data['sampling'] = data['sampling']
        
        # Apply model preset if specified
        if data.get('modelPreset'):
            try:
                char_data = apply_model_preset_to_character(char_data, data['modelPreset'])
            except FileOperationError:
                return jsonify({'error': 'Invalid model preset'}), 400
        
        # Generate safe filename
        safe_name = sanitize_filename(data['name'])
        char_file = CHARACTERS_DIR / f"{safe_name}.json"
        
        # Check if file already exists
        counter = 1
        while char_file.exists():
            char_file = CHARACTERS_DIR / f"{safe_name}_{counter}.json"
            counter += 1
        
        # Save character
        with open(char_file, 'w', encoding='utf-8') as f:
            json.dump(char_data, f, indent=2, ensure_ascii=False)
        
        return jsonify({
            'id': char_file.stem,
            'message': 'Character created successfully',
            'file_path': str(char_file)
        }), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/characters/<character_id>', methods=['PUT'])
def update_character(character_id):
    """Update an existing character"""
    try:
        char_file = find_character_file(character_id)
        if not char_file:
            return jsonify({'error': 'Character not found'}), 404
        
        data = request.get_json()
        
        # Load existing character data
        with open(char_file, 'r', encoding='utf-8') as f:
            char_data = json.load(f)
        
        # Update character data
        if 'name' in data:
            char_data.setdefault('lore', {})['name'] = data['name']
        if 'description' in data:
            char_data.setdefault('lore', {})['description'] = data['description']
        if 'personality' in data:
            char_data.setdefault('lore', {})['personality'] = data['personality']
        if 'background' in data:
            char_data.setdefault('lore', {})['background'] = data['background']
        if 'type' in data:
            char_data.setdefault('lore', {})['type'] = data['type']
        
        # Apply model preset if specified
        if data.get('modelPreset'):
            try:
                char_data = apply_model_preset_to_character(char_data, data['modelPreset'])
            except FileOperationError:
                return jsonify({'error': 'Invalid model preset'}), 400
        
        # Save updated character
        with open(char_file, 'w', encoding='utf-8') as f:
            json.dump(char_data, f, indent=2, ensure_ascii=False)
        
        return jsonify({
            'id': character_id,
            'message': 'Character updated successfully'
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/characters/<character_id>', methods=['DELETE'])
def delete_character(character_id):
    """Delete a character"""
    try:
        char_file = find_character_file(character_id)
        if not char_file:
            return jsonify({'error': 'Character not found'}), 404
        
        # Don't allow deleting example characters
        if 'examples' in str(char_file):
            return jsonify({'error': 'Cannot delete example characters'}), 400
        
        char_file.unlink()
        
        return jsonify({
            'message': 'Character deleted successfully'
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ────────────────────────────  Model Presets  ────────────────────────────
@app.route('/api/model-presets', methods=['GET'])
def get_model_presets():
    """Get all model presets"""
    try:
        presets = load_model_presets()
        # Add the ID field to each preset for frontend use
        for preset_id, preset_data in presets.items():
            preset_data['id'] = preset_id
        return jsonify(presets)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/model-presets/<preset_id>', methods=['GET'])
def get_model_preset(preset_id):
    """Get a specific model preset"""
    try:
        presets = load_model_presets()
        if preset_id not in presets:
            return jsonify({'error': 'Preset not found'}), 404
        
        return jsonify(presets[preset_id])
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/model-presets', methods=['POST'])
def create_model_preset():
    """Create a new model preset"""
    try:
        data = request.get_json()
        
        # Validate required fields
        if not data.get('id'):
            return jsonify({'error': 'Preset ID is required'}), 400
        if not data.get('name'):
            return jsonify({'error': 'Preset name is required'}), 400
        
        preset_data = {
            'name': data['name'],
            'description': data.get('description', ''),
            'model': data.get('model', 'default-model'),
            'cot': data.get('cot', False),
            'sampling': data.get('sampling', {
                'temperature': 0.7,
                'top_k': 40,
                'top_p': 0.9,
                'repeat_penalty': 1.1,
                'max_tokens': 500
            }),
            'response_format': data.get('response_format', None)
        }
        
        if save_model_preset(data['id'], preset_data):
            return jsonify({
                'message': 'Model preset created successfully',
                'id': data['id']
            }), 201
        else:
            return jsonify({'error': 'Failed to save preset'}), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/model-presets/<preset_id>', methods=['PUT'])
def update_model_preset(preset_id):
    """Update an existing model preset"""
    try:
        data = request.get_json()
        
        # Load existing preset
        presets = load_model_presets()
        if preset_id not in presets:
            return jsonify({'error': 'Preset not found'}), 404
        
        # Update preset data
        preset_data = presets[preset_id].copy()
        preset_data.update({
            'name': data.get('name', preset_data.get('name')),
            'description': data.get('description', preset_data.get('description')),
            'model': data.get('model', preset_data.get('model')),
            'cot': data.get('cot', preset_data.get('cot')),
            'sampling': data.get('sampling', preset_data.get('sampling')),
            'response_format': data.get('response_format', preset_data.get('response_format'))
        })
        
        if save_model_preset(preset_id, preset_data):
            return jsonify({
                'message': 'Model preset updated successfully'
            })
        else:
            return jsonify({'error': 'Failed to update preset'}), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/model-presets/<preset_id>', methods=['DELETE'])
def delete_model_preset(preset_id):
    """Delete a model preset"""
    try:
        preset_file = MODEL_PRESETS_DIR / f"{preset_id}.json"
        if not preset_file.exists():
            return jsonify({'error': 'Preset not found'}), 404
        
        # Check if this is a default preset that needs to be marked as deleted
        default_preset_ids = {"balanced", "creative", "analytical", "conversational", "chaotic"}
        sanitization_preset_ids = {"sanitizer-conservative", "sanitizer-balanced", "sanitizer-aggressive", "sanitizer-editor"}
        
        if preset_id in default_preset_ids:
            # Import the function here to avoid circular imports
            from core import add_deleted_preset
            add_deleted_preset(preset_id)
        elif preset_id in sanitization_preset_ids:
            # Track deleted sanitization presets
            deleted_sanitization_presets = load_deleted_sanitization_presets()
            deleted_sanitization_presets.add(preset_id)
            save_deleted_sanitization_presets(deleted_sanitization_presets)
        
        preset_file.unlink()
        
        return jsonify({
            'message': 'Model preset deleted successfully'
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/characters/<character_id>/apply-preset', methods=['POST'])
def apply_preset_to_character(character_id):
    """Apply a model preset to a character"""
    try:
        data = request.get_json()
        preset_id = data.get('presetId')
        
        if not preset_id:
            return jsonify({'error': 'Preset ID is required'}), 400
        
        char_file = find_character_file(character_id)
        if not char_file:
            return jsonify({'error': 'Character not found'}), 404
        
        # Load character data
        with open(char_file, 'r', encoding='utf-8') as f:
            char_data = json.load(f)
        
        # Apply preset
        try:
            updated_char_data = apply_model_preset_to_character(char_data, preset_id)
        except FileOperationError as e:
            return jsonify({'error': str(e)}), 400
        
        # Save if requested
        if data.get('save', False):
            with open(char_file, 'w', encoding='utf-8') as f:
                json.dump(updated_char_data, f, indent=2, ensure_ascii=False)
        
        return jsonify({
            'message': 'Model preset applied successfully',
            'character_data': updated_char_data
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ────────────────────────────  Templates  ────────────────────────────
@app.route('/api/templates', methods=['GET'])
def get_templates():
    """Get all templates"""
    try:
        templates = {
            'character': [],
            'session': []
        }
        
        # Character templates
        char_template_dir = CHARACTERS_DIR / "templates"
        if char_template_dir.exists():
            for template_file in char_template_dir.glob("*.json"):
                try:
                    with open(template_file, 'r', encoding='utf-8') as f:
                        template_data = json.load(f)
                    
                    templates['character'].append({
                        'id': template_file.stem,
                        'name': template_data.get('template_info', {}).get('name', template_file.stem),
                        'description': template_data.get('template_info', {}).get('description', ''),
                        'placeholders': template_data.get('template_info', {}).get('total_placeholders', 0),
                        'file_path': str(template_file)
                    })
                except Exception as e:
                    app.logger.warning(f"Failed to load character template {template_file}: {e}")
        
        # Session templates
        session_template_dir = PRESETS_DIR / "templates"
        if session_template_dir.exists():
            for template_file in session_template_dir.glob("*.json"):
                try:
                    with open(template_file, 'r', encoding='utf-8') as f:
                        template_data = json.load(f)
                    
                    templates['session'].append({
                        'id': template_file.stem,
                        'name': template_data.get('template_info', {}).get('name', template_file.stem),
                        'description': template_data.get('template_info', {}).get('description', ''),
                        'file_path': str(template_file)
                    })
                except Exception as e:
                    app.logger.warning(f"Failed to load session template {template_file}: {e}")
        
        return jsonify(templates)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/templates/session/<template_id>', methods=['GET'])
def get_session_template(template_id):
    """Get a session template with its configuration"""
    try:
        template_dir = PRESETS_DIR / "templates"
        template_file = template_dir / f"{template_id}.json"
        
        if not template_file.exists():
            return jsonify({'error': 'Session template not found'}), 404
        
        with open(template_file, 'r', encoding='utf-8') as f:
            template_data = json.load(f)
        
        return jsonify(template_data)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/templates/character', methods=['POST'])
def create_character_template_api():
    """Create a character template from existing character"""
    try:
        data = request.get_json()
        
        # Validate required fields
        if not data.get('characterId'):
            return jsonify({'error': 'Character ID is required'}), 400
        if not data.get('templateName'):
            return jsonify({'error': 'Template name is required'}), 400
        
        # Load character data
        char_file = find_character_file(data['characterId'])
        if not char_file:
            return jsonify({'error': 'Character not found'}), 404
        
        with open(char_file, 'r', encoding='utf-8') as f:
            char_data = json.load(f)
        
        # Use TUI functionality if available
        try:
            # Fallback to simple template if TUI function not available
            template_data = {
                'template_info': {
                    'name': data['templateName'],
                    'description': data.get('description', ''),
                    'created_from': data['characterId'],
                    'total_placeholders': 0,
                    'placeholders': []
                },
                'template': char_data
            }
        except (NameError, Exception) as e:
            # Fallback to simple template if TUI function not available
            template_data = {
                'template_info': {
                    'name': data['templateName'],
                    'description': data.get('description', ''),
                    'created_from': data['characterId'],
                    'total_placeholders': 0,
                    'placeholders': []
                },
                'template': char_data
            }
        
        # Save template
        safe_name = sanitize_filename(data['templateName'])
        template_dir = CHARACTERS_DIR / "templates"
        template_dir.mkdir(exist_ok=True)
        
        template_file = template_dir / f"{safe_name}.json"
        counter = 1
        while template_file.exists():
            template_file = template_dir / f"{safe_name}_{counter}.json"
            counter += 1
        
        with open(template_file, 'w', encoding='utf-8') as f:
            json.dump(template_data, f, indent=2, ensure_ascii=False)
        
        return jsonify({
            'id': template_file.stem,
            'message': 'Character template created successfully',
            'file_path': str(template_file),
            'placeholders': template_data['template_info'].get('placeholders', [])
        }), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/templates/character/<template_id>', methods=['GET'])
def get_character_template(template_id):
    """Get a character template with its placeholders"""
    try:
        template_dir = CHARACTERS_DIR / "templates"
        template_file = template_dir / f"{template_id}.json"
        
        if not template_file.exists():
            return jsonify({'error': 'Template not found'}), 404
        
        with open(template_file, 'r', encoding='utf-8') as f:
            template_data = json.load(f)
        
        # Extract template info and placeholders
        template_info = template_data.get('template_info', {})
        placeholders = template_info.get('placeholders', [])
        
        return jsonify({
            'id': template_id,
            'name': template_info.get('name', template_id),
            'description': template_info.get('description', ''),
            'total_placeholders': template_info.get('total_placeholders', len(placeholders)),
            'placeholders': placeholders,
            'template': template_data.get('character_template', template_data.get('template', {}))
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/templates/character/<template_id>/populate', methods=['POST'])
def populate_character_template(template_id):
    """Populate a character template with data"""
    try:
        data = request.get_json()
        
        # Load template
        template_dir = CHARACTERS_DIR / "templates"
        template_file = template_dir / f"{template_id}.json"
        
        if not template_file.exists():
            return jsonify({'error': 'Template not found'}), 404
        
        with open(template_file, 'r', encoding='utf-8') as f:
            template_data = json.load(f)
        
        # Get placeholder values
        placeholder_values = data.get('placeholders', {})
        
        # Get the actual template data (could be in character_template or template key)
        template_obj = template_data.get('character_template', template_data.get('template', {}))
        
        # Fallback to recursive replacement
        def replace_placeholders(obj):
            if isinstance(obj, dict):
                result = {}
                for k, v in obj.items():
                    result[k] = replace_placeholders(v)
                return result
            elif isinstance(obj, list):
                return [replace_placeholders(item) for item in obj]
            elif isinstance(obj, str):
                result = obj
                for placeholder, value in placeholder_values.items():
                    if placeholder in result:
                        result = result.replace(placeholder, str(value))
                return result
            else:
                return obj
        
        populated_data = replace_placeholders(template_obj)
        
        return jsonify({
            'character_data': populated_data,
            'message': 'Template populated successfully'
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ────────────────────────────  Sessions  ────────────────────────────
@app.route('/api/sessions', methods=['GET'])
def get_sessions():
    """Get recent sessions"""
    try:
        sessions = []
        sessions_dir = STORIES_DIR / "sessions"
        
        if sessions_dir.exists():
            for session_file in sessions_dir.glob("*.json"):
                try:
                    with open(session_file, 'r', encoding='utf-8') as f:
                        session_data = json.load(f)
                    
                    sessions.append({
                        'id': session_file.stem,
                        'type': session_data.get('type', 'chat'),
                        'title': session_data.get('title', session_file.stem),
                        'characters': [char.get('name', 'Unknown') for char in session_data.get('characters', [])],
                        'created_at': session_data.get('created_at'),
                        'status': session_data.get('status', 'unknown'),
                        'message_count': len(session_data.get('messages', []))
                    })
                except Exception as e:
                    app.logger.warning(f"Failed to load session {session_file}: {e}")
        
        # Sort by creation time, newest first
        sessions.sort(key=lambda x: x.get('created_at', 0), reverse=True)
        return jsonify(sessions)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/sessions', methods=['POST'])
def create_session():
    """Create a new session with real story/chat generation"""
    try:
        data = request.get_json()
        
        # Validate required fields
        if not data.get('characters'):
            return jsonify({'error': 'Characters are required'}), 400
        
        session_type = data.get('type', 'chat')
        chat_mode = data.get('chatMode', 'single')  # 'single' or 'multi'
        session_id = generate_session_id()
        
        # Load character data with applied presets
        session_characters = []
        for char_info in data['characters']:
            char_file = find_character_file(char_info['id'])
            if not char_file:
                continue
                
            with open(char_file, 'r', encoding='utf-8') as f:
                char_data = json.load(f)
            
            # Apply preset if specified
            if char_info.get('preset'):
                try:
                    char_data = apply_model_preset_to_character(char_data, char_info['preset'])
                except FileOperationError:
                    pass  # Use original if preset fails
            
            session_characters.append({
                'id': char_info['id'],
                'name': char_info['name'],
                'data': char_data
            })
        
        # Create appropriate title based on session type and chat mode
        if session_type == 'chat' and chat_mode == 'multi':
            title = f"Multi-Character Chat - {', '.join([c['name'] for c in session_characters])}"
        elif session_type == 'chat':
            title = f"Chat Session - {', '.join([c['name'] for c in session_characters])}"
        else:
            title = f"Story Session - {', '.join([c['name'] for c in session_characters])}"
        
        # Create session data
        session_data = {
            'id': session_id,
            'type': session_type,
            'chatMode': chat_mode if session_type == 'chat' else None,
            'title': title,
            'characters': session_characters,
            'scenario': data.get('scenario', ''),
            'setting': data.get('setting', ''),
            'turns': data.get('turns', 6) if session_type == 'chat' else None,
            'parts': data.get('parts', 4) if session_type == 'story' else None,
            'created_at': pathlib.Path().stat().st_mtime,
            'status': 'active',
            'messages': []
        }
        
        # Save session
        sessions_dir = STORIES_DIR / "sessions"
        sessions_dir.mkdir(parents=True, exist_ok=True)
        session_file = sessions_dir / f"{session_id}.json"
        
        with open(session_file, 'w', encoding='utf-8') as f:
            json.dump(session_data, f, indent=2, ensure_ascii=False)
        
        # Track analytics
        update_session_analytics(session_data, "created")
        
        if session_type == 'story':
            # For story sessions, generate the complete story in the background
            def background_generate():
                try:
                    generate_complete_story(session_data, session_file)
                except Exception as e:
                    app.logger.error(f"Background story generation failed: {e}")
            import threading
            threading.Thread(target=background_generate, daemon=True).start()

            return jsonify({
                'session': {
                    'id': session_id,
                    'type': session_type,
                    'title': session_data['title'],
                    'characters': [{'id': c['id'], 'name': c['name']} for c in session_characters],
                    'initial_content': 'Story generation started automatically'
                },
                'message': 'Story session created and generation started'
            }), 201
        else:
            # For chat sessions, handle differently based on chat mode
            initial_content = None
            
            if chat_mode == 'multi':
                # For multi-character chat, start conversation generation in background
                def background_generate():
                    try:
                        generate_multi_character_conversation(session_data, session_file)
                    except Exception as e:
                        app.logger.error(f"Background multi-character chat generation failed: {e}")
                import threading
                threading.Thread(target=background_generate, daemon=True).start()
                
                # Add initial system message
                initial_content = f"Multi-character conversation started between {', '.join([c['name'] for c in session_characters])}"
                session_data['messages'].append({
                    'type': 'system',
                    'content': initial_content,
                    'timestamp': pathlib.Path().stat().st_mtime
                })
            else:
                # For single character chat, generate opening
                initial_content = generate_chat_opening(session_data)
                
                if initial_content:
                    session_data['messages'].append({
                        'type': 'system',
                        'content': initial_content,
                        'timestamp': pathlib.Path().stat().st_mtime
                    })
            
            # Save updated session
            with open(session_file, 'w', encoding='utf-8') as f:
                json.dump(session_data, f, indent=2, ensure_ascii=False)
            
            return jsonify({
                'session': {
                    'id': session_id,
                    'type': session_type,
                    'title': session_data['title'],
                    'characters': [{'id': c['id'], 'name': c['name']} for c in session_characters],
                    'initial_content': initial_content or 'Chat session created'
                },
                'message': 'Session created successfully'
            }), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/sessions/<session_id>', methods=['GET'])
def get_session(session_id):
    """Get a specific session"""
    try:
        session_file = STORIES_DIR / "sessions" / f"{session_id}.json"
        
        if not session_file.exists():
            return jsonify({'error': 'Session not found'}), 404
        
        with open(session_file, 'r', encoding='utf-8') as f:
            session_data = json.load(f)
        
        return jsonify(session_data)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/sessions/<session_id>/generate', methods=['POST'])
def generate_session_content(session_id):
    """Generate next content for session (chat or story)"""
    try:
        data = request.get_json()
        user_input = data.get('input', '')
        
        # Load session
        session_file = STORIES_DIR / "sessions" / f"{session_id}.json"
        if not session_file.exists():
            return jsonify({'error': 'Session not found'}), 404
        
        with open(session_file, 'r', encoding='utf-8') as f:
            session_data = json.load(f)
        
        # Check if session is paused
        if session_data.get('paused', False):
            return jsonify({
                'response': None,
                'message': 'Session is paused. Resume the session to continue generation.',
                'paused': True
            }), 400
        
        # Check if this is a quick chat (unlimited turns)
        is_quick_chat = session_data.get('turns') == 999
        
        # Only check turn limits for regular sessions, not quick chats
        if not is_quick_chat:
            # Check if session has reached its limit
            ai_messages = [msg for msg in session_data.get('messages', []) if msg['type'] == 'ai']
            current_count = len(ai_messages)
            
            if session_data['type'] == 'chat':
                max_turns = session_data.get('turns', 6)
                if current_count >= max_turns:
                    return jsonify({
                        'response': None,
                        'message': f'Chat session completed ({current_count}/{max_turns} turns)',
                        'completed': True
                    })
            else:  # story
                max_parts = session_data.get('parts', 4)
                # Only enforce limit if parts is not unlimited (999) and not null
                if max_parts != 999 and max_parts is not None and current_count >= max_parts:
                    return jsonify({
                        'response': None,
                        'message': f'Story session completed ({current_count}/{max_parts} parts)',
                        'completed': True
                    })
        
        # For story sessions, generate all remaining parts automatically
        if session_data['type'] == 'story' and not user_input:
            return generate_complete_story(session_data, session_file)
        
        # Generate response based on session type
        if session_data['type'] == 'story':
            response = generate_story_continuation(session_data, user_input)
        else:
            response = generate_chat_response(session_data, user_input)
        
        if response:
            # Add user input and AI response to messages
            if user_input:
                session_data['messages'].append({
                    'type': 'user',
                    'content': user_input,
                    'timestamp': pathlib.Path().stat().st_mtime
                })
            
            session_data['messages'].append({
                'type': 'ai',
                'content': response,
                'timestamp': pathlib.Path().stat().st_mtime
            })
            
            # Save updated session
            with open(session_file, 'w', encoding='utf-8') as f:
                json.dump(session_data, f, indent=2, ensure_ascii=False)
        
        # For quick chats, never mark as completed
        if is_quick_chat:
            return jsonify({
                'response': response,
                'message': 'Content generated successfully',
                'completed': False,
                'progress': {
                    'current': len([msg for msg in session_data.get('messages', []) if msg['type'] == 'ai']),
                    'max': None  # No limit for quick chats
                }
            })
        
        # Check if this was the final response for regular sessions
        ai_messages = [msg for msg in session_data.get('messages', []) if msg['type'] == 'ai']
        current_count = len(ai_messages)
        
        if session_data['type'] == 'chat':
            max_turns = session_data.get('turns', 6)
            completed = current_count >= max_turns
        else:  # story
            max_parts = session_data.get('parts', 4)
            # Only mark as completed if parts is not unlimited (999) and not null
            completed = max_parts != 999 and max_parts is not None and current_count >= max_parts
        
        # Update session status if completed
        if completed:
            session_data['status'] = 'completed'
            session_data['is_completed'] = True  # Add explicit completion flag
            # Save updated session with completed status
            with open(session_file, 'w', encoding='utf-8') as f:
                json.dump(session_data, f, indent=2, ensure_ascii=False)
        
        # Calculate progress max value
        if session_data['type'] == 'chat':
            progress_max = session_data.get('turns', 6)
        else:  # story
            # For unlimited parts (999 or null), set max to null
            if session_data.get('parts') == 999 or session_data.get('parts') is None:
                progress_max = None
            else:
                progress_max = session_data.get('parts', 4)
        
        return jsonify({
            'response': response,
            'message': 'Content generated successfully',
            'completed': completed,
            'progress': {
                'current': current_count,
                'max': progress_max
            }
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/sessions/<session_id>', methods=['DELETE'])
def delete_session(session_id):
    """Delete a session"""
    try:
        session_file = STORIES_DIR / "sessions" / f"{session_id}.json"
        if os.path.exists(session_file):
            os.remove(session_file)
            return jsonify({"message": "Session deleted successfully"})
        else:
            return jsonify({"error": "Session not found"}), 404
    except Exception as e:
        return jsonify({"error": f"Failed to delete session: {str(e)}"}), 500

@app.route('/api/sessions/<session_id>/pause', methods=['POST'])
def pause_session(session_id):
    """Pause a session generation"""
    try:
        session_file = STORIES_DIR / "sessions" / f"{session_id}.json"
        if not session_file.exists():
            return jsonify({"error": "Session not found"}), 404
        
        with open(session_file, 'r') as f:
            session_data = json.load(f)
        
        # Mark session as paused
        session_data['paused'] = True
        session_data['paused_at'] = datetime.datetime.now().timestamp()
        
        with open(session_file, 'w') as f:
            json.dump(session_data, f, indent=2)
        
        return jsonify({"message": "Session paused successfully"})
    except Exception as e:
        return jsonify({"error": f"Failed to pause session: {str(e)}"}), 500

@app.route('/api/sessions/<session_id>/resume', methods=['POST'])
def resume_session(session_id):
    """Resume a paused session generation"""
    try:
        session_file = STORIES_DIR / "sessions" / f"{session_id}.json"
        if not session_file.exists():
            return jsonify({"error": "Session not found"}), 404
        
        with open(session_file, 'r') as f:
            session_data = json.load(f)
        
        # Remove paused flag
        session_data.pop('paused', None)
        session_data.pop('paused_at', None)
        
        with open(session_file, 'w') as f:
            json.dump(session_data, f, indent=2)
        
        return jsonify({"message": "Session resumed successfully"})
    except Exception as e:
        return jsonify({"error": f"Failed to resume session: {str(e)}"}), 500

@app.route('/api/sessions/<session_id>/sanitize', methods=['POST'])
def sanitize_session_story(session_id):
    """Sanitize a completed story session by removing illogical parts and repetitive content"""
    try:
        data = request.get_json() or {}
        preset_id = data.get('preset_id', 'sanitizer-balanced')
        
        print(f"Starting sanitization for session {session_id} with preset {preset_id}")
        
        # Load the session
        session_file = STORIES_DIR / "sessions" / f"{session_id}.json"
        if not session_file.exists():
            return jsonify({'error': 'Session not found'}), 404
            
        with open(session_file, 'r', encoding='utf-8') as f:
            session_data = json.load(f)
        
        # Only allow sanitization for completed story sessions
        if session_data.get('type') != 'story':
            return jsonify({'error': 'Sanitization only available for story sessions'}), 400
            
        # Check if session is completed
        ai_messages = [msg for msg in session_data.get('messages', []) if msg['type'] == 'ai']
        if not ai_messages:
            return jsonify({'error': 'No story content to sanitize'}), 400
            
        # Combine all AI messages into the full story
        story_parts = [msg['content'] for msg in ai_messages]
        original_story = '\n\n'.join(story_parts)
        
        print(f"Original story length: {len(original_story)} characters")
        
        # Sanitize the story using the specified preset
        sanitized_story = sanitize_story(original_story, preset_id)
        
        print(f"Sanitized story length: {len(sanitized_story)} characters")
        
        # Update the session with sanitized content
        # Replace all AI messages with a single sanitized message
        session_data['messages'] = [
            {
                'type': 'ai',
                'content': sanitized_story,
                'timestamp': datetime.datetime.now().timestamp(),
                'sanitized': True
            }
        ]
        
        # Save the updated session
        with open(session_file, 'w', encoding='utf-8') as f:
            json.dump(session_data, f, indent=2, ensure_ascii=False)
        
        # Track sanitization analytics
        update_sanitization_analytics(len(original_story), len(sanitized_story), preset_id)
        
        return jsonify({
            'message': 'Story sanitized successfully',
            'original_length': len(original_story),
            'sanitized_length': len(sanitized_story),
            'characters_removed': len(original_story) - len(sanitized_story),
            'session': session_data
        })
        
    except Exception as e:
        return jsonify({'error': f'Failed to sanitize story: {str(e)}'}), 500

# ────────────────────────────  Helper Functions  ────────────────────────────
def find_character_file(character_id):
    """Find character file by ID"""
    if character_id.startswith('example_'):
        actual_id = character_id[8:]  # Remove 'example_' prefix
        char_file = CHARACTERS_DIR / "examples" / f"{actual_id}.json"
    else:
        char_file = CHARACTERS_DIR / f"{character_id}.json"
    
    return char_file if char_file.exists() else None

def convert_character_data_to_character(char_data, char_name):
    """Convert character data from session format to Character object"""
    try:
        # Extract model and sampling parameters
        model = char_data.get('model', 'default-model')
        sampling = char_data.get('sampling', {})
        
        # Build system prompt from lore
        lore = char_data.get('lore', {})
        system_prompt_parts = []
        
        # Define preferred order for common fields
        priority_fields = [
            'name', 'description', 'personality', 'background', 'appearance', 
            'speaking_style', 'goals', 'motivations', 'features', 'powers', 
            'skills', 'weaknesses', 'bodyType', 'skinColor'
        ]
        
        processed_fields = set()
        
        # Process priority fields in preferred order
        for field in priority_fields:
            if field in lore:
                value = lore[field]
                if isinstance(value, str) and value.strip():
                    formatted_key = field.replace('_', ' ').replace('Color', ' Color').replace('Type', ' Type').title()
                    system_prompt_parts.append(f"{formatted_key}: {value}")
                elif isinstance(value, list) and value:
                    formatted_key = field.replace('_', ' ').replace('Color', ' Color').replace('Type', ' Type').title()
                    # Join list items with commas
                    value_str = ', '.join(str(v) for v in value if str(v).strip())
                    if value_str:
                        system_prompt_parts.append(f"{formatted_key}: {value_str}")
                elif isinstance(value, dict) and value:
                    formatted_key = field.replace('_', ' ').replace('Color', ' Color').replace('Type', ' Type').title()
                    # Handle nested objects
                    nested_items = [f"{k}: {v}" for k, v in value.items() if v and str(v).strip()]
                    if nested_items:
                        system_prompt_parts.append(f"{formatted_key}: {'; '.join(nested_items)}")
                processed_fields.add(field)
        
        # Process any remaining fields that weren't in the priority list
        for key, value in lore.items():
            if key not in processed_fields and key != 'name':
                if isinstance(value, str) and value.strip():
                    formatted_key = key.replace('_', ' ').replace('Color', ' Color').replace('Type', ' Type').title()
                    system_prompt_parts.append(f"{formatted_key}: {value}")
                elif isinstance(value, list) and value:
                    formatted_key = key.replace('_', ' ').replace('Color', ' Color').replace('Type', ' Type').title()
                    value_str = ', '.join(str(v) for v in value if str(v).strip())
                    if value_str:
                        system_prompt_parts.append(f"{formatted_key}: {value_str}")
                elif isinstance(value, dict) and value:
                    formatted_key = key.replace('_', ' ').replace('Color', ' Color').replace('Type', ' Type').title()
                    nested_items = [f"{k}: {v}" for k, v in value.items() if v and str(v).strip()]
                    if nested_items:
                        system_prompt_parts.append(f"{formatted_key}: {'; '.join(nested_items)}")
        
        # Create a comprehensive system prompt that clearly shows character data injection
        if system_prompt_parts:
            system_prompt = f"You are {char_name}. Here is your complete character data:\n\n=== CHARACTER PROFILE ===\n" + "\n".join(system_prompt_parts) + "\n=== END CHARACTER PROFILE ===\n\nEmbody this character completely. Use all the information above to inform your responses, personality, and behavior."
        else:
            system_prompt = f"You are {char_name}."
        
        # Create params dict with sampling parameters
        params = {
            'temperature': float(sampling.get('temperature', 0.7)),
            'top_k': int(sampling.get('top_k', 40)),
            'top_p': float(sampling.get('top_p', 0.9)),
            'repeat_penalty': float(sampling.get('repeat_penalty', 1.1)),
            'max_tokens': int(sampling.get('max_tokens', 500))
        }
        
        # Create Character object
        return Character(
            name=char_name,
            model=model,
            system_prompt=system_prompt,
            params=params,
            cot=char_data.get('cot', False),
            context_limit=char_data.get('context_limit', 4096)
        )
    except Exception as e:
        app.logger.error(f"Error converting character data: {e}")
        # Return a basic character as fallback
        return Character(
            name=char_name,
            model='default-model',
            system_prompt=f"You are {char_name}.",
            params={'temperature': 0.7, 'top_k': 40, 'top_p': 0.9, 'repeat_penalty': 1.1, 'max_tokens': 500},
            cot=False,
            context_limit=4096
        )

def extract_model_preset_id(char_data):
    """Extract model preset ID from character data"""
    # This is a simplified version - in a real implementation,
    # you might want to match the model config against known presets
    sampling = char_data.get('sampling', {})
    temp = sampling.get('temperature', 0.7)
    cot = char_data.get('cot', False)
    
    # Simple heuristic to guess preset
    if cot and temp <= 0.3:
        return 'analytical'
    elif temp >= 1.0:
        return 'chaotic'
    elif temp >= 0.8:
        return 'creative'
    elif temp <= 0.6:
        return 'conversational'
    else:
        return 'balanced'

def sanitize_filename(filename):
    """Sanitize filename for safe file system storage"""
    import re
    # Remove invalid characters and replace with underscores
    safe_name = re.sub(r'[<>:"/\\|?*]', '_', filename)
    # Replace spaces with underscores
    safe_name = safe_name.replace(' ', '_')
    # Remove consecutive underscores
    safe_name = re.sub(r'_+', '_', safe_name)
    # Remove leading/trailing underscores
    safe_name = safe_name.strip('_')
    # Ensure it's not empty
    return safe_name if safe_name else 'character'

def generate_story_opening(session_data):
    """Generate opening for a story session"""
    try:
        characters = session_data['characters']
        scenario = session_data.get('scenario', '')
        setting = session_data.get('setting', '')
        
        # Build prompt for story opening
        prompt_parts = ["Generate an engaging story opening with the following elements:"]
        
        if setting:
            prompt_parts.append(f"Setting: {setting}")
        
        if scenario:
            prompt_parts.append(f"Scenario: {scenario}")
        
        prompt_parts.append("Characters:")
        for char in characters:
            char_data = char['data']
            lore = char_data.get('lore', {})
            prompt_parts.append(f"- {char['name']}: {lore.get('description', 'No description')}")
        
        prompt_parts.append("\nWrite a compelling opening that introduces the setting and sets up the scenario. Keep it under 300 words.")
        
        prompt = "\n".join(prompt_parts)
        
        # Use first character's config for generation
        if characters:
            first_char = convert_character_data_to_character(characters[0]['data'], characters[0]['name'])
            response = chat_call(first_char, [], prompt)
            return response.strip()
        
        return None
    except Exception as e:
        app.logger.error(f"Story opening generation error: {e}")
        return None

def generate_story_continuation(session_data, user_input):
    """Generate story continuation"""
    try:
        characters = session_data['characters']
        messages = session_data.get('messages', [])
        
        # Build the full story content so far (like in original chat.py)
        story_parts = []
        for msg in messages:
            if msg['type'] == 'ai':
                story_parts.append(msg['content'])
        
        # Get the story prompt from session data
        story_prompt = session_data.get('scenario', '')
        
        # Build the user message like in original chat.py
        if len(story_parts) == 0:
            # First part - start the story
            user_msg = f"Story idea: {story_prompt}"
        else:
            # Continue the story with full context
            story_so_far = '\n\n'.join(story_parts)
            if user_input:
                user_msg = f"Story so far:\n{story_so_far}\n\nUser direction: {user_input}\n\nContinue the story."
            else:
                user_msg = f"Story so far:\n{story_so_far}\n\nContinue the story."
        
        # Use rotating character for variety
        char_index = len(messages) % len(characters)
        character = convert_character_data_to_character(characters[char_index]['data'], characters[char_index]['name'])
        
        # Call the model with the full story context
        response = chat_call(character, [], user_msg)
        return response.strip()
    except Exception as e:
        app.logger.error(f"Story continuation error: {e}")
        return "I'm having trouble generating the story continuation. Please try again."

def generate_chat_response(session_data, user_input):
    """Generate chat response from characters"""
    try:
        characters = session_data['characters']
        messages = session_data.get('messages', [])
        scenario = session_data.get('scenario', '')
        
        # Determine which character should respond
        char_index = len([m for m in messages if m['type'] == 'ai']) % len(characters)
        responding_char = characters[char_index]
        
        # Build conversation history from recent messages
        history = []
        for msg in messages[-6:]:  # Last 6 messages
            if msg['type'] == 'user':
                history.append({
                    'role': 'user',
                    'content': msg['content']
                })
            elif msg['type'] == 'ai':
                history.append({
                    'role': 'assistant',
                    'content': msg['content']
                })
        
        # Build the prompt for the character's response
        prompt_parts = []
        if scenario:
            prompt_parts.append(f"Scenario: {scenario}")
        
        prompt_parts.append(f"You are {responding_char['name']} in a conversation.")
        
        # Add character info
        char_data = responding_char['data']
        lore = char_data.get('lore', {})
        if lore.get('personality'):
            prompt_parts.append(f"Your personality: {lore['personality']}")
        
        if user_input:
            prompt_parts.append(f"User: {user_input}")
        
        prompt_parts.append(f"\nRespond as {responding_char['name']} in character:")
        
        prompt = "\n".join(prompt_parts)
        
        character = convert_character_data_to_character(responding_char['data'], responding_char['name'])
        response = chat_call(character, history, prompt)
        return response.strip()
    except Exception as e:
        app.logger.error(f"Chat response error: {e}")
        return "I'm having trouble responding right now. Please try again."

def generate_chat_opening(session_data):
    """Generate opening for a chat session"""
    try:
        characters = session_data['characters']
        scenario = session_data.get('scenario', '')
        setting = session_data.get('setting', '')
        
        if not characters:
            return None
        
        # Use first character to set the scene
        first_char = characters[0]
        char_data = first_char['data']
        
        prompt_parts = [f"You are {first_char['name']} starting a conversation."]
        
        if scenario:
            prompt_parts.append(f"Topic/Scenario: {scenario}")
        
        if setting:
            prompt_parts.append(f"Setting: {setting}")
        
        # Add character personality
        lore = char_data.get('lore', {})
        if lore.get('personality'):
            prompt_parts.append(f"Your personality: {lore['personality']}")
        
        prompt_parts.append("Start the conversation with a greeting or opening statement (1-2 sentences):")
        
        prompt = "\n".join(prompt_parts)
        
        character = convert_character_data_to_character(char_data, first_char['name'])
        response = chat_call(character, [], prompt)
        return response.strip()
    except Exception as e:
        app.logger.error(f"Chat opening generation error: {e}")
        return None

def generate_complete_story(session_data, session_file):
    """Generate the complete story with all parts automatically"""
    try:
        characters = session_data['characters']
        max_parts = session_data.get('parts', 4)
        
        # Handle unlimited mode (999) - only generate opening, then stop
        if max_parts == 999:
            # For unlimited stories, just generate opening and let user request more
            opening = generate_story_opening(session_data)
            if opening:
                session_data['messages'] = [{
                    'type': 'ai',
                    'content': opening,
                    'timestamp': pathlib.Path().stat().st_mtime
                }]
                # Save the opening and mark as active (not completed) for unlimited mode
                session_data['status'] = 'active'
                with open(session_file, 'w', encoding='utf-8') as f:
                    json.dump(session_data, f, indent=2, ensure_ascii=False)
            return True
        
        # Generate story opening first for limited mode
        opening = generate_story_opening(session_data)
        if opening:
            session_data['messages'] = [{
                'type': 'ai',
                'content': opening,
                'timestamp': pathlib.Path().stat().st_mtime
            }]
            # Save the opening immediately
            with open(session_file, 'w', encoding='utf-8') as f:
                json.dump(session_data, f, indent=2, ensure_ascii=False)
        
        # Generate remaining parts sequentially for limited mode
        for part_num in range(1, max_parts):  # Start from 1 since we already have opening
            # Reload the session data to get the latest messages (full story so far)
            with open(session_file, 'r', encoding='utf-8') as f:
                session_data = json.load(f)
            
            # Generate next part using the updated session data with full story context
            response = generate_story_continuation(session_data, '')
            if response:
                session_data['messages'].append({
                    'type': 'ai',
                    'content': response,
                    'timestamp': pathlib.Path().stat().st_mtime
                })
                
                # Save the updated session immediately after each part
                with open(session_file, 'w', encoding='utf-8') as f:
                    json.dump(session_data, f, indent=2, ensure_ascii=False)
        
        # Update session status to completed
        session_data['status'] = 'completed'
        session_data['is_completed'] = True  # Add explicit completion flag
        with open(session_file, 'w', encoding='utf-8') as f:
            json.dump(session_data, f, indent=2, ensure_ascii=False)
        
        # Combine all parts for the response
        all_parts = [msg['content'] for msg in session_data['messages'] if msg['type'] == 'ai']
        complete_story = "\n\n".join(all_parts)
        
        return jsonify({
            'response': complete_story,
            'message': f'Complete story generated ({len(all_parts)}/{max_parts} parts)',
            'completed': True,
            'progress': {
                'current': len(all_parts),
                'max': max_parts
            }
        })
    except Exception as e:
        app.logger.error(f"Complete story generation error: {e}")
        return jsonify({'error': str(e)}), 500

def generate_multi_character_conversation(session_data, session_file):
    """Generate a multi-character conversation automatically"""
    try:
        characters = session_data['characters']
        max_turns = session_data.get('turns', 6)
        scenario = session_data.get('scenario', '')
        setting = session_data.get('setting', '')
        
        if len(characters) < 2:
            return None
        
        conversation_history = []
        
        # Generate conversation turns
        for turn in range(max_turns):
            # Rotate through characters
            current_char = characters[turn % len(characters)]
            char_data = current_char['data']
            
            # Build context for this character
            context_parts = [f"You are {current_char['name']} in a conversation."]
            
            if scenario:
                context_parts.append(f"Topic/Scenario: {scenario}")
            
            if setting:
                context_parts.append(f"Setting: {setting}")
            
            # Add character personality
            lore = char_data.get('lore', {})
            if lore.get('personality'):
                context_parts.append(f"Your personality: {lore['personality']}")
            
            # Add other characters info
            other_chars = [c['name'] for c in characters if c['name'] != current_char['name']]
            if other_chars:
                context_parts.append(f"You are talking with: {', '.join(other_chars)}")
            
            # Add conversation context
            if conversation_history:
                context_parts.append("\nConversation so far:")
                context_parts.extend([f"{msg['character']}: {msg['content']}" for msg in conversation_history[-6:]])  # Last 6 messages for context
            
            if turn == 0:
                context_parts.append("\nStart the conversation with a greeting or opening statement:")
            else:
                context_parts.append(f"\nRespond naturally to continue the conversation:")
            
            prompt = "\n".join(context_parts)
            
            # Generate response
            character_obj = convert_character_data_to_character(char_data, current_char['name'])
            response = chat_call(character_obj, [], prompt)
            
            if response:
                # Clean the response
                cleaned_response = response.strip()
                
                # Add to conversation history
                conversation_history.append({
                    'character': current_char['name'],
                    'content': cleaned_response
                })
                
                # Add to session messages
                session_data['messages'].append({
                    'type': 'ai',
                    'character': current_char['name'],
                    'content': cleaned_response,
                    'timestamp': pathlib.Path().stat().st_mtime
                })
                
                # Save progress after each turn
                with open(session_file, 'w', encoding='utf-8') as f:
                    json.dump(session_data, f, indent=2, ensure_ascii=False)
        
        # Mark as completed
        session_data['status'] = 'completed'
        session_data['is_completed'] = True
        with open(session_file, 'w', encoding='utf-8') as f:
            json.dump(session_data, f, indent=2, ensure_ascii=False)
        
        return True
    except Exception as e:
        app.logger.error(f"Multi-character conversation generation error: {e}")
        return False

def sanitize_story(story_content: str, preset_id: str = "sanitizer-balanced") -> str:
    """Sanitize story content by removing illogical parts, repetitive content, and meta-commentary.
    
    Uses a sanitization preset for consistent, high-quality text cleaning while preserving the original
    creative content and style. Similar to the editor_clean function in core.py.
    
    Args:
        story_content: Raw story content to sanitize
        preset_id: ID of the sanitization preset to use (default: sanitizer-balanced)
        
    Returns:
        Sanitized story content with problems removed, or original content if sanitization fails
    """
    print(f"Starting sanitize_story with preset {preset_id}")
    
    prompt = f"""You are a careful text sanitizer. Your job is to clean the following story by:
- Removing repetitive loops where the model repeats itself
- Removing meta-commentary or breaking character
- Removing nonsensical gibberish or illogical parts
- Removing excessive repetition of phrases or ideas
- DO NOT change the actual story content, plot, or creative elements
- DO NOT rewrite or improve the story - only remove problematic parts
- Preserve the original creative voice and style
- Keep the story coherent and flowing naturally

Return only the cleaned story with problems removed.

===
{story_content}
==="""
    
    try:
        # Load the sanitization preset
        preset_file = MODEL_PRESETS_DIR / f"{preset_id}.json"
        if preset_file.exists():
            print(f"Using preset file: {preset_file}")
            with open(preset_file, 'r', encoding='utf-8') as f:
                preset_data = json.load(f)
            
            # Extract settings from preset
            model = preset_data.get('model', 'default-model')
            sampling = preset_data.get('sampling', {})
            cot = preset_data.get('cot', False)
            
            print(f"Preset settings - model: {model}, temperature: {sampling.get('temperature')}, max_tokens: {sampling.get('max_tokens')}")
            
            # Use preset settings for the API call
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": "You are a careful, low-temperature text sanitizer. Only remove problems, do not rewrite."},
                    {"role": "user", "content": prompt}
                ],
                temperature=sampling.get('temperature', 0.2),
                max_tokens=sampling.get('max_tokens', len(story_content.split()) * 2)
            )
        else:
            print(f"Preset file not found, using fallback settings")
            # Fallback to default settings if preset not found
            response = client.chat.completions.create(
                model="default-model",
                messages=[
                    {"role": "system", "content": "You are a careful, low-temperature text sanitizer. Only remove problems, do not rewrite."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.2,
                max_tokens=min(100000, len(story_content.split()) * 3)  # More generous token limit
            )
        
        result = response.choices[0].message.content
        print(f"Sanitization API call successful, result length: {len(result) if result else 0}")
        return result.strip() if result else story_content
    except Exception as e:
        print(f"Sanitization failed: {e}")
        import traceback
        traceback.print_exc()
        return story_content  # Return original if sanitization fails

@app.route('/api/model-presets/create-sanitization', methods=['POST'])
def create_sanitization_presets_endpoint():
    """Create sanitization-specific model presets on demand"""
    try:
        create_sanitization_presets()
        return jsonify({
            'message': 'Sanitization presets created successfully',
            'presets': [
                'sanitizer-conservative',
                'sanitizer-balanced', 
                'sanitizer-aggressive',
                'sanitizer-editor'
            ]
        })
    except Exception as e:
        return jsonify({'error': f'Failed to create sanitization presets: {str(e)}'}), 500

# ────────────────────────────  Analytics & Metrics  ────────────────────────────
import datetime
# Collections import removed - not used

# Analytics data storage
ANALYTICS_FILE = SETTINGS_DIR / "analytics.json"
ANALYTICS_LOCK = threading.Lock()

DEFAULT_ANALYTICS = {
    "sessions": {
        "total_created": 0,
        "total_completed": 0,
        "by_type": {"chat": 0, "story": 0},
        "completion_rates": {"chat": 0.0, "story": 0.0},
        "average_duration": {"chat": 0, "story": 0},
        "daily_created": {},
        "daily_completed": {}
    },
    "characters": {
        "most_used": {},
        "combinations": {},
        "usage_trends": {}
    },
    "content": {
        "total_words": 0,
        "average_words_per_session": {"chat": 0, "story": 0},
        "word_count_trends": {},
        "quality_ratings": []
    },
    "performance": {
        "average_generation_time": 0,
        "generation_times": [],
        "sanitization_usage": 0,
        "sanitization_effectiveness": 0.0
    },
    "user_behavior": {
        "session_abandonment_rate": 0.0,
        "most_used_presets": {},
        "quick_chat_usage": 0,
        "template_usage": 0
    }
}

def load_analytics():
    """Load analytics data from file"""
    if ANALYTICS_FILE.exists():
        try:
            with open(ANALYTICS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            pass
    return DEFAULT_ANALYTICS.copy()

def save_analytics(analytics):
    """Save analytics data to file"""
    with ANALYTICS_LOCK:
        with open(ANALYTICS_FILE, 'w', encoding='utf-8') as f:
            json.dump(analytics, f, indent=2, ensure_ascii=False)

def update_session_analytics(session_data, action="created"):
    """Update analytics when a session is created or completed"""
    analytics = load_analytics()
    today = datetime.datetime.now().strftime("%Y-%m-%d")
    
    # Session creation/completion tracking
    if action == "created":
        analytics["sessions"]["total_created"] += 1
        analytics["sessions"]["by_type"][session_data["type"]] += 1
        analytics["sessions"]["daily_created"][today] = analytics["sessions"]["daily_created"].get(today, 0) + 1
        
        # Track character usage
        for char in session_data.get("characters", []):
            char_name = char.get("name", "Unknown")
            analytics["characters"]["most_used"][char_name] = analytics["characters"]["most_used"].get(char_name, 0) + 1
        
        # Track character combinations
        char_names = tuple(sorted([c.get("name", "Unknown") for c in session_data.get("characters", [])]))
        if len(char_names) > 1:
            analytics["characters"]["combinations"][str(char_names)] = analytics["characters"]["combinations"].get(str(char_names), 0) + 1
    
    elif action == "completed":
        analytics["sessions"]["total_completed"] += 1
        analytics["sessions"]["daily_completed"][today] = analytics["sessions"]["daily_completed"].get(today, 0) + 1
        
        # Calculate completion rates
        for session_type in ["chat", "story"]:
            created = analytics["sessions"]["by_type"].get(session_type, 0)
            completed = sum(1 for s in analytics["sessions"]["daily_completed"].values() if s > 0)  # Simplified
            analytics["sessions"]["completion_rates"][session_type] = (completed / created * 100) if created > 0 else 0
    
    save_analytics(analytics)

def update_content_analytics(session_data, word_count, generation_time=None):
    """Update content analytics when content is generated"""
    analytics = load_analytics()
    today = datetime.datetime.now().strftime("%Y-%m-%d")
    
    # Word count tracking
    analytics["content"]["total_words"] += word_count
    session_type = session_data.get("type", "unknown")
    
    # Update average words per session type
    current_avg = analytics["content"]["average_words_per_session"].get(session_type, 0)
    session_count = analytics["sessions"]["by_type"].get(session_type, 1)
    analytics["content"]["average_words_per_session"][session_type] = (
        (current_avg * (session_count - 1) + word_count) / session_count
    )
    
    # Word count trends
    analytics["content"]["word_count_trends"][today] = analytics["content"]["word_count_trends"].get(today, 0) + word_count
    
    # Performance tracking
    if generation_time:
        analytics["performance"]["generation_times"].append(generation_time)
        # Keep only last 100 generation times
        if len(analytics["performance"]["generation_times"]) > 100:
            analytics["performance"]["generation_times"] = analytics["performance"]["generation_times"][-100:]
        
        # Update average generation time
        times = analytics["performance"]["generation_times"]
        analytics["performance"]["average_generation_time"] = sum(times) / len(times) if times else 0
    
    save_analytics(analytics)

def update_sanitization_analytics(original_length, sanitized_length, preset_used):
    """Update sanitization analytics"""
    analytics = load_analytics()
    
    analytics["performance"]["sanitization_usage"] += 1
    
    # Calculate effectiveness (percentage of content preserved)
    if original_length > 0:
        effectiveness = (sanitized_length / original_length) * 100
        current_avg = analytics["performance"]["sanitization_effectiveness"]
        usage_count = analytics["performance"]["sanitization_usage"]
        
        analytics["performance"]["sanitization_effectiveness"] = (
            (current_avg * (usage_count - 1) + effectiveness) / usage_count
        )
    
    save_analytics(analytics)

@app.route('/api/analytics/overview', methods=['GET'])
def get_analytics_overview():
    """Get comprehensive analytics overview"""
    try:
        analytics = load_analytics()
        
        # Calculate additional metrics
        total_sessions = analytics["sessions"]["total_created"]
        completed_sessions = analytics["sessions"]["total_completed"]
        overall_completion_rate = (completed_sessions / total_sessions * 100) if total_sessions > 0 else 0
        
        # Get top characters
        top_characters = sorted(
            analytics["characters"]["most_used"].items(),
            key=lambda x: x[1],
            reverse=True
        )[:10]
        
        # Get top character combinations
        top_combinations = sorted(
            analytics["characters"]["combinations"].items(),
            key=lambda x: x[1],
            reverse=True
        )[:5]
        
        # Calculate recent activity (last 7 days)
        today = datetime.datetime.now()
        recent_created = 0
        recent_completed = 0
        
        for i in range(7):
            date = (today - datetime.timedelta(days=i)).strftime("%Y-%m-%d")
            recent_created += analytics["sessions"]["daily_created"].get(date, 0)
            recent_completed += analytics["sessions"]["daily_completed"].get(date, 0)
        
        return jsonify({
            "overview": {
                "total_sessions": total_sessions,
                "completed_sessions": completed_sessions,
                "overall_completion_rate": round(overall_completion_rate, 1),
                "total_words": analytics["content"]["total_words"],
                "average_generation_time": round(analytics["performance"]["average_generation_time"], 2),
                "sanitization_usage": analytics["performance"]["sanitization_usage"],
                "sanitization_effectiveness": round(analytics["performance"]["sanitization_effectiveness"], 1)
            },
            "recent_activity": {
                "sessions_created_7d": recent_created,
                "sessions_completed_7d": recent_completed,
                "words_generated_7d": sum(
                    analytics["content"]["word_count_trends"].get(
                        (today - datetime.timedelta(days=i)).strftime("%Y-%m-%d"), 0
                    ) for i in range(7)
                )
            },
            "session_types": analytics["sessions"]["by_type"],
            "completion_rates": analytics["sessions"]["completion_rates"],
            "average_words": analytics["content"]["average_words_per_session"],
            "top_characters": top_characters,
            "top_combinations": top_combinations
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/analytics/trends', methods=['GET'])
def get_analytics_trends():
    """Get trend data for charts"""
    try:
        analytics = load_analytics()
        days = int(request.args.get('days', 30))
        
        today = datetime.datetime.now()
        trend_data = {
            "dates": [],
            "sessions_created": [],
            "sessions_completed": [],
            "words_generated": [],
            "generation_times": []
        }
        
        for i in range(days - 1, -1, -1):
            date = (today - datetime.timedelta(days=i)).strftime("%Y-%m-%d")
            trend_data["dates"].append(date)
            trend_data["sessions_created"].append(analytics["sessions"]["daily_created"].get(date, 0))
            trend_data["sessions_completed"].append(analytics["sessions"]["daily_completed"].get(date, 0))
            trend_data["words_generated"].append(analytics["content"]["word_count_trends"].get(date, 0))
        
        return jsonify(trend_data)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/analytics/characters', methods=['GET'])
def get_character_analytics():
    """Get detailed character analytics"""
    try:
        analytics = load_analytics()
        
        # Character usage statistics
        character_stats = []
        for char_name, usage_count in analytics["characters"]["most_used"].items():
            # Calculate average words per character
            # This is a simplified calculation - in a real system you'd track this per character
            avg_words = analytics["content"]["total_words"] / max(len(analytics["characters"]["most_used"]), 1)
            
            character_stats.append({
                "name": char_name,
                "usage_count": usage_count,
                "average_words": round(avg_words, 0),
                "usage_percentage": round((usage_count / analytics["sessions"]["total_created"]) * 100, 1)
            })
        
        # Sort by usage count
        character_stats.sort(key=lambda x: x["usage_count"], reverse=True)
        
        return jsonify({
            "character_stats": character_stats,
            "top_combinations": analytics["characters"]["combinations"],
            "total_characters_used": len(analytics["characters"]["most_used"])
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/analytics/performance', methods=['GET'])
def get_performance_analytics():
    """Get performance metrics"""
    try:
        analytics = load_analytics()
        
        # Generation time distribution
        generation_times = analytics["performance"]["generation_times"]
        time_distribution = {
            "fast": len([t for t in generation_times if t < 30]),
            "medium": len([t for t in generation_times if 30 <= t < 120]),
            "slow": len([t for t in generation_times if t >= 120])
        }
        
        # Session duration analysis
        session_durations = analytics["sessions"]["average_duration"]
        
        return jsonify({
            "generation_times": {
                "average": round(analytics["performance"]["average_generation_time"], 2),
                "distribution": time_distribution,
                "recent_times": generation_times[-20:] if generation_times else []
            },
            "session_durations": session_durations,
            "sanitization": {
                "usage_count": analytics["performance"]["sanitization_usage"],
                "effectiveness": round(analytics["performance"]["sanitization_effectiveness"], 1)
            }
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/analytics/reset', methods=['POST'])
def reset_analytics():
    """Reset all analytics data"""
    try:
        analytics = {
            "sessions": {},
            "content": {},
            "characters": {},
            "performance": {},
            "trends": {},
            "sanitization": {}
        }
        save_analytics(analytics)
        return jsonify({"message": "Analytics reset successfully"})
    except Exception as e:
        return jsonify({"error": f"Failed to reset analytics: {str(e)}"}), 500

# ────────────────────────────  Content Rating System  ────────────────────────────

RATINGS_FILE = SETTINGS_DIR / "content_ratings.json"
RATINGS_LOCK = threading.Lock()

def load_ratings():
    """Load content ratings from file"""
    if RATINGS_FILE.exists():
        try:
            with open(RATINGS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            pass
    return {"sessions": {}, "quick_chats": {}}

def save_ratings(ratings):
    """Save content ratings to file"""
    with RATINGS_LOCK:
        with open(RATINGS_FILE, 'w', encoding='utf-8') as f:
            json.dump(ratings, f, indent=2, ensure_ascii=False)

@app.route('/api/ratings/session/<session_id>', methods=['GET'])
def get_session_rating(session_id):
    """Get rating for a specific session"""
    try:
        ratings = load_ratings()
        session_rating = ratings.get("sessions", {}).get(session_id, {})
        return jsonify(session_rating)
    except Exception as e:
        return jsonify({"error": f"Failed to get session rating: {str(e)}"}), 500

@app.route('/api/ratings/session/<session_id>', methods=['POST'])
def rate_session(session_id):
    """Rate a session with content rating and optional feedback"""
    try:
        data = request.get_json() or {}
        rating = data.get('rating')  # 1-5 stars
        content_rating = data.get('content_rating')  # G, PG, PG-13, R, NC-17
        feedback = data.get('feedback', '')
        tags = data.get('tags', [])  # e.g., ["violence", "romance", "humor"]
        
        if not rating or not content_rating:
            return jsonify({"error": "Rating and content_rating are required"}), 400
        
        if not (1 <= rating <= 5):
            return jsonify({"error": "Rating must be between 1 and 5"}), 400
        
        valid_content_ratings = ["G", "PG", "PG-13", "R", "NC-17"]
        if content_rating not in valid_content_ratings:
            return jsonify({"error": f"Content rating must be one of: {valid_content_ratings}"}), 400
        
        # Load existing ratings
        ratings = load_ratings()
        
        # Get session data to include title and preview
        session_data = {}
        try:
            session_file = find_session_file(session_id)
            if session_file and session_file.exists():
                with open(session_file, 'r', encoding='utf-8') as f:
                    session_data = json.load(f)
        except Exception:
            pass
        
        # Update session rating
        ratings["sessions"][session_id] = {
            "rating": rating,
            "content_rating": content_rating,
            "feedback": feedback,
            "tags": tags,
            "rated_at": datetime.datetime.now().isoformat(),
            "rated_by": "user",  # Could be extended to support multiple users
            "id": session_id,
            "title": session_data.get("title", f"Session {session_id}"),
            "type": session_data.get("type", "unknown"),
            "preview": session_data.get("messages", [{}])[0].get("content", "")[:200] if session_data.get("messages") else "",
            "characters": [char.get("name", "Unknown") for char in session_data.get("characters", [])]
        }
        
        save_ratings(ratings)
        
        return jsonify({
            "message": "Session rated successfully",
            "rating": ratings["sessions"][session_id]
        })
        
    except Exception as e:
        return jsonify({"error": f"Failed to rate session: {str(e)}"}), 500

@app.route('/api/ratings/quick-chat/<chat_id>', methods=['GET'])
def get_quick_chat_rating(chat_id):
    """Get rating for a specific quick chat"""
    try:
        ratings = load_ratings()
        chat_rating = ratings.get("quick_chats", {}).get(chat_id, {})
        return jsonify(chat_rating)
    except Exception as e:
        return jsonify({"error": f"Failed to get quick chat rating: {str(e)}"}), 500

@app.route('/api/ratings/quick-chat/<chat_id>', methods=['POST'])
def rate_quick_chat(chat_id):
    """Rate a quick chat"""
    try:
        data = request.get_json() or {}
        rating = data.get('rating')
        content_rating = data.get('content_rating')
        feedback = data.get('feedback', '')
        tags = data.get('tags', [])
        chat_data = data.get('chat_data', {})

        if not rating or not content_rating:
            return jsonify({"error": "Rating and content_rating are required"}), 400
            
        ratings = load_ratings()
        
        if "quick_chats" not in ratings:
            ratings["quick_chats"] = {}

        ratings["quick_chats"][chat_id] = {
            "rating": rating,
            "content_rating": content_rating,
            "feedback": feedback,
            "tags": tags,
            "rated_at": datetime.datetime.now().isoformat(),
            "rated_by": "user",
            "id": chat_id,
            "type": "quick_chat",
            "title": chat_data.get("title", f"Quick Chat {chat_id[:8]}"),
            "preview": chat_data.get("preview", "")[:200],
            "character": chat_data.get("character", "Unknown")
        }

        save_ratings(ratings)
        return jsonify({"message": "Quick Chat rated successfully"})
    except Exception as e:
        return jsonify({"error": f"Failed to rate quick chat: {str(e)}"}), 500

@app.route('/api/ratings/summary', methods=['GET'])
def get_ratings_summary():
    """Get summary of all ratings"""
    try:
        ratings = load_ratings()
        
        # Calculate summary statistics
        session_ratings = list(ratings.get("sessions", {}).values())
        quick_chat_ratings = list(ratings.get("quick_chats", {}).values())
        all_ratings = session_ratings + quick_chat_ratings
        
        if not all_ratings:
            return jsonify({
                "total_rated": 0,
                "average_rating": 0,
                "content_ratings": {},
                "popular_tags": [],
                "recent_ratings": []
            })
        
        # Calculate average rating
        total_rating = sum(r.get('rating', 0) for r in all_ratings)
        average_rating = round(total_rating / len(all_ratings), 2)
        
        # Count content ratings
        content_ratings = {}
        for rating in all_ratings:
            content_rating = rating.get('content_rating', 'Unknown')
            content_ratings[content_rating] = content_ratings.get(content_rating, 0) + 1
        
        # Get popular tags
        all_tags = []
        for rating in all_ratings:
            all_tags.extend(rating.get('tags', []))
        
        tag_counts = {}
        for tag in all_tags:
            tag_counts[tag] = tag_counts.get(tag, 0) + 1
        
        popular_tags = sorted(tag_counts.items(), key=lambda x: x[1], reverse=True)[:10]
        
        # Get recent ratings (last 10)
        recent_ratings = sorted(
            all_ratings, 
            key=lambda x: x.get('rated_at', ''), 
            reverse=True
        )[:10]
        
        return jsonify({
            "total_rated": len(all_ratings),
            "average_rating": average_rating,
            "content_ratings": content_ratings,
            "popular_tags": [{"tag": tag, "count": count} for tag, count in popular_tags],
            "recent_ratings": recent_ratings
        })
        
    except Exception as e:
        return jsonify({"error": f"Failed to get ratings summary: {str(e)}"}), 500

@app.route('/api/content-ratings', methods=['GET'])
def get_content_ratings():
    """Get all content ratings data"""
    try:
        ratings = load_ratings()
        return jsonify(ratings)
    except Exception as e:
        return jsonify({"error": f"Failed to get content ratings: {str(e)}"}), 500

@app.route('/api/ratings/reset', methods=['POST'])
def reset_ratings():
    """Reset all content ratings"""
    try:
        ratings = {"sessions": {}, "quick_chats": {}}
        save_ratings(ratings)
        return jsonify({"message": "Content ratings reset successfully"})
    except Exception as e:
        return jsonify({"error": f"Failed to reset ratings: {str(e)}"}), 500

def find_session_file(session_id):
    """Find session file by ID, checking main and subdirectories"""
    sessions_dir = STORIES_DIR / "sessions"
    session_file = sessions_dir / f"{session_id}.json"
    if session_file.exists():
        return session_file
    return None

@app.route('/api/ratings/migrate', methods=['POST'])
def migrate_ratings():
    """Migrate existing ratings to include new fields like title, type, preview, etc."""
    ratings_file = SETTINGS_DIR / 'content_ratings.json'
    if not ratings_file.exists():
        return jsonify({"message": "No ratings file to migrate."}), 200

    with open(ratings_file, 'r+', encoding='utf-8') as f:
        ratings = json.load(f)
        
        migrated = False

        # Migrate session ratings
        for session_id, rating_data in ratings.get("sessions", {}).items():
            if "id" not in rating_data:
                rating_data["id"] = session_id
                migrated = True
            if "type" not in rating_data:
                session_file = find_session_file(session_id)
                if session_file and session_file.exists():
                    with open(session_file, 'r', encoding='utf-8') as sf:
                        session_data = json.load(sf)
                        rating_data["type"] = session_data.get("type", "unknown")
                        migrated = True
        
        # Migrate quick chat ratings
        for chat_id, rating_data in ratings.get("quick_chats", {}).items():
            if "id" not in rating_data:
                rating_data["id"] = chat_id
                migrated = True
            if "type" not in rating_data:
                rating_data["type"] = "quick_chat"
                migrated = True

        if migrated:
            f.seek(0)
            json.dump(ratings, f, indent=2)
            f.truncate()
            return jsonify({"message": "Ratings migrated successfully."}), 200
        else:
            return jsonify({"message": "Ratings are already up-to-date."}), 200


@app.route("/api/characters/<character_id>/image", methods=["POST"])
def upload_character_image(character_id):
    """Upload an image for a character"""
    try:
        if "image" not in request.files:
            return jsonify({"error": "No image file provided"}), 400
        
        file = request.files["image"]
        if file.filename == "":
            return jsonify({"error": "No file selected"}), 400
        
        # Check file type
        allowed_extensions = {"png", "jpg", "jpeg", "gif", "webp"}
        file_extension = file.filename.rsplit(".", 1)[1].lower() if "." in file.filename else ""
        
        if file_extension not in allowed_extensions:
            return jsonify({"error": "Invalid file type. Allowed: PNG, JPG, JPEG, GIF, WEBP"}), 400
        
        # Create images directory if it doesn't exist
        images_dir = CHARACTERS_DIR / "images"
        images_dir.mkdir(exist_ok=True)
        
        # Save file with character ID as filename
        filename = f"{character_id}.{file_extension}"
        file_path = images_dir / filename
        file.save(str(file_path))
        
        # Update character data with image path
        char_file = find_character_file(character_id)
        if char_file and char_file.exists():
            with open(char_file, "r", encoding="utf-8") as f:
                char_data = json.load(f)
            
            # Add image path to character data
            if "lore" not in char_data:
                char_data["lore"] = {}
            char_data["lore"]["image"] = f"characters/images/{filename}"
            
            with open(char_file, "w", encoding="utf-8") as f:
                json.dump(char_data, f, indent=2, ensure_ascii=False)
        
        return jsonify({
            "message": "Image uploaded successfully",
            "image_path": f"characters/images/{filename}"
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/characters/<character_id>/image", methods=["DELETE"])
def delete_character_image(character_id):
    """Delete a character's image"""
    try:
        # Find and delete the image file
        images_dir = CHARACTERS_DIR / "images"
        for ext in ["png", "jpg", "jpeg", "gif", "webp"]:
            image_file = images_dir / f"{character_id}.{ext}"
            if image_file.exists():
                image_file.unlink()
                break
        
        # Remove image path from character data
        char_file = find_character_file(character_id)
        if char_file and char_file.exists():
            with open(char_file, "r", encoding="utf-8") as f:
                char_data = json.load(f)
            
            if "lore" in char_data and "image" in char_data["lore"]:
                del char_data["lore"]["image"]
            
            with open(char_file, "w", encoding="utf-8") as f:
                json.dump(char_data, f, indent=2, ensure_ascii=False)
        
        return jsonify({"message": "Image deleted successfully"})
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500



@app.route("/characters/images/<filename>")
def serve_character_image(filename):
    """Serve character images"""
    try:
        images_dir = CHARACTERS_DIR / "images"
        return send_from_directory(str(images_dir), filename)
    except Exception as e:
        return jsonify({"error": str(e)}), 404

# ────────────────────────────  Model Ratings & Tags ────────────────────────────
import threading
MODEL_RATINGS_FILE = SETTINGS_DIR / "model_ratings.json"
MODEL_RATINGS_LOCK = threading.Lock()

def load_model_ratings():
    if MODEL_RATINGS_FILE.exists():
        try:
            with open(MODEL_RATINGS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            pass
    return {}

def save_model_ratings(ratings):
    with MODEL_RATINGS_LOCK:
        with open(MODEL_RATINGS_FILE, 'w', encoding='utf-8') as f:
            json.dump(ratings, f, indent=2, ensure_ascii=False)

@app.route('/api/model-ratings', methods=['GET'])
def get_model_ratings():
    """Get all model ratings and tags"""
    try:
        ratings = load_model_ratings()
        return jsonify(ratings)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/model-ratings/<model_id>', methods=['POST'])
def set_model_rating(model_id):
    """Set or update rating/tags for a model"""
    try:
        data = request.get_json() or {}
        rating = data.get('rating')  # 1-5
        tags = data.get('tags', [])  # list of strings
        feedback = data.get('feedback', '')
        
        if not rating:
            return jsonify({'error': 'Rating is required'}), 400
        if not (1 <= int(rating) <= 5):
            return jsonify({'error': 'Rating must be 1-5'}), 400
        
        ratings = load_model_ratings()
        ratings[model_id] = {
            'rating': int(rating),
            'tags': tags,
            'feedback': feedback,
            'rated_at': datetime.datetime.now().isoformat(),
        }
        save_model_ratings(ratings)
        return jsonify({'message': 'Model rating updated', 'rating': ratings[model_id]})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ────────────────────────────  Model Preset Ratings & Tags ────────────────────────────
MODEL_PRESET_RATINGS_FILE = SETTINGS_DIR / "model_preset_ratings.json"
MODEL_PRESET_RATINGS_LOCK = threading.Lock()

def load_model_preset_ratings():
    if MODEL_PRESET_RATINGS_FILE.exists():
        try:
            with open(MODEL_PRESET_RATINGS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            pass
    return {}

def save_model_preset_ratings(ratings):
    with MODEL_PRESET_RATINGS_LOCK:
        with open(MODEL_PRESET_RATINGS_FILE, 'w', encoding='utf-8') as f:
            json.dump(ratings, f, indent=2, ensure_ascii=False)

@app.route('/api/model-preset-ratings', methods=['GET'])
def get_model_preset_ratings():
    """Get all model preset ratings and tags"""
    try:
        ratings = load_model_preset_ratings()
        return jsonify(ratings)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/model-preset-ratings/<preset_id>', methods=['POST'])
def set_model_preset_rating(preset_id):
    """Set or update rating/tags for a model preset"""
    try:
        data = request.get_json() or {}
        rating = data.get('rating')  # 1-5
        tags = data.get('tags', [])  # list of strings
        feedback = data.get('feedback', '')
        
        if not rating:
            return jsonify({'error': 'Rating is required'}), 400
        if not (1 <= int(rating) <= 5):
            return jsonify({'error': 'Rating must be 1-5'}), 400
        
        ratings = load_model_preset_ratings()
        ratings[preset_id] = {
            'rating': int(rating),
            'tags': tags,
            'feedback': feedback,
            'rated_at': datetime.datetime.now().isoformat(),
        }
        save_model_preset_ratings(ratings)
        return jsonify({'message': 'Model preset rating updated', 'rating': ratings[preset_id]})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ════════════════════════════════════════════════════════════════════════════════
# CHARACTER RATINGS ENDPOINTS  
# ════════════════════════════════════════════════════════════════════════════════

@app.route('/api/character-ratings', methods=['GET'])
def get_character_ratings():
    """Get all character ratings"""
    try:
        ratings_file = SETTINGS_DIR / 'character_ratings.json'
        
        if not ratings_file.exists():
            return jsonify({})
        
        with open(ratings_file, 'r', encoding='utf-8') as f:
            ratings = json.load(f)
        
        return jsonify(ratings)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/character-ratings/<character_id>', methods=['POST'])
def set_character_rating(character_id):
    """Set or update rating/tags for a character"""
    try:
        data = request.get_json() or {}
        rating = data.get('rating')  # 1-5
        notes = data.get('notes', '')
        tags = data.get('tags', [])
        
        # Validate rating
        if rating is not None and (not isinstance(rating, (int, float)) or not (1 <= rating <= 5)):
            return jsonify({'error': 'Rating must be between 1 and 5'}), 400
        
        # Load existing ratings
        ratings_file = SETTINGS_DIR / 'character_ratings.json'
        ratings = {}
        
        if ratings_file.exists():
            try:
                with open(ratings_file, 'r', encoding='utf-8') as f:
                    ratings = json.load(f)
            except json.JSONDecodeError:
                ratings = {}
        
        # Update or create rating entry
        if character_id not in ratings:
            ratings[character_id] = {}
        
        if rating is not None:
            ratings[character_id]['rating'] = float(rating)
            ratings[character_id]['rated_at'] = datetime.datetime.now().isoformat()
        
        if notes is not None:
            ratings[character_id]['notes'] = notes
            
        if tags is not None:
            ratings[character_id]['tags'] = tags
        
        ratings[character_id]['character_id'] = character_id
        
        # Save updated ratings
        ratings_file.parent.mkdir(parents=True, exist_ok=True)
        with open(ratings_file, 'w', encoding='utf-8') as f:
            json.dump(ratings, f, indent=2, ensure_ascii=False)
        
        return jsonify({'message': 'Character rating updated', 'rating': ratings[character_id]})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ────────────────────────────  Real Model Performance Analytics  ────────────────────────────
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from model_performance_tracker import model_tracker

@app.route('/api/model-performance', methods=['GET'])
def get_model_performance():
    """Get real-time model performance analytics"""
    try:
        # Get query parameters
        model_name = request.args.get('model')
        hours = int(request.args.get('hours', 24))
        
        # Get performance summary
        summary = model_tracker.get_performance_summary()
        
        # Get model-specific stats
        if model_name:
            stats = model_tracker.get_model_stats(model_name)
            recent_entries = model_tracker.get_recent_entries(hours, model_name)
        else:
            stats = model_tracker.get_model_stats()
            recent_entries = model_tracker.get_recent_entries(hours)
        
        return jsonify({
            'summary': summary,
            'model_stats': stats,
            'recent_entries': recent_entries[:50],  # Limit recent entries
            'timestamp': datetime.datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/model-performance/top', methods=['GET'])
def get_top_models():
    """Get top performing models by various metrics"""
    try:
        metric = request.args.get('metric', 'total_calls')
        limit = int(request.args.get('limit', 10))
        
        valid_metrics = [
            'total_calls', 'successful_calls', 'average_generation_time',
            'average_words_per_call', 'words_per_second', 'success_rate'
        ]
        
        if metric not in valid_metrics:
            return jsonify({'error': f'Invalid metric. Use one of: {valid_metrics}'}), 400
        
        top_models = model_tracker.get_top_models(metric, limit)
        
        return jsonify({
            'top_models': top_models,
            'metric': metric,
            'limit': limit
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/model-performance/reset', methods=['POST'])
def reset_model_performance():
    """Reset all model performance tracking data"""
    try:
        model_tracker.reset_performance_data()
        return jsonify({'message': 'Model performance data reset successfully'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ════════════════════════════════════════════════════════════════════════════════
# VISION PROCESSING ENDPOINTS
# ════════════════════════════════════════════════════════════════════════════════

@app.route('/api/vision/describe', methods=['POST'])
def describe_image():
    """Process uploaded image through vision model"""
    try:
        # Import vision processor
        import sys
        sys.path.append(str(ROOT_DIR))
        from vision_processor import get_vision_processor, format_image_message
        
        vision_processor = get_vision_processor()
        
        # Check if image file is provided
        if 'image' not in request.files:
            return jsonify({'error': 'No image file provided'}), 400
        
        image_file = request.files['image']
        if image_file.filename == '':
            return jsonify({'error': 'No image file selected'}), 400
        
        # Get optional character context
        character = None
        if 'character' in request.form:
            try:
                character = json.loads(request.form['character'])
            except json.JSONDecodeError:
                pass
        
        # Read image data
        image_data = image_file.read()
        
        # Process through vision model
        description = vision_processor.process_image_upload(image_data, character)
        
        # Format for chat
        formatted_message = format_image_message(description)
        
        return jsonify({
            'description': description,
            'formatted_message': formatted_message,
            'success': True
        })
        
    except Exception as e:
        app.logger.error(f"Vision processing failed: {e}")
        return jsonify({'error': 'Failed to process image'}), 500

@app.route('/api/vision/config', methods=['GET'])
def get_vision_config():
    """Get current vision processing configuration"""
    try:
        import sys
        sys.path.append(str(ROOT_DIR))
        from vision_processor import get_vision_processor
        
        vision_processor = get_vision_processor()
        
        return jsonify({
            'model': vision_processor.config.model,
            'global_prompt': vision_processor.config.global_prompt,
            'enabled': vision_processor.config.enabled,
            'available_models': vision_processor.get_available_vision_models()
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/vision/config', methods=['POST'])
def update_vision_config():
    """Update vision processing configuration"""
    try:
        import sys
        sys.path.append(str(ROOT_DIR))
        from vision_processor import get_vision_processor, save_vision_config
        
        data = request.get_json() or {}
        
        vision_processor = get_vision_processor()
        vision_processor.update_vision_config(data)
        
        # Save to disk
        save_vision_config({
            'model': vision_processor.config.model,
            'global_prompt': vision_processor.config.global_prompt,
            'enabled': vision_processor.config.enabled
        })
        
        return jsonify({'message': 'Vision configuration updated'})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/characters/<character_id>/image-assets', methods=['GET'])
def get_character_image_assets(character_id):
    """Get image assets for a character"""
    try:
        import sys
        sys.path.append(str(ROOT_DIR))
        from vision_processor import get_vision_processor
        
        vision_processor = get_vision_processor()
        assets = vision_processor.get_character_image_assets(character_id)
        
        assets_data = []
        for asset in assets:
            assets_data.append({
                'filename': asset.filename,
                'keywords': asset.keywords,
                'url': f'/api/characters/{character_id}/image-assets/{asset.filename}'
            })
        
        return jsonify({'assets': assets_data})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/characters/<character_id>/image-assets', methods=['POST'])
def upload_character_image_asset(character_id):
    """Upload a new image asset for a character"""
    try:
        import sys
        sys.path.append(str(ROOT_DIR))
        from vision_processor import get_vision_processor
        
        vision_processor = get_vision_processor()
        
        # Check if image file is provided
        if 'image' not in request.files:
            return jsonify({'error': 'No image file provided'}), 400
        
        image_file = request.files['image']
        if image_file.filename == '':
            return jsonify({'error': 'No image file selected'}), 400
        
        # Get keywords
        keywords_str = request.form.get('keywords', '')
        keywords = [k.strip() for k in keywords_str.split(',') if k.strip()]
        
        if not keywords:
            return jsonify({'error': 'Keywords are required'}), 400
        
        # Read image data
        image_data = image_file.read()
        
        # Save the asset
        filename = vision_processor.save_character_image_asset(
            character_id, image_data, keywords, image_file.filename
        )
        
        # Update character data with new image asset
        try:
            char_file = CHARACTERS_DIR / f"{character_id}.json"
            if char_file.exists():
                with open(char_file, 'r', encoding='utf-8') as f:
                    character_data = json.load(f)
                
                # Add to imageAssets
                if 'imageAssets' not in character_data:
                    character_data['imageAssets'] = {}
                
                # Create keyword pattern
                keyword_pattern = '|'.join(keywords)
                character_data['imageAssets'][keyword_pattern] = filename
                
                # Save updated character
                with open(char_file, 'w', encoding='utf-8') as f:
                    json.dump(character_data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            app.logger.warning(f"Failed to update character data: {e}")
        
        return jsonify({
            'message': 'Image asset uploaded successfully',
            'filename': filename,
            'keywords': keywords,
            'url': f'/api/characters/{character_id}/image-assets/{filename}'
        })
        
    except Exception as e:
        app.logger.error(f"Failed to upload image asset: {e}")
        return jsonify({'error': 'Failed to upload image asset'}), 500

@app.route('/api/characters/<character_id>/image-assets/<filename>', methods=['GET'])
def serve_character_image_asset(character_id, filename):
    """Serve a character image asset"""
    try:
        import sys
        sys.path.append(str(ROOT_DIR))
        from vision_processor import get_vision_processor
        
        vision_processor = get_vision_processor()
        asset_path = vision_processor.assets_dir / character_id / filename
        
        if not asset_path.exists():
            return jsonify({'error': 'Image asset not found'}), 404
        
        return send_from_directory(asset_path.parent, asset_path.name)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/vision/scan-message', methods=['POST'])
def scan_message_for_images():
    """Scan a message for keywords that should trigger character images"""
    try:
        import sys
        sys.path.append(str(ROOT_DIR))
        from vision_processor import get_vision_processor
        
        data = request.get_json() or {}
        message_content = data.get('message', '')
        character = data.get('character')
        
        if not message_content or not character:
            return jsonify({'triggered_image': None})
        
        vision_processor = get_vision_processor()
        triggered_image = vision_processor.scan_for_character_images(message_content, character)
        
        if triggered_image:
            # Convert absolute path to URL
            character_id = character.get('id')
            filename = pathlib.Path(triggered_image).name
            image_url = f'/api/characters/{character_id}/image-assets/{filename}'
        else:
            image_url = None
        
        return jsonify({
            'triggered_image': image_url,
            'message_scanned': message_content[:100] + '...' if len(message_content) > 100 else message_content
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ════════════════════════════════════════════════════════════════════════════════
# MULTI-CHARACTER CHAT ENDPOINTS
# ════════════════════════════════════════════════════════════════════════════════

@app.route('/api/sessions/multi-character-chat', methods=['POST'])
def start_multi_character_chat():
    """Start a new multi-character chat session"""
    try:
        import sys
        sys.path.append(str(ROOT_DIR))
        from session_manager import get_session_manager
        
        data = request.get_json() or {}
        
        # Validate required fields
        characters = data.get('characters', [])
        if len(characters) < 2:
            return jsonify({'error': 'At least 2 characters are required for multi-character chat'}), 400
        
        scenario = data.get('scenario', '')
        max_turns = data.get('max_turns', 10)
        
        # Prepare task data
        task_data = {
            'type': 'multi_character_chat',
            'participants': characters,
            'scenario': scenario,
            'max_turns': max_turns,
            'current_turn': 0,
            'context_limit': data.get('context_limit', 4096)
        }
        
        # Create and queue the session
        session_manager = get_session_manager()
        task_id = session_manager.create_task('conversation', task_data, step_control=False)
        
        return jsonify({
            'message': 'Multi-character chat session started',
            'session_id': task_id,
            'participants': [char['name'] for char in characters],
            'scenario': scenario,
            'max_turns': max_turns
        })
        
    except Exception as e:
        app.logger.error(f"Failed to start multi-character chat: {e}")
        return jsonify({'error': 'Failed to start chat session'}), 500

@app.route('/api/sessions/<session_id>/status', methods=['GET'])
def get_session_status(session_id):
    """Get the status of a session"""
    try:
        import sys
        sys.path.append(str(ROOT_DIR))
        from session_manager import get_session_manager
        
        session_manager = get_session_manager()
        task = session_manager.get_task(session_id)
        
        if not task:
            return jsonify({'error': 'Session not found'}), 404
        
        response_data = {
            'session_id': session_id,
            'status': task.status.value,
            'created_at': task.created_at.isoformat(),
            'started_at': task.started_at.isoformat() if task.started_at else None,
            'completed_at': task.completed_at.isoformat() if task.completed_at else None,
            'progress': task.progress,
            'current_step': task.current_step,
            'total_steps': task.total_steps,
            'type': task.type,
            'error': task.error
        }
        
        # Add result data if available
        if task.result:
            response_data['result'] = task.result
        
        return jsonify(response_data)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/sessions/<session_id>/messages', methods=['GET'])
def get_session_messages(session_id):
    """Get messages from a session"""
    try:
        import sys
        sys.path.append(str(ROOT_DIR))
        from session_manager import get_session_manager
        
        session_manager = get_session_manager()
        task = session_manager.get_task(session_id)
        
        if not task:
            return jsonify({'error': 'Session not found'}), 404
        
        messages = []
        if task.result and 'messages' in task.result:
            messages = task.result['messages']
        
        return jsonify({
            'session_id': session_id,
            'messages': messages,
            'total_messages': len(messages)
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Multi-Character Chat endpoints
@app.route('/api/sessions/multi-character-chat', methods=['POST'])
def create_multi_character_chat():
    """Create a new multi-character chat session"""
    try:
        data = request.get_json()
        
        # Validate required fields
        characters = data.get('characters', [])
        if len(characters) < 2:
            return jsonify({'error': 'At least 2 characters are required'}), 400
        
        scenario = data.get('scenario', '')
        max_turns = data.get('max_turns', 10)
        context_limit = data.get('context_limit', 4096)
        
        # Import session manager
        import sys
        sys.path.append(str(ROOT_DIR))
        from session_manager import get_session_manager
        
        # Create task data
        task_data = {
            'type': 'multi_character_chat',
            'participants': characters,
            'scenario': scenario,
            'max_turns': max_turns,
            'context_limit': context_limit
        }
        
        # Create session task
        session_manager = get_session_manager()
        session_id = session_manager.create_task('conversation', task_data)
        
        return jsonify({
            'session_id': session_id,
            'message': 'Multi-character chat session created and queued'
        }), 201
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500



# ────────────────────────────  Character Analytics  ────────────────────────────
@app.route('/api/character-usage', methods=['GET'])
def get_character_usage_stats():
    """Get character usage statistics"""
    try:
        usage_file = SETTINGS_DIR / 'character_usage.json'
        
        if not usage_file.exists():
            return jsonify({})
        
        with open(usage_file, 'r', encoding='utf-8') as f:
            usage_data = json.load(f)
        
        return jsonify(usage_data)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/character-usage/<character_id>', methods=['POST'])
def record_character_usage(character_id):
    """Record character usage"""
    try:
        data = request.get_json() or {}
        session_type = data.get('session_type', 'unknown')
        metadata = data.get('metadata', {})
        
        usage_file = SETTINGS_DIR / 'character_usage.json'
        
        # Load existing usage data
        if usage_file.exists():
            with open(usage_file, 'r', encoding='utf-8') as f:
                usage_data = json.load(f)
        else:
            usage_data = {}
        
        # Initialize character data if not exists
        if character_id not in usage_data:
            usage_data[character_id] = {
                'total_messages': 0,
                'total_sessions': 0,
                'session_types': {},
                'first_used': datetime.datetime.now().isoformat(),
                'last_used': datetime.datetime.now().isoformat(),
                'total_response_time': 0.0,
                'response_count': 0
            }
        
        char_data = usage_data[character_id]
        
        # Update usage statistics
        char_data['total_messages'] += 1
        char_data['last_used'] = datetime.datetime.now().isoformat()
        
        # Track session types
        if session_type not in char_data['session_types']:
            char_data['session_types'][session_type] = 0
        char_data['session_types'][session_type] += 1
        
        # Track response time if provided
        if 'response_time' in metadata:
            char_data['total_response_time'] += metadata['response_time']
            char_data['response_count'] += 1
        
        # Track session if it's a new session
        if metadata.get('new_session', False):
            char_data['total_sessions'] += 1
        
        # Initialize model tracking if not exists
        if 'model_usage' not in char_data:
            char_data['model_usage'] = {
                'presets': {},
                'direct_models': {},
                'combinations': {}  # Track preset + model override combinations
            }
        
        # Track model/preset usage
        preset_used = metadata.get('preset_used')
        model_used = metadata.get('model_used')
        
        if preset_used:
            # Track preset usage
            if preset_used not in char_data['model_usage']['presets']:
                char_data['model_usage']['presets'][preset_used] = {
                    'count': 0,
                    'total_response_time': 0,
                    'response_count': 0,
                    'last_used': datetime.datetime.now().isoformat()
                }
            
            preset_stats = char_data['model_usage']['presets'][preset_used]
            preset_stats['count'] += 1
            preset_stats['last_used'] = datetime.datetime.now().isoformat()
            
            if 'response_time' in metadata:
                preset_stats['total_response_time'] += metadata['response_time']
                preset_stats['response_count'] += 1
        
        elif model_used:
            # Track direct model usage
            if model_used not in char_data['model_usage']['direct_models']:
                char_data['model_usage']['direct_models'][model_used] = {
                    'count': 0,
                    'total_response_time': 0,
                    'response_count': 0,
                    'last_used': datetime.datetime.now().isoformat()
                }
            
            model_stats = char_data['model_usage']['direct_models'][model_used]
            model_stats['count'] += 1
            model_stats['last_used'] = datetime.datetime.now().isoformat()
            
            if 'response_time' in metadata:
                model_stats['total_response_time'] += metadata['response_time']
                model_stats['response_count'] += 1
        
        # Track preset + model override combinations
        if preset_used and model_used:
            combo_key = f"{preset_used}+{model_used}"
            if combo_key not in char_data['model_usage']['combinations']:
                char_data['model_usage']['combinations'][combo_key] = {
                    'count': 0,
                    'preset': preset_used,
                    'model': model_used,
                    'total_response_time': 0,
                    'response_count': 0,
                    'last_used': datetime.datetime.now().isoformat()
                }
            
            combo_stats = char_data['model_usage']['combinations'][combo_key]
            combo_stats['count'] += 1
            combo_stats['last_used'] = datetime.datetime.now().isoformat()
            
            if 'response_time' in metadata:
                combo_stats['total_response_time'] += metadata['response_time']
                combo_stats['response_count'] += 1
        
        # Save updated usage data
        with open(usage_file, 'w', encoding='utf-8') as f:
            json.dump(usage_data, f, indent=2, ensure_ascii=False)
        
        return jsonify({'success': True, 'message': 'Character usage recorded'})
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/character-performance/<character_id>', methods=['GET'])
def get_character_performance(character_id):
    """Get character performance metrics"""
    try:
        usage_file = SETTINGS_DIR / 'character_usage.json'
        
        if not usage_file.exists():
            return jsonify({
                'total_messages': 0,
                'total_sessions': 0,
                'avg_response_time': 0,
                'session_types': {},
                'activity': []
            })
        
        with open(usage_file, 'r', encoding='utf-8') as f:
            usage_data = json.load(f)
        
        char_data = usage_data.get(character_id, {})
        
        # Calculate average response time
        avg_response_time = 0
        if char_data.get('response_count', 0) > 0:
            avg_response_time = char_data.get('total_response_time', 0) / char_data['response_count']
        
        return jsonify({
            'total_messages': char_data.get('total_messages', 0),
            'total_sessions': char_data.get('total_sessions', 0),
            'avg_response_time': round(avg_response_time, 2),
            'session_types': char_data.get('session_types', {}),
            'first_used': char_data.get('first_used'),
            'last_used': char_data.get('last_used'),
            'activity': []  # TODO: Implement daily activity tracking
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/character-usage/reset/<character_id>', methods=['POST'])
def reset_character_usage(character_id):
    """Reset character usage statistics"""
    try:
        usage_file = SETTINGS_DIR / 'character_usage.json'
        
        if not usage_file.exists():
            return jsonify({'success': True, 'message': 'No usage data to reset'})
        
        with open(usage_file, 'r', encoding='utf-8') as f:
            usage_data = json.load(f)
        
        # Remove character data
        if character_id in usage_data:
            del usage_data[character_id]
        
        # Save updated data
        with open(usage_file, 'w', encoding='utf-8') as f:
            json.dump(usage_data, f, indent=2, ensure_ascii=False)
        
        return jsonify({'success': True, 'message': 'Character usage statistics reset'})
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/character-best-model/<character_id>', methods=['GET'])
def get_character_best_model(character_id):
    """Get the best model recommendation for a character based on usage analytics and performance"""
    try:
        usage_file = SETTINGS_DIR / 'character_usage.json'
        
        # Load character usage data
        usage_data = {}
        if usage_file.exists():
            with open(usage_file, 'r', encoding='utf-8') as f:
                usage_data = json.load(f)
        
        char_data = usage_data.get(character_id, {})
        model_usage = char_data.get('model_usage', {})
        
        # Load model ratings for performance scoring
        ratings_file = SETTINGS_DIR / 'model_ratings.json'
        model_ratings = {}
        if ratings_file.exists():
            with open(ratings_file, 'r', encoding='utf-8') as f:
                model_ratings = json.load(f)
        
        # Load preset ratings
        preset_ratings_file = SETTINGS_DIR / 'model_preset_ratings.json'
        preset_ratings = {}
        if preset_ratings_file.exists():
            with open(preset_ratings_file, 'r', encoding='utf-8') as f:
                preset_ratings = json.load(f)
        
        # Score all available options
        recommendations = []
        
        # Score presets
        for preset_name, stats in model_usage.get('presets', {}).items():
            avg_response_time = 0
            if stats['response_count'] > 0:
                avg_response_time = stats['total_response_time'] / stats['response_count']
            
            # Calculate performance score
            usage_score = min(stats['count'] / 10, 1.0)  # Normalize usage (max 10 uses = 1.0)
            rating_score = preset_ratings.get(preset_name, {}).get('rating', 3) / 5.0  # Normalize rating
            response_time_score = max(0, 1.0 - (avg_response_time / 10.0))  # Faster = better
            
            # Weighted composite score
            composite_score = (
                usage_score * 0.4 +      # 40% usage frequency
                rating_score * 0.4 +     # 40% user rating
                response_time_score * 0.2 # 20% performance
            )
            
            recommendations.append({
                'type': 'preset',
                'id': preset_name,
                'name': preset_name,
                'score': composite_score,
                'usage_count': stats['count'],
                'avg_response_time': round(avg_response_time, 2),
                'user_rating': preset_ratings.get(preset_name, {}).get('rating'),
                'last_used': stats['last_used'],
                'reason': f"Used {stats['count']} times with avg {avg_response_time:.1f}s response"
            })
        
        # Score direct models
        for model_name, stats in model_usage.get('direct_models', {}).items():
            avg_response_time = 0
            if stats['response_count'] > 0:
                avg_response_time = stats['total_response_time'] / stats['response_count']
            
            usage_score = min(stats['count'] / 10, 1.0)
            rating_score = model_ratings.get(model_name, {}).get('rating', 3) / 5.0
            response_time_score = max(0, 1.0 - (avg_response_time / 10.0))
            
            composite_score = (
                usage_score * 0.4 +
                rating_score * 0.4 +
                response_time_score * 0.2
            )
            
            recommendations.append({
                'type': 'model',
                'id': model_name,
                'name': model_name,
                'score': composite_score,
                'usage_count': stats['count'],
                'avg_response_time': round(avg_response_time, 2),
                'user_rating': model_ratings.get(model_name, {}).get('rating'),
                'last_used': stats['last_used'],
                'reason': f"Used {stats['count']} times with avg {avg_response_time:.1f}s response"
            })
        
        # Score combinations (preset + model override)
        for combo_key, stats in model_usage.get('combinations', {}).items():
            avg_response_time = 0
            if stats['response_count'] > 0:
                avg_response_time = stats['total_response_time'] / stats['response_count']
            
            usage_score = min(stats['count'] / 5, 1.0)  # Combinations are less common
            preset_rating = preset_ratings.get(stats['preset'], {}).get('rating', 3) / 5.0
            model_rating = model_ratings.get(stats['model'], {}).get('rating', 3) / 5.0
            rating_score = (preset_rating + model_rating) / 2  # Average of both ratings
            response_time_score = max(0, 1.0 - (avg_response_time / 10.0))
            
            composite_score = (
                usage_score * 0.4 +
                rating_score * 0.4 +
                response_time_score * 0.2
            )
            
            recommendations.append({
                'type': 'combination',
                'id': combo_key,
                'name': f"{stats['preset']} + {stats['model']}",
                'preset': stats['preset'],
                'model': stats['model'],
                'score': composite_score,
                'usage_count': stats['count'],
                'avg_response_time': round(avg_response_time, 2),
                'user_rating': round(rating_score * 5, 1),
                'last_used': stats['last_used'],
                'reason': f"Combination used {stats['count']} times with good performance"
            })
        
        # Sort by score (highest first)
        recommendations.sort(key=lambda x: x['score'], reverse=True)
        
        # Get the best recommendation
        best_recommendation = recommendations[0] if recommendations else None
        
        # Fallback logic if no usage data exists
        fallback_recommendation = None
        if not best_recommendation:
            # Load character file to get default model
            char_file = None
            for file_path in CHARACTERS_DIR.glob("*.json"):
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        char_json = json.load(f)
                        if file_path.stem == character_id or char_json.get('lore', {}).get('name') == character_id:
                            char_file = file_path
                            break
                except:
                    continue
            
            if char_file:
                with open(char_file, 'r', encoding='utf-8') as f:
                    char_json = json.load(f)
                    default_model = char_json.get('model', 'default-model')
                    
                    fallback_recommendation = {
                        'type': 'model',
                        'id': default_model,
                        'name': default_model,
                        'score': 0.5,  # Neutral score for fallback
                        'usage_count': 0,
                        'avg_response_time': 0,
                        'user_rating': None,
                        'last_used': None,
                        'reason': 'Character default model (no usage history)'
                    }
        
        return jsonify({
            'best_recommendation': best_recommendation or fallback_recommendation,
            'all_recommendations': recommendations[:5],  # Top 5 recommendations
            'has_usage_data': len(recommendations) > 0,
            'total_usage_count': char_data.get('total_messages', 0)
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=8000)
