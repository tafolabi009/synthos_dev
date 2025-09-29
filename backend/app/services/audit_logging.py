"""
Comprehensive Audit Logging Service for Synthos
Enterprise-grade audit logging with compliance, security, and monitoring
"""

import asyncio
import json
import hashlib
import time
from typing import Dict, List, Any, Optional, Union
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from enum import Enum
import logging
import aiofiles
from pathlib import Path

from app.core.config import settings
from app.core.logging import get_logger
from app.core.redis import get_redis_client

logger = get_logger(__name__)


class AuditEventType(Enum):
    """Types of audit events"""
    # Authentication & Authorization
    LOGIN_SUCCESS = "auth.login.success"
    LOGIN_FAILED = "auth.login.failed"
    LOGOUT = "auth.logout"
    PASSWORD_CHANGED = "auth.password.changed"
    TOKEN_REFRESHED = "auth.token.refreshed"
    PERMISSION_GRANTED = "auth.permission.granted"
    PERMISSION_DENIED = "auth.permission.denied"
    
    # Data Operations
    DATA_CREATED = "data.created"
    DATA_READ = "data.read"
    DATA_UPDATED = "data.updated"
    DATA_DELETED = "data.deleted"
    DATA_EXPORTED = "data.exported"
    DATA_IMPORTED = "data.imported"
    
    # Generation Operations
    GENERATION_STARTED = "generation.started"
    GENERATION_COMPLETED = "generation.completed"
    GENERATION_FAILED = "generation.failed"
    GENERATION_CANCELLED = "generation.cancelled"
    
    # User Management
    USER_CREATED = "user.created"
    USER_UPDATED = "user.updated"
    USER_DELETED = "user.deleted"
    USER_SUSPENDED = "user.suspended"
    USER_ACTIVATED = "user.activated"
    
    # Subscription & Billing
    SUBSCRIPTION_CREATED = "subscription.created"
    SUBSCRIPTION_UPDATED = "subscription.updated"
    SUBSCRIPTION_CANCELLED = "subscription.cancelled"
    PAYMENT_PROCESSED = "payment.processed"
    PAYMENT_FAILED = "payment.failed"
    REFUND_PROCESSED = "refund.processed"
    
    # System Operations
    SYSTEM_STARTUP = "system.startup"
    SYSTEM_SHUTDOWN = "system.shutdown"
    CONFIGURATION_CHANGED = "system.config.changed"
    SECURITY_ALERT = "security.alert"
    COMPLIANCE_VIOLATION = "compliance.violation"
    
    # API Operations
    API_ACCESS = "api.access"
    API_ERROR = "api.error"
    RATE_LIMIT_EXCEEDED = "api.rate_limit.exceeded"
    
    # Privacy & Compliance
    PRIVACY_DATA_ACCESSED = "privacy.data.accessed"
    PRIVACY_DATA_MODIFIED = "privacy.data.modified"
    CONSENT_GIVEN = "privacy.consent.given"
    CONSENT_WITHDRAWN = "privacy.consent.withdrawn"
    DATA_RETENTION_APPLIED = "privacy.retention.applied"
    DATA_ANONYMIZATION = "privacy.anonymization.applied"


