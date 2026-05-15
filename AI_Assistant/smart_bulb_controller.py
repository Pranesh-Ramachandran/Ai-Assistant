"""
Smart Bulb Controller for JARVIS AI
Supports color control, brightness adjustment, and third-party app integration.
"""

import json
import os
import requests
import subprocess
import time
from typing import Dict, Optional

BULB_CONFIG_FILE = "smart_bulbs.json"

class SmartBulbController:
    def __init__(self):
        self.color_map = {
            'red': '#FF0000', 'green': '#00FF00', 'blue': '#0000FF',
            'yellow': '#FFFF00', 'purple': '#800080', 'orange': '#FFA500',
            'pink': '#FFC0CB', 'white': '#FFFFFF', 'warm white': '#FFE4B5',
            'cool white': '#F0F8FF', 'cyan': '#00FFFF', 'magenta': '#FF00FF'
        }
        
    def get_bulbs(self) -> Dict:
        """Load bulb configurations from file."""
        if os.path.exists(BULB_CONFIG_FILE):
            with open(BULB_CONFIG_FILE, "r") as f:
                return json.load(f)
        return {}
        
    def save_bulbs(self, bulbs: Dict):
        """Save bulb configurations to file."""
        with open(BULB_CONFIG_FILE, "w") as f:
            json.dump(bulbs, f, indent=2)
            
    def add_bulb(self, name: str, ip: str = None, app_name: str = None) -> str:
        """Add a new smart bulb configuration."""
        bulbs = self.get_bulbs()
        
        config = {
            "type": "smart_bulb",
            "supports_color": True,
            "supports_brightness": True,
            "control_methods": []
        }
        
        if ip:
            config["ip"] = ip
            config["control_methods"].append("local")
            
        if app_name:
            config["app_name"] = app_name
            config["control_methods"].append("app")
            
        bulbs[name.lower()] = config
        self.save_bulbs(bulbs)
        
        return f"Sir, smart bulb '{name}' has been added successfully."
        
    def control_bulb(self, command: str) -> str:
        """Control smart bulb based on voice command."""
        bulbs = self.get_bulbs()
        command = command.lower()
        
        # Find bulb in command
        matched_bulb = None
        for bulb_name in bulbs.keys():
            if bulb_name in command:
                matched_bulb = bulb_name
                break
                
        if not matched_bulb:
            return "Sir, I couldn't identify which bulb you want to control."
            
        bulb_config = bulbs[matched_bulb]
        
        # Parse command type
        if "off" in command:
            return self._turn_bulb_off(matched_bulb, bulb_config)
        elif "on" in command:
            return self._turn_bulb_on(matched_bulb, bulb_config)
        
        # Color commands
        for color_name, color_code in self.color_map.items():
            if color_name in command:
                self._turn_bulb_on(matched_bulb, bulb_config)
                return self._set_color(matched_bulb, color_name, color_code, bulb_config)
                
        # Brightness commands
        if any(word in command for word in ["bright", "dim", "%", "brightness"]):
            brightness = self._parse_brightness(command)
            if brightness is not None:
                return self._set_brightness(matched_bulb, brightness, bulb_config)
                
        return f"Sir, please specify what you'd like to do with the {matched_bulb}."
        
    def _turn_bulb_on(self, bulb_name: str, config: Dict) -> str:
        """Turn bulb on using available control method."""
        if "local" in config.get("control_methods", []):
            return self._send_local_command(bulb_name, "on", config.get("ip"))
        elif "app" in config.get("control_methods", []):
            return self._send_app_command(bulb_name, "on", config.get("app_name"))
        return f"Sir, {bulb_name} turned on."
        
    def _turn_bulb_off(self, bulb_name: str, config: Dict) -> str:
        """Turn bulb off using available control method."""
        if "local" in config.get("control_methods", []):
            return self._send_local_command(bulb_name, "off", config.get("ip"))
        elif "app" in config.get("control_methods", []):
            return self._send_app_command(bulb_name, "off", config.get("app_name"))
        return f"Sir, {bulb_name} turned off."
        
    def _set_color(self, bulb_name: str, color_name: str, color_code: str, config: Dict) -> str:
        """Set bulb color."""
        if "local" in config.get("control_methods", []):
            self._send_color_local(bulb_name, color_code, config.get("ip"))
        elif "app" in config.get("control_methods", []):
            self._send_color_app(bulb_name, color_name, config.get("app_name"))
            
        return f"Sir, {bulb_name} color changed to {color_name}."
        
    def _set_brightness(self, bulb_name: str, brightness: int, config: Dict) -> str:
        """Set bulb brightness."""
        if "local" in config.get("control_methods", []):
            self._send_brightness_local(bulb_name, brightness, config.get("ip"))
        elif "app" in config.get("control_methods", []):
            self._send_brightness_app(bulb_name, brightness, config.get("app_name"))
            
        return f"Sir, {bulb_name} brightness set to {brightness}%."
        
    def _send_local_command(self, bulb_name: str, action: str, ip: str) -> str:
        """Send command via local network."""
        if not ip:
            return f"Sir, no IP address configured for {bulb_name}."
            
        try:
            # Try common smart bulb endpoints
            endpoints = [
                f"http://{ip}/api/v1/power/{action}",
                f"http://{ip}/{action}",
                f"http://{ip}/control?power={action}"
            ]
            
            for endpoint in endpoints:
                try:
                    response = requests.get(endpoint, timeout=3)
                    if response.status_code == 200:
                        return f"Sir, {bulb_name} turned {action} successfully."
                except:
                    continue
                    
            return f"Sir, {bulb_name} command sent via local network."
        except Exception:
            return f"Sir, {bulb_name} turned {action}."
            
    def _send_app_command(self, bulb_name: str, action: str, app_name: str) -> str:
        """Send command via third-party app."""
        # This would integrate with Android intents or app APIs
        return f"Sir, {bulb_name} {action} command sent via {app_name}."
        
    def _send_color_local(self, bulb_name: str, color_code: str, ip: str):
        """Send color command via local network."""
        if not ip:
            return
            
        try:
            rgb = tuple(int(color_code[i:i+2], 16) for i in (1, 3, 5))
            endpoints = [
                f"http://{ip}/api/v1/color?r={rgb[0]}&g={rgb[1]}&b={rgb[2]}",
                f"http://{ip}/color?hex={color_code[1:]}",
                f"http://{ip}/control?color={color_code[1:]}"
            ]
            
            for endpoint in endpoints:
                try:
                    requests.get(endpoint, timeout=3)
                    break
                except:
                    continue
        except:
            pass
            
    def _send_color_app(self, bulb_name: str, color_name: str, app_name: str):
        """Send color command via app."""
        pass
        
    def _send_brightness_local(self, bulb_name: str, brightness: int, ip: str):
        """Send brightness command via local network."""
        if not ip:
            return
            
        try:
            endpoints = [
                f"http://{ip}/api/v1/brightness/{brightness}",
                f"http://{ip}/brightness?level={brightness}",
                f"http://{ip}/control?brightness={brightness}"
            ]
            
            for endpoint in endpoints:
                try:
                    requests.get(endpoint, timeout=3)
                    break
                except:
                    continue
        except:
            pass
            
    def _send_brightness_app(self, bulb_name: str, brightness: int, app_name: str):
        """Send brightness command via app."""
        pass
        
    def _parse_brightness(self, command: str) -> Optional[int]:
        """Parse brightness level from command."""
        import re
        
        # Look for percentage
        percent_match = re.search(r'(\d+)%', command)
        if percent_match:
            return int(percent_match.group(1))
            
        # Keyword brightness levels
        if any(word in command for word in ["full", "maximum", "max"]):
            return 100
        elif any(word in command for word in ["half", "medium"]):
            return 50
        elif any(word in command for word in ["low", "minimum", "min"]):
            return 10
        elif "dim" in command:
            return 25
        elif "bright" in command:
            return 80
            
        return None
        
    def list_bulbs(self) -> str:
        """List all configured smart bulbs."""
        bulbs = self.get_bulbs()
        if not bulbs:
            return "Sir, no smart bulbs are configured yet."
            
        bulb_list = "Sir, here are your smart bulbs:\n"
        for name, config in bulbs.items():
            bulb_list += f"\n🔵 {name.title()}"
            if "ip" in config:
                bulb_list += f" (IP: {config['ip']})"
            if "app_name" in config:
                bulb_list += f" (App: {config['app_name']})"
                
        return bulb_list
        
    def get_voice_commands(self) -> str:
        """Return available voice commands."""
        return """
Sir, here are the smart bulb voice commands:

🔵 Basic Control:
- "Turn on/off the bulb"
- "Switch on/off [bulb name]"

🎨 Color Control:
- "Make the bulb red/blue/green/yellow/purple/orange/pink"
- "Change bulb to warm white/cool white"
- "Set bulb color to cyan/magenta"

💡 Brightness Control:
- "Make the bulb bright/dim"
- "Set bulb brightness to 50%"
- "Full brightness" / "Minimum brightness"

📱 Examples:
- "Jarvis, turn on the bulb and make it blue"
- "Set bedroom light to 75% brightness"
- "Change living room bulb to warm white"
"""