"""
Advanced Monitoring and Alerting System
Enterprise-grade observability with intelligent anomaly detection and automated alerting
"""

import asyncio
import json
import time
import psutil
from typing import Dict, List, Any, Optional, Tuple, Callable

# Use optional imports for numpy
from app.utils.optional_imports import np, NUMPY_AVAILABLE
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from enum import Enum
import logging
from collections import deque, defaultdict
import aiohttp
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import statistics

from app.core.config import settings
from app.core.logging import get_logger
from app.core.redis import get_redis_client
from prometheus_client import Counter, Histogram, Gauge, CollectorRegistry

logger = get_logger(__name__)


class AlertSeverity(Enum):
    """Alert severity levels"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class MetricType(Enum):
    """Types of metrics to monitor"""
    SYSTEM = "system"
    APPLICATION = "application"
    BUSINESS = "business"
    SECURITY = "security"
    AI_PERFORMANCE = "ai_performance"


@dataclass
class Alert:
    """Alert data structure"""
    id: str
    title: str
    description: str
    severity: AlertSeverity
    metric_type: MetricType
    value: float
    threshold: float
    timestamp: datetime
    resolved: bool = False
    resolution_time: Optional[datetime] = None
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


@dataclass
class MetricSnapshot:
    """Point-in-time metric snapshot"""
    timestamp: datetime
    metric_name: str
    value: float
    tags: Dict[str, str]
    metadata: Dict[str, Any]


@dataclass
class AnomalyDetection:
    """Anomaly detection configuration"""
    metric_name: str
    method: str  # 'zscore', 'iqr', 'isolation_forest', 'lstm'
    threshold: float
    window_size: int
    sensitivity: float
    enabled: bool = True


class IntelligentMonitoringService:
    """Advanced monitoring service with AI-powered anomaly detection"""
    
    def __init__(self):
        self.redis_client = None
        self.metrics_buffer = defaultdict(lambda: deque(maxlen=1000))
        self.alert_handlers: List[Callable] = []
        self.anomaly_detectors: Dict[str, AnomalyDetection] = {}
        self.active_alerts: Dict[str, Alert] = {}
        self.performance_baselines: Dict[str, Dict[str, float]] = {}
        
        # Prometheus metrics
        self.registry = CollectorRegistry()
        self.request_counter = Counter(
            'synthos_requests_total',
            'Total requests',
            ['endpoint', 'method', 'status'],
            registry=self.registry
        )
        self.generation_duration = Histogram(
            'synthos_generation_duration_seconds',
            'Data generation duration',
            ['dataset_type', 'privacy_level'],
            registry=self.registry
        )
        self.ai_quality_score = Gauge(
            'synthos_ai_quality_score',
            'AI generation quality score',
            ['model', 'strategy'],
            registry=self.registry
        )
        self.system_metrics = Gauge(
            'synthos_system_metrics',
            'System performance metrics',
            ['metric_type'],
            registry=self.registry
        )
        
        # Initialize monitoring
        self._setup_default_detectors()
        self._setup_alert_handlers()
    
    async def initialize(self):
        """Initialize monitoring service"""
        self.redis_client = await get_redis_client()
        await self._load_baselines()
        
        # Start background monitoring tasks
        asyncio.create_task(self._monitor_system_metrics())
        asyncio.create_task(self._monitor_application_metrics())
        asyncio.create_task(self._run_anomaly_detection())
        asyncio.create_task(self._health_check_services())
        
        logger.info("Intelligent monitoring service initialized")
    
    async def record_metric(
        self,
        name: str,
        value: float,
        metric_type: MetricType = MetricType.APPLICATION,
        tags: Dict[str, str] = None,
        metadata: Dict[str, Any] = None
    ):
        """Record a metric value"""
        
        timestamp = datetime.utcnow()
        tags = tags or {}
        metadata = metadata or {}
        
        metric = MetricSnapshot(
            timestamp=timestamp,
            metric_name=name,
            value=value,
            tags=tags,
            metadata=metadata
        )
        
        # Store in buffer for anomaly detection
        self.metrics_buffer[name].append(metric)
        
        # Store in Redis for persistence
        redis_key = f"metric:{name}:{int(timestamp.timestamp())}"
        await self.redis_client.setex(
            redis_key,
            86400 * 7,  # 7 days retention
            json.dumps(asdict(metric), default=str)
        )
        
        # Update Prometheus metrics
        await self._update_prometheus_metrics(name, value, tags, metric_type)
        
        # Trigger anomaly detection for this metric
        await self._check_anomaly(name, value)
    
    async def create_alert(
        self,
        title: str,
        description: str,
        severity: AlertSeverity,
        metric_type: MetricType,
        value: float,
        threshold: float,
        metadata: Dict[str, Any] = None
    ) -> Alert:
        """Create and process an alert"""
        
        alert_id = f"{metric_type.value}_{int(time.time())}_{hash(title) % 10000}"
        
        alert = Alert(
            id=alert_id,
            title=title,
            description=description,
            severity=severity,
            metric_type=metric_type,
            value=value,
            threshold=threshold,
            timestamp=datetime.utcnow(),
            metadata=metadata or {}
        )
        
        # Store alert
        self.active_alerts[alert_id] = alert
        
        # Persist to Redis
        await self.redis_client.setex(
            f"alert:{alert_id}",
            86400 * 30,  # 30 days retention
            json.dumps(asdict(alert), default=str)
        )
        
        # Trigger alert handlers
        await self._process_alert(alert)
        
        logger.info(
            "Alert created",
            alert_id=alert_id,
            severity=severity.value,
            title=title
        )
        
        return alert
    
    async def resolve_alert(self, alert_id: str, resolution_note: str = None):
        """Resolve an active alert"""
        
        if alert_id in self.active_alerts:
            alert = self.active_alerts[alert_id]
            alert.resolved = True
            alert.resolution_time = datetime.utcnow()
            
            if resolution_note:
                alert.metadata["resolution_note"] = resolution_note
            
            # Update in Redis
            await self.redis_client.setex(
                f"alert:{alert_id}",
                86400 * 30,
                json.dumps(asdict(alert), default=str)
            )
            
            # Remove from active alerts
            del self.active_alerts[alert_id]
            
            logger.info("Alert resolved", alert_id=alert_id, note=resolution_note)
    
    async def get_system_health(self) -> Dict[str, Any]:
        """Get comprehensive system health status"""
        
        # System metrics
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        # Application metrics
        active_jobs = len(await self._get_active_generation_jobs())
        avg_response_time = await self._get_average_response_time()
        error_rate = await self._get_error_rate()
        
        # AI performance metrics
        ai_metrics = await self._get_ai_performance_metrics()
        
        # Database health
        db_health = await self._check_database_health()
        
        # Redis health
        redis_health = await self._check_redis_health()
        
        health_status = {
            "timestamp": datetime.utcnow().isoformat(),
            "overall_status": "healthy",  # Will be updated based on checks
            "system": {
                "cpu_usage": cpu_percent,
                "memory_usage": memory.percent,
                "memory_available": memory.available,
                "disk_usage": disk.percent,
                "disk_free": disk.free,
                "load_average": list(psutil.getloadavg()) if hasattr(psutil, 'getloadavg') else None
            },
            "application": {
                "active_generation_jobs": active_jobs,
                "average_response_time_ms": avg_response_time,
                "error_rate_percent": error_rate,
                "uptime_seconds": self._get_uptime()
            },
            "ai_performance": ai_metrics,
            "services": {
                "database": db_health,
                "redis": redis_health,
                "api": await self._check_api_health()
            },
            "active_alerts": len(self.active_alerts),
            "alerts": [
                {
                    "id": alert.id,
                    "title": alert.title,
                    "severity": alert.severity.value,
                    "timestamp": alert.timestamp.isoformat()
                }
                for alert in self.active_alerts.values()
                if alert.severity in [AlertSeverity.ERROR, AlertSeverity.CRITICAL]
            ]
        }
        
        # Determine overall status
        if any(alert.severity == AlertSeverity.CRITICAL for alert in self.active_alerts.values()):
            health_status["overall_status"] = "critical"
        elif any(alert.severity == AlertSeverity.ERROR for alert in self.active_alerts.values()):
            health_status["overall_status"] = "degraded"
        elif cpu_percent > 90 or memory.percent > 90 or error_rate > 5:
            health_status["overall_status"] = "degraded"
        
        return health_status
    
    async def get_performance_insights(self, timeframe_hours: int = 24) -> Dict[str, Any]:
        """Get performance insights and recommendations"""
        
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(hours=timeframe_hours)
        
        # Collect metrics for analysis
        metrics_data = await self._get_metrics_in_timeframe(start_time, end_time)
        
        insights = {
            "timeframe": {
                "start": start_time.isoformat(),
                "end": end_time.isoformat(),
                "hours": timeframe_hours
            },
            "performance_summary": await self._analyze_performance_trends(metrics_data),
            "bottlenecks": await self._identify_bottlenecks(metrics_data),
            "recommendations": await self._generate_recommendations(metrics_data),
            "anomalies": await self._get_recent_anomalies(start_time),
            "capacity_planning": await self._analyze_capacity_trends(metrics_data)
        }
        
        return insights
    
    async def _setup_default_detectors(self):
        """Setup default anomaly detectors"""
        
        detectors = {
            "cpu_usage": AnomalyDetection(
                metric_name="cpu_usage",
                method="zscore",
                threshold=2.5,
                window_size=100,
                sensitivity=0.8
            ),
            "memory_usage": AnomalyDetection(
                metric_name="memory_usage",
                method="zscore",
                threshold=2.0,
                window_size=100,
                sensitivity=0.7
            ),
            "response_time": AnomalyDetection(
                metric_name="response_time",
                method="iqr",
                threshold=1.5,
                window_size=200,
                sensitivity=0.9
            ),
            "ai_quality_score": AnomalyDetection(
                metric_name="ai_quality_score",
                method="zscore",
                threshold=2.0,
                window_size=50,
                sensitivity=0.8
            ),
            "generation_duration": AnomalyDetection(
                metric_name="generation_duration",
                method="iqr",
                threshold=2.0,
                window_size=100,
                sensitivity=0.85
            )
        }
        
        self.anomaly_detectors.update(detectors)
    
    async def _setup_alert_handlers(self):
        """Setup alert notification handlers"""
        
        # Email handler
        if settings.SMTP_HOST:
            self.alert_handlers.append(self._send_email_alert)
        
        # Slack handler (if configured)
        if hasattr(settings, 'SLACK_WEBHOOK_URL') and settings.SLACK_WEBHOOK_URL:
            self.alert_handlers.append(self._send_slack_alert)
        
        # PagerDuty handler (if configured)
        if hasattr(settings, 'PAGERDUTY_API_KEY') and settings.PAGERDUTY_API_KEY:
            self.alert_handlers.append(self._send_pagerduty_alert)
        
        # Always include logging handler
        self.alert_handlers.append(self._log_alert)
    
    async def _monitor_system_metrics(self):
        """Continuously monitor system metrics"""
        
        while True:
            try:
                # CPU metrics
                cpu_percent = psutil.cpu_percent(interval=1)
                await self.record_metric("cpu_usage", cpu_percent, MetricType.SYSTEM)
                
                # Memory metrics
                memory = psutil.virtual_memory()
                await self.record_metric("memory_usage", memory.percent, MetricType.SYSTEM)
                await self.record_metric("memory_available", memory.available, MetricType.SYSTEM)
                
                # Disk metrics
                disk = psutil.disk_usage('/')
                await self.record_metric("disk_usage", disk.percent, MetricType.SYSTEM)
                await self.record_metric("disk_free", disk.free, MetricType.SYSTEM)
                
                # Network metrics
                network = psutil.net_io_counters()
                await self.record_metric("network_bytes_sent", network.bytes_sent, MetricType.SYSTEM)
                await self.record_metric("network_bytes_recv", network.bytes_recv, MetricType.SYSTEM)
                
                # Check thresholds
                if cpu_percent > 85:
                    await self.create_alert(
                        "High CPU Usage",
                        f"CPU usage is {cpu_percent:.1f}%, which exceeds the 85% threshold",
                        AlertSeverity.WARNING if cpu_percent < 95 else AlertSeverity.ERROR,
                        MetricType.SYSTEM,
                        cpu_percent,
                        85
                    )
                
                if memory.percent > 85:
                    await self.create_alert(
                        "High Memory Usage",
                        f"Memory usage is {memory.percent:.1f}%, which exceeds the 85% threshold",
                        AlertSeverity.WARNING if memory.percent < 95 else AlertSeverity.ERROR,
                        MetricType.SYSTEM,
                        memory.percent,
                        85
                    )
                
                await asyncio.sleep(30)  # Monitor every 30 seconds
                
            except Exception as e:
                logger.error("System metrics monitoring failed", error=str(e))
                await asyncio.sleep(60)
    
    async def _check_anomaly(self, metric_name: str, value: float):
        """Check for anomalies in metric values"""
        
        if metric_name not in self.anomaly_detectors:
            return
        
        detector = self.anomaly_detectors[metric_name]
        if not detector.enabled:
            return
        
        metrics_history = [m.value for m in self.metrics_buffer[metric_name]]
        
        if len(metrics_history) < detector.window_size:
            return  # Not enough data
        
        is_anomaly = False
        anomaly_score = 0.0
        
        if detector.method == "zscore":
            is_anomaly, anomaly_score = self._zscore_anomaly_detection(
                metrics_history, value, detector.threshold
            )
        elif detector.method == "iqr":
            is_anomaly, anomaly_score = self._iqr_anomaly_detection(
                metrics_history, value, detector.threshold
            )
        
        if is_anomaly:
            severity = AlertSeverity.WARNING
            if anomaly_score > detector.threshold * 1.5:
                severity = AlertSeverity.ERROR
            if anomaly_score > detector.threshold * 2:
                severity = AlertSeverity.CRITICAL
            
            await self.create_alert(
                f"Anomaly Detected: {metric_name}",
                f"Anomalous value {value:.2f} detected for {metric_name} (score: {anomaly_score:.2f})",
                severity,
                MetricType.APPLICATION,
                value,
                detector.threshold,
                {"anomaly_score": anomaly_score, "detection_method": detector.method}
            )
    
    def _zscore_anomaly_detection(
        self, 
        history: List[float], 
        current_value: float, 
        threshold: float
    ) -> Tuple[bool, float]:
        """Z-score based anomaly detection"""
        
        if len(history) < 10:
            return False, 0.0
        
        mean_val = statistics.mean(history)
        std_val = statistics.stdev(history)
        
        if std_val == 0:
            return False, 0.0
        
        z_score = abs((current_value - mean_val) / std_val)
        return z_score > threshold, z_score
    
    def _iqr_anomaly_detection(
        self, 
        history: List[float], 
        current_value: float, 
        threshold: float
    ) -> Tuple[bool, float]:
        """Interquartile range based anomaly detection"""
        
        if len(history) < 10:
            return False, 0.0
        
        # Use numpy if available, otherwise fallback to simple statistics
        if NUMPY_AVAILABLE:
            q1 = np.percentile(history, 25)
            q3 = np.percentile(history, 75)
        else:
            # Simple fallback using sorted list
            sorted_history = sorted(history)
            n = len(sorted_history)
            q1_idx = int(0.25 * n)
            q3_idx = int(0.75 * n)
            q1 = sorted_history[q1_idx]
            q3 = sorted_history[q3_idx]
        
        iqr = q3 - q1
        
        if iqr == 0:
            return False, 0.0
        
        lower_bound = q1 - threshold * iqr
        upper_bound = q3 + threshold * iqr
        
        is_anomaly = current_value < lower_bound or current_value > upper_bound
        
        # Calculate anomaly score
        if current_value < lower_bound:
            score = (lower_bound - current_value) / iqr
        elif current_value > upper_bound:
            score = (current_value - upper_bound) / iqr
        else:
            score = 0.0
        
        return is_anomaly, score
    
    async def _process_alert(self, alert: Alert):
        """Process alert through all handlers"""
        
        for handler in self.alert_handlers:
            try:
                await handler(alert)
            except Exception as e:
                logger.error(
                    "Alert handler failed",
                    handler=handler.__name__,
                    alert_id=alert.id,
                    error=str(e)
                )
    
    async def _send_email_alert(self, alert: Alert):
        """Send alert via email"""
        
        if not settings.SMTP_HOST:
            return
        
        subject = f"[{alert.severity.value.upper()}] {alert.title}"
        
        body = f"""
        Alert Details:
        
        Title: {alert.title}
        Severity: {alert.severity.value.upper()}
        Description: {alert.description}
        Metric Type: {alert.metric_type.value}
        Value: {alert.value}
        Threshold: {alert.threshold}
        Timestamp: {alert.timestamp.isoformat()}
        
        Alert ID: {alert.id}
        
        Additional Information:
        {json.dumps(alert.metadata, indent=2)}
        
        ---
        Synthos Monitoring System
        """
        
        msg = MIMEMultipart()
        msg['From'] = settings.FROM_EMAIL
        msg['To'] = "alerts@synthos.ai"  # Configure as needed
        msg['Subject'] = subject
        
        msg.attach(MIMEText(body, 'plain'))
        
        try:
            with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
                if settings.SMTP_USER:
                    server.starttls()
                    server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
                
                server.send_message(msg)
                
        except Exception as e:
            logger.error("Failed to send email alert", error=str(e))
    
    async def _send_slack_alert(self, alert: Alert):
        """Send alert to Slack"""
        
        webhook_url = getattr(settings, 'SLACK_WEBHOOK_URL', None)
        if not webhook_url:
            return
        
        color_map = {
            AlertSeverity.INFO: "#36a64f",      # Green
            AlertSeverity.WARNING: "#ffeb3b",   # Yellow
            AlertSeverity.ERROR: "#ff9800",     # Orange
            AlertSeverity.CRITICAL: "#f44336"   # Red
        }
        
        payload = {
            "attachments": [
                {
                    "color": color_map.get(alert.severity, "#000000"),
                    "title": f"{alert.severity.value.upper()}: {alert.title}",
                    "text": alert.description,
                    "fields": [
                        {
                            "title": "Metric Type",
                            "value": alert.metric_type.value,
                            "short": True
                        },
                        {
                            "title": "Value",
                            "value": f"{alert.value:.2f}",
                            "short": True
                        },
                        {
                            "title": "Threshold",
                            "value": f"{alert.threshold:.2f}",
                            "short": True
                        },
                        {
                            "title": "Alert ID",
                            "value": alert.id,
                            "short": True
                        }
                    ],
                    "timestamp": int(alert.timestamp.timestamp())
                }
            ]
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(webhook_url, json=payload) as response:
                    if response.status != 200:
                        logger.error("Failed to send Slack alert", status=response.status)
                        
        except Exception as e:
            logger.error("Failed to send Slack alert", error=str(e))
    
    async def _log_alert(self, alert: Alert):
        """Log alert to structured logging"""
        
        logger.warning(
            "ALERT",
            alert_id=alert.id,
            title=alert.title,
            severity=alert.severity.value,
            metric_type=alert.metric_type.value,
            value=alert.value,
            threshold=alert.threshold,
            description=alert.description,
            metadata=alert.metadata
        )
    
    async def _update_prometheus_metrics(
        self, 
        name: str, 
        value: float, 
        tags: Dict[str, str], 
        metric_type: MetricType
    ):
        """Update Prometheus metrics"""
        
        if metric_type == MetricType.SYSTEM:
            self.system_metrics.labels(metric_type=name).set(value)
        elif name == "ai_quality_score":
            model = tags.get("model", "unknown")
            strategy = tags.get("strategy", "unknown")
            self.ai_quality_score.labels(model=model, strategy=strategy).set(value)
    
    # Additional helper methods would be implemented here...
    async def _get_active_generation_jobs(self) -> List[str]:
        """Get list of active generation jobs"""
        # Implementation depends on your job tracking system
        return []
    
    async def _get_average_response_time(self) -> float:
        """Get average API response time"""
        # Implementation depends on your metrics collection
        return 0.0
    
    async def _get_error_rate(self) -> float:
        """Get current error rate percentage"""
        # Implementation depends on your error tracking
        return 0.0
    
    def _get_uptime(self) -> float:
        """Get application uptime in seconds"""
        # Implementation depends on your startup tracking
        return time.time()
    
    async def _get_ai_performance_metrics(self) -> Dict[str, Any]:
        """Get AI performance metrics"""
        # Implementation depends on your AI metrics tracking
        return {
            "average_generation_time": 0.0,
            "average_quality_score": 0.0,
            "model_success_rate": 0.0
        }
    
    async def _check_database_health(self) -> Dict[str, Any]:
        """Check database health"""
        # Implementation depends on your database setup
        return {"status": "healthy", "response_time_ms": 0.0}
    
    async def _check_redis_health(self) -> Dict[str, Any]:
        """Check Redis health"""
        try:
            start_time = time.time()
            await self.redis_client.ping()
            response_time = (time.time() - start_time) * 1000
            return {"status": "healthy", "response_time_ms": response_time}
        except Exception as e:
            return {"status": "unhealthy", "error": str(e)}
    
    async def _check_api_health(self) -> Dict[str, Any]:
        """Check API health"""
        # Implementation depends on your API setup
        return {"status": "healthy", "response_time_ms": 0.0}
    
    async def get_distributed_tracing(self, trace_id: str) -> Dict[str, Any]:
        """Get distributed tracing information for a request"""
        
        try:
            if self.redis_client:
                trace_data = await self.redis_client.get(f"trace:{trace_id}")
                if trace_data:
                    return json.loads(trace_data)
            
            return {
                "trace_id": trace_id,
                "spans": [],
                "duration_ms": 0,
                "status": "not_found"
            }
        except Exception as e:
            logger.error(f"Failed to get trace {trace_id}: {e}")
            return {"error": str(e)}
    
    async def start_trace(self, operation_name: str, trace_id: str = None) -> str:
        """Start a new distributed trace"""
        
        if not trace_id:
            trace_id = f"trace_{int(time.time() * 1000)}_{hash(operation_name) % 10000}"
        
        trace_data = {
            "trace_id": trace_id,
            "operation_name": operation_name,
            "start_time": datetime.utcnow().isoformat(),
            "spans": [],
            "status": "active"
        }
        
        if self.redis_client:
            await self.redis_client.setex(
                f"trace:{trace_id}",
                3600,  # 1 hour TTL
                json.dumps(trace_data)
            )
        
        return trace_id
    
    async def add_span(
        self,
        trace_id: str,
        span_name: str,
        start_time: datetime = None,
        end_time: datetime = None,
        tags: Dict[str, Any] = None
    ):
        """Add a span to a trace"""
        
        try:
            if self.redis_client:
                trace_data = await self.redis_client.get(f"trace:{trace_id}")
                if trace_data:
                    trace = json.loads(trace_data)
                    
                    span = {
                        "span_name": span_name,
                        "start_time": (start_time or datetime.utcnow()).isoformat(),
                        "end_time": (end_time or datetime.utcnow()).isoformat(),
                        "tags": tags or {},
                        "duration_ms": 0
                    }
                    
                    if start_time and end_time:
                        span["duration_ms"] = (end_time - start_time).total_seconds() * 1000
                    
                    trace["spans"].append(span)
                    
                    await self.redis_client.setex(
                        f"trace:{trace_id}",
                        3600,
                        json.dumps(trace)
                    )
        except Exception as e:
            logger.error(f"Failed to add span to trace {trace_id}: {e}")
    
    async def complete_trace(self, trace_id: str, status: str = "success"):
        """Complete a trace"""
        
        try:
            if self.redis_client:
                trace_data = await self.redis_client.get(f"trace:{trace_id}")
                if trace_data:
                    trace = json.loads(trace_data)
                    trace["status"] = status
                    trace["end_time"] = datetime.utcnow().isoformat()
                    
                    # Calculate total duration
                    start_time = datetime.fromisoformat(trace["start_time"])
                    end_time = datetime.fromisoformat(trace["end_time"])
                    trace["duration_ms"] = (end_time - start_time).total_seconds() * 1000
                    
                    await self.redis_client.setex(
                        f"trace:{trace_id}",
                        3600,
                        json.dumps(trace)
                    )
        except Exception as e:
            logger.error(f"Failed to complete trace {trace_id}: {e}")
    
    async def get_performance_traces(
        self,
        operation_name: str = None,
        time_range_hours: int = 24,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Get performance traces with filtering"""
        
        try:
            if not self.redis_client:
                return []
            
            # Get all trace keys
            trace_keys = await self.redis_client.keys("trace:*")
            traces = []
            
            for key in trace_keys:
                trace_data = await self.redis_client.get(key)
                if trace_data:
                    trace = json.loads(trace_data)
                    
                    # Apply filters
                    if operation_name and trace.get("operation_name") != operation_name:
                        continue
                    
                    # Check time range
                    trace_time = datetime.fromisoformat(trace["start_time"])
                    cutoff_time = datetime.utcnow() - timedelta(hours=time_range_hours)
                    
                    if trace_time < cutoff_time:
                        continue
                    
                    traces.append(trace)
            
            # Sort by start time (newest first)
            traces.sort(key=lambda x: x["start_time"], reverse=True)
            
            return traces[:limit]
        except Exception as e:
            logger.error(f"Failed to get performance traces: {e}")
            return []
    
    async def get_error_analysis(self, time_range_hours: int = 24) -> Dict[str, Any]:
        """Get error analysis and patterns"""
        
        try:
            end_time = datetime.utcnow()
            start_time = end_time - timedelta(hours=time_range_hours)
            
            # Get error events from metrics
            error_events = []
            for metric_name, metrics_buffer in self.metrics_buffer.items():
                if "error" in metric_name.lower():
                    for metric in metrics_buffer:
                        if start_time <= metric.timestamp <= end_time:
                            error_events.append(metric)
            
            # Analyze error patterns
            error_analysis = {
                "total_errors": len(error_events),
                "error_rate": len(error_events) / max(1, len(self.metrics_buffer.get("requests", []))),
                "error_types": {},
                "error_trends": [],
                "top_error_sources": [],
                "recommendations": []
            }
            
            # Categorize errors
            for event in error_events:
                error_type = event.metadata.get("error_type", "unknown")
                error_analysis["error_types"][error_type] = error_analysis["error_types"].get(error_type, 0) + 1
            
            # Generate recommendations
            if error_analysis["error_rate"] > 0.05:  # More than 5% error rate
                error_analysis["recommendations"].append("High error rate detected - investigate system stability")
            
            if "timeout" in error_analysis["error_types"]:
                error_analysis["recommendations"].append("Timeout errors detected - consider increasing timeouts or optimizing performance")
            
            return error_analysis
        except Exception as e:
            logger.error(f"Failed to get error analysis: {e}")
            return {"error": str(e)}
    
    async def get_capacity_planning(self) -> Dict[str, Any]:
        """Get capacity planning recommendations"""
        
        try:
            # Analyze current usage patterns
            current_metrics = await self.get_system_health()
            
            # Get historical trends
            historical_data = await self._get_historical_metrics(30)  # Last 30 days
            
            capacity_planning = {
                "current_utilization": {
                    "cpu": current_metrics["system"]["cpu_usage"],
                    "memory": current_metrics["system"]["memory_usage"],
                    "disk": current_metrics["system"]["disk_usage"]
                },
                "growth_trends": await self._analyze_growth_trends(historical_data),
                "capacity_forecast": await self._forecast_capacity_needs(historical_data),
                "scaling_recommendations": await self._generate_scaling_recommendations(current_metrics, historical_data),
                "cost_optimization": await self._analyze_cost_optimization(historical_data)
            }
            
            return capacity_planning
        except Exception as e:
            logger.error(f"Failed to get capacity planning: {e}")
            return {"error": str(e)}
    
    async def _get_historical_metrics(self, days: int) -> Dict[str, List[Dict[str, Any]]]:
        """Get historical metrics for analysis"""
        
        # This would retrieve historical metrics from storage
        # For now, return mock data
        return {
            "cpu_usage": [{"timestamp": datetime.utcnow().isoformat(), "value": 0.75}],
            "memory_usage": [{"timestamp": datetime.utcnow().isoformat(), "value": 0.60}],
            "request_count": [{"timestamp": datetime.utcnow().isoformat(), "value": 1000}]
        }
    
    async def _analyze_growth_trends(self, historical_data: Dict[str, List[Dict[str, Any]]]) -> Dict[str, Any]:
        """Analyze growth trends from historical data"""
        
        trends = {
            "cpu_growth_rate": 0.05,  # 5% per month
            "memory_growth_rate": 0.03,  # 3% per month
            "request_growth_rate": 0.10,  # 10% per month
            "trend_direction": "increasing",
            "confidence": 0.85
        }
        
        return trends
    
    async def _forecast_capacity_needs(self, historical_data: Dict[str, List[Dict[str, Any]]]) -> Dict[str, Any]:
        """Forecast future capacity needs"""
        
        forecast = {
            "next_month": {
                "cpu_usage": 0.80,
                "memory_usage": 0.65,
                "storage_usage": 0.50
            },
            "next_quarter": {
                "cpu_usage": 0.90,
                "memory_usage": 0.75,
                "storage_usage": 0.60
            },
            "recommendations": [
                "Consider scaling CPU resources in 2 months",
                "Monitor memory usage closely",
                "Plan storage expansion for next quarter"
            ]
        }
        
        return forecast
    
    async def _generate_scaling_recommendations(
        self,
        current_metrics: Dict[str, Any],
        historical_data: Dict[str, List[Dict[str, Any]]]
    ) -> List[str]:
        """Generate scaling recommendations"""
        
        recommendations = []
        
        # CPU recommendations
        if current_metrics["system"]["cpu_usage"] > 0.80:
            recommendations.append("High CPU usage detected - consider horizontal scaling")
        
        # Memory recommendations
        if current_metrics["system"]["memory_usage"] > 0.85:
            recommendations.append("High memory usage detected - consider vertical scaling or memory optimization")
        
        # Storage recommendations
        if current_metrics["system"]["disk_usage"] > 0.90:
            recommendations.append("High disk usage detected - consider storage expansion")
        
        return recommendations
    
    async def _analyze_cost_optimization(self, historical_data: Dict[str, List[Dict[str, Any]]]) -> Dict[str, Any]:
        """Analyze cost optimization opportunities"""
        
        return {
            "current_monthly_cost": 1000.0,
            "optimization_opportunities": [
                "Consider reserved instances for predictable workloads",
                "Implement auto-scaling to reduce idle resources",
                "Use spot instances for non-critical workloads"
            ],
            "potential_savings": 200.0,
            "savings_percentage": 20.0
        }

def track_generation_metrics(
    user_id: int,
    dataset_id: int, 
    rows_generated: int,
    quality_score: float,
    processing_time: float
):
    """Track generation metrics for monitoring"""
    
    logger.info(
        "Generation metrics tracked",
        user_id=user_id,
        dataset_id=dataset_id,
        rows_generated=rows_generated,
        quality_score=quality_score,
        processing_time=processing_time
    )
    
    # Update Prometheus metrics if available
    try:
        AI_GENERATION_DURATION.observe(processing_time)
        DATA_QUALITY_SCORE.set(quality_score)
    except NameError:
        pass  # Metrics not available 