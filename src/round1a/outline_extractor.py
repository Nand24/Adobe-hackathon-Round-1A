"""
Round 1A: Document Outline Extractor
Extracts structured outlines (Title, H1, H2, H3) from PDF documents
"""

import json
import statistics
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
import re

from shared.pdf_utils import extract_document_content, TextBlock
from shared.text_processor import TextProcessor
from shared.config import Config
from shared.text_utils import detect_headings_from_text


class OutlineExtractor:
    """
    Main class for extracting document outlines. This version is optimized for
    offline performance and high accuracy using rich text features.
    """
    
    def __init__(self):
        # No external dependencies needed for this offline-first approach
        pass
    
    def extract_outline(self, file_path: str) -> Dict:
        """
        Extract a structured outline from a PDF file by analyzing its
        layout, font styles, and text patterns.
        """
        try:
            # Extract rich text blocks from the PDF
            doc_content = extract_document_content(file_path)
            
            if not doc_content or not doc_content['text_blocks']:
                return {"title": "", "outline": []}
            
            # Detect headings using our advanced offline logic
            headings = detect_headings_from_text(doc_content['text_blocks'])
            
            # Extract a title for the document
            title = self._extract_title(headings, doc_content['text_blocks'])
            
            # Build the final hierarchical outline
            outline = self._build_hierarchical_outline(headings)
            
            return {
                "title": title,
                "outline": outline
            }
            
        except Exception as e:
            print(f"Error extracting outline from {file_path}: {e}")
            return {"title": "", "outline": []}

    def _extract_title(self, headings: List[Dict], text_blocks: List[TextBlock]) -> str:
        """
        Extract the document title from the highest-level heading or the
        first prominent text block.
        """
        if headings:
            # The title is likely the first H1 heading
            for heading in headings:
                if heading['level'] == 1:
                    return heading['text']
        
        # Fallback: find the most prominent text on the first page
        first_page_blocks = [b for b in text_blocks if b.page_num == 1]
        if not first_page_blocks:
            return ""
            
        # Sort by font size (desc) and then position (asc)
        sorted_blocks = sorted(first_page_blocks, key=lambda b: (-b.font_size, b.bbox[1]))
        return sorted_blocks[0].text if sorted_blocks else ""

    def _build_hierarchical_outline(self, headings: List[Dict]) -> List[Dict]:
        """
        Build a flat outline structure in Adobe's required format:
        {"level": "H1", "text": "...", "page": 1}
        """
        if not headings:
            return []

        # Sort headings by page and position
        sorted_headings = sorted(headings, key=lambda h: (h['page_num'], h['bbox'][1]))
        
        outline = []
        
        for heading in sorted_headings:
            level = heading['level']
            
            # Convert level to Adobe's string format (H1, H2, H3)
            level_mapping = {1: "H1", 2: "H2", 3: "H3"}
            level_str = level_mapping.get(level, f"H{min(level, 3)}")
            
            # Adobe's exact required format - flat structure
            outline_item = {
                "level": level_str,
                "text": heading['text'],
                "page": heading['page_num']
            }
            outline.append(outline_item)
        
        return outline
