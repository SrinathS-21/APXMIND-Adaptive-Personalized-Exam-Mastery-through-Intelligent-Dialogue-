"""
Complete PDF Processing Pipeline
================================

Processes ALL PDFs from:
- Raw Data/NCRTBooks/ (168 PDFs)
- Raw Data/MentorGuide/ (2 PDFs)
- Raw Data/QuestionBank/ (47 PDFs)

Total: 217 PDFs

Features:
- Incremental processing with checkpoints every 5 PDFs
- Error handling - continues on failure
- Progress tracking
- Multiple PDF libraries (fallback support)
- Chunk quality validation
"""

import json
import os
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any
import hashlib
import re
from collections import defaultdict

# Try PyMuPDF first (faster), fallback to PyPDF2
try:
    import fitz  # PyMuPDF
    USE_PYMUPDF = True
    print("Using PyMuPDF (fitz) for PDF extraction")
except ImportError:
    USE_PYMUPDF = False
    print("PyMuPDF not available, using PyPDF2")
    from PyPDF2 import PdfReader


class PDFProcessor:
    """Processes individual PDFs with multiple library support."""
    
    def __init__(self):
        self.use_pymupdf = USE_PYMUPDF
    
    def extract_text_pymupdf(self, pdf_path: str) -> str:
        """Extract text using PyMuPDF (faster)."""
        try:
            doc = fitz.open(pdf_path)
            text = ""
            for page_num, page in enumerate(doc):
                try:
                    page_text = page.get_text()
                    text += page_text + "\n"
                except Exception as e:
                    print(f"  Warning: Error on page {page_num}: {e}")
                    continue
            doc.close()
            return text.strip()
        except Exception as e:
            print(f"  PyMuPDF extraction failed: {e}")
            return ""
    
    def extract_text_pypdf2(self, pdf_path: str) -> str:
        """Extract text using PyPDF2 (fallback)."""
        try:
            reader = PdfReader(pdf_path)
            text = ""
            for page_num, page in enumerate(reader.pages):
                try:
                    page_text = page.extract_text()
                    text += page_text + "\n"
                except Exception as e:
                    print(f"  Warning: Error on page {page_num}: {e}")
                    continue
            return text.strip()
        except Exception as e:
            print(f"  PyPDF2 extraction failed: {e}")
            return ""
    
    def extract_text(self, pdf_path: str) -> str:
        """Extract text with automatic fallback."""
        filename = Path(pdf_path).name
        print(f"  Extracting: {filename}...", end=" ", flush=True)
        
        # Try PyMuPDF first if available
        if self.use_pymupdf:
            text = self.extract_text_pymupdf(pdf_path)
            if text:
                print(f"✓ ({len(text)} chars)")
                return text
            print("Failed, trying PyPDF2...", end=" ", flush=True)
        
        # Fallback to PyPDF2
        text = self.extract_text_pypdf2(pdf_path)
        if text:
            print(f"✓ ({len(text)} chars)")
        else:
            print("✗ No text extracted")
        
        return text


