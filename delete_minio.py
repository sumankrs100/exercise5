"""
MinIO Service Module - Delete Only

A simplified Python module for deleting files and folders from S3-compatible storage
using the MinIO client library.
"""

import logging
from typing import Dict, Any
from minio import Minio
from minio.error import S3Error


class MinIOServiceError(Exception):
    """Custom exception for MinIO service errors"""
    pass


class MinIOService:
    """
    A simplified service class for deleting files and folders from MinIO/S3.
    
    Assumes buckets already exist and focuses solely on deletion operations.
    """
    
    def __init__(
        self,
        endpoint: str,
        access_key: str,
        secret_key: str,
        secure: bool = True,
        region: str = None
    ):
        """
        Initialize the MinIO service.
        
        Args:
            endpoint: MinIO server endpoint (e.g., 'localhost:9000' or 's3.amazonaws.com')
            access_key: Access key for authentication
            secret_key: Secret key for authentication
            secure: Whether to use HTTPS (default: True)
            region: Region name (optional)
        
        Raises:
            MinIOServiceError: If connection to MinIO server fails
        """
        self.logger = logging.getLogger(__name__)
        
        try:
            self.client = Minio(
                endpoint=endpoint,
                access_key=access_key,
                secret_key=secret_key,
                secure=secure,
                region=region
            )
        except Exception as e:
            raise MinIOServiceError(f"Failed to initialize MinIO client: {str(e)}")
    
    def delete(self, bucket_name: str, path: str) -> Dict[str, Any]:
        """
        Delete a file or folder from MinIO bucket.
        
        Automatically detects whether the path is a file or folder and performs
        the appropriate deletion operation.
        
        Args:
            bucket_name: Name of the bucket
            path: Path to file or folder to delete
            
        Returns:
            Dict containing deletion results:
                For files:
                    - 'type': 'file'
                    - 'success': bool
                    - 'object_name': str
                For folders:
                    - 'type': 'folder'
                    - 'total_objects': int
                    - 'deleted_successfully': int
                    - 'failed_deletions': int
                    - 'deleted_objects': list
                    - 'failed_objects': list
                For not found:
                    - 'type': 'not_found'
                    - 'success': False
                    - 'message': str
            
        Raises:
            MinIOServiceError: If deletion fails
        """
        try:
            # First, check if the path exists as a direct file
            if self._file_exists(bucket_name, path):
                # It's a file
                success = self._delete_file(bucket_name, path)
                return {
                    'type': 'file',
                    'success': success,
                    'object_name': path
                }
            
            # Check if it's a folder by looking for objects with this prefix
            folder_path = path if path.endswith('/') else path + '/'
            
            try:
                # List objects with the folder prefix to see if any exist
                objects = list(self.client.list_objects(bucket_name, prefix=folder_path, recursive=True))
                
                if objects:
                    # It's a folder with contents
                    result = self._delete_folder(bucket_name, path)
                    result['type'] = 'folder'
                    return result
                else:
                    # Check if the original path (without trailing slash) matches any objects
                    if not path.endswith('/'):
                        objects = list(self.client.list_objects(bucket_name, prefix=path, recursive=True))
                        if objects:
                            # Treat it as a folder
                            result = self._delete_folder(bucket_name, path)
                            result['type'] = 'folder'
                            return result
                    
                    # Nothing found
                    self.logger.warning(f"No file or folder found at path: {bucket_name}/{path}")
                    return {
                        'type': 'not_found',
                        'success': False,
                        'message': f"No file or folder found at path: {path}"
                    }
                    
            except S3Error as e:
                if e.code == 'NoSuchBucket':
                    raise MinIOServiceError(f"Bucket '{bucket_name}' does not exist")
                else:
                    raise MinIOServiceError(f"Error checking path: {str(e)}")
                    
        except MinIOServiceError:
            raise
        except Exception as e:
            error_msg = f"Unexpected error during deletion: {str(e)}"
            self.logger.error(error_msg)
            raise MinIOServiceError(error_msg)
    
    def _file_exists(self, bucket_name: str, object_name: str) -> bool:
        """Check if a file exists in the bucket."""
        try:
            self.client.stat_object(bucket_name, object_name)
            return True
        except S3Error as e:
            if e.code == 'NoSuchKey':
                return False
            else:
                raise MinIOServiceError(f"Error checking file existence: {str(e)}")
    
    def _delete_file(self, bucket_name: str, object_name: str) -> bool:
        """Delete a single file from MinIO bucket."""
        try:
            self.client.remove_object(bucket_name, object_name)
            self.logger.info(f"Successfully deleted file: {bucket_name}/{object_name}")
            return True
            
        except S3Error as e:
            error_msg = f"Failed to delete file {bucket_name}/{object_name}: {str(e)}"
            self.logger.error(error_msg)
            raise MinIOServiceError(error_msg)
        except Exception as e:
            error_msg = f"Unexpected error during file deletion: {str(e)}"
            self.logger.error(error_msg)
            raise MinIOServiceError(error_msg)
    
    def _delete_folder(self, bucket_name: str, folder_path: str) -> Dict[str, Any]:
        """Delete an entire folder and all its contents from MinIO bucket."""
        try:
            # Ensure folder_path ends with '/' for proper prefix matching
            if folder_path and not folder_path.endswith('/'):
                folder_path += '/'
            
            self.logger.info(f"Starting deletion of folder: {bucket_name}/{folder_path}")
            
            # List all objects in the folder
            objects_to_delete = []
            try:
                objects = self.client.list_objects(bucket_name, prefix=folder_path, recursive=True)
                objects_to_delete = [obj.object_name for obj in objects]
            except S3Error as e:
                raise MinIOServiceError(f"Failed to list objects in folder: {str(e)}")
            
            if not objects_to_delete:
                self.logger.warning(f"No objects found in folder {bucket_name}/{folder_path}")
                return {
                    'total_objects': 0,
                    'deleted_successfully': 0,
                    'failed_deletions': 0,
                    'deleted_objects': [],
                    'failed_objects': []
                }
            
            self.logger.info(f"Found {len(objects_to_delete)} objects to delete in folder {folder_path}")
            
            # Delete all objects in batches for better performance
            deleted_objects = []
            failed_objects = []
            
            try:
                from minio.deleteobjects import DeleteObject
                
                # Create delete objects list
                delete_object_list = [DeleteObject(name) for name in objects_to_delete]
                
                # Perform batch deletion
                errors = self.client.remove_objects(bucket_name, delete_object_list)
                
                # Process results
                error_objects = {}
                for error in errors:
                    error_objects[error.object_name] = str(error)
                    self.logger.error(f"Failed to delete {error.object_name}: {error}")
                
                # Categorize results
                for obj_name in objects_to_delete:
                    if obj_name in error_objects:
                        failed_objects.append({
                            'object_name': obj_name,
                            'error': error_objects[obj_name]
                        })
                    else:
                        deleted_objects.append(obj_name)
                
            except Exception as e:
                # Fallback to individual deletion if batch deletion fails
                self.logger.warning(f"Batch deletion failed, falling back to individual deletion: {str(e)}")
                
                for obj_name in objects_to_delete:
                    try:
                        self.client.remove_object(bucket_name, obj_name)
                        deleted_objects.append(obj_name)
                    except Exception as delete_error:
                        failed_objects.append({
                            'object_name': obj_name,
                            'error': str(delete_error)
                        })
                        self.logger.error(f"Failed to delete {obj_name}: {delete_error}")
            
            # Summary
            result = {
                'total_objects': len(objects_to_delete),
                'deleted_successfully': len(deleted_objects),
                'failed_deletions': len(failed_objects),
                'deleted_objects': deleted_objects,
                'failed_objects': failed_objects
            }
            
            if result['failed_deletions'] == 0:
                self.logger.info(f"Successfully deleted entire folder {bucket_name}/{folder_path} "
                               f"({result['deleted_successfully']} objects)")
            else:
                self.logger.warning(f"Folder deletion completed with some failures: "
                                  f"{result['deleted_successfully']} successful, "
                                  f"{result['failed_deletions']} failed")
            
            return result
            
        except MinIOServiceError:
            raise
        except Exception as e:
            error_msg = f"Unexpected error during folder deletion: {str(e)}"
            self.logger.error(error_msg)
            raise MinIOServiceError(error_msg)


if __name__ == "__main__":
    # Example usage
    import os
    
    # Setup logging
    logging.basicConfig(level=logging.INFO)
    
    try:
        # Initialize service
        service = MinIOService(
            endpoint=os.getenv('MINIO_ENDPOINT', 'localhost:9000'),
            access_key=os.getenv('MINIO_ACCESS_KEY', 'minioadmin'),
            secret_key=os.getenv('MINIO_SECRET_KEY', 'minioadmin'),
            secure=False
        )
        
        bucket_name = "test-bucket"
        
        # Example: Delete a single file
        print("=== Deleting single file ===")
        result = service.delete(bucket_name, "documents/report.pdf")
        print(f"Result: {result}")
        
        # Example: Delete entire folder
        print("\n=== Deleting entire folder ===")
        result = service.delete(bucket_name, "documents/")
        print(f"Result: {result}")
        
        # Example: Delete folder without trailing slash
        print("\n=== Deleting folder (no trailing slash) ===")
        result = service.delete(bucket_name, "old-data")
        print(f"Result: {result}")
        
        print("\nAll delete operations completed!")
        
    except MinIOServiceError as e:
        print(f"MinIO service error: {e}")
    except Exception as e:
        print(f"Unexpected error: {e}")
