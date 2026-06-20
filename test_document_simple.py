#!/usr/bin/env python3
"""
Simple test for Document Intelligence core functionality.
Tests basic features without AI dependencies.
"""

import os
import sys
import tempfile
from pathlib import Path

# Add jarvis to path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from jarvis.services.document_intelligence import get_document_intelligence


def test_basic_functionality():
    """Test core document intelligence features."""
    print("🧪 Testing Document Intelligence Core Features...")
    
    doc_intel = get_document_intelligence()
    
    # Test 1: Supported formats
    print("\n1️⃣ Supported formats:")
    formats = doc_intel.list_supported_formats()
    print(formats)
    assert "Pdf: .pdf" in formats
    assert "Image:" in formats
    assert "Text:" in formats
    
    # Test 2: Text document processing
    print("\n2️⃣ Text document processing:")
    sample_content = """
JARVIS AI Assistant Documentation

This is a comprehensive AI assistant with the following features:
- Voice recognition and speech synthesis
- Natural language processing
- Smart home integration
- Weather and information queries
- Document processing capabilities

Installation:
pip install -r requirements.txt
python -m jarvis.main --web

The system uses Python 3.11+ and Flask for the web interface.
"""
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
        f.write(sample_content.strip())
        temp_path = f.name
    
    try:
        # Test basic summarization (fallback mode)
        result = doc_intel.process_document(temp_path)
        print(f"Summary: {result}")
        assert "JARVIS AI Assistant Documentation" in result
        
        # Test question answering (fallback mode) 
        answer = doc_intel.process_document(temp_path, "What programming language is used?")
        print(f"Q&A Result: {answer}")
        assert "Python" in answer
        
        # Test structure analysis
        analysis = doc_intel.analyze_document_structure(temp_path)
        print(f"Analysis: {analysis}")
        assert ".txt" in analysis
        
    finally:
        os.unlink(temp_path)
    
    # Test 3: Cache functionality
    print("\n3️⃣ Cache functionality:")
    cache_result = doc_intel.clear_cache()
    print(f"Cache cleared: {cache_result}")
    
    # Test 4: Error handling
    print("\n4️⃣ Error handling:")
    error_result = doc_intel.process_document("nonexistent_file.txt")
    print(f"Error handling: {error_result}")
    assert "File not found" in error_result
    
    print("\n✅ All core tests passed!")


def test_dependencies():
    """Test dependency availability."""
    print("\n🔧 Testing Dependencies...")
    
    # Test PDF support
    try:
        import PyPDF2
        print("✅ PyPDF2 available")
    except ImportError:
        print("❌ PyPDF2 not available")
    
    # Test OCR support  
    try:
        import pytesseract
        from PIL import Image
        print("✅ OCR libraries available")
    except ImportError:
        print("❌ OCR libraries not available")
    
    # Test requests
    try:
        import requests
        print("✅ Requests available")
    except ImportError:
        print("❌ Requests not available")


if __name__ == "__main__":
    test_basic_functionality()
    test_dependencies()
    print("\n🎉 Document Intelligence is working correctly!")