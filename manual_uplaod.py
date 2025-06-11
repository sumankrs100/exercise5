Mimport os
import tempfile
import shutil
from typing import Dict, Any, Optional
from minio import Minio
from minio.error import S3Error
import subprocess
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class VideoConverter:
    """Separate class to handle video conversion operations"""
    
    @staticmethod
    def convert_mp4_to_m3u8(input_file: str, output_dir: str, bucket_name: str) -> Dict[str, Any]:
        """
        Convert MP4 file to M3U8 format using FFmpeg
        
        Args:
            input_file (str): Path to input MP4 file
            output_dir (str): Directory to store output files
            bucket_name (str): MinIO bucket name
            
        Returns:
            Dict[str, Any]: Conversion details including file paths
        """
        try:
            # Create output directory if it doesn't exist
            os.makedirs(output_dir, exist_ok=True)
            
            # Define output file paths
            base_name = os.path.splitext(os.path.basename(input_file))[0]
            playlist_file = os.path.join(output_dir, f"{base_name}.m3u8")
            segment_pattern = os.path.join(output_dir, f"{base_name}_%03d.ts")
            
            # FFmpeg command for HLS conversion
            ffmpeg_cmd = [
                'ffmpeg',
                '-i', input_file,
                '-c:v', 'libx264',
                '-c:a', 'aac',
                '-hls_time', '10',  # 10 second segments
                '-hls_list_size', '0',  # Keep all segments in playlist
                '-hls_segment_filename', segment_pattern,
                '-f', 'hls',
                playlist_file
            ]
            
            logger.info(f"Starting conversion: {input_file} -> {playlist_file}")
            
            # Execute FFmpeg command
            result = subprocess.run(
                ffmpeg_cmd,
                capture_output=True,
                text=True,
                timeout=3600  # 1 hour timeout
            )
            
            if result.returncode != 0:
                raise Exception(f"FFmpeg conversion failed: {result.stderr}")
            
            # Get list of generated files
            generated_files = []
            if os.path.exists(playlist_file):
                generated_files.append(playlist_file)
                
            # Find all segment files
            for file in os.listdir(output_dir):
                if file.endswith('.ts') and base_name in file:
                    generated_files.append(os.path.join(output_dir, file))
            
            conversion_details = {
                'status': 'success',
                'input_file': input_file,
                'playlist_file': playlist_file,
                'output_directory': output_dir,
                'generated_files': generated_files,
                'bucket_name': bucket_name,
                'base_name': base_name
            }
            
            logger.info(f"Conversion completed successfully. Generated {len(generated_files)} files.")
            return conversion_details
            
        except subprocess.TimeoutExpired:
            raise Exception("Video conversion timed out")
        except Exception as e:
            logger.error(f"Conversion failed: {str(e)}")
            raise Exception(f"Video conversion failed: {str(e)}")


