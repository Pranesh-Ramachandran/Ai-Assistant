"""
JARVIS Friday Integration — Main orchestrator

Coordinates:
  - Voice system (provider-based)
  - MCP server with tools
  - LLM tool calling
  - LiveKit voice rooms
  - Prompt templates

This is the central hub that brings everything together.
"""

import os
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime

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
# Friday System
# ─────────────────────────────────────────────────────────────────────────────

class Friday:
    """Main Friday integration system for JARVIS."""
    
    def __init__(self):
        """Initialize Friday system."""
        self.name = "FRIDAY"
        self.version = "2.0"
        self.started_at = datetime.now()
        self._initialized = False
        self._init_components()
    
    def _init_components(self) -> None:
        """Initialize all components."""
        try:
            # Initialize MCP server
            from mcp_server import init_mcp_server
            self.mcp_server = init_mcp_server("JARVIS-FRIDAY")
            LOGGER.info("✓ MCP server initialized")
            
            # Register web tools
            from mcp_web_tools import register_web_tools
            register_web_tools(self.mcp_server)
            
            # Register system tools
            from mcp_system_tools import register_system_tools
            register_system_tools(self.mcp_server)
            
            LOGGER.info("✓ Tools registered")
            
            # Initialize tool executor
            from tool_calling import init_tool_executor
            self.tool_executor = init_tool_executor()
            LOGGER.info("✓ Tool executor initialized")
            
            # Initialize prompt registry
            from prompt_templates import _global_prompt_registry
            self.prompts = _global_prompt_registry
            LOGGER.info("✓ Prompts initialized")
            
            # Initialize LiveKit
            from livekit_integration import init_livekit, get_room_manager
            self.livekit_config = init_livekit()
            self.room_manager = get_room_manager()
            LOGGER.info("✓ LiveKit initialized")
            
            self._initialized = True
            LOGGER.info("✓ Friday system fully initialized")
        
        except Exception as e:
            LOGGER.error(f"Error initializing Friday: {e}")
            self._initialized = False
    
    def is_ready(self) -> bool:
        """Check if Friday system is ready."""
        return self._initialized
    
    def get_status(self) -> Dict[str, Any]:
        """Get comprehensive system status."""
        return {
            "name": self.name,
            "version": self.version,
            "initialized": self._initialized,
            "started_at": self.started_at.isoformat(),
            "components": {
                "mcp_server": {
                    "available": hasattr(self, 'mcp_server'),
                    "tools_count": len(self.mcp_server.get_available_tools()) if hasattr(self, 'mcp_server') else 0,
                    "status": self.mcp_server.to_dict() if hasattr(self, 'mcp_server') else {},
                },
                "tool_executor": {
                    "available": hasattr(self, 'tool_executor'),
                    "tools_registered": len(self.tool_executor.get_available_tools()) if hasattr(self, 'tool_executor') else 0,
                },
                "prompts": {
                    "available": hasattr(self, 'prompts'),
                    "templates_count": len(self.prompts.list_prompts()) if hasattr(self, 'prompts') else 0,
                },
                "livekit": {
                    "available": hasattr(self, 'livekit_config'),
                    "configured": self.livekit_config.is_configured() if hasattr(self, 'livekit_config') else False,
                    "active_rooms": len(self.room_manager.active_rooms) if hasattr(self, 'room_manager') else 0,
                },
                "voice": {
                    "available": True,
                    "status": "ready",
                }
            },
        }
    
    # ─────────────────────────────────────────────────────────────────────────
    # Voice Control
    # ─────────────────────────────────────────────────────────────────────────
    
    def speak(self, text: str, provider_hint: Optional[str] = None) -> bool:
        """Speak text using configured voice provider."""
        try:
            from voice_provider_integration import speak as voice_speak
            return voice_speak(text, provider_hint=provider_hint)
        except Exception as e:
            LOGGER.error(f"Voice error: {e}")
            return False
    
    def listen(self, timeout: Optional[int] = None) -> str:
        """Listen using configured STT provider."""
        try:
            from voice_provider_integration import listen as voice_listen
            return voice_listen(timeout=timeout)
        except Exception as e:
            LOGGER.error(f"Listen error: {e}")
            return ""
    
    def switch_voice_provider(self, provider_type: str, provider_name: str) -> bool:
        """Switch voice provider."""
        try:
            from voice_provider_integration import set_voice_provider
            return set_voice_provider(provider_type, provider_name)
        except Exception as e:
            LOGGER.error(f"Provider switch error: {e}")
            return False
    
    def get_voice_status(self) -> Dict[str, Any]:
        """Get voice system status."""
        try:
            from voice_provider_integration import get_voice_info
            return get_voice_info()
        except Exception as e:
            return {"error": str(e)}
    
    # ─────────────────────────────────────────────────────────────────────────
    # Tool Calling
    # ─────────────────────────────────────────────────────────────────────────
    
    def get_available_tools(self) -> List[str]:
        """Get list of available tools."""
        return self.tool_executor.get_available_tools() if hasattr(self, 'tool_executor') else []
    
    def execute_tool(self, tool_name: str, **parameters) -> Dict[str, Any]:
        """Execute a tool directly."""
        from tool_calling import ToolCall
        
        tool_call = ToolCall(tool_name=tool_name, parameters=parameters)
        result = self.tool_executor.execute_tool(tool_call)
        return result.to_dict()
    
    def handle_llm_response(self, llm_response: str) -> Optional[Dict[str, Any]]:
        """Process LLM response and execute tools if needed."""
        result = self.tool_executor.handle_llm_response(llm_response)
        return result.to_dict() if result else None
    
    def get_tool_info(self, tool_name: str) -> Dict[str, Any]:
        """Get information about a tool."""
        return self.tool_executor.get_tool_info(tool_name)
    
    # ─────────────────────────────────────────────────────────────────────────
    # Voice Rooms
    # ─────────────────────────────────────────────────────────────────────────
    
    def create_room(self, room_name: str, metadata: Optional[Dict] = None) -> Dict[str, Any]:
        """Create a new voice room."""
        return self.room_manager.create_room(room_name, metadata)
    
    def join_room(self, room_name: str, participant_name: str) -> Dict[str, Any]:
        """Join a room."""
        return self.room_manager.join_room(room_name, participant_name)
    
    def leave_room(self, room_name: str, participant_name: str) -> Dict[str, Any]:
        """Leave a room."""
        return self.room_manager.leave_room(room_name, participant_name)
    
    def list_rooms(self) -> List[Dict[str, Any]]:
        """List active voice rooms."""
        return self.room_manager.list_active_rooms()
    
    # ─────────────────────────────────────────────────────────────────────────
    # Prompts
    # ─────────────────────────────────────────────────────────────────────────
    
    def get_prompt(self, name: str, **kwargs) -> str:
        """Get a prompt template."""
        return self.prompts.get_prompt(name, **kwargs) if hasattr(self, 'prompts') else ""
    
    def get_system_prompt(self) -> str:
        """Get the system prompt."""
        return self.prompts.get_system_prompt() if hasattr(self, 'prompts') else ""
    
    # ─────────────────────────────────────────────────────────────────────────
    # Session Management
    # ─────────────────────────────────────────────────────────────────────────
    
    def start_session(self, room_name: str, participant_name: str = "User") -> Dict[str, Any]:
        """Start a new Friday session."""
        LOGGER.info(f"Starting Friday session: {room_name}")
        
        # Create room
        room_result = self.create_room(room_name)
        
        # Join room
        join_result = self.join_room(room_name, participant_name)
        
        # Get system status
        status = self.get_status()
        
        return {
            "session_started": True,
            "room_name": room_name,
            "participant": participant_name,
            "room_info": room_result,
            "join_info": join_result,
            "system_status": status,
        }
    
    def end_session(self, room_name: str) -> Dict[str, Any]:
        """End a Friday session."""
        LOGGER.info(f"Ending Friday session: {room_name}")
        return self.room_manager.close_room(room_name)


