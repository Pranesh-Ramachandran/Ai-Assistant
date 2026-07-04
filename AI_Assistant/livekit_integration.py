"""
JARVIS LiveKit Integration — Real-time voice rooms with Friday

Enables:
  - Real-time multi-user voice conversations
  - Browser-based agent playground
  - Voice room management
  - Participant tracking

Setup:
  1. Create LiveKit Cloud project (free tier available)
  2. Get project URL and API keys
  3. Set environment variables
  4. Start voice agent
"""

import os
import logging
from typing import Dict, Any, Optional, List
import json

# Load .env file if it exists
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    # Fallback: manually load .env
    env_path = os.path.join(os.path.dirname(__file__), "..", ".env")
    if os.path.exists(env_path):
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, value = line.split("=", 1)
                    os.environ[key.strip()] = value.strip()

LOGGER = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# LiveKit Configuration
# ─────────────────────────────────────────────────────────────────────────────

class LiveKitConfig:
    """Configuration for LiveKit integration."""
    
    def __init__(self):
        """Initialize LiveKit config from environment."""
        self.url = os.getenv("LIVEKIT_URL")
        self.api_key = os.getenv("LIVEKIT_API_KEY")
        self.api_secret = os.getenv("LIVEKIT_API_SECRET")
        self.port = int(os.getenv("LIVEKIT_PORT", "8000"))
        self.dev_mode = os.getenv("LIVEKIT_DEV_MODE", "false").lower() == "true"
    
    def is_configured(self) -> bool:
        """Check if LiveKit is properly configured."""
        return bool(self.url and self.api_key and self.api_secret)
    
    def validate(self) -> Dict[str, Any]:
        """Validate configuration."""
        issues = []
        
        if not self.url:
            issues.append("LIVEKIT_URL not set")
        if not self.api_key:
            issues.append("LIVEKIT_API_KEY not set")
        if not self.api_secret:
            issues.append("LIVEKIT_API_SECRET not set")
        
        return {
            "valid": len(issues) == 0,
            "issues": issues,
            "configured": self.is_configured(),
        }
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary (hide secrets)."""
        return {
            "url": self.url,
            "port": self.port,
            "dev_mode": self.dev_mode,
            "api_key_present": bool(self.api_key),
            "api_secret_present": bool(self.api_secret),
        }


# ─────────────────────────────────────────────────────────────────────────────
# Voice Room Manager
# ─────────────────────────────────────────────────────────────────────────────

class VoiceRoomManager:
    """Manages LiveKit voice rooms."""
    
    def __init__(self, config: Optional[LiveKitConfig] = None):
        """Initialize room manager."""
        self.config = config or LiveKitConfig()
        self.active_rooms: Dict[str, Dict[str, Any]] = {}
        self.participants: Dict[str, List[str]] = {}
    
    def create_room(self, room_name: str, metadata: Optional[Dict] = None) -> Dict[str, Any]:
        """Create a new voice room."""
        if not self.config.is_configured():
            LOGGER.error("LiveKit not configured")
            return {"success": False, "error": "LiveKit not configured"}
        
        room_info = {
            "name": room_name,
            "created_at": str(__import__('datetime').datetime.now()),
            "metadata": metadata or {},
            "participants": [],
            "status": "active",
        }
        
        self.active_rooms[room_name] = room_info
        self.participants[room_name] = []
        
        LOGGER.info(f"Created room: {room_name}")
        
        return {
            "success": True,
            "room_name": room_name,
            "room_info": room_info,
        }
    
    def join_room(self, room_name: str, participant_name: str) -> Dict[str, Any]:
        """Join a participant to a room."""
        if room_name not in self.active_rooms:
            return {"success": False, "error": f"Room '{room_name}' not found"}
        
        if participant_name not in self.participants.get(room_name, []):
            self.participants[room_name].append(participant_name)
            self.active_rooms[room_name]["participants"].append({
                "name": participant_name,
                "joined_at": str(__import__('datetime').datetime.now()),
            })
        
        LOGGER.info(f"Participant '{participant_name}' joined room '{room_name}'")
        
        return {
            "success": True,
            "room_name": room_name,
            "participant": participant_name,
            "room_info": self.active_rooms[room_name],
        }
    
    def leave_room(self, room_name: str, participant_name: str) -> Dict[str, Any]:
        """Remove a participant from a room."""
        if room_name not in self.active_rooms:
            return {"success": False, "error": f"Room '{room_name}' not found"}
        
        if participant_name in self.participants.get(room_name, []):
            self.participants[room_name].remove(participant_name)
            self.active_rooms[room_name]["participants"] = [
                p for p in self.active_rooms[room_name]["participants"]
                if p["name"] != participant_name
            ]
        
        LOGGER.info(f"Participant '{participant_name}' left room '{room_name}'")
        
        return {
            "success": True,
            "room_name": room_name,
            "participant": participant_name,
        }
    
    def get_room_info(self, room_name: str) -> Optional[Dict[str, Any]]:
        """Get information about a room."""
        return self.active_rooms.get(room_name)
    
    def list_active_rooms(self) -> List[Dict[str, Any]]:
        """List all active rooms."""
        return list(self.active_rooms.values())
    
    def close_room(self, room_name: str) -> Dict[str, Any]:
        """Close a room."""
        if room_name not in self.active_rooms:
            return {"success": False, "error": f"Room '{room_name}' not found"}
        
        del self.active_rooms[room_name]
        del self.participants[room_name]
        
        LOGGER.info(f"Closed room: {room_name}")
        
        return {
            "success": True,
            "room_name": room_name,
            "message": f"Room '{room_name}' closed",
        }


# ─────────────────────────────────────────────────────────────────────────────
# Voice Agent
# ─────────────────────────────────────────────────────────────────────────────

class VoiceAgent:
    """JARVIS voice agent for LiveKit rooms."""
    
    def __init__(self, room_name: str, config: Optional[LiveKitConfig] = None):
        """Initialize voice agent."""
        self.room_name = room_name
        self.config = config or LiveKitConfig()
        self.is_running = False
        self.audio_enabled = True
        self.video_enabled = False
    
    def start(self) -> Dict[str, Any]:
        """Start the voice agent."""
        if not self.config.is_configured():
            return {"success": False, "error": "LiveKit not configured"}
        
        self.is_running = True
        LOGGER.info(f"Voice agent started for room: {self.room_name}")
        
        return {
            "success": True,
            "agent_status": "running",
            "room_name": self.room_name,
            "livekit_url": self.config.url,
        }
    
    def stop(self) -> Dict[str, Any]:
        """Stop the voice agent."""
        self.is_running = False
        LOGGER.info(f"Voice agent stopped for room: {self.room_name}")
        
        return {
            "success": True,
            "agent_status": "stopped",
            "room_name": self.room_name,
        }
    
    def toggle_audio(self) -> Dict[str, Any]:
        """Toggle audio on/off."""
        self.audio_enabled = not self.audio_enabled
        return {
            "success": True,
            "audio_enabled": self.audio_enabled,
        }
    
    def get_status(self) -> Dict[str, Any]:
        """Get voice agent status."""
        return {
            "running": self.is_running,
            "room_name": self.room_name,
            "audio_enabled": self.audio_enabled,
            "video_enabled": self.video_enabled,
        }


# ─────────────────────────────────────────────────────────────────────────────
# Global Instances
# ─────────────────────────────────────────────────────────────────────────────

_global_config: Optional[LiveKitConfig] = None
_global_room_manager: Optional[VoiceRoomManager] = None
_global_agent: Optional[VoiceAgent] = None


def init_livekit(config: Optional[LiveKitConfig] = None) -> LiveKitConfig:
    """Initialize LiveKit configuration."""
    global _global_config
    _global_config = config or LiveKitConfig()
    return _global_config


def get_livekit_config() -> LiveKitConfig:
    """Get LiveKit configuration."""
    global _global_config
    if _global_config is None:
        _global_config = LiveKitConfig()
    return _global_config


def get_room_manager() -> VoiceRoomManager:
    """Get the global room manager."""
    global _global_room_manager
    if _global_room_manager is None:
        _global_room_manager = VoiceRoomManager(get_livekit_config())
    return _global_room_manager


def get_voice_agent(room_name: str) -> VoiceAgent:
    """Get or create voice agent for a room."""
    return VoiceAgent(room_name, get_livekit_config())


def validate_livekit_setup() -> Dict[str, Any]:
    """Validate LiveKit setup."""
    config = get_livekit_config()
    validation = config.validate()
    
    return {
        "livekit_configured": config.is_configured(),
        "validation": validation,
        "config": config.to_dict(),
        "setup_url": "https://cloud.livekit.io/",
        "setup_steps": [
            "1. Create LiveKit Cloud account at https://cloud.livekit.io/",
            "2. Create a new project (free tier available)",
            "3. Get your project URL and API keys",
            "4. Set environment variables:",
            "   - LIVEKIT_URL",
            "   - LIVEKIT_API_KEY",
            "   - LIVEKIT_API_SECRET",
            "5. Start JARVIS voice agent",
            "6. Open LiveKit Agents Playground to test",
        ],
    }


__all__ = [
    "LiveKitConfig",
    "VoiceRoomManager",
    "VoiceAgent",
    "init_livekit",
    "get_livekit_config",
    "get_room_manager",
    "get_voice_agent",
    "validate_livekit_setup",
]
