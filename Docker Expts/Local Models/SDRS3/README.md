# SDRS3: SimpleDirectoryReader with S3 Support

This container demonstrates mounting an S3 bucket using s3fs-fuse and running document ingestion with llama-index.

## Usage

1. **Build the image:**
   ```bash
   docker build -t sdrs3 .
   ```
2. **Run the container with AWS credentials:**
   ```bash
   docker run --rm -it \
     -e AWS_ACCESS_KEY_ID=your-access-key \
     -e AWS_SECRET_ACCESS_KEY=your-secret-key \
     -e AWS_DEFAULT_REGION=us-east-1 \
     sdrs3
   ```
3. **Mount the S3 bucket inside the container:**
   ```bash
   s3fs my-rag-base-svt /mnt/s3 -o use_path_request_style -o url=https://s3.amazonaws.com
   ```
4. **Run your SDR script, pointing to `/mnt/s3` as the document directory.**

## Notes
- Make sure your IAM user has appropriate S3 permissions.
- You can automate the mount and script execution in the Dockerfile or an entrypoint script for production use.
