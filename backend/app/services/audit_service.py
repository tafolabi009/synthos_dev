"""
Comprehensive Audit Logging and Observability Service
Enterprise-grade audit trail with compliance and monitoring
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
import structlog
from pathlib import Path
import aiofiles
from collections import defaultdict, deque
import threading
from concurrent.futures import ThreadPoolExecutor

from app.core.config import settings
from app.core.logging import get_logger
from app.core.redis import get_redis_client

logger = get_logger(__name__)


class AuditEventType(Enum):
    """Audit event types"""
    # Authentication & Authorization
    LOGIN = "auth.login"
    LOGOUT = "auth.logout"
    LOGIN_FAILED = "auth.login_failed"
    PASSWORD_CHANGE = "auth.password_change"
    TOKEN_REFRESH = "auth.token_refresh"
    PERMISSION_GRANTED = "auth.permission_granted"
    PERMISSION_REVOKED = "auth.permission_revoked"
    
    # Data Operations
    DATASET_CREATED = "data.dataset_created"
    DATASET_UPDATED = "data.dataset_updated"
    DATASET_DELETED = "data.dataset_deleted"
    DATASET_ACCESSED = "data.dataset_accessed"
    DATA_EXPORTED = "data.data_exported"
    DATA_IMPORTED = "data.data_imported"
    
    # Generation Operations
    GENERATION_STARTED = "generation.started"
    GENERATION_COMPLETED = "generation.completed"
    GENERATION_FAILED = "generation.failed"
    GENERATION_CANCELLED = "generation.cancelled"
    GENERATION_DOWNLOADED = "generation.downloaded"
    
    # Model Operations
    MODEL_UPLOADED = "model.uploaded"
    MODEL_DELETED = "model.deleted"
    MODEL_TRAINED = "model.trained"
    MODEL_DEPLOYED = "model.deployed"
    
    # System Operations
    SYSTEM_STARTUP = "system.startup"
    SYSTEM_SHUTDOWN = "system.shutdown"
    CONFIG_CHANGED = "system.config_changed"
    BACKUP_CREATED = "system.backup_created"
    BACKUP_RESTORED = "system.backup_restored"
    
    # Security Events
    SECURITY_ALERT = "security.alert"
    SUSPICIOUS_ACTIVITY = "security.suspicious_activity"
    RATE_LIMIT_EXCEEDED = "security.rate_limit_exceeded"
    IP_BLOCKED = "security.ip_blocked"
    MALICIOUS_REQUEST = "security.malicious_request"
    
    # Compliance Events
    GDPR_REQUEST = "compliance.gdpr_request"
    DATA_RETENTION = "compliance.data_retention"
    PRIVACY_VIOLATION = "compliance.privacy_violation"
    AUDIT_TRAIL_ACCESSED = "compliance.audit_trail_accessed"


class AuditSeverity(Enum):
    """Audit event severity levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class AuditCategory(Enum):
    """Audit event categories"""
    AUTHENTICATION = "authentication"
    AUTHORIZATION = "authorization"
    DATA_ACCESS = "data_access"
    DATA_MODIFICATION = "data_modification"
    SYSTEM_OPERATION = "system_operation"
    SECURITY = "security"
    COMPLIANCE = "compliance"
    PERFORMANCE = "performance"
    ERROR = "error"


@dataclass
class AuditEvent:
    """Audit event record"""
    id: str
    event_type: AuditEventType
    severity: AuditSeverity
    category: AuditCategory
    user_id: Optional[int]
    session_id: Optional[str]
    ip_address: Optional[str]
    user_agent: Optional[str]
    timestamp: datetime
    message: str
    details: Dict[str, Any]
    resource_id: Optional[str] = None
    resource_type: Optional[str] = None
    correlation_id: Optional[str] = None
    parent_event_id: Optional[str] = None
    tags: List[str] = None
    
    def __post_init__(self):
        if self.tags is None:
            self.tags = []


