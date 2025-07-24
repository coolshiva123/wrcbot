#!/usr/bin/env python3

from llama_index import SimpleDirectoryReader
import os

def test_directory_reader():
    """Test SimpleDirectoryReader functionality"""
    
    # Create a test document
    docs_dir = "/app/data/documents"
    os.makedirs(docs_dir, exist_ok=True)
    
    # Create different types of documents for testing
    with open(os.path.join(docs_dir, "test1.txt"), "w") as f:
        f.write("This is a test document 1.\nIt has multiple lines.\nTesting SimpleDirectoryReader.")
    
    with open(os.path.join(docs_dir, "test2.txt"), "w") as f:
        f.write("This is test document 2.\nTesting document loading capabilities.")
    
    print("\n1. Testing basic document loading...")
    try:
        reader = SimpleDirectoryReader(docs_dir)
        documents = reader.load_data()
        print(f"✓ Successfully loaded {len(documents)} documents")
        
        # Print document contents
        for i, doc in enumerate(documents, 1):
            print(f"\nDocument {i}:")
            print(f"Content: {doc.text[:100]}...")  # Print first 100 chars
            print(f"Metadata: {doc.metadata}")
            
    except Exception as e:
        print(f"✗ Error loading documents: {str(e)}")
        return False
    
    print("\n2. Testing metadata extraction...")
    try:
        reader = SimpleDirectoryReader(
            docs_dir,
            filename_as_id=True,  # Use filename as document ID
        )
        documents = reader.load_data()
        print(f"✓ Successfully loaded documents with metadata")
        
        for doc in documents:
            print(f"\nFile: {doc.metadata.get('file_name')}")
            print(f"ID: {doc.metadata.get('doc_id')}")
            
    except Exception as e:
        print(f"✗ Error testing metadata: {str(e)}")
        return False
    
    return True

if __name__ == "__main__":
    print("Starting SimpleDirectoryReader tests...")
    success = test_directory_reader()
    print("\nTest results:")
    print("✓ All tests passed" if success else "✗ Tests failed")
