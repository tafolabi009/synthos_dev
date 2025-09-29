"""
Advanced Storage Service for Synthetic Data Platform
Multi-provider storage with GCS, S3, and intelligent routing
"""

import os
import json
import asyncio
import logging
from typing import Dict, List, Any, Optional, Tuple, Union, BinaryIO
from dataclasses import dataclass, asdict
from enum import Enum
import time
import uuid
from datetime import datetime, timedelta
from pathlib import Path
import hashlib
import mimetypes
from io import BytesIO, StringIO
import aiofiles
import aiohttp

# Google Cloud Storage
try:
    from google.cloud import storage as gcs_storage
    from google.cloud.storage import Blob
    from google.cloud.exceptions import NotFound, GoogleCloudError
    GCS_AVAILABLE = True
except ImportError:
    GCS_AVAILABLE = False
    gcs_storage = None
    Blob = None
    NotFound = Exception
    GoogleCloudError = Exception

# AWS S3
try:
    import boto3
    from botocore.exceptions import ClientError, NoCredentialsError
    S3_AVAILABLE = True
except ImportError:
    S3_AVAILABLE = False
    boto3 = None
    ClientError = Exception
    NoCredentialsError = Exception

# Azure Blob Storage
try:
    from azure.storage.blob import BlobServiceClient, BlobClient, ContainerClient
    from azure.core.exceptions import ResourceNotFoundError, AzureError
    AZURE_AVAILABLE = True
except ImportError:
    AZURE_AVAILABLE = False
    BlobServiceClient = None
    BlobClient = None
    ContainerClient = None
    ResourceNotFoundError = Exception
    AzureError = Exception

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class StorageProvider(Enum):
    """Supported storage providers"""
    GCS = "gcs"
    S3 = "s3"
    AZURE = "azure"
    LOCAL = "local"
    HYBRID = "hybrid"


class FileType(Enum):
    """File types for storage optimization"""
    CSV = "csv"
    JSON = "json"
    PARQUET = "parquet"
    EXCEL = "excel"
    PICKLE = "pickle"
    MODEL = "model"
    IMAGE = "image"
    DOCUMENT = "document"
    ARCHIVE = "archive"


@dataclass
class StorageConfig:
    """Storage configuration"""
    provider: StorageProvider
    bucket_name: str
    region: Optional[str] = None
    credentials: Optional[Dict[str, Any]] = None
    encryption: bool = True
    compression: bool = True
    versioning: bool = True
    lifecycle_rules: Optional[Dict[str, Any]] = None


@dataclass
class StorageObject:
    """Storage object metadata"""
    key: str
    size: int
    content_type: str
    last_modified: datetime
    etag: str
    metadata: Dict[str, Any]
    provider: StorageProvider
    url: Optional[str] = None


