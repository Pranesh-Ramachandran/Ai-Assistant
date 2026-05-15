#!/usr/bin/env python3
"""
Test script to verify state manager integration in MainScreen
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'AI_Assistant'))

import weakref
from state_manager import JarvisStateManager

class MockMainScreen:
    """Mock MainScreen for testing state manager integration"""
    def __init__(self):
        self.status_label_text = ""
        self.state_manager = None

    def set_status_label(self, text):
        self.status_label_text = text
        print(f"Status label updated to: {text}")

    def on_state_change(self, old_state, new_state):
        """Handle state changes from state manager"""
        if new_state == self.state_manager.ACTIVE_MODE:
            self.set_status_label("Say 'Hey Jarvis' to wake me up")
        elif new_state == self.state_manager.LIGHT_IDLE:
            self.set_status_label("Light idle mode - listening for wake word")
        elif new_state == self.state_manager.DEEP_IDLE:
            self.set_status_label("Deep idle - wake word only")

def test_state_manager_integration():
    """Test state manager initialization and callback functionality"""
    print("Testing state manager integration...")

    # Create mock main screen
    mock_screen = MockMainScreen()

    # Initialize state manager with weak reference
    try:
        mock_screen.state_manager = JarvisStateManager(weakref.ref(mock_screen))
        mock_screen.state_manager.add_state_change_callback(mock_screen.on_state_change)
        print("✓ State manager initialized successfully with weak reference")
    except Exception as e:
        print(f"✗ Failed to initialize state manager: {e}")
        return False

    # Test state transitions
    print("\nTesting state transitions...")

    # Test ACTIVE_MODE
    try:
        mock_screen.state_manager.set_state(mock_screen.state_manager.ACTIVE_MODE)
        expected = "Say 'Hey Jarvis' to wake me up"
        if mock_screen.status_label_text == expected:
            print("✓ ACTIVE_MODE state change handled correctly")
        else:
            print(f"✗ ACTIVE_MODE failed: expected '{expected}', got '{mock_screen.status_label_text}'")
            return False
    except Exception as e:
        print(f"✗ ACTIVE_MODE transition failed: {e}")
        return False

    # Test LIGHT_IDLE
    try:
        mock_screen.state_manager.force_state(mock_screen.state_manager.LIGHT_IDLE)
        expected = "Light idle mode - listening for wake word"
        if mock_screen.status_label_text == expected:
            print("✓ LIGHT_IDLE state change handled correctly")
        else:
            print(f"✗ LIGHT_IDLE failed: expected '{expected}', got '{mock_screen.status_label_text}'")
            return False
    except Exception as e:
        print(f"✗ LIGHT_IDLE transition failed: {e}")
        return False

    # Test DEEP_IDLE
    try:
        mock_screen.state_manager.force_state(mock_screen.state_manager.DEEP_IDLE)
        expected = "Deep idle - wake word only"
        if mock_screen.status_label_text == expected:
            print("✓ DEEP_IDLE state change handled correctly")
        else:
            print(f"✗ DEEP_IDLE failed: expected '{expected}', got '{mock_screen.status_label_text}'")
            return False
    except Exception as e:
        print(f"✗ DEEP_IDLE transition failed: {e}")
        return False

    print("\n✓ All state manager integration tests passed!")
    return True

if __name__ == "__main__":
    success = test_state_manager_integration()
    sys.exit(0 if success else 1)