class ManualUpload:
    """Class to handle manual upload and processing of MP4 files with MinIO"""
    
    def __init__(self, minio_endpoint: str, access_key: str, secret_key: str, secure: bool = True):
        """
        Initialize ManualUpload with MinIO configuration
        
        Args:
            minio_endpoint (str): MinIO server endpoint
            access_key (str): MinIO access key
            secret_key (str): MinIO secret key
            secure (bool): Whether to use HTTPS (default: True)
        """
        self.minio_client = Minio(
            minio_endpoint,
            access_key=access_key,
            secret_key=secret_key,
            secure=secure
        )
        self.video_converter = VideoConverter()
        
    def process_mp4_file(self, mp4_filename: str, bucket_name: str) -> Dict[str, Any]:
        """
        Main function that downloads MP4, converts to M3U8, and uploads back to MinIO
        
        Args:
            mp4_filename (str): Name of the MP4 file in MinIO bucket
            bucket_name (str): MinIO bucket name
            
        Returns:
            Dict[str, Any]: Processing details including local paths and bucket information
        """
        temp_dir = None
        try:
            # Create temporary directory for processing
            temp_dir = tempfile.mkdtemp(prefix='video_processing_')
            logger.info(f"Created temporary directory: {temp_dir}")
            
            # Step 1: Download MP4 file from MinIO
            local_mp4_path = self._download_file_from_minio(
                bucket_name, mp4_filename, temp_dir
            )
            
            # Step 2: Convert MP4 to M3U8
            conversion_output_dir = os.path.join(temp_dir, 'hls_output')
            conversion_details = self.video_converter.convert_mp4_to_m3u8(
                local_mp4_path, conversion_output_dir, bucket_name
            )
            
            # Step 3: Upload M3U8 files back to MinIO
            upload_details = self._upload_hls_files_to_minio(
                conversion_details, bucket_name
            )
            
            # Prepare final response
            result = {
                'status': 'success',
                'original_file': {
                    'filename': mp4_filename,
                    'bucket': bucket_name,
                    'local_path': local_mp4_path
                },
                'conversion_details': conversion_details,
                'upload_details': upload_details,
                'local_processing_path': temp_dir,
                'bucket_details': {
                    'bucket_name': bucket_name,
                    'endpoint': self.minio_client._base_url,
                    'hls_playlist': f"{conversion_details['base_name']}.m3u8"
                }
            }
            
            logger.info("File processing completed successfully")
            return result
            
        except Exception as e:
            logger.error(f"Processing failed: {str(e)}")
            error_result = {
                'status': 'error',
                'error_message': str(e),
                'original_file': mp4_filename,
                'bucket': bucket_name,
                'local_processing_path': temp_dir
            }
            return error_result
            
        finally:
            # Clean up temporary directory
            if temp_dir and os.path.exists(temp_dir):
                try:
                    shutil.rmtree(temp_dir)
                    logger.info(f"Cleaned up temporary directory: {temp_dir}")
                except Exception as e:
                    logger.warning(f"Failed to clean up temporary directory: {str(e)}")
    
    def _download_file_from_minio(self, bucket_name: str, filename: str, local_dir: str) -> str:
        """Download file from MinIO bucket to local directory"""
        try:
            # Check if bucket exists
            if not self.minio_client.bucket_exists(bucket_name):
                raise Exception(f"Bucket '{bucket_name}' does not exist")
            
            local_file_path = os.path.join(local_dir, filename)
            
            # Download file
            self.minio_client.fget_object(bucket_name, filename, local_file_path)
            logger.info(f"Downloaded {filename} to {local_file_path}")
            
            return local_file_path
            
        except S3Error as e:
            raise Exception(f"MinIO download error: {str(e)}")
        except Exception as e:
            raise Exception(f"Download failed: {str(e)}")
    
    def _upload_hls_files_to_minio(self, conversion_details: Dict[str, Any], bucket_name: str) -> Dict[str, Any]:
        """Upload HLS files (M3U8 and TS segments) to MinIO bucket"""
        uploaded_files = []
        
        try:
            base_name = conversion_details['base_name']
            hls_folder = f"hls/{base_name}/"
            
            for local_file_path in conversion_details['generated_files']:
                filename = os.path.basename(local_file_path)
                object_name = f"{hls_folder}{filename}"
                
                # Determine content type
                content_type = 'application/vnd.apple.mpegurl' if filename.endswith('.m3u8') else 'video/mp2t'
                
                # Upload file
                self.minio_client.fput_object(
                    bucket_name,
                    object_name,
                    local_file_path,
                    content_type=content_type
                )
                
                uploaded_files.append({
                    'local_path': local_file_path,
                    'bucket_path': object_name,
                    'content_type': content_type
                })
                
                logger.info(f"Uploaded {filename} to {object_name}")
            
            upload_details = {
                'status': 'success',
                'bucket_name': bucket_name,
                'hls_folder': hls_folder,
                'uploaded_files': uploaded_files,
                'playlist_url': f"{hls_folder}{base_name}.m3u8"
            }
            
            return upload_details
            
        except S3Error as e:
            raise Exception(f"MinIO upload error: {str(e)}")
        except Exception as e:
            raise Exception(f"Upload failed: {str(e)}")


# Example usage
if __name__ == "__main__":
    # Configuration
    MINIO_ENDPOINT = "your-minio-endpoint.com:9000"
    MINIO_ACCESS_KEY = "your-access-key"
    MINIO_SECRET_KEY = "your-secret-key"
    
    # Initialize ManualUpload
    uploader = ManualUpload(
        minio_endpoint=MINIO_ENDPOINT,
        access_key=MINIO_ACCESS_KEY,
        secret_key=MINIO_SECRET_KEY,
        secure=True
    )
    
    # Process MP4 file
    result = uploader.process_mp4_file("sample_video.mp4", "video-bucket")
    
    # Print results
    if result['status'] == 'success':
        print("✅ Processing completed successfully!")
        print(f"Local processing path: {result['local_processing_path']}")
        print(f"HLS playlist available at: {result['upload_details']['playlist_url']}")
    else:
        print("❌ Processing failed!")
        print(f"Error: {result['error_message']}")
