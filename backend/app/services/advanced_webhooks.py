"""
Advanced Webhooks Service for Synthos
Enterprise-grade webhook system with retry logic, security, and monitoring
"""

import asyncio
import json
import hmac
import hashlib
import time
import uuid
from typing import Dict, List, Any, Optional, Callable, Union
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from enum import Enum
import logging
import aiohttp
from aiohttp import ClientSession, ClientTimeout
import aiofiles

from app.core.config import settings
from app.core.logging import get_logger
from app.core.redis import get_redis_client

logger = get_logger(__name__)


class WebhookStatus(Enum):
    """Webhook delivery status"""
    PENDING = "pending"
    DELIVERED = "delivered"
    FAILED = "failed"
    RETRYING = "retrying"
    EXPIRED = "expired"


class WebhookEvent(Enum):
    """Supported webhook events"""
    GENERATION_STARTED = "generation.started"
    GENERATION_COMPLETED = "generation.completed"
    GENERATION_FAILED = "generation.failed"
    USER_SIGNED_UP = "user.signed_up"
    USER_SUBSCRIPTION_CHANGED = "user.subscription_changed"
    PAYMENT_SUCCEEDED = "payment.succeeded"
    PAYMENT_FAILED = "payment.failed"
    CUSTOM_MODEL_UPLOADED = "custom_model.uploaded"
    CUSTOM_MODEL_VALIDATED = "custom_model.validated"
    DATASET_CREATED = "dataset.created"
    DATASET_DELETED = "dataset.deleted"
    SYSTEM_ALERT = "system.alert"


class RetryStrategy(Enum):
    """Webhook retry strategies"""
    EXPONENTIAL_BACKOFF = "exponential_backoff"
    LINEAR_BACKOFF = "linear_backoff"
    FIXED_INTERVAL = "fixed_interval"
    IMMEDIATE = "immediate"


@dataclass
class WebhookEndpoint:
    """Webhook endpoint configuration"""
    id: str
    url: str
    events: List[WebhookEvent]
    secret: str
    active: bool = True
    retry_strategy: RetryStrategy = RetryStrategy.EXPONENTIAL_BACKOFF
    max_retries: int = 5
    timeout_seconds: int = 30
    headers: Dict[str, str] = None
    created_at: datetime = None
    updated_at: datetime = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.utcnow()
        if self.updated_at is None:
            self.updated_at = datetime.utcnow()
        if self.headers is None:
            self.headers = {}


@dataclass
class WebhookDelivery:
    """Webhook delivery attempt"""
    id: str
    endpoint_id: str
    event: WebhookEvent
    payload: Dict[str, Any]
    status: WebhookStatus
    attempt_number: int
    created_at: datetime
    delivered_at: Optional[datetime] = None
    failed_at: Optional[datetime] = None
    response_status: Optional[int] = None
    response_body: Optional[str] = None
    error_message: Optional[str] = None
    next_retry_at: Optional[datetime] = None


@dataclass
class WebhookMetrics:
    """Webhook performance metrics"""
    total_deliveries: int
    successful_deliveries: int
    failed_deliveries: int
    avg_delivery_time_ms: float
    success_rate: float
    retry_rate: float


