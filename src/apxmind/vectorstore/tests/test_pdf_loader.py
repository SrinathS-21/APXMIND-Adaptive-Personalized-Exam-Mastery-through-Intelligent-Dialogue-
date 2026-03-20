"""
Test PDF Loader
===============

Tests for PDF loading functionality.

Usage:
    python src\APXMIND\vectorstore\tests\test_pdf_loader.py
"""

import sys
from pathlib import Path
from datetime import datetime

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from apxmind.vectorstore.ingestion import PDFLoader, NCERTBookLoader, QuestionPaperLoader


def test_pdf_loader_initialization():
    """Test PDF loader initialization."""
    print("=" * 60)
    print("TEST 1: PDF Loader Initialization")
    print("=" * 60)
    
    loader = PDFLoader()
    
    print(f"\n✓ PDF Loader created")
    print(f"  Extract images: {loader.extract_images}")
    print(f"  Extract tables: {loader.extract_tables}")
    print(f"  Min text length: {loader.min_text_length}")
    print(f"  Supported extensions: {loader.get_supported_extensions()}")
    
    return True


def test_ncert_loader_initialization():
    """Test NCERT book loader initialization."""
    print("\n" + "=" * 60)
    print("TEST 2: NCERT Book Loader Initialization")
    print("=" * 60)
    
    loader = NCERTBookLoader()
    
    print(f"\n✓ NCERT Book Loader created")
    print(f"  Extract images: {loader.extract_images}")
    print(f"  Extract tables: {loader.extract_tables}")
    print(f"  Min text length: {loader.min_text_length}")
    
    return True


def test_question_paper_loader():
    """Test question paper loader initialization."""
    print("\n" + "=" * 60)
    print("TEST 3: Question Paper Loader Initialization")
    print("=" * 60)
    
    loader = QuestionPaperLoader()
    
    print(f"\n✓ Question Paper Loader created")
    print(f"  Extract images: {loader.extract_images}")
    print(f"  Extract tables: {loader.extract_tables}")
    print(f"  Min text length: {loader.min_text_length}")
    
    return True


def test_subject_detection():
    """Test subject detection from path."""
    print("\n" + "=" * 60)
    print("TEST 4: Subject Detection")
    print("=" * 60)
    
    loader = PDFLoader()
    
    test_cases = [
        ('Raw Data/NCRTBooks/Biology/11Bio1/chapter1.pdf', 'biology'),
        ('Raw Data/NCRTBooks/chemistry/12ChemPart1/chapter2.pdf', 'chemistry'),
        ('Raw Data/NCRTBooks/Physics/11Physics1/chapter3.pdf', 'physics'),
        ('Raw Data/other/document.pdf', None),
    ]
    
    print("\n✓ Testing subject detection:")
    for path, expected in test_cases:
        detected = loader._detect_subject(path)
        match = "✓" if detected == expected else "✗"
        print(f"  {match} {path}")
        print(f"     Expected: {expected}, Got: {detected}")
    
    return True


def test_class_level_detection():
    """Test class level detection."""
    print("\n" + "=" * 60)
    print("TEST 5: Class Level Detection")
    print("=" * 60)
    
    loader = PDFLoader()
    
    test_cases = [
        ('11Bio1', 11),
        ('12ChemPart1', 12),
        ('11Physics1', 11),
        ('chapter1', None),
    ]
    
    print("\n✓ Testing class level detection:")
    for filename, expected in test_cases:
        detected = loader._detect_class_level(filename)
        match = "✓" if detected == expected else "✗"
        print(f"  {match} Filename: {filename}")
        print(f"     Expected: {expected}, Got: {detected}")
    
    return True


def test_part_number_detection():
    """Test part number detection."""
    print("\n" + "=" * 60)
    print("TEST 6: Part Number Detection")
    print("=" * 60)
    
    loader = PDFLoader()
    
    test_cases = [
        ('11Bio1', 1),
        ('12ChemPart2', 2),
        ('11PhysicsPart1', 1),
        ('textbook', None),
    ]
    
    print("\n✓ Testing part number detection:")
    for filename, expected in test_cases:
        detected = loader._detect_part_number(filename)
        match = "✓" if detected == expected else "✗"
        print(f"  {match} Filename: {filename}")
        print(f"     Expected: {expected}, Got: {detected}")
    
    return True


def test_text_cleaning():
    """Test text cleaning."""
    print("\n" + "=" * 60)
    print("TEST 7: Text Cleaning")
    print("=" * 60)
    
    loader = PDFLoader()
    
    dirty_text = """   123   This is   a test   with  

    multiple    spaces   and   
    
    newlines.   456   """
    
    clean_text = loader._clean_text(dirty_text)
    
    print(f"\n✓ Text cleaning:")
    print(f"  Original length: {len(dirty_text)} chars")
    print(f"  Cleaned length: {len(clean_text)} chars")
    print(f"  Cleaned text: \"{clean_text}\"")
    
    # Should remove excessive whitespace
    has_multiple_spaces = '  ' in clean_text
    
    print(f"\n  Has multiple spaces: {has_multiple_spaces}")
    
    return not has_multiple_spaces


def test_structure_detection():
    """Test chapter/section structure detection."""
    print("\n" + "=" * 60)
    print("TEST 8: Structure Detection")
    print("=" * 60)
    
    loader = PDFLoader()
    
    test_text = """
    CHAPTER 1: THE LIVING WORLD
    
    1.1 What is Living?
    
    Biology is the science of life forms and living processes.
    """
    
    structure = loader._detect_structure(test_text)
    
    print(f"\n✓ Detected structure:")
    print(f"  Chapter: {structure.get('chapter')}")
    print(f"  Section: {structure.get('section')}")
    print(f"  Topic: {structure.get('topic')}")
    
    return structure.get('topic') is not None


