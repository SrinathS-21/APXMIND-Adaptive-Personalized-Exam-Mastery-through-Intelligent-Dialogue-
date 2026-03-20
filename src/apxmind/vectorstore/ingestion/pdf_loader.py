"""
PDF Loader
==========

Loads PDF files and extracts text with metadata.

Handles:
- Text extraction from PDFs
- Multi-column layouts
- Metadata parsing (title, author, pages)
- Image and diagram detection
- Table extraction

Author: APXMIND Team
Date: November 2024
"""

import re
from pathlib import Path
from typing import List, Dict, Optional, Any
from datetime import datetime
import PyPDF2
from PyPDF2 import PdfReader

from .base_loader import BaseLoader, Document, LoadResult
from ..constants import Subject, ContentType, Difficulty


class PDFLoader(BaseLoader):
    """
    Loads PDF files and extracts text with metadata.
    
    Features:
    - Text extraction with page tracking
    - Multi-column layout handling
    - Metadata extraction from PDF info
    - Chapter/section detection
    - Image/diagram detection
    """
    
    # Patterns for detecting structure
    CHAPTER_PATTERN = re.compile(r'^chapter\s+(\d+)[:\s]*(.*?)$', re.IGNORECASE)
    SECTION_PATTERN = re.compile(r'^\d+\.\d+\s+(.*?)$')
    HEADING_PATTERN = re.compile(r'^[A-Z][A-Z\s]{10,}$')  # ALL CAPS headings
    
    # Patterns for content detection
    FORMULA_PATTERN = re.compile(r'[A-Z][a-z]?\d+|[=+\-*/^]|\d+\.\d+')
    DIAGRAM_KEYWORDS = {'figure', 'fig', 'diagram', 'illustration', 'image', 'table'}
    
    def __init__(self, 
                 extract_images: bool = False,
                 extract_tables: bool = False,
                 min_text_length: int = 10):
        """
        Initialize the PDF loader.
        
        Args:
            extract_images: Whether to detect and mark images
            extract_tables: Whether to detect and mark tables
            min_text_length: Minimum text length to consider valid
        """
        self.extract_images = extract_images
        self.extract_tables = extract_tables
        self.min_text_length = min_text_length
    
    def load(self, source: str) -> LoadResult:
        """
        Load a PDF file and extract text with metadata.
        
        Args:
            source: Path to the PDF file
            
        Returns:
            LoadResult with extracted document (combined pages)
        """
        source_path = Path(source)
        
        if not source_path.exists():
            return LoadResult(
                success=False,
                document=None,
                error=f"PDF file not found: {source_path}"
            )
        
        try:
            # Open PDF
            with open(source_path, 'rb') as file:
                pdf_reader = PdfReader(file)
                
                # Extract PDF metadata
                pdf_metadata = self._extract_pdf_metadata(pdf_reader, source_path)
                
                # Extract text from all pages
                all_text = []
                has_diagrams = False
                
                for page_num in range(len(pdf_reader.pages)):
                    page_text = self._extract_page_text(
                        pdf_reader.pages[page_num],
                        page_num + 1
                    )
                    
                    if page_text and len(page_text.strip()) >= self.min_text_length:
                        all_text.append(page_text)
                        if self._detect_diagrams(page_text):
                            has_diagrams = True
                
                # Combine all pages
                combined_text = '\n\n'.join(all_text)
                
                if len(combined_text.strip()) < self.min_text_length:
                    return LoadResult(
                        success=False,
                        document=None,
                        error="No valid text extracted from PDF"
                    )
                
                # Detect structure from first page
                structure = self._detect_structure(all_text[0] if all_text else "")
                
                # Create combined document
                doc_metadata = {
                    'source_file': source_path.name,
                    'source_path': str(source_path),
                    'total_pages': len(pdf_reader.pages),
                    'has_diagram': has_diagrams,
                    'extracted_at': datetime.now().isoformat(),
                    **pdf_metadata,
                    **structure
                }
                
                document = Document(
                    content=combined_text,
                    metadata=doc_metadata,
                    source_path=source_path,
                    page_count=len(pdf_reader.pages)
                )
                
                return LoadResult(
                    success=True,
                    document=document,
                    metrics={
                        'source': str(source_path),
                        'total_pages': len(pdf_reader.pages),
                        'text_length': len(combined_text),
                        **pdf_metadata
                    }
                )
        
        except Exception as e:
            return LoadResult(
                success=False,
                document=None,
                error=f"Error loading PDF: {str(e)}"
            )
    
    def _extract_pdf_metadata(self, pdf_reader: PdfReader, source_path: Path) -> Dict[str, Any]:
        """
        Extract metadata from PDF.
        
        Args:
            pdf_reader: PyPDF2 reader object
            source_path: Path to the PDF file
            
        Returns:
            Dictionary of metadata
        """
        metadata = {}
        
        # Get PDF info
        if pdf_reader.metadata:
            if pdf_reader.metadata.title:
                metadata['title'] = pdf_reader.metadata.title
            if pdf_reader.metadata.author:
                metadata['author'] = pdf_reader.metadata.author
            if pdf_reader.metadata.subject:
                metadata['pdf_subject'] = pdf_reader.metadata.subject
            if pdf_reader.metadata.creator:
                metadata['creator'] = pdf_reader.metadata.creator
        
        # Infer metadata from filename
        filename = source_path.stem
        
        # Detect subject from path or filename
        subject = self._detect_subject(str(source_path))
        if subject:
            metadata['subject'] = subject
        
        # Detect class level
        class_level = self._detect_class_level(filename)
        if class_level:
            metadata['class_level'] = class_level
        
        # Detect part number (for multi-part books)
        part = self._detect_part_number(filename)
        if part:
            metadata['part'] = part
        
        return metadata
    
    def _detect_subject(self, path: str) -> Optional[str]:
        """Detect subject from path."""
        path_lower = path.lower()
        
        if 'biology' in path_lower or 'bio' in path_lower:
            return 'biology'
        elif 'chemistry' in path_lower or 'chem' in path_lower:
            return 'chemistry'
        elif 'physics' in path_lower or 'phy' in path_lower:
            return 'physics'
        
        return None
    
    def _detect_class_level(self, filename: str) -> Optional[int]:
        """Detect class level from filename."""
        # Pattern: 11Bio1, 12ChemPart1, etc.
        match = re.search(r'(\d{2})', filename)
        if match:
            level = int(match.group(1))
            if level in [11, 12]:
                return level
        
        return None
    
    def _detect_part_number(self, filename: str) -> Optional[int]:
        """Detect part number from filename."""
        # Pattern: Part1, Part2, 11ChemPart1, etc.
        match = re.search(r'[Pp]art\s*(\d+)', filename)
        if match:
            return int(match.group(1))
        
        # Pattern: 11Bio1 (the trailing 1)
        match = re.search(r'\d{2}[A-Za-z]+(\d+)', filename)
        if match:
            return int(match.group(1))
        
        return None
    
    def _extract_page_text(self, page, page_num: int) -> str:
        """
        Extract and clean text from a single PDF page.
        
        Args:
            page: PyPDF2 page object
            page_num: Page number (1-indexed)
            
        Returns:
            Cleaned text from the page
        """
        try:
            # Extract text
            text = page.extract_text()
            
            if not text or len(text.strip()) < self.min_text_length:
                return ""
            
            # Clean up text
            text = self._clean_text(text)
            
            return text
        
        except Exception:
            # Return empty string if page extraction fails
            return ""
    
    def _clean_text(self, text: str) -> str:
        """
        Clean extracted text.
        
        Args:
            text: Raw extracted text
            
        Returns:
            Cleaned text
        """
        # Remove excessive whitespace
        text = re.sub(r'\s+', ' ', text)
        
        # Remove page numbers at start/end
        text = re.sub(r'^\d+\s*', '', text)
        text = re.sub(r'\s*\d+$', '', text)
        
        # Fix common OCR issues
        text = text.replace('­', '')  # Remove soft hyphens
        text = text.replace('\x00', '')  # Remove null characters
        
        # Normalize quotes
        text = text.replace('"', '"').replace('"', '"')
        text = text.replace(''', "'").replace(''', "'")
        
        # Remove multiple spaces
        text = re.sub(r' {2,}', ' ', text)
        
        return text.strip()
    
    def _detect_structure(self, text: str) -> Dict[str, Optional[str]]:
        """
        Detect chapter/section structure from text.
        
        Args:
            text: Page text
            
        Returns:
            Dictionary with chapter/section info
        """
        structure = {
            'chapter': None,
            'section': None,
            'topic': None
        }
        
        lines = text.split('\n')
        
        for line in lines[:10]:  # Check first 10 lines
            line = line.strip()
            
            # Check for chapter
            chapter_match = self.CHAPTER_PATTERN.match(line)
            if chapter_match:
                chapter_num = chapter_match.group(1)
                chapter_title = chapter_match.group(2).strip()
                structure['chapter'] = f"Chapter {chapter_num}"
                if chapter_title:
                    structure['topic'] = chapter_title
                continue
            
            # Check for section
            section_match = self.SECTION_PATTERN.match(line)
            if section_match:
                structure['section'] = section_match.group(1).strip()
                if not structure['topic']:
                    structure['topic'] = section_match.group(1).strip()
                continue
            
            # Check for heading (all caps)
            if self.HEADING_PATTERN.match(line):
                if not structure['topic']:
                    structure['topic'] = line.title()  # Convert to title case
        
        return structure
    
    def _detect_diagrams(self, text: str) -> bool:
        """
        Detect if page contains diagrams/images.
        
        Args:
            text: Page text
            
        Returns:
            True if diagrams detected
        """
        text_lower = text.lower()
        
        # Check for diagram keywords
        for keyword in self.DIAGRAM_KEYWORDS:
            if keyword in text_lower:
                return True
        
        return False
    
    def load_batch(self, sources: List[str]) -> Dict[str, LoadResult]:
        """
        Load multiple PDF files.
        
        Args:
            sources: List of PDF file paths
            
        Returns:
            Dictionary mapping source paths to LoadResults
        """
        results = {}
        
        for source in sources:
            result = self.load(source)
            results[source] = result
        
        return results
    
    def get_supported_extensions(self) -> List[str]:
        """Get list of supported file extensions."""
        return ['.pdf']
    
    def validate_source(self, source: str) -> bool:
        """
        Validate that source is a PDF file.
        
        Args:
            source: Path to check
            
        Returns:
            True if valid PDF source
        """
        path = Path(source)
        return path.exists() and path.suffix.lower() == '.pdf'
    
    def validate_file(self, file_path: Path) -> bool:
        """
        Validate that file is a valid PDF.
        
        Args:
            file_path: Path to validate
            
        Returns:
            True if valid PDF file
        """
        return file_path.exists() and file_path.suffix.lower() == '.pdf'