class AdvancedWebhookService:
    """Advanced webhook service with enterprise features"""
    
    def __init__(self):
        self.endpoints: Dict[str, WebhookEndpoint] = {}
        self.deliveries: Dict[str, WebhookDelivery] = {}
        self.metrics: Dict[str, WebhookMetrics] = {}
        self.retry_queue = asyncio.Queue()
        self.session: Optional[ClientSession] = None
        
        # Initialize Redis client
        self.redis_client = None
        
        # Start background tasks
        asyncio.create_task(self._initialize_service())
    
    async def _initialize_service(self):
        """Initialize webhook service"""
        self.redis_client = await get_redis_client()
        
        # Load existing endpoints
        await self._load_endpoints()
        
        # Start retry processor
        asyncio.create_task(self._process_retry_queue())
        
        # Start metrics collector
        asyncio.create_task(self._collect_metrics())
        
        logger.info("Advanced webhook service initialized")
    
    async def create_endpoint(
        self,
        url: str,
        events: List[WebhookEvent],
        secret: str,
        retry_strategy: RetryStrategy = RetryStrategy.EXPONENTIAL_BACKOFF,
        max_retries: int = 5,
        timeout_seconds: int = 30,
        headers: Dict[str, str] = None
    ) -> WebhookEndpoint:
        """Create a new webhook endpoint"""
        
        endpoint_id = str(uuid.uuid4())
        
        endpoint = WebhookEndpoint(
            id=endpoint_id,
            url=url,
            events=events,
            secret=secret,
            retry_strategy=retry_strategy,
            max_retries=max_retries,
            timeout_seconds=timeout_seconds,
            headers=headers or {}
        )
        
        # Store endpoint
        self.endpoints[endpoint_id] = endpoint
        await self._save_endpoint(endpoint)
        
        logger.info(f"Created webhook endpoint: {endpoint_id}")
        
        return endpoint
    
    async def update_endpoint(
        self,
        endpoint_id: str,
        **updates
    ) -> WebhookEndpoint:
        """Update webhook endpoint"""
        
        if endpoint_id not in self.endpoints:
            raise ValueError(f"Endpoint not found: {endpoint_id}")
        
        endpoint = self.endpoints[endpoint_id]
        
        # Update fields
        for key, value in updates.items():
            if hasattr(endpoint, key):
                setattr(endpoint, key, value)
        
        endpoint.updated_at = datetime.utcnow()
        
        # Save updated endpoint
        await self._save_endpoint(endpoint)
        
        logger.info(f"Updated webhook endpoint: {endpoint_id}")
        
        return endpoint
    
    async def delete_endpoint(self, endpoint_id: str) -> bool:
        """Delete webhook endpoint"""
        
        if endpoint_id not in self.endpoints:
            return False
        
        # Remove from memory
        del self.endpoints[endpoint_id]
        
        # Remove from storage
        await self._delete_endpoint(endpoint_id)
        
        logger.info(f"Deleted webhook endpoint: {endpoint_id}")
        
        return True
    
    async def trigger_webhook(
        self,
        event: WebhookEvent,
        payload: Dict[str, Any],
        endpoint_id: str = None
    ) -> List[WebhookDelivery]:
        """Trigger webhook for an event"""
        
        deliveries = []
        
        # Find endpoints for this event
        target_endpoints = []
        if endpoint_id:
            if endpoint_id in self.endpoints:
                target_endpoints = [self.endpoints[endpoint_id]]
        else:
            target_endpoints = [
                endpoint for endpoint in self.endpoints.values()
                if event in endpoint.events and endpoint.active
            ]
        
        # Create deliveries for each endpoint
        for endpoint in target_endpoints:
            delivery = await self._create_delivery(endpoint, event, payload)
            deliveries.append(delivery)
            
            # Attempt immediate delivery
            await self._attempt_delivery(delivery)
        
        return deliveries
    
    async def _create_delivery(
        self,
        endpoint: WebhookEndpoint,
        event: WebhookEvent,
        payload: Dict[str, Any]
    ) -> WebhookDelivery:
        """Create a new webhook delivery"""
        
        delivery_id = str(uuid.uuid4())
        
        delivery = WebhookDelivery(
            id=delivery_id,
            endpoint_id=endpoint.id,
            event=event,
            payload=payload,
            status=WebhookStatus.PENDING,
            attempt_number=0,
            created_at=datetime.utcnow()
        )
        
        # Store delivery
        self.deliveries[delivery_id] = delivery
        await self._save_delivery(delivery)
        
        return delivery
    
    async def _attempt_delivery(self, delivery: WebhookDelivery) -> bool:
        """Attempt to deliver webhook"""
        
        endpoint = self.endpoints[delivery.endpoint_id]
        delivery.attempt_number += 1
        
        try:
            # Create HTTP session if needed
            if not self.session:
                timeout = ClientTimeout(total=endpoint.timeout_seconds)
                self.session = ClientSession(timeout=timeout)
            
            # Prepare headers
            headers = endpoint.headers.copy()
            headers.update({
                "Content-Type": "application/json",
                "User-Agent": "Synthos-Webhooks/1.0",
                "X-Webhook-Event": delivery.event.value,
                "X-Webhook-Delivery": delivery.id,
                "X-Webhook-Timestamp": str(int(time.time()))
            })
            
            # Generate signature
            signature = self._generate_signature(
                delivery.payload, endpoint.secret
            )
            headers["X-Webhook-Signature"] = signature
            
            # Make request
            async with self.session.post(
                endpoint.url,
                json=delivery.payload,
                headers=headers
            ) as response:
                
                delivery.response_status = response.status
                delivery.response_body = await response.text()
                
                if 200 <= response.status < 300:
                    # Success
                    delivery.status = WebhookStatus.DELIVERED
                    delivery.delivered_at = datetime.utcnow()
                    
                    logger.info(f"Webhook delivered successfully: {delivery.id}")
                    
                    # Update metrics
                    await self._update_delivery_metrics(endpoint.id, True)
                    
                    return True
                else:
                    # HTTP error
                    delivery.status = WebhookStatus.FAILED
                    delivery.failed_at = datetime.utcnow()
                    delivery.error_message = f"HTTP {response.status}: {delivery.response_body}"
                    
                    logger.warning(f"Webhook delivery failed: {delivery.id} - {delivery.error_message}")
                    
                    # Schedule retry if within limits
                    if delivery.attempt_number < endpoint.max_retries:
                        await self._schedule_retry(delivery, endpoint)
                    
                    # Update metrics
                    await self._update_delivery_metrics(endpoint.id, False)
                    
                    return False
        
        except asyncio.TimeoutError:
            delivery.status = WebhookStatus.FAILED
            delivery.failed_at = datetime.utcnow()
            delivery.error_message = "Request timeout"
            
            logger.warning(f"Webhook delivery timeout: {delivery.id}")
            
            # Schedule retry if within limits
            if delivery.attempt_number < endpoint.max_retries:
                await self._schedule_retry(delivery, endpoint)
            
            return False
        
        except Exception as e:
            delivery.status = WebhookStatus.FAILED
            delivery.failed_at = datetime.utcnow()
            delivery.error_message = str(e)
            
            logger.error(f"Webhook delivery error: {delivery.id} - {e}")
            
            # Schedule retry if within limits
            if delivery.attempt_number < endpoint.max_retries:
                await self._schedule_retry(delivery, endpoint)
            
            return False
        
        finally:
            # Save delivery state
            await self._save_delivery(delivery)
    
    async def _schedule_retry(self, delivery: WebhookDelivery, endpoint: WebhookEndpoint):
        """Schedule retry for failed delivery"""
        
        # Calculate retry delay based on strategy
        delay_seconds = self._calculate_retry_delay(
            delivery.attempt_number, endpoint.retry_strategy
        )
        
        delivery.next_retry_at = datetime.utcnow() + timedelta(seconds=delay_seconds)
        delivery.status = WebhookStatus.RETRYING
        
        # Add to retry queue
        await self.retry_queue.put((delivery.id, delivery.next_retry_at))
        
        logger.info(f"Scheduled retry for delivery {delivery.id} in {delay_seconds} seconds")
    
    def _calculate_retry_delay(
        self,
        attempt_number: int,
        strategy: RetryStrategy
    ) -> int:
        """Calculate retry delay based on strategy"""
        
        if strategy == RetryStrategy.IMMEDIATE:
            return 0
        elif strategy == RetryStrategy.FIXED_INTERVAL:
            return 60  # 1 minute
        elif strategy == RetryStrategy.LINEAR_BACKOFF:
            return min(attempt_number * 60, 3600)  # Max 1 hour
        elif strategy == RetryStrategy.EXPONENTIAL_BACKOFF:
            return min(2 ** attempt_number * 60, 3600)  # Max 1 hour
        else:
            return 60
    
    async def _process_retry_queue(self):
        """Process retry queue for failed deliveries"""
        
        while True:
            try:
                # Get next retry
                delivery_id, retry_at = await self.retry_queue.get()
                
                # Wait until retry time
                now = datetime.utcnow()
                if retry_at > now:
                    await asyncio.sleep((retry_at - now).total_seconds())
                
                # Get delivery
                if delivery_id in self.deliveries:
                    delivery = self.deliveries[delivery_id]
                    endpoint = self.endpoints[delivery.endpoint_id]
                    
                    # Attempt delivery
                    await self._attempt_delivery(delivery)
                
            except Exception as e:
                logger.error(f"Error processing retry queue: {e}")
                await asyncio.sleep(60)  # Wait before retrying
    
    async def _collect_metrics(self):
        """Collect webhook metrics"""
        
        while True:
            try:
                # Calculate metrics for each endpoint
                for endpoint_id in self.endpoints:
                    metrics = await self._calculate_endpoint_metrics(endpoint_id)
                    self.metrics[endpoint_id] = metrics
                
                # Save metrics
                await self._save_metrics()
                
                # Wait before next collection
                await asyncio.sleep(300)  # 5 minutes
                
            except Exception as e:
                logger.error(f"Error collecting metrics: {e}")
                await asyncio.sleep(60)
    
    async def _calculate_endpoint_metrics(self, endpoint_id: str) -> WebhookMetrics:
        """Calculate metrics for an endpoint"""
        
        # Get deliveries for this endpoint
        deliveries = [
            delivery for delivery in self.deliveries.values()
            if delivery.endpoint_id == endpoint_id
        ]
        
        total_deliveries = len(deliveries)
        successful_deliveries = len([
            d for d in deliveries if d.status == WebhookStatus.DELIVERED
        ])
        failed_deliveries = len([
            d for d in deliveries if d.status == WebhookStatus.FAILED
        ])
        
        # Calculate average delivery time
        delivered_deliveries = [
            d for d in deliveries 
            if d.status == WebhookStatus.DELIVERED and d.delivered_at
        ]
        
        if delivered_deliveries:
            total_time = sum([
                (d.delivered_at - d.created_at).total_seconds() * 1000
                for d in delivered_deliveries
            ])
            avg_delivery_time_ms = total_time / len(delivered_deliveries)
        else:
            avg_delivery_time_ms = 0.0
        
        # Calculate rates
        success_rate = (successful_deliveries / total_deliveries) if total_deliveries > 0 else 0.0
        retry_rate = len([
            d for d in deliveries if d.attempt_number > 1
        ]) / total_deliveries if total_deliveries > 0 else 0.0
        
        return WebhookMetrics(
            total_deliveries=total_deliveries,
            successful_deliveries=successful_deliveries,
            failed_deliveries=failed_deliveries,
            avg_delivery_time_ms=avg_delivery_time_ms,
            success_rate=success_rate,
            retry_rate=retry_rate
        )
    
    def _generate_signature(self, payload: Dict[str, Any], secret: str) -> str:
        """Generate webhook signature for security"""
        
        payload_str = json.dumps(payload, sort_keys=True)
        signature = hmac.new(
            secret.encode(),
            payload_str.encode(),
            hashlib.sha256
        ).hexdigest()
        
        return f"sha256={signature}"
    
    def verify_signature(self, payload: str, signature: str, secret: str) -> bool:
        """Verify webhook signature"""
        
        expected_signature = hmac.new(
            secret.encode(),
            payload.encode(),
            hashlib.sha256
        ).hexdigest()
        
        provided_signature = signature.replace("sha256=", "")
        
        return hmac.compare_digest(expected_signature, provided_signature)
    
    async def get_endpoint_metrics(self, endpoint_id: str) -> Optional[WebhookMetrics]:
        """Get metrics for a specific endpoint"""
        
        return self.metrics.get(endpoint_id)
    
    async def get_all_metrics(self) -> Dict[str, WebhookMetrics]:
        """Get metrics for all endpoints"""
        
        return self.metrics
    
    async def get_delivery_status(self, delivery_id: str) -> Optional[WebhookDelivery]:
        """Get delivery status"""
        
        return self.deliveries.get(delivery_id)
    
    async def get_endpoint_deliveries(
        self,
        endpoint_id: str,
        limit: int = 100,
        status: WebhookStatus = None
    ) -> List[WebhookDelivery]:
        """Get deliveries for an endpoint"""
        
        deliveries = [
            delivery for delivery in self.deliveries.values()
            if delivery.endpoint_id == endpoint_id
        ]
        
        if status:
            deliveries = [d for d in deliveries if d.status == status]
        
        # Sort by creation time (newest first)
        deliveries.sort(key=lambda x: x.created_at, reverse=True)
        
        return deliveries[:limit]
    
    async def _save_endpoint(self, endpoint: WebhookEndpoint):
        """Save endpoint to storage"""
        
        if self.redis_client:
            key = f"webhook_endpoint:{endpoint.id}"
            await self.redis_client.setex(
                key,
                86400 * 30,  # 30 days
                json.dumps(asdict(endpoint), default=str)
            )
    
    async def _load_endpoints(self):
        """Load endpoints from storage"""
        
        if not self.redis_client:
            return
        
        # Get all endpoint keys
        keys = await self.redis_client.keys("webhook_endpoint:*")
        
        for key in keys:
            try:
                endpoint_data = await self.redis_client.get(key)
                if endpoint_data:
                    endpoint_dict = json.loads(endpoint_data)
                    
                    # Convert back to WebhookEndpoint
                    endpoint = WebhookEndpoint(
                        id=endpoint_dict["id"],
                        url=endpoint_dict["url"],
                        events=[WebhookEvent(e) for e in endpoint_dict["events"]],
                        secret=endpoint_dict["secret"],
                        active=endpoint_dict["active"],
                        retry_strategy=RetryStrategy(endpoint_dict["retry_strategy"]),
                        max_retries=endpoint_dict["max_retries"],
                        timeout_seconds=endpoint_dict["timeout_seconds"],
                        headers=endpoint_dict.get("headers", {}),
                        created_at=datetime.fromisoformat(endpoint_dict["created_at"]),
                        updated_at=datetime.fromisoformat(endpoint_dict["updated_at"])
                    )
                    
                    self.endpoints[endpoint.id] = endpoint
                    
            except Exception as e:
                logger.error(f"Error loading endpoint {key}: {e}")
    
    async def _delete_endpoint(self, endpoint_id: str):
        """Delete endpoint from storage"""
        
        if self.redis_client:
            key = f"webhook_endpoint:{endpoint_id}"
            await self.redis_client.delete(key)
    
    async def _save_delivery(self, delivery: WebhookDelivery):
        """Save delivery to storage"""
        
        if self.redis_client:
            key = f"webhook_delivery:{delivery.id}"
            await self.redis_client.setex(
                key,
                86400 * 7,  # 7 days
                json.dumps(asdict(delivery), default=str)
            )
    
    async def _update_delivery_metrics(self, endpoint_id: str, success: bool):
        """Update delivery metrics"""
        
        if self.redis_client:
            key = f"webhook_metrics:{endpoint_id}"
            
            # Get current metrics
            current_data = await self.redis_client.get(key)
            if current_data:
                metrics = json.loads(current_data)
            else:
                metrics = {
                    "total_deliveries": 0,
                    "successful_deliveries": 0,
                    "failed_deliveries": 0
                }
            
            # Update metrics
            metrics["total_deliveries"] += 1
            if success:
                metrics["successful_deliveries"] += 1
            else:
                metrics["failed_deliveries"] += 1
            
            # Save updated metrics
            await self.redis_client.setex(key, 86400, json.dumps(metrics))
    
    async def _save_metrics(self):
        """Save metrics to storage"""
        
        if self.redis_client:
            for endpoint_id, metrics in self.metrics.items():
                key = f"webhook_metrics:{endpoint_id}"
                await self.redis_client.setex(
                    key,
                    86400,
                    json.dumps(asdict(metrics), default=str)
                )
    
    async def cleanup_expired_deliveries(self, days: int = 7):
        """Clean up expired deliveries"""
        
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        expired_deliveries = [
            delivery_id for delivery_id, delivery in self.deliveries.items()
            if delivery.created_at < cutoff_date
        ]
        
        for delivery_id in expired_deliveries:
            delivery = self.deliveries[delivery_id]
            delivery.status = WebhookStatus.EXPIRED
            
            # Remove from memory
            del self.deliveries[delivery_id]
            
            # Remove from storage
            if self.redis_client:
                key = f"webhook_delivery:{delivery_id}"
                await self.redis_client.delete(key)
        
        logger.info(f"Cleaned up {len(expired_deliveries)} expired deliveries")
    
    async def close(self):
        """Close webhook service"""
        
        if self.session:
            await self.session.close()
        
        logger.info("Webhook service closed")