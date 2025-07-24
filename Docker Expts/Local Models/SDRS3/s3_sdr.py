import boto3
import os
from llama_index import SimpleDirectoryReader

def download_s3_docs(bucket, prefix, local_dir):
    os.makedirs(local_dir, exist_ok=True)
    s3 = boto3.client("s3")
    paginator = s3.get_paginator("list_objects_v2")
    print(f"\nListing all S3 object keys in bucket '{bucket}' with prefix '{prefix}':")
    found_any = False
    for page in paginator.paginate(Bucket=bucket, Prefix=prefix):
        for obj in page.get("Contents", []):
            key = obj["Key"]
            print(f"- {key}")
            found_any = True
    if not found_any:
        print("No objects found in S3 bucket with the given prefix.")
    # Now, download only .txt, .pdf, and .docx files
    for page in paginator.paginate(Bucket=bucket, Prefix=prefix):
        for obj in page.get("Contents", []):
            key = obj["Key"]
            if key.endswith((".txt", ".pdf", ".docx")):
                local_path = os.path.join(local_dir, os.path.basename(key))
                print(f"Downloading {key} to {local_path}")
                s3.download_file(bucket, key, local_path)

if __name__ == "__main__":
    BUCKET = "my-rag-base-svt"
    PREFIX = ""  # or set to a folder in your bucket
    LOCAL_DIR = "/tmp/s3docs"
    download_s3_docs(BUCKET, PREFIX, LOCAL_DIR)
    print(f"\nListing files in {LOCAL_DIR} after S3 download:")
    files = os.listdir(LOCAL_DIR)
    if not files:
        print("No files found in the directory.")
    else:
        for f in files:
            print(f"- {f}")
    print("\nRunning SimpleDirectoryReader on downloaded files...")
    reader = SimpleDirectoryReader(LOCAL_DIR)
    documents = reader.load_data()
    print(f"\nLoaded {len(documents)} documents from S3 bucket.")
    for doc in documents:
        print(f"\nFile: {doc.metadata.get('file_name')}")
        print(f"First 200 chars: {doc.text[:200]}")
        print(f"Metadata: {doc.metadata}")