class AdvancedStorageService:
    """
    Advanced storage service with multi-provider support
    """

    def __init__(self):
        """Initialize storage service"""
        self.providers = {}
        self.default_provider = StorageProvider.GCS
        self.redis_client = None
        
        # Initialize providers
        self._init_providers()
        self._init_cache()
        
        logger.info("Advanced Storage Service initialized")

    def _init_providers(self):
        """Initialize storage providers"""
        
        # GCS Provider
        if GCS_AVAILABLE and settings.GCP_PROJECT_ID:
            try:
                self.providers[StorageProvider.GCS] = GCSProvider(
                    project_id=settings.GCP_PROJECT_ID,
                    bucket_name=settings.GCS_BUCKET,
                    credentials=settings.GCP_CREDENTIALS
                )
                logger.info("GCS provider initialized")
            except Exception as e:
                logger.warning("Failed to initialize GCS provider", error=str(e))
        
        # S3 Provider
        if S3_AVAILABLE and settings.AWS_ACCESS_KEY_ID:
            try:
                self.providers[StorageProvider.S3] = S3Provider(
                    bucket_name=settings.AWS_S3_BUCKET,
                    region=settings.AWS_REGION,
                    access_key=settings.AWS_ACCESS_KEY_ID,
                    secret_key=settings.AWS_SECRET_ACCESS_KEY
                )
                logger.info("S3 provider initialized")
            except Exception as e:
                logger.warning("Failed to initialize S3 provider", error=str(e))
        
        # Azure Provider
        if AZURE_AVAILABLE and settings.AZURE_STORAGE_ACCOUNT:
            try:
                self.providers[StorageProvider.AZURE] = AzureProvider(
                    account_name=settings.AZURE_STORAGE_ACCOUNT,
                    account_key=settings.AZURE_STORAGE_KEY,
                    container_name=settings.AZURE_CONTAINER
                )
                logger.info("Azure provider initialized")
            except Exception as e:
                logger.warning("Failed to initialize Azure provider", error=str(e))
        
        # Local Provider (fallback)
        self.providers[StorageProvider.LOCAL] = LocalProvider(
            base_path=Path(settings.UPLOAD_PATH)
        )
        logger.info("Local provider initialized")

    async def _init_cache(self):
        """Initialize Redis cache"""
        try:
            from app.core.redis import get_redis_client
            self.redis_client = await get_redis_client()
        except Exception as e:
            logger.warning("Redis cache not available", error=str(e))

    async def upload_file(
        self,
        file_data: Union[bytes, BinaryIO, str],
        key: str,
        content_type: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        provider: Optional[StorageProvider] = None,
        file_type: Optional[FileType] = None
    ) -> StorageObject:
        """Upload file to storage"""
        
        # Determine provider
        if provider is None:
            provider = await self._select_optimal_provider(file_type, len(file_data) if isinstance(file_data, bytes) else 0)
        
        # Get provider
        storage_provider = self.providers.get(provider)
        if not storage_provider:
            raise ValueError(f"Provider {provider.value} not available")
        
        # Determine content type
        if content_type is None:
            content_type = self._detect_content_type(key, file_data)
        
        # Prepare metadata
        upload_metadata = {
            "uploaded_at": datetime.utcnow().isoformat(),
            "file_type": file_type.value if file_type else "unknown",
            "provider": provider.value
        }
        if metadata:
            upload_metadata.update(metadata)
        
        try:
            # Upload file
            storage_obj = await storage_provider.upload_file(
                file_data=file_data,
                key=key,
                content_type=content_type,
                metadata=upload_metadata
            )
            
            # Cache metadata
            await self._cache_object_metadata(storage_obj)
            
            logger.info(
                "File uploaded successfully",
                key=key,
                provider=provider.value,
                size=storage_obj.size
            )
            
            return storage_obj
            
        except Exception as e:
            logger.error("File upload failed", error=str(e), key=key, provider=provider.value)
            raise

    async def download_file(
        self,
        key: str,
        provider: Optional[StorageProvider] = None
    ) -> bytes:
        """Download file from storage"""
        
        # Determine provider
        if provider is None:
            provider = await self._get_provider_for_key(key)
        
        # Get provider
        storage_provider = self.providers.get(provider)
        if not storage_provider:
            raise ValueError(f"Provider {provider.value} not available")
        
        try:
            # Download file
            file_data = await storage_provider.download_file(key)
            
            logger.info("File downloaded successfully", key=key, provider=provider.value)
            return file_data
            
        except Exception as e:
            logger.error("File download failed", error=str(e), key=key, provider=provider.value)
            raise

    async def generate_signed_url(
        self,
        key: str,
        expiration: int = 3600,
        method: str = "GET",
        provider: Optional[StorageProvider] = None
    ) -> str:
        """Generate signed URL for file access"""
        
        # Determine provider
        if provider is None:
            provider = await self._get_provider_for_key(key)
        
        # Get provider
        storage_provider = self.providers.get(provider)
        if not storage_provider:
            raise ValueError(f"Provider {provider.value} not available")
        
        try:
            # Generate signed URL
            signed_url = await storage_provider.generate_signed_url(
                key=key,
                expiration=expiration,
                method=method
            )
            
            logger.info("Signed URL generated", key=key, provider=provider.value)
            return signed_url
            
        except Exception as e:
            logger.error("Failed to generate signed URL", error=str(e), key=key, provider=provider.value)
            raise

    async def delete_file(
        self,
        key: str,
        provider: Optional[StorageProvider] = None
    ) -> bool:
        """Delete file from storage"""
        
        # Determine provider
        if provider is None:
            provider = await self._get_provider_for_key(key)
        
        # Get provider
        storage_provider = self.providers.get(provider)
        if not storage_provider:
            raise ValueError(f"Provider {provider.value} not available")
        
        try:
            # Delete file
            success = await storage_provider.delete_file(key)
            
            if success:
                # Remove from cache
                await self._remove_cached_metadata(key)
                logger.info("File deleted successfully", key=key, provider=provider.value)
            else:
                logger.warning("File deletion failed", key=key, provider=provider.value)
            
            return success
            
        except Exception as e:
            logger.error("File deletion failed", error=str(e), key=key, provider=provider.value)
            raise

    async def list_files(
        self,
        prefix: str = "",
        provider: Optional[StorageProvider] = None,
        limit: int = 1000
    ) -> List[StorageObject]:
        """List files in storage"""
        
        # Determine provider
        if provider is None:
            provider = self.default_provider
        
        # Get provider
        storage_provider = self.providers.get(provider)
        if not storage_provider:
            raise ValueError(f"Provider {provider.value} not available")
        
        try:
            # List files
            files = await storage_provider.list_files(prefix=prefix, limit=limit)
            
            logger.info("Files listed successfully", prefix=prefix, count=len(files), provider=provider.value)
            return files
            
        except Exception as e:
            logger.error("Failed to list files", error=str(e), prefix=prefix, provider=provider.value)
            raise

    async def get_file_metadata(
        self,
        key: str,
        provider: Optional[StorageProvider] = None
    ) -> Optional[StorageObject]:
        """Get file metadata"""
        
        # Check cache first
        cached_metadata = await self._get_cached_metadata(key)
        if cached_metadata:
            return cached_metadata
        
        # Determine provider
        if provider is None:
            provider = await self._get_provider_for_key(key)
        
        # Get provider
        storage_provider = self.providers.get(provider)
        if not storage_provider:
            raise ValueError(f"Provider {provider.value} not available")
        
        try:
            # Get metadata
            metadata = await storage_provider.get_file_metadata(key)
            
            if metadata:
                # Cache metadata
                await self._cache_object_metadata(metadata)
            
            return metadata
            
        except Exception as e:
            logger.error("Failed to get file metadata", error=str(e), key=key, provider=provider.value)
            return None

    async def _select_optimal_provider(
        self,
        file_type: Optional[FileType],
        file_size: int
    ) -> StorageProvider:
        """Select optimal storage provider based on file characteristics"""
        
        # Check provider availability
        available_providers = [p for p in self.providers.keys() if p != StorageProvider.LOCAL]
        
        if not available_providers:
            return StorageProvider.LOCAL
        
        # Provider selection logic
        if file_type == FileType.MODEL and StorageProvider.GCS in available_providers:
            return StorageProvider.GCS  # GCS is good for ML models
        elif file_type in [FileType.CSV, FileType.JSON] and file_size > 100 * 1024 * 1024:  # > 100MB
            if StorageProvider.S3 in available_providers:
                return StorageProvider.S3  # S3 is good for large files
            elif StorageProvider.GCS in available_providers:
                return StorageProvider.GCS
        elif StorageProvider.GCS in available_providers:
            return StorageProvider.GCS  # Default to GCS
        elif StorageProvider.S3 in available_providers:
            return StorageProvider.S3
        else:
            return StorageProvider.LOCAL

    async def _get_provider_for_key(self, key: str) -> StorageProvider:
        """Get provider for a specific key"""
        
        # Check cache for provider info
        if self.redis_client:
            try:
                cached_provider = await self.redis_client.get(f"provider:{key}")
                if cached_provider:
                    return StorageProvider(cached_provider.decode())
            except Exception as e:
                logger.warning("Failed to get cached provider", error=str(e))
        
        # Try to find provider by checking each one
        for provider, storage_provider in self.providers.items():
            try:
                if await storage_provider.file_exists(key):
                    # Cache provider info
                    if self.redis_client:
                        try:
                            await self.redis_client.setex(f"provider:{key}", 3600, provider.value)
                        except Exception as e:
                            logger.warning("Failed to cache provider", error=str(e))
                    return provider
            except Exception:
                continue
        
        # Default to local if not found
        return StorageProvider.LOCAL

    def _detect_content_type(self, key: str, file_data: Union[bytes, BinaryIO, str]) -> str:
        """Detect content type from key and data"""
        
        # Try to detect from file extension
        content_type, _ = mimetypes.guess_type(key)
        if content_type:
            return content_type
        
        # Detect from data if it's bytes
        if isinstance(file_data, bytes):
            if file_data.startswith(b'\x89PNG'):
                return 'image/png'
            elif file_data.startswith(b'\xff\xd8\xff'):
                return 'image/jpeg'
            elif file_data.startswith(b'PK'):
                return 'application/zip'
            elif file_data.startswith(b'%PDF'):
                return 'application/pdf'
        
        # Default content types
        if key.endswith('.csv'):
            return 'text/csv'
        elif key.endswith('.json'):
            return 'application/json'
        elif key.endswith('.parquet'):
            return 'application/octet-stream'
        elif key.endswith('.pkl'):
            return 'application/octet-stream'
        else:
            return 'application/octet-stream'

    async def _cache_object_metadata(self, storage_obj: StorageObject):
        """Cache object metadata"""
        
        if self.redis_client:
            try:
                cache_key = f"metadata:{storage_obj.key}"
                metadata_data = {
                    "key": storage_obj.key,
                    "size": storage_obj.size,
                    "content_type": storage_obj.content_type,
                    "last_modified": storage_obj.last_modified.isoformat(),
                    "etag": storage_obj.etag,
                    "metadata": storage_obj.metadata,
                    "provider": storage_obj.provider.value,
                    "url": storage_obj.url
                }
                await self.redis_client.setex(cache_key, 3600, json.dumps(metadata_data))
            except Exception as e:
                logger.warning("Failed to cache metadata", error=str(e))

    async def _get_cached_metadata(self, key: str) -> Optional[StorageObject]:
        """Get cached object metadata"""
        
        if self.redis_client:
            try:
                cache_key = f"metadata:{key}"
                cached_data = await self.redis_client.get(cache_key)
                if cached_data:
                    data = json.loads(cached_data)
                    return StorageObject(
                        key=data["key"],
                        size=data["size"],
                        content_type=data["content_type"],
                        last_modified=datetime.fromisoformat(data["last_modified"]),
                        etag=data["etag"],
                        metadata=data["metadata"],
                        provider=StorageProvider(data["provider"]),
                        url=data.get("url")
                    )
            except Exception as e:
                logger.warning("Failed to get cached metadata", error=str(e))
        
        return None

    async def _remove_cached_metadata(self, key: str):
        """Remove cached metadata"""
        
        if self.redis_client:
            try:
                await self.redis_client.delete(f"metadata:{key}")
                await self.redis_client.delete(f"provider:{key}")
            except Exception as e:
                logger.warning("Failed to remove cached metadata", error=str(e))

    async def get_storage_stats(self) -> Dict[str, Any]:
        """Get storage statistics"""
        
        stats = {
            "providers": {},
            "total_files": 0,
            "total_size": 0,
            "last_updated": datetime.utcnow().isoformat()
        }
        
        for provider_name, provider in self.providers.items():
            try:
                provider_stats = await provider.get_stats()
                stats["providers"][provider_name.value] = provider_stats
                stats["total_files"] += provider_stats.get("file_count", 0)
                stats["total_size"] += provider_stats.get("total_size", 0)
            except Exception as e:
                logger.warning(f"Failed to get stats for {provider_name.value}", error=str(e))
        
        return stats


