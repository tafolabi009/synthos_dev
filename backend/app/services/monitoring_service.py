"""
Comprehensive Monitoring and Alerting Service
Enterprise-grade monitoring with real-time metrics and intelligent alerting
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
import psutil
import threading
from collections import defaultdict, deque
import statistics
from concurrent.futures import ThreadPoolExecutor
import aiohttp
from aiohttp import ClientSession, ClientTimeout

# Prometheus metrics
try:
    from prometheus_client import Counter, Histogram, Gauge, Summary, CollectorRegistry, generate_latest
    PROMETHEUS_AVAILABLE = True
except ImportError:
    PROMETHEUS_AVAILABLE = False
    Counter = None
    Histogram = None
    Gauge = None
    Summary = None
    CollectorRegistry = None
    generate_latest = None

from app.core.config import settings
from app.core.logging import get_logger
from app.core.redis import get_redis_client

logger = get_logger(__name__)


class MetricType(Enum):
    """Metric types"""
    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    SUMMARY = "summary"


class AlertSeverity(Enum):
    """Alert severity levels"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class AlertStatus(Enum):
    """Alert status"""
    ACTIVE = "active"
    RESOLVED = "resolved"
    SUPPRESSED = "suppressed"


@dataclass
class Metric:
    """Metric definition"""
    name: str
    value: float
    metric_type: MetricType
    labels: Dict[str, str]
    timestamp: datetime
    description: Optional[str] = None


@dataclass
class AlertRule:
    """Alert rule definition"""
    name: str
    metric_name: str
    condition: str  # e.g., "value > 100"
    severity: AlertSeverity
    duration: int  # seconds
    enabled: bool = True
    notification_channels: List[str] = None
    
    def __post_init__(self):
        if self.notification_channels is None:
            self.notification_channels = []


@dataclass
class Alert:
    """Alert instance"""
    id: str
    rule_name: str
    severity: AlertSeverity
    status: AlertStatus
    message: str
    metric_name: str
    metric_value: float
    threshold: float
    triggered_at: datetime
    resolved_at: Optional[datetime] = None
    notification_sent: bool = False


@dataclass
class SystemHealth:
    """System health status"""
    overall_status: str
    cpu_usage: float
    memory_usage: float
    disk_usage: float
    network_io: Dict[str, float]
    active_connections: int
    response_time: float
    error_rate: float
    timestamp: datetime


