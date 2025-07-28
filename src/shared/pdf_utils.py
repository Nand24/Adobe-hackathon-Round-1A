"""
Common PDF processing utilities
"""

# Try to import PyMuPDF, fallback to text processing
try:
    import fitz  # PyMuPDF
    PYMUPDF_AVAILABLE = True
except ImportError:
    print("Warning: PyMuPDF not available. Using text file fallback.")
    PYMUPDF_AVAILABLE = False

import re
import statistics
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass

# Import our text fallback
from shared.text_utils import extract_document_structure as extract_text_structure, TextBlock


def extract_document_content(file_path: str) -> Dict:
    """
    Extract content from PDF or text file
    """
    file_path_lower = file_path.lower()
    
    if file_path_lower.endswith('.txt'):
        # Handle text files
        return extract_text_structure(file_path)
    elif file_path_lower.endswith('.pdf') and PYMUPDF_AVAILABLE:
        # Handle PDF files with PyMuPDF
        return extract_pdf_content(file_path)
    elif file_path_lower.endswith('.pdf') and not PYMUPDF_AVAILABLE:
        # PDF requested but PyMuPDF not available
        print(f"Warning: PyMuPDF not available for PDF {file_path}. Please install PyMuPDF or provide a text file.")
        return {'text_blocks': [], 'headings': [], 'statistics': {'total_blocks': 0, 'avg_font_size': 12.0, 'font_sizes': [12.0]}}
    else:
        print(f"Unsupported file type: {file_path}")
        return {'text_blocks': [], 'headings': [], 'statistics': {'total_blocks': 0, 'avg_font_size': 12.0, 'font_sizes': [12.0]}}


def extract_pdf_content(file_path: str) -> Dict:
    """
    Extract rich content from a PDF file using PyMuPDF, including text,
    font size, font weight, and layout information.
    """
    if not PYMUPDF_AVAILABLE:
        raise ImportError("PyMuPDF not available")
    
    doc = fitz.open(file_path)
    text_blocks = []
    
    for page_num in range(len(doc)):
        page = doc.load_page(page_num)
        
        # Extract blocks with detailed information
        blocks = page.get_text("dict", flags=fitz.TEXTFLAGS_DICT & ~fitz.TEXT_PRESERVE_LIGATURES & ~fitz.TEXT_PRESERVE_IMAGES)["blocks"]
        
        for block in blocks:
            if block['type'] == 0:  # It's a text block
                for line in block['lines']:
                    for span in line['spans']:
                        text = clean_text(span['text'])
                        if text:
                            # Enhanced bold detection
                            font_name = span['font'].lower()
                            is_bold = ("bold" in font_name or 
                                     "black" in font_name or 
                                     span['flags'] & 2**4 or  # Bold flag
                                     span['flags'] & 16)      # Bold flag alternative
                            
                            text_block = TextBlock(
                                text=text,
                                page_num=page_num + 1,
                                bbox=span['bbox'],
                                font_size=round(span['size']),
                                font_name=span['font'],
                                font_flags=span['flags'],
                                line_height=line['bbox'][3] - line['bbox'][1],
                                is_bold=is_bold
                            )
                            text_blocks.append(text_block)
                            
    doc.close()
    
    # This part can be simplified as heading detection will be more sophisticated
    headings = [] 
    statistics = get_text_statistics(text_blocks)
    
    return {
        'text_blocks': text_blocks,
        'headings': headings,
        'statistics': statistics
    }


def clean_text(text: str) -> str:
    """
    Clean and normalize a text string.
    """
    if not text:
        return ""
    # Replace multiple spaces with a single space
    text = re.sub(r'\s+', ' ', text)
    # Remove non-printable characters
    text = ''.join(char for char in text if char.isprintable())
    return text.strip()


def get_text_statistics(text_blocks: List[TextBlock]) -> Dict:
    """
    Calculate statistics about the text blocks.
    """
    if not text_blocks:
        return {
            'total_blocks': 0,
            'avg_font_size': 12.0,
            'font_sizes': [12.0]
        }
    
    font_sizes = [block.font_size for block in text_blocks if block.font_size]
    if not font_sizes:
        return {
            'total_blocks': len(text_blocks),
            'avg_font_size': 12.0,
            'font_sizes': [12.0]
        }

    return {
        'total_blocks': len(text_blocks),
        'avg_font_size': statistics.mean(font_sizes),
        'font_sizes': font_sizes
    }


def is_likely_heading(text: str) -> bool:
    """
    Check if a given text string is likely to be a heading.
    """
    if not text or len(text.strip()) < 3:
        return False
    
    text = text.strip()
    
    # Rule 1: Ends with punctuation (less likely to be a heading)
    if text.endswith(('.', ',', ';', ':')):
        return False
        
    # Rule 2: Starts with a lowercase letter (less likely)
    if text[0].islower():
        return False
        
    # Rule 3: Short and title-cased
    words = text.split()
    if len(words) < 8 and text.istitle():
        return True
        
    # Rule 4: All caps
    if text.isupper() and len(words) < 8:
        return True
        
    # Rule 5: Starts with a number (e.g., "1. Introduction")
    if text[0].isdigit() and '.' in text:
        return True
        
    return False


class PDFUtils:
    """Utility functions for PDF processing"""
    
    @staticmethod
    def extract_text_blocks(pdf_path: str) -> List[TextBlock]:
        """Extract text blocks with formatting information from PDF"""
        # Use our fallback system
        doc_content = extract_document_content(pdf_path)
        return doc_content.get('text_blocks', [])
    
    @staticmethod
    def clean_text(text: str) -> str:
        """Clean and normalize text"""
        return clean_text(text)
    
    @staticmethod
    # def is_likely_heading(text: str) -> bool:
    #     """Check if text looks like a heading"""
    #     return is_likely_heading(text)
    def is_likely_heading(text: str) -> bool:
        """Check if text looks like a heading with stricter H3 rules"""
        ## added stricter H3 rules
        if not text or len(text.strip()) < 3:
            return False

        text = text.strip()

        # Numbered sections
        if re.match(r'^\d+(\.\d+)*\.?\s+\w+', text):
            return True

        # All caps
        if text.isupper() and len(text.split()) <= 6:
            return True

        # Short title-case phrase (improved H3)
        words = text.split()
        if (
            2 <= len(words) <= 6 and
            not text.endswith(('.', ',', ';', ':')) and
            all(w[0].isupper() for w in words if w and w[0].isalpha()) and
            not any(w.lower() in {'the', 'and', 'for', 'with', 'from', 'that', 'this', 'will', 'must', 'should', 'could'} for w in words)
        ):
            return True

        return False
    @staticmethod
    def get_document_stats(text_blocks: List[TextBlock]) -> Dict:
        """Get document statistics"""
        return get_text_statistics(text_blocks)