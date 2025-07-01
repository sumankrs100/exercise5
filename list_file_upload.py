"""
MinIO S3 Connection Module

This module provides functionality to connect to MinIO S3 storage
and perform basic operations like listing buckets.
"""

import logging
from typing import List, Optional, Dict, Any
from minio import Minio
from minio.error import S3Error, InvalidResponseError
from urllib3.exceptions import MaxRetryError
import sys


class MinIOClient:
    """
    A wrapper class for MinIO client operations.
    """
    
    def __init__(self, 
                 endpoint: str,
                 access_key: str,
                 secret_key: str,
                 secure: bool = True,
                 region: Optional[str] = None):
        """
        Initialize MinIO client.
        
        Args:
            endpoint: MinIO server endpoint (e.g., 'localhost:9000')
            access_key: Access key for MinIO
            secret_key: Secret key for MinIO
            secure: Use HTTPS if True, HTTP if False
            region: Optional region name
        """
        self.endpoint = endpoint
        self.access_key = access_key
        self.secret_key = secret_key
        self.secure = secure
        self.region = region
        self.client = None
        
        # Set up logging
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
    
    def connect(self) -> bool:
        """
        Establish connection to MinIO server.
        
        Returns:
            bool: True if connection successful, False otherwise
        """
        try:
            self.client = Minio(
                endpoint=self.endpoint,
                access_key=self.access_key,
                secret_key=self.secret_key,
                secure=self.secure,
                region=self.region
            )
            
            # Test connection by listing buckets
            list(self.client.list_buckets())
            self.logger.info(f"Successfully connected to MinIO at {self.endpoint}")
            return True
            
        except S3Error as e:
            self.logger.error(f"S3 Error: {e}")
            return False
        except InvalidResponseError as e:
            self.logger.error(f"Invalid Response Error: {e}")
            return False
        except MaxRetryError as e:
            self.logger.error(f"Connection Error: {e}")
            return False
        except Exception as e:
            self.logger.error(f"Unexpected error: {e}")
            return False
    
    def list_buckets(self) -> Optional[List[Dict[str, Any]]]:
        """
        List all buckets in the MinIO instance.
        
        Returns:
            List of dictionaries containing bucket information, or None if error
        """
        if not self.client:
            self.logger.error("Client not connected. Call connect() first.")
            return None
        
        try:
            buckets = self.client.list_buckets()
            bucket_list = []
            
            for bucket in buckets:
                bucket_info = {
                    'name': bucket.name,
                    'creation_date': bucket.creation_date.isoformat() if bucket.creation_date else None
                }
                bucket_list.append(bucket_info)
            
            self.logger.info(f"Found {len(bucket_list)} buckets")
            return bucket_list
            
        except S3Error as e:
            self.logger.error(f"Error listing buckets: {e}")
            return None
        except Exception as e:
            self.logger.error(f"Unexpected error listing buckets: {e}")
            return None
    
    def bucket_exists(self, bucket_name: str) -> bool:
        """
        Check if a bucket exists.
        
        Args:
            bucket_name: Name of the bucket to check
            
        Returns:
            bool: True if bucket exists, False otherwise
        """
        if not self.client:
            self.logger.error("Client not connected. Call connect() first.")
            return False
        
        try:
            return self.client.bucket_exists(bucket_name)
        except Exception as e:
            self.logger.error(f"Error checking if bucket exists: {e}")
            return False
    
    def get_bucket_info(self, bucket_name: str) -> Optional[Dict[str, Any]]:
        """
        Get detailed information about a specific bucket.
        
        Args:
            bucket_name: Name of the bucket
            
        Returns:
            Dictionary with bucket information, or None if error
        """
        if not self.client:
            self.logger.error("Client not connected. Call connect() first.")
            return None
        
        try:
            if not self.client.bucket_exists(bucket_name):
                self.logger.warning(f"Bucket '{bucket_name}' does not exist")
                return None
            
            # Get bucket creation date
            buckets = self.client.list_buckets()
            for bucket in buckets:
                if bucket.name == bucket_name:
                    return {
                        'name': bucket.name,
                        'creation_date': bucket.creation_date.isoformat() if bucket.creation_date else None,
                        'exists': True
                    }
            
            return None
            
        except Exception as e:
            self.logger.error(f"Error getting bucket info: {e}")
            return None
    
    def create_bucket(self, bucket_name: str, region: Optional[str] = None) -> bool:
        """
        Create a new bucket.
        
        Args:
            bucket_name: Name of the bucket to create
            region: Optional region for the bucket
            
        Returns:
            bool: True if bucket created successfully, False otherwise
        """
        if not self.client:
            self.logger.error("Client not connected. Call connect() first.")
            return False
        
        try:
            self.client.make_bucket(bucket_name, location=region or self.region)
            self.logger.info(f"Successfully created bucket '{bucket_name}'")
            return True
            
        except S3Error as e:
            if e.code == 'BucketAlreadyOwnedByYou':
                self.logger.info(f"Bucket '{bucket_name}' already exists and is owned by you")
                return True
            elif e.code == 'BucketAlreadyExists':
                self.logger.error(f"Bucket '{bucket_name}' already exists but is owned by someone else")
                return False
            else:
                self.logger.error(f"S3 Error creating bucket: {e}")
                return False
        except Exception as e:
            self.logger.error(f"Unexpected error creating bucket: {e}")
            return False
    
    def create_bucket_if_not_exists(self, bucket_name: str, region: Optional[str] = None) -> bool:
        """
        Create a bucket if it doesn't already exist.
        
        Args:
            bucket_name: Name of the bucket to create
            region: Optional region for the bucket
            
        Returns:
            bool: True if bucket exists or was created successfully, False otherwise
        """
        if not self.client:
            self.logger.error("Client not connected. Call connect() first.")
            return False
        
        try:
            if self.client.bucket_exists(bucket_name):
                self.logger.info(f"Bucket '{bucket_name}' already exists")
                return True
            else:
                self.logger.info(f"Bucket '{bucket_name}' does not exist, creating...")
                return self.create_bucket(bucket_name, region)
                
        except Exception as e:
            self.logger.error(f"Error checking/creating bucket: {e}")
            return False
    
    def list_objects(self, bucket_name: str, prefix: Optional[str] = None, recursive: bool = True) -> Optional[List[Dict[str, Any]]]:
        """
        List objects in a bucket.
        
        Args:
            bucket_name: Name of the bucket
            prefix: Filter objects by prefix (optional)
            recursive: List objects recursively (default: True)
            
        Returns:
            List of dictionaries containing object information, or None if error
        """
        if not self.client:
            self.logger.error("Client not connected. Call connect() first.")
            return None
        
        try:
            if not self.client.bucket_exists(bucket_name):
                self.logger.error(f"Bucket '{bucket_name}' does not exist")
                return None
            
            objects = self.client.list_objects(bucket_name, prefix=prefix, recursive=recursive)
            object_list = []
            
            for obj in objects:
                object_info = {
                    'name': obj.object_name,
                    'size': obj.size,
                    'etag': obj.etag,
                    'last_modified': obj.last_modified.isoformat() if obj.last_modified else None,
                    'content_type': obj.content_type,
                    'is_dir': obj.is_dir
                }
                object_list.append(object_info)
            
            self.logger.info(f"Found {len(object_list)} objects in bucket '{bucket_name}'")
            return object_list
            
        except S3Error as e:
            self.logger.error(f"S3 Error listing objects: {e}")
            return None
        except Exception as e:
            self.logger.error(f"Unexpected error listing objects: {e}")
            return None
    
    def upload_file(self, bucket_name: str, object_name: str, file_path: str, 
                    content_type: Optional[str] = None) -> bool:
        """
        Upload a file to a bucket.
        
        Args:
            bucket_name: Name of the bucket
            object_name: Name of the object in the bucket
            file_path: Path to the local file to upload
            content_type: Optional content type (auto-detected if not provided)
            
        Returns:
            bool: True if upload successful, False otherwise
        """
        if not self.client:
            self.logger.error("Client not connected. Call connect() first.")
            return False
        
        try:
            import os
            if not os.path.exists(file_path):
                self.logger.error(f"File '{file_path}' does not exist")
                return False
            
            if not self.client.bucket_exists(bucket_name):
                self.logger.error(f"Bucket '{bucket_name}' does not exist")
                return False
            
            # Auto-detect content type if not provided
            if not content_type:
                import mimetypes
                content_type, _ = mimetypes.guess_type(file_path)
                if not content_type:
                    content_type = 'application/octet-stream'
            
            self.client.fput_object(
                bucket_name=bucket_name,
                object_name=object_name,
                file_path=file_path,
                content_type=content_type
            )
            
            self.logger.info(f"Successfully uploaded '{file_path}' as '{object_name}' to bucket '{bucket_name}'")
            return True
            
        except S3Error as e:
            self.logger.error(f"S3 Error uploading file: {e}")
            return False
        except Exception as e:
            self.logger.error(f"Unexpected error uploading file: {e}")
            return False
    
    def upload_text_content(self, bucket_name: str, object_name: str, content: str,
                           content_type: str = 'text/plain') -> bool:
        """
        Upload text content directly to a bucket without creating a local file.
        
        Args:
            bucket_name: Name of the bucket
            object_name: Name of the object in the bucket
            content: Text content to upload
            content_type: Content type (default: 'text/plain')
            
        Returns:
            bool: True if upload successful, False otherwise
        """
        if not self.client:
            self.logger.error("Client not connected. Call connect() first.")
            return False
        
        try:
            if not self.client.bucket_exists(bucket_name):
                self.logger.error(f"Bucket '{bucket_name}' does not exist")
                return False
            
            from io import BytesIO
            content_bytes = content.encode('utf-8')
            content_stream = BytesIO(content_bytes)
            
            self.client.put_object(
                bucket_name=bucket_name,
                object_name=object_name,
                data=content_stream,
                length=len(content_bytes),
                content_type=content_type
            )
            
            self.logger.info(f"Successfully uploaded text content as '{object_name}' to bucket '{bucket_name}'")
            return True
            
        except S3Error as e:
            self.logger.error(f"S3 Error uploading text content: {e}")
            return False
        except Exception as e:
            self.logger.error(f"Unexpected error uploading text content: {e}")
            return False
    
    def create_sample_text_file(self, file_path: str, content: Optional[str] = None) -> bool:
        """
        Create a sample text file for testing purposes.
        
        Args:
            file_path: Path where to create the file
            content: Optional custom content (default: sample text)
            
        Returns:
            bool: True if file created successfully, False otherwise
        """
        try:
            if content is None:
                content = """This is a sample text file created for MinIO S3 testing.

File created on: {datetime}
Purpose: Testing file upload functionality
Content: Lorem ipsum dolor sit amet, consectetur adipiscing elit.

Features tested:
- File upload to MinIO S3
- Bucket creation
- Object listing
- Connection handling

End of sample file."""
                
                from datetime import datetime
                content = content.format(datetime=datetime.now().isoformat())
            
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            self.logger.info(f"Sample file created at: {file_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error creating sample file: {e}")
            return False


