from llama_index import SimpleDirectoryReader
import os

def test_s3_reader():
    docs_dir = "/mnt/s3"
    print(f"Reading documents from {docs_dir}...")
    try:
        reader = SimpleDirectoryReader(docs_dir)
        documents = reader.load_data()
        print(f"✓ Loaded {len(documents)} documents from S3 mount.")
        for i, doc in enumerate(documents, 1):
            print(f"\nDocument {i}:")
            print(f"Content: {doc.text[:100]}...")
            print(f"Metadata: {doc.metadata}")
    except Exception as e:
        print(f"✗ Error: {e}")
        return False
    return True

if __name__ == "__main__":
    print("Starting S3 SDR test...")
    success = test_s3_reader()
    print("\nTest results:")
    print("✓ All tests passed" if success else "✗ Tests failed")
