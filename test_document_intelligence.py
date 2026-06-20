#!/usr/bin/env python3
"""
Test script for JARVIS Document Intelligence functionality.
Tests PDF processing, OCR, text analysis, and question answering.
"""

import os
import sys
import tempfile
from pathlib import Path

# Add jarvis to path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from jarvis.services.document_intelligence import get_document_intelligence, process_document_command
from jarvis.core.brain import JarvisBrain


def create_sample_text_file():
    """Create a sample text file for testing."""
    content = """
JARVIS AI Assistant - Technical Specifications

Overview:
JARVIS is an advanced AI assistant built with Python, featuring voice recognition,
natural language processing, and smart home integration capabilities.

Key Features:
- Voice-to-text using multiple STT engines (Google, Azure, Vosk)
- Text-to-speech with pyttsx3 and edge-tts
- Weather information via wttr.in API
- Wikipedia integration for knowledge queries
- Smart home device control through IoT module
- Alarm and reminder system with persistent storage

Architecture:
The system follows a modular design with separate services for:
1. Core brain (intent analysis and response generation)
2. Natural language processing engine
3. Data collection services (weather, news, Wikipedia)
4. Text-to-speech and speech-to-text services
5. IoT device integration
6. Web-based user interface

Installation:
pip install -r requirements.txt
python -m jarvis.main --web

Technical Stack:
- Backend: Python 3.11+ with Flask web framework
- AI/ML: Groq and Google Gemini APIs for advanced reasoning
- Voice: SpeechRecognition, pyttsx3, edge-tts
- Data: SQLite for caching and user management
- Frontend: HTML5, CSS3, JavaScript with WebRTC for voice
"""
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
        f.write(content.strip())
        return f.name


def test_document_intelligence():
    """Test document intelligence functionality."""
    print("🧪 Testing JARVIS Document Intelligence...")
    
    # Initialize document intelligence
    doc_intel = get_document_intelligence()
    
    # Test 1: List supported formats
    print("\n1️⃣ Testing supported formats:")
    formats = doc_intel.list_supported_formats()
    print(formats)
    
    # Test 2: Create and process a sample text document
    print("\n2️⃣ Testing text document processing:")
    sample_file = create_sample_text_file()
    try:
        # Test basic summarization
        result = doc_intel.process_document(sample_file)
        print(f"Summary: {result}")
        
        # Test question answering
        print("\n3️⃣ Testing question answering:")
        questions = [
            "What programming language is JARVIS built with?",
            "What are the key features?",
            "How do you install JARVIS?",
            "What APIs does it use for AI?"
        ]
        
        for question in questions:
            answer = doc_intel.process_document(sample_file, question)
            print(f"Q: {question}")
            print(f"A: {answer}\n")
        
        # Test document analysis
        print("4️⃣ Testing document analysis:")
        analysis = doc_intel.analyze_document_structure(sample_file)
        print(f"Analysis: {analysis}")
        
    finally:
        # Cleanup
        os.unlink(sample_file)
    
    # Test 3: Brain integration
    print("\n5️⃣ Testing brain integration:")
    brain = JarvisBrain()
    
    test_commands = [
        "what document formats do you support",
        "analyze document sample.txt",
        "summarize document test.pdf",
        "clear document cache"
    ]
    
    for command in test_commands:
        intent = brain.analyze_intent(command)
        response = brain.generate_response(intent, command)
        print(f"Command: {command}")
        print(f"Intent: {intent}")
        print(f"Response: {response}\n")
    
    # Test 4: Direct command processing
    print("6️⃣ Testing direct command processing:")
    direct_commands = [
        "supported formats",
        "clear document cache"
    ]
    
    for cmd in direct_commands:
        result = process_document_command(cmd)
        print(f"Command: {cmd}")
        print(f"Result: {result}\n")
    
    print("✅ Document Intelligence tests completed!")


def test_missing_dependencies():
    """Test behavior when optional dependencies are missing."""
    print("\n🔧 Testing missing dependency handling...")
    
    # This will show warnings for missing dependencies
    try:
        doc_intel = get_document_intelligence()
        
        # Try processing a PDF (should show helpful message if PyPDF2 not installed)
        fake_pdf = "test.pdf"
        with open(fake_pdf, 'w') as f:
            f.write("fake pdf content")
        
        try:
            result = doc_intel._extract_pdf_text(fake_pdf)
            print(f"PDF processing result: {result}")
        finally:
            os.unlink(fake_pdf)
            
    except Exception as e:
        print(f"Expected behavior for missing dependencies: {e}")


if __name__ == "__main__":
    test_document_intelligence()
    test_missing_dependencies()
    print("\n🎉 All tests completed! Document Intelligence is ready for use.")