@dataclass
class AuditQuery:
    """Audit query parameters"""
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    user_id: Optional[int] = None
    event_types: Optional[List[AuditEventType]] = None
    severity_levels: Optional[List[AuditSeverity]] = None
    categories: Optional[List[AuditCategory]] = None
    resource_id: Optional[str] = None
    resource_type: Optional[str] = None
    correlation_id: Optional[str] = None
    limit: int = 1000
    offset: int = 0


class ComprehensiveAuditService:
    """
    Comprehensive audit logging and observability service
    """

    def __init__(self):
        """Initialize audit service"""
        self.events: deque = deque(maxlen=100000)  # In-memory buffer
        self.redis_client = None
        self._init_cache()
        
        # Audit configuration
        self.retention_days = 2555  # 7 years for compliance
        self.batch_size = 1000
        self.flush_interval = 60  # seconds
        
        # Background tasks
        self._flush_task = None
        self._cleanup_task = None
        
        # Structured logging
        self.audit_logger = structlog.get_logger("audit")
        
        logger.info("Comprehensive Audit Service initialized")

    async def _init_cache(self):
        """Initialize Redis cache"""
        try:
            self.redis_client = await get_redis_client()
        except Exception as e:
            logger.warning("Redis cache not available", error=str(e))

    async def start(self):
        """Start audit service"""
        # Start background tasks
        self._flush_task = asyncio.create_task(self._flush_events())
        self._cleanup_task = asyncio.create_task(self._cleanup_old_events())
        
        logger.info("Audit service started")

    async def stop(self):
        """Stop audit service"""
        # Cancel background tasks
        if self._flush_task:
            self._flush_task.cancel()
            try:
                await self._flush_task
            except asyncio.CancelledError:
                pass
        
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
        
        # Flush remaining events
        await self._flush_events()
        
        logger.info("Audit service stopped")

    async def log_event(
        self,
        event_type: AuditEventType,
        message: str,
        user_id: Optional[int] = None,
        session_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        resource_id: Optional[str] = None,
        resource_type: Optional[str] = None,
        correlation_id: Optional[str] = None,
        parent_event_id: Optional[str] = None,
        tags: Optional[List[str]] = None,
        severity: Optional[AuditSeverity] = None,
        category: Optional[AuditCategory] = None
    ) -> str:
        """Log an audit event"""
        
        # Generate event ID
        event_id = str(uuid.uuid4())
        
        # Determine severity and category if not provided
        if severity is None:
            severity = self._determine_severity(event_type)
        
        if category is None:
            category = self._determine_category(event_type)
        
        # Create audit event
        event = AuditEvent(
            id=event_id,
            event_type=event_type,
            severity=severity,
            category=category,
            user_id=user_id,
            session_id=session_id,
            ip_address=ip_address,
            user_agent=user_agent,
            timestamp=datetime.utcnow(),
            message=message,
            details=details or {},
            resource_id=resource_id,
            resource_type=resource_type,
            correlation_id=correlation_id,
            parent_event_id=parent_event_id,
            tags=tags or []
        )
        
        # Add to in-memory buffer
        self.events.append(event)
        
        # Log to structured logger
        self.audit_logger.info(
            "Audit event logged",
            event_id=event_id,
            event_type=event_type.value,
            severity=severity.value,
            category=category.value,
            user_id=user_id,
            message=message,
            details=details,
            resource_id=resource_id,
            correlation_id=correlation_id
        )
        
        # Cache in Redis for real-time access
        await self._cache_event(event)
        
        # Check for security alerts
        await self._check_security_alerts(event)
        
        return event_id

    def _determine_severity(self, event_type: AuditEventType) -> AuditSeverity:
        """Determine severity based on event type"""
        
        critical_events = {
            AuditEventType.SECURITY_ALERT,
            AuditEventType.SUSPICIOUS_ACTIVITY,
            AuditEventType.MALICIOUS_REQUEST,
            AuditEventType.PRIVACY_VIOLATION,
            AuditEventType.SYSTEM_SHUTDOWN
        }
        
        high_events = {
            AuditEventType.LOGIN_FAILED,
            AuditEventType.RATE_LIMIT_EXCEEDED,
            AuditEventType.IP_BLOCKED,
            AuditEventType.DATASET_DELETED,
            AuditEventType.GENERATION_FAILED
        }
        
        medium_events = {
            AuditEventType.PASSWORD_CHANGE,
            AuditEventType.PERMISSION_GRANTED,
            AuditEventType.PERMISSION_REVOKED,
            AuditEventType.DATASET_UPDATED,
            AuditEventType.MODEL_DELETED
        }
        
        if event_type in critical_events:
            return AuditSeverity.CRITICAL
        elif event_type in high_events:
            return AuditSeverity.HIGH
        elif event_type in medium_events:
            return AuditSeverity.MEDIUM
        else:
            return AuditSeverity.LOW

    def _determine_category(self, event_type: AuditEventType) -> AuditCategory:
        """Determine category based on event type"""
        
        auth_events = {
            AuditEventType.LOGIN, AuditEventType.LOGOUT, AuditEventType.LOGIN_FAILED,
            AuditEventType.PASSWORD_CHANGE, AuditEventType.TOKEN_REFRESH
        }
        
        authz_events = {
            AuditEventType.PERMISSION_GRANTED, AuditEventType.PERMISSION_REVOKED
        }
        
        data_events = {
            AuditEventType.DATASET_CREATED, AuditEventType.DATASET_UPDATED,
            AuditEventType.DATASET_DELETED, AuditEventType.DATASET_ACCESSED,
            AuditEventType.DATA_EXPORTED, AuditEventType.DATA_IMPORTED
        }
        
        security_events = {
            AuditEventType.SECURITY_ALERT, AuditEventType.SUSPICIOUS_ACTIVITY,
            AuditEventType.RATE_LIMIT_EXCEEDED, AuditEventType.IP_BLOCKED,
            AuditEventType.MALICIOUS_REQUEST
        }
        
        compliance_events = {
            AuditEventType.GDPR_REQUEST, AuditEventType.DATA_RETENTION,
            AuditEventType.PRIVACY_VIOLATION, AuditEventType.AUDIT_TRAIL_ACCESSED
        }
        
        if event_type in auth_events:
            return AuditCategory.AUTHENTICATION
        elif event_type in authz_events:
            return AuditCategory.AUTHORIZATION
        elif event_type in data_events:
            return AuditCategory.DATA_ACCESS
        elif event_type in security_events:
            return AuditCategory.SECURITY
        elif event_type in compliance_events:
            return AuditCategory.COMPLIANCE
        else:
            return AuditCategory.SYSTEM_OPERATION

    async def _cache_event(self, event: AuditEvent):
        """Cache event in Redis for real-time access"""
        
        if self.redis_client:
            try:
                # Cache recent events
                cache_key = f"audit:recent:{event.user_id or 'system'}"
                event_data = {
                    "id": event.id,
                    "event_type": event.event_type.value,
                    "severity": event.severity.value,
                    "category": event.category.value,
                    "timestamp": event.timestamp.isoformat(),
                    "message": event.message,
                    "details": event.details,
                    "resource_id": event.resource_id,
                    "correlation_id": event.correlation_id
                }
                
                await self.redis_client.lpush(cache_key, json.dumps(event_data))
                await self.redis_client.ltrim(cache_key, 0, 999)  # Keep last 1000 events
                await self.redis_client.expire(cache_key, 86400)  # 24 hours
                
            except Exception as e:
                logger.warning("Failed to cache audit event", error=str(e))

    async def _check_security_alerts(self, event: AuditEvent):
        """Check for security alerts and patterns"""
        
        # Check for suspicious patterns
        if event.severity in [AuditSeverity.HIGH, AuditSeverity.CRITICAL]:
            await self._analyze_security_patterns(event)
        
        # Check for rate limiting
        if event.event_type == AuditEventType.RATE_LIMIT_EXCEEDED:
            await self._handle_rate_limit_exceeded(event)
        
        # Check for multiple failed logins
        if event.event_type == AuditEventType.LOGIN_FAILED:
            await self._check_failed_login_patterns(event)

    async def _analyze_security_patterns(self, event: AuditEvent):
        """Analyze security patterns"""
        
        # Get recent events for the same user/IP
        recent_events = await self._get_recent_events(
            user_id=event.user_id,
            ip_address=event.ip_address,
            hours=24
        )
        
        # Check for patterns
        high_severity_count = len([
            e for e in recent_events
            if e.severity in [AuditSeverity.HIGH, AuditSeverity.CRITICAL]
        ])
        
        if high_severity_count >= 5:
            # Create security alert
            await self.log_event(
                event_type=AuditEventType.SECURITY_ALERT,
                message=f"Multiple high-severity events detected for user {event.user_id}",
                user_id=event.user_id,
                ip_address=event.ip_address,
                details={
                    "high_severity_count": high_severity_count,
                    "time_window": "24 hours",
                    "trigger_event": event.id
                },
                severity=AuditSeverity.CRITICAL,
                category=AuditCategory.SECURITY
            )

    async def _handle_rate_limit_exceeded(self, event: AuditEvent):
        """Handle rate limit exceeded events"""
        
        # Check if IP should be blocked
        recent_rate_limit_events = await self._get_recent_events(
            event_type=AuditEventType.RATE_LIMIT_EXCEEDED,
            ip_address=event.ip_address,
            hours=1
        )
        
        if len(recent_rate_limit_events) >= 10:
            # Block IP
            await self.log_event(
                event_type=AuditEventType.IP_BLOCKED,
                message=f"IP {event.ip_address} blocked due to excessive rate limiting",
                ip_address=event.ip_address,
                details={
                    "rate_limit_events": len(recent_rate_limit_events),
                    "time_window": "1 hour"
                },
                severity=AuditSeverity.HIGH,
                category=AuditCategory.SECURITY
            )

    async def _check_failed_login_patterns(self, event: AuditEvent):
        """Check for failed login patterns"""
        
        # Get recent failed logins
        recent_failed_logins = await self._get_recent_events(
            event_type=AuditEventType.LOGIN_FAILED,
            ip_address=event.ip_address,
            hours=1
        )
        
        if len(recent_failed_logins) >= 5:
            # Create suspicious activity alert
            await self.log_event(
                event_type=AuditEventType.SUSPICIOUS_ACTIVITY,
                message=f"Suspicious login activity from IP {event.ip_address}",
                ip_address=event.ip_address,
                details={
                    "failed_login_count": len(recent_failed_logins),
                    "time_window": "1 hour"
                },
                severity=AuditSeverity.HIGH,
                category=AuditCategory.SECURITY
            )

    async def _get_recent_events(
        self,
        user_id: Optional[int] = None,
        ip_address: Optional[str] = None,
        event_type: Optional[AuditEventType] = None,
        hours: int = 24
    ) -> List[AuditEvent]:
        """Get recent events for analysis"""
        
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        
        recent_events = []
        for event in self.events:
            if event.timestamp < cutoff_time:
                break
            
            if user_id and event.user_id != user_id:
                continue
            
            if ip_address and event.ip_address != ip_address:
                continue
            
            if event_type and event.event_type != event_type:
                continue
            
            recent_events.append(event)
        
        return recent_events

    async def _flush_events(self):
        """Background task to flush events to persistent storage"""
        
        while True:
            try:
                await asyncio.sleep(self.flush_interval)
                
                if len(self.events) >= self.batch_size:
                    await self._flush_batch()
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("Error in flush task", error=str(e))

    async def _flush_batch(self):
        """Flush a batch of events to storage"""
        
        if not self.events:
            return
        
        # Get batch of events
        batch_events = []
        for _ in range(min(self.batch_size, len(self.events))):
            if self.events:
                batch_events.append(self.events.popleft())
        
        if not batch_events:
            return
        
        try:
            # Write to file
            await self._write_events_to_file(batch_events)
            
            # Store in Redis for querying
            await self._store_events_in_redis(batch_events)
            
            logger.info(f"Flushed {len(batch_events)} audit events")
            
        except Exception as e:
            logger.error("Failed to flush audit events", error=str(e))
            # Put events back in queue
            for event in reversed(batch_events):
                self.events.appendleft(event)

    async def _write_events_to_file(self, events: List[AuditEvent]):
        """Write events to audit log file"""
        
        audit_dir = Path(settings.UPLOAD_PATH) / "audit_logs"
        audit_dir.mkdir(parents=True, exist_ok=True)
        
        # Create daily log file
        date_str = datetime.utcnow().strftime("%Y-%m-%d")
        log_file = audit_dir / f"audit_{date_str}.jsonl"
        
        # Write events to file
        async with aiofiles.open(log_file, "a") as f:
            for event in events:
                event_data = {
                    "id": event.id,
                    "event_type": event.event_type.value,
                    "severity": event.severity.value,
                    "category": event.category.value,
                    "user_id": event.user_id,
                    "session_id": event.session_id,
                    "ip_address": event.ip_address,
                    "user_agent": event.user_agent,
                    "timestamp": event.timestamp.isoformat(),
                    "message": event.message,
                    "details": event.details,
                    "resource_id": event.resource_id,
                    "resource_type": event.resource_type,
                    "correlation_id": event.correlation_id,
                    "parent_event_id": event.parent_event_id,
                    "tags": event.tags
                }
                await f.write(json.dumps(event_data) + "\n")

    async def _store_events_in_redis(self, events: List[AuditEvent]):
        """Store events in Redis for querying"""
        
        if not self.redis_client:
            return
        
        try:
            for event in events:
                # Store by date
                date_key = event.timestamp.strftime("%Y-%m-%d")
                redis_key = f"audit:events:{date_key}"
                
                event_data = {
                    "id": event.id,
                    "event_type": event.event_type.value,
                    "severity": event.severity.value,
                    "category": event.category.value,
                    "user_id": event.user_id,
                    "timestamp": event.timestamp.isoformat(),
                    "message": event.message,
                    "details": event.details,
                    "resource_id": event.resource_id,
                    "correlation_id": event.correlation_id
                }
                
                await self.redis_client.lpush(redis_key, json.dumps(event_data))
                await self.redis_client.expire(redis_key, 86400 * 7)  # 7 days
                
        except Exception as e:
            logger.warning("Failed to store events in Redis", error=str(e))

    async def _cleanup_old_events(self):
        """Background task to cleanup old events"""
        
        while True:
            try:
                await asyncio.sleep(86400)  # Run daily
                
                cutoff_date = datetime.utcnow() - timedelta(days=self.retention_days)
                
                # Clean up old files
                await self._cleanup_old_files(cutoff_date)
                
                # Clean up Redis
                await self._cleanup_redis_events(cutoff_date)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("Error in cleanup task", error=str(e))

    async def _cleanup_old_files(self, cutoff_date: datetime):
        """Clean up old audit log files"""
        
        audit_dir = Path(settings.UPLOAD_PATH) / "audit_logs"
        if not audit_dir.exists():
            return
        
        for log_file in audit_dir.glob("audit_*.jsonl"):
            try:
                # Extract date from filename
                date_str = log_file.stem.replace("audit_", "")
                file_date = datetime.strptime(date_str, "%Y-%m-%d")
                
                if file_date < cutoff_date:
                    log_file.unlink()
                    logger.info(f"Deleted old audit log file: {log_file}")
                    
            except Exception as e:
                logger.warning(f"Failed to process audit log file {log_file}", error=str(e))

    async def _cleanup_redis_events(self, cutoff_date: datetime):
        """Clean up old Redis events"""
        
        if not self.redis_client:
            return
        
        try:
            # Get all audit keys
            pattern = "audit:events:*"
            keys = await self.redis_client.keys(pattern)
            
            for key in keys:
                # Extract date from key
                date_str = key.decode().split(":")[-1]
                try:
                    key_date = datetime.strptime(date_str, "%Y-%m-%d")
                    if key_date < cutoff_date:
                        await self.redis_client.delete(key)
                        logger.info(f"Deleted old Redis audit key: {key}")
                except ValueError:
                    continue
                    
        except Exception as e:
            logger.warning("Failed to cleanup Redis events", error=str(e))

    async def query_events(self, query: AuditQuery) -> List[AuditEvent]:
        """Query audit events"""
        
        # Get events from Redis first (recent)
        recent_events = await self._query_redis_events(query)
        
        # Get events from files if needed
        file_events = await self._query_file_events(query)
        
        # Combine and deduplicate
        all_events = recent_events + file_events
        unique_events = {event.id: event for event in all_events}
        
        # Sort by timestamp
        sorted_events = sorted(unique_events.values(), key=lambda x: x.timestamp, reverse=True)
        
        # Apply limit and offset
        return sorted_events[query.offset:query.offset + query.limit]

    async def _query_redis_events(self, query: AuditQuery) -> List[AuditEvent]:
        """Query events from Redis"""
        
        if not self.redis_client:
            return []
        
        events = []
        
        try:
            # Get date range
            if query.start_date and query.end_date:
                current_date = query.start_date.date()
                end_date = query.end_date.date()
                
                while current_date <= end_date:
                    redis_key = f"audit:events:{current_date.strftime('%Y-%m-%d')}"
                    cached_events = await self.redis_client.lrange(redis_key, 0, -1)
                    
                    for event_data in cached_events:
                        try:
                            data = json.loads(event_data)
                            event = self._deserialize_event(data)
                            if self._matches_query(event, query):
                                events.append(event)
                        except Exception as e:
                            logger.warning("Failed to deserialize event", error=str(e))
                    
                    current_date += timedelta(days=1)
            
        except Exception as e:
            logger.warning("Failed to query Redis events", error=str(e))
        
        return events

    async def _query_file_events(self, query: AuditQuery) -> List[AuditEvent]:
        """Query events from files"""
        
        events = []
        audit_dir = Path(settings.UPLOAD_PATH) / "audit_logs"
        
        if not audit_dir.exists():
            return events
        
        try:
            # Get date range
            if query.start_date and query.end_date:
                current_date = query.start_date.date()
                end_date = query.end_date.date()
                
                while current_date <= end_date:
                    log_file = audit_dir / f"audit_{current_date.strftime('%Y-%m-%d')}.jsonl"
                    
                    if log_file.exists():
                        async with aiofiles.open(log_file, "r") as f:
                            async for line in f:
                                try:
                                    data = json.loads(line.strip())
                                    event = self._deserialize_event(data)
                                    if self._matches_query(event, query):
                                        events.append(event)
                                except Exception as e:
                                    logger.warning("Failed to deserialize file event", error=str(e))
                    
                    current_date += timedelta(days=1)
            
        except Exception as e:
            logger.warning("Failed to query file events", error=str(e))
        
        return events

    def _deserialize_event(self, data: Dict[str, Any]) -> AuditEvent:
        """Deserialize event from JSON data"""
        
        return AuditEvent(
            id=data["id"],
            event_type=AuditEventType(data["event_type"]),
            severity=AuditSeverity(data["severity"]),
            category=AuditCategory(data["category"]),
            user_id=data.get("user_id"),
            session_id=data.get("session_id"),
            ip_address=data.get("ip_address"),
            user_agent=data.get("user_agent"),
            timestamp=datetime.fromisoformat(data["timestamp"]),
            message=data["message"],
            details=data.get("details", {}),
            resource_id=data.get("resource_id"),
            resource_type=data.get("resource_type"),
            correlation_id=data.get("correlation_id"),
            parent_event_id=data.get("parent_event_id"),
            tags=data.get("tags", [])
        )

    def _matches_query(self, event: AuditEvent, query: AuditQuery) -> bool:
        """Check if event matches query criteria"""
        
        if query.user_id and event.user_id != query.user_id:
            return False
        
        if query.event_types and event.event_type not in query.event_types:
            return False
        
        if query.severity_levels and event.severity not in query.severity_levels:
            return False
        
        if query.categories and event.category not in query.categories:
            return False
        
        if query.resource_id and event.resource_id != query.resource_id:
            return False
        
        if query.resource_type and event.resource_type != query.resource_type:
            return False
        
        if query.correlation_id and event.correlation_id != query.correlation_id:
            return False
        
        if query.start_date and event.timestamp < query.start_date:
            return False
        
        if query.end_date and event.timestamp > query.end_date:
            return False
        
        return True

    async def get_audit_stats(self) -> Dict[str, Any]:
        """Get audit statistics"""
        
        stats = {
            "total_events": len(self.events),
            "events_by_severity": defaultdict(int),
            "events_by_category": defaultdict(int),
            "events_by_type": defaultdict(int),
            "recent_events_count": 0,
            "security_alerts_count": 0
        }
        
        # Analyze in-memory events
        for event in self.events:
            stats["events_by_severity"][event.severity.value] += 1
            stats["events_by_category"][event.category.value] += 1
            stats["events_by_type"][event.event_type.value] += 1
            
            if event.timestamp > datetime.utcnow() - timedelta(hours=24):
                stats["recent_events_count"] += 1
            
            if event.event_type == AuditEventType.SECURITY_ALERT:
                stats["security_alerts_count"] += 1
        
        return stats

    async def export_audit_trail(
        self,
        query: AuditQuery,
        format: str = "json"
    ) -> bytes:
        """Export audit trail"""
        
        events = await self.query_events(query)
        
        if format == "json":
            return json.dumps([asdict(event) for event in events], indent=2).encode()
        elif format == "csv":
            import csv
            from io import StringIO
            
            output = StringIO()
            writer = csv.writer(output)
            
            # Write header
            writer.writerow([
                "id", "event_type", "severity", "category", "user_id",
                "timestamp", "message", "resource_id", "correlation_id"
            ])
            
            # Write events
            for event in events:
                writer.writerow([
                    event.id, event.event_type.value, event.severity.value,
                    event.category.value, event.user_id, event.timestamp.isoformat(),
                    event.message, event.resource_id, event.correlation_id
                ])
            
            return output.getvalue().encode()
        else:
            raise ValueError(f"Unsupported format: {format}")

    async def get_user_activity(self, user_id: int, hours: int = 24) -> Dict[str, Any]:
        """Get user activity summary"""
        
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        
        user_events = [
            event for event in self.events
            if event.user_id == user_id and event.timestamp >= cutoff_time
        ]
        
        return {
            "user_id": user_id,
            "time_window_hours": hours,
            "total_events": len(user_events),
            "events_by_type": {
                event_type.value: len([e for e in user_events if e.event_type == event_type])
                for event_type in set(e.event_type for e in user_events)
            },
            "events_by_severity": {
                severity.value: len([e for e in user_events if e.severity == severity])
                for severity in set(e.severity for e in user_events)
            },
            "recent_events": [
                {
                    "id": event.id,
                    "event_type": event.event_type.value,
                    "severity": event.severity.value,
                    "timestamp": event.timestamp.isoformat(),
                    "message": event.message
                }
                for event in sorted(user_events, key=lambda x: x.timestamp, reverse=True)[:10]
            ]
        }