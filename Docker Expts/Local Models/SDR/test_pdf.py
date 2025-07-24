from llama_index import SimpleDirectoryReader, download_loader
import os

PDFReader = download_loader("PDFReader")

def create_sample_pdf():
    """Create a sample PDF for testing"""
    try:
        from fpdf import FPDF
        
        # Initialize PDF object
        pdf = FPDF()
        
        # Add a page
        pdf.add_page()
        
        # Set font
        pdf.set_font("Arial", size=12)
        
        # Add some test content
        pdf.cell(200, 10, txt="Sample PDF Document", ln=1, align="C")
        pdf.cell(200, 10, txt="This is a test PDF file for SimpleDirectoryReader", ln=2, align="L")
        pdf.cell(200, 10, txt="Testing PDF reading capabilities:", ln=3, align="L")
        pdf.cell(200, 10, txt="- Document structure", ln=4, align="L")
        pdf.cell(200, 10, txt="- Text extraction", ln=5, align="L")
        pdf.cell(200, 10, txt="- Metadata handling", ln=6, align="L")
        
        # Save the pdf
        pdf.output("/app/data/documents/test.pdf")
        return True
        
    except Exception as e:
        print(f"Error creating PDF: {str(e)}")
        return False

def test_pdf_reader():
    """Test PDF reading capabilities"""
    print("\nTesting PDF document loading...")
    
    # Create test PDF
    if not create_sample_pdf():
        print("✗ Failed to create test PDF")
        return False
    
    try:
        # Load the document
        print("Creating reader...")
        # Initialize PDF loader
        loader = PDFReader()
        
        # For PDFs, use PDFReader directly
        reader = SimpleDirectoryReader(
            input_dir="/app/data/documents",
            filename_as_id=True,
            file_extractor={
                ".pdf": loader  # Use PDFReader instance
            }
        )
        
        print("Loading data...")
        documents = reader.load_data()
        print(f"Got {len(documents)} documents")
        print("\nDocument details:")
        for doc in documents:
            print(f"\nDocument metadata: {doc.metadata}")
            print(f"Document type: {type(doc)}")
            print(f"First 100 chars of text: {doc.text[:100]}")
            
        pdf_docs = [doc for doc in documents if os.path.splitext(doc.metadata["file_name"])[1] == ".pdf"]
        
        if not pdf_docs:
            print("✗ No PDF documents found")
            return False
        
        print(f"✓ Successfully loaded {len(pdf_docs)} PDF document(s)")
        
        # Print document details
        for doc in pdf_docs:
            print(f"\nDocument Content (first 200 chars):")
            print(f"{doc.text[:200]}...")
            print("\nMetadata:")
            for key, value in doc.metadata.items():
                print(f"- {key}: {value}")
            
        return True
        
    except Exception as e:
        print(f"✗ Error testing PDF reader: {str(e)}")
        import traceback
        print(traceback.format_exc())
        return False

if __name__ == "__main__":
    print("Starting PDF Reader tests...")
    success = test_pdf_reader()
    print("\nTest results:")
    print("✓ All tests passed" if success else "✗ Tests failed")