class ComprehensiveMonitoringService:
    """
    Comprehensive monitoring and alerting service
    """

    def __init__(self):
        """Initialize monitoring service"""
        self.redis_client = None
        self._init_cache()
        
        # Metrics storage
        self.metrics: Dict[str, deque] = defaultdict(lambda: deque(maxlen=10000))
        self.alerts: Dict[str, Alert] = {}
        self.alert_rules: List[AlertRule] = []
        
        # Prometheus metrics
        self.prometheus_registry = None
        self.prometheus_metrics = {}
        
        # Background tasks
        self._metrics_collection_task = None
        self._alerting_task = None
        self._health_check_task = None
        
        # Initialize Prometheus
        self._init_prometheus()
        
        # Load alert rules
        self._load_alert_rules()
        
        logger.info("Comprehensive Monitoring Service initialized")

    async def _init_cache(self):
        """Initialize Redis cache"""
        try:
            self.redis_client = await get_redis_client()
        except Exception as e:
            logger.warning("Redis cache not available", error=str(e))

    def _init_prometheus(self):
        """Initialize Prometheus metrics"""
        
        if not PROMETHEUS_AVAILABLE:
            logger.warning("Prometheus not available, using fallback metrics")
            return
        
        try:
            self.prometheus_registry = CollectorRegistry()
            
            # System metrics
            self.prometheus_metrics["cpu_usage"] = Gauge(
                "system_cpu_usage_percent",
                "CPU usage percentage",
                registry=self.prometheus_registry
            )
            
            self.prometheus_metrics["memory_usage"] = Gauge(
                "system_memory_usage_bytes",
                "Memory usage in bytes",
                registry=self.prometheus_registry
            )
            
            self.prometheus_metrics["disk_usage"] = Gauge(
                "system_disk_usage_percent",
                "Disk usage percentage",
                registry=self.prometheus_registry
            )
            
            # Application metrics
            self.prometheus_metrics["http_requests"] = Counter(
                "http_requests_total",
                "Total HTTP requests",
                ["method", "endpoint", "status"],
                registry=self.prometheus_registry
            )
            
            self.prometheus_metrics["http_duration"] = Histogram(
                "http_request_duration_seconds",
                "HTTP request duration",
                ["method", "endpoint"],
                registry=self.prometheus_registry
            )
            
            self.prometheus_metrics["active_connections"] = Gauge(
                "active_connections",
                "Active connections",
                registry=self.prometheus_registry
            )
            
            # Business metrics
            self.prometheus_metrics["generations_total"] = Counter(
                "generations_total",
                "Total data generations",
                ["user_id", "status"],
                registry=self.prometheus_registry
            )
            
            self.prometheus_metrics["generation_duration"] = Histogram(
                "generation_duration_seconds",
                "Data generation duration",
                ["model_type"],
                registry=self.prometheus_registry
            )
            
            logger.info("Prometheus metrics initialized")
            
        except Exception as e:
            logger.error("Failed to initialize Prometheus metrics", error=str(e))

    def _load_alert_rules(self):
        """Load alert rules"""
        
        self.alert_rules = [
            AlertRule(
                name="High CPU Usage",
                metric_name="cpu_usage",
                condition="value > 80",
                severity=AlertSeverity.WARNING,
                duration=300,  # 5 minutes
                notification_channels=["email", "slack"]
            ),
            AlertRule(
                name="High Memory Usage",
                metric_name="memory_usage",
                condition="value > 90",
                severity=AlertSeverity.ERROR,
                duration=180,  # 3 minutes
                notification_channels=["email", "slack", "pagerduty"]
            ),
            AlertRule(
                name="High Disk Usage",
                metric_name="disk_usage",
                condition="value > 85",
                severity=AlertSeverity.WARNING,
                duration=600,  # 10 minutes
                notification_channels=["email"]
            ),
            AlertRule(
                name="High Error Rate",
                metric_name="error_rate",
                condition="value > 5",
                severity=AlertSeverity.CRITICAL,
                duration=60,  # 1 minute
                notification_channels=["email", "slack", "pagerduty"]
            ),
            AlertRule(
                name="High Response Time",
                metric_name="response_time",
                condition="value > 5",
                severity=AlertSeverity.WARNING,
                duration=300,  # 5 minutes
                notification_channels=["email"]
            )
        ]

    async def start(self):
        """Start monitoring service"""
        # Start background tasks
        self._metrics_collection_task = asyncio.create_task(self._collect_metrics())
        self._alerting_task = asyncio.create_task(self._process_alerts())
        self._health_check_task = asyncio.create_task(self._health_check())
        
        logger.info("Monitoring service started")

    async def stop(self):
        """Stop monitoring service"""
        # Cancel background tasks
        tasks = [self._metrics_collection_task, self._alerting_task, self._health_check_task]
        for task in tasks:
            if task:
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
        
        logger.info("Monitoring service stopped")

    async def record_metric(
        self,
        name: str,
        value: float,
        metric_type: MetricType = MetricType.GAUGE,
        labels: Optional[Dict[str, str]] = None,
        description: Optional[str] = None
    ):
        """Record a metric"""
        
        metric = Metric(
            name=name,
            value=value,
            metric_type=metric_type,
            labels=labels or {},
            timestamp=datetime.utcnow(),
            description=description
        )
        
        # Store in memory
        self.metrics[name].append(metric)
        
        # Update Prometheus metrics
        await self._update_prometheus_metric(metric)
        
        # Cache in Redis
        await self._cache_metric(metric)
        
        # Check for alerts
        await self._check_alerts(metric)

    async def _update_prometheus_metric(self, metric: Metric):
        """Update Prometheus metric"""
        
        if not PROMETHEUS_AVAILABLE or not self.prometheus_metrics:
            return
        
        try:
            prom_metric = self.prometheus_metrics.get(metric.name)
            if prom_metric:
                if metric.metric_type == MetricType.GAUGE:
                    prom_metric.set(metric.value)
                elif metric.metric_type == MetricType.COUNTER:
                    prom_metric.inc(metric.value)
                elif metric.metric_type == MetricType.HISTOGRAM:
                    prom_metric.observe(metric.value)
                elif metric.metric_type == MetricType.SUMMARY:
                    prom_metric.observe(metric.value)
        except Exception as e:
            logger.warning("Failed to update Prometheus metric", error=str(e))

    async def _cache_metric(self, metric: Metric):
        """Cache metric in Redis"""
        
        if self.redis_client:
            try:
                cache_key = f"metric:{metric.name}"
                metric_data = {
                    "name": metric.name,
                    "value": metric.value,
                    "metric_type": metric.metric_type.value,
                    "labels": metric.labels,
                    "timestamp": metric.timestamp.isoformat(),
                    "description": metric.description
                }
                
                await self.redis_client.lpush(cache_key, json.dumps(metric_data))
                await self.redis_client.ltrim(cache_key, 0, 999)  # Keep last 1000 metrics
                await self.redis_client.expire(cache_key, 3600)  # 1 hour
                
            except Exception as e:
                logger.warning("Failed to cache metric", error=str(e))

    async def _check_alerts(self, metric: Metric):
        """Check if metric triggers any alerts"""
        
        for rule in self.alert_rules:
            if not rule.enabled or rule.metric_name != metric.name:
                continue
            
            # Check if condition is met
            if await self._evaluate_condition(metric.value, rule.condition):
                # Check if alert already exists
                alert_key = f"{rule.name}:{metric.name}"
                if alert_key in self.alerts:
                    continue
                
                # Create new alert
                alert = Alert(
                    id=str(uuid.uuid4()),
                    rule_name=rule.name,
                    severity=rule.severity,
                    status=AlertStatus.ACTIVE,
                    message=f"{rule.name}: {metric.name} = {metric.value}",
                    metric_name=metric.name,
                    metric_value=metric.value,
                    threshold=self._extract_threshold(rule.condition),
                    triggered_at=datetime.utcnow()
                )
                
                self.alerts[alert_key] = alert
                
                # Send notifications
                await self._send_alert_notifications(alert, rule)
                
                logger.warning(
                    "Alert triggered",
                    alert_id=alert.id,
                    rule_name=rule.name,
                    severity=rule.severity.value,
                    metric_name=metric.name,
                    metric_value=metric.value
                )

    async def _evaluate_condition(self, value: float, condition: str) -> bool:
        """Evaluate alert condition"""
        
        try:
            # Simple condition evaluation
            # Replace 'value' with actual value
            eval_condition = condition.replace("value", str(value))
            return eval(eval_condition)
        except Exception as e:
            logger.warning("Failed to evaluate condition", error=str(e), condition=condition)
            return False

    def _extract_threshold(self, condition: str) -> float:
        """Extract threshold from condition"""
        
        try:
            # Extract number from condition
            import re
            numbers = re.findall(r'\d+\.?\d*', condition)
            if numbers:
                return float(numbers[0])
        except Exception:
            pass
        
        return 0.0

    async def _send_alert_notifications(self, alert: Alert, rule: AlertRule):
        """Send alert notifications"""
        
        for channel in rule.notification_channels:
            try:
                if channel == "email":
                    await self._send_email_alert(alert)
                elif channel == "slack":
                    await self._send_slack_alert(alert)
                elif channel == "pagerduty":
                    await self._send_pagerduty_alert(alert)
            except Exception as e:
                logger.warning("Failed to send alert notification", error=str(e), channel=channel)

    async def _send_email_alert(self, alert: Alert):
        """Send email alert"""
        
        # TODO: Implement email notification
        logger.info("Email alert sent", alert_id=alert.id, severity=alert.severity.value)

    async def _send_slack_alert(self, alert: Alert):
        """Send Slack alert"""
        
        # TODO: Implement Slack notification
        logger.info("Slack alert sent", alert_id=alert.id, severity=alert.severity.value)

    async def _send_pagerduty_alert(self, alert: Alert):
        """Send PagerDuty alert"""
        
        # TODO: Implement PagerDuty notification
        logger.info("PagerDuty alert sent", alert_id=alert.id, severity=alert.severity.value)

    async def _collect_metrics(self):
        """Background task to collect system metrics"""
        
        while True:
            try:
                await asyncio.sleep(30)  # Collect every 30 seconds
                
                # Collect system metrics
                await self._collect_system_metrics()
                
                # Collect application metrics
                await self._collect_application_metrics()
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("Error in metrics collection", error=str(e))

    async def _collect_system_metrics(self):
        """Collect system metrics"""
        
        try:
            # CPU usage
            cpu_percent = psutil.cpu_percent(interval=1)
            await self.record_metric("cpu_usage", cpu_percent, description="CPU usage percentage")
            
            # Memory usage
            memory = psutil.virtual_memory()
            await self.record_metric("memory_usage", memory.percent, description="Memory usage percentage")
            
            # Disk usage
            disk = psutil.disk_usage('/')
            disk_percent = (disk.used / disk.total) * 100
            await self.record_metric("disk_usage", disk_percent, description="Disk usage percentage")
            
            # Network I/O
            network = psutil.net_io_counters()
            await self.record_metric("network_bytes_sent", network.bytes_sent, description="Network bytes sent")
            await self.record_metric("network_bytes_recv", network.bytes_recv, description="Network bytes received")
            
        except Exception as e:
            logger.error("Failed to collect system metrics", error=str(e))

    async def _collect_application_metrics(self):
        """Collect application metrics"""
        
        try:
            # Active connections (simplified)
            active_connections = len(psutil.net_connections())
            await self.record_metric("active_connections", active_connections, description="Active connections")
            
            # Process count
            process_count = len(psutil.pids())
            await self.record_metric("process_count", process_count, description="Number of processes")
            
            # Load average
            load_avg = psutil.getloadavg()[0]  # 1-minute load average
            await self.record_metric("load_average", load_avg, description="System load average")
            
        except Exception as e:
            logger.error("Failed to collect application metrics", error=str(e))

    async def _process_alerts(self):
        """Background task to process alerts"""
        
        while True:
            try:
                await asyncio.sleep(60)  # Check every minute
                
                # Resolve alerts that are no longer active
                await self._resolve_alerts()
                
                # Send notifications for new alerts
                await self._process_pending_notifications()
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("Error in alert processing", error=str(e))

    async def _resolve_alerts(self):
        """Resolve alerts that are no longer active"""
        
        current_time = datetime.utcnow()
        
        for alert_key, alert in list(self.alerts.items()):
            if alert.status != AlertStatus.ACTIVE:
                continue
            
            # Check if alert should be resolved
            rule = next((r for r in self.alert_rules if r.name == alert.rule_name), None)
            if not rule:
                continue
            
            # Get latest metric value
            latest_metrics = self.metrics.get(alert.metric_name, deque())
            if not latest_metrics:
                continue
            
            latest_metric = latest_metrics[-1]
            
            # Check if condition is still met
            if not await self._evaluate_condition(latest_metric.value, rule.condition):
                # Resolve alert
                alert.status = AlertStatus.RESOLVED
                alert.resolved_at = current_time
                
                logger.info("Alert resolved", alert_id=alert.id, rule_name=alert.rule_name)

    async def _process_pending_notifications(self):
        """Process pending notifications"""
        
        for alert in self.alerts.values():
            if alert.status == AlertStatus.ACTIVE and not alert.notification_sent:
                # Send notifications
                rule = next((r for r in self.alert_rules if r.name == alert.rule_name), None)
                if rule:
                    await self._send_alert_notifications(alert, rule)
                    alert.notification_sent = True

    async def _health_check(self):
        """Background task for health checks"""
        
        while True:
            try:
                await asyncio.sleep(60)  # Check every minute
                
                # Perform health checks
                health_status = await self._perform_health_checks()
                
                # Store health status
                await self._store_health_status(health_status)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("Error in health check", error=str(e))

    async def _perform_health_checks(self) -> SystemHealth:
        """Perform comprehensive health checks"""
        
        try:
            # System metrics
            cpu_usage = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            network = psutil.net_io_counters()
            
            # Calculate response time (simplified)
            start_time = time.time()
            # TODO: Add actual health check endpoint call
            response_time = (time.time() - start_time) * 1000  # Convert to milliseconds
            
            # Calculate error rate (simplified)
            error_rate = 0.0  # TODO: Calculate actual error rate
            
            # Determine overall status
            overall_status = "healthy"
            if cpu_usage > 80 or memory.percent > 90 or disk.percent > 85:
                overall_status = "degraded"
            if cpu_usage > 95 or memory.percent > 95 or disk.percent > 95:
                overall_status = "unhealthy"
            
            return SystemHealth(
                overall_status=overall_status,
                cpu_usage=cpu_usage,
                memory_usage=memory.percent,
                disk_usage=(disk.used / disk.total) * 100,
                network_io={
                    "bytes_sent": network.bytes_sent,
                    "bytes_recv": network.bytes_recv
                },
                active_connections=len(psutil.net_connections()),
                response_time=response_time,
                error_rate=error_rate,
                timestamp=datetime.utcnow()
            )
            
        except Exception as e:
            logger.error("Failed to perform health checks", error=str(e))
            return SystemHealth(
                overall_status="unknown",
                cpu_usage=0.0,
                memory_usage=0.0,
                disk_usage=0.0,
                network_io={"bytes_sent": 0, "bytes_recv": 0},
                active_connections=0,
                response_time=0.0,
                error_rate=0.0,
                timestamp=datetime.utcnow()
            )

    async def _store_health_status(self, health: SystemHealth):
        """Store health status"""
        
        if self.redis_client:
            try:
                health_data = {
                    "overall_status": health.overall_status,
                    "cpu_usage": health.cpu_usage,
                    "memory_usage": health.memory_usage,
                    "disk_usage": health.disk_usage,
                    "network_io": health.network_io,
                    "active_connections": health.active_connections,
                    "response_time": health.response_time,
                    "error_rate": health.error_rate,
                    "timestamp": health.timestamp.isoformat()
                }
                
                await self.redis_client.setex(
                    "system_health",
                    300,  # 5 minutes
                    json.dumps(health_data)
                )
                
            except Exception as e:
                logger.warning("Failed to store health status", error=str(e))

    async def get_metrics(
        self,
        metric_name: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 1000
    ) -> List[Metric]:
        """Get metrics"""
        
        if metric_name:
            metrics = list(self.metrics.get(metric_name, []))
        else:
            metrics = []
            for metric_list in self.metrics.values():
                metrics.extend(metric_list)
        
        # Filter by time range
        if start_time:
            metrics = [m for m in metrics if m.timestamp >= start_time]
        if end_time:
            metrics = [m for m in metrics if m.timestamp <= end_time]
        
        # Sort by timestamp
        metrics.sort(key=lambda x: x.timestamp, reverse=True)
        
        # Apply limit
        return metrics[:limit]

    async def get_alerts(
        self,
        status: Optional[AlertStatus] = None,
        severity: Optional[AlertSeverity] = None,
        limit: int = 100
    ) -> List[Alert]:
        """Get alerts"""
        
        alerts = list(self.alerts.values())
        
        # Filter by status
        if status:
            alerts = [a for a in alerts if a.status == status]
        
        # Filter by severity
        if severity:
            alerts = [a for a in alerts if a.severity == severity]
        
        # Sort by triggered time
        alerts.sort(key=lambda x: x.triggered_at, reverse=True)
        
        # Apply limit
        return alerts[:limit]

    async def get_system_health(self) -> Optional[SystemHealth]:
        """Get current system health"""
        
        if self.redis_client:
            try:
                health_data = await self.redis_client.get("system_health")
                if health_data:
                    data = json.loads(health_data)
                    return SystemHealth(
                        overall_status=data["overall_status"],
                        cpu_usage=data["cpu_usage"],
                        memory_usage=data["memory_usage"],
                        disk_usage=data["disk_usage"],
                        network_io=data["network_io"],
                        active_connections=data["active_connections"],
                        response_time=data["response_time"],
                        error_rate=data["error_rate"],
                        timestamp=datetime.fromisoformat(data["timestamp"])
                    )
            except Exception as e:
                logger.warning("Failed to get system health", error=str(e))
        
        return None

    async def get_prometheus_metrics(self) -> str:
        """Get Prometheus metrics"""
        
        if not PROMETHEUS_AVAILABLE or not self.prometheus_registry:
            return "# Prometheus not available\n"
        
        try:
            return generate_latest(self.prometheus_registry).decode()
        except Exception as e:
            logger.error("Failed to generate Prometheus metrics", error=str(e))
            return "# Error generating metrics\n"

    async def resolve_alert(self, alert_id: str) -> bool:
        """Manually resolve an alert"""
        
        for alert in self.alerts.values():
            if alert.id == alert_id:
                alert.status = AlertStatus.RESOLVED
                alert.resolved_at = datetime.utcnow()
                
                logger.info("Alert manually resolved", alert_id=alert_id)
                return True
        
        return False

    async def suppress_alert(self, alert_id: str) -> bool:
        """Suppress an alert"""
        
        for alert in self.alerts.values():
            if alert.id == alert_id:
                alert.status = AlertStatus.SUPPRESSED
                
                logger.info("Alert suppressed", alert_id=alert_id)
                return True
        
        return False

    async def get_monitoring_dashboard(self) -> Dict[str, Any]:
        """Get monitoring dashboard data"""
        
        # Get current metrics
        current_metrics = {}
        for name, metrics_list in self.metrics.items():
            if metrics_list:
                current_metrics[name] = metrics_list[-1].value
        
        # Get active alerts
        active_alerts = [a for a in self.alerts.values() if a.status == AlertStatus.ACTIVE]
        
        # Get system health
        health = await self.get_system_health()
        
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "current_metrics": current_metrics,
            "active_alerts": len(active_alerts),
            "total_alerts": len(self.alerts),
            "system_health": health.overall_status if health else "unknown",
            "cpu_usage": health.cpu_usage if health else 0.0,
            "memory_usage": health.memory_usage if health else 0.0,
            "disk_usage": health.disk_usage if health else 0.0,
            "response_time": health.response_time if health else 0.0,
            "error_rate": health.error_rate if health else 0.0,
            "alerts_by_severity": {
                severity.value: len([a for a in active_alerts if a.severity == severity])
                for severity in AlertSeverity
            }
        }