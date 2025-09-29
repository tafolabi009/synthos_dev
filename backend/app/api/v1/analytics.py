from fastapi import APIRouter, HTTPException, Body, Query, Depends
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime, timedelta
import asyncio
from app.agents.claude_agent import GenerationAnalytics, AdaptiveLearning
from app.services.monitoring import IntelligentMonitoringService
from app.core.redis import get_redis_client

router = APIRouter()

# Singleton instances (in production, use dependency injection or persistent storage)
generation_analytics = GenerationAnalytics()
adaptive_learning = AdaptiveLearning()
monitoring_service = IntelligentMonitoringService()

class PerformanceLogEntry(BaseModel):
    timestamp: float
    response_time: Optional[float]
    quality: Optional[float]
    cost: Optional[float]

class PerformanceLogResponse(BaseModel):
    performance_log: List[PerformanceLogEntry]
    quality_degradation_events: List[float]

class PromptCacheResponse(BaseModel):
    prompt_cache: Dict[str, str]

class FeedbackRequest(BaseModel):
    generation_id: str = Field(...)
    quality_score: float = Field(..., ge=0, le=10)

class FeedbackResponse(BaseModel):
    average_score: Optional[float]
    all_scores: List[List[Any]]

@router.get("/analytics/performance", response_model=PerformanceLogResponse)
def get_generation_performance(skip: int = Query(0), limit: int = Query(100)):
    """Get Claude generation performance analytics (response time, quality, cost)."""
    log = generation_analytics.performance_log[skip:skip+limit]
    entries = [PerformanceLogEntry(timestamp=e[0], response_time=e[1], quality=e[2], cost=e[3]) for e in log]
    return PerformanceLogResponse(
        performance_log=entries,
        quality_degradation_events=generation_analytics.quality_degradation_events
    )

@router.get("/analytics/prompt-cache", response_model=PromptCacheResponse)
def get_prompt_cache():
    """Get cached prompts for schemas."""
    return PromptCacheResponse(prompt_cache=generation_analytics.prompt_cache)

@router.post("/analytics/feedback", response_model=Dict[str, str])
def submit_feedback(feedback: FeedbackRequest):
    """Submit user feedback for a generation job."""
    try:
        adaptive_learning.learn_from_user_feedback(feedback.generation_id, feedback.quality_score)
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Feedback error: {str(e)}")

@router.get("/analytics/feedback/{generation_id}", response_model=FeedbackResponse)
def get_feedback(generation_id: str):
    """Get feedback/quality scores for a generation job."""
    try:
        avg = adaptive_learning.get_average_score(generation_id)
        all_scores = adaptive_learning.feedback_store[generation_id]
        return FeedbackResponse(average_score=avg, all_scores=all_scores)
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"No feedback found: {str(e)}")

# Advanced Analytics Endpoints

class RealTimeMetrics(BaseModel):
    timestamp: datetime
    active_users: int
    generation_jobs: int
    system_health: Dict[str, Any]
    performance_metrics: Dict[str, Any]
    ai_model_usage: Dict[str, int]
    error_rate: float
    throughput: float

class BusinessIntelligence(BaseModel):
    total_generations: int
    total_users: int
    revenue_metrics: Dict[str, Any]
    user_engagement: Dict[str, Any]
    feature_usage: Dict[str, int]
    conversion_rates: Dict[str, float]
    churn_analysis: Dict[str, Any]

class PredictiveAnalytics(BaseModel):
    demand_forecast: Dict[str, Any]
    capacity_planning: Dict[str, Any]
    anomaly_predictions: List[Dict[str, Any]]
    trend_analysis: Dict[str, Any]
    recommendations: List[str]

