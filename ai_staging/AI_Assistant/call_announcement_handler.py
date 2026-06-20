"""
Call Announcement Handler - Integrates call notifications with Jarvis TTS
Respects security modes, time awareness, and bilingual support
"""

from call_listener import call_listener
from personality_coordinator import personality_coordinator
from security_manager import security_manager
from thread_manager import thread_manager
import threading
import time

class CallAnnouncementHandler:
    def __init__(self):
        self.tts_engine = None
        self.is_enabled = True
        self.announcement_volume = 0.7  # Default volume
        
    def initialize(self, tts_engine):
        """Initialize with TTS engine and start call listener"""
        self.tts_engine = tts_engine
        
        # Set up call listener callback
        call_listener.set_announcement_callback(self.handle_call_announcement)
        
        # Start listening for calls
        success = call_listener.start_listener()
        if success:
            print("Call notification system started successfully")
        else:
            print("Failed to start call notification system")
    
    def handle_call_announcement(self, announcement_text: str, security_mode: str):
        """Handle incoming call announcement"""
        if not self.is_enabled or not self.tts_engine:
            return
        
        # Check security mode restrictions
        if security_mode == 'public':
            # In public mode, only vibrate or show visual notification
            self._handle_public_mode_notification()
            return
        
        # Check if it's night time for volume adjustment
        is_night = personality_coordinator.dnd_personality.is_night_time()
        
        # Adjust volume for night time
        volume = 0.3 if is_night else self.announcement_volume
        
        # Schedule announcement in audio thread
        if hasattr(thread_manager, 'submit_task'):
            thread_manager.submit_task(
                'AUDIO', 
                self._announce_call, 
                announcement_text, 
                volume,
                priority=1  # High priority for calls
            )
        else:
            # Fallback to direct threading
            announcement_thread = threading.Thread(
                target=self._announce_call, 
                args=(announcement_text, volume),
                daemon=True
            )
            announcement_thread.start()
    
    def _announce_call(self, announcement_text: str, volume: float):
        """Announce the incoming call"""
        try:
            # Set volume if TTS supports it
            if hasattr(self.tts_engine, 'set_volume'):
                original_volume = getattr(self.tts_engine, 'volume', 0.7)
                self.tts_engine.set_volume(volume)
            
            # Speak the announcement
            self.tts_engine.speak(announcement_text)
            
            # Wait for announcement to complete
            time.sleep(2)  # Adjust based on typical announcement length
            
            # Restore original volume
            if hasattr(self.tts_engine, 'set_volume'):
                self.tts_engine.set_volume(original_volume)
                
        except Exception as e:
            print(f"Call announcement error: {e}")
    
    def _handle_public_mode_notification(self):
        """Handle call notification in public mode (no audio)"""
        # In a real implementation, this could:
        # - Show a visual notification
        # - Vibrate the device
        # - Flash the Jarvis ring
        print("Call notification (public mode - silent)")
    
    def enable_call_announcements(self):
        """Enable call announcements"""
        self.is_enabled = True
        return "Call announcements enabled."
    
    def disable_call_announcements(self):
        """Disable call announcements"""
        self.is_enabled = False
        return "Call announcements disabled."
    
    def set_announcement_volume(self, volume: float):
        """Set call announcement volume (0.0 to 1.0)"""
        self.announcement_volume = max(0.0, min(1.0, volume))
        return f"Call announcement volume set to {int(self.announcement_volume * 100)}%"
    
    def get_status(self) -> dict:
        """Get call notification system status"""
        listener_status = call_listener.get_listener_status()
        
        return {
            'enabled': self.is_enabled,
            'volume': self.announcement_volume,
            'listener_active': listener_status['listening'],
            'listener_port': listener_status['port'],
            'tts_ready': self.tts_engine is not None
        }
    
    def handle_voice_command(self, command: str) -> str:
        """Handle voice commands related to call notifications"""
        command_lower = command.lower()
        
        if 'enable call' in command_lower or 'turn on call' in command_lower:
            return self.enable_call_announcements()
        
        elif 'disable call' in command_lower or 'turn off call' in command_lower:
            return self.disable_call_announcements()
        
        elif 'call volume' in command_lower:
            # Extract volume level from command
            words = command_lower.split()
            for i, word in enumerate(words):
                if word.isdigit():
                    volume = int(word) / 100.0
                    return self.set_announcement_volume(volume)
            
            return "Please specify volume level (0-100)"
        
        elif 'call status' in command_lower:
            status = self.get_status()
            if status['enabled'] and status['listener_active']:
                return "Call notifications are active and working."
            elif status['enabled']:
                return "Call notifications enabled but listener not active."
            else:
                return "Call notifications are disabled."
        
        return None
    
    def shutdown(self):
        """Shutdown call notification system"""
        call_listener.stop_listener()
        self.is_enabled = False

# Global instance
call_announcement_handler = CallAnnouncementHandler()