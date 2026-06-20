"""
JARVIS Document Intelligence — PDF parsing, OCR, image analysis, content summarization.
Supports upload/capture of documents for question answering and content extraction.
"""

import io
import logging
import os
import tempfile
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import requests

logger = logging.getLogger(__name__)

# Optional dependencies with fallbacks
try:
    import PyPDF2
    _PDF_AVAILABLE = True
except ImportError:
    _PDF_AVAILABLE = False
    
try:
    import pytesseract
    from PIL import Image
    _OCR_AVAILABLE = True
except ImportError:
    _OCR_AVAILABLE = False

try:
    # Lazy import to avoid circular dependency
    pass
except ImportError:
    pass


class DocumentIntelligence:
    """Document processing service for JARVIS."""
    
    def __init__(self):
        self.supported_formats = {
            'pdf': ['.pdf'],
            'image': ['.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.tif'],
            'text': ['.txt', '.md', '.rtf']
        }
        self._cache = {}
    
    def process_document(self, file_path: str, query: Optional[str] = None) -> str:
        """Main entry point for document processing."""
        if not os.path.exists(file_path):
            return f"File not found: {file_path}"
        
        file_ext = Path(file_path).suffix.lower()
        
        # Extract content based on file type
        content = self._extract_content(file_path, file_ext)
        if not content:
            return f"Could not extract content from {file_path}"
        
        # Cache the content
        self._cache[file_path] = content
        
        # Process query if provided
        if query:
            return self._answer_question(content, query, file_path)
        else:
            return self._summarize_content(content, file_path)
    
    def _extract_content(self, file_path: str, file_ext: str) -> Optional[str]:
        """Extract text content from various file formats."""
        try:
            if file_ext in self.supported_formats['pdf']:
                return self._extract_pdf_text(file_path)
            elif file_ext in self.supported_formats['image']:
                return self._extract_image_text(file_path)
            elif file_ext in self.supported_formats['text']:
                return self._extract_text_file(file_path)
            else:
                logger.warning(f"Unsupported file format: {file_ext}")
                return None
        except Exception as e:
            logger.error(f"Content extraction failed for {file_path}: {e}")
            return None
    
    def _extract_pdf_text(self, file_path: str) -> Optional[str]:
        """Extract text from PDF files."""
        if not _PDF_AVAILABLE:
            return "PDF processing requires PyPDF2. Install with: pip install PyPDF2"
        
        try:
            with open(file_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                text_content = []
                
                for page_num, page in enumerate(pdf_reader.pages):
                    page_text = page.extract_text()
                    if page_text.strip():
                        text_content.append(f"Page {page_num + 1}:\n{page_text}")
                
                return "\n\n".join(text_content) if text_content else None
        except Exception as e:
            logger.error(f"PDF extraction failed: {e}")
            return None
    
    def _extract_image_text(self, file_path: str) -> Optional[str]:
        """Extract text from images using OCR."""
        if not _OCR_AVAILABLE:
            return "OCR requires pytesseract and PIL. Install with: pip install pytesseract pillow"
        
        try:
            image = Image.open(file_path)
            text = pytesseract.image_to_string(image)
            return text.strip() if text.strip() else None
        except Exception as e:
            logger.error(f"OCR extraction failed: {e}")
            return None
    
    def _extract_text_file(self, file_path: str) -> Optional[str]:
        """Extract content from text files."""
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                return file.read().strip()
        except UnicodeDecodeError:
            try:
                with open(file_path, 'r', encoding='latin-1') as file:
                    return file.read().strip()
            except Exception as e:
                logger.error(f"Text file extraction failed: {e}")
                return None
        except Exception as e:
            logger.error(f"Text file extraction failed: {e}")
            return None
    
    def _summarize_content(self, content: str, file_path: str) -> str:
        """Generate a summary of the document content."""
        file_name = Path(file_path).name
        
        # Lazy import to avoid circular dependency
        try:
            from jarvis.core.ai_brain import ask as ai_ask
            _AI_AVAILABLE = True
            
            # Test if AI is actually working by checking if it returns real content
            test_response = ai_ask("summarize: test document content")
            if test_response and not any(greeting in test_response.lower() for greeting in ["hello", "what do you need", "i'm jarvis"]):
                prompt = f"Summarize this document in 2-3 sentences:\n\n{content[:2000]}"
                ai_summary = ai_ask(prompt)
                if ai_summary and not any(greeting in ai_summary.lower() for greeting in ["hello", "what do you need", "i'm jarvis"]):
                    return f"Summary of {file_name}:\n{ai_summary}"
        except ImportError:
            pass
        
        # Fallback summary (always use this for now since AI seems to return greetings)
        lines = content.split('\n')
        word_count = len(content.split())
        char_count = len(content)
        
        summary_lines = []
        for line in lines[:5]:
            if line.strip():
                summary_lines.append(line.strip())
        
        preview = "\n".join(summary_lines)
        if len(preview) > 300:
            preview = preview[:300] + "..."
        
        return (
            f"Document: {file_name}\n"
            f"Content: {word_count} words, {char_count} characters\n\n"
            f"Preview:\n{preview}"
        )
    
    def _answer_question(self, content: str, query: str, file_path: str) -> str:
        """Answer questions about the document content."""
        file_name = Path(file_path).name
        
        # For now, use fallback mode since AI returns generic greetings
        # TODO: Fix AI integration to properly process document content
        
        # Fallback: simple keyword search
        query_lower = query.lower()
        relevant_lines = []
        
        for line in content.split('\n'):
            if any(word in line.lower() for word in query_lower.split()):
                relevant_lines.append(line.strip())
                if len(relevant_lines) >= 3:
                    break
        
        if relevant_lines:
            return f"Relevant content from {file_name}:\n" + "\n".join(relevant_lines)
        else:
            return f"No specific information found about '{query}' in {file_name}"
    
    def analyze_document_structure(self, file_path: str) -> str:
        """Analyze document structure and metadata."""
        if not os.path.exists(file_path):
            return f"File not found: {file_path}"
        
        file_stats = os.stat(file_path)
        file_ext = Path(file_path).suffix.lower()
        
        info = [
            f"File: {Path(file_path).name}",
            f"Size: {file_stats.st_size:,} bytes",
            f"Type: {file_ext}",
        ]
        
        if file_ext == '.pdf' and _PDF_AVAILABLE:
            try:
                with open(file_path, 'rb') as file:
                    pdf_reader = PyPDF2.PdfReader(file)
                    info.append(f"Pages: {len(pdf_reader.pages)}")
                    
                    if pdf_reader.metadata:
                        metadata = pdf_reader.metadata
                        if metadata.get('/Title'):
                            info.append(f"Title: {metadata['/Title']}")
                        if metadata.get('/Author'):
                            info.append(f"Author: {metadata['/Author']}")
            except Exception as e:
                logger.warning(f"PDF metadata extraction failed: {e}")
        
        return "\n".join(info)
    
    def get_cached_content(self, file_path: str) -> Optional[str]:
        """Get cached document content."""
        return self._cache.get(file_path)
    
    def clear_cache(self) -> str:
        """Clear document cache."""
        count = len(self._cache)
        self._cache.clear()
        return f"Cleared {count} cached documents"
    
    def list_supported_formats(self) -> str:
        """List supported document formats."""
        formats = []
        for category, extensions in self.supported_formats.items():
            formats.append(f"{category.title()}: {', '.join(extensions)}")
        
        return "Supported document formats:\n" + "\n".join(formats)


# Global instance
_doc_intel = None

def get_document_intelligence() -> DocumentIntelligence:
    """Get the global document intelligence instance."""
    global _doc_intel
    if _doc_intel is None:
        _doc_intel = DocumentIntelligence()
    return _doc_intel


def process_document_command(command: str) -> str:
    """Process document-related commands from the main brain."""
    doc_intel = get_document_intelligence()
    
    command = command.lower().strip()
    
    if "supported formats" in command or "what formats" in command or "document formats" in command:
        return doc_intel.list_supported_formats()
    
    if "clear document cache" in command or "clear cache" in command:
        return doc_intel.clear_cache()
    
    # Extract file path from command
    import re
    path_match = re.search(r'["\']([^"\']+)["\']|(\S+\.\w+)', command)
    if not path_match:
        return (
            "Please specify a document file path. Example:\n"
            "• analyze document 'C:/path/to/file.pdf'\n"
            "• summarize document '/path/to/image.jpg'\n"
            "• ask about document 'file.txt' what is the main topic?"
        )
    
    file_path = path_match.group(1) or path_match.group(2)
    
    # Extract query if present
    query_match = re.search(r'(?:ask|question|what|how|when|where|why|who)\s+(.+)', command)
    query = query_match.group(1) if query_match else None
    
    if "analyze" in command or "structure" in command:
        return doc_intel.analyze_document_structure(file_path)
    else:
        return doc_intel.process_document(file_path, query)