# Storage Provider Implementations

class BaseStorageProvider:
    """Base storage provider interface"""
    
    async def upload_file(self, file_data: Union[bytes, BinaryIO, str], key: str, content_type: str, metadata: Dict[str, Any]) -> StorageObject:
        raise NotImplementedError
    
    async def download_file(self, key: str) -> bytes:
        raise NotImplementedError
    
    async def delete_file(self, key: str) -> bool:
        raise NotImplementedError
    
    async def list_files(self, prefix: str = "", limit: int = 1000) -> List[StorageObject]:
        raise NotImplementedError
    
    async def get_file_metadata(self, key: str) -> Optional[StorageObject]:
        raise NotImplementedError
    
    async def generate_signed_url(self, key: str, expiration: int, method: str) -> str:
        raise NotImplementedError
    
    async def file_exists(self, key: str) -> bool:
        raise NotImplementedError
    
    async def get_stats(self) -> Dict[str, Any]:
        raise NotImplementedError


class GCSProvider(BaseStorageProvider):
    """Google Cloud Storage provider"""
    
    def __init__(self, project_id: str, bucket_name: str, credentials: Optional[Dict[str, Any]] = None):
        self.project_id = project_id
        self.bucket_name = bucket_name
        self.client = gcs_storage.Client(project=project_id, credentials=credentials)
        self.bucket = self.client.bucket(bucket_name)
    
    async def upload_file(self, file_data: Union[bytes, BinaryIO, str], key: str, content_type: str, metadata: Dict[str, Any]) -> StorageObject:
        blob = self.bucket.blob(key)
        blob.content_type = content_type
        blob.metadata = metadata
        
        if isinstance(file_data, str):
            file_data = file_data.encode('utf-8')
        
        blob.upload_from_string(file_data)
        
        return StorageObject(
            key=key,
            size=blob.size,
            content_type=blob.content_type,
            last_modified=blob.time_created,
            etag=blob.etag,
            metadata=blob.metadata or {},
            provider=StorageProvider.GCS,
            url=blob.public_url
        )
    
    async def download_file(self, key: str) -> bytes:
        blob = self.bucket.blob(key)
        return blob.download_as_bytes()
    
    async def delete_file(self, key: str) -> bool:
        try:
            blob = self.bucket.blob(key)
            blob.delete()
            return True
        except NotFound:
            return False
    
    async def list_files(self, prefix: str = "", limit: int = 1000) -> List[StorageObject]:
        blobs = self.bucket.list_blobs(prefix=prefix, max_results=limit)
        
        files = []
        for blob in blobs:
            files.append(StorageObject(
                key=blob.name,
                size=blob.size,
                content_type=blob.content_type,
                last_modified=blob.time_created,
                etag=blob.etag,
                metadata=blob.metadata or {},
                provider=StorageProvider.GCS,
                url=blob.public_url
            ))
        
        return files
    
    async def get_file_metadata(self, key: str) -> Optional[StorageObject]:
        try:
            blob = self.bucket.blob(key)
            blob.reload()
            
            return StorageObject(
                key=blob.name,
                size=blob.size,
                content_type=blob.content_type,
                last_modified=blob.time_created,
                etag=blob.etag,
                metadata=blob.metadata or {},
                provider=StorageProvider.GCS,
                url=blob.public_url
            )
        except NotFound:
            return None
    
    async def generate_signed_url(self, key: str, expiration: int, method: str) -> str:
        blob = self.bucket.blob(key)
        return blob.generate_signed_url(expiration=timedelta(seconds=expiration), method=method)
    
    async def file_exists(self, key: str) -> bool:
        try:
            blob = self.bucket.blob(key)
            return blob.exists()
        except Exception:
            return False
    
    async def get_stats(self) -> Dict[str, Any]:
        try:
            blobs = list(self.bucket.list_blobs())
            total_size = sum(blob.size for blob in blobs)
            return {
                "file_count": len(blobs),
                "total_size": total_size,
                "bucket_name": self.bucket_name
            }
        except Exception:
            return {"file_count": 0, "total_size": 0, "bucket_name": self.bucket_name}


