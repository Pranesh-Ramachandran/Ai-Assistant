"""
Call Notification Listener - Receives call alerts from companion phone app
Local Wi-Fi peer-to-peer communication, privacy-safe, battery efficient
"""

import socket
import json
import threading
from datetime import datetime
from typing import Optional, Callable
from security_manager import security_manager
from personality_coordinator import personality_coordinator

class CallNotificationListener:
    def __init__(self):
        self.listen_port = 8765
        self.server_socket = None
        self.is_listening = False
        self.callback_function = None
        self.security_mode = "home"  # Default to home mode
        
    def set_announcement_callback(self, callback: Callable[[str, str], None]):
        """Set callback function for call announcements"""
        self.callback_function = callback
    
    def start_listener(self) -> bool:
        """Start listening for call notifications"""
        try:
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server_socket.bind(('', self.listen_port))
            self.server_socket.listen(1)
            self.is_listening = True
            
            # Start listener thread
            listener_thread = threading.Thread(target=self._listen_for_calls, daemon=True)
            listener_thread.start()
            
            return True
        except Exception as e:
            print(f"Failed to start call listener: {e}")
            return False
    
    def stop_listener(self):
        """Stop listening for call notifications"""
        self.is_listening = False
        if self.server_socket:
            self.server_socket.close()
    
    def _listen_for_calls(self):
        """Main listener loop"""
        while self.is_listening:
            try:
                client_socket, address = self.server_socket.accept()
                
                # Receive data
                data = client_socket.recv(1024).decode('utf-8')
                client_socket.close()
                
                if data:
                    self._process_call_notification(data)
                    
            except Exception as e:
                if self.is_listening:  # Only log if we're supposed to be listening
                    print(f"Call listener error: {e}")
    
    def _process_call_notification(self, data: str):
        """Process incoming call notification"""
        try:
            call_data = json.loads(data)
            
            # Validate required fields
            if call_data.get('event') != 'incoming_call':
                return
            
            caller_name = call_data.get('caller_name', 'Unknown')
            timestamp = call_data.get('timestamp')
            
            # Get current security mode
            current_mode = security_manager.get_current_mode() if hasattr(security_manager, 'get_current_mode') else 'home'
            
            # Generate appropriate announcement
            announcement = self._generate_announcement(caller_name, current_mode)
            
            # Call the announcement callback
            if self.callback_function:
                self.callback_function(announcement, current_mode)
                
        except json.JSONDecodeError:
            print("Invalid call notification data received")
        except Exception as e:
            print(f"Error processing call notification: {e}")
    
    def _generate_announcement(self, caller_name: str, security_mode: str) -> str:
        """Generate appropriate call announcement based on context"""
        # Check if it's night time
        is_night = personality_coordinator.dnd_personality.is_night_time()
        current_language = personality_coordinator.current_language
        
        # Handle different security modes
        if security_mode == 'public':
            # Public mode - no caller name, just notification
            if current_language == 'tamil':
                return "அழைப்பு வந்துள்ளது."  # "Call incoming"
            else:
                return "Incoming call."
        
        elif security_mode == 'private':
            # Private mode - generic announcement
            if current_language == 'tamil':
                return "அழைப்பு வந்துள்ளது."
            else:
                return "You have an incoming call."
        
        else:  # Home mode - full announcement
            if caller_name == 'Unknown' or not caller_name:
                if current_language == 'tamil':
                    return "தெரியாத எண்ணிலிருந்து அழைப்பு."
                else:
                    return "Incoming call from an unsaved number."
            else:
                if current_language == 'tamil':
                    return f"{caller_name} அழைக்கிறார்."
                else:
                    return f"Incoming call from {caller_name}."
    
    def get_listener_status(self) -> dict:
        """Get current listener status"""
        return {
            'listening': self.is_listening,
            'port': self.listen_port,
            'has_callback': self.callback_function is not None
        }

# Global instance
call_listener = CallNotificationListener()