def main():
    """
    Example usage of the MinIOClient class.
    """
    # Configuration - replace with your MinIO settings
    config = {
        'endpoint': 'localhost:9000',
        'access_key': 'minioadmin',
        'secret_key': 'minioadmin',
        'secure': False  # Set to True for HTTPS
    }
    
    # Create client instance
    minio_client = MinIOClient(**config)
    
    # Connect to MinIO
    if not minio_client.connect():
        print("Failed to connect to MinIO")
        sys.exit(1)
    
    # List buckets
    buckets = minio_client.list_buckets()
    if buckets:
        print(f"\nFound {len(buckets)} buckets:")
        for bucket in buckets:
            print(f"  - {bucket['name']} (created: {bucket['creation_date']})")
    else:
        print("No buckets found or error occurred")
    
    # Example: Check if a specific bucket exists
    bucket_name = "test-bucket"
    if minio_client.bucket_exists(bucket_name):
        print(f"\nBucket '{bucket_name}' exists")
        bucket_info = minio_client.get_bucket_info(bucket_name)
        if bucket_info:
            print(f"Bucket info: {bucket_info}")
    else:
        print(f"\nBucket '{bucket_name}' does not exist")
    
    # Example: Create bucket if it doesn't exist
    new_bucket_name = "my-data-bucket"
    if minio_client.create_bucket_if_not_exists(new_bucket_name):
        print(f"\nBucket '{new_bucket_name}' is ready for use")
    else:
        print(f"\nFailed to create bucket '{new_bucket_name}'")
    
    # Example: Create and upload a sample text file
    sample_file_path = "sample_file.txt"
    if minio_client.create_sample_text_file(sample_file_path):
        print(f"\nSample file created: {sample_file_path}")
        
        # Upload the sample file
        if minio_client.upload_file(new_bucket_name, "documents/sample.txt", sample_file_path):
            print(f"Successfully uploaded sample file to bucket")
        else:
            print("Failed to upload sample file")
    
    # Example: Upload text content directly (without creating local file)
    sample_content = """Direct upload test file
    
This content was uploaded directly to MinIO S3 without creating a local file first.
Timestamp: """ + str(__import__('datetime').datetime.now())
    
    if minio_client.upload_text_content(new_bucket_name, "direct_upload.txt", sample_content):
        print("\nSuccessfully uploaded text content directly to bucket")
    
    # Example: List files in the bucket
    print(f"\nListing files in bucket '{new_bucket_name}':")
    objects = minio_client.list_objects(new_bucket_name)
    if objects:
        for obj in objects:
            size_mb = obj['size'] / (1024 * 1024) if obj['size'] else 0
            print(f"  - {obj['name']} ({size_mb:.3f} MB, modified: {obj['last_modified']})")
    else:
        print("  No files found in bucket")
    
    # Example: List files with specific prefix
    print(f"\nListing files with 'documents/' prefix:")
    docs_objects = minio_client.list_objects(new_bucket_name, prefix="documents/")
    if docs_objects:
        for obj in docs_objects:
            print(f"  - {obj['name']} ({obj['size']} bytes)")
    else:
        print("  No files found with 'documents/' prefix")
    
    # Example: Create bucket with specific region
    regional_bucket = "my-regional-bucket"
    if minio_client.create_bucket_if_not_exists(regional_bucket, region="us-east-1"):
        print(f"\nRegional bucket '{regional_bucket}' is ready for use")
        
        # Upload a file to the regional bucket
        if minio_client.upload_text_content(regional_bucket, "regional_file.txt", 
                                          "This file is in a regional bucket"):
            print(f"Successfully uploaded file to regional bucket")
    else:
        print(f"\nFailed to create regional bucket '{regional_bucket}'")


if __name__ == "__main__":
    main()