class NCERTBookLoader(PDFLoader):
    """
    Specialized loader for NCERT textbooks.
    
    Understands NCERT book structure and metadata conventions.
    """
    
    def __init__(self):
        """Initialize NCERT book loader."""
        super().__init__(
            extract_images=True,
            extract_tables=True,
            min_text_length=20
        )
    
    def _extract_pdf_metadata(self, pdf_reader: PdfReader, source_path: Path) -> Dict[str, Any]:
        """
        Extract NCERT-specific metadata.
        
        Args:
            pdf_reader: PyPDF2 reader object
            source_path: Path to the PDF file
            
        Returns:
            Dictionary of metadata
        """
        # Get base metadata
        metadata = super()._extract_pdf_metadata(pdf_reader, source_path)
        
        # Add NCERT-specific metadata
        metadata['source_type'] = 'ncert_textbook'
        metadata['publisher'] = 'NCERT'
        metadata['language'] = 'english'
        
        # Determine content type (usually explanation for textbooks)
        metadata['content_type'] = 'explanation'
        
        # Set default difficulty based on class level
        if metadata.get('class_level') == 11:
            metadata['difficulty'] = 'intermediate'
        elif metadata.get('class_level') == 12:
            metadata['difficulty'] = 'advanced'
        else:
            metadata['difficulty'] = 'intermediate'
        
        return metadata