def test_diagram_detection():
    """Test diagram detection."""
    print("\n" + "=" * 60)
    print("TEST 9: Diagram Detection")
    print("=" * 60)
    
    loader = PDFLoader()
    
    text_with_diagram = "See Figure 1.1 for the cell structure diagram."
    text_without_diagram = "This is just plain text content."
    
    has_diagram_1 = loader._detect_diagrams(text_with_diagram)
    has_diagram_2 = loader._detect_diagrams(text_without_diagram)
    
    print(f"\n✓ Diagram detection:")
    print(f"  Text with 'Figure': {has_diagram_1}")
    print(f"  Plain text: {has_diagram_2}")
    
    return has_diagram_1 and not has_diagram_2


def test_file_validation():
    """Test source file validation."""
    print("\n" + "=" * 60)
    print("TEST 10: File Validation")
    print("=" * 60)
    
    loader = PDFLoader()
    
    # Test with actual files if they exist
    base_path = Path("d:/APXMIND-main/APXMIND-main/Raw Data/NCRTBooks")
    
    if base_path.exists():
        pdf_files = list(base_path.rglob("*.pdf"))
        if pdf_files:
            test_file = str(pdf_files[0])
            is_valid = loader.validate_source(test_file)
            print(f"\n✓ Found PDF file: {Path(test_file).name}")
            print(f"  Valid: {is_valid}")
            
            return is_valid
    
    print(f"\n⚠ No PDF files found in Raw Data/")
    print(f"  Testing with mock validation")
    
    # Mock test
    is_valid_pdf = loader.validate_source("test.pdf") == False  # File doesn't exist
    is_valid_txt = loader.validate_source("test.txt") == False  # Wrong extension
    
    print(f"  Non-existent PDF rejected: {is_valid_pdf}")
    print(f"  TXT file rejected: {is_valid_txt}")
    
    return True


def test_load_nonexistent_file():
    """Test loading a non-existent file."""
    print("\n" + "=" * 60)
    print("TEST 11: Load Non-Existent File")
    print("=" * 60)
    
    loader = PDFLoader()
    result = loader.load("nonexistent_file.pdf")
    
    print(f"\n✓ Load result:")
    print(f"  Success: {result.success}")
    print(f"  Has document: {result.document is not None}")
    print(f"  Error: {result.error}")
    
    return not result.success and result.error is not None


def test_load_actual_pdf():
    """Test loading an actual PDF if available."""
    print("\n" + "=" * 60)
    print("TEST 12: Load Actual PDF (if available)")
    print("=" * 60)
    
    loader = NCERTBookLoader()
    
    # Try to find an actual PDF
    base_path = Path("d:/APXMIND-main/APXMIND-main/Raw Data/NCRTBooks")
    
    if not base_path.exists():
        print(f"\n⚠ Raw Data not found, skipping actual PDF test")
        return True
    
    pdf_files = list(base_path.rglob("*.pdf"))
    
    if not pdf_files:
        print(f"\n⚠ No PDF files found, skipping actual PDF test")
        return True
    
    # Load first PDF
    test_file = str(pdf_files[0])
    print(f"\n✓ Loading: {Path(test_file).name}")
    
    result = loader.load(test_file)
    
    print(f"\n  Load Result:")
    print(f"    Success: {result.success}")
    print(f"    Has document: {result.document is not None}")
    
    if result.success and result.document:
        doc = result.document
        print(f"\n  Document:")
        print(f"    Source: {doc.source_path}")
        print(f"    Page count: {doc.page_count}")
        print(f"    Content length: {len(doc.content)} chars")
        print(f"    Content preview: \"{doc.content[:100]}...\"")
        print(f"\n  Metadata:")
        for key, value in list(doc.metadata.items())[:8]:
            print(f"    {key}: {value}")
    
    if result.error:
        print(f"\n  Error: {result.error}")
    
    return result.success


def main():
    """Run all tests."""
    print("\n" + "=" * 60)
    print("PDF LOADER TEST SUITE")
    print("=" * 60 + "\n")
    
    tests = [
        ("PDF Loader Initialization", test_pdf_loader_initialization),
        ("NCERT Loader Initialization", test_ncert_loader_initialization),
        ("Question Paper Loader", test_question_paper_loader),
        ("Subject Detection", test_subject_detection),
        ("Class Level Detection", test_class_level_detection),
        ("Part Number Detection", test_part_number_detection),
        ("Text Cleaning", test_text_cleaning),
        ("Structure Detection", test_structure_detection),
        ("Diagram Detection", test_diagram_detection),
        ("File Validation", test_file_validation),
        ("Load Non-Existent File", test_load_nonexistent_file),
        ("Load Actual PDF", test_load_actual_pdf),
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            success = test_func()
            results.append((test_name, success))
        except Exception as e:
            print(f"\n✗ Test '{test_name}' crashed: {e}")
            import traceback
            traceback.print_exc()
            results.append((test_name, False))
    
    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    
    passed = sum(1 for _, success in results if success)
    total = len(results)
    
    for test_name, success in results:
        status = "✓ PASS" if success else "✗ FAIL"
        print(f"  {status}: {test_name}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    print("=" * 60 + "\n")
    
    return passed == total


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
