"""
Advanced Webhook Service for Synthetic Data Platform
Secure webhook delivery with retry logic, authentication, and monitoring
"""

import json
import asyncio
import logging
from typing import Dict, List, Any, Optional, Tuple, Union, Callable
from dataclasses import dataclass, asdict
from enum import Enum
import time
import uuid
from datetime import datetime, timedelta
import hashlib
import hmac
import base64
import aiohttp
from aiohttp import ClientSession, ClientTimeout, ClientError
import ssl
from urllib.parse import urlparse
import secrets
import string

from app.core.config import settings
from app.core.logging import get_logger
from app.core.redis import get_redis_client

logger = get_logger(__name__)


class WebhookEventType(Enum):
    """Webhook event types"""
    GENERATION_STARTED = "generation.started"
    GENERATION_COMPLETED = "generation.completed"
    GENERATION_FAILED = "generation.failed"
    GENERATION_CANCELLED = "generation.cancelled"
    DATASET_CREATED = "dataset.created"
    DATASET_UPDATED = "dataset.updated"
    DATASET_DELETED = "dataset.deleted"
    USER_REGISTERED = "user.registered"
    USER_UPDATED = "user.updated"
    PAYMENT_SUCCEEDED = "payment.succeeded"
    PAYMENT_FAILED = "payment.failed"
    SUBSCRIPTION_CREATED = "subscription.created"
    SUBSCRIPTION_CANCELLED = "subscription.cancelled"
    CUSTOM_MODEL_UPLOADED = "custom_model.uploaded"
    CUSTOM_MODEL_DELETED = "custom_model.deleted"


class WebhookStatus(Enum):
    """Webhook delivery status"""
    PENDING = "pending"
    DELIVERING = "delivering"
    DELIVERED = "delivered"
    FAILED = "failed"
    RETRYING = "retrying"
    DISABLED = "disabled"


class RetryStrategy(Enum):
    """Retry strategies"""
    EXPONENTIAL = "exponential"
    LINEAR = "linear"
    FIXED = "fixed"
    CUSTOM = "custom"


@dataclass
class WebhookConfig:
    """Webhook configuration"""
    url: str
    secret: str
    events: List[WebhookEventType]
    retry_strategy: RetryStrategy = RetryStrategy.EXPONENTIAL
    max_retries: int = 5
    retry_delay: int = 60  # seconds
    timeout: int = 30  # seconds
    verify_ssl: bool = True
    headers: Optional[Dict[str, str]] = None
    enabled: bool = True
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class WebhookDelivery:
    """Webhook delivery record"""
    id: str
    webhook_id: str
    event_type: WebhookEventType
    payload: Dict[str, Any]
    status: WebhookStatus
    attempts: int = 0
    max_attempts: int = 5
    next_retry_at: Optional[datetime] = None
    last_attempt_at: Optional[datetime] = None
    last_response_code: Optional[int] = None
    last_response_body: Optional[str] = None
    created_at: datetime = None
    delivered_at: Optional[datetime] = None
    error_message: Optional[str] = None


@dataclass
class WebhookEvent:
    """Webhook event data"""
    event_type: WebhookEventType
    data: Dict[str, Any]
    timestamp: datetime
    user_id: Optional[int] = None
    correlation_id: Optional[str] = None


