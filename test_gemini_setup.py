#!/usr/bin/env python3
"""
Test Gemini API Key Configuration for JARVIS Vision
"""

import os
import sys
from pathlib import Path

# Add jarvis to path
sys.path.insert(0, str(Path(__file__).resolve().parent))

# Load environment variables
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    # Manual .env loading if python-dotenv not available
    env_path = Path(__file__).parent / '.env'
    if env_path.exists():
        with open(env_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    os.environ[key.strip()] = value.strip()


def test_gemini_api_key():
    """Test if Gemini API key is configured."""
    print("🔑 Testing Gemini API Key Configuration...")
    
    api_key = os.getenv("GEMINI_API_KEY")
    
    if not api_key:
        print("❌ GEMINI_API_KEY not found in environment")
        print("📋 Setup Instructions:")
        print("1. Get API key from: https://aistudio.google.com/apikey")
        print("2. Add to .env file: GEMINI_API_KEY=your_key_here")
        print("3. Run this test again")
        return False
    
    if api_key.strip() == "":
        print("❌ GEMINI_API_KEY is empty")
        return False
    
    print(f"✅ GEMINI_API_KEY found: {api_key[:10]}...{api_key[-4:]}")
    return True


def test_gemini_connection():
    """Test connection to Gemini API."""
    print("\n🌐 Testing Gemini API Connection...")
    
    try:
        import google.genai as genai
        
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            print("❌ No API key to test")
            return False
        
        client = genai.Client(api_key=api_key)
        
        # Simple text test (no vision)
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents="Say 'JARVIS vision test successful' if you can read this."
        )
        
        if response.text and "JARVIS vision test successful" in response.text:
            print("✅ Gemini API connection successful")
            print(f"📝 Response: {response.text.strip()}")
            return True
        else:
            print(f"⚠️ Unexpected response: {response.text}")
            return False
            
    except ImportError:
        print("❌ google-generativeai package not installed")
        print("📦 Install with: pip install google-generativeai")
        return False
    except Exception as e:
        print(f"❌ Gemini API test failed: {e}")
        return False


def test_vision_with_gemini():
    """Test vision system with Gemini integration."""
    print("\n👁️ Testing Vision System with AI...")
    
    try:
        from jarvis.services.vision import get_vision_capabilities, analyze_image_bytes
        
        # Check capabilities
        caps = get_vision_capabilities()
        print(f"📋 Vision capabilities: {caps}")
        
        if "AI Vision (Gemini)" in caps:
            print("✅ AI Vision capability detected")
            
            # Create a simple test image
            try:
                from PIL import Image, ImageDraw
                import io
                
                # Create test image
                img = Image.new('RGB', (200, 100), color='white')
                draw = ImageDraw.Draw(img)
                draw.text((20, 30), "JARVIS TEST", fill='black')
                
                # Convert to bytes
                buf = io.BytesIO()
                img.save(buf, format='JPEG')
                image_bytes = buf.getvalue()
                
                # Test AI analysis
                result = analyze_image_bytes(image_bytes, use_cloud=True)
                print(f"🤖 AI Analysis Result: {result}")
                
                if "Gemini couldn't describe" in result:
                    print("⚠️ AI analysis not working - check API key")
                    return False
                else:
                    print("✅ AI vision analysis working")
                    return True
                    
            except Exception as e:
                print(f"❌ Vision test failed: {e}")
                return False
        else:
            print("❌ AI Vision not available")
            return False
            
    except ImportError as e:
        print(f"❌ Vision system import failed: {e}")
        return False


def main():
    """Run all Gemini configuration tests."""
    print("🧪 JARVIS Gemini API Configuration Test")
    print("=" * 50)
    
    # Test 1: API Key
    key_ok = test_gemini_api_key()
    
    if key_ok:
        # Test 2: Connection
        connection_ok = test_gemini_connection()
        
        if connection_ok:
            # Test 3: Vision Integration
            vision_ok = test_vision_with_gemini()
            
            if vision_ok:
                print("\n🎉 All tests passed! Gemini AI Vision is ready to use.")
                print("\n🎯 Try these enhanced commands:")
                print("• 'analyze what you see' - Detailed scene analysis")
                print("• 'describe image photo.jpg' - AI image description")
                print("• Click 👁️ Vision button in web interface")
            else:
                print("\n⚠️ Vision integration needs work")
        else:
            print("\n❌ API connection failed")
    else:
        print("\n❌ API key configuration needed")
    
    print("\n📚 For setup help, see: GEMINI_SETUP_INSTRUCTIONS.md")


if __name__ == "__main__":
    main()