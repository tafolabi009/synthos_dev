"""
Advanced Analytics Service for Synthetic Data Platform
Comprehensive metrics, insights, and reporting capabilities
"""

import json
import asyncio
import logging
from typing import Dict, List, Any, Optional, Tuple, Union
from dataclasses import dataclass, asdict
from enum import Enum
import time
import uuid
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
from collections import defaultdict, Counter
import statistics
from scipy import stats
from scipy.stats import ks_2samp, chi2_contingency, pearsonr, spearmanr
import matplotlib.pyplot as plt
import seaborn as sns
from io import BytesIO
import base64

from app.core.config import settings
from app.core.logging import get_logger
from app.models.dataset import Dataset, GenerationJob
from app.models.user import User, UserUsage
from app.core.redis import get_redis_client

logger = get_logger(__name__)


class AnalyticsMetricType(Enum):
    """Types of analytics metrics"""
    USAGE = "usage"
    QUALITY = "quality"
    PERFORMANCE = "performance"
    PRIVACY = "privacy"
    BUSINESS = "business"
    TECHNICAL = "technical"


class ReportType(Enum):
    """Types of analytics reports"""
    DASHBOARD = "dashboard"
    DETAILED = "detailed"
    COMPARATIVE = "comparative"
    TREND = "trend"
    PREDICTIVE = "predictive"


@dataclass
class AnalyticsMetric:
    """Analytics metric definition"""
    name: str
    value: float
    metric_type: AnalyticsMetricType
    timestamp: datetime
    metadata: Optional[Dict[str, Any]] = None
    user_id: Optional[int] = None
    dataset_id: Optional[int] = None
    job_id: Optional[int] = None


@dataclass
class AnalyticsInsight:
    """Analytics insight definition"""
    title: str
    description: str
    insight_type: str
    confidence: float
    impact: str
    recommendations: List[str]
    metrics: List[AnalyticsMetric]
    generated_at: datetime