class S3Provider(BaseStorageProvider):
    """AWS S3 provider"""
    
    def __init__(self, bucket_name: str, region: str, access_key: str, secret_key: str):
        self.bucket_name = bucket_name
        self.region = region
        self.client = boto3.client(
            's3',
            region_name=region,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key
        )
    
    async def upload_file(self, file_data: Union[bytes, BinaryIO, str], key: str, content_type: str, metadata: Dict[str, Any]) -> StorageObject:
        if isinstance(file_data, str):
            file_data = file_data.encode('utf-8')
        
        self.client.put_object(
            Bucket=self.bucket_name,
            Key=key,
            Body=file_data,
            ContentType=content_type,
            Metadata=metadata
        )
        
        # Get object metadata
        response = self.client.head_object(Bucket=self.bucket_name, Key=key)
        
        return StorageObject(
            key=key,
            size=response['ContentLength'],
            content_type=response['ContentType'],
            last_modified=response['LastModified'],
            etag=response['ETag'].strip('"'),
            metadata=response.get('Metadata', {}),
            provider=StorageProvider.S3
        )
    
    async def download_file(self, key: str) -> bytes:
        response = self.client.get_object(Bucket=self.bucket_name, Key=key)
        return response['Body'].read()
    
    async def delete_file(self, key: str) -> bool:
        try:
            self.client.delete_object(Bucket=self.bucket_name, Key=key)
            return True
        except ClientError:
            return False
    
    async def list_files(self, prefix: str = "", limit: int = 1000) -> List[StorageObject]:
        response = self.client.list_objects_v2(
            Bucket=self.bucket_name,
            Prefix=prefix,
            MaxKeys=limit
        )
        
        files = []
        for obj in response.get('Contents', []):
            files.append(StorageObject(
                key=obj['Key'],
                size=obj['Size'],
                content_type='application/octet-stream',  # S3 doesn't always provide this
                last_modified=obj['LastModified'],
                etag=obj['ETag'].strip('"'),
                metadata={},
                provider=StorageProvider.S3
            ))
        
        return files
    
    async def get_file_metadata(self, key: str) -> Optional[StorageObject]:
        try:
            response = self.client.head_object(Bucket=self.bucket_name, Key=key)
            return StorageObject(
                key=key,
                size=response['ContentLength'],
                content_type=response['ContentType'],
                last_modified=response['LastModified'],
                etag=response['ETag'].strip('"'),
                metadata=response.get('Metadata', {}),
                provider=StorageProvider.S3
            )
        except ClientError:
            return None
    
    async def generate_signed_url(self, key: str, expiration: int, method: str) -> str:
        return self.client.generate_presigned_url(
            'get_object',
            Params={'Bucket': self.bucket_name, 'Key': key},
            ExpiresIn=expiration
        )
    
    async def file_exists(self, key: str) -> bool:
        try:
            self.client.head_object(Bucket=self.bucket_name, Key=key)
            return True
        except ClientError:
            return False
    
    async def get_stats(self) -> Dict[str, Any]:
        try:
            response = self.client.list_objects_v2(Bucket=self.bucket_name)
            total_size = sum(obj['Size'] for obj in response.get('Contents', []))
            return {
                "file_count": len(response.get('Contents', [])),
                "total_size": total_size,
                "bucket_name": self.bucket_name
            }
        except Exception:
            return {"file_count": 0, "total_size": 0, "bucket_name": self.bucket_name}


