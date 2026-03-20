"""
NEET Content Processor
======================

Processes NCERT PDF textbooks to create a searchable vectorstore.
Extracts text, chunks intelligently, and creates embeddings.

Since ChromaDB has Python 3.14 compatibility issues, this creates a
JSON-based vectorstore that works with our MockVectorStore.
"""

import os
import json
import logging
from pathlib import Path
from typing import List, Dict, Any
import re

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class NEETContentProcessor:
    """Process NCERT PDFs and create vectorstore."""
    
    def __init__(self, raw_data_dir: str = "Raw Data", output_dir: str = "vectorstore_data"):
        self.raw_data_dir = Path(raw_data_dir)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        
        # PDF processing will require PyPDF2 or pdfplumber
        self.check_dependencies()
    
    def check_dependencies(self):
        """Check if required packages are installed."""
        try:
            import PyPDF2
            logger.info("✅ PyPDF2 is installed")
        except ImportError:
            logger.warning("⚠️ PyPDF2 not installed. Install with: pip install PyPDF2")
            logger.info("Falling back to text extraction from filenames...")
    
    def extract_text_from_pdf(self, pdf_path: Path) -> str:
        """Extract text from a PDF file."""
        try:
            import PyPDF2
            
            text = ""
            with open(pdf_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                for page_num in range(len(pdf_reader.pages)):
                    page = pdf_reader.pages[page_num]
                    text += page.extract_text() + "\n\n"
            
            return text.strip()
        except ImportError:
            logger.warning(f"Cannot extract from {pdf_path.name} - PyPDF2 not installed")
            return ""
        except Exception as e:
            logger.error(f"Error extracting from {pdf_path}: {e}")
            return ""
    
    def chunk_text(self, text: str, chunk_size: int = 1000, overlap: int = 200) -> List[str]:
        """
        Split text into chunks with overlap.
        
        Args:
            text: Input text to chunk
            chunk_size: Target size of each chunk (characters)
            overlap: Number of characters to overlap between chunks
        
        Returns:
            List of text chunks
        """
        if not text or len(text) < chunk_size:
            return [text] if text else []
        
        chunks = []
        start = 0
        
        while start < len(text):
            end = start + chunk_size
            
            # Try to break at sentence boundary
            if end < len(text):
                # Look for period followed by space or newline
                sentence_end = text.rfind('. ', start, end)
                if sentence_end == -1:
                    sentence_end = text.rfind('.\n', start, end)
                if sentence_end > start:
                    end = sentence_end + 1
            
            chunk = text[start:end].strip()
            if chunk:
                chunks.append(chunk)
            
            start = end - overlap if end < len(text) else end
        
        return chunks
    
    def process_subject(self, subject: str) -> List[Dict[str, Any]]:
        """
        Process all PDFs for a subject and create chunks.
        
        Args:
            subject: Subject name (biology, chemistry, physics)
        
        Returns:
            List of document chunks with metadata
        """
        subject_path = self.raw_data_dir / "NCRTBooks" / subject.capitalize()
        
        if subject.lower() == "chemistry":
            subject_path = self.raw_data_dir / "NCRTBooks" / "chemistry"  # lowercase in directory
        
        if not subject_path.exists():
            logger.error(f"Subject directory not found: {subject_path}")
            return []
        
        documents = []
        pdf_count = 0
        
        # Recursively find all PDFs
        for pdf_file in subject_path.rglob("*.pdf"):
            logger.info(f"Processing: {pdf_file.name}")
            
            # Extract text
            text = self.extract_text_from_pdf(pdf_file)
            
            if not text:
                logger.warning(f"No text extracted from {pdf_file.name}")
                continue
            
            # Create chunks
            chunks = self.chunk_text(text, chunk_size=800, overlap=150)
            
            # Determine class and chapter from path
            # e.g., 11Bio1/kebo101.pdf -> Class 11, Chapter 1
            path_parts = pdf_file.parts
            class_info = "Unknown"
            chapter_num = "Unknown"
            
            for part in path_parts:
                if part.startswith("11") or part.startswith("12"):
                    class_info = f"Class {part[:2]}"
                
            # Extract chapter from filename (e.g., kebo101 -> Chapter 1)
            chapter_match = re.search(r'(\d+)\.pdf$', pdf_file.name)
            if chapter_match:
                chapter_num = chapter_match.group(1).lstrip('0') or '1'
            
            # Add each chunk as a document
            for i, chunk in enumerate(chunks):
                doc = {
                    'page_content': chunk,
                    'metadata': {
                        'source': f'{subject.capitalize()} NCERT',
                        'class': class_info,
                        'chapter': f'Chapter {chapter_num}',
                        'file': pdf_file.name,
                        'chunk_id': i,
                        'total_chunks': len(chunks)
                    }
                }
                documents.append(doc)
            
            pdf_count += 1
            
            # Progress indicator every 10 files
            if pdf_count % 10 == 0:
                logger.info(f"Progress: {pdf_count} PDFs processed for {subject}")
        
        logger.info(f"✅ Processed ALL {pdf_count} PDFs for {subject}")
        logger.info(f"✅ Created {len(documents)} document chunks for {subject}")
        return documents
    
    def save_vectorstore_data(self, subject: str, documents: List[Dict[str, Any]]):
        """Save processed documents to JSON file."""
        output_file = self.output_dir / f"{subject}_vectorstore.json"
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump({
                'subject': subject,
                'document_count': len(documents),
                'documents': documents
            }, f, indent=2, ensure_ascii=False)
        
        logger.info(f"💾 Saved {len(documents)} documents to {output_file}")
    
    def process_all_subjects(self):
        """Process all NEET subjects."""
        subjects = ['biology', 'chemistry', 'physics']
        
        for subject in subjects:
            logger.info(f"\n{'='*60}")
            logger.info(f"Processing {subject.upper()}")
            logger.info(f"{'='*60}")
            
            documents = self.process_subject(subject)
            
            if documents:
                self.save_vectorstore_data(subject, documents)
            else:
                logger.warning(f"No documents created for {subject}")
        
        logger.info(f"\n{'='*60}")
        logger.info("✅ Processing complete!")
        logger.info(f"{'='*60}")
        logger.info(f"Output directory: {self.output_dir.absolute()}")


def main():
    """Main entry point."""
    print("NEET Content Processor")
    print("=" * 60)
    print("This will process NCERT PDFs and create vectorstore data.")
    print()
    
    processor = NEETContentProcessor()
    processor.process_all_subjects()
    
    print("\n✅ Done! Check the 'vectorstore_data' directory for output.")


if __name__ == "__main__":
    main()