# ─────────────────────────────────────────────────────────────────────────────
# Global Friday Instance
# ─────────────────────────────────────────────────────────────────────────────

_global_friday: Optional[Friday] = None


def init_friday() -> Friday:
    """Initialize the global Friday system."""
    global _global_friday
    _global_friday = Friday()
    return _global_friday


def get_friday() -> Friday:
    """Get the global Friday system (auto-initializes if needed)."""
    global _global_friday
    if _global_friday is None:
        _global_friday = Friday()
    return _global_friday


def print_friday_status() -> None:
    """Print formatted Friday system status."""
    friday = get_friday()
    status = friday.get_status()
    
    print("\n" + "="*70)
    print(f"  {status['name']} System Status (v{status['version']})")
    print("="*70)
    
    print(f"\n✓ Status: {'READY' if status['initialized'] else 'INITIALIZING'}")
    print(f"✓ Started: {status['started_at']}")
    
    print(f"\n📡 Components:")
    for component, info in status['components'].items():
        symbol = "✓" if info.get('available') else "✗"
        print(f"  {symbol} {component.upper()}")
        
        if component == "mcp_server" and info.get('tools_count'):
            print(f"      → Tools: {info['tools_count']}")
        elif component == "tool_executor" and info.get('tools_registered'):
            print(f"      → Registered: {info['tools_registered']}")
        elif component == "prompts" and info.get('templates_count'):
            print(f"      → Templates: {info['templates_count']}")
        elif component == "livekit":
            print(f"      → Configured: {info.get('configured')}")
            print(f"      → Active rooms: {info.get('active_rooms')}")
    
    print("="*70 + "\n")


__all__ = [
    "Friday",
    "init_friday",
    "get_friday",
    "print_friday_status",
]
