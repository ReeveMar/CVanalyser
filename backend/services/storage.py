import os
import boto3
from botocore.exceptions import ClientError
from botocore.config import Config
from typing import Optional
from dotenv import load_dotenv

load_dotenv()

AWS_ACCESS_KEY_ID = os.environ.get("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.environ.get("AWS_SECRET_ACCESS_KEY")
AWS_REGION = os.environ.get("AWS_REGION", "us-east-1")
S3_BUCKET_NAME = os.environ.get("S3_BUCKET_NAME")
AWS_ENDPOINT_URL = os.environ.get("AWS_ENDPOINT_URL")  # Optional, e.g. for MinIO or LocalStack

class S3StorageService:
    def __init__(self):
        self.bucket_name = S3_BUCKET_NAME
        # Use standard botocore config with retry logic
        boto_config = Config(
            region_name=AWS_REGION,
            retries={"max_attempts": 3, "mode": "standard"}
        )
        
        session_kwargs = {}
        if AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY:
            session_kwargs["aws_access_key_id"] = AWS_ACCESS_KEY_ID
            session_kwargs["aws_secret_access_key"] = AWS_SECRET_ACCESS_KEY
            session_kwargs["region_name"] = AWS_REGION

        if AWS_ENDPOINT_URL:
            session_kwargs["endpoint_url"] = AWS_ENDPOINT_URL

        self.s3_client = boto3.client("s3", config=boto_config, **session_kwargs)

    def is_configured(self) -> bool:
        """Check if S3 bucket name is set."""
        return bool(self.bucket_name)

    def upload_file(
        self,
        data: bytes,
        key: str,
        content_type: str = "application/octet-stream"
    ) -> str:
        """
        Upload raw bytes to S3 with Server-Side Encryption (AES256).
        Returns the object key.
        """
        if not self.bucket_name:
            raise RuntimeError("S3_BUCKET_NAME is not configured in environment variables.")

        try:
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=key,
                Body=data,
                ContentType=content_type,
                ServerSideEncryption="AES256"
            )
            return key
        except ClientError as e:
            print(f"Error uploading file to S3 ({key}): {e}")
            raise e

    def get_file_bytes(self, key: str) -> bytes:
        """
        Retrieve raw file bytes from S3.
        """
        if not self.bucket_name:
            raise RuntimeError("S3_BUCKET_NAME is not configured in environment variables.")

        try:
            response = self.s3_client.get_object(Bucket=self.bucket_name, Key=key)
            return response["Body"].read()
        except ClientError as e:
            print(f"Error reading file from S3 ({key}): {e}")
            raise e

    def get_file_stream(self, key: str):
        """
        Returns the streaming body from S3 for efficient direct streaming.
        """
        if not self.bucket_name:
            raise RuntimeError("S3_BUCKET_NAME is not configured in environment variables.")

        try:
            response = self.s3_client.get_object(Bucket=self.bucket_name, Key=key)
            return response["Body"]
        except ClientError as e:
            print(f"Error getting file stream from S3 ({key}): {e}")
            raise e

    def delete_file(self, key: str) -> bool:
        """
        Delete an object from S3.
        """
        if not self.bucket_name:
            return False

        try:
            self.s3_client.delete_object(Bucket=self.bucket_name, Key=key)
            return True
        except ClientError as e:
            print(f"Error deleting file from S3 ({key}): {e}")
            return False

    def object_exists(self, key: str) -> bool:
        """
        Check if an object exists in S3 using head_object.
        """
        if not self.bucket_name:
            return False

        try:
            self.s3_client.head_object(Bucket=self.bucket_name, Key=key)
            return True
        except ClientError:
            return False

    def generate_presigned_url(self, key: str, expires_in: int = 900) -> Optional[str]:
        """
        Generate a pre-signed URL for temporary secure access (default 15 minutes).
        """
        if not self.bucket_name:
            return None

        try:
            url = self.s3_client.generate_presigned_url(
                "get_object",
                Params={"Bucket": self.bucket_name, "Key": key},
                ExpiresIn=expires_in
            )
            return url
        except ClientError as e:
            print(f"Error generating presigned URL for {key}: {e}")
            return None


# Global singleton instance
storage_service = S3StorageService()
