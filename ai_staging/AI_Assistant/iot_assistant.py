"""
IoT Assistant for Jarvis AI
Local-only smart home control - works only with devices that support local control.
No cloud-dependent devices supported to maintain privacy.
"""

import json
import os
from smart_bulb_controller import SmartBulbController

DEVICE_FILE = "devices.json"

class IoTAssistant:
    def __init__(self):
        self.local_only_notice = (
            "Note: This IoT assistant works only with devices that support local control. "
            "Cloud-dependent devices are not supported to maintain your privacy."
        )
        self.bulb_controller = SmartBulbController()

    def get_devices(self):
        """Load devices from file."""
        if os.path.exists(DEVICE_FILE):
            with open(DEVICE_FILE, "r") as f:
                return json.load(f)
        return {}

    def save_devices(self, devices):
        """Save devices to file."""
        with open(DEVICE_FILE, "w") as f:
            json.dump(devices, f, indent=2)

    def add_device(self):
        """Add a new IoT device with keyword and IP address."""
        print(self.local_only_notice)
        devices = self.get_devices()

        keyword = input("Enter keyword for this device (e.g., 'lamp', 'fan'): ").strip().lower()
        if keyword in devices:
            print(f"❌ Keyword '{keyword}' already exists. Choose another one.")
            return

        ip = input(f"Enter LOCAL IP address for '{keyword}' (e.g., 192.168.1.100): ").strip()
        devices[keyword] = {"ip": ip}
        self.save_devices(devices)

        print(f"✅ Device '{keyword}' added successfully with IP {ip}")
        print("💡 Tip: Only devices with local control APIs will work.")

    def control_device(self, command):
        """Control IoT device based on user command."""
        devices = self.get_devices()
        command = command.lower()

        # Match keyword
        matched_device = None
        for keyword in devices:
            if keyword in command:
                matched_device = keyword
                break

        if not matched_device:
            return "No matching device keyword found in command."

        # Determine action
        if "on" in command:
            action = "ON"
        elif "off" in command:
            action = "OFF"
        else:
            return "Please say 'on' or 'off' in your command."

        ip = devices[matched_device]["ip"]
        print(f"🎯 Sending '{action}' command to '{matched_device}' at {ip}")

        # TODO: Uncomment this when connecting real device
        # import requests
        # try:
        #     requests.get(f"http://{ip}/{action.lower()}", timeout=2)
        #     return f"{matched_device} turned {action}"
        # except Exception:
        #     return f"Could not reach {matched_device} at {ip}"

        return f"Command executed (simulated). {matched_device} turned {action}"

    def list_devices(self):
        """List all registered devices."""
        devices = self.get_devices()
        if not devices:
            return "No local devices found. Add devices with local control support only."

        device_list = "\nRegistered Local IoT Devices:"
        for keyword, info in devices.items():
            device_list += f"\n - {keyword} → {info['ip']} (local control)"
        device_list += "\n\n" + self.local_only_notice
        return device_list

    def remove_device(self, keyword):
        """Remove an IoT device by keyword."""
        devices = self.get_devices()
        if keyword not in devices:
            return f"❌ Device '{keyword}' not found."
        del devices[keyword]
        self.save_devices(devices)
        return f"✅ Device '{keyword}' removed successfully."

    def handle_iot_command(self, command):
        """Handle IoT commands and return a response string."""
        command = command.lower()
        
        # Check for bulb-specific commands first
        if any(word in command for word in ["bulb", "light", "lamp"]):
            if "add" in command:
                return self._add_bulb_interactive()
            elif "list" in command:
                return self.bulb_controller.list_bulbs()
            else:
                return self.bulb_controller.control_bulb(command)
        
        # Handle color commands (likely for bulbs)
        colors = ['red', 'green', 'blue', 'yellow', 'purple', 'orange', 'pink', 'white', 'cyan', 'magenta']
        if any(color in command for color in colors):
            return self.bulb_controller.control_bulb(command)
            
        # Handle brightness commands (likely for bulbs)
        if any(word in command for word in ["bright", "dim", "brightness", "%"]):
            return self.bulb_controller.control_bulb(command)
        
        # General IoT commands
        if "add device" in command or "add" in command:
            self.add_device()
            return "Device added."
        elif "list devices" in command or "list" in command:
            return self.list_devices()
        else:
            return self.control_device(command)
            
    def _add_bulb_interactive(self):
        """Interactive bulb addition."""
        print("\n🔵 Adding Smart Bulb to JARVIS")
        name = input("Enter bulb name (e.g., 'living room', 'bedroom'): ").strip()
        
        has_ip = input("Do you know the bulb's IP address? (y/n): ").strip().lower() == 'y'
        ip = None
        if has_ip:
            ip = input("Enter IP address: ").strip()
            
        has_app = input("Is it controlled by a third-party app? (y/n): ").strip().lower() == 'y'
        app_name = None
        if has_app:
            app_name = input("Enter app name (e.g., Smart Life, Tuya Smart): ").strip()
            
        result = self.bulb_controller.add_bulb(name, ip, app_name)
        print(result)
        return result
        
    def get_bulb_help(self):
        """Get smart bulb voice commands help."""
        return self.bulb_controller.get_voice_commands()

if __name__ == "__main__":
    iot = IoTAssistant()
    while True:
        print("\n=== IoT Assistant Menu ===")
        print("1. Add new device")
        print("2. Control device")
        print("3. List devices")
        print("4. Exit")
        choice = input("Enter your choice: ").strip()

        if choice == "1":
            iot.add_device()
        elif choice == "2":
            cmd = input("Enter your command (e.g., 'turn on lamp'): ")
            print(iot.control_device(cmd))
        elif choice == "3":
            print(iot.list_devices())
        elif choice == "4":
            print("👋 Exiting IoT Assistant.")
            break
        else:
            print("❌ Invalid choice.")
