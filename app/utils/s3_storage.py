import boto3
from botocore.exceptions import ClientError
import os
from typing import Any, Dict, Optional
import uuid

from app.core.config import settings
from app.utils.logging import get_logger

logger = get_logger("s3_storage")

class S3Storage:
    """S3 storage client for document persistence"""
    
    def __init__(self):
        """Initialize S3 storage client"""
        self.s3_client = boto3.client(
            's3',
            region_name=settings.AWS_REGION,
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY
        )
        self.bucket_name = settings.AWS_S3_BUCKET
        self.logger = logger
    
    async def upload_document(self, file_content: bytes, file_name: Optional[str] = None, 
                        content_type: str = 'application/octet-stream', metadata: Dict[str, str] = None) -> Dict[str, Any]:
        """
        Upload document to S3
        
        Args:
            file_content: File content bytes
            file_name: Optional file name (will generate if not provided)
            content_type: MIME type of the file
            metadata: Optional metadata dict
            
        Returns:
            Dict with file information including S3 URL
        """
        try:
            # Generate unique key if filename not provided
            if not file_name:
                ext = self._get_extension_from_content_type(content_type)
                file_name = f"{uuid.uuid4()}{ext}"
            
            # Ensure the key has proper path structure
            key = f"documents/{file_name}"
            
            # Prepare upload parameters
            upload_args = {
                'Bucket': self.bucket_name,
                'Key': key,
                'Body': file_content,
                'ContentType': content_type
            }
            
            # Add metadata if provided
            if metadata:
                upload_args['Metadata'] = {k: str(v) for k, v in metadata.items()}
            
            # Upload file to S3
            self.s3_client.put_object(**upload_args)
            
            # Generate S3 URL
            s3_url = f"https://{self.bucket_name}.s3.{settings.AWS_REGION}.amazonaws.com/{key}"
            
            return {
                'file_name': file_name,
                'key': key,
                's3_url': s3_url,
                'content_type': content_type,
                'size': len(file_content),
                'metadata': metadata or {}
            }
            
        except Exception as e:
            self.logger.error(f"Error uploading document to S3: {str(e)}")
            raise
    
    async def download_document(self, key: str) -> bytes:
        """
        Download document from S3
        
        Args:
            key: S3 object key
            
        Returns:
            File content bytes
        """
        try:
            response = self.s3_client.get_object(Bucket=self.bucket_name, Key=key)
            file_content = response['Body'].read()
            return file_content
        except Exception as e:
            self.logger.error(f"Error downloading document from S3: {str(e)}")
            raise
    
    def _get_extension_from_content_type(self, content_type: str) -> str:
        """Get file extension from content type"""
        content_type_map = {
            'image/jpeg': '.jpg',
            'image/png': '.png',
            'image/gif': '.gif',
            'application/pdf': '.pdf',
            'text/plain': '.txt',
            'text/csv': '.csv',
            'application/json': '.json',
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': '.xlsx',
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document': '.docx'
        }
        return content_type_map.get(content_type, '')

# Create singleton instance
s3_storage = S3Storage()