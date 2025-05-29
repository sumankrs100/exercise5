from minio import Minio
from minio.error import S3Error
from datetime import datetime
import os

class MinIOBucket:
    """
    A class to manage MinIO buckets - check existence, create if needed, and get details.
    """
    
    def __init__(self, endpoint="localhost:9000", access_key=None, secret_key=None, secure=False):
        """
        Initialize MinIO client connection.
        
        Args:
            endpoint (str): MinIO server endpoint (default: localhost:9000)
            access_key (str): MinIO access key (if None, will try to get from environment)
            secret_key (str): MinIO secret key (if None, will try to get from environment)
            secure (bool): Whether to use HTTPS (default: False for local development)
        """
        # Get credentials from environment variables if not provided
        if access_key is None:
            access_key = os.getenv('MINIO_ACCESS_KEY', 'minioadmin')
        if secret_key is None:
            secret_key = os.getenv('MINIO_SECRET_KEY', 'minioadmin')
            
        try:
            self.client = Minio(
                endpoint,
                access_key=access_key,
                secret_key=secret_key,
                secure=secure
            )
            print(f"✅ Connected to MinIO server at {endpoint}")
        except Exception as e:
            print(f"❌ Failed to connect to MinIO server: {e}")
            raise
    
    def manage_bucket(self, bucket_name):
        """
        Check if bucket exists, create if it doesn't, and return bucket details.
        
        Args:
            bucket_name (str): Name of the bucket to check/create
            
        Returns:
            dict: Dictionary containing bucket information and status
        """
        try:
            # Validate bucket name
            if not bucket_name or not isinstance(bucket_name, str):
                return {
                    "error": "Invalid bucket name. Must be a non-empty string.",
                    "status": "error"
                }
            
            # Check if bucket exists
            bucket_exists = self.client.bucket_exists(bucket_name)
            
            if bucket_exists:
                print(f"✅ Bucket '{bucket_name}' already exists")
                bucket_info = self._get_bucket_details(bucket_name)
                bucket_info["status"] = "exists"
                bucket_info["action"] = "found_existing"
                return bucket_info
            else:
                print(f"📦 Bucket '{bucket_name}' does not exist. Creating...")
                
                # Create the bucket
                self.client.make_bucket(bucket_name)
                print(f"✅ Successfully created bucket '{bucket_name}'")
                
                # Get details of the newly created bucket
                bucket_info = self._get_bucket_details(bucket_name)
                bucket_info["status"] = "created"
                bucket_info["action"] = "newly_created"
                return bucket_info
                
        except S3Error as e:
            error_msg = f"MinIO S3 Error: {e}"
            print(f"❌ {error_msg}")
            return {
                "error": error_msg,
                "status": "error",
                "bucket_name": bucket_name
            }
        except Exception as e:
            error_msg = f"Unexpected error: {e}"
            print(f"❌ {error_msg}")
            return {
                "error": error_msg,
                "status": "error",
                "bucket_name": bucket_name
            }
    
    def _get_bucket_details(self, bucket_name):
        """
        Get detailed information about a bucket.
        
        Args:
            bucket_name (str): Name of the bucket
            
        Returns:
            dict: Bucket details including name, creation date, and object count
        """
        try:
            # Get basic bucket info
            bucket_info = {
                "bucket_name": bucket_name,
                "exists": True,
                "checked_at": datetime.now().isoformat()
            }
            
            # Try to get bucket creation date and other metadata
            try:
                # List objects to get count and size
                objects = list(self.client.list_objects(bucket_name, recursive=True))
                bucket_info["object_count"] = len(objects)
                bucket_info["total_size_bytes"] = sum(obj.size for obj in objects if obj.size)
                
                # Get a sample of object names (first 5)
                bucket_info["sample_objects"] = [obj.object_name for obj in objects[:5]]
                
            except S3Error:
                # If we can't list objects, still return basic info
                bucket_info["object_count"] = "Unable to retrieve"
                bucket_info["total_size_bytes"] = "Unable to retrieve"
                bucket_info["sample_objects"] = []
            
            return bucket_info
            
        except Exception as e:
            return {
                "bucket_name": bucket_name,
                "error": f"Could not retrieve bucket details: {e}",
                "exists": True
            }
    
    def list_all_buckets(self):
        """
        List all buckets in the MinIO server.
        
        Returns:
            list: List of bucket information dictionaries
        """
        try:
            buckets = self.client.list_buckets()
            bucket_list = []
            
            for bucket in buckets:
                bucket_info = {
                    "name": bucket.name,
                    "creation_date": bucket.creation_date.isoformat() if bucket.creation_date else None
                }
                bucket_list.append(bucket_info)
            
            return bucket_list
            
        except Exception as e:
            print(f"❌ Error listing buckets: {e}")
            return []

# Example usage
if __name__ == "__main__":
    # Initialize MinIO bucket manager
    # You can customize the connection parameters as needed
    minio_manager = MinIOBucket(
        endpoint="localhost:9000",  # Change to your MinIO server
        access_key="minioadmin",    # Change to your access key
        secret_key="minioadmin",    # Change to your secret key
        secure=False                # Set to True for HTTPS
    )
    
    # Test the bucket management functionality
    test_bucket_name = "my-test-bucket"
    
    print(f"\n🔍 Managing bucket: {test_bucket_name}")
    result = minio_manager.manage_bucket(test_bucket_name)
    
    print("\n📋 Bucket Details:")
    for key, value in result.items():
        print(f"  {key}: {value}")
    
    # List all buckets
    print("\n📦 All buckets:")
    all_buckets = minio_manager.list_all_buckets()
    for bucket in all_buckets:
        print(f"  - {bucket['name']} (created: {bucket['creation_date']})")