class AdvancedAnalyticsService:
    """
    Advanced analytics service for comprehensive insights and reporting
    """

    def __init__(self):
        """Initialize analytics service"""
        self.redis_client = None
        self._init_cache()
        
        # Analytics storage
        self.metrics_storage = defaultdict(list)
        self.insights_storage = []
        
        logger.info("Advanced Analytics Service initialized")

    async def _init_cache(self):
        """Initialize Redis cache"""
        try:
            self.redis_client = await get_redis_client()
        except Exception as e:
            logger.warning("Redis cache not available", error=str(e))

    async def track_generation_metrics(
        self,
        user_id: int,
        dataset_id: int,
        job_id: int,
        metrics: Dict[str, Any]
    ):
        """Track generation metrics"""
        
        timestamp = datetime.utcnow()
        
        # Create metrics
        generation_metrics = [
            AnalyticsMetric(
                name="rows_generated",
                value=metrics.get("rows_generated", 0),
                metric_type=AnalyticsMetricType.USAGE,
                timestamp=timestamp,
                user_id=user_id,
                dataset_id=dataset_id,
                job_id=job_id
            ),
            AnalyticsMetric(
                name="quality_score",
                value=metrics.get("quality_score", 0.0),
                metric_type=AnalyticsMetricType.QUALITY,
                timestamp=timestamp,
                user_id=user_id,
                dataset_id=dataset_id,
                job_id=job_id
            ),
            AnalyticsMetric(
                name="execution_time",
                value=metrics.get("execution_time", 0.0),
                metric_type=AnalyticsMetricType.PERFORMANCE,
                timestamp=timestamp,
                user_id=user_id,
                dataset_id=dataset_id,
                job_id=job_id
            ),
            AnalyticsMetric(
                name="privacy_score",
                value=metrics.get("privacy_score", 0.0),
                metric_type=AnalyticsMetricType.PRIVACY,
                timestamp=timestamp,
                user_id=user_id,
                dataset_id=dataset_id,
                job_id=job_id
            )
        ]
        
        # Store metrics
        await self._store_metrics(generation_metrics)
        
        # Generate real-time insights
        await self._generate_real_time_insights(user_id, generation_metrics)

    async def _store_metrics(self, metrics: List[AnalyticsMetric]):
        """Store metrics in storage and cache"""
        
        for metric in metrics:
            # Store in memory
            self.metrics_storage[metric.metric_type.value].append(metric)
            
            # Store in Redis cache
            if self.redis_client:
                try:
                    cache_key = f"analytics:{metric.metric_type.value}:{metric.user_id}"
                    await self.redis_client.lpush(
                        cache_key,
                        json.dumps({
                            "name": metric.name,
                            "value": metric.value,
                            "timestamp": metric.timestamp.isoformat(),
                            "metadata": metric.metadata or {}
                        })
                    )
                    await self.redis_client.expire(cache_key, 86400)  # 24 hours
                except Exception as e:
                    logger.warning("Failed to cache metric", error=str(e))

    async def _generate_real_time_insights(
        self,
        user_id: int,
        metrics: List[AnalyticsMetric]
    ):
        """Generate real-time insights from metrics"""
        
        insights = []
        
        # Quality insights
        quality_metrics = [m for m in metrics if m.metric_type == AnalyticsMetricType.QUALITY]
        if quality_metrics:
            avg_quality = statistics.mean([m.value for m in quality_metrics])
            if avg_quality > 0.9:
                insights.append(AnalyticsInsight(
                    title="Excellent Data Quality",
                    description=f"Your synthetic data quality is {avg_quality:.2f}, which is excellent.",
                    insight_type="quality",
                    confidence=0.95,
                    impact="high",
                    recommendations=[
                        "Continue using current generation parameters",
                        "Consider sharing your approach with the team"
                    ],
                    metrics=quality_metrics,
                    generated_at=datetime.utcnow()
                ))
            elif avg_quality < 0.7:
                insights.append(AnalyticsInsight(
                    title="Quality Improvement Needed",
                    description=f"Your synthetic data quality is {avg_quality:.2f}, which could be improved.",
                    insight_type="quality",
                    confidence=0.90,
                    impact="medium",
                    recommendations=[
                        "Try adjusting generation parameters",
                        "Consider using a different model",
                        "Review your input data quality"
                    ],
                    metrics=quality_metrics,
                    generated_at=datetime.utcnow()
                ))
        
        # Performance insights
        performance_metrics = [m for m in metrics if m.metric_type == AnalyticsMetricType.PERFORMANCE]
        if performance_metrics:
            avg_time = statistics.mean([m.value for m in performance_metrics])
            if avg_time > 300:  # 5 minutes
                insights.append(AnalyticsInsight(
                    title="Long Generation Times",
                    description=f"Your generation time is {avg_time:.1f} seconds, which is quite long.",
                    insight_type="performance",
                    confidence=0.85,
                    impact="medium",
                    recommendations=[
                        "Consider reducing batch size",
                        "Try using a faster model",
                        "Check your system resources"
                    ],
                    metrics=performance_metrics,
                    generated_at=datetime.utcnow()
                ))
        
        # Store insights
        for insight in insights:
            self.insights_storage.append(insight)
            await self._store_insight(insight)

    async def _store_insight(self, insight: AnalyticsInsight):
        """Store insight in cache"""
        
        if self.redis_client:
            try:
                cache_key = f"insights:{insight.generated_at.strftime('%Y-%m-%d')}"
                await self.redis_client.lpush(
                    cache_key,
                    json.dumps({
                        "title": insight.title,
                        "description": insight.description,
                        "insight_type": insight.insight_type,
                        "confidence": insight.confidence,
                        "impact": insight.impact,
                        "recommendations": insight.recommendations,
                        "generated_at": insight.generated_at.isoformat()
                    })
                )
                await self.redis_client.expire(cache_key, 604800)  # 7 days
            except Exception as e:
                logger.warning("Failed to cache insight", error=str(e))

    async def get_user_dashboard(self, user_id: int) -> Dict[str, Any]:
        """Get user analytics dashboard"""
        
        # Get user metrics
        user_metrics = await self._get_user_metrics(user_id)
        
        # Calculate dashboard metrics
        dashboard = {
            "user_id": user_id,
            "generated_at": datetime.utcnow().isoformat(),
            "summary": {
                "total_generations": len([m for m in user_metrics if m.metric_type == AnalyticsMetricType.USAGE]),
                "average_quality": self._calculate_average_quality(user_metrics),
                "total_rows_generated": sum([m.value for m in user_metrics if m.name == "rows_generated"]),
                "average_execution_time": self._calculate_average_execution_time(user_metrics)
            },
            "quality_trends": await self._calculate_quality_trends(user_metrics),
            "usage_patterns": await self._analyze_usage_patterns(user_metrics),
            "performance_metrics": await self._calculate_performance_metrics(user_metrics),
            "insights": await self._get_user_insights(user_id),
            "recommendations": await self._generate_recommendations(user_metrics)
        }
        
        return dashboard

    async def _get_user_metrics(self, user_id: int) -> List[AnalyticsMetric]:
        """Get all metrics for a user"""
        
        user_metrics = []
        
        # Get from memory storage
        for metric_type, metrics in self.metrics_storage.items():
            user_metrics.extend([m for m in metrics if m.user_id == user_id])
        
        # Get from cache
        if self.redis_client:
            try:
                for metric_type in AnalyticsMetricType:
                    cache_key = f"analytics:{metric_type.value}:{user_id}"
                    cached_metrics = await self.redis_client.lrange(cache_key, 0, -1)
                    for metric_data in cached_metrics:
                        try:
                            data = json.loads(metric_data)
                            user_metrics.append(AnalyticsMetric(
                                name=data["name"],
                                value=data["value"],
                                metric_type=metric_type,
                                timestamp=datetime.fromisoformat(data["timestamp"]),
                                metadata=data.get("metadata"),
                                user_id=user_id
                            ))
                        except Exception as e:
                            logger.warning("Failed to parse cached metric", error=str(e))
            except Exception as e:
                logger.warning("Failed to get cached metrics", error=str(e))
        
        return user_metrics

    def _calculate_average_quality(self, metrics: List[AnalyticsMetric]) -> float:
        """Calculate average quality score"""
        
        quality_metrics = [m for m in metrics if m.name == "quality_score"]
        if not quality_metrics:
            return 0.0
        
        return statistics.mean([m.value for m in quality_metrics])

    def _calculate_average_execution_time(self, metrics: List[AnalyticsMetric]) -> float:
        """Calculate average execution time"""
        
        time_metrics = [m for m in metrics if m.name == "execution_time"]
        if not time_metrics:
            return 0.0
        
        return statistics.mean([m.value for m in time_metrics])

    async def _calculate_quality_trends(self, metrics: List[AnalyticsMetric]) -> Dict[str, Any]:
        """Calculate quality trends over time"""
        
        quality_metrics = [m for m in metrics if m.name == "quality_score"]
        if not quality_metrics:
            return {"trend": "stable", "change": 0.0}
        
        # Sort by timestamp
        quality_metrics.sort(key=lambda x: x.timestamp)
        
        # Calculate trend
        if len(quality_metrics) >= 2:
            recent_avg = statistics.mean([m.value for m in quality_metrics[-5:]])  # Last 5
            older_avg = statistics.mean([m.value for m in quality_metrics[:-5]]) if len(quality_metrics) > 5 else recent_avg
            
            change = recent_avg - older_avg
            trend = "improving" if change > 0.05 else "declining" if change < -0.05 else "stable"
        else:
            trend = "stable"
            change = 0.0
        
        return {
            "trend": trend,
            "change": change,
            "current_quality": quality_metrics[-1].value if quality_metrics else 0.0,
            "data_points": len(quality_metrics)
        }

    async def _analyze_usage_patterns(self, metrics: List[AnalyticsMetric]) -> Dict[str, Any]:
        """Analyze usage patterns"""
        
        usage_metrics = [m for m in metrics if m.metric_type == AnalyticsMetricType.USAGE]
        
        if not usage_metrics:
            return {"pattern": "no_usage", "frequency": 0}
        
        # Analyze frequency
        timestamps = [m.timestamp for m in usage_metrics]
        timestamps.sort()
        
        if len(timestamps) >= 2:
            intervals = [(timestamps[i+1] - timestamps[i]).total_seconds() / 3600 for i in range(len(timestamps)-1)]
            avg_interval = statistics.mean(intervals)
            
            if avg_interval < 24:  # Daily usage
                frequency = "daily"
            elif avg_interval < 168:  # Weekly usage
                frequency = "weekly"
            else:
                frequency = "monthly"
        else:
            frequency = "single_use"
        
        # Analyze volume
        total_rows = sum([m.value for m in usage_metrics if m.name == "rows_generated"])
        avg_rows = total_rows / len(usage_metrics) if usage_metrics else 0
        
        volume_pattern = "high" if avg_rows > 10000 else "medium" if avg_rows > 1000 else "low"
        
        return {
            "frequency": frequency,
            "volume_pattern": volume_pattern,
            "total_generations": len(usage_metrics),
            "total_rows": total_rows,
            "average_rows_per_generation": avg_rows
        }

    async def _calculate_performance_metrics(self, metrics: List[AnalyticsMetric]) -> Dict[str, Any]:
        """Calculate performance metrics"""
        
        performance_metrics = [m for m in metrics if m.metric_type == AnalyticsMetricType.PERFORMANCE]
        
        if not performance_metrics:
            return {"average_time": 0.0, "efficiency": "unknown"}
        
        times = [m.value for m in performance_metrics]
        avg_time = statistics.mean(times)
        median_time = statistics.median(times)
        
        # Calculate efficiency
        if avg_time < 60:  # Less than 1 minute
            efficiency = "excellent"
        elif avg_time < 300:  # Less than 5 minutes
            efficiency = "good"
        elif avg_time < 900:  # Less than 15 minutes
            efficiency = "fair"
        else:
            efficiency = "poor"
        
        return {
            "average_time": avg_time,
            "median_time": median_time,
            "efficiency": efficiency,
            "fastest_generation": min(times),
            "slowest_generation": max(times),
            "total_generations": len(performance_metrics)
        }

    async def _get_user_insights(self, user_id: int) -> List[Dict[str, Any]]:
        """Get insights for a user"""
        
        user_insights = [i for i in self.insights_storage if any(m.user_id == user_id for m in i.metrics)]
        
        return [
            {
                "title": insight.title,
                "description": insight.description,
                "insight_type": insight.insight_type,
                "confidence": insight.confidence,
                "impact": insight.impact,
                "recommendations": insight.recommendations,
                "generated_at": insight.generated_at.isoformat()
            }
            for insight in user_insights[-10:]  # Last 10 insights
        ]

    async def _generate_recommendations(self, metrics: List[AnalyticsMetric]) -> List[str]:
        """Generate recommendations based on metrics"""
        
        recommendations = []
        
        # Quality recommendations
        quality_metrics = [m for m in metrics if m.name == "quality_score"]
        if quality_metrics:
            avg_quality = statistics.mean([m.value for m in quality_metrics])
            if avg_quality < 0.8:
                recommendations.append("Consider using Claude 4.1 Sonnet for better quality")
                recommendations.append("Try adjusting your generation parameters")
        
        # Performance recommendations
        performance_metrics = [m for m in metrics if m.name == "execution_time"]
        if performance_metrics:
            avg_time = statistics.mean([m.value for m in performance_metrics])
            if avg_time > 300:
                recommendations.append("Consider using smaller batch sizes for faster generation")
                recommendations.append("Try using Claude 3.5 Haiku for faster processing")
        
        # Usage recommendations
        usage_metrics = [m for m in metrics if m.metric_type == AnalyticsMetricType.USAGE]
        if len(usage_metrics) > 10:
            recommendations.append("You're a power user! Consider upgrading to a higher tier")
        
        return recommendations

    async def generate_comprehensive_report(
        self,
        user_id: int,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """Generate comprehensive analytics report"""
        
        # Get metrics for date range
        user_metrics = await self._get_user_metrics(user_id)
        
        if start_date and end_date:
            user_metrics = [
                m for m in user_metrics
                if start_date <= m.timestamp <= end_date
            ]
        
        # Generate report sections
        report = {
            "user_id": user_id,
            "report_period": {
                "start_date": start_date.isoformat() if start_date else None,
                "end_date": end_date.isoformat() if end_date else None
            },
            "generated_at": datetime.utcnow().isoformat(),
            "executive_summary": await self._generate_executive_summary(user_metrics),
            "quality_analysis": await self._analyze_quality_metrics(user_metrics),
            "performance_analysis": await self._analyze_performance_metrics(user_metrics),
            "usage_analysis": await self._analyze_usage_metrics(user_metrics),
            "privacy_analysis": await self._analyze_privacy_metrics(user_metrics),
            "trends": await self._analyze_trends(user_metrics),
            "insights": await self._generate_advanced_insights(user_metrics),
            "recommendations": await self._generate_advanced_recommendations(user_metrics),
            "visualizations": await self._generate_visualizations(user_metrics)
        }
        
        return report

    async def _generate_executive_summary(self, metrics: List[AnalyticsMetric]) -> Dict[str, Any]:
        """Generate executive summary"""
        
        total_generations = len([m for m in metrics if m.metric_type == AnalyticsMetricType.USAGE])
        total_rows = sum([m.value for m in metrics if m.name == "rows_generated"])
        avg_quality = self._calculate_average_quality(metrics)
        avg_time = self._calculate_average_execution_time(metrics)
        
        return {
            "total_generations": total_generations,
            "total_rows_generated": total_rows,
            "average_quality_score": avg_quality,
            "average_execution_time": avg_time,
            "quality_grade": "A" if avg_quality > 0.9 else "B" if avg_quality > 0.8 else "C" if avg_quality > 0.7 else "D",
            "efficiency_grade": "A" if avg_time < 60 else "B" if avg_time < 300 else "C" if avg_time < 900 else "D"
        }

    async def _analyze_quality_metrics(self, metrics: List[AnalyticsMetric]) -> Dict[str, Any]:
        """Analyze quality metrics in detail"""
        
        quality_metrics = [m for m in metrics if m.name == "quality_score"]
        
        if not quality_metrics:
            return {"analysis": "No quality data available"}
        
        values = [m.value for m in quality_metrics]
        
        return {
            "average_quality": statistics.mean(values),
            "median_quality": statistics.median(values),
            "quality_std": statistics.stdev(values) if len(values) > 1 else 0.0,
            "min_quality": min(values),
            "max_quality": max(values),
            "quality_distribution": {
                "excellent": len([v for v in values if v > 0.9]),
                "good": len([v for v in values if 0.8 < v <= 0.9]),
                "fair": len([v for v in values if 0.7 < v <= 0.8]),
                "poor": len([v for v in values if v <= 0.7])
            },
            "trend": "improving" if len(values) > 1 and values[-1] > values[0] else "stable"
        }

    async def _analyze_performance_metrics(self, metrics: List[AnalyticsMetric]) -> Dict[str, Any]:
        """Analyze performance metrics in detail"""
        
        performance_metrics = [m for m in metrics if m.name == "execution_time"]
        
        if not performance_metrics:
            return {"analysis": "No performance data available"}
        
        values = [m.value for m in performance_metrics]
        
        return {
            "average_time": statistics.mean(values),
            "median_time": statistics.median(values),
            "time_std": statistics.stdev(values) if len(values) > 1 else 0.0,
            "min_time": min(values),
            "max_time": max(values),
            "efficiency_score": 100 - min(100, (statistics.mean(values) / 600) * 100),  # Score based on 10-minute baseline
            "performance_trend": "improving" if len(values) > 1 and values[-1] < values[0] else "stable"
        }

    async def _analyze_usage_metrics(self, metrics: List[AnalyticsMetric]) -> Dict[str, Any]:
        """Analyze usage metrics in detail"""
        
        usage_metrics = [m for m in metrics if m.metric_type == AnalyticsMetricType.USAGE]
        row_metrics = [m for m in usage_metrics if m.name == "rows_generated"]
        
        total_rows = sum([m.value for m in row_metrics])
        total_generations = len(usage_metrics)
        
        return {
            "total_generations": total_generations,
            "total_rows_generated": total_rows,
            "average_rows_per_generation": total_rows / total_generations if total_generations > 0 else 0,
            "usage_frequency": await self._calculate_usage_frequency(metrics),
            "peak_usage_times": await self._analyze_peak_usage_times(metrics),
            "usage_growth": await self._calculate_usage_growth(metrics)
        }

    async def _analyze_privacy_metrics(self, metrics: List[AnalyticsMetric]) -> Dict[str, Any]:
        """Analyze privacy metrics"""
        
        privacy_metrics = [m for m in metrics if m.name == "privacy_score"]
        
        if not privacy_metrics:
            return {"analysis": "No privacy data available"}
        
        values = [m.value for m in privacy_metrics]
        
        return {
            "average_privacy_score": statistics.mean(values),
            "privacy_compliance": "excellent" if statistics.mean(values) > 0.9 else "good" if statistics.mean(values) > 0.8 else "needs_improvement",
            "privacy_trend": "improving" if len(values) > 1 and values[-1] > values[0] else "stable"
        }

    async def _analyze_trends(self, metrics: List[AnalyticsMetric]) -> Dict[str, Any]:
        """Analyze trends across all metrics"""
        
        # Group metrics by time periods
        daily_metrics = defaultdict(list)
        for metric in metrics:
            day = metric.timestamp.date()
            daily_metrics[day].append(metric)
        
        trends = {}
        
        # Quality trend
        quality_metrics = [m for m in metrics if m.name == "quality_score"]
        if quality_metrics:
            quality_metrics.sort(key=lambda x: x.timestamp)
            if len(quality_metrics) >= 2:
                first_half = quality_metrics[:len(quality_metrics)//2]
                second_half = quality_metrics[len(quality_metrics)//2:]
                
                first_avg = statistics.mean([m.value for m in first_half])
                second_avg = statistics.mean([m.value for m in second_half])
                
                trends["quality"] = {
                    "trend": "improving" if second_avg > first_avg else "declining" if second_avg < first_avg else "stable",
                    "change": second_avg - first_avg
                }
        
        return trends

    async def _generate_advanced_insights(self, metrics: List[AnalyticsMetric]) -> List[Dict[str, Any]]:
        """Generate advanced insights using statistical analysis"""
        
        insights = []
        
        # Quality insights
        quality_metrics = [m for m in metrics if m.name == "quality_score"]
        if len(quality_metrics) >= 5:
            values = [m.value for m in quality_metrics]
            
            # Check for quality patterns
            if statistics.mean(values) > 0.9:
                insights.append({
                    "title": "Consistently High Quality",
                    "description": "Your synthetic data consistently achieves high quality scores",
                    "confidence": 0.95,
                    "impact": "positive"
                })
            elif statistics.stdev(values) > 0.1:
                insights.append({
                    "title": "Variable Quality",
                    "description": "Your data quality varies significantly between generations",
                    "confidence": 0.85,
                    "impact": "neutral"
                })
        
        # Performance insights
        performance_metrics = [m for m in metrics if m.name == "execution_time"]
        if len(performance_metrics) >= 3:
            values = [m.value for m in performance_metrics]
            
            if statistics.mean(values) < 60:
                insights.append({
                    "title": "Excellent Performance",
                    "description": "Your generations complete very quickly",
                    "confidence": 0.90,
                    "impact": "positive"
                })
            elif statistics.mean(values) > 600:
                insights.append({
                    "title": "Performance Optimization Opportunity",
                    "description": "Your generations take longer than average",
                    "confidence": 0.80,
                    "impact": "neutral"
                })
        
        return insights

    async def _generate_advanced_recommendations(self, metrics: List[AnalyticsMetric]) -> List[Dict[str, Any]]:
        """Generate advanced recommendations"""
        
        recommendations = []
        
        # Quality-based recommendations
        quality_metrics = [m for m in metrics if m.name == "quality_score"]
        if quality_metrics:
            avg_quality = statistics.mean([m.value for m in quality_metrics])
            
            if avg_quality < 0.8:
                recommendations.append({
                    "category": "quality",
                    "priority": "high",
                    "recommendation": "Upgrade to Claude 4.1 Sonnet for better quality",
                    "expected_impact": "Increase quality by 15-20%"
                })
        
        # Performance-based recommendations
        performance_metrics = [m for m in metrics if m.name == "execution_time"]
        if performance_metrics:
            avg_time = statistics.mean([m.value for m in performance_metrics])
            
            if avg_time > 300:
                recommendations.append({
                    "category": "performance",
                    "priority": "medium",
                    "recommendation": "Use smaller batch sizes for faster generation",
                    "expected_impact": "Reduce generation time by 30-50%"
                })
        
        return recommendations

    async def _generate_visualizations(self, metrics: List[AnalyticsMetric]) -> Dict[str, str]:
        """Generate visualization charts"""
        
        visualizations = {}
        
        try:
            # Quality trend chart
            quality_metrics = [m for m in metrics if m.name == "quality_score"]
            if quality_metrics:
                quality_chart = await self._create_quality_trend_chart(quality_metrics)
                visualizations["quality_trend"] = quality_chart
            
            # Performance chart
            performance_metrics = [m for m in metrics if m.name == "execution_time"]
            if performance_metrics:
                performance_chart = await self._create_performance_chart(performance_metrics)
                visualizations["performance"] = performance_chart
            
        except Exception as e:
            logger.warning("Failed to generate visualizations", error=str(e))
        
        return visualizations

    async def _create_quality_trend_chart(self, metrics: List[AnalyticsMetric]) -> str:
        """Create quality trend chart"""
        
        try:
            # Sort by timestamp
            metrics.sort(key=lambda x: x.timestamp)
            
            # Create chart
            plt.figure(figsize=(10, 6))
            timestamps = [m.timestamp for m in metrics]
            values = [m.value for m in metrics]
            
            plt.plot(timestamps, values, marker='o', linewidth=2, markersize=6)
            plt.title('Quality Score Trend', fontsize=16, fontweight='bold')
            plt.xlabel('Time', fontsize=12)
            plt.ylabel('Quality Score', fontsize=12)
            plt.grid(True, alpha=0.3)
            plt.ylim(0, 1)
            
            # Convert to base64
            buffer = BytesIO()
            plt.savefig(buffer, format='png', dpi=150, bbox_inches='tight')
            buffer.seek(0)
            chart_data = base64.b64encode(buffer.getvalue()).decode()
            plt.close()
            
            return f"data:image/png;base64,{chart_data}"
            
        except Exception as e:
            logger.warning("Failed to create quality chart", error=str(e))
            return ""

    async def _create_performance_chart(self, metrics: List[AnalyticsMetric]) -> str:
        """Create performance chart"""
        
        try:
            # Sort by timestamp
            metrics.sort(key=lambda x: x.timestamp)
            
            # Create chart
            plt.figure(figsize=(10, 6))
            timestamps = [m.timestamp for m in metrics]
            values = [m.value for m in metrics]
            
            plt.plot(timestamps, values, marker='s', linewidth=2, markersize=6, color='orange')
            plt.title('Execution Time Trend', fontsize=16, fontweight='bold')
            plt.xlabel('Time', fontsize=12)
            plt.ylabel('Execution Time (seconds)', fontsize=12)
            plt.grid(True, alpha=0.3)
            
            # Convert to base64
            buffer = BytesIO()
            plt.savefig(buffer, format='png', dpi=150, bbox_inches='tight')
            buffer.seek(0)
            chart_data = base64.b64encode(buffer.getvalue()).decode()
            plt.close()
            
            return f"data:image/png;base64,{chart_data}"
            
        except Exception as e:
            logger.warning("Failed to create performance chart", error=str(e))
            return ""

    async def _calculate_usage_frequency(self, metrics: List[AnalyticsMetric]) -> str:
        """Calculate usage frequency"""
        
        usage_metrics = [m for m in metrics if m.metric_type == AnalyticsMetricType.USAGE]
        
        if len(usage_metrics) < 2:
            return "single_use"
        
        # Calculate average interval between uses
        timestamps = sorted([m.timestamp for m in usage_metrics])
        intervals = [(timestamps[i+1] - timestamps[i]).total_seconds() / 3600 for i in range(len(timestamps)-1)]
        avg_interval = statistics.mean(intervals)
        
        if avg_interval < 24:
            return "daily"
        elif avg_interval < 168:
            return "weekly"
        else:
            return "monthly"

    async def _analyze_peak_usage_times(self, metrics: List[AnalyticsMetric]) -> Dict[str, int]:
        """Analyze peak usage times"""
        
        usage_metrics = [m for m in metrics if m.metric_type == AnalyticsMetricType.USAGE]
        
        hour_counts = defaultdict(int)
        for metric in usage_metrics:
            hour_counts[metric.timestamp.hour] += 1
        
        return dict(hour_counts)

    async def _calculate_usage_growth(self, metrics: List[AnalyticsMetric]) -> Dict[str, Any]:
        """Calculate usage growth"""
        
        usage_metrics = [m for m in metrics if m.metric_type == AnalyticsMetricType.USAGE]
        
        if len(usage_metrics) < 2:
            return {"growth_rate": 0.0, "trend": "stable"}
        
        # Group by week
        weekly_counts = defaultdict(int)
        for metric in usage_metrics:
            week = metric.timestamp.isocalendar()[1]
            weekly_counts[week] += 1
        
        weeks = sorted(weekly_counts.keys())
        if len(weeks) < 2:
            return {"growth_rate": 0.0, "trend": "stable"}
        
        # Calculate growth rate
        first_week = weekly_counts[weeks[0]]
        last_week = weekly_counts[weeks[-1]]
        
        if first_week > 0:
            growth_rate = ((last_week - first_week) / first_week) * 100
        else:
            growth_rate = 100.0 if last_week > 0 else 0.0
        
        trend = "growing" if growth_rate > 10 else "declining" if growth_rate < -10 else "stable"
        
        return {
            "growth_rate": growth_rate,
            "trend": trend,
            "first_week_usage": first_week,
            "last_week_usage": last_week
        }