class LocalProvider(BaseStorageProvider):
    """Local filesystem provider"""
    
    def __init__(self, base_path: Path):
        self.base_path = base_path
        self.base_path.mkdir(parents=True, exist_ok=True)
    
    async def upload_file(self, file_data: Union[bytes, BinaryIO, str], key: str, content_type: str, metadata: Dict[str, Any]) -> StorageObject:
        file_path = self.base_path / key
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        if isinstance(file_data, str):
            file_data = file_data.encode('utf-8')
        
        with open(file_path, 'wb') as f:
            f.write(file_data)
        
        stat = file_path.stat()
        
        return StorageObject(
            key=key,
            size=stat.st_size,
            content_type=content_type,
            last_modified=datetime.fromtimestamp(stat.st_mtime),
            etag=hashlib.md5(file_data).hexdigest(),
            metadata=metadata,
            provider=StorageProvider.LOCAL,
            url=f"file://{file_path.absolute()}"
        )
    
    async def download_file(self, key: str) -> bytes:
        file_path = self.base_path / key
        with open(file_path, 'rb') as f:
            return f.read()
    
    async def delete_file(self, key: str) -> bool:
        try:
            file_path = self.base_path / key
            file_path.unlink()
            return True
        except FileNotFoundError:
            return False
    
    async def list_files(self, prefix: str = "", limit: int = 1000) -> List[StorageObject]:
        files = []
        count = 0
        
        for file_path in self.base_path.rglob("*"):
            if file_path.is_file():
                relative_path = file_path.relative_to(self.base_path)
                if str(relative_path).startswith(prefix):
                    if count >= limit:
                        break
                    
                    stat = file_path.stat()
                    files.append(StorageObject(
                        key=str(relative_path),
                        size=stat.st_size,
                        content_type='application/octet-stream',
                        last_modified=datetime.fromtimestamp(stat.st_mtime),
                        etag=hashlib.md5(file_path.read_bytes()).hexdigest(),
                        metadata={},
                        provider=StorageProvider.LOCAL,
                        url=f"file://{file_path.absolute()}"
                    ))
                    count += 1
        
        return files
    
    async def get_file_metadata(self, key: str) -> Optional[StorageObject]:
        try:
            file_path = self.base_path / key
            if not file_path.exists():
                return None
            
            stat = file_path.stat()
            return StorageObject(
                key=key,
                size=stat.st_size,
                content_type='application/octet-stream',
                last_modified=datetime.fromtimestamp(stat.st_mtime),
                etag=hashlib.md5(file_path.read_bytes()).hexdigest(),
                metadata={},
                provider=StorageProvider.LOCAL,
                url=f"file://{file_path.absolute()}"
            )
        except Exception:
            return None
    
    async def generate_signed_url(self, key: str, expiration: int, method: str) -> str:
        file_path = self.base_path / key
        return f"file://{file_path.absolute()}"
    
    async def file_exists(self, key: str) -> bool:
        file_path = self.base_path / key
        return file_path.exists()
    
    async def get_stats(self) -> Dict[str, Any]:
        total_size = 0
        file_count = 0
        
        for file_path in self.base_path.rglob("*"):
            if file_path.is_file():
                total_size += file_path.stat().st_size
                file_count += 1
        
        return {
            "file_count": file_count,
            "total_size": total_size,
            "base_path": str(self.base_path)
        }