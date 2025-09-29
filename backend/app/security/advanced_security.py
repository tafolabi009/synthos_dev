"""
Advanced Security System for Synthetic Data Platform
Enterprise-grade security with threat detection and response
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
import secrets
import string
import ipaddress
import re
from collections import defaultdict, deque
import threading
from concurrent.futures import ThreadPoolExecutor

# Security libraries
try:
    import cryptography
    from cryptography.fernet import Fernet
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import rsa, padding
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
    CRYPTOGRAPHY_AVAILABLE = True
except ImportError:
    CRYPTOGRAPHY_AVAILABLE = False
    cryptography = None
    Fernet = None

try:
    import bcrypt
    BCRYPT_AVAILABLE = True
except ImportError:
    BCRYPT_AVAILABLE = False
    bcrypt = None

from app.core.config import settings
from app.core.logging import get_logger
from app.core.redis import get_redis_client

logger = get_logger(__name__)


class ThreatLevel(Enum):
    """Threat severity levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class SecurityEventType(Enum):
    """Security event types"""
    BRUTE_FORCE_ATTACK = "brute_force_attack"
    DDoS_ATTACK = "ddos_attack"
    SQL_INJECTION = "sql_injection"
    XSS_ATTACK = "xss_attack"
    CSRF_ATTACK = "csrf_attack"
    UNAUTHORIZED_ACCESS = "unauthorized_access"
    DATA_BREACH = "data_breach"
    MALICIOUS_FILE = "malicious_file"
    SUSPICIOUS_ACTIVITY = "suspicious_activity"
    RATE_LIMIT_EXCEEDED = "rate_limit_exceeded"
    IP_BLOCKED = "ip_blocked"
    ACCOUNT_COMPROMISED = "account_compromised"


class SecurityAction(Enum):
    """Security response actions"""
    LOG = "log"
    BLOCK_IP = "block_ip"
    RATE_LIMIT = "rate_limit"
    REQUIRE_CAPTCHA = "require_captcha"
    SUSPEND_USER = "suspend_user"
    ALERT_ADMIN = "alert_admin"
    QUARANTINE = "quarantine"


@dataclass
class SecurityEvent:
    """Security event record"""
    id: str
    event_type: SecurityEventType
    threat_level: ThreatLevel
    source_ip: str
    user_id: Optional[int]
    timestamp: datetime
    description: str
    details: Dict[str, Any]
    actions_taken: List[SecurityAction]
    resolved: bool = False
    resolved_at: Optional[datetime] = None


@dataclass
class SecurityRule:
    """Security rule definition"""
    name: str
    pattern: str
    event_type: SecurityEventType
    threat_level: ThreatLevel
    actions: List[SecurityAction]
    enabled: bool = True
    cooldown: int = 300  # seconds
    threshold: int = 5


@dataclass
class IPReputation:
    """IP reputation data"""
    ip: str
    reputation_score: float  # 0.0 (bad) to 1.0 (good)
    threat_types: List[str]
    last_seen: datetime
    block_count: int = 0
    allow_count: int = 0