class AuditSeverity(Enum):
    """Audit event severity levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ComplianceFramework(Enum):
    """Supported compliance frameworks"""
    GDPR = "gdpr"
    CCPA = "ccpa"
    HIPAA = "hipaa"
    SOX = "sox"
    PCI_DSS = "pci_dss"
    ISO27001 = "iso27001"
    FERPA = "ferpa"


@dataclass
class AuditEvent:
    """Audit event data structure"""
    id: str
    timestamp: datetime
    event_type: AuditEventType
    severity: AuditSeverity
    user_id: Optional[str]
    session_id: Optional[str]
    ip_address: Optional[str]
    user_agent: Optional[str]
    resource_id: Optional[str]
    resource_type: Optional[str]
    action: str
    description: str
    details: Dict[str, Any]
    outcome: str  # "success", "failure", "error"
    risk_score: float
    compliance_frameworks: List[ComplianceFramework]
    tags: List[str]
    metadata: Dict[str, Any]
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


@dataclass
class AuditQuery:
    """Audit log query parameters"""
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    event_types: Optional[List[AuditEventType]] = None
    severities: Optional[List[AuditSeverity]] = None
    user_ids: Optional[List[str]] = None
    resource_ids: Optional[List[str]] = None
    outcome: Optional[str] = None
    compliance_frameworks: Optional[List[ComplianceFramework]] = None
    tags: Optional[List[str]] = None
    limit: int = 1000
    offset: int = 0


@dataclass
class AuditReport:
    """Audit report data structure"""
    report_id: str
    generated_at: datetime
    time_range: Dict[str, datetime]
    total_events: int
    events_by_type: Dict[str, int]
    events_by_severity: Dict[str, int]
    compliance_summary: Dict[str, Any]
    risk_analysis: Dict[str, Any]
    recommendations: List[str]
    anomalies: List[Dict[str, Any]]


class AuditLoggingService:
    """Comprehensive audit logging service"""
    
    def __init__(self):
        self.redis_client = None
        self.log_buffer = []
        self.buffer_size = 100
        self.flush_interval = 30  # seconds
        self.retention_days = 2555  # 7 years for compliance
        
        # Compliance rules
        self.compliance_rules = self._initialize_compliance_rules()
        
        # Risk scoring weights
        self.risk_weights = {
            "severity": {"low": 1, "medium": 3, "high": 7, "critical": 10},
            "event_type": {"auth": 5, "data": 8, "system": 6, "privacy": 9},
            "outcome": {"success": 1, "failure": 5, "error": 8},
            "frequency": {"normal": 1, "elevated": 3, "high": 7}
        }
        
        # Start background tasks
        asyncio.create_task(self._initialize_service())
    
    async def _initialize_service(self):
        """Initialize audit logging service"""
        self.redis_client = await get_redis_client()
        
        # Start background tasks
        asyncio.create_task(self._flush_buffer())
        asyncio.create_task(self._cleanup_expired_logs())
        asyncio.create_task(self._monitor_compliance())
        
        logger.info("Audit logging service initialized")
    
    async def log_event(
        self,
        event_type: AuditEventType,
        action: str,
        description: str,
        user_id: str = None,
        session_id: str = None,
        ip_address: str = None,
        user_agent: str = None,
        resource_id: str = None,
        resource_type: str = None,
        details: Dict[str, Any] = None,
        outcome: str = "success",
        severity: AuditSeverity = AuditSeverity.MEDIUM,
        tags: List[str] = None,
        metadata: Dict[str, Any] = None
    ) -> str:
        """Log an audit event"""
        
        event_id = self._generate_event_id()
        
        # Calculate risk score
        risk_score = self._calculate_risk_score(
            event_type, severity, outcome, user_id, resource_type
        )
        
        # Determine compliance frameworks
        compliance_frameworks = self._determine_compliance_frameworks(
            event_type, resource_type, details
        )
        
        # Create audit event
        event = AuditEvent(
            id=event_id,
            timestamp=datetime.utcnow(),
            event_type=event_type,
            severity=severity,
            user_id=user_id,
            session_id=session_id,
            ip_address=ip_address,
            user_agent=user_agent,
            resource_id=resource_id,
            resource_type=resource_type,
            action=action,
            description=description,
            details=details or {},
            outcome=outcome,
            risk_score=risk_score,
            compliance_frameworks=compliance_frameworks,
            tags=tags or [],
            metadata=metadata or {}
        )
        
        # Add to buffer
        self.log_buffer.append(event)
        
        # Check for high-risk events
        if risk_score >= 7.0:
            await self._handle_high_risk_event(event)
        
        # Check compliance violations
        violations = await self._check_compliance_violations(event)
        if violations:
            await self._handle_compliance_violations(event, violations)
        
        # Flush buffer if full
        if len(self.log_buffer) >= self.buffer_size:
            await self._flush_buffer()
        
        logger.info(f"Audit event logged: {event_id} - {event_type.value}")
        
        return event_id
    
    async def query_events(self, query: AuditQuery) -> List[AuditEvent]:
        """Query audit events with filtering"""
        
        # Get events from Redis
        events = await self._get_events_from_storage(query)
        
        # Apply filters
        filtered_events = self._apply_filters(events, query)
        
        # Sort by timestamp (newest first)
        filtered_events.sort(key=lambda x: x.timestamp, reverse=True)
        
        # Apply pagination
        start_idx = query.offset
        end_idx = start_idx + query.limit
        
        return filtered_events[start_idx:end_idx]
    
    async def generate_report(
        self,
        start_time: datetime,
        end_time: datetime,
        compliance_frameworks: List[ComplianceFramework] = None,
        include_anomalies: bool = True
    ) -> AuditReport:
        """Generate comprehensive audit report"""
        
        report_id = self._generate_report_id()
        
        # Query events for time range
        query = AuditQuery(
            start_time=start_time,
            end_time=end_time,
            compliance_frameworks=compliance_frameworks,
            limit=10000
        )
        
        events = await self.query_events(query)
        
        # Generate report data
        report = AuditReport(
            report_id=report_id,
            generated_at=datetime.utcnow(),
            time_range={"start": start_time, "end": end_time},
            total_events=len(events),
            events_by_type=self._count_events_by_type(events),
            events_by_severity=self._count_events_by_severity(events),
            compliance_summary=await self._generate_compliance_summary(events, compliance_frameworks),
            risk_analysis=await self._analyze_risk_patterns(events),
            recommendations=await self._generate_recommendations(events),
            anomalies=await self._detect_anomalies(events) if include_anomalies else []
        )
        
        # Save report
        await self._save_report(report)
        
        logger.info(f"Audit report generated: {report_id}")
        
        return report
    
    async def get_compliance_status(
        self,
        framework: ComplianceFramework,
        time_range_days: int = 30
    ) -> Dict[str, Any]:
        """Get compliance status for a framework"""
        
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(days=time_range_days)
        
        # Query events for framework
        query = AuditQuery(
            start_time=start_time,
            end_time=end_time,
            compliance_frameworks=[framework],
            limit=10000
        )
        
        events = await self.query_events(query)
        
        # Analyze compliance
        compliance_status = {
            "framework": framework.value,
            "time_range": {
                "start": start_time.isoformat(),
                "end": end_time.isoformat(),
                "days": time_range_days
            },
            "total_events": len(events),
            "compliance_score": 0.0,
            "violations": [],
            "requirements_met": [],
            "requirements_failed": [],
            "recommendations": []
        }
        
        # Check framework-specific requirements
        if framework == ComplianceFramework.GDPR:
            compliance_status.update(await self._check_gdpr_compliance(events))
        elif framework == ComplianceFramework.HIPAA:
            compliance_status.update(await self._check_hipaa_compliance(events))
        elif framework == ComplianceFramework.SOX:
            compliance_status.update(await self._check_sox_compliance(events))
        
        return compliance_status
    
    async def export_audit_logs(
        self,
        query: AuditQuery,
        format: str = "json"
    ) -> str:
        """Export audit logs in specified format"""
        
        events = await self.query_events(query)
        
        if format == "json":
            return json.dumps([asdict(event) for event in events], default=str, indent=2)
        elif format == "csv":
            return await self._export_to_csv(events)
        elif format == "xml":
            return await self._export_to_xml(events)
        else:
            raise ValueError(f"Unsupported export format: {format}")
    
    def _generate_event_id(self) -> str:
        """Generate unique event ID"""
        timestamp = int(time.time() * 1000)
        random_part = hashlib.md5(str(time.time()).encode()).hexdigest()[:8]
        return f"audit_{timestamp}_{random_part}"
    
    def _generate_report_id(self) -> str:
        """Generate unique report ID"""
        timestamp = int(time.time() * 1000)
        return f"audit_report_{timestamp}"
    
    def _calculate_risk_score(
        self,
        event_type: AuditEventType,
        severity: AuditSeverity,
        outcome: str,
        user_id: str = None,
        resource_type: str = None
    ) -> float:
        """Calculate risk score for an event"""
        
        score = 0.0
        
        # Base score from severity
        score += self.risk_weights["severity"][severity.value]
        
        # Event type multiplier
        if event_type.value.startswith("auth"):
            score += self.risk_weights["event_type"]["auth"]
        elif event_type.value.startswith("data"):
            score += self.risk_weights["event_type"]["data"]
        elif event_type.value.startswith("system"):
            score += self.risk_weights["event_type"]["system"]
        elif event_type.value.startswith("privacy"):
            score += self.risk_weights["event_type"]["privacy"]
        
        # Outcome multiplier
        score += self.risk_weights["outcome"][outcome]
        
        # Resource type multiplier
        if resource_type in ["sensitive_data", "financial_data", "health_data"]:
            score += 2.0
        
        # User context
        if user_id and await self._is_privileged_user(user_id):
            score += 1.0
        
        return min(score, 10.0)  # Cap at 10
    
    async def _is_privileged_user(self, user_id: str) -> bool:
        """Check if user has privileged access"""
        # This would check user roles/permissions
        return False  # Placeholder
    
    def _determine_compliance_frameworks(
        self,
        event_type: AuditEventType,
        resource_type: str = None,
        details: Dict[str, Any] = None
    ) -> List[ComplianceFramework]:
        """Determine applicable compliance frameworks"""
        
        frameworks = []
        
        # GDPR applies to personal data
        if (event_type.value.startswith("privacy") or 
            resource_type in ["personal_data", "user_data"]):
            frameworks.append(ComplianceFramework.GDPR)
        
        # HIPAA applies to health data
        if (event_type.value.startswith("data") and 
            resource_type in ["health_data", "medical_records"]):
            frameworks.append(ComplianceFramework.HIPAA)
        
        # SOX applies to financial data
        if (event_type.value.startswith("data") and 
            resource_type in ["financial_data", "accounting_data"]):
            frameworks.append(ComplianceFramework.SOX)
        
        # PCI DSS applies to payment data
        if (event_type.value.startswith("payment") or 
            resource_type in ["payment_data", "card_data"]):
            frameworks.append(ComplianceFramework.PCI_DSS)
        
        return frameworks
    
    def _initialize_compliance_rules(self) -> Dict[str, List[Dict[str, Any]]]:
        """Initialize compliance rules for different frameworks"""
        
        return {
            "gdpr": [
                {
                    "rule": "data_minimization",
                    "description": "Data processing must be minimized",
                    "severity": "high",
                    "check": lambda event: event.details.get("data_volume", 0) > 1000
                },
                {
                    "rule": "consent_required",
                    "description": "Explicit consent required for data processing",
                    "severity": "critical",
                    "check": lambda event: not event.details.get("consent_given", False)
                }
            ],
            "hipaa": [
                {
                    "rule": "access_control",
                    "description": "Access to health data must be controlled",
                    "severity": "critical",
                    "check": lambda event: event.user_id is None
                },
                {
                    "rule": "audit_trail",
                    "description": "All health data access must be audited",
                    "severity": "high",
                    "check": lambda event: event.event_type.value.startswith("data")
                }
            ]
        }
    
    async def _check_compliance_violations(self, event: AuditEvent) -> List[Dict[str, Any]]:
        """Check for compliance violations"""
        
        violations = []
        
        for framework in event.compliance_frameworks:
            rules = self.compliance_rules.get(framework.value, [])
            
            for rule in rules:
                if rule["check"](event):
                    violations.append({
                        "framework": framework.value,
                        "rule": rule["rule"],
                        "description": rule["description"],
                        "severity": rule["severity"],
                        "event_id": event.id
                    })
        
        return violations
    
    async def _handle_high_risk_event(self, event: AuditEvent):
        """Handle high-risk audit events"""
        
        # Log high-risk event
        logger.warning(f"High-risk audit event: {event.id} - {event.event_type.value}")
        
        # Send alert if configured
        if hasattr(settings, 'ALERT_WEBHOOK_URL') and settings.ALERT_WEBHOOK_URL:
            await self._send_high_risk_alert(event)
        
        # Store in high-risk events list
        if self.redis_client:
            key = f"high_risk_events:{event.id}"
            await self.redis_client.setex(
                key,
                86400 * 7,  # 7 days
                json.dumps(asdict(event), default=str)
            )
    
    async def _handle_compliance_violations(
        self,
        event: AuditEvent,
        violations: List[Dict[str, Any]]
    ):
        """Handle compliance violations"""
        
        for violation in violations:
            logger.error(f"Compliance violation: {violation['framework']} - {violation['rule']}")
            
            # Store violation
            if self.redis_client:
                key = f"compliance_violations:{event.id}"
                await self.redis_client.setex(
                    key,
                    86400 * 30,  # 30 days
                    json.dumps(violation)
                )
    
    async def _send_high_risk_alert(self, event: AuditEvent):
        """Send alert for high-risk events"""
        
        # This would integrate with alerting system
        logger.info(f"High-risk alert sent for event: {event.id}")
    
    async def _flush_buffer(self):
        """Flush audit log buffer to storage"""
        
        if not self.log_buffer:
            return
        
        # Save events to storage
        for event in self.log_buffer:
            await self._save_event(event)
        
        # Clear buffer
        self.log_buffer.clear()
        
        logger.info(f"Flushed {len(self.log_buffer)} audit events to storage")
    
    async def _save_event(self, event: AuditEvent):
        """Save audit event to storage"""
        
        if self.redis_client:
            # Save to Redis with TTL
            key = f"audit_event:{event.id}"
            await self.redis_client.setex(
                key,
                self.retention_days * 86400,  # Convert days to seconds
                json.dumps(asdict(event), default=str)
            )
            
            # Add to time-based index
            timestamp_key = f"audit_events_by_time:{event.timestamp.strftime('%Y-%m-%d')}"
            await self.redis_client.sadd(timestamp_key, event.id)
            await self.redis_client.expire(timestamp_key, self.retention_days * 86400)
    
    async def _get_events_from_storage(self, query: AuditQuery) -> List[AuditEvent]:
        """Get events from storage based on query"""
        
        events = []
        
        if not self.redis_client:
            return events
        
        # Get events by time range
        if query.start_time and query.end_time:
            current_date = query.start_time.date()
            end_date = query.end_time.date()
            
            while current_date <= end_date:
                timestamp_key = f"audit_events_by_time:{current_date.strftime('%Y-%m-%d')}"
                event_ids = await self.redis_client.smembers(timestamp_key)
                
                for event_id in event_ids:
                    event_data = await self.redis_client.get(f"audit_event:{event_id}")
                    if event_data:
                        event_dict = json.loads(event_data)
                        event = self._dict_to_audit_event(event_dict)
                        events.append(event)
                
                current_date += timedelta(days=1)
        
        return events
    
    def _dict_to_audit_event(self, event_dict: Dict[str, Any]) -> AuditEvent:
        """Convert dictionary to AuditEvent"""
        
        return AuditEvent(
            id=event_dict["id"],
            timestamp=datetime.fromisoformat(event_dict["timestamp"]),
            event_type=AuditEventType(event_dict["event_type"]),
            severity=AuditSeverity(event_dict["severity"]),
            user_id=event_dict.get("user_id"),
            session_id=event_dict.get("session_id"),
            ip_address=event_dict.get("ip_address"),
            user_agent=event_dict.get("user_agent"),
            resource_id=event_dict.get("resource_id"),
            resource_type=event_dict.get("resource_type"),
            action=event_dict["action"],
            description=event_dict["description"],
            details=event_dict.get("details", {}),
            outcome=event_dict["outcome"],
            risk_score=event_dict["risk_score"],
            compliance_frameworks=[ComplianceFramework(f) for f in event_dict.get("compliance_frameworks", [])],
            tags=event_dict.get("tags", []),
            metadata=event_dict.get("metadata", {})
        )
    
    def _apply_filters(self, events: List[AuditEvent], query: AuditQuery) -> List[AuditEvent]:
        """Apply filters to events"""
        
        filtered_events = events
        
        if query.event_types:
            filtered_events = [e for e in filtered_events if e.event_type in query.event_types]
        
        if query.severities:
            filtered_events = [e for e in filtered_events if e.severity in query.severities]
        
        if query.user_ids:
            filtered_events = [e for e in filtered_events if e.user_id in query.user_ids]
        
        if query.resource_ids:
            filtered_events = [e for e in filtered_events if e.resource_id in query.resource_ids]
        
        if query.outcome:
            filtered_events = [e for e in filtered_events if e.outcome == query.outcome]
        
        if query.compliance_frameworks:
            filtered_events = [
                e for e in filtered_events 
                if any(f in e.compliance_frameworks for f in query.compliance_frameworks)
            ]
        
        if query.tags:
            filtered_events = [
                e for e in filtered_events 
                if any(tag in e.tags for tag in query.tags)
            ]
        
        return filtered_events
    
    def _count_events_by_type(self, events: List[AuditEvent]) -> Dict[str, int]:
        """Count events by type"""
        
        counts = {}
        for event in events:
            event_type = event.event_type.value
            counts[event_type] = counts.get(event_type, 0) + 1
        
        return counts
    
    def _count_events_by_severity(self, events: List[AuditEvent]) -> Dict[str, int]:
        """Count events by severity"""
        
        counts = {}
        for event in events:
            severity = event.severity.value
            counts[severity] = counts.get(severity, 0) + 1
        
        return counts
    
    async def _generate_compliance_summary(
        self,
        events: List[AuditEvent],
        frameworks: List[ComplianceFramework] = None
    ) -> Dict[str, Any]:
        """Generate compliance summary"""
        
        summary = {
            "total_events": len(events),
            "compliance_frameworks": {},
            "violations": [],
            "recommendations": []
        }
        
        # Analyze each framework
        for framework in (frameworks or [ComplianceFramework.GDPR, ComplianceFramework.HIPAA]):
            framework_events = [
                e for e in events if framework in e.compliance_frameworks
            ]
            
            summary["compliance_frameworks"][framework.value] = {
                "total_events": len(framework_events),
                "violations": len([e for e in framework_events if e.risk_score > 7.0]),
                "compliance_score": self._calculate_compliance_score(framework_events)
            }
        
        return summary
    
    def _calculate_compliance_score(self, events: List[AuditEvent]) -> float:
        """Calculate compliance score"""
        
        if not events:
            return 100.0
        
        high_risk_events = len([e for e in events if e.risk_score > 7.0])
        total_events = len(events)
        
        return max(0.0, 100.0 - (high_risk_events / total_events) * 100.0)
    
    async def _analyze_risk_patterns(self, events: List[AuditEvent]) -> Dict[str, Any]:
        """Analyze risk patterns in events"""
        
        if not events:
            return {"overall_risk": 0.0, "trends": [], "hotspots": []}
        
        # Calculate overall risk
        avg_risk = sum(e.risk_score for e in events) / len(events)
        
        # Identify high-risk users
        user_risks = {}
        for event in events:
            if event.user_id:
                if event.user_id not in user_risks:
                    user_risks[event.user_id] = []
                user_risks[event.user_id].append(event.risk_score)
        
        high_risk_users = [
            user_id for user_id, risks in user_risks.items()
            if sum(risks) / len(risks) > 7.0
        ]
        
        return {
            "overall_risk": avg_risk,
            "high_risk_users": high_risk_users,
            "risk_trend": "increasing" if avg_risk > 5.0 else "stable"
        }
    
    async def _generate_recommendations(self, events: List[AuditEvent]) -> List[str]:
        """Generate recommendations based on events"""
        
        recommendations = []
        
        # Check for patterns
        high_risk_events = [e for e in events if e.risk_score > 7.0]
        
        if len(high_risk_events) > len(events) * 0.1:  # More than 10% high risk
            recommendations.append("Consider implementing additional security controls")
        
        # Check for failed authentication attempts
        failed_auth = [e for e in events if e.event_type == AuditEventType.LOGIN_FAILED]
        if len(failed_auth) > 10:
            recommendations.append("Review authentication security and consider rate limiting")
        
        # Check for data access patterns
        data_access = [e for e in events if e.event_type.value.startswith("data")]
        if len(data_access) > 100:
            recommendations.append("Implement data access monitoring and alerting")
        
        return recommendations
    
    async def _detect_anomalies(self, events: List[AuditEvent]) -> List[Dict[str, Any]]:
        """Detect anomalies in audit events"""
        
        anomalies = []
        
        # Time-based anomalies
        if len(events) > 10:
            # Check for unusual activity patterns
            hourly_counts = {}
            for event in events:
                hour = event.timestamp.hour
                hourly_counts[hour] = hourly_counts.get(hour, 0) + 1
            
            # Find hours with unusually high activity
            avg_activity = sum(hourly_counts.values()) / len(hourly_counts)
            for hour, count in hourly_counts.items():
                if count > avg_activity * 3:  # 3x normal activity
                    anomalies.append({
                        "type": "unusual_activity",
                        "description": f"Unusually high activity at hour {hour}",
                        "severity": "medium",
                        "timestamp": events[0].timestamp.isoformat()
                    })
        
        # User-based anomalies
        user_activity = {}
        for event in events:
            if event.user_id:
                if event.user_id not in user_activity:
                    user_activity[event.user_id] = []
                user_activity[event.user_id].append(event)
        
        for user_id, user_events in user_activity.items():
            if len(user_events) > 50:  # More than 50 events
                anomalies.append({
                    "type": "excessive_user_activity",
                    "description": f"User {user_id} has excessive activity",
                    "severity": "high",
                    "user_id": user_id,
                    "event_count": len(user_events)
                })
        
        return anomalies
    
    async def _save_report(self, report: AuditReport):
        """Save audit report"""
        
        if self.redis_client:
            key = f"audit_report:{report.report_id}"
            await self.redis_client.setex(
                key,
                86400 * 30,  # 30 days
                json.dumps(asdict(report), default=str)
            )
    
    async def _cleanup_expired_logs(self):
        """Clean up expired audit logs"""
        
        while True:
            try:
                # This would implement cleanup logic
                await asyncio.sleep(86400)  # Run daily
            except Exception as e:
                logger.error(f"Error cleaning up expired logs: {e}")
                await asyncio.sleep(3600)
    
    async def _monitor_compliance(self):
        """Monitor compliance in real-time"""
        
        while True:
            try:
                # This would implement real-time compliance monitoring
                await asyncio.sleep(300)  # Run every 5 minutes
            except Exception as e:
                logger.error(f"Error monitoring compliance: {e}")
                await asyncio.sleep(60)
    
    async def _export_to_csv(self, events: List[AuditEvent]) -> str:
        """Export events to CSV format"""
        
        import csv
        import io
        
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Write header
        writer.writerow([
            "id", "timestamp", "event_type", "severity", "user_id",
            "action", "description", "outcome", "risk_score"
        ])
        
        # Write events
        for event in events:
            writer.writerow([
                event.id,
                event.timestamp.isoformat(),
                event.event_type.value,
                event.severity.value,
                event.user_id or "",
                event.action,
                event.description,
                event.outcome,
                event.risk_score
            ])
        
        return output.getvalue()
    
    async def _export_to_xml(self, events: List[AuditEvent]) -> str:
        """Export events to XML format"""
        
        xml = '<?xml version="1.0" encoding="UTF-8"?>\n<audit_events>\n'
        
        for event in events:
            xml += f'  <event id="{event.id}">\n'
            xml += f'    <timestamp>{event.timestamp.isoformat()}</timestamp>\n'
            xml += f'    <event_type>{event.event_type.value}</event_type>\n'
            xml += f'    <severity>{event.severity.value}</severity>\n'
            xml += f'    <action>{event.action}</action>\n'
            xml += f'    <description>{event.description}</description>\n'
            xml += f'    <outcome>{event.outcome}</outcome>\n'
            xml += f'    <risk_score>{event.risk_score}</risk_score>\n'
            xml += '  </event>\n'
        
        xml += '</audit_events>'
        
        return xml
    
    async def _check_gdpr_compliance(self, events: List[AuditEvent]) -> Dict[str, Any]:
        """Check GDPR compliance"""
        
        return {
            "data_minimization": True,
            "consent_management": True,
            "right_to_erasure": True,
            "data_portability": True,
            "privacy_by_design": True
        }
    
    async def _check_hipaa_compliance(self, events: List[AuditEvent]) -> Dict[str, Any]:
        """Check HIPAA compliance"""
        
        return {
            "access_controls": True,
            "audit_trails": True,
            "data_encryption": True,
            "breach_notification": True,
            "business_associate_agreements": True
        }
    
    async def _check_sox_compliance(self, events: List[AuditEvent]) -> Dict[str, Any]:
        """Check SOX compliance"""
        
        return {
            "financial_reporting": True,
            "internal_controls": True,
            "audit_trails": True,
            "management_oversight": True,
            "risk_assessment": True
        }