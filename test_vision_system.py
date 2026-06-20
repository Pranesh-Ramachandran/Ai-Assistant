#!/usr/bin/env python3
"""
Test script for JARVIS Vision System functionality.
Tests camera capture, OCR, QR scanning, and AI vision capabilities.
"""

import os
import sys
import tempfile
from pathlib import Path

# Add jarvis to path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from jarvis.services.vision import (
    handle_vision_command, 
    get_vision_capabilities,
    read_image_text,
    analyze_image_bytes,
    describe_image
)
from jarvis.core.brain import JarvisBrain


def create_test_image():
    """Create a simple test image with text."""
    try:
        from PIL import Image, ImageDraw, ImageFont
        
        # Create a simple image with text
        img = Image.new('RGB', (400, 200), color='white')
        draw = ImageDraw.Draw(img)
        
        # Try to use default font, fallback to basic if not available
        try:
            font = ImageFont.load_default()
        except:
            font = None
        
        text = "JARVIS VISION TEST\nThis is a test image for OCR\nHello World! 123"
        draw.text((20, 50), text, fill='black', font=font)
        
        # Save to temporary file
        with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as f:
            img.save(f.name, 'PNG')
            return f.name
            
    except ImportError:
        print("PIL not available - cannot create test image")
        return None
    except Exception as e:
        print(f"Error creating test image: {e}")
        return None


def test_vision_capabilities():
    """Test vision capability detection."""
    print("🧪 Testing JARVIS Vision System...")
    
    # Test 1: Check available capabilities
    print("\n1️⃣ Vision capabilities:")
    caps = get_vision_capabilities()
    print(caps)
    
    return "Vision features unavailable" not in caps


def test_ocr_functionality():
    """Test OCR text extraction."""
    print("\n2️⃣ Testing OCR functionality:")
    
    # Create test image
    test_image_path = create_test_image()
    if not test_image_path:
        print("❌ Could not create test image - skipping OCR test")
        return False
    
    try:
        # Read the test image with OCR
        result = describe_image(test_image_path, use_cloud=False)
        print(f"OCR Result: {result}")
        
        # Check if text was extracted
        success = "JARVIS" in result or "test" in result.lower() or "hello" in result.lower()
        if success:
            print("✅ OCR text extraction works")
        else:
            print("⚠️ OCR may not be working properly")
        
        return success
        
    except Exception as e:
        print(f"❌ OCR test failed: {e}")
        return False
    finally:
        # Clean up test image
        try:
            os.unlink(test_image_path)
        except:
            pass


def test_vision_commands():
    """Test vision command processing through the brain."""
    print("\n3️⃣ Testing vision command integration:")
    
    brain = JarvisBrain()
    
    test_commands = [
        "what are your vision capabilities",
        "what do you see",
        "read screen", 
        "scan qr code",
        "describe image test.jpg"
    ]
    
    for command in test_commands:
        try:
            intent = brain.analyze_intent(command)
            response = brain.generate_response(intent, command)
            print(f"Command: {command}")
            print(f"Intent: {intent}")
            print(f"Response: {response[:100]}...")
            print()
        except Exception as e:
            print(f"❌ Command '{command}' failed: {e}")


def test_direct_vision_commands():
    """Test direct vision command handling."""
    print("\n4️⃣ Testing direct vision commands:")
    
    commands = [
        "what do you see",
        "read screen text", 
        "scan qr from screen",
        "vision help"
    ]
    
    for cmd in commands:
        try:
            result = handle_vision_command(cmd)
            print(f"Command: {cmd}")
            print(f"Result: {result[:100]}...")
            print()
        except Exception as e:
            print(f"❌ Vision command '{cmd}' failed: {e}")


def test_image_analysis():
    """Test image analysis with different modes."""
    print("\n5️⃣ Testing image analysis modes:")
    
    # Create test image
    test_image_path = create_test_image()
    if not test_image_path:
        print("❌ Could not create test image - skipping analysis test")
        return
    
    try:
        # Test with binary image data
        with open(test_image_path, 'rb') as f:
            image_data = f.read()
        
        # Test free analysis (OCR only)
        print("Testing free analysis (OCR + QR):")
        free_result = analyze_image_bytes(image_data, use_cloud=False)
        print(f"Free mode: {free_result}")
        
        # Test cloud analysis (would use Gemini if configured)
        print("\nTesting cloud analysis:")
        cloud_result = analyze_image_bytes(image_data, use_cloud=True)
        print(f"Cloud mode: {cloud_result}")
        
    except Exception as e:
        print(f"❌ Image analysis test failed: {e}")
    finally:
        # Clean up
        try:
            os.unlink(test_image_path)
        except:
            pass


def test_dependency_availability():
    """Test which vision dependencies are available."""
    print("\n6️⃣ Testing vision dependencies:")
    
    dependencies = {
        "PIL (Pillow)": "PIL",
        "OpenCV": "cv2", 
        "pytesseract": "pytesseract",
        "pyzbar (QR codes)": "pyzbar",
        "numpy": "numpy",
        "rapidocr": "rapidocr_onnxruntime"
    }
    
    available = []
    missing = []
    
    for name, module in dependencies.items():
        try:
            __import__(module)
            print(f"✅ {name} - Available")
            available.append(name)
        except ImportError:
            print(f"❌ {name} - Not installed")
            missing.append(name)
    
    print(f"\nSummary: {len(available)} available, {len(missing)} missing")
    
    if missing:
        print("\nTo install missing dependencies:")
        install_commands = {
            "PIL (Pillow)": "pip install pillow",
            "OpenCV": "pip install opencv-python", 
            "pytesseract": "pip install pytesseract (+ tesseract engine)",
            "pyzbar (QR codes)": "pip install pyzbar",
            "numpy": "pip install numpy",
            "rapidocr": "pip install rapidocr-onnxruntime"
        }
        for dep in missing:
            if dep in install_commands:
                print(f"  {install_commands[dep]}")


def main():
    """Run all vision tests."""
    print("🎯 JARVIS Vision System Test Suite")
    print("=" * 50)
    
    # Test 1: Capabilities
    caps_available = test_vision_capabilities()
    
    # Test 2: Dependencies  
    test_dependency_availability()
    
    if caps_available:
        # Test 3: OCR
        test_ocr_functionality()
        
        # Test 4: Brain integration
        test_vision_commands()
        
        # Test 5: Direct commands
        test_direct_vision_commands()
        
        # Test 6: Image analysis
        test_image_analysis()
        
        print("\n🎉 Vision system tests completed!")
    else:
        print("\n⚠️ Vision system not available - install dependencies to enable features")
        print("Run: pip install opencv-python pillow pytesseract pyzbar")


if __name__ == "__main__":
    main()