class AdvancedSecuritySystem:
    """
    Advanced security system with threat detection and response
    """

    def __init__(self):
        """Initialize security system"""
        self.redis_client = None
        self._init_cache()
        
        # Security state
        self.blocked_ips = set()
        self.rate_limits = defaultdict(lambda: deque())
        self.failed_logins = defaultdict(lambda: deque())
        self.suspicious_activities = defaultdict(lambda: deque())
        
        # Security rules
        self.rules = self._load_security_rules()
        
        # Encryption keys
        self.encryption_key = self._get_or_create_encryption_key()
        
        # Background tasks
        self._cleanup_task = None
        self._monitoring_task = None
        
        logger.info("Advanced Security System initialized")

    async def _init_cache(self):
        """Initialize Redis cache"""
        try:
            self.redis_client = await get_redis_client()
        except Exception as e:
            logger.warning("Redis cache not available", error=str(e))

    async def start(self):
        """Start security system"""
        # Start background tasks
        self._cleanup_task = asyncio.create_task(self._cleanup_old_data())
        self._monitoring_task = asyncio.create_task(self._monitor_threats())
        
        logger.info("Security system started")

    async def stop(self):
        """Stop security system"""
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
        
        if self._monitoring_task:
            self._monitoring_task.cancel()
            try:
                await self._monitoring_task
            except asyncio.CancelledError:
                pass
        
        logger.info("Security system stopped")

    def _load_security_rules(self) -> List[SecurityRule]:
        """Load security rules"""
        
        return [
            SecurityRule(
                name="Brute Force Detection",
                pattern=r"login.*failed",
                event_type=SecurityEventType.BRUTE_FORCE_ATTACK,
                threat_level=ThreatLevel.HIGH,
                actions=[SecurityAction.BLOCK_IP, SecurityAction.ALERT_ADMIN],
                threshold=5,
                cooldown=300
            ),
            SecurityRule(
                name="SQL Injection Detection",
                pattern=r"(union|select|insert|update|delete|drop|create|alter).*from",
                event_type=SecurityEventType.SQL_INJECTION,
                threat_level=ThreatLevel.CRITICAL,
                actions=[SecurityAction.BLOCK_IP, SecurityAction.ALERT_ADMIN],
                threshold=1,
                cooldown=0
            ),
            SecurityRule(
                name="XSS Detection",
                pattern=r"<script|javascript:|onload=|onerror=",
                event_type=SecurityEventType.XSS_ATTACK,
                threat_level=ThreatLevel.HIGH,
                actions=[SecurityAction.BLOCK_IP, SecurityAction.ALERT_ADMIN],
                threshold=1,
                cooldown=0
            ),
            SecurityRule(
                name="Rate Limiting",
                pattern=r"rate.*limit",
                event_type=SecurityEventType.RATE_LIMIT_EXCEEDED,
                threat_level=ThreatLevel.MEDIUM,
                actions=[SecurityAction.RATE_LIMIT, SecurityAction.REQUIRE_CAPTCHA],
                threshold=10,
                cooldown=60
            )
        ]

    def _get_or_create_encryption_key(self) -> bytes:
        """Get or create encryption key"""
        
        if not CRYPTOGRAPHY_AVAILABLE:
            logger.warning("Cryptography library not available, using fallback encryption")
            return secrets.token_bytes(32)
        
        try:
            # Try to load existing key
            key_file = Path(settings.UPLOAD_PATH) / "security" / "encryption.key"
            key_file.parent.mkdir(parents=True, exist_ok=True)
            
            if key_file.exists():
                with open(key_file, "rb") as f:
                    return f.read()
            else:
                # Generate new key
                key = Fernet.generate_key()
                with open(key_file, "wb") as f:
                    f.write(key)
                return key
                
        except Exception as e:
            logger.warning("Failed to load/create encryption key", error=str(e))
            return secrets.token_bytes(32)

    async def analyze_request(
        self,
        request_data: Dict[str, Any],
        source_ip: str,
        user_id: Optional[int] = None
    ) -> Tuple[bool, List[SecurityEvent]]:
        """Analyze request for security threats"""
        
        threats_detected = []
        
        try:
            # Check if IP is blocked
            if await self._is_ip_blocked(source_ip):
                event = SecurityEvent(
                    id=str(uuid.uuid4()),
                    event_type=SecurityEventType.UNAUTHORIZED_ACCESS,
                    threat_level=ThreatLevel.HIGH,
                    source_ip=source_ip,
                    user_id=user_id,
                    timestamp=datetime.utcnow(),
                    description="Blocked IP attempted access",
                    details={"reason": "ip_blocked"},
                    actions_taken=[SecurityAction.BLOCK_IP]
                )
                threats_detected.append(event)
                return False, threats_detected
            
            # Check rate limits
            if await self._check_rate_limit(source_ip, user_id):
                event = SecurityEvent(
                    id=str(uuid.uuid4()),
                    event_type=SecurityEventType.RATE_LIMIT_EXCEEDED,
                    threat_level=ThreatLevel.MEDIUM,
                    source_ip=source_ip,
                    user_id=user_id,
                    timestamp=datetime.utcnow(),
                    description="Rate limit exceeded",
                    details={"ip": source_ip, "user_id": user_id},
                    actions_taken=[SecurityAction.RATE_LIMIT]
                )
                threats_detected.append(event)
                return False, threats_detected
            
            # Analyze request content
            content_threats = await self._analyze_content(request_data, source_ip, user_id)
            threats_detected.extend(content_threats)
            
            # Check for suspicious patterns
            pattern_threats = await self._check_security_patterns(request_data, source_ip, user_id)
            threats_detected.extend(pattern_threats)
            
            # Update IP reputation
            await self._update_ip_reputation(source_ip, len(threats_detected) == 0)
            
            # Process detected threats
            for threat in threats_detected:
                await self._process_security_event(threat)
            
            return len(threats_detected) == 0, threats_detected
            
        except Exception as e:
            logger.error("Security analysis failed", error=str(e))
            return True, []

    async def _is_ip_blocked(self, ip: str) -> bool:
        """Check if IP is blocked"""
        
        # Check in-memory cache
        if ip in self.blocked_ips:
            return True
        
        # Check Redis cache
        if self.redis_client:
            try:
                blocked = await self.redis_client.get(f"blocked_ip:{ip}")
                if blocked:
                    return True
            except Exception as e:
                logger.warning("Failed to check blocked IP in Redis", error=str(e))
        
        return False

    async def _check_rate_limit(self, ip: str, user_id: Optional[int]) -> bool:
        """Check rate limiting"""
        
        current_time = time.time()
        window_size = 60  # 1 minute window
        max_requests = 100  # Max requests per window
        
        # Clean old entries
        cutoff_time = current_time - window_size
        while self.rate_limits[ip] and self.rate_limits[ip][0] < cutoff_time:
            self.rate_limits[ip].popleft()
        
        # Check if limit exceeded
        if len(self.rate_limits[ip]) >= max_requests:
            return True
        
        # Add current request
        self.rate_limits[ip].append(current_time)
        
        return False

    async def _analyze_content(
        self,
        request_data: Dict[str, Any],
        source_ip: str,
        user_id: Optional[int]
    ) -> List[SecurityEvent]:
        """Analyze request content for threats"""
        
        threats = []
        
        # Convert request data to string for analysis
        content_str = json.dumps(request_data, default=str).lower()
        
        # Check for SQL injection patterns
        sql_patterns = [
            r"union.*select", r"drop.*table", r"delete.*from",
            r"insert.*into", r"update.*set", r"create.*table"
        ]
        
        for pattern in sql_patterns:
            if re.search(pattern, content_str, re.IGNORECASE):
                threat = SecurityEvent(
                    id=str(uuid.uuid4()),
                    event_type=SecurityEventType.SQL_INJECTION,
                    threat_level=ThreatLevel.CRITICAL,
                    source_ip=source_ip,
                    user_id=user_id,
                    timestamp=datetime.utcnow(),
                    description="SQL injection attempt detected",
                    details={"pattern": pattern, "content": content_str[:200]},
                    actions_taken=[SecurityAction.BLOCK_IP, SecurityAction.ALERT_ADMIN]
                )
                threats.append(threat)
                break
        
        # Check for XSS patterns
        xss_patterns = [
            r"<script", r"javascript:", r"onload=", r"onerror=",
            r"onclick=", r"onmouseover=", r"eval\("
        ]
        
        for pattern in xss_patterns:
            if re.search(pattern, content_str, re.IGNORECASE):
                threat = SecurityEvent(
                    id=str(uuid.uuid4()),
                    event_type=SecurityEventType.XSS_ATTACK,
                    threat_level=ThreatLevel.HIGH,
                    source_ip=source_ip,
                    user_id=user_id,
                    timestamp=datetime.utcnow(),
                    description="XSS attack attempt detected",
                    details={"pattern": pattern, "content": content_str[:200]},
                    actions_taken=[SecurityAction.BLOCK_IP, SecurityAction.ALERT_ADMIN]
                )
                threats.append(threat)
                break
        
        return threats

    async def _check_security_patterns(
        self,
        request_data: Dict[str, Any],
        source_ip: str,
        user_id: Optional[int]
    ) -> List[SecurityEvent]:
        """Check for security patterns using rules"""
        
        threats = []
        content_str = json.dumps(request_data, default=str).lower()
        
        for rule in self.rules:
            if not rule.enabled:
                continue
            
            if re.search(rule.pattern, content_str, re.IGNORECASE):
                # Check cooldown
                if await self._is_rule_in_cooldown(rule, source_ip):
                    continue
                
                # Check threshold
                if await self._check_rule_threshold(rule, source_ip):
                    threat = SecurityEvent(
                        id=str(uuid.uuid4()),
                        event_type=rule.event_type,
                        threat_level=rule.threat_level,
                        source_ip=source_ip,
                        user_id=user_id,
                        timestamp=datetime.utcnow(),
                        description=f"Security rule triggered: {rule.name}",
                        details={"rule": rule.name, "pattern": rule.pattern},
                        actions_taken=rule.actions
                    )
                    threats.append(threat)
                    
                    # Set cooldown
                    await self._set_rule_cooldown(rule, source_ip)
        
        return threats

    async def _is_rule_in_cooldown(self, rule: SecurityRule, source_ip: str) -> bool:
        """Check if rule is in cooldown for IP"""
        
        if self.redis_client:
            try:
                cooldown_key = f"rule_cooldown:{rule.name}:{source_ip}"
                cooldown = await self.redis_client.get(cooldown_key)
                if cooldown:
                    return True
            except Exception as e:
                logger.warning("Failed to check rule cooldown", error=str(e))
        
        return False

    async def _check_rule_threshold(self, rule: SecurityRule, source_ip: str) -> bool:
        """Check if rule threshold is exceeded"""
        
        if self.redis_client:
            try:
                threshold_key = f"rule_threshold:{rule.name}:{source_ip}"
                count = await self.redis_client.get(threshold_key)
                if count and int(count) >= rule.threshold:
                    return True
            except Exception as e:
                logger.warning("Failed to check rule threshold", error=str(e))
        
        return False

    async def _set_rule_cooldown(self, rule: SecurityRule, source_ip: str):
        """Set rule cooldown for IP"""
        
        if self.redis_client:
            try:
                cooldown_key = f"rule_cooldown:{rule.name}:{source_ip}"
                await self.redis_client.setex(cooldown_key, rule.cooldown, "1")
            except Exception as e:
                logger.warning("Failed to set rule cooldown", error=str(e))

    async def _update_ip_reputation(self, ip: str, is_good: bool):
        """Update IP reputation"""
        
        if self.redis_client:
            try:
                rep_key = f"ip_reputation:{ip}"
                rep_data = await self.redis_client.get(rep_key)
                
                if rep_data:
                    reputation = json.loads(rep_data)
                else:
                    reputation = {
                        "ip": ip,
                        "reputation_score": 0.5,
                        "threat_types": [],
                        "last_seen": datetime.utcnow().isoformat(),
                        "block_count": 0,
                        "allow_count": 0
                    }
                
                if is_good:
                    reputation["allow_count"] += 1
                    reputation["reputation_score"] = min(1.0, reputation["reputation_score"] + 0.01)
                else:
                    reputation["block_count"] += 1
                    reputation["reputation_score"] = max(0.0, reputation["reputation_score"] - 0.1)
                
                reputation["last_seen"] = datetime.utcnow().isoformat()
                
                await self.redis_client.setex(rep_key, 86400, json.dumps(reputation))
                
            except Exception as e:
                logger.warning("Failed to update IP reputation", error=str(e))

    async def _process_security_event(self, event: SecurityEvent):
        """Process security event and take actions"""
        
        try:
            # Log event
            logger.warning(
                "Security event detected",
                event_id=event.id,
                event_type=event.event_type.value,
                threat_level=event.threat_level.value,
                source_ip=event.source_ip,
                user_id=event.user_id,
                description=event.description
            )
            
            # Take actions
            for action in event.actions_taken:
                await self._execute_security_action(action, event)
            
            # Store event
            await self._store_security_event(event)
            
        except Exception as e:
            logger.error("Failed to process security event", error=str(e))

    async def _execute_security_action(self, action: SecurityAction, event: SecurityEvent):
        """Execute security action"""
        
        try:
            if action == SecurityAction.BLOCK_IP:
                await self._block_ip(event.source_ip, event.id)
            elif action == SecurityAction.RATE_LIMIT:
                await self._apply_rate_limit(event.source_ip, event.user_id)
            elif action == SecurityAction.ALERT_ADMIN:
                await self._send_admin_alert(event)
            elif action == SecurityAction.SUSPEND_USER:
                if event.user_id:
                    await self._suspend_user(event.user_id, event.id)
            
        except Exception as e:
            logger.error("Failed to execute security action", error=str(e), action=action.value)

    async def _block_ip(self, ip: str, event_id: str):
        """Block IP address"""
        
        # Add to in-memory cache
        self.blocked_ips.add(ip)
        
        # Store in Redis
        if self.redis_client:
            try:
                await self.redis_client.setex(f"blocked_ip:{ip}", 86400, event_id)
            except Exception as e:
                logger.warning("Failed to store blocked IP in Redis", error=str(e))
        
        logger.info("IP blocked", ip=ip, event_id=event_id)

    async def _apply_rate_limit(self, ip: str, user_id: Optional[int]):
        """Apply rate limiting"""
        
        # Add to rate limit tracking
        current_time = time.time()
        self.rate_limits[ip].append(current_time)
        
        logger.info("Rate limit applied", ip=ip, user_id=user_id)

    async def _send_admin_alert(self, event: SecurityEvent):
        """Send admin alert"""
        
        # TODO: Implement admin alert system
        logger.critical(
            "SECURITY ALERT",
            event_id=event.id,
            event_type=event.event_type.value,
            threat_level=event.threat_level.value,
            source_ip=event.source_ip,
            user_id=event.user_id,
            description=event.description
        )

    async def _suspend_user(self, user_id: int, event_id: str):
        """Suspend user account"""
        
        # TODO: Implement user suspension
        logger.info("User suspended", user_id=user_id, event_id=event_id)

    async def _store_security_event(self, event: SecurityEvent):
        """Store security event"""
        
        if self.redis_client:
            try:
                event_data = {
                    "id": event.id,
                    "event_type": event.event_type.value,
                    "threat_level": event.threat_level.value,
                    "source_ip": event.source_ip,
                    "user_id": event.user_id,
                    "timestamp": event.timestamp.isoformat(),
                    "description": event.description,
                    "details": event.details,
                    "actions_taken": [action.value for action in event.actions_taken],
                    "resolved": event.resolved
                }
                
                await self.redis_client.lpush("security_events", json.dumps(event_data))
                await self.redis_client.ltrim("security_events", 0, 9999)  # Keep last 10000 events
                
            except Exception as e:
                logger.warning("Failed to store security event", error=str(e))

    async def _cleanup_old_data(self):
        """Background task to cleanup old security data"""
        
        while True:
            try:
                await asyncio.sleep(3600)  # Run every hour
                
                current_time = time.time()
                cutoff_time = current_time - 86400  # 24 hours ago
                
                # Cleanup rate limits
                for ip in list(self.rate_limits.keys()):
                    while self.rate_limits[ip] and self.rate_limits[ip][0] < cutoff_time:
                        self.rate_limits[ip].popleft()
                    
                    if not self.rate_limits[ip]:
                        del self.rate_limits[ip]
                
                # Cleanup failed logins
                for ip in list(self.failed_logins.keys()):
                    while self.failed_logins[ip] and self.failed_logins[ip][0] < cutoff_time:
                        self.failed_logins[ip].popleft()
                    
                    if not self.failed_logins[ip]:
                        del self.failed_logins[ip]
                
                logger.info("Security data cleanup completed")
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("Error in security cleanup task", error=str(e))

    async def _monitor_threats(self):
        """Background task to monitor threats"""
        
        while True:
            try:
                await asyncio.sleep(60)  # Run every minute
                
                # Check for suspicious patterns
                await self._analyze_threat_patterns()
                
                # Update security metrics
                await self._update_security_metrics()
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("Error in threat monitoring task", error=str(e))

    async def _analyze_threat_patterns(self):
        """Analyze threat patterns"""
        
        # TODO: Implement advanced threat pattern analysis
        pass

    async def _update_security_metrics(self):
        """Update security metrics"""
        
        # TODO: Implement security metrics collection
        pass

    async def get_security_stats(self) -> Dict[str, Any]:
        """Get security statistics"""
        
        stats = {
            "blocked_ips_count": len(self.blocked_ips),
            "rate_limited_ips_count": len(self.rate_limits),
            "failed_login_ips_count": len(self.failed_logins),
            "active_rules_count": len([r for r in self.rules if r.enabled]),
            "total_security_events": 0
        }
        
        # Get total security events from Redis
        if self.redis_client:
            try:
                events_count = await self.redis_client.llen("security_events")
                stats["total_security_events"] = events_count
            except Exception as e:
                logger.warning("Failed to get security events count", error=str(e))
        
        return stats

    async def unblock_ip(self, ip: str) -> bool:
        """Unblock IP address"""
        
        try:
            # Remove from in-memory cache
            self.blocked_ips.discard(ip)
            
            # Remove from Redis
            if self.redis_client:
                await self.redis_client.delete(f"blocked_ip:{ip}")
            
            logger.info("IP unblocked", ip=ip)
            return True
            
        except Exception as e:
            logger.error("Failed to unblock IP", error=str(e), ip=ip)
            return False

    async def get_blocked_ips(self) -> List[str]:
        """Get list of blocked IPs"""
        
        blocked_ips = list(self.blocked_ips)
        
        if self.redis_client:
            try:
                # Get additional blocked IPs from Redis
                keys = await self.redis_client.keys("blocked_ip:*")
                for key in keys:
                    ip = key.decode().replace("blocked_ip:", "")
                    if ip not in blocked_ips:
                        blocked_ips.append(ip)
            except Exception as e:
                logger.warning("Failed to get blocked IPs from Redis", error=str(e))
        
        return blocked_ips

    async def encrypt_sensitive_data(self, data: str) -> str:
        """Encrypt sensitive data"""
        
        if not CRYPTOGRAPHY_AVAILABLE:
            # Fallback to simple base64 encoding
            return base64.b64encode(data.encode()).decode()
        
        try:
            fernet = Fernet(self.encryption_key)
            encrypted_data = fernet.encrypt(data.encode())
            return base64.b64encode(encrypted_data).decode()
        except Exception as e:
            logger.error("Failed to encrypt data", error=str(e))
            return data

    async def decrypt_sensitive_data(self, encrypted_data: str) -> str:
        """Decrypt sensitive data"""
        
        if not CRYPTOGRAPHY_AVAILABLE:
            # Fallback to simple base64 decoding
            return base64.b64decode(encrypted_data.encode()).decode()
        
        try:
            fernet = Fernet(self.encryption_key)
            decoded_data = base64.b64decode(encrypted_data.encode())
            decrypted_data = fernet.decrypt(decoded_data)
            return decrypted_data.decode()
        except Exception as e:
            logger.error("Failed to decrypt data", error=str(e))
            return encrypted_data

    async def hash_password(self, password: str) -> str:
        """Hash password securely"""
        
        if BCRYPT_AVAILABLE:
            try:
                salt = bcrypt.gensalt()
                hashed = bcrypt.hashpw(password.encode(), salt)
                return hashed.decode()
            except Exception as e:
                logger.error("Failed to hash password with bcrypt", error=str(e))
        
        # Fallback to PBKDF2
        if CRYPTOGRAPHY_AVAILABLE:
            try:
                salt = secrets.token_bytes(16)
                kdf = PBKDF2HMAC(
                    algorithm=hashes.SHA256(),
                    length=32,
                    salt=salt,
                    iterations=100000,
                )
                key = base64.b64encode(kdf.derive(password.encode()))
                return f"pbkdf2_sha256$100000${base64.b64encode(salt).decode()}${key.decode()}"
            except Exception as e:
                logger.error("Failed to hash password with PBKDF2", error=str(e))
        
        # Fallback to simple hash (not recommended for production)
        return hashlib.sha256(password.encode()).hexdigest()

    async def verify_password(self, password: str, hashed: str) -> bool:
        """Verify password against hash"""
        
        if BCRYPT_AVAILABLE:
            try:
                return bcrypt.checkpw(password.encode(), hashed.encode())
            except Exception as e:
                logger.error("Failed to verify password with bcrypt", error=str(e))
        
        # Check if it's a PBKDF2 hash
        if hashed.startswith("pbkdf2_sha256$"):
            try:
                parts = hashed.split("$")
                if len(parts) == 4:
                    iterations = int(parts[1])
                    salt = base64.b64decode(parts[2])
                    stored_key = parts[3]
                    
                    kdf = PBKDF2HMAC(
                        algorithm=hashes.SHA256(),
                        length=32,
                        salt=salt,
                        iterations=iterations,
                    )
                    key = base64.b64encode(kdf.derive(password.encode()))
                    return key.decode() == stored_key
            except Exception as e:
                logger.error("Failed to verify PBKDF2 password", error=str(e))
        
        # Fallback to simple hash comparison
        return hashlib.sha256(password.encode()).hexdigest() == hashed