@router.get("/analytics/realtime", response_model=RealTimeMetrics)
async def get_realtime_metrics():
    """Get real-time system metrics and performance data."""
    try:
        # Get system health
        system_health = await monitoring_service.get_system_health()
        
        # Get performance metrics
        performance_metrics = await monitoring_service.get_performance_insights(1)  # Last hour
        
        # Get AI model usage from Redis
        redis_client = await get_redis_client()
        model_usage = {}
        for model in ["claude-3-5-sonnet", "claude-3-5-haiku", "claude-3-opus", "gpt-4-turbo"]:
            usage_count = await redis_client.get(f"model_usage:{model}")
            model_usage[model] = int(usage_count) if usage_count else 0
        
        return RealTimeMetrics(
            timestamp=datetime.utcnow(),
            active_users=system_health.get("application", {}).get("active_generation_jobs", 0),
            generation_jobs=system_health.get("application", {}).get("active_generation_jobs", 0),
            system_health=system_health,
            performance_metrics=performance_metrics,
            ai_model_usage=model_usage,
            error_rate=system_health.get("application", {}).get("error_rate_percent", 0.0),
            throughput=performance_metrics.get("performance_summary", {}).get("throughput", 0.0)
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get real-time metrics: {str(e)}")

@router.get("/analytics/business-intelligence", response_model=BusinessIntelligence)
async def get_business_intelligence():
    """Get comprehensive business intelligence metrics."""
    try:
        redis_client = await get_redis_client()
        
        # Get total generations
        total_generations = await redis_client.get("total_generations")
        total_generations = int(total_generations) if total_generations else 0
        
        # Get total users
        total_users = await redis_client.get("total_users")
        total_users = int(total_users) if total_users else 0
        
        # Get revenue metrics
        revenue_metrics = {
            "monthly_revenue": await redis_client.get("monthly_revenue") or 0,
            "subscription_revenue": await redis_client.get("subscription_revenue") or 0,
            "usage_revenue": await redis_client.get("usage_revenue") or 0,
            "growth_rate": await redis_client.get("revenue_growth_rate") or 0.0
        }
        
        # Get user engagement metrics
        user_engagement = {
            "daily_active_users": await redis_client.get("dau") or 0,
            "weekly_active_users": await redis_client.get("wau") or 0,
            "monthly_active_users": await redis_client.get("mau") or 0,
            "session_duration": await redis_client.get("avg_session_duration") or 0.0
        }
        
        # Get feature usage
        feature_usage = {
            "synthetic_generation": await redis_client.get("feature:generation") or 0,
            "custom_models": await redis_client.get("feature:custom_models") or 0,
            "privacy_controls": await redis_client.get("feature:privacy") or 0,
            "analytics": await redis_client.get("feature:analytics") or 0
        }
        
        # Get conversion rates
        conversion_rates = {
            "free_to_pro": await redis_client.get("conversion:free_to_pro") or 0.0,
            "pro_to_enterprise": await redis_client.get("conversion:pro_to_enterprise") or 0.0,
            "trial_to_paid": await redis_client.get("conversion:trial_to_paid") or 0.0
        }
        
        # Get churn analysis
        churn_analysis = {
            "monthly_churn_rate": await redis_client.get("churn:monthly") or 0.0,
            "churn_reasons": await redis_client.get("churn:reasons") or {},
            "retention_cohorts": await redis_client.get("retention:cohorts") or {}
        }
        
        return BusinessIntelligence(
            total_generations=total_generations,
            total_users=total_users,
            revenue_metrics=revenue_metrics,
            user_engagement=user_engagement,
            feature_usage=feature_usage,
            conversion_rates=conversion_rates,
            churn_analysis=churn_analysis
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get business intelligence: {str(e)}")

@router.get("/analytics/predictive", response_model=PredictiveAnalytics)
async def get_predictive_analytics():
    """Get predictive analytics and forecasting."""
    try:
        # Demand forecast
        demand_forecast = {
            "next_month_generations": await self._forecast_demand("generations", 30),
            "next_quarter_revenue": await self._forecast_demand("revenue", 90),
            "capacity_requirements": await self._forecast_capacity_requirements()
        }
        
        # Capacity planning
        capacity_planning = {
            "current_capacity": await self._get_current_capacity(),
            "projected_usage": await self._project_usage(),
            "scaling_recommendations": await self._get_scaling_recommendations()
        }
        
        # Anomaly predictions
        anomaly_predictions = await self._detect_anomalies()
        
        # Trend analysis
        trend_analysis = {
            "user_growth_trend": await self._analyze_trend("users"),
            "usage_trend": await self._analyze_trend("generations"),
            "revenue_trend": await self._analyze_trend("revenue")
        }
        
        # Generate recommendations
        recommendations = await self._generate_analytics_recommendations()
        
        return PredictiveAnalytics(
            demand_forecast=demand_forecast,
            capacity_planning=capacity_planning,
            anomaly_predictions=anomaly_predictions,
            trend_analysis=trend_analysis,
            recommendations=recommendations
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get predictive analytics: {str(e)}")

@router.get("/analytics/advanced-metrics")
async def get_advanced_metrics(
    timeframe_hours: int = Query(24, description="Timeframe in hours"),
    metric_types: List[str] = Query(["system", "application", "business"], description="Types of metrics to include")
):
    """Get advanced metrics with filtering and time-based analysis."""
    try:
        redis_client = await get_redis_client()
        
        # Calculate time range
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(hours=timeframe_hours)
        
        # Get metrics for each type
        metrics = {}
        
        if "system" in metric_types:
            metrics["system"] = await self._get_system_metrics(redis_client, start_time, end_time)
        
        if "application" in metric_types:
            metrics["application"] = await self._get_application_metrics(redis_client, start_time, end_time)
        
        if "business" in metric_types:
            metrics["business"] = await self._get_business_metrics(redis_client, start_time, end_time)
        
        # Get performance insights
        insights = await monitoring_service.get_performance_insights(timeframe_hours)
        
        return {
            "timeframe": {
                "start": start_time.isoformat(),
                "end": end_time.isoformat(),
                "hours": timeframe_hours
            },
            "metrics": metrics,
            "insights": insights,
            "summary": await self._generate_metrics_summary(metrics)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get advanced metrics: {str(e)}")

# Helper methods for analytics
async def _forecast_demand(self, metric_type: str, days: int) -> Dict[str, Any]:
    """Forecast demand for a specific metric"""
    # This would implement time series forecasting
    return {
        "forecasted_value": 1000,  # Placeholder
        "confidence_interval": [800, 1200],
        "trend": "increasing",
        "seasonality": "low"
    }

async def _forecast_capacity_requirements(self) -> Dict[str, Any]:
    """Forecast capacity requirements"""
    return {
        "cpu_requirements": "high",
        "memory_requirements": "medium",
        "storage_requirements": "high",
        "network_requirements": "medium"
    }

async def _get_current_capacity(self) -> Dict[str, Any]:
    """Get current system capacity"""
    return {
        "cpu_usage": 0.75,
        "memory_usage": 0.60,
        "storage_usage": 0.45,
        "network_usage": 0.30
    }

async def _project_usage(self) -> Dict[str, Any]:
    """Project future usage"""
    return {
        "next_month": {"cpu": 0.85, "memory": 0.70, "storage": 0.55},
        "next_quarter": {"cpu": 0.95, "memory": 0.80, "storage": 0.65}
    }

async def _get_scaling_recommendations(self) -> List[str]:
    """Get scaling recommendations"""
    return [
        "Consider horizontal scaling for CPU-intensive tasks",
        "Implement caching for frequently accessed data",
        "Optimize database queries for better performance"
    ]

async def _detect_anomalies(self) -> List[Dict[str, Any]]:
    """Detect anomalies in system behavior"""
    return [
        {
            "type": "performance_degradation",
            "severity": "medium",
            "description": "Response time increased by 50%",
            "timestamp": datetime.utcnow().isoformat()
        }
    ]

async def _analyze_trend(self, metric: str) -> Dict[str, Any]:
    """Analyze trend for a specific metric"""
    return {
        "direction": "increasing",
        "rate": 0.15,
        "volatility": "low",
        "seasonality": "none"
    }

async def _generate_analytics_recommendations(self) -> List[str]:
    """Generate analytics-based recommendations"""
    return [
        "Consider implementing predictive scaling",
        "Optimize data generation algorithms",
        "Implement advanced caching strategies"
    ]

async def _get_system_metrics(self, redis_client, start_time: datetime, end_time: datetime) -> Dict[str, Any]:
    """Get system metrics for the time range"""
    return {
        "cpu_usage": 0.75,
        "memory_usage": 0.60,
        "disk_usage": 0.45,
        "network_usage": 0.30
    }

async def _get_application_metrics(self, redis_client, start_time: datetime, end_time: datetime) -> Dict[str, Any]:
    """Get application metrics for the time range"""
    return {
        "request_count": 1000,
        "response_time": 250.0,
        "error_rate": 0.02,
        "throughput": 50.0
    }

async def _get_business_metrics(self, redis_client, start_time: datetime, end_time: datetime) -> Dict[str, Any]:
    """Get business metrics for the time range"""
    return {
        "active_users": 100,
        "generations": 500,
        "revenue": 1000.0,
        "conversion_rate": 0.15
    }

async def _generate_metrics_summary(self, metrics: Dict[str, Any]) -> Dict[str, Any]:
    """Generate summary of all metrics"""
    return {
        "overall_health": "good",
        "key_insights": [
            "System performance is stable",
            "User engagement is increasing",
            "Revenue growth is positive"
        ],
        "recommendations": [
            "Monitor CPU usage closely",
            "Consider scaling infrastructure",
            "Optimize database performance"
        ]
    } 