class AdvancedWebhookService:
    """
    Advanced webhook service with security, retry logic, and monitoring
    """

    def __init__(self):
        """Initialize webhook service"""
        self.webhooks: Dict[str, WebhookConfig] = {}
        self.deliveries: Dict[str, WebhookDelivery] = {}
        self.redis_client = None
        self.session: Optional[ClientSession] = None
        self._init_cache()
        
        # Retry task
        self._retry_task = None
        
        logger.info("Advanced Webhook Service initialized")

    async def _init_cache(self):
        """Initialize Redis cache"""
        try:
            self.redis_client = await get_redis_client()
        except Exception as e:
            logger.warning("Redis cache not available", error=str(e))

    async def start(self):
        """Start webhook service"""
        # Initialize HTTP session
        timeout = ClientTimeout(total=30, connect=10)
        connector = aiohttp.TCPConnector(
            limit=100,
            limit_per_host=30,
            ssl=ssl.create_default_context()
        )
        self.session = ClientSession(
            timeout=timeout,
            connector=connector,
            headers={'User-Agent': 'Synthos-Webhook/1.0'}
        )
        
        # Start retry task
        self._retry_task = asyncio.create_task(self._retry_failed_deliveries())
        
        logger.info("Webhook service started")

    async def stop(self):
        """Stop webhook service"""
        if self._retry_task:
            self._retry_task.cancel()
            try:
                await self._retry_task
            except asyncio.CancelledError:
                pass
        
        if self.session:
            await self.session.close()
        
        logger.info("Webhook service stopped")

    async def register_webhook(
        self,
        webhook_id: str,
        config: WebhookConfig
    ) -> bool:
        """Register a new webhook"""
        
        try:
            # Validate webhook URL
            if not self._validate_webhook_url(config.url):
                raise ValueError("Invalid webhook URL")
            
            # Generate secret if not provided
            if not config.secret:
                config.secret = self._generate_webhook_secret()
            
            # Store webhook configuration
            self.webhooks[webhook_id] = config
            
            # Cache in Redis
            await self._cache_webhook_config(webhook_id, config)
            
            logger.info(
                "Webhook registered successfully",
                webhook_id=webhook_id,
                url=config.url,
                events=len(config.events)
            )
            
            return True
            
        except Exception as e:
            logger.error("Failed to register webhook", error=str(e), webhook_id=webhook_id)
            return False

    async def unregister_webhook(self, webhook_id: str) -> bool:
        """Unregister a webhook"""
        
        try:
            # Remove from memory
            if webhook_id in self.webhooks:
                del self.webhooks[webhook_id]
            
            # Remove from cache
            await self._remove_cached_webhook(webhook_id)
            
            logger.info("Webhook unregistered", webhook_id=webhook_id)
            return True
            
        except Exception as e:
            logger.error("Failed to unregister webhook", error=str(e), webhook_id=webhook_id)
            return False

    async def trigger_webhook(
        self,
        event: WebhookEvent,
        webhook_id: Optional[str] = None
    ) -> List[str]:
        """Trigger webhook(s) for an event"""
        
        delivery_ids = []
        
        try:
            # Find webhooks for this event
            target_webhooks = []
            
            if webhook_id:
                # Specific webhook
                if webhook_id in self.webhooks:
                    webhook = self.webhooks[webhook_id]
                    if event.event_type in webhook.events and webhook.enabled:
                        target_webhooks.append((webhook_id, webhook))
            else:
                # All webhooks for this event
                for wid, webhook in self.webhooks.items():
                    if event.event_type in webhook.events and webhook.enabled:
                        target_webhooks.append((wid, webhook))
            
            # Create deliveries
            for webhook_id, webhook in target_webhooks:
                delivery_id = await self._create_delivery(webhook_id, event, webhook)
                delivery_ids.append(delivery_id)
                
                # Start delivery
                asyncio.create_task(self._deliver_webhook(delivery_id))
            
            logger.info(
                "Webhook triggered",
                event_type=event.event_type.value,
                webhook_count=len(target_webhooks),
                delivery_ids=delivery_ids
            )
            
        except Exception as e:
            logger.error("Failed to trigger webhook", error=str(e), event_type=event.event_type.value)
        
        return delivery_ids

    async def _create_delivery(
        self,
        webhook_id: str,
        event: WebhookEvent,
        webhook: WebhookConfig
    ) -> str:
        """Create a webhook delivery record"""
        
        delivery_id = str(uuid.uuid4())
        
        # Create payload
        payload = {
            "id": delivery_id,
            "event_type": event.event_type.value,
            "data": event.data,
            "timestamp": event.timestamp.isoformat(),
            "user_id": event.user_id,
            "correlation_id": event.correlation_id
        }
        
        # Create delivery record
        delivery = WebhookDelivery(
            id=delivery_id,
            webhook_id=webhook_id,
            event_type=event.event_type,
            payload=payload,
            status=WebhookStatus.PENDING,
            max_attempts=webhook.max_retries,
            created_at=datetime.utcnow()
        )
        
        # Store delivery
        self.deliveries[delivery_id] = delivery
        
        # Cache delivery
        await self._cache_delivery(delivery)
        
        return delivery_id

    async def _deliver_webhook(self, delivery_id: str):
        """Deliver a webhook"""
        
        delivery = self.deliveries.get(delivery_id)
        if not delivery:
            logger.error("Delivery not found", delivery_id=delivery_id)
            return
        
        webhook = self.webhooks.get(delivery.webhook_id)
        if not webhook:
            logger.error("Webhook not found", webhook_id=delivery.webhook_id)
            return
        
        try:
            # Update status
            delivery.status = WebhookStatus.DELIVERING
            delivery.attempts += 1
            delivery.last_attempt_at = datetime.utcnow()
            
            # Create signature
            signature = self._create_webhook_signature(
                delivery.payload,
                webhook.secret
            )
            
            # Prepare headers
            headers = {
                'Content-Type': 'application/json',
                'X-Webhook-Signature': signature,
                'X-Webhook-Event': delivery.event_type.value,
                'X-Webhook-Delivery': delivery_id,
                'X-Webhook-Timestamp': str(int(time.time()))
            }
            
            if webhook.headers:
                headers.update(webhook.headers)
            
            # Make request
            async with self.session.post(
                webhook.url,
                json=delivery.payload,
                headers=headers,
                ssl=webhook.verify_ssl
            ) as response:
                
                delivery.last_response_code = response.status
                delivery.last_response_body = await response.text()
                
                if 200 <= response.status < 300:
                    # Success
                    delivery.status = WebhookStatus.DELIVERED
                    delivery.delivered_at = datetime.utcnow()
                    delivery.next_retry_at = None
                    
                    logger.info(
                        "Webhook delivered successfully",
                        delivery_id=delivery_id,
                        webhook_id=delivery.webhook_id,
                        status_code=response.status
                    )
                else:
                    # Failed
                    delivery.status = WebhookStatus.FAILED
                    delivery.error_message = f"HTTP {response.status}: {delivery.last_response_body}"
                    
                    # Schedule retry if attempts remaining
                    if delivery.attempts < delivery.max_attempts:
                        await self._schedule_retry(delivery, webhook)
                    
                    logger.warning(
                        "Webhook delivery failed",
                        delivery_id=delivery_id,
                        webhook_id=delivery.webhook_id,
                        status_code=response.status,
                        attempts=delivery.attempts
                    )
                
                # Update cache
                await self._cache_delivery(delivery)
                
        except asyncio.TimeoutError:
            delivery.status = WebhookStatus.FAILED
            delivery.error_message = "Request timeout"
            
            if delivery.attempts < delivery.max_attempts:
                await self._schedule_retry(delivery, webhook)
            
            logger.warning(
                "Webhook delivery timeout",
                delivery_id=delivery_id,
                webhook_id=delivery.webhook_id,
                attempts=delivery.attempts
            )
            
        except Exception as e:
            delivery.status = WebhookStatus.FAILED
            delivery.error_message = str(e)
            
            if delivery.attempts < delivery.max_attempts:
                await self._schedule_retry(delivery, webhook)
            
            logger.error(
                "Webhook delivery error",
                delivery_id=delivery_id,
                webhook_id=delivery.webhook_id,
                error=str(e),
                attempts=delivery.attempts
            )
        
        finally:
            # Update cache
            await self._cache_delivery(delivery)

    async def _schedule_retry(self, delivery: WebhookDelivery, webhook: WebhookConfig):
        """Schedule retry for failed delivery"""
        
        # Calculate retry delay
        delay = self._calculate_retry_delay(
            delivery.attempts,
            webhook.retry_strategy,
            webhook.retry_delay
        )
        
        delivery.status = WebhookStatus.RETRYING
        delivery.next_retry_at = datetime.utcnow() + timedelta(seconds=delay)
        
        logger.info(
            "Webhook retry scheduled",
            delivery_id=delivery.id,
            webhook_id=delivery.webhook_id,
            delay_seconds=delay,
            attempt=delivery.attempts + 1
        )

    def _calculate_retry_delay(
        self,
        attempt: int,
        strategy: RetryStrategy,
        base_delay: int
    ) -> int:
        """Calculate retry delay based on strategy"""
        
        if strategy == RetryStrategy.EXPONENTIAL:
            return min(base_delay * (2 ** attempt), 3600)  # Cap at 1 hour
        elif strategy == RetryStrategy.LINEAR:
            return base_delay * attempt
        elif strategy == RetryStrategy.FIXED:
            return base_delay
        else:
            return base_delay

    async def _retry_failed_deliveries(self):
        """Background task to retry failed deliveries"""
        
        while True:
            try:
                await asyncio.sleep(60)  # Check every minute
                
                current_time = datetime.utcnow()
                retry_deliveries = [
                    delivery for delivery in self.deliveries.values()
                    if delivery.status == WebhookStatus.RETRYING
                    and delivery.next_retry_at
                    and delivery.next_retry_at <= current_time
                ]
                
                for delivery in retry_deliveries:
                    asyncio.create_task(self._deliver_webhook(delivery.id))
                
                if retry_deliveries:
                    logger.info(
                        "Retrying webhook deliveries",
                        count=len(retry_deliveries)
                    )
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("Error in retry task", error=str(e))

    def _validate_webhook_url(self, url: str) -> bool:
        """Validate webhook URL"""
        
        try:
            parsed = urlparse(url)
            return parsed.scheme in ['http', 'https'] and parsed.netloc
        except Exception:
            return False

    def _generate_webhook_secret(self) -> str:
        """Generate webhook secret"""
        
        alphabet = string.ascii_letters + string.digits
        return ''.join(secrets.choice(alphabet) for _ in range(32))

    def _create_webhook_signature(self, payload: Dict[str, Any], secret: str) -> str:
        """Create webhook signature"""
        
        payload_str = json.dumps(payload, separators=(',', ':'), sort_keys=True)
        signature = hmac.new(
            secret.encode('utf-8'),
            payload_str.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        
        return f"sha256={signature}"

    def _verify_webhook_signature(
        self,
        payload: str,
        signature: str,
        secret: str
    ) -> bool:
        """Verify webhook signature"""
        
        try:
            expected_signature = self._create_webhook_signature(
                json.loads(payload),
                secret
            )
            return hmac.compare_digest(signature, expected_signature)
        except Exception:
            return False

    async def _cache_webhook_config(self, webhook_id: str, config: WebhookConfig):
        """Cache webhook configuration"""
        
        if self.redis_client:
            try:
                cache_key = f"webhook:{webhook_id}"
                config_data = {
                    "url": config.url,
                    "secret": config.secret,
                    "events": [e.value for e in config.events],
                    "retry_strategy": config.retry_strategy.value,
                    "max_retries": config.max_retries,
                    "retry_delay": config.retry_delay,
                    "timeout": config.timeout,
                    "verify_ssl": config.verify_ssl,
                    "headers": config.headers or {},
                    "enabled": config.enabled,
                    "metadata": config.metadata or {}
                }
                await self.redis_client.setex(cache_key, 86400, json.dumps(config_data))
            except Exception as e:
                logger.warning("Failed to cache webhook config", error=str(e))

    async def _remove_cached_webhook(self, webhook_id: str):
        """Remove cached webhook"""
        
        if self.redis_client:
            try:
                await self.redis_client.delete(f"webhook:{webhook_id}")
            except Exception as e:
                logger.warning("Failed to remove cached webhook", error=str(e))

    async def _cache_delivery(self, delivery: WebhookDelivery):
        """Cache delivery record"""
        
        if self.redis_client:
            try:
                cache_key = f"delivery:{delivery.id}"
                delivery_data = {
                    "id": delivery.id,
                    "webhook_id": delivery.webhook_id,
                    "event_type": delivery.event_type.value,
                    "payload": delivery.payload,
                    "status": delivery.status.value,
                    "attempts": delivery.attempts,
                    "max_attempts": delivery.max_attempts,
                    "next_retry_at": delivery.next_retry_at.isoformat() if delivery.next_retry_at else None,
                    "last_attempt_at": delivery.last_attempt_at.isoformat() if delivery.last_attempt_at else None,
                    "last_response_code": delivery.last_response_code,
                    "last_response_body": delivery.last_response_body,
                    "created_at": delivery.created_at.isoformat(),
                    "delivered_at": delivery.delivered_at.isoformat() if delivery.delivered_at else None,
                    "error_message": delivery.error_message
                }
                await self.redis_client.setex(cache_key, 86400, json.dumps(delivery_data))
            except Exception as e:
                logger.warning("Failed to cache delivery", error=str(e))

    async def get_delivery_status(self, delivery_id: str) -> Optional[Dict[str, Any]]:
        """Get delivery status"""
        
        delivery = self.deliveries.get(delivery_id)
        if not delivery:
            return None
        
        return {
            "id": delivery.id,
            "webhook_id": delivery.webhook_id,
            "event_type": delivery.event_type.value,
            "status": delivery.status.value,
            "attempts": delivery.attempts,
            "max_attempts": delivery.max_attempts,
            "next_retry_at": delivery.next_retry_at.isoformat() if delivery.next_retry_at else None,
            "last_attempt_at": delivery.last_attempt_at.isoformat() if delivery.last_attempt_at else None,
            "last_response_code": delivery.last_response_code,
            "delivered_at": delivery.delivered_at.isoformat() if delivery.delivered_at else None,
            "error_message": delivery.error_message
        }

    async def get_webhook_stats(self, webhook_id: str) -> Dict[str, Any]:
        """Get webhook statistics"""
        
        webhook_deliveries = [
            delivery for delivery in self.deliveries.values()
            if delivery.webhook_id == webhook_id
        ]
        
        if not webhook_deliveries:
            return {"total_deliveries": 0}
        
        total_deliveries = len(webhook_deliveries)
        successful_deliveries = len([d for d in webhook_deliveries if d.status == WebhookStatus.DELIVERED])
        failed_deliveries = len([d for d in webhook_deliveries if d.status == WebhookStatus.FAILED])
        pending_deliveries = len([d for d in webhook_deliveries if d.status == WebhookStatus.PENDING])
        retrying_deliveries = len([d for d in webhook_deliveries if d.status == WebhookStatus.RETRYING])
        
        return {
            "total_deliveries": total_deliveries,
            "successful_deliveries": successful_deliveries,
            "failed_deliveries": failed_deliveries,
            "pending_deliveries": pending_deliveries,
            "retrying_deliveries": retrying_deliveries,
            "success_rate": (successful_deliveries / total_deliveries) * 100 if total_deliveries > 0 else 0,
            "average_attempts": sum(d.attempts for d in webhook_deliveries) / total_deliveries if total_deliveries > 0 else 0
        }

    async def list_webhooks(self) -> List[Dict[str, Any]]:
        """List all webhooks"""
        
        webhooks = []
        for webhook_id, config in self.webhooks.items():
            stats = await self.get_webhook_stats(webhook_id)
            webhooks.append({
                "id": webhook_id,
                "url": config.url,
                "events": [e.value for e in config.events],
                "enabled": config.enabled,
                "stats": stats
            })
        
        return webhooks

    async def test_webhook(self, webhook_id: str) -> Dict[str, Any]:
        """Test webhook delivery"""
        
        if webhook_id not in self.webhooks:
            return {"success": False, "error": "Webhook not found"}
        
        webhook = self.webhooks[webhook_id]
        
        # Create test event
        test_event = WebhookEvent(
            event_type=WebhookEventType.GENERATION_STARTED,
            data={"test": True, "message": "Webhook test"},
            timestamp=datetime.utcnow(),
            user_id=None,
            correlation_id="test"
        )
        
        # Trigger webhook
        delivery_ids = await self.trigger_webhook(test_event, webhook_id)
        
        if delivery_ids:
            return {
                "success": True,
                "delivery_id": delivery_ids[0],
                "message": "Test webhook triggered"
            }
        else:
            return {
                "success": False,
                "error": "Failed to trigger test webhook"
            }