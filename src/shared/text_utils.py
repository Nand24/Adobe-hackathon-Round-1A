"""
Fallback text processing when PyMuPDF is not available
"""

import re
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass


@dataclass
class TextBlock:
    """Represents a text block with formatting information"""
    text: str
    page_num: int
    bbox: Tuple[float, float, float, float]  # x0, y0, x1, y1
    font_size: float
    font_name: str
    font_flags: int
    line_height: float
    is_bold: bool = False


def extract_text_from_file(file_path: str) -> List[TextBlock]:
    """
    Extract text from a simple text file as fallback
    """
    text_blocks = []
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Split into lines and create text blocks
        lines = content.split('\n')
        for i, line in enumerate(lines):
            if line.strip():  # Skip empty lines
                # Simulate text block with default values
                text_block = TextBlock(
                    text=line.strip(),
                    page_num=1,  # All content on page 1 for text files
                    bbox=(0, i * 20, 100, (i + 1) * 20),  # Simulate line positions
                    font_size=12.0,  # Default font size
                    font_name="Arial",
                    font_flags=0,
                    line_height=14.0
                )
                text_blocks.append(text_block)
        
        print(f"Extracted {len(text_blocks)} text blocks from {file_path}")
        return text_blocks
        
    except Exception as e:
        print(f"Error reading text file {file_path}: {e}")
        return []


def detect_headings_from_text(text_blocks: List[TextBlock]) -> List[Dict]:
    """
    Ultra-precise offline heading detection that filters out fragments and bullet points.
    Uses advanced pattern matching and contextual analysis.
    """
    if not text_blocks:
        return []

    # Analyze font distribution for intelligent size-based detection
    font_sizes = [block.font_size for block in text_blocks if block.font_size]
    if not font_sizes:
        body_font_size = 12.0
        large_font_threshold = 14.0
        very_large_font_threshold = 16.0
    else:
        body_font_size = max(set(font_sizes), key=font_sizes.count)
        large_font_threshold = body_font_size + 2
        very_large_font_threshold = body_font_size + 4

    headings = []
    
    for block in text_blocks:
        text = block.text.strip()
        if not text or len(text) < 3:
            continue
            
        words = text.split()
        
        # STRICT EXCLUSION RULES - Filter out non-headings
        # Rule: Exclude fragments (incomplete sentences)
        if (text.startswith(('and ', 'or ', 'the ', 'of ', 'in ', 'to ', 'for ', 'with ')) or
            text.endswith((' and', ' or', ' the', ' of', ' in', ' to', ' for', ' with'))):
            continue
            
        # Rule: Exclude bullet points and list items
        if (text.startswith(('• ', '- ', '* ', '◦ ', '▪ ')) or
            re.match(r'^\w\)\s', text) or  # a) b) c) format
            re.match(r'^\d+\)\s', text)):  # 1) 2) 3) format
            continue
            
        # Rule: Exclude sentences (contain common sentence indicators)
        sentence_indicators = [
            ' is ', ' are ', ' was ', ' were ', ' will ', ' would ', ' should ', ' could ',
            ' have ', ' has ', ' had ', ' must ', ' may ', ' can ', ' shall ', ' do ', ' does ',
            ' the ', ' this ', ' that ', ' these ', ' those ', ' a ', ' an '
        ]
        if any(indicator in text.lower() for indicator in sentence_indicators):
            continue
            
        # Rule: Exclude lines that end with incomplete thoughts
        if (text.endswith((' a', ' an', ' the', ' and', ' or', ' but', ' with', ' for', ' of', ' in')) or
            len(words) > 12):  # Too long for a heading
            continue
            
        # POSITIVE HEADING DETECTION RULES
        level = None
        confidence = 0
        
        # RULE 1: Numbered section headings (highest confidence)
        if re.match(r'^\d+\.\s+[A-Z]', text):
            level = 1
            confidence = 0.95
        elif re.match(r'^\d+\.\d+\s+[A-Z]', text):
            level = 2
            confidence = 0.95
        elif re.match(r'^\d+\.\d+\.\d+\s+[A-Z]', text):
            level = 3
            confidence = 0.95
            
        # RULE 2: All caps (likely main headings)
        elif (text.isupper() and 
              2 <= len(words) <= 6 and 
              not any(char in text for char in '.,;:')):
            level = 1
            confidence = 0.9
            
        # RULE 3: Large font size (structural headings)
        elif block.font_size >= very_large_font_threshold:
            if 2 <= len(words) <= 8:
                level = 1
                confidence = 0.85
        elif block.font_size >= large_font_threshold:
            if 2 <= len(words) <= 8:
                level = 2
                confidence = 0.8
                
        # RULE 4: Bold text with title characteristics
        elif (block.is_bold and 
              2 <= len(words) <= 6 and
              (text.istitle() or text.endswith(':')) and
              not any(char in text for char in '.,;')):
            level = 2
            confidence = 0.75
            
        # RULE 5: Title case with colon (section labels)
        elif (text.endswith(':') and 
              text.istitle() and 
              2 <= len(words) <= 4):
            level = 2
            confidence = 0.8
            
        # RULE 6: Short title case phrases (subsection headings)
        elif (text.istitle() and 
              2 <= len(words) <= 5 and
              not text.endswith(('.', ',', ';')) and
              all(word[0].isupper() for word in words if word.isalpha())):
            # Additional validation for H3
            if not any(word.lower() in ['the', 'and', 'for', 'with', 'from'] for word in words):
                level = 3
                confidence = 0.7
        
        # Only add if we found a valid heading with sufficient confidence
        if level and confidence >= 0.7:
            headings.append({
                'text': text,
                'level': level,
                'page_num': block.page_num,
                'bbox': block.bbox,
                'font_size': block.font_size,
                'is_bold': block.is_bold,
                'confidence': confidence
            })
    
    return headings

def get_text_statistics(text_blocks: List[TextBlock]) -> Dict:
    """
    Get basic statistics about the text
    """
    if not text_blocks:
        return {
            'total_blocks': 0,
            'avg_font_size': 12.0,
            'font_sizes': [12.0]
        }
    
    font_sizes = [block.font_size for block in text_blocks]
    
    return {
        'total_blocks': len(text_blocks),
        'avg_font_size': sum(font_sizes) / len(font_sizes),
        'font_sizes': font_sizes
    }


def extract_document_structure(file_path: str) -> Dict:
    """
    Extract document structure from a text file
    """
    print(f"Processing text file: {file_path}")
    
    # Extract text blocks
    text_blocks = extract_text_from_file(file_path)
    
    if not text_blocks:
        return {
            'text_blocks': [],
            'headings': [],
            'statistics': get_text_statistics([])
        }
    
    # Detect headings
    headings = detect_headings_from_text(text_blocks)
    
    # Get statistics
    statistics = get_text_statistics(text_blocks)
    
    return {
        'text_blocks': text_blocks,
        'headings': headings,
        'statistics': statistics
    }
