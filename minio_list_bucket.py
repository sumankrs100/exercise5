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


if __name__ == "__main__":
    main()
