"""
Fast PDF Loader using PyMuPDF
==============================

Much faster alternative to PyPDF2 for processing large batches of PDFs.
PyMuPDF (fitz) is 10-20x faster than PyPDF2.
"""

import fitz  # PyMuPDF
from pathlib import Path
from typing import List, Dict, Any
import logging

logger = logging.getLogger(__name__)


class FastPDFLoader:
    """Fast PDF text extraction using PyMuPDF."""
    
    def __init__(self, min_text_length: int = 50):
        """
        Initialize fast PDF loader.
        
        Args:
            min_text_length: Minimum text length to consider valid
        """
        self.min_text_length = min_text_length
    
    def load(self, file_path: str) -> Dict[str, Any]:
        """
        Load and extract text from PDF file.
        
        Args:
            file_path: Path to PDF file
            
        Returns:
            Dictionary with extracted text and metadata
        """
        file_path = Path(file_path)
        
        if not file_path.exists():
            raise FileNotFoundError(f"PDF file not found: {file_path}")
        
        try:
            # Open PDF
            doc = fitz.open(str(file_path))
            
            # Extract text from all pages
            full_text = ""
            page_texts = []
            
            for page_num in range(len(doc)):
                page = doc[page_num]
                page_text = page.get_text()
                
                if page_text and len(page_text.strip()) >= self.min_text_length:
                    full_text += page_text + "\n\n"
                    page_texts.append({
                        'page_number': page_num + 1,
                        'text': page_text,
                        'char_count': len(page_text)
                    })
            
            doc.close()
            
            # Extract metadata
            metadata = {
                'source': str(file_path),
                'filename': file_path.name,
                'total_pages': len(doc),
                'extracted_pages': len(page_texts),
                'total_chars': len(full_text)
            }
            
            result = {
                'text': full_text.strip(),
                'metadata': metadata,
                'pages': page_texts
            }
            
            logger.info(f"Extracted {len(full_text)} chars from {file_path.name} ({len(page_texts)} pages)")
            
            return result
            
        except Exception as e:
            logger.error(f"Error loading {file_path}: {e}")
            raise


def batch_load_pdfs(pdf_files: List[Path], min_text_length: int = 50) -> List[Dict[str, Any]]:
    """
    Load multiple PDFs in batch.
    
    Args:
        pdf_files: List of PDF file paths
        min_text_length: Minimum text length per page
        
    Returns:
        List of extracted documents
    """
    loader = FastPDFLoader(min_text_length=min_text_length)
    documents = []
    
    for i, pdf_file in enumerate(pdf_files, 1):
        try:
            logger.info(f"[{i}/{len(pdf_files)}] Loading {pdf_file.name}...")
            result = loader.load(str(pdf_file))
            documents.append(result)
        except Exception as e:
            logger.error(f"Failed to load {pdf_file.name}: {e}")
            continue
    
    logger.info(f"Successfully loaded {len(documents)}/{len(pdf_files)} PDFs")
    return documents