class TextChunker:
    """Splits text into semantic chunks."""
    
    def __init__(self, chunk_size: int = 1000, overlap: int = 200):
        self.chunk_size = chunk_size
        self.overlap = overlap
    
    def clean_text(self, text: str) -> str:
        """Clean extracted text."""
        # Remove excessive whitespace
        text = re.sub(r'\s+', ' ', text)
        # Remove page numbers (simple heuristic)
        text = re.sub(r'\b\d{1,3}\b\s*$', '', text, flags=re.MULTILINE)
        return text.strip()
    
    def split_into_chunks(self, text: str, metadata: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Split text into overlapping chunks."""
        text = self.clean_text(text)
        
        if not text:
            return []
        
        chunks = []
        words = text.split()
        
        if len(words) <= self.chunk_size:
            # Single chunk
            chunk_text = ' '.join(words)
            if len(chunk_text) > 100:  # Minimum chunk size
                chunks.append(self._create_chunk(chunk_text, metadata, 0))
        else:
            # Multiple chunks with overlap
            start = 0
            chunk_index = 0
            
            while start < len(words):
                end = start + self.chunk_size
                chunk_words = words[start:end]
                chunk_text = ' '.join(chunk_words)
                
                if len(chunk_text) > 100:  # Minimum chunk size
                    chunks.append(self._create_chunk(chunk_text, metadata, chunk_index))
                    chunk_index += 1
                
                # Move forward with overlap
                start += (self.chunk_size - self.overlap)
                
                if end >= len(words):
                    break
        
        return chunks
    
    def _create_chunk(self, content: str, metadata: Dict[str, Any], index: int) -> Dict[str, Any]:
        """Create a chunk with metadata."""
        chunk_id = self._generate_id(content, metadata.get('subject', 'unknown'), index)
        
        return {
            'id': chunk_id,
            'content': content,
            'metadata': {
                **metadata,
                'chunk_index': index
            },
            'quality_score': self._calculate_quality(content),
            'tokens': len(content.split())
        }
    
    def _generate_id(self, content: str, subject: str, index: int) -> str:
        """Generate unique chunk ID."""
        hash_obj = hashlib.md5(content[:50].encode())
        return f"{subject}_{hash_obj.hexdigest()[:8]}_chunk_{index:04d}"
    
    def _calculate_quality(self, content: str) -> float:
        """Calculate chunk quality score."""
        score = 0.5  # Base score
        
        # Length check
        word_count = len(content.split())
        if 200 <= word_count <= 1500:
            score += 0.2
        
        # Has numbers/formulas (likely educational content)
        if re.search(r'\d+', content):
            score += 0.1
        
        # Has proper sentences
        if content.count('.') >= 2:
            score += 0.1
        
        # Not too repetitive
        words = content.lower().split()
        if len(set(words)) / len(words) > 0.4:
            score += 0.1
        
        return min(score, 1.0)


class ComprehensivePDFPipeline:
    """Main pipeline to process all PDFs."""
    
    def __init__(self, base_dir: str = "Raw Data"):
        self.base_dir = Path(base_dir)
        self.output_dir = Path("vectorstore_data")
        self.output_dir.mkdir(exist_ok=True)
        
        self.pdf_processor = PDFProcessor()
        self.chunker = TextChunker(chunk_size=1000, overlap=200)
        
        self.stats = defaultdict(int)
        self.failed_pdfs = []
    
    def find_all_pdfs(self) -> Dict[str, List[Path]]:
        """Find all PDFs organized by category."""
        pdfs = {
            'biology': [],
            'chemistry': [],
            'physics': [],
            'mentor_guide': [],
            'question_bank': []
        }
        
        # NCERT Books
        ncert_dir = self.base_dir / "NCRTBooks"
        if ncert_dir.exists():
            # Biology
            bio_dir = ncert_dir / "Biology"
            if bio_dir.exists():
                pdfs['biology'] = list(bio_dir.rglob("*.pdf"))
            
            # Chemistry
            chem_dir = ncert_dir / "chemistry"
            if chem_dir.exists():
                pdfs['chemistry'] = list(chem_dir.rglob("*.pdf"))
            
            # Physics
            phys_dir = ncert_dir / "Physics"
            if phys_dir.exists():
                pdfs['physics'] = list(phys_dir.rglob("*.pdf"))
        
        # MentorGuide
        mentor_dir = self.base_dir / "MentorGuide"
        if mentor_dir.exists():
            pdfs['mentor_guide'] = [p for p in mentor_dir.glob("*.pdf")]
        
        # QuestionBank
        qb_dir = self.base_dir / "QuestionBank"
        if qb_dir.exists():
            pdfs['question_bank'] = list(qb_dir.glob("*.pdf"))
        
        return pdfs
    
    def extract_metadata(self, pdf_path: Path, category: str) -> Dict[str, Any]:
        """Extract metadata from PDF path."""
        filename = pdf_path.stem
        
        metadata = {
            'source': str(pdf_path.relative_to(self.base_dir)),
            'filename': filename,
            'category': category,
            'ncert_aligned': category in ['biology', 'chemistry', 'physics']
        }
        
        # Subject mapping
        if category in ['biology', 'chemistry', 'physics']:
            metadata['subject'] = category
            
            # Try to extract class from filename/path
            if '11' in str(pdf_path):
                metadata['class'] = 'Class 11'
            elif '12' in str(pdf_path):
                metadata['class'] = 'Class 12'
            else:
                metadata['class'] = 'Unknown'
        
        elif category == 'mentor_guide':
            metadata['subject'] = 'mentor_guide'
            metadata['type'] = 'study_strategy'
        
        elif category == 'question_bank':
            metadata['subject'] = 'question_bank'
            metadata['type'] = 'practice_questions'
            
            # Extract question paper number
            match = re.search(r'Question_Paper_(\d+)', filename)
            if match:
                metadata['paper_number'] = int(match.group(1))
        
        return metadata
    
    def process_category(self, category: str, pdf_paths: List[Path]) -> List[Dict[str, Any]]:
        """Process all PDFs in a category."""
        if not pdf_paths:
            print(f"\nNo PDFs found for {category}")
            return []
        
        print(f"\n{'='*60}")
        print(f"Processing {category.upper()}: {len(pdf_paths)} PDFs")
        print(f"{'='*60}")
        
        all_chunks = []
        checkpoint_interval = 5
        
        for i, pdf_path in enumerate(pdf_paths, 1):
            print(f"\n[{i}/{len(pdf_paths)}] {pdf_path.name}")
            
            try:
                # Extract text
                text = self.pdf_processor.extract_text(str(pdf_path))
                
                if not text or len(text) < 100:
                    print(f"  ⚠ Skipping: Insufficient text extracted")
                    self.failed_pdfs.append((str(pdf_path), "Insufficient text"))
                    self.stats[f'{category}_failed'] += 1
                    continue
                
                # Create metadata
                metadata = self.extract_metadata(pdf_path, category)
                
                # Create chunks
                chunks = self.chunker.split_into_chunks(text, metadata)
                print(f"  Created {len(chunks)} chunks")
                
                all_chunks.extend(chunks)
                self.stats[f'{category}_processed'] += 1
                self.stats[f'{category}_chunks'] += len(chunks)
                
                # Checkpoint save
                if i % checkpoint_interval == 0:
                    self._save_checkpoint(category, all_chunks, i)
            
            except Exception as e:
                print(f"  ✗ Error processing PDF: {e}")
                self.failed_pdfs.append((str(pdf_path), str(e)))
                self.stats[f'{category}_failed'] += 1
                continue
        
        return all_chunks
    
    def _save_checkpoint(self, category: str, chunks: List[Dict[str, Any]], count: int):
        """Save checkpoint."""
        checkpoint_file = self.output_dir / f"{category}_checkpoint_{count}.json"
        try:
            with open(checkpoint_file, 'w', encoding='utf-8') as f:
                json.dump({
                    'category': category,
                    'processed_count': count,
                    'timestamp': datetime.now().isoformat(),
                    'total_chunks': len(chunks),
                    'chunks': chunks
                }, f, indent=2, ensure_ascii=False)
            print(f"  💾 Checkpoint saved: {checkpoint_file.name}")
        except Exception as e:
            print(f"  ⚠ Checkpoint save failed: {e}")
    
    def save_final(self, category: str, chunks: List[Dict[str, Any]]):
        """Save final output."""
        if not chunks:
            print(f"\nNo chunks to save for {category}")
            return
        
        output_file = self.output_dir / f"{category}_chunks.json"
        
        output = {
            'subject': category,
            'created_at': datetime.now().isoformat(),
            'total_chunks': len(chunks),
            'chunks': chunks
        }
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(output, f, indent=2, ensure_ascii=False)
        
        print(f"\n✓ Saved {len(chunks)} chunks to {output_file}")
    
    def process_all(self):
        """Process all PDFs."""
        print("="*60)
        print("COMPREHENSIVE PDF PROCESSING PIPELINE")
        print("="*60)
        
        start_time = datetime.now()
        
        # Find all PDFs
        print("\nScanning for PDFs...")
        all_pdfs = self.find_all_pdfs()
        
        total_pdfs = sum(len(pdfs) for pdfs in all_pdfs.values())
        print(f"\nFound {total_pdfs} PDFs:")
        for category, pdfs in all_pdfs.items():
            print(f"  {category}: {len(pdfs)} PDFs")
        
        # Process each category
        for category, pdf_paths in all_pdfs.items():
            if not pdf_paths:
                continue
            
            chunks = self.process_category(category, pdf_paths)
            self.save_final(category, chunks)
        
        # Final summary
        self._print_summary(start_time)
    
    def _print_summary(self, start_time):
        """Print processing summary."""
        duration = datetime.now() - start_time
        
        print("\n" + "="*60)
        print("PROCESSING COMPLETE")
        print("="*60)
        
        print(f"\nDuration: {duration}")
        
        print("\nStatistics:")
        for key, value in sorted(self.stats.items()):
            print(f"  {key}: {value}")
        
        if self.failed_pdfs:
            print(f"\n⚠ Failed PDFs ({len(self.failed_pdfs)}):")
            for pdf_path, error in self.failed_pdfs[:10]:  # Show first 10
                print(f"  - {Path(pdf_path).name}: {error}")
            if len(self.failed_pdfs) > 10:
                print(f"  ... and {len(self.failed_pdfs) - 10} more")
        
        print("\nOutput files created in vectorstore_data/:")
        for file in sorted(self.output_dir.glob("*_chunks.json")):
            print(f"  ✓ {file.name}")


if __name__ == "__main__":
    pipeline = ComprehensivePDFPipeline()
    pipeline.process_all()
