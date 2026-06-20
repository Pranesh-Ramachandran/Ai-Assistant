#!/usr/bin/env python3
"""
Document Intelligence test without AI dependencies.
"""

import os
import sys
import tempfile
from pathlib import Path

# Add jarvis to path
sys.path.insert(0, str(Path(__file__).resolve().parent))


def test_core_without_ai():
    """Test document intelligence without AI brain."""
    print("🧪 Testing Document Intelligence (No AI)...")
    
    # Import directly to avoid AI brain
    from jarvis.services.document_intelligence import DocumentIntelligence
    
    # Create instance without AI
    doc_intel = DocumentIntelligence()
    
    # Test 1: Formats
    print("\n1️⃣ Supported formats:")
    formats = doc_intel.list_supported_formats()
    print(formats)
    
    # Test 2: Create sample document
    sample_content = """
JARVIS AI Assistant - Technical Documentation

Overview:
JARVIS is a comprehensive AI assistant built with Python.

Key Features:
- Voice recognition using multiple STT engines
- Natural language processing
- Smart home device control
- Weather information via APIs
- Document processing and analysis

Installation:
1. Install Python 3.11+
2. Run: pip install -r requirements.txt
3. Execute: python -m jarvis.main --web

Architecture:
The system uses a modular design with Flask web interface.
"""
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
        f.write(sample_content.strip())
        temp_path = f.name
    
    try:
        # Test content extraction
        print(f"\n2️⃣ Extracting content from: {temp_path}")
        content = doc_intel._extract_text_file(temp_path)
        print(f"Content length: {len(content)} characters")
        assert "JARVIS AI Assistant" in content
        print("✅ Content extraction works")
        
        # Test fallback summary (without AI)
        print("\n3️⃣ Testing fallback summary:")
        summary = doc_intel._summarize_content(content, temp_path)
        print(summary)
        assert "JARVIS AI Assistant" in summary
        print("✅ Fallback summary works")
        
        # Test fallback Q&A (without AI)
        print("\n4️⃣ Testing fallback Q&A:")
        answer = doc_intel._answer_question(content, "What language is JARVIS built with", temp_path)
        print(answer)
        assert "Python" in answer
        print("✅ Fallback Q&A works")
        
        # Test structure analysis
        print("\n5️⃣ Testing structure analysis:")
        analysis = doc_intel.analyze_document_structure(temp_path)
        print(analysis)
        assert ".txt" in analysis
        print("✅ Structure analysis works")
        
    finally:
        os.unlink(temp_path)
    
    # Test cache
    print("\n6️⃣ Testing cache:")
    doc_intel._cache["test"] = "cached content"
    result = doc_intel.clear_cache()
    print(result)
    assert "1 cached documents" in result
    print("✅ Cache works")
    
    print("\n🎉 All core functionality tests passed!")


def test_voice_commands():
    """Test voice command processing."""
    print("\n🎤 Testing Voice Commands...")
    
    from jarvis.services.document_intelligence import process_document_command
    
    # Test format query
    result1 = process_document_command("what document formats do you support")
    print(f"Format query: {result1}")
    assert "Supported document formats" in result1
    
    # Test cache clear
    result2 = process_document_command("clear document cache")
    print(f"Clear cache: {result2}")
    assert "cached documents" in result2
    
    # Test invalid file
    result3 = process_document_command("analyze document nonexistent.pdf")
    print(f"Invalid file: {result3}")
    assert "File not found" in result3
    
    print("✅ Voice commands work")


if __name__ == "__main__":
    test_core_without_ai()
    test_voice_commands()
    print("\n🚀 Document Intelligence is fully functional!")