class QuestionPaperLoader(PDFLoader):
    """
    Specialized loader for question papers.
    
    Detects questions, answers, and exam metadata.
    """
    
    # Patterns for question detection
    QUESTION_PATTERN = re.compile(r'^(?:Q\.?\s*)?(\d+)[.:\)]\s*(.*?)$', re.MULTILINE)
    MCQ_PATTERN = re.compile(r'^[A-D][.:\)]\s+(.*?)$')
    
    def __init__(self):
        """Initialize question paper loader."""
        super().__init__(
            extract_images=False,
            extract_tables=False,
            min_text_length=10
        )
    
    def _extract_pdf_metadata(self, pdf_reader: PdfReader, source_path: Path) -> Dict[str, Any]:
        """
        Extract question paper metadata.
        
        Args:
            pdf_reader: PyPDF2 reader object
            source_path: Path to the PDF file
            
        Returns:
            Dictionary of metadata
        """
        metadata = super()._extract_pdf_metadata(pdf_reader, source_path)
        
        # Add question paper metadata
        metadata['source_type'] = 'question_paper'
        metadata['content_type'] = 'question'
        metadata['difficulty'] = 'neet_level'
        
        # Detect year from filename
        year_match = re.search(r'(20\d{2})', source_path.name)
        if year_match:
            metadata['exam_year'] = int(year_match.group(1))
        
        return metadata
    
    def _detect_structure(self, text: str) -> Dict[str, Optional[str]]:
        """
        Detect question paper structure.
        
        Args:
            text: Page text
            
        Returns:
            Dictionary with structure info
        """
        structure = super()._detect_structure(text)
        
        # Detect questions
        questions = self.QUESTION_PATTERN.findall(text)
        if questions:
            structure['has_questions'] = True
            structure['question_count'] = len(questions)
        
        # Detect MCQs
        mcqs = self.MCQ_PATTERN.findall(text)
        if mcqs:
            structure['has_mcq'] = True
        
        return structure
