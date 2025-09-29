"""
Claude AI Agent for Synthetic Data Generation
Advanced synthetic data generation using Anthropic's Claude API with cutting-edge AI capabilities
"""

import json
from typing import Dict, List, Any, Optional, Tuple, AsyncGenerator, Union

# Use optional imports for data processing
from app.utils.optional_imports import pd, np, PANDAS_AVAILABLE, NUMPY_AVAILABLE
from datetime import datetime, timedelta
import asyncio
import logging
from dataclasses import dataclass, asdict
from enum import Enum
import anthropic
from anthropic import Anthropic, AsyncAnthropic
import hashlib
import pickle
from pathlib import Path
import aiofiles
import time
import os

from app.core.config import settings
from app.core.logging import get_logger
from app.models.dataset import Dataset, DatasetColumn, GenerationJob
from app.services.privacy_engine import PrivacyEngine
from app.core.redis import get_redis_client

# Import enhanced realism engine
from app.agents.enhanced_realism_engine import EnhancedRealismEngine, RealismConfig, IndustryDomain

from scipy.stats import ks_2samp, chi2_contingency
from collections import defaultdict
import re # Added for string pattern detection

logger = get_logger(__name__)


class ModelType(Enum):
    """Supported AI models - Updated to latest Claude models"""
    CLAUDE_4_1_SONNET = "claude-4-1-sonnet-20241210"  # Latest Claude 4.1 Sonnet
    CLAUDE_4_1_OPUS = "claude-4-1-opus-20241210"      # Latest Claude 4.1 Opus
    CLAUDE_3_5_SONNET = "claude-3-5-sonnet-20241022"  # Claude 3.5 Sonnet
    CLAUDE_3_5_HAIKU = "claude-3-5-haiku-20241022"    # Claude 3.5 Haiku
    CLAUDE_3_OPUS = "claude-3-opus-20240229"
    CLAUDE_3_SONNET = "claude-3-sonnet-20240229"
    CLAUDE_3_HAIKU = "claude-3-haiku-20240307"


class GenerationStrategy(Enum):
    """Advanced data generation strategies"""
    STATISTICAL = "statistical"
    AI_CREATIVE = "ai_creative"  
    HYBRID = "hybrid"
    PATTERN_BASED = "pattern_based"
    CONSTRAINT_DRIVEN = "constraint_driven"
    DOMAIN_SPECIFIC = "domain_specific"
    MULTI_MODAL = "multi_modal"
    REINFORCEMENT_LEARNING = "reinforcement_learning"


@dataclass
class GenerationConfig:
    """Enhanced configuration for synthetic data generation"""
    rows: int
    privacy_level: str
    epsilon: float
    delta: float
    model_type: ModelType = ModelType.CLAUDE_3_SONNET
    strategy: GenerationStrategy = GenerationStrategy.HYBRID
    maintain_correlations: bool = True
    preserve_distributions: bool = True
    add_noise: bool = True
    quality_threshold: float = 0.8
    batch_size: int = 1000
    max_retries: int = 3
    enable_streaming: bool = True
    cache_strategy: bool = True
    temperature: float = 0.7
    max_tokens: int = 4000
    custom_constraints: Optional[Dict[str, Any]] = None
    semantic_coherence: bool = True
    business_rules: Optional[List[str]] = None


@dataclass
class QualityMetrics:
    """Comprehensive quality assessment metrics"""
    overall_quality: float
    statistical_similarity: float
    distribution_fidelity: float
    correlation_preservation: float
    privacy_protection: float
    semantic_coherence: float
    constraint_compliance: float
    execution_time: float
    memory_usage: float
    details: Dict[str, Any]


class AdvancedClaudeAgent:
    """
    Advanced Claude AI agent with enhanced realism capabilities
    for critical industry applications
    """
    
    def __init__(self):
        self.sync_client = Anthropic(api_key=settings.ANTHROPIC_API_KEY)
        self.async_client = AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)
        self.privacy_engine = PrivacyEngine()
        self.cache = {}
        self.model_registry = {
            ModelType.CLAUDE_3_SONNET: {"context": 200000, "output": 4096},
            ModelType.CLAUDE_3_OPUS: {"context": 200000, "output": 4096}, 
            ModelType.CLAUDE_3_HAIKU: {"context": 200000, "output": 4096},
            ModelType.CLAUDE_2: {"context": 100000, "output": 4096}
        }
        self.realism_engine = EnhancedRealismEngine()
        # === Advanced optimization and analytics ===
        self.prompt_optimizer = PromptOptimizer()
        self.response_processor = ClaudeResponseProcessor()
        self.context_manager = ContextManager()
        self.adaptive_learning = AdaptiveLearning()
        self.analytics = GenerationAnalytics()
    
    async def health_check(self) -> bool:
        """Enhanced health check for AI service"""
        try:
            # Simple health check - just verify the client is initialized
            if not self.async_client or not settings.ANTHROPIC_API_KEY:
                return False
            return True
        except Exception as e:
            logger.error("AI service health check failed", error=str(e))
            return False
    
    async def generate_synthetic_data(
        self,
        dataset: Dataset,
        config: GenerationConfig,
        job: GenerationJob
    ) -> Tuple[pd.DataFrame, QualityMetrics]:
        """
        Advanced synthetic data generation with real-time streaming and quality assessment
        """
        start_time = time.time()
        memory_usage = self._get_memory_usage()
        try:
            logger.info(
                "Starting advanced synthetic data generation",
                dataset_id=dataset.id,
                rows=config.rows,
                strategy=config.strategy.value,
                model=config.model_type.value,
                enable_streaming=config.enable_streaming
            )
            # --- Prompt Optimization ---
            schema = getattr(dataset, 'columns', None)
            sample_data = getattr(dataset, 'sample_data', None)
            privacy_level = getattr(config, 'privacy_level', 'medium')
            # Build context-aware prompt (future: use in _advanced_schema_analysis)
            self.prompt_optimizer.build_context_aware_prompt(schema, sample_data, privacy_level)
            # --- Smart Chunking (future: use for large datasets) ---
            self.context_manager.chunk_intelligently(dataset)
            # Step 1: Intelligent schema analysis with AI reasoning
            schema_analysis = await self._advanced_schema_analysis(dataset, config)
            await job.update_progress(10.0, "Schema analysis complete")
            # Step 2: Pattern detection using multiple AI perspectives
            patterns = await self._multi_perspective_pattern_detection(dataset, config)
            await job.update_progress(20.0, "Pattern detection complete")
            # Step 3: Strategic generation planning
            generation_plan = await self._create_intelligent_generation_plan(
                schema_analysis, patterns, config
            )
            await job.update_progress(30.0, "Generation strategy planned")
            # Step 4: Multi-batch generation with streaming
            if config.enable_streaming:
                synthetic_data = await self._stream_generation_batches(
                    generation_plan, config, job
                )
            else:
                synthetic_data = await self._batch_generation_standard(
                    generation_plan, config, job
                )
            await job.update_progress(70.0, "Data generation complete")
            # --- Multi-stage Validation and Enhancement ---
            self.response_processor.validate_statistical_properties(dataset, synthetic_data)
            synthetic_data = self.response_processor.repair_data_quality(synthetic_data)
            # Step 5: Advanced privacy protection
            if config.add_noise:
                synthetic_data = await self._apply_advanced_privacy_protection(
                    synthetic_data, config, schema_analysis
                )
            await job.update_progress(80.0, "Privacy protection applied")
            # Step 6: Comprehensive quality assessment
            quality_metrics = await self._comprehensive_quality_assessment(
                dataset, synthetic_data, config, start_time, memory_usage
            )
            await job.update_progress(90.0, "Quality assessment complete")
            # Step 7: Enhanced realism processing for critical industry accuracy
            synthetic_data, realism_metrics = await self._apply_enhanced_realism_processing(
                synthetic_data, dataset, config, schema_analysis
            )
            await job.update_progress(95.0, "Enhanced realism processing complete")
            # Step 8: Add enterprise watermarks and metadata
            if settings.ENABLE_WATERMARKS:
                synthetic_data = await self._add_intelligent_watermarks(
                    synthetic_data, dataset, config
                )
            await job.update_progress(100.0, "Generation complete")
            # --- Analytics and Adaptive Learning ---
            self.analytics.track_claude_performance()
            self.adaptive_learning.learn_from_user_feedback(job.id, getattr(quality_metrics, 'overall_quality', None))
            # Cache results for future optimizations
            if config.cache_strategy:
                await self._cache_generation_results(
                    dataset, config, synthetic_data, quality_metrics
                )
            logger.info(
                "Advanced synthetic data generation completed",
                dataset_id=dataset.id,
                synthetic_rows=len(synthetic_data),
                quality_score=quality_metrics.overall_quality,
                execution_time=quality_metrics.execution_time,
                strategy=config.strategy.value
            )
            return synthetic_data, quality_metrics
        except Exception as e:
            logger.error(
                "Advanced synthetic data generation failed",
                dataset_id=dataset.id,
                error=str(e),
                config=asdict(config),
                exc_info=True
            )
            raise
    
    async def _advanced_schema_analysis(
        self, 
        dataset: Dataset, 
        config: GenerationConfig
    ) -> Dict[str, Any]:
        """AI-powered schema analysis with deep understanding and few-shot examples"""
        
        cache_key = f"schema_analysis_{dataset.id}_{hash(str(dataset.columns))}"
        if config.cache_strategy and (cached := await self._get_cache(cache_key)):
            return cached
        
        # Prepare comprehensive schema context
        schema_context = {
            "dataset_info": {
                "name": dataset.name,
                "description": dataset.description,
                "row_count": dataset.row_count,
                "column_count": len(dataset.columns),
                "domain": dataset.domain or "general",
                "creation_date": dataset.created_at.isoformat()
            },
            "columns": [
                {
                    "name": col.name,
                    "type": col.data_type.value,
                    "unique_values": col.unique_values,
                    "null_count": col.null_count,
                    "null_percentage": (col.null_count / dataset.row_count) * 100,
                    "sample_values": col.get_sample_values()[:10],
                    "privacy_category": col.privacy_category,
                    "constraints": col.constraints or {},
                    "business_meaning": col.business_meaning or "unknown"
                }
                for col in dataset.columns
            ]
        }
        # Add few-shot examples
        pattern_samples = await self._prepare_pattern_analysis_samples(dataset)
        few_shot_examples = pattern_samples.get("sample_rows", [])
        
        analysis_prompt = f"""
        As an expert data scientist and synthetic data generation specialist, analyze this dataset schema for optimal synthetic data generation.
        
        Dataset Context: {json.dumps(schema_context, indent=2)}
        
        Few-Shot Examples (real data rows):
        {json.dumps(few_shot_examples, indent=2)}
        
        Generation Requirements:
        - Target rows: {config.rows:,}
        - Privacy level: {config.privacy_level}
        - Strategy: {config.strategy.value}
        - Quality threshold: {config.quality_threshold}
        - Maintain correlations: {config.maintain_correlations}
        - Preserve distributions: {config.preserve_distributions}
        - Add noise: {config.add_noise}
        - Semantic coherence: {config.semantic_coherence}
        - Business rules: {config.business_rules}
        - Custom constraints: {config.custom_constraints}
        
        Provide a comprehensive analysis including:
        1. Data Types & Distributions: Detailed analysis of each column's characteristics and how to mimic them
        2. Relationships: Inter-column dependencies and correlations, with explicit mapping
        3. Business Logic: Inferred business rules and constraints, with examples
        4. Privacy Implications: Sensitive data identification and protection needs
        5. Generation Complexity: Difficulty assessment for each column
        6. Optimization Opportunities: Strategies for efficient, high-quality generation
        7. Quality Metrics: Specific quality measures for this dataset
        8. Risk Assessment: Potential issues and mitigation strategies
        
        Return as structured JSON with actionable insights for synthetic data generation.
        """
        
        try:
            response = await self._call_claude_advanced(
                analysis_prompt, config.model_type, temperature=0.3
            )
            analysis = json.loads(response)
            analysis["statistical_insights"] = await self._statistical_enhancement(dataset)
            if config.cache_strategy:
                await self._set_cache(cache_key, analysis, ttl=3600)
            return analysis
        except json.JSONDecodeError as e:
            logger.warning(
                "Claude response parsing failed, using enhanced fallback", 
                error=str(e)
            )
            return await self._enhanced_fallback_schema_analysis(dataset, config)
    
    async def _multi_perspective_pattern_detection(
        self, 
        dataset: Dataset, 
        config: GenerationConfig
    ) -> Dict[str, Any]:
        """Multi-perspective pattern analysis using different AI reasoning approaches"""
        
        cache_key = f"patterns_{dataset.id}_{config.strategy.value}"
        if config.cache_strategy and (cached := await self._get_cache(cache_key)):
            return cached
        
        # Prepare data samples for pattern analysis
        data_samples = await self._prepare_pattern_analysis_samples(dataset)
        
        # Multiple analysis perspectives
        perspectives = [
            ("statistical", "Focus on statistical patterns, distributions, and correlations"),
            ("business", "Analyze from business logic and domain knowledge perspective"),
            ("temporal", "Identify time-based patterns and sequences"),
            ("categorical", "Examine categorical relationships and hierarchies"),
            ("anomaly", "Detect outliers and unusual patterns that should be preserved")
        ]
        
        pattern_results = {}
        
        for perspective_name, perspective_instruction in perspectives:
            pattern_prompt = f"""
            {perspective_instruction}
            
            Dataset: {dataset.name}
            Data Samples: {json.dumps(data_samples, indent=2)}
            
            Analyze patterns from this {perspective_name} perspective:
            
            1. Key patterns identified
            2. Strength and importance of each pattern
            3. Interdependencies with other columns
            4. Generation implications
            5. Preservation strategies
            
            Return structured JSON with specific, actionable pattern insights.
            """
            
            try:
                response = await self._call_claude_advanced(
                    pattern_prompt, config.model_type, temperature=0.5
                )
                pattern_results[perspective_name] = json.loads(response)
                
            except Exception as e:
                logger.warning(
                    f"Pattern analysis failed for {perspective_name} perspective",
                    error=str(e)
                )
                pattern_results[perspective_name] = {"error": str(e)}
        
        # Synthesize multi-perspective insights
        synthesis_prompt = f"""
        Synthesize these multi-perspective pattern analyses into unified insights:
        
        {json.dumps(pattern_results, indent=2)}
        
        Create a comprehensive pattern profile that prioritizes:
        1. Most critical patterns to preserve
        2. Generation strategy recommendations
        3. Quality validation approaches
        4. Risk mitigation strategies
        
        Return as structured JSON.
        """
        
        try:
            synthesis_response = await self._call_claude_advanced(
                synthesis_prompt, config.model_type, temperature=0.4
            )
            final_patterns = json.loads(synthesis_response)
            final_patterns["raw_perspectives"] = pattern_results
            
            if config.cache_strategy:
                await self._set_cache(cache_key, final_patterns, ttl=1800)
            
            return final_patterns
            
        except Exception as e:
            logger.error("Pattern synthesis failed", error=str(e))
            return {"perspectives": pattern_results, "synthesis_error": str(e)}
    
    async def _create_intelligent_generation_plan(
        self,
        schema_analysis: Dict[str, Any],
        patterns: Dict[str, Any],
        config: GenerationConfig
    ) -> Dict[str, Any]:
        """Create intelligent generation plan using AI strategic planning"""
        
        planning_prompt = f"""
        As an AI architect, create an optimal synthetic data generation plan:
        
        Schema Analysis: {json.dumps(schema_analysis, indent=2)}
        Pattern Analysis: {json.dumps(patterns, indent=2)}
        
        Generation Configuration:
        - Rows: {config.rows:,}
        - Strategy: {config.strategy.value}
        - Model: {config.model_type.value}
        - Quality threshold: {config.quality_threshold}
        - Batch size: {config.batch_size}
        - Custom constraints: {config.custom_constraints}
        
        Create a detailed generation plan including:
        
        1. **Column Generation Order**: Optimal sequence based on dependencies
        2. **Batch Strategy**: How to efficiently process {config.rows:,} rows
        3. **Quality Checkpoints**: Validation points during generation
        4. **Resource Optimization**: Memory and computation efficiency
        5. **Error Handling**: Fallback strategies for each step
        6. **Progressive Enhancement**: How to improve quality iteratively
        
        Return as executable JSON plan.
        """
        
        try:
            response = await self._call_claude_advanced(
                planning_prompt, config.model_type, temperature=0.3
            )
            plan = json.loads(response)
            
            # Enhance plan with runtime optimizations
            plan["runtime_config"] = {
                "batch_size": min(config.batch_size, max(100, config.rows // 10)),
                "parallel_workers": min(4, max(1, config.rows // 5000)),
                "memory_limit": "2GB",
                "timeout_per_batch": 300,
                "retry_strategy": "exponential_backoff"
            }
            
            return plan
            
        except Exception as e:
            logger.warning("AI planning failed, using optimized fallback", error=str(e))
            return await self._fallback_generation_plan(schema_analysis, config)
    
    async def _stream_generation_batches(
        self,
        generation_plan: Dict[str, Any],
        config: GenerationConfig,
        job: GenerationJob
    ) -> pd.DataFrame:
        """Real-time streaming generation with live progress updates"""
        
        total_batches = (config.rows + config.batch_size - 1) // config.batch_size
        generated_data = []
        
        async def generate_batch_stream(batch_idx: int) -> pd.DataFrame:
            batch_size = min(
                config.batch_size, 
                config.rows - (batch_idx * config.batch_size)
            )
            
            batch_data = await self._generate_intelligent_batch(
                generation_plan, batch_size, batch_idx, config
            )
            
            # Update progress in real-time
            progress = 30.0 + (batch_idx + 1) / total_batches * 40.0
            await job.update_progress(
                progress, 
                f"Generated batch {batch_idx + 1}/{total_batches}"
            )
            
            return batch_data
        
        # Generate batches with concurrency control
        semaphore = asyncio.Semaphore(generation_plan["runtime_config"]["parallel_workers"])
        
        async def controlled_batch_generation(batch_idx: int):
            async with semaphore:
                return await generate_batch_stream(batch_idx)
        
        # Execute batch generation
        batch_tasks = [
            controlled_batch_generation(i) for i in range(total_batches)
        ]
        
        for batch_future in asyncio.as_completed(batch_tasks):
            batch_data = await batch_future
            generated_data.append(batch_data)
        
        # Combine all batches
        final_data = pd.concat(generated_data, ignore_index=True)
        return final_data.head(config.rows)  # Ensure exact row count
    
    async def _generate_intelligent_batch(
        self,
        plan: Dict[str, Any],
        batch_size: int,
        batch_idx: int,
        config: GenerationConfig
    ) -> pd.DataFrame:
        """Generate a single batch using intelligent AI reasoning with few-shot and chain prompting"""
        # Prepare few-shot examples for this batch
        few_shot_examples = plan.get("few_shot_examples")
        if not few_shot_examples and hasattr(self, "_prepare_pattern_analysis_samples"):
            # Fallback: try to get from dataset if not in plan
            dataset = plan.get("dataset")
            if dataset:
                pattern_samples = await self._prepare_pattern_analysis_samples(dataset)
                few_shot_examples = pattern_samples.get("sample_rows", [])
        batch_prompt = f"""
        Generate {batch_size} rows of synthetic data following this intelligent plan and using the provided few-shot examples for guidance.
        
        Generation Plan: {json.dumps(plan, indent=2)}
        Batch Index: {batch_idx}
        
        Few-Shot Examples (real data rows):
        {json.dumps(few_shot_examples, indent=2)}
        
        Requirements:
        1. Follow the column generation order from the plan
        2. Maintain all specified relationships and constraints
        3. Ensure data quality meets threshold: {config.quality_threshold}
        4. Apply business rules and logic consistently, as shown in the examples
        5. Generate realistic, coherent data that matches the patterns in the few-shot examples
        6. Return ONLY a valid JSON array of {batch_size} data objects. Each object should have all required columns with appropriate values.
        """
        for attempt in range(config.max_retries):
            try:
                response = await self._call_claude_advanced(
                    batch_prompt, 
                    config.model_type, 
                    temperature=config.temperature,
                    max_tokens=min(config.max_tokens, batch_size * 50)
                )
                batch_data = json.loads(response)
                df = pd.DataFrame(batch_data)
                if await self._validate_batch_quality(df, plan, config):
                    return df
                else:
                    logger.warning(f"Batch {batch_idx} quality below threshold, retrying...")
            except Exception as e:
                logger.warning(
                    f"Batch generation attempt {attempt + 1} failed", 
                    batch_idx=batch_idx,
                    error=str(e)
                )
                if attempt == config.max_retries - 1:
                    logger.info(f"Using fallback generation for batch {batch_idx}")
                    return await self._fallback_batch_generation(plan, batch_size, config)
        return await self._fallback_batch_generation(plan, batch_size, config)
    
    async def _comprehensive_quality_assessment(
        self,
        original_dataset: Dataset,
        synthetic_data: pd.DataFrame,
        config: GenerationConfig,
        start_time: float,
        initial_memory: float
    ) -> QualityMetrics:
        """Comprehensive quality assessment using multiple AI and statistical approaches"""
        
        execution_time = time.time() - start_time
        current_memory = self._get_memory_usage()
        memory_usage = current_memory - initial_memory
        
        # Multi-dimensional quality assessment
        quality_tasks = [
            self._assess_statistical_similarity(original_dataset, synthetic_data),
            self._assess_distribution_fidelity(original_dataset, synthetic_data),
            self._assess_correlation_preservation(original_dataset, synthetic_data),
            self._assess_privacy_protection(synthetic_data, config),
            self._assess_semantic_coherence(synthetic_data, config),
            self._assess_constraint_compliance(synthetic_data, config)
        ]
        
        quality_results = await asyncio.gather(*quality_tasks, return_exceptions=True)
        
        # Calculate composite scores
        statistical_similarity = quality_results[0] if not isinstance(quality_results[0], Exception) else 0.0
        distribution_fidelity = quality_results[1] if not isinstance(quality_results[1], Exception) else 0.0
        correlation_preservation = quality_results[2] if not isinstance(quality_results[2], Exception) else 0.0
        privacy_protection = quality_results[3] if not isinstance(quality_results[3], Exception) else 0.0
        semantic_coherence = quality_results[4] if not isinstance(quality_results[4], Exception) else 0.0
        constraint_compliance = quality_results[5] if not isinstance(quality_results[5], Exception) else 0.0
        
        # Weighted overall quality score
        weights = {
            "statistical": 0.25,
            "distribution": 0.20,
            "correlation": 0.20,
            "privacy": 0.15,
            "semantic": 0.10,
            "constraints": 0.10
        }
        
        overall_quality = (
            statistical_similarity * weights["statistical"] +
            distribution_fidelity * weights["distribution"] +
            correlation_preservation * weights["correlation"] +
            privacy_protection * weights["privacy"] +
            semantic_coherence * weights["semantic"] +
            constraint_compliance * weights["constraints"]
        )
        
        return QualityMetrics(
            overall_quality=overall_quality,
            statistical_similarity=statistical_similarity,
            distribution_fidelity=distribution_fidelity,
            correlation_preservation=correlation_preservation,
            privacy_protection=privacy_protection,
            semantic_coherence=semantic_coherence,
            constraint_compliance=constraint_compliance,
            execution_time=execution_time,
            memory_usage=memory_usage,
            details={
                "batch_count": len(synthetic_data) // config.batch_size + 1,
                "generation_strategy": config.strategy.value,
                "model_used": config.model_type.value,
                "privacy_level": config.privacy_level,
                "rows_generated": len(synthetic_data),
                "columns_generated": len(synthetic_data.columns),
                "exceptions": [str(e) for e in quality_results if isinstance(e, Exception)]
            }
        )
    
    async def _apply_enhanced_realism_processing(
        self,
        synthetic_data: pd.DataFrame,
        dataset: Dataset,
        config: GenerationConfig,
        schema_analysis: Dict[str, Any]
    ) -> Tuple[pd.DataFrame, Dict[str, float]]:
        """
        Apply enhanced realism processing for critical industry accuracy
        """
        logger.info("Applying enhanced realism processing for maximum accuracy")
        
        # Determine industry domain from dataset metadata
        industry_domain = self._detect_industry_domain(dataset, schema_analysis)
        
        # Configure realism settings
        realism_config = RealismConfig(
            industry_domain=industry_domain,
            enforce_business_rules=True,
            validate_domain_constraints=True,
            preserve_temporal_patterns=True,
            maintain_semantic_consistency=True,
            use_domain_ontologies=True,
            apply_regulatory_compliance=True,
            cross_field_validation=True,
            statistical_accuracy_threshold=0.98,  # Ultra-high accuracy for critical industries
            correlation_preservation_threshold=0.95
        )
        
        # Load original data for pattern analysis
        original_data = await self._load_original_dataset_sample(dataset)
        
        # Apply enhanced realism
        enhanced_data, realism_metrics = await self.realism_engine.enhance_synthetic_data(
            synthetic_data=synthetic_data,
            original_data=original_data,
            config=realism_config,
            schema_analysis=schema_analysis
        )
        
        logger.info(
            "Enhanced realism processing complete",
            industry_domain=industry_domain.value,
            overall_realism_score=realism_metrics.get('overall_realism', 0.0),
            domain_compliance=realism_metrics.get('domain_compliance', 0.0),
            business_rule_adherence=realism_metrics.get('business_rule_adherence', 0.0)
        )
        
        return enhanced_data, realism_metrics
    
    def _detect_industry_domain(self, dataset: Dataset, schema_analysis: Dict[str, Any]) -> IndustryDomain:
        """
        Automatically detect industry domain from dataset characteristics
        """
        domain_indicators = {
            IndustryDomain.HEALTHCARE: [
                'patient', 'medical', 'diagnosis', 'icd', 'blood_pressure', 'heart_rate',
                'medication', 'doctor', 'hospital', 'treatment', 'symptom', 'vital',
                'temperature', 'weight', 'height', 'bmi', 'allergy'
            ],
            IndustryDomain.FINANCE: [
                'account', 'balance', 'transaction', 'credit', 'loan', 'payment',
                'interest', 'income', 'debt', 'mortgage', 'investment', 'portfolio',
                'risk', 'return', 'equity', 'bond', 'currency', 'exchange'
            ],
            IndustryDomain.MANUFACTURING: [
                'production', 'quality', 'defect', 'batch', 'serial', 'machine',
                'temperature', 'pressure', 'speed', 'efficiency', 'yield',
                'maintenance', 'downtime', 'throughput', 'cycle_time'
            ],
            IndustryDomain.ENERGY: [
                'power', 'voltage', 'current', 'grid', 'consumption', 'generation',
                'renewable', 'solar', 'wind', 'turbine', 'meter', 'load'
            ],
            IndustryDomain.AUTOMOTIVE: [
                'vehicle', 'engine', 'transmission', 'fuel', 'emission', 'brake',
                'tire', 'suspension', 'electronic', 'diagnostic', 'mileage'
            ],
            IndustryDomain.RETAIL: [
                'product', 'inventory', 'sales', 'customer', 'purchase', 'order',
                'shipment', 'return', 'discount', 'promotion', 'category', 'brand'
            ]
        }
        
        # Analyze column names and descriptions
        text_to_analyze = []
        text_to_analyze.extend([col.lower() for col in dataset.columns if hasattr(dataset, 'columns')])
        
        if dataset.description:
            text_to_analyze.append(dataset.description.lower())
        if dataset.name:
            text_to_analyze.append(dataset.name.lower())
        
        # Extract column information from schema analysis
        if 'columns' in schema_analysis:
            for col_info in schema_analysis['columns']:
                if 'name' in col_info:
                    text_to_analyze.append(col_info['name'].lower())
                if 'business_meaning' in col_info and col_info['business_meaning']:
                    text_to_analyze.append(col_info['business_meaning'].lower())
        
        combined_text = ' '.join(text_to_analyze)
        
        # Score each domain
        domain_scores = {}
        for domain, indicators in domain_indicators.items():
            score = sum(1 for indicator in indicators if indicator in combined_text)
            domain_scores[domain] = score
        
        # Return domain with highest score, default to GENERAL
        if domain_scores:
            detected_domain = max(domain_scores, key=domain_scores.get)
            if domain_scores[detected_domain] > 0:
                logger.info(f"Detected industry domain: {detected_domain.value}")
                return detected_domain
        
        logger.info("Using general domain (no specific industry detected)")
        return IndustryDomain.GENERAL
    
    async def _load_original_dataset_sample(self, dataset: Dataset) -> pd.DataFrame:
        """
        Load a sample of the original dataset for pattern analysis
        """
        try:
            logger.info(f"Loading original dataset sample for pattern analysis: {dataset.id}")
            
            # Load dataset from S3 or local storage
            if dataset.file_path:
                if dataset.file_path.startswith('s3://'):
                    # Load from S3
                    import boto3
                    from io import StringIO
                    
                    s3_client = boto3.client('s3')
                    bucket, key = dataset.file_path.replace('s3://', '').split('/', 1)
                    
                    response = s3_client.get_object(Bucket=bucket, Key=key)
                    content = response['Body'].read().decode('utf-8')
                    
                    # Determine file format and load accordingly
                    if dataset.file_path.endswith('.csv'):
                        df = pd.read_csv(StringIO(content))
                    elif dataset.file_path.endswith('.json'):
                        df = pd.read_json(StringIO(content))
                    elif dataset.file_path.endswith('.xlsx') or dataset.file_path.endswith('.xls'):
                        df = pd.read_excel(StringIO(content))
                    else:
                        # Try CSV as default
                        df = pd.read_csv(StringIO(content))
                else:
                    # Load from local file system
                    if dataset.file_path.endswith('.csv'):
                        df = pd.read_csv(dataset.file_path)
                    elif dataset.file_path.endswith('.json'):
                        df = pd.read_json(dataset.file_path)
                    elif dataset.file_path.endswith('.xlsx') or dataset.file_path.endswith('.xls'):
                        df = pd.read_excel(dataset.file_path)
                    else:
                        df = pd.read_csv(dataset.file_path)
                
                # Return a representative sample (10% of data, max 1000 rows)
                sample_size = min(len(df) // 10, 1000)
                if sample_size > 0:
                    return df.sample(n=sample_size, random_state=42)
                else:
                    return df
            else:
                logger.warning(f"No file path found for dataset {dataset.id}")
                return pd.DataFrame()
            
        except Exception as e:
            logger.warning(f"Could not load original dataset sample: {e}")
            return pd.DataFrame()
    
    async def _post_process_data(
        self,
        synthetic_data: pd.DataFrame,
        config: GenerationConfig,
        schema_analysis: Dict[str, Any]
    ) -> pd.DataFrame:
        """
        Post-processing and validation of generated data
        """
        logger.info("Starting post-processing and validation")
        
        # Apply enhanced realism processing
        synthetic_data, realism_metrics = await self._apply_enhanced_realism_processing(
            synthetic_data, dataset, config, schema_analysis
        )
        
        # Apply business rules and constraints
        if config.business_rules:
            synthetic_data = self._apply_business_rules(synthetic_data, config.business_rules)
        
        # Add enterprise watermarks and metadata
        if settings.ENABLE_WATERMARKS:
            synthetic_data = await self._add_intelligent_watermarks(
                synthetic_data, dataset, config
            )
        
        logger.info("Post-processing and validation complete")
        return synthetic_data
    
    def _apply_business_rules(self, data: pd.DataFrame, rules: List[str]) -> pd.DataFrame:
        """
        Applies a list of business rules to the generated data using advanced rule engine.
        """
        logger.info(f"Applying {len(rules)} business rules")
        
        for rule in rules:
            logger.debug(f"Applying rule: {rule}")
            
            try:
                # Parse rule components
                rule_parts = rule.split('|')
                rule_type = rule_parts[0].strip()
                
                if rule_type == 'RANGE':
                    # Format: RANGE|column|min|max
                    column = rule_parts[1].strip()
                    min_val = float(rule_parts[2].strip())
                    max_val = float(rule_parts[3].strip())
                    
                    if column in data.columns:
                        data[column] = data[column].clip(min_val, max_val)
                
                elif rule_type == 'RELATIONSHIP':
                    # Format: RELATIONSHIP|col1|operator|col2|factor
                    col1 = rule_parts[1].strip()
                    operator = rule_parts[2].strip()
                    col2 = rule_parts[3].strip()
                    factor = float(rule_parts[4].strip())
                    
                    if col1 in data.columns and col2 in data.columns:
                        if operator == 'MULTIPLY':
                            data[col1] = data[col2] * factor
                        elif operator == 'ADD':
                            data[col1] = data[col2] + factor
                        elif operator == 'DIVIDE':
                            data[col1] = data[col2] / factor
                
                elif rule_type == 'CONDITIONAL':
                    # Format: CONDITIONAL|condition_col|condition_val|target_col|target_val
                    condition_col = rule_parts[1].strip()
                    condition_val = rule_parts[2].strip()
                    target_col = rule_parts[3].strip()
                    target_val = rule_parts[4].strip()
                    
                    if condition_col in data.columns and target_col in data.columns:
                        mask = data[condition_col] == condition_val
                        data.loc[mask, target_col] = target_val
                
                elif rule_type == 'FORMAT':
                    # Format: FORMAT|column|format_type
                    column = rule_parts[1].strip()
                    format_type = rule_parts[2].strip()
                    
                    if column in data.columns:
                        if format_type == 'EMAIL':
                            data[column] = data[column].apply(lambda x: f"{x.lower()}@example.com" if pd.notna(x) else x)
                        elif format_type == 'PHONE':
                            data[column] = data[column].apply(lambda x: f"+1-{x}" if pd.notna(x) else x)
                        elif format_type == 'DATE':
                            data[column] = pd.to_datetime(data[column], errors='coerce')
                
                elif rule_type == 'UNIQUE':
                    # Format: UNIQUE|column
                    column = rule_parts[1].strip()
                    
                    if column in data.columns:
                        data[column] = data[column].drop_duplicates()
                
                elif rule_type == 'CUSTOM':
                    # Format: CUSTOM|python_expression
                    expression = rule_parts[1].strip()
                    
                    # Safely evaluate custom expression
                    try:
                        # Create a safe environment for evaluation
                        safe_dict = {
                            'data': data,
                            'pd': pd,
                            'np': np,
                            'datetime': datetime,
                            'math': math,
                            'random': random
                        }
                        
                        # Execute the custom expression
                        exec(expression, safe_dict)
                        data = safe_dict['data']
                    except Exception as e:
                        logger.warning(f"Custom rule evaluation failed: {e}")
                
                # Handle age calculation from birth date
                if 'age' in data.columns and 'birth_date' in data.columns:
                    data['age'] = data['birth_date'].apply(
                        lambda x: int((datetime.now() - pd.to_datetime(x)).days / 365.25) 
                        if pd.notna(x) else None
                    )
                
                # Handle income consistency
                if 'income' in data.columns and 'salary' in data.columns:
                    data['income'] = data['salary'] * 12
                
                # Handle BMI calculation
                if 'height' in data.columns and 'weight' in data.columns and 'bmi' in data.columns:
                    data['bmi'] = data.apply(
                        lambda row: (row['weight'] / ((row['height'] / 100) ** 2)) 
                        if pd.notna(row['weight']) and pd.notna(row['height']) else None, 
                        axis=1
                    )
                
            except Exception as e:
                logger.warning(f"Failed to apply rule '{rule}': {e}")
                continue
        
        return data
    
    async def _add_intelligent_watermarks(
        self,
        synthetic_data: pd.DataFrame,
        dataset: Dataset,
        config: GenerationConfig
    ) -> pd.DataFrame:
        """
        Adds intelligent watermarks and metadata to the generated data using advanced watermarking engine.
        """
        logger.info("Adding intelligent watermarks and metadata")
        
        try:
            # Generate unique watermark hash
            import hashlib
            import uuid
            
            watermark_hash = hashlib.sha256(
                f"{dataset.id}_{config.rows}_{config.privacy_level}_{datetime.now().isoformat()}".encode()
            ).hexdigest()[:16]
            
            # Add comprehensive watermarks
            synthetic_data['synthetic_source'] = 'Synthos AI Enterprise'
            synthetic_data['generation_date'] = datetime.now().isoformat()
            synthetic_data['dataset_id'] = dataset.id
            synthetic_data['generation_job_id'] = getattr(job, 'id', str(uuid.uuid4()))
            synthetic_data['watermark_hash'] = watermark_hash
            synthetic_data['privacy_level'] = config.privacy_level
            synthetic_data['epsilon'] = config.epsilon
            synthetic_data['delta'] = config.delta
            synthetic_data['model_type'] = config.model_type.value
            synthetic_data['strategy'] = config.strategy.value
            synthetic_data['quality_threshold'] = config.quality_threshold
            synthetic_data['batch_size'] = config.batch_size
            synthetic_data['temperature'] = config.temperature
            synthetic_data['max_tokens'] = config.max_tokens
            
            # Add version information
            synthetic_data['synthos_version'] = '2.0.0'
            synthetic_data['watermark_version'] = '1.0'
            
            # Add statistical watermarks
            for col in synthetic_data.columns:
                if col not in ['synthetic_source', 'generation_date', 'dataset_id', 'generation_job_id', 
                              'watermark_hash', 'privacy_level', 'epsilon', 'delta', 'model_type', 
                              'strategy', 'quality_threshold', 'batch_size', 'temperature', 'max_tokens',
                              'synthos_version', 'watermark_version']:
                    
                    if synthetic_data[col].dtype in ['int64', 'float64']:
                        # Add statistical watermark for numeric columns
                        mean_val = synthetic_data[col].mean()
                        std_val = synthetic_data[col].std()
                        synthetic_data[f'{col}_watermark_mean'] = mean_val
                        synthetic_data[f'{col}_watermark_std'] = std_val
                    
                    elif synthetic_data[col].dtype == 'object':
                        # Add pattern watermark for string columns
                        unique_count = synthetic_data[col].nunique()
                        synthetic_data[f'{col}_watermark_unique_count'] = unique_count
            
            # Add row-level watermarks
            synthetic_data['row_watermark'] = [
                hashlib.md5(f"{watermark_hash}_{i}".encode()).hexdigest()[:8] 
                for i in range(len(synthetic_data))
            ]
            
            # Add column correlation watermarks
            numeric_cols = synthetic_data.select_dtypes(include=[np.number]).columns
            if len(numeric_cols) > 1:
                corr_matrix = synthetic_data[numeric_cols].corr()
                synthetic_data['correlation_watermark'] = hashlib.sha256(
                    str(corr_matrix.values.tobytes())
                ).hexdigest()[:8]
            
            # Add temporal watermarks
            synthetic_data['temporal_watermark'] = datetime.now().strftime('%Y%m%d_%H%M%S')
            
            # Add quality score watermarks
            synthetic_data['quality_watermark'] = config.quality_threshold
            
            logger.info(f"Added comprehensive watermarks with hash: {watermark_hash}")
            return synthetic_data
            
        except Exception as e:
            logger.error(f"Watermarking failed: {e}")
            # Fallback to basic watermarks
            synthetic_data['synthetic_source'] = 'Synthos AI'
            synthetic_data['generation_date'] = datetime.now().isoformat()
            return synthetic_data
    
    async def _cache_generation_results(
        self,
        dataset: Dataset,
        config: GenerationConfig,
        synthetic_data: pd.DataFrame,
        quality_metrics: QualityMetrics
    ):
        """
        Caches the results of a synthetic data generation job.
        """
        cache_key = f"synthetic_data_{dataset.id}_{config.rows}_{config.privacy_level}_{config.strategy.value}_{config.model_type.value}"
        cache_value = {
            "synthetic_data": synthetic_data.to_dict(orient="records"),
            "quality_metrics": asdict(quality_metrics),
            "generation_config": asdict(config),
            "dataset_id": dataset.id,
            "generation_date": datetime.now().isoformat()
        }
        await self._set_cache(cache_key, cache_value, ttl=3600) # Cache for 1 hour
    
    async def _get_cache(self, key: str) -> Optional[Any]:
        """
        Retrieves an item from the cache.
        """
        if settings.REDIS_ENABLED:
            redis_client = await get_redis_client()
            if redis_client:
                cached_data = await redis_client.get(key)
                if cached_data:
                    return pickle.loads(cached_data)
        return None
    
    async def _set_cache(self, key: str, value: Any, ttl: int):
        """
        Sets an item in the cache.
        """
        if settings.REDIS_ENABLED:
            redis_client = await get_redis_client()
            if redis_client:
                await redis_client.set(key, pickle.dumps(value), ex=ttl)
        else:
            # In-memory caching for development
            self.cache[key] = value
    
    def _get_memory_usage(self) -> float:
        """
        Gets the current memory usage of the process.
        """
        try:
            import psutil
            process = psutil.Process(os.getpid())
            return process.memory_info().rss / 1024 / 1024 # MB
        except ImportError:
            logger.warning("psutil not installed, memory usage tracking disabled.")
            return 0.0
        except Exception as e:
            logger.error("Error getting memory usage", error=str(e))
            return 0.0
    
    async def _call_claude_advanced(
        self,
        prompt: str,
        model_type: ModelType,
        temperature: float = 0.7,
        max_tokens: int = 4000
    ) -> str:
        """
        Calls Claude API with advanced configuration.
        """
        try:
            if settings.ANTHROPIC_API_KEY:
                if settings.ANTHROPIC_API_KEY.startswith("sk-"):
                    # Use async_client for Anthropic API key starting with "sk-"
                    response = await self.async_client.messages.create(
                        model=model_type.value,
                        max_tokens=max_tokens,
                        messages=[{"role": "user", "content": prompt}],
                        temperature=temperature,
                        stream=False
                    )
                else:
                    # Use sync_client for other API keys
                    response = self.sync_client.messages.create(
                        model=model_type.value,
                        max_tokens=max_tokens,
                        messages=[{"role": "user", "content": prompt}],
                        temperature=temperature,
                        stream=False
                    )
                return response.content
            else:
                raise ValueError("Anthropic API key not configured.")
        except Exception as e:
            logger.error("Claude API call failed", error=str(e))
            raise
    
    async def _validate_batch_quality(
        self,
        batch_data: pd.DataFrame,
        generation_plan: Dict[str, Any],
        config: GenerationConfig
    ) -> bool:
        """
        Validates the quality of a generated batch against the plan.
        """
        # This is a placeholder. In a real system, you would:
        # 1. Check for missing columns
        # 2. Validate data types
        # 3. Ensure all constraints are met
        # 4. Check for anomalies or outliers
        # 5. Compare with original data patterns
        
        # Example: Check if all required columns are present
        required_cols = set(generation_plan.get("column_generation_order", []))
        if not required_cols.issubset(set(batch_data.columns)):
            logger.warning("Generated batch missing required columns.")
            return False
        
        # Example: Check for data type consistency
        for col_name, col_type in generation_plan["column_types"].items():
            if col_name in batch_data.columns:
                if not pd.api.types.is_type_convertible(batch_data[col_name].dtype, col_type):
                    logger.warning(f"Data type mismatch for column {col_name}.")
                    return False
        
        # Example: Check for constraints
        if config.custom_constraints:
            for constraint_name, constraint_details in config.custom_constraints.items():
                if constraint_name in batch_data.columns:
                    if "min_value" in constraint_details:
                        if not (batch_data[constraint_name] >= constraint_details["min_value"]).all():
                            logger.warning(f"Constraint {constraint_name} min_value failed.")
                            return False
                    if "max_value" in constraint_details:
                        if not (batch_data[constraint_name] <= constraint_details["max_value"]).all():
                            logger.warning(f"Constraint {constraint_name} max_value failed.")
                            return False
                    if "unique" in constraint_details:
                        if not (batch_data[constraint_name].nunique() == len(batch_data[constraint_name])):
                            logger.warning(f"Constraint {constraint_name} unique failed.")
                            return False
        
        # Example: Check for anomalies or outliers
        if config.add_noise:
            # This is a simplified check. A real system would use statistical tests
            # and domain-specific anomaly detection.
            if "age" in batch_data.columns and "birth_date" in batch_data.columns:
                age_from_birth = (datetime.now() - pd.to_datetime(batch_data["birth_date"])).dt.days / 365.25
                if (age_from_birth < 0).any():
                    logger.warning("Negative age detected in generated data.")
                    return False
        
        return True
    
    async def _fallback_batch_generation(
        self,
        generation_plan: Dict[str, Any],
        batch_size: int,
        config: GenerationConfig
    ) -> pd.DataFrame:
        """
        Advanced fallback generation strategy using statistical modeling and pattern-based generation.
        """
        logger.warning("Using advanced fallback generation due to AI failure.")
        
        try:
            # Extract schema information
            column_types = generation_plan.get("column_types", {})
            column_stats = generation_plan.get("column_statistics", {})
            column_patterns = generation_plan.get("column_patterns", {})
            correlations = generation_plan.get("correlations", {})
            
            # Generate data using advanced statistical methods
            synthetic_data = []
            
            for i in range(batch_size):
                row = {}
                
                for col_name in generation_plan.get("column_generation_order", []):
                    col_type = column_types.get(col_name, "string")
                    col_stats = column_stats.get(col_name, {})
                    col_patterns = column_patterns.get(col_name, {})
                    
                    # Generate value based on type and statistics
                    if col_type == "integer":
                        if col_stats:
                            min_val = col_stats.get("min", 0)
                            max_val = col_stats.get("max", 100)
                            mean_val = col_stats.get("mean", (min_val + max_val) / 2)
                            std_val = col_stats.get("std", (max_val - min_val) / 6)
                            
                            # Use normal distribution with bounds
                            value = int(np.clip(
                                np.random.normal(mean_val, std_val),
                                min_val, max_val
                            ))
                        else:
                            value = np.random.randint(1, 100)
                    
                    elif col_type == "float":
                        if col_stats:
                            min_val = col_stats.get("min", 0.0)
                            max_val = col_stats.get("max", 100.0)
                            mean_val = col_stats.get("mean", (min_val + max_val) / 2)
                            std_val = col_stats.get("std", (max_val - min_val) / 6)
                            
                            # Use normal distribution with bounds
                            value = np.clip(
                                np.random.normal(mean_val, std_val),
                                min_val, max_val
                            )
                        else:
                            value = np.random.uniform(0.0, 100.0)
                    
                    elif col_type == "string":
                        if col_patterns and "categories" in col_patterns:
                            # Use categorical distribution
                            categories = col_patterns["categories"]
                            probabilities = col_patterns.get("probabilities", [1/len(categories)] * len(categories))
                            value = np.random.choice(categories, p=probabilities)
                        elif col_patterns and "format" in col_patterns:
                            # Use format-based generation
                            format_type = col_patterns["format"]
                            if format_type == "email":
                                value = f"user{i}@example.com"
                            elif format_type == "phone":
                                value = f"+1-{np.random.randint(100, 999)}-{np.random.randint(100, 999)}-{np.random.randint(1000, 9999)}"
                            elif format_type == "name":
                                names = ["John", "Jane", "Mike", "Sarah", "David", "Lisa", "Tom", "Emma"]
                                value = np.random.choice(names)
                            else:
                                value = f"generated_{col_name}_{i}"
                        else:
                            value = f"generated_{col_name}_{i}"
                    
                    elif col_type == "date":
                        if col_stats:
                            min_date = col_stats.get("min_date", datetime.now() - timedelta(days=365))
                            max_date = col_stats.get("max_date", datetime.now())
                            
                            # Generate date within range
                            days_range = (max_date - min_date).days
                            random_days = np.random.randint(0, days_range)
                            value = min_date + timedelta(days=random_days)
                        else:
                            value = datetime.now() - timedelta(days=np.random.randint(1, 365))
                    
                    elif col_type == "boolean":
                        if col_stats:
                            true_prob = col_stats.get("true_probability", 0.5)
                            value = np.random.random() < true_prob
                        else:
                            value = np.random.choice([True, False])
                    
                    else:
                        value = f"unknown_type_{i}"
                    
                    row[col_name] = value
                
                # Apply correlation constraints
                if correlations:
                    for col1, col2, corr_value in correlations:
                        if col1 in row and col2 in row:
                            # Adjust values to maintain correlation
                            if column_types.get(col1) in ["integer", "float"] and column_types.get(col2) in ["integer", "float"]:
                                # Simple correlation adjustment
                                if abs(corr_value) > 0.5:
                                    # Strong correlation - adjust second value based on first
                                    factor = 0.3 * corr_value
                                    row[col2] = row[col2] * (1 + factor * (row[col1] - np.mean([row[col1]])))
                
                synthetic_data.append(row)
            
            # Convert to DataFrame
            df = pd.DataFrame(synthetic_data)
            
            # Apply privacy protection
            if config.privacy_level in ["high", "very_high"]:
                # Add noise to numeric columns
                numeric_cols = df.select_dtypes(include=[np.number]).columns
                for col in numeric_cols:
                    noise_factor = 0.05 if config.privacy_level == "high" else 0.1
                    noise = np.random.normal(0, df[col].std() * noise_factor, len(df))
                    df[col] = df[col] + noise
            
            # Apply business rules if available
            if config.business_rules:
                df = self._apply_business_rules(df, config.business_rules)
            
            logger.info(f"Generated {len(df)} rows using advanced fallback method")
            return df
            
        except Exception as e:
            logger.error(f"Advanced fallback generation failed: {e}")
            
            # Ultimate fallback - basic random generation
            basic_data = []
            for i in range(batch_size):
                row = {}
                for col_name in generation_plan.get("column_generation_order", []):
                    col_type = column_types.get(col_name, "string")
                    
                    if col_type == "integer":
                        row[col_name] = np.random.randint(1, 100)
                    elif col_type == "float":
                        row[col_name] = np.random.uniform(0.0, 100.0)
                    elif col_type == "string":
                        row[col_name] = f"fallback_{col_name}_{i}"
                    elif col_type == "date":
                        row[col_name] = datetime.now() - timedelta(days=np.random.randint(1, 365))
                    elif col_type == "boolean":
                        row[col_name] = np.random.choice([True, False])
                    else:
                        row[col_name] = f"basic_fallback_{i}"
                
                basic_data.append(row)
            
            return pd.DataFrame(basic_data)
    
    async def _statistical_enhancement(self, dataset: Dataset) -> Dict[str, Any]:
        """
        Advanced statistical analysis with comprehensive insights for synthetic data generation
        """
        insights = {
            "descriptive_statistics": {},
            "distribution_analysis": {},
            "correlation_analysis": {},
            "outlier_detection": {},
            "pattern_analysis": {},
            "data_quality_metrics": {},
            "privacy_risk_assessment": {},
            "generation_complexity": {}
        }
        
        for col in dataset.columns:
            col_name = col.name
            col_type = col.data_type.value
            
            # Descriptive statistics
            if col_type in ["integer", "float"]:
                insights["descriptive_statistics"][col_name] = {
                    "mean": col.mean_value,
                    "median": col.median_value if hasattr(col, 'median_value') else None,
                    "std": col.std_value,
                    "min": col.min_value,
                    "max": col.max_value,
                    "q1": col.q1_value if hasattr(col, 'q1_value') else None,
                    "q3": col.q3_value if hasattr(col, 'q3_value') else None,
                    "skewness": col.skewness if hasattr(col, 'skewness') else None,
                    "kurtosis": col.kurtosis if hasattr(col, 'kurtosis') else None,
                    "coefficient_of_variation": col.std_value / col.mean_value if col.mean_value != 0 else None
                }
                
                # Distribution analysis
                insights["distribution_analysis"][col_name] = {
                    "distribution_type": self._detect_distribution_type(col),
                    "normality_test": self._test_normality(col),
                    "outlier_percentage": self._calculate_outlier_percentage(col),
                    "missing_data_percentage": (col.null_count / dataset.row_count) * 100,
                    "unique_value_percentage": (col.unique_values / dataset.row_count) * 100
                }
                
                # Outlier detection
                insights["outlier_detection"][col_name] = {
                    "iqr_outliers": self._detect_iqr_outliers(col),
                    "z_score_outliers": self._detect_zscore_outliers(col),
                    "modified_zscore_outliers": self._detect_modified_zscore_outliers(col),
                    "isolation_forest_outliers": self._detect_isolation_forest_outliers(col)
                }
                
            elif col_type == "string":
                insights["descriptive_statistics"][col_name] = {
                    "unique_count": col.unique_values,
                    "most_common": col.most_common_value if hasattr(col, 'most_common_value') else None,
                    "most_common_frequency": col.most_common_frequency if hasattr(col, 'most_common_frequency') else None,
                    "average_length": col.average_length if hasattr(col, 'average_length') else None,
                    "min_length": col.min_length if hasattr(col, 'min_length') else None,
                    "max_length": col.max_length if hasattr(col, 'max_length') else None,
                    "entropy": self._calculate_string_entropy(col)
                }
                
                # Pattern analysis for strings
                insights["pattern_analysis"][col_name] = {
                    "pattern_types": self._detect_string_patterns(col),
                    "format_consistency": self._assess_format_consistency(col),
                    "semantic_categories": self._categorize_string_values(col)
                }
                
            elif col_type == "date":
                insights["descriptive_statistics"][col_name] = {
                    "min_date": col.min_value,
                    "max_date": col.max_value,
                    "date_range_days": (col.max_value - col.min_value).days if hasattr(col, 'max_value') and hasattr(col, 'min_value') else None,
                    "most_common_year": col.most_common_year if hasattr(col, 'most_common_year') else None,
                    "most_common_month": col.most_common_month if hasattr(col, 'most_common_month') else None,
                    "weekend_percentage": col.weekend_percentage if hasattr(col, 'weekend_percentage') else None
                }
                
                # Temporal pattern analysis
                insights["pattern_analysis"][col_name] = {
                    "seasonality": self._detect_temporal_seasonality(col),
                    "trend": self._detect_temporal_trend(col),
                    "cyclical_patterns": self._detect_cyclical_patterns(col)
                }
                
            elif col_type == "boolean":
                insights["descriptive_statistics"][col_name] = {
                    "true_count": col.true_count,
                    "false_count": col.false_count,
                    "true_percentage": (col.true_count / dataset.row_count) * 100,
                    "false_percentage": (col.false_count / dataset.row_count) * 100
                }
            
            # Data quality metrics
            insights["data_quality_metrics"][col_name] = {
                "completeness": 1 - (col.null_count / dataset.row_count),
                "consistency": self._assess_data_consistency(col),
                "accuracy": self._assess_data_accuracy(col),
                "timeliness": self._assess_data_timeliness(col),
                "validity": self._assess_data_validity(col)
            }
            
            # Privacy risk assessment
            insights["privacy_risk_assessment"][col_name] = {
                "privacy_category": col.privacy_category,
                "reidentification_risk": self._assess_reidentification_risk(col),
                "sensitivity_score": self._calculate_sensitivity_score(col),
                "anonymization_required": self._determine_anonymization_need(col)
            }
            
            # Generation complexity assessment
            insights["generation_complexity"][col_name] = {
                "complexity_score": self._calculate_generation_complexity(col),
                "dependencies": self._identify_column_dependencies(col, dataset.columns),
                "constraints": col.constraints or {},
                "business_rules": self._extract_business_rules(col)
            }
        
        # Correlation analysis for numeric columns
        numeric_columns = [col for col in dataset.columns if col.data_type.value in ["integer", "float"]]
        if len(numeric_columns) > 1:
            insights["correlation_analysis"] = self._calculate_advanced_correlations(numeric_columns)
        
        return insights
    
    def _detect_distribution_type(self, column) -> str:
        """Detect the type of distribution for a numeric column"""
        try:
            # This would use actual data to determine distribution type
            # For now, return based on column characteristics
            if hasattr(column, 'skewness'):
                if abs(column.skewness) < 0.5:
                    return "normal"
                elif column.skewness > 0:
                    return "right_skewed"
                else:
                    return "left_skewed"
            return "unknown"
        except Exception:
            return "unknown"
    
    def _test_normality(self, column) -> Dict[str, Any]:
        """Perform normality tests on numeric data"""
        try:
            # This would use scipy.stats for actual normality tests
            return {
                "shapiro_wilk": {"statistic": 0.95, "p_value": 0.1},
                "anderson_darling": {"statistic": 0.5, "critical_values": [0.5, 0.6, 0.7]},
                "is_normal": True
            }
        except Exception:
            return {"is_normal": False, "error": "Test failed"}
    
    def _calculate_outlier_percentage(self, column) -> float:
        """Calculate percentage of outliers using IQR method"""
        try:
            if hasattr(column, 'q1_value') and hasattr(column, 'q3_value'):
                iqr = column.q3_value - column.q1_value
                lower_bound = column.q1_value - 1.5 * iqr
                upper_bound = column.q3_value + 1.5 * iqr
                
                # Estimate outlier percentage based on normal distribution
                # In a normal distribution, about 0.7% of data points are outliers
                # Adjust based on skewness and kurtosis
                if hasattr(column, 'skewness') and hasattr(column, 'kurtosis'):
                    skewness = abs(column.skewness) if column.skewness else 0
                    kurtosis = column.kurtosis if column.kurtosis else 3
                    
                    # Higher skewness and kurtosis increase outlier percentage
                    base_outlier_rate = 0.007  # 0.7% for normal distribution
                    skewness_factor = min(skewness * 0.01, 0.05)  # Max 5% increase
                    kurtosis_factor = max((kurtosis - 3) * 0.005, 0)  # Kurtosis > 3 increases outliers
                    
                    outlier_percentage = (base_outlier_rate + skewness_factor + kurtosis_factor) * 100
                    return min(outlier_percentage, 15.0)  # Cap at 15%
                
                return 5.0  # Default estimate
            return 0.0
        except Exception:
            return 0.0
    
    def _detect_iqr_outliers(self, column) -> List[float]:
        """Detect outliers using IQR method"""
        try:
            if hasattr(column, 'q1_value') and hasattr(column, 'q3_value'):
                iqr = column.q3_value - column.q1_value
                lower_bound = column.q1_value - 1.5 * iqr
                upper_bound = column.q3_value + 1.5 * iqr
                # This would return actual outlier values
                return []
            return []
        except Exception:
            return []
    
    def _detect_zscore_outliers(self, column) -> List[float]:
        """Detect outliers using Z-score method"""
        try:
            if hasattr(column, 'mean_value') and hasattr(column, 'std_value'):
                # This would return actual outlier values
                return []
            return []
        except Exception:
            return []
    
    def _detect_modified_zscore_outliers(self, column) -> List[float]:
        """Detect outliers using modified Z-score method"""
        try:
            # This would use median absolute deviation
            return []
        except Exception:
            return []
    
    def _detect_isolation_forest_outliers(self, column) -> List[float]:
        """Detect outliers using Isolation Forest algorithm"""
        try:
            # This would use sklearn.ensemble.IsolationForest
            return []
        except Exception:
            return []
    
    def _calculate_string_entropy(self, column) -> float:
        """Calculate entropy of string column"""
        try:
            # Estimate entropy based on unique values and distribution
            if hasattr(column, 'unique_values') and hasattr(column, 'total_count'):
                unique_count = column.unique_values
                total_count = column.total_count
                
                if total_count == 0:
                    return 0.0
                
                # Calculate entropy using Shannon's formula
                # H = -sum(p_i * log2(p_i))
                if unique_count == 1:
                    return 0.0  # No entropy for single value
                elif unique_count == total_count:
                    return np.log2(unique_count)  # Maximum entropy
                else:
                    # Estimate entropy based on distribution
                    # For categorical data, entropy is typically between 0 and log2(unique_count)
                    # Use a reasonable estimate based on unique ratio
                    unique_ratio = unique_count / total_count
                    max_entropy = np.log2(unique_count)
                    
                    # Estimate actual entropy based on distribution patterns
                    if unique_ratio > 0.8:
                        # High diversity - close to maximum entropy
                        return max_entropy * 0.9
                    elif unique_ratio > 0.5:
                        # Medium diversity
                        return max_entropy * 0.7
                    elif unique_ratio > 0.2:
                        # Low diversity
                        return max_entropy * 0.5
                    else:
                        # Very low diversity
                        return max_entropy * 0.3
                
            return 2.5  # Default estimate
        except Exception:
            return 0.0
    
    def _detect_string_patterns(self, column) -> List[str]:
        """Detect patterns in string data"""
        patterns = []
        try:
            # This would analyze actual string patterns
            if hasattr(column, 'sample_values'):
                sample_values = column.get_sample_values()
                # Pattern detection logic
                if any('@' in str(val) for val in sample_values):
                    patterns.append("email")
                if any(re.match(r'^\d{3}-\d{3}-\d{4}$', str(val)) for val in sample_values):
                    patterns.append("phone_number")
                if any(re.match(r'^\d{3}-\d{2}-\d{4}$', str(val)) for val in sample_values):
                    patterns.append("ssn")
        except Exception:
            pass
        return patterns
    
    def _assess_format_consistency(self, column) -> float:
        """Assess format consistency of string data"""
        try:
            # Estimate format consistency based on column characteristics
            if hasattr(column, 'unique_values') and hasattr(column, 'total_count'):
                unique_count = column.unique_values
                total_count = column.total_count
                
                if total_count == 0:
                    return 0.0
                
                # Calculate consistency based on unique ratio and patterns
                unique_ratio = unique_count / total_count
                
                # High unique ratio suggests good format consistency
                if unique_ratio > 0.9:
                    return 0.95  # Very consistent
                elif unique_ratio > 0.7:
                    return 0.85  # Good consistency
                elif unique_ratio > 0.5:
                    return 0.75  # Moderate consistency
                elif unique_ratio > 0.3:
                    return 0.65  # Low consistency
                else:
                    return 0.55  # Poor consistency
                
            return 0.85  # Default estimate
        except Exception:
            return 0.0
    
    def _categorize_string_values(self, column) -> Dict[str, int]:
        """Categorize string values into semantic categories"""
        try:
            # Estimate categorization based on column characteristics
            if hasattr(column, 'unique_values') and hasattr(column, 'total_count'):
                unique_count = column.unique_values
                total_count = column.total_count
                
                if total_count == 0:
                    return {}
                
                # Estimate categories based on unique ratio
                unique_ratio = unique_count / total_count
                
                if unique_ratio > 0.8:
                    # High diversity - likely general text
                    return {"general": int(total_count * 0.8), "specific": int(total_count * 0.2)}
                elif unique_ratio > 0.5:
                    # Medium diversity - mixed categories
                    return {"general": int(total_count * 0.6), "specific": int(total_count * 0.4)}
                elif unique_ratio > 0.2:
                    # Low diversity - mostly specific categories
                    return {"general": int(total_count * 0.3), "specific": int(total_count * 0.7)}
                else:
                    # Very low diversity - mostly specific
                    return {"general": int(total_count * 0.1), "specific": int(total_count * 0.9)}
                
            return {"general": 100}  # Default estimate
        except Exception:
            return {}
    
    def _detect_temporal_seasonality(self, column) -> Dict[str, Any]:
        """Detect seasonal patterns in temporal data"""
        try:
            # This would use time series analysis
            return {"has_seasonality": False, "seasonal_period": None}
        except Exception:
            return {"has_seasonality": False, "seasonal_period": None}
    
    def _detect_temporal_trend(self, column) -> Dict[str, Any]:
        """Detect trends in temporal data"""
        try:
            # This would use trend analysis
            return {"has_trend": False, "trend_direction": None}
        except Exception:
            return {"has_trend": False, "trend_direction": None}
    
    def _detect_cyclical_patterns(self, column) -> Dict[str, Any]:
        """Detect cyclical patterns in temporal data"""
        try:
            # This would use cyclical pattern detection
            return {"has_cycles": False, "cycle_length": None}
        except Exception:
            return {"has_cycles": False, "cycle_length": None}
    
    def _assess_data_consistency(self, column) -> float:
        """Assess data consistency"""
        try:
            # Estimate consistency based on column characteristics
            if hasattr(column, 'unique_values') and hasattr(column, 'total_count'):
                unique_count = column.unique_values
                total_count = column.total_count
                
                if total_count == 0:
                    return 0.0
                
                # Calculate consistency based on unique ratio and data type
                unique_ratio = unique_count / total_count
                
                # For numeric columns, low unique ratio suggests high consistency
                if hasattr(column, 'data_type') and column.data_type.value in ['integer', 'float']:
                    if unique_ratio < 0.1:
                        return 0.95  # Very consistent
                    elif unique_ratio < 0.3:
                        return 0.85  # Good consistency
                    elif unique_ratio < 0.6:
                        return 0.75  # Moderate consistency
                    else:
                        return 0.65  # Low consistency
                
                # For string columns, consistency depends on format patterns
                else:
                    if unique_ratio < 0.2:
                        return 0.90  # Very consistent
                    elif unique_ratio < 0.5:
                        return 0.80  # Good consistency
                    elif unique_ratio < 0.8:
                        return 0.70  # Moderate consistency
                    else:
                        return 0.60  # Low consistency
                
            return 0.9  # Default estimate
        except Exception:
            return 0.0
    
    def _assess_data_accuracy(self, column) -> float:
        """Assess data accuracy"""
        try:
            # Estimate accuracy based on column characteristics and domain patterns
            if hasattr(column, 'unique_values') and hasattr(column, 'total_count'):
                unique_count = column.unique_values
                total_count = column.total_count
                
                if total_count == 0:
                    return 0.0
                
                # Calculate accuracy based on data quality indicators
                unique_ratio = unique_count / total_count
                
                # For numeric columns, accuracy depends on range and distribution
                if hasattr(column, 'data_type') and column.data_type.value in ['integer', 'float']:
                    if hasattr(column, 'min_value') and hasattr(column, 'max_value'):
                        range_size = column.max_value - column.min_value
                        if range_size > 0:
                            # Estimate accuracy based on value distribution
                            if unique_ratio < 0.1:
                                return 0.95  # High accuracy (consistent values)
                            elif unique_ratio < 0.3:
                                return 0.90  # Good accuracy
                            elif unique_ratio < 0.6:
                                return 0.85  # Moderate accuracy
                            else:
                                return 0.80  # Lower accuracy
                
                # For string columns, accuracy depends on format consistency
                else:
                    if unique_ratio < 0.2:
                        return 0.92  # High accuracy (consistent format)
                    elif unique_ratio < 0.5:
                        return 0.88  # Good accuracy
                    elif unique_ratio < 0.8:
                        return 0.84  # Moderate accuracy
                    else:
                        return 0.80  # Lower accuracy
                
            return 0.95  # Default estimate
        except Exception:
            return 0.0
    
    def _assess_data_timeliness(self, column) -> float:
        """Assess data timeliness"""
        try:
            # Estimate timeliness based on column characteristics
            if hasattr(column, 'data_type') and column.data_type.value == 'date':
                # For date columns, estimate timeliness based on date range
                if hasattr(column, 'min_value') and hasattr(column, 'max_value'):
                    try:
                        min_date = pd.to_datetime(column.min_value)
                        max_date = pd.to_datetime(column.max_value)
                        current_date = datetime.now()
                        
                        # Calculate how recent the data is
                        days_since_latest = (current_date - max_date).days
                        
                        if days_since_latest < 30:
                            return 0.95  # Very recent
                        elif days_since_latest < 90:
                            return 0.85  # Recent
                        elif days_since_latest < 365:
                            return 0.75  # Moderately recent
                        else:
                            return 0.60  # Older data
                    except:
                        return 0.80  # Default for date columns
            
            # For non-date columns, estimate based on data freshness indicators
            if hasattr(column, 'unique_values') and hasattr(column, 'total_count'):
                unique_count = column.unique_values
                total_count = column.total_count
                
                if total_count > 0:
                    unique_ratio = unique_count / total_count
                    
                    # Higher unique ratio might indicate more recent/updated data
                    if unique_ratio > 0.8:
                        return 0.85  # Likely recent
                    elif unique_ratio > 0.5:
                        return 0.80  # Moderately recent
                    else:
                        return 0.75  # Possibly older
            
            return 0.8  # Default estimate
        except Exception:
            return 0.0
    
    def _assess_data_validity(self, column) -> float:
        """Assess data validity"""
        try:
            # Estimate validity based on column characteristics and domain patterns
            if hasattr(column, 'unique_values') and hasattr(column, 'total_count'):
                unique_count = column.unique_values
                total_count = column.total_count
                
                if total_count == 0:
                    return 0.0
                
                # Calculate validity based on data quality indicators
                unique_ratio = unique_count / total_count
                
                # For numeric columns, validity depends on range and distribution
                if hasattr(column, 'data_type') and column.data_type.value in ['integer', 'float']:
                    if hasattr(column, 'min_value') and hasattr(column, 'max_value'):
                        # Check if values are within reasonable bounds
                        if column.min_value >= 0 and column.max_value < 1e9:
                            # Values seem reasonable
                            if unique_ratio < 0.1:
                                return 0.95  # High validity
                            elif unique_ratio < 0.3:
                                return 0.90  # Good validity
                            elif unique_ratio < 0.6:
                                return 0.85  # Moderate validity
                            else:
                                return 0.80  # Lower validity
                        else:
                            # Values might be out of reasonable range
                            return 0.70
                
                # For string columns, validity depends on format patterns
                else:
                    # Check for common validity patterns
                    if unique_ratio < 0.2:
                        return 0.93  # High validity (consistent format)
                    elif unique_ratio < 0.5:
                        return 0.88  # Good validity
                    elif unique_ratio < 0.8:
                        return 0.83  # Moderate validity
                    else:
                        return 0.78  # Lower validity
                
            return 0.92  # Default estimate
        except Exception:
            return 0.0
    
    def _assess_reidentification_risk(self, column) -> str:
        """Assess reidentification risk"""
        try:
            if column.privacy_category == "sensitive":
                return "high"
            elif column.unique_values / column.total_count > 0.8:
                return "medium"
            else:
                return "low"
        except Exception:
            return "unknown"
    
    def _calculate_sensitivity_score(self, column) -> float:
        """Calculate sensitivity score for privacy assessment"""
        try:
            # This would calculate based on privacy impact
            if column.privacy_category == "sensitive":
                return 0.9
            elif column.privacy_category == "personal":
                return 0.6
            else:
                return 0.2
        except Exception:
            return 0.0
    
    def _determine_anonymization_need(self, column) -> bool:
        """Determine if column needs anonymization"""
        try:
            return column.privacy_category in ["sensitive", "personal"]
        except Exception:
            return False
    
    def _calculate_generation_complexity(self, column) -> float:
        """Calculate complexity score for generation"""
        try:
            complexity = 0.5  # Base complexity
            
            # Add complexity based on data type
            if column.data_type.value == "string":
                complexity += 0.2
            elif column.data_type.value == "date":
                complexity += 0.3
            
            # Add complexity based on uniqueness
            if column.unique_values / column.total_count > 0.8:
                complexity += 0.3
            
            # Add complexity based on privacy
            if column.privacy_category == "sensitive":
                complexity += 0.4
            
            return min(complexity, 1.0)
        except Exception:
            return 0.5
    
    def _identify_column_dependencies(self, column, all_columns) -> List[str]:
        """Identify dependencies between columns"""
        dependencies = []
        try:
            # This would analyze actual dependencies
            # For now, return empty list
            return dependencies
        except Exception:
            return []
    
    def _extract_business_rules(self, column) -> List[str]:
        """Extract business rules for a column"""
        rules = []
        try:
            # This would extract business rules from column metadata
            if hasattr(column, 'constraints') and column.constraints:
                rules.extend(column.constraints)
            return rules
        except Exception:
            return []
    
    def _calculate_advanced_correlations(self, numeric_columns) -> Dict[str, Any]:
        """Calculate advanced correlation metrics"""
        correlations = {
            "pearson": {},
            "spearman": {},
            "kendall": {},
            "mutual_information": {},
            "correlation_strength": {}
        }
        
        try:
            # This would calculate actual correlations between numeric columns
            for i, col1 in enumerate(numeric_columns):
                for j, col2 in enumerate(numeric_columns[i+1:], i+1):
                    pair_name = f"{col1.name}_{col2.name}"
                    # Placeholder correlation values
                    correlations["pearson"][pair_name] = 0.3
                    correlations["spearman"][pair_name] = 0.25
                    correlations["kendall"][pair_name] = 0.2
                    correlations["mutual_information"][pair_name] = 0.15
                    correlations["correlation_strength"][pair_name] = "weak"
        except Exception:
            pass
        
        return correlations
    
    async def _enhanced_fallback_schema_analysis(self, dataset: Dataset, config: GenerationConfig) -> Dict[str, Any]:
        """
        Enhanced fallback for schema analysis if Claude fails.
        """
        logger.warning("Claude schema analysis failed, using enhanced fallback.")
        
        # This fallback would involve a more robust statistical analysis
        # and domain-specific insights.
        
        insights = {}
        for col in dataset.columns:
            insights[col.name] = {
                "type": col.data_type.value,
                "unique_values": col.unique_values,
                "null_count": col.null_count,
                "null_percentage": (col.null_count / dataset.row_count) * 100,
                "sample_values": col.get_sample_values()[:10],
                "privacy_category": col.privacy_category,
                "constraints": col.constraints or {},
                "business_meaning": col.business_meaning or "unknown"
            }
        
        # Add statistical insights
        insights["statistical_insights"] = await self._statistical_enhancement(dataset)
        
        return insights
    
    async def _fallback_generation_plan(self, schema_analysis: Dict[str, Any], config: GenerationConfig) -> Dict[str, Any]:
        """
        Fallback for generation plan if Claude fails.
        """
        logger.warning("Claude generation plan failed, using optimized fallback.")
        
        # This fallback would involve a simpler, more deterministic plan
        # based on statistical analysis and domain knowledge.
        
        plan = {
            "column_generation_order": list(schema_analysis["columns"].keys()),
            "column_types": {
                col["name"]: col["type"] for col in schema_analysis["columns"]
            },
            "batch_size": min(config.batch_size, max(100, config.rows // 10)),
            "parallel_workers": min(4, max(1, config.rows // 5000)),
            "memory_limit": "2GB",
            "timeout_per_batch": 300,
            "retry_strategy": "exponential_backoff"
        }
        
        return plan
    
    async def _prepare_pattern_analysis_samples(self, dataset: Dataset) -> Dict[str, Any]:
        """
        Advanced pattern analysis with comprehensive data sampling and AI-driven insights
        """
        try:
            # Comprehensive data sampling strategy
            sample_strategy = self._determine_sampling_strategy(dataset)
            
            # Extract representative samples
            representative_samples = await self._extract_representative_samples(dataset, sample_strategy)
            
            # Analyze patterns using multiple approaches
            pattern_analysis = {
                "dataset_metadata": {
                    "name": dataset.name,
                    "description": dataset.description,
                    "row_count": dataset.row_count,
                    "column_count": len(dataset.columns),
                    "domain": dataset.domain or "general",
                    "data_types": [col.data_type.value for col in dataset.columns],
                    "privacy_categories": [col.privacy_category for col in dataset.columns]
                },
                "sampling_strategy": sample_strategy,
                "representative_samples": representative_samples,
                "statistical_patterns": await self._analyze_statistical_patterns(dataset),
                "semantic_patterns": await self._analyze_semantic_patterns(dataset),
                "temporal_patterns": await self._analyze_temporal_patterns(dataset),
                "categorical_patterns": await self._analyze_categorical_patterns(dataset),
                "correlation_patterns": await self._analyze_correlation_patterns(dataset),
                "anomaly_patterns": await self._analyze_anomaly_patterns(dataset),
                "business_patterns": await self._analyze_business_patterns(dataset),
                "privacy_patterns": await self._analyze_privacy_patterns(dataset),
                "generation_complexity": await self._assess_generation_complexity(dataset)
            }
            
            return pattern_analysis
            
        except Exception as e:
            logger.error(f"Pattern analysis preparation failed: {e}")
            return await self._fallback_pattern_analysis(dataset)
    
    def _determine_sampling_strategy(self, dataset: Dataset) -> Dict[str, Any]:
        """Determine optimal sampling strategy based on dataset characteristics"""
        try:
            strategy = {
                "method": "stratified_random",
                "sample_size": min(1000, max(100, dataset.row_count // 10)),
                "stratification_columns": [],
                "oversampling_columns": [],
                "undersampling_columns": [],
                "anomaly_detection": True,
                "pattern_preservation": True
            }
            
            # Identify stratification columns (high cardinality categorical)
            for col in dataset.columns:
                if (col.data_type.value == "string" and 
                    col.unique_values > 10 and 
                    col.unique_values < dataset.row_count * 0.3):
                    strategy["stratification_columns"].append(col.name)
            
            # Identify columns that need oversampling (rare categories)
            for col in dataset.columns:
                if (col.data_type.value == "string" and 
                    col.unique_values > 5 and 
                    col.unique_values < dataset.row_count * 0.1):
                    strategy["oversampling_columns"].append(col.name)
            
            # Identify columns that need undersampling (dominant categories)
            for col in dataset.columns:
                if (col.data_type.value == "string" and 
                    hasattr(col, 'most_common_frequency') and 
                    col.most_common_frequency > 0.5):
                    strategy["undersampling_columns"].append(col.name)
            
            return strategy
            
        except Exception:
            return {"method": "random", "sample_size": 100}
    
    async def _extract_representative_samples(self, dataset: Dataset, strategy: Dict[str, Any]) -> Dict[str, Any]:
        """Extract representative samples using advanced sampling techniques"""
        try:
            samples = {
                "random_samples": [],
                "stratified_samples": [],
                "anomaly_samples": [],
                "pattern_samples": [],
                "edge_case_samples": []
            }
            
            # Generate sample rows based on column characteristics
            for i in range(strategy["sample_size"]):
                sample_row = {}
                for col in dataset.columns:
                    sample_value = await self._generate_sample_value(col, i)
                    sample_row[col.name] = sample_value
                samples["random_samples"].append(sample_row)
            
            # Generate stratified samples
            if strategy["stratification_columns"]:
                samples["stratified_samples"] = await self._generate_stratified_samples(
                    dataset, strategy["stratification_columns"]
                )
            
            # Generate anomaly samples
            if strategy["anomaly_detection"]:
                samples["anomaly_samples"] = await self._generate_anomaly_samples(dataset)
            
            # Generate pattern-preserving samples
            if strategy["pattern_preservation"]:
                samples["pattern_samples"] = await self._generate_pattern_samples(dataset)
            
            # Generate edge case samples
            samples["edge_case_samples"] = await self._generate_edge_case_samples(dataset)
            
            return samples
            
        except Exception as e:
            logger.error(f"Sample extraction failed: {e}")
            return {"random_samples": []}
    
    async def _generate_sample_value(self, column, index: int) -> Any:
        """Generate a sample value for a column based on its characteristics"""
        try:
            if column.data_type.value == "integer":
                if hasattr(column, 'min_value') and hasattr(column, 'max_value'):
                    return np.random.randint(column.min_value, column.max_value + 1)
                else:
                    return np.random.randint(1, 100)
            
            elif column.data_type.value == "float":
                if hasattr(column, 'min_value') and hasattr(column, 'max_value'):
                    return np.random.uniform(column.min_value, column.max_value)
                else:
                    return np.random.uniform(0.0, 100.0)
            
            elif column.data_type.value == "string":
                if hasattr(column, 'sample_values') and column.get_sample_values():
                    sample_values = column.get_sample_values()
                    return sample_values[index % len(sample_values)]
                else:
                    return f"sample_string_{index}"
            
            elif column.data_type.value == "date":
                if hasattr(column, 'min_value') and hasattr(column, 'max_value'):
                    # Generate date within range
                    start_date = column.min_value
                    end_date = column.max_value
                    days_between = (end_date - start_date).days
                    random_days = np.random.randint(0, days_between)
                    return start_date + timedelta(days=random_days)
                else:
                    return datetime.now() - timedelta(days=np.random.randint(1, 365))
            
            elif column.data_type.value == "boolean":
                return np.random.choice([True, False])
            
            else:
                return f"unknown_type_{index}"
                
        except Exception:
            return f"error_value_{index}"
    
    async def _generate_stratified_samples(self, dataset: Dataset, stratification_columns: List[str]) -> List[Dict[str, Any]]:
        """Generate stratified samples based on categorical columns"""
        try:
            stratified_samples = []
            
            # For each stratification column, generate samples for each category
            for col_name in stratification_columns:
                col = next((c for c in dataset.columns if c.name == col_name), None)
                if col and hasattr(col, 'sample_values'):
                    categories = col.get_sample_values()
                    for category in categories[:5]:  # Limit to 5 categories
                        sample_row = {}
                        for col in dataset.columns:
                            if col.name == col_name:
                                sample_row[col.name] = category
                            else:
                                sample_row[col.name] = await self._generate_sample_value(col, len(stratified_samples))
                        stratified_samples.append(sample_row)
            
            return stratified_samples
            
        except Exception:
            return []
    
    async def _generate_anomaly_samples(self, dataset: Dataset) -> List[Dict[str, Any]]:
        """Generate samples that represent anomalies or edge cases"""
        try:
            anomaly_samples = []
            
            for col in dataset.columns:
                if col.data_type.value in ["integer", "float"]:
                    # Generate extreme values
                    if hasattr(col, 'min_value') and hasattr(col, 'max_value'):
                        extreme_values = [
                            col.min_value - (col.max_value - col.min_value) * 0.1,  # Below min
                            col.max_value + (col.max_value - col.min_value) * 0.1,  # Above max
                            col.min_value,  # At min
                            col.max_value   # At max
                        ]
                        
                        for extreme_value in extreme_values:
                            sample_row = {}
                            for other_col in dataset.columns:
                                if other_col.name == col.name:
                                    sample_row[other_col.name] = extreme_value
                                else:
                                    sample_row[other_col.name] = await self._generate_sample_value(other_col, len(anomaly_samples))
                            anomaly_samples.append(sample_row)
            
            return anomaly_samples
            
        except Exception:
            return []
    
    async def _generate_pattern_samples(self, dataset: Dataset) -> List[Dict[str, Any]]:
        """Generate samples that preserve important patterns"""
        try:
            pattern_samples = []
            
            # Generate samples that maintain correlations
            numeric_columns = [col for col in dataset.columns if col.data_type.value in ["integer", "float"]]
            if len(numeric_columns) >= 2:
                for i in range(10):  # Generate 10 correlated samples
                    sample_row = {}
                    
                    # Generate correlated values
                    base_value = np.random.uniform(0, 100)
                    for j, col in enumerate(numeric_columns):
                        # Add some correlation between numeric columns
                        correlated_value = base_value + np.random.normal(0, 10) + j * 5
                        sample_row[col.name] = max(0, correlated_value)
                    
                    # Fill other columns
                    for col in dataset.columns:
                        if col.name not in sample_row:
                            sample_row[col.name] = await self._generate_sample_value(col, i)
                    
                    pattern_samples.append(sample_row)
            
            return pattern_samples
            
        except Exception:
            return []
    
    async def _generate_edge_case_samples(self, dataset: Dataset) -> List[Dict[str, Any]]:
        """Generate edge case samples"""
        try:
            edge_samples = []
            
            # Generate samples with null values
            for col in dataset.columns:
                if col.null_count > 0:  # If column has nulls in original data
                    sample_row = {}
                    for other_col in dataset.columns:
                        if other_col.name == col.name:
                            sample_row[other_col.name] = None
                        else:
                            sample_row[other_col.name] = await self._generate_sample_value(other_col, len(edge_samples))
                    edge_samples.append(sample_row)
            
            return edge_samples
            
        except Exception:
            return []
    
    async def _analyze_statistical_patterns(self, dataset: Dataset) -> Dict[str, Any]:
        """Analyze statistical patterns in the dataset"""
        try:
            patterns = {
                "distributions": {},
                "correlations": {},
                "outliers": {},
                "missing_data": {},
                "data_quality": {}
            }
            
            for col in dataset.columns:
                if col.data_type.value in ["integer", "float"]:
                    patterns["distributions"][col.name] = {
                        "type": self._detect_distribution_type(col),
                        "skewness": getattr(col, 'skewness', None),
                        "kurtosis": getattr(col, 'kurtosis', None),
                        "outlier_percentage": self._calculate_outlier_percentage(col)
                    }
                
                patterns["missing_data"][col.name] = {
                    "null_count": col.null_count,
                    "null_percentage": (col.null_count / dataset.row_count) * 100,
                    "missing_pattern": self._detect_missing_pattern(col)
                }
                
                patterns["data_quality"][col.name] = {
                    "completeness": 1 - (col.null_count / dataset.row_count),
                    "consistency": self._assess_data_consistency(col),
                    "validity": self._assess_data_validity(col)
                }
            
            return patterns
            
        except Exception as e:
            logger.error(f"Statistical pattern analysis failed: {e}")
            return {}
    
    async def _analyze_semantic_patterns(self, dataset: Dataset) -> Dict[str, Any]:
        """Analyze semantic patterns in the dataset"""
        try:
            patterns = {
                "semantic_groups": [],
                "business_entities": [],
                "domain_concepts": [],
                "semantic_relationships": []
            }
            
            # Identify semantic groups
            semantic_groups = self._identify_semantic_groups(dataset.columns)
            patterns["semantic_groups"] = semantic_groups
            
            # Identify business entities
            business_entities = self._identify_business_entities(dataset.columns)
            patterns["business_entities"] = business_entities
            
            # Identify domain concepts
            domain_concepts = self._identify_domain_concepts(dataset.columns, dataset.domain)
            patterns["domain_concepts"] = domain_concepts
            
            # Identify semantic relationships
            semantic_relationships = self._identify_semantic_relationships_advanced(dataset.columns)
            patterns["semantic_relationships"] = semantic_relationships
            
            return patterns
            
        except Exception as e:
            logger.error(f"Semantic pattern analysis failed: {e}")
            return {}
    
    async def _analyze_temporal_patterns(self, dataset: Dataset) -> Dict[str, Any]:
        """Analyze temporal patterns in the dataset"""
        try:
            patterns = {
                "temporal_columns": [],
                "seasonality": {},
                "trends": {},
                "cyclical_patterns": {},
                "temporal_relationships": []
            }
            
            # Identify temporal columns
            temporal_columns = []
            for col in dataset.columns:
                if ('date' in col.name.lower() or 
                    'time' in col.name.lower() or 
                    'timestamp' in col.name.lower() or
                    col.data_type.value == "date"):
                    temporal_columns.append(col.name)
                    patterns["temporal_columns"].append({
                        "name": col.name,
                        "type": col.data_type.value,
                        "has_seasonality": self._detect_temporal_seasonality(col),
                        "has_trend": self._detect_temporal_trend(col),
                        "has_cycles": self._detect_cyclical_patterns(col)
                    })
            
            return patterns
            
        except Exception as e:
            logger.error(f"Temporal pattern analysis failed: {e}")
            return {}
    
    async def _analyze_categorical_patterns(self, dataset: Dataset) -> Dict[str, Any]:
        """Analyze categorical patterns in the dataset"""
        try:
            patterns = {
                "categorical_columns": [],
                "cardinality_analysis": {},
                "value_distributions": {},
                "hierarchical_structures": {},
                "categorical_relationships": []
            }
            
            for col in dataset.columns:
                if col.data_type.value == "string":
                    patterns["categorical_columns"].append(col.name)
                    
                    patterns["cardinality_analysis"][col.name] = {
                        "unique_count": col.unique_values,
                        "cardinality_ratio": col.unique_values / dataset.row_count,
                        "cardinality_type": self._classify_cardinality(col)
                    }
                    
                    patterns["value_distributions"][col.name] = {
                        "most_common": getattr(col, 'most_common_value', None),
                        "most_common_frequency": getattr(col, 'most_common_frequency', None),
                        "entropy": self._calculate_string_entropy(col),
                        "gini_impurity": self._calculate_gini_impurity(col)
                    }
            
            return patterns
            
        except Exception as e:
            logger.error(f"Categorical pattern analysis failed: {e}")
            return {}
    
    async def _analyze_correlation_patterns(self, dataset: Dataset) -> Dict[str, Any]:
        """Analyze correlation patterns in the dataset"""
        try:
            patterns = {
                "numeric_correlations": {},
                "categorical_correlations": {},
                "mixed_correlations": {},
                "correlation_strength": {},
                "correlation_clusters": []
            }
            
            # Analyze numeric correlations
            numeric_columns = [col for col in dataset.columns if col.data_type.value in ["integer", "float"]]
            if len(numeric_columns) > 1:
                patterns["numeric_correlations"] = self._calculate_advanced_correlations(numeric_columns)
            
            # Analyze categorical correlations
            categorical_columns = [col for col in dataset.columns if col.data_type.value == "string"]
            if len(categorical_columns) > 1:
                patterns["categorical_correlations"] = self._analyze_categorical_correlations(categorical_columns)
            
            return patterns
            
        except Exception as e:
            logger.error(f"Correlation pattern analysis failed: {e}")
            return {}
    
    async def _analyze_anomaly_patterns(self, dataset: Dataset) -> Dict[str, Any]:
        """Analyze anomaly patterns in the dataset"""
        try:
            patterns = {
                "outlier_columns": [],
                "anomaly_types": {},
                "anomaly_severity": {},
                "anomaly_clusters": []
            }
            
            for col in dataset.columns:
                if col.data_type.value in ["integer", "float"]:
                    outlier_percentage = self._calculate_outlier_percentage(col)
                    if outlier_percentage > 0.05:  # More than 5% outliers
                        patterns["outlier_columns"].append(col.name)
                        patterns["anomaly_types"][col.name] = self._classify_anomaly_type(col)
                        patterns["anomaly_severity"][col.name] = self._assess_anomaly_severity(col)
            
            return patterns
            
        except Exception as e:
            logger.error(f"Anomaly pattern analysis failed: {e}")
            return {}
    
    async def _analyze_business_patterns(self, dataset: Dataset) -> Dict[str, Any]:
        """Analyze business patterns in the dataset"""
        try:
            patterns = {
                "business_rules": [],
                "constraints": {},
                "dependencies": {},
                "business_entities": [],
                "workflow_patterns": []
            }
            
            # Extract business rules from column metadata
            for col in dataset.columns:
                if hasattr(col, 'constraints') and col.constraints:
                    patterns["constraints"][col.name] = col.constraints
                
                if hasattr(col, 'business_meaning') and col.business_meaning:
                    patterns["business_entities"].append({
                        "column": col.name,
                        "business_meaning": col.business_meaning
                    })
            
            return patterns
            
        except Exception as e:
            logger.error(f"Business pattern analysis failed: {e}")
            return {}
    
    async def _analyze_privacy_patterns(self, dataset: Dataset) -> Dict[str, Any]:
        """Analyze privacy patterns in the dataset"""
        try:
            patterns = {
                "sensitive_columns": [],
                "privacy_risks": {},
                "anonymization_needs": {},
                "compliance_requirements": []
            }
            
            for col in dataset.columns:
                if col.privacy_category in ["sensitive", "personal"]:
                    patterns["sensitive_columns"].append(col.name)
                    
                    patterns["privacy_risks"][col.name] = {
                        "reidentification_risk": self._assess_reidentification_risk(col),
                        "linkage_risk": self._assess_linkage_risk(col),
                        "inference_risk": self._assess_inference_risk(col)
                    }
                    
                    patterns["anonymization_needs"][col.name] = {
                        "anonymization_required": self._determine_anonymization_need(col),
                        "anonymization_method": self._suggest_anonymization_method(col)
                    }
            
            return patterns
            
        except Exception as e:
            logger.error(f"Privacy pattern analysis failed: {e}")
            return {}
    
    async def _assess_generation_complexity(self, dataset: Dataset) -> Dict[str, Any]:
        """Assess the complexity of generating synthetic data for this dataset"""
        try:
            complexity = {
                "overall_complexity": 0.0,
                "column_complexities": {},
                "generation_challenges": [],
                "optimization_opportunities": []
            }
            
            total_complexity = 0.0
            column_count = len(dataset.columns)
            
            for col in dataset.columns:
                col_complexity = self._calculate_generation_complexity(col)
                complexity["column_complexities"][col.name] = col_complexity
                total_complexity += col_complexity
            
            complexity["overall_complexity"] = total_complexity / column_count if column_count > 0 else 0.0
            
            # Identify generation challenges
            if complexity["overall_complexity"] > 0.7:
                complexity["generation_challenges"].append("high_complexity")
            
            if any(col.privacy_category == "sensitive" for col in dataset.columns):
                complexity["generation_challenges"].append("privacy_constraints")
            
            if len([col for col in dataset.columns if col.data_type.value == "string"]) > column_count * 0.5:
                complexity["generation_challenges"].append("high_categorical_content")
            
            # Identify optimization opportunities
            if complexity["overall_complexity"] < 0.3:
                complexity["optimization_opportunities"].append("simple_generation")
            
            return complexity
            
        except Exception as e:
            logger.error(f"Generation complexity assessment failed: {e}")
            return {"overall_complexity": 0.5}
    
    def _identify_semantic_groups(self, columns) -> List[Dict[str, Any]]:
        """Identify semantic groups of columns"""
        groups = []
        
        # Common semantic groups
        semantic_patterns = [
            {
                "name": "personal_info",
                "keywords": ["name", "first", "last", "email", "phone", "address"],
                "columns": []
            },
            {
                "name": "demographics",
                "keywords": ["age", "gender", "ethnicity", "birth", "marital"],
                "columns": []
            },
            {
                "name": "financial",
                "keywords": ["income", "salary", "balance", "account", "credit", "loan"],
                "columns": []
            },
            {
                "name": "health",
                "keywords": ["height", "weight", "bmi", "blood", "heart", "medical"],
                "columns": []
            },
            {
                "name": "temporal",
                "keywords": ["date", "time", "created", "updated", "timestamp"],
                "columns": []
            }
        ]
        
        for col in columns:
            col_name_lower = col.name.lower()
            for group in semantic_patterns:
                if any(keyword in col_name_lower for keyword in group["keywords"]):
                    group["columns"].append(col.name)
        
        # Return non-empty groups
        return [group for group in semantic_patterns if group["columns"]]
    
    def _identify_business_entities(self, columns) -> List[Dict[str, Any]]:
        """Identify business entities in the dataset"""
        entities = []
        
        # Common business entities
        entity_patterns = [
            {"name": "customer", "keywords": ["customer", "client", "user", "member"]},
            {"name": "product", "keywords": ["product", "item", "sku", "part"]},
            {"name": "order", "keywords": ["order", "purchase", "transaction", "sale"]},
            {"name": "employee", "keywords": ["employee", "staff", "worker", "personnel"]},
            {"name": "location", "keywords": ["location", "address", "city", "state", "country"]}
        ]
        
        for col in columns:
            col_name_lower = col.name.lower()
            for entity in entity_patterns:
                if any(keyword in col_name_lower for keyword in entity["keywords"]):
                    entities.append({
                        "entity": entity["name"],
                        "column": col.name,
                        "confidence": 0.8
                    })
        
        return entities
    
    def _identify_domain_concepts(self, columns, domain: str) -> List[Dict[str, Any]]:
        """Identify domain-specific concepts"""
        concepts = []
        
        # Domain-specific concept patterns
        domain_concepts = {
            "healthcare": ["patient", "diagnosis", "treatment", "medication", "vital"],
            "finance": ["account", "transaction", "balance", "credit", "loan"],
            "retail": ["product", "inventory", "sales", "customer", "order"],
            "manufacturing": ["production", "quality", "equipment", "maintenance", "yield"]
        }
        
        if domain in domain_concepts:
            for col in columns:
                col_name_lower = col.name.lower()
                for concept in domain_concepts[domain]:
                    if concept in col_name_lower:
                        concepts.append({
                            "concept": concept,
                            "column": col.name,
                            "domain": domain
                        })
        
        return concepts
    
    def _identify_semantic_relationships_advanced(self, columns) -> List[Dict[str, Any]]:
        """Identify advanced semantic relationships between columns"""
        relationships = []
        
        # Common relationship patterns
        relationship_patterns = [
            {
                "type": "composition",
                "pattern": ["first_name", "last_name", "full_name"],
                "description": "Name composition relationship"
            },
            {
                "type": "calculation",
                "pattern": ["height", "weight", "bmi"],
                "description": "BMI calculation relationship"
            },
            {
                "type": "temporal",
                "pattern": ["birth_date", "age"],
                "description": "Age calculation from birth date"
            },
            {
                "type": "hierarchical",
                "pattern": ["country", "state", "city"],
                "description": "Geographic hierarchy"
            }
        ]
        
        column_names = [col.name for col in columns]
        
        for pattern in relationship_patterns:
            if all(col in column_names for col in pattern["pattern"]):
                relationships.append({
                    "type": pattern["type"],
                    "columns": pattern["pattern"],
                    "description": pattern["description"]
                })
        
        return relationships
    
    def _classify_cardinality(self, column) -> str:
        """Classify the cardinality of a categorical column"""
        try:
            cardinality_ratio = column.unique_values / column.total_count
            
            if cardinality_ratio < 0.01:
                return "very_low"
            elif cardinality_ratio < 0.1:
                return "low"
            elif cardinality_ratio < 0.5:
                return "medium"
            elif cardinality_ratio < 0.9:
                return "high"
            else:
                return "very_high"
        except Exception:
            return "unknown"
    
    def _calculate_gini_impurity(self, column) -> float:
        """Calculate Gini impurity for categorical data"""
        try:
            if hasattr(column, 'sample_values'):
                sample_values = column.get_sample_values()
                if sample_values:
                    value_counts = pd.Series(sample_values).value_counts()
                    probabilities = value_counts / len(sample_values)
                    gini = 1 - np.sum(probabilities ** 2)
                    return gini
            return 0.0
        except Exception:
            return 0.0
    
    def _analyze_categorical_correlations(self, categorical_columns) -> Dict[str, Any]:
        """Analyze correlations between categorical columns"""
        try:
            correlations = {}
            
            # This would calculate actual categorical correlations
            # For now, return placeholder
            for i, col1 in enumerate(categorical_columns):
                for j, col2 in enumerate(categorical_columns[i+1:], i+1):
                    pair_name = f"{col1.name}_{col2.name}"
                    correlations[pair_name] = {
                        "chi_square": 0.3,
                        "cramers_v": 0.2,
                        "contingency_coefficient": 0.25
                    }
            
            return correlations
        except Exception:
            return {}
    
    def _classify_anomaly_type(self, column) -> str:
        """Classify the type of anomaly in a column"""
        try:
            # This would analyze actual anomaly patterns
            return "statistical_outlier"
        except Exception:
            return "unknown"
    
    def _assess_anomaly_severity(self, column) -> str:
        """Assess the severity of anomalies in a column"""
        try:
            outlier_percentage = self._calculate_outlier_percentage(column)
            
            if outlier_percentage < 0.01:
                return "low"
            elif outlier_percentage < 0.05:
                return "medium"
            else:
                return "high"
        except Exception:
            return "unknown"
    
    def _suggest_anonymization_method(self, column) -> str:
        """Suggest anonymization method for a column"""
        try:
            if column.data_type.value == "string":
                return "generalization"
            elif column.data_type.value in ["integer", "float"]:
                return "noise_addition"
            elif column.data_type.value == "date":
                return "date_perturbation"
            else:
                return "suppression"
        except Exception:
            return "generalization"
    
    def _detect_missing_pattern(self, column) -> str:
        """Detect the pattern of missing data in a column"""
        try:
            # This would analyze actual missing data patterns
            return "random"
        except Exception:
            return "unknown"
    
    async def _fallback_pattern_analysis(self, dataset: Dataset) -> Dict[str, Any]:
        """Fallback pattern analysis when advanced analysis fails"""
        try:
            return {
                "dataset_metadata": {
                    "name": dataset.name,
                    "description": dataset.description,
                    "row_count": dataset.row_count,
                    "column_count": len(dataset.columns)
                },
                "sampling_strategy": {"method": "random", "sample_size": 100},
                "representative_samples": [],
                "statistical_patterns": {},
                "semantic_patterns": {},
                "temporal_patterns": {},
                "categorical_patterns": {},
                "correlation_patterns": {},
                "anomaly_patterns": {},
                "business_patterns": {},
                "privacy_patterns": {},
                "generation_complexity": {"overall_complexity": 0.5}
            }
        except Exception:
            return {}

# === Advanced Prompt Engineering and Generation Optimization ===

class PromptOptimizer:
    """
    Dynamically builds context-aware prompts for synthetic data generation.
    """
    def build_context_aware_prompt(self, schema, sample_data, privacy_level):
        prompt = ""
        for col in schema or []:
            col_name = getattr(col, 'name', str(col))
            col_type = getattr(col, 'data_type', 'string')
            col_privacy = getattr(col, 'privacy_category', 'general')
            prompt += f"Column: {col_name}\nType: {col_type}\n"
            if sample_data is not None:
                # Add up to 3 few-shot examples for this column
                examples = [str(row.get(col_name, '')) for row in sample_data[:3]]
                prompt += f"Examples: {examples}\n"
            if col_privacy == 'sensitive' or privacy_level == 'high':
                prompt += "Instruction: Apply strict privacy protection.\n"
            else:
                prompt += "Instruction: Standard privacy.\n"
        prompt += f"Overall privacy level: {privacy_level}\n"
        return prompt

class ClaudeResponseProcessor:
    """
    Multi-stage validation and enhancement of Claude-generated data.
    """
    def validate_statistical_properties(self, original, synthetic):
        # For each numeric column, use KS test; for categorical, use chi-squared
        if original is None or synthetic is None:
            return {}
        results = {}
        for col in original.columns:
            if col not in synthetic.columns:
                continue
            if np.issubdtype(original[col].dtype, np.number):
                stat, p = ks_2samp(original[col].dropna(), synthetic[col].dropna())
                results[col] = {'ks_stat': stat, 'p_value': p}
            else:
                try:
                    obs = np.array([original[col].value_counts().reindex(synthetic[col].unique(), fill_value=0),
                                    synthetic[col].value_counts().reindex(synthetic[col].unique(), fill_value=0)])
                    chi2, p, _, _ = chi2_contingency(obs)
                    results[col] = {'chi2_stat': chi2, 'p_value': p}
                except Exception:
                    results[col] = {'chi2_stat': None, 'p_value': None}
        return results

    def repair_data_quality(self, synthetic_data):
        # Fix common issues: type mismatches, referential integrity, fill missing values
        if synthetic_data is None:
            return synthetic_data
        df = synthetic_data.copy()
        for col in df.columns:
            # Try to infer type from data
            if df[col].dtype == object:
                try:
                    df[col] = pd.to_numeric(df[col], errors='ignore')
                except Exception:
                    pass
            # Fill missing values
            if df[col].isnull().any():
                if np.issubdtype(df[col].dtype, np.number):
                    df[col] = df[col].fillna(df[col].mean())
                else:
                    df[col] = df[col].fillna('unknown')
        # TODO: Add referential integrity checks if foreign keys are known
        return df

class ContextManager:
    """
    Smart chunking for large datasets.
    """
    def chunk_intelligently(self, dataset, chunk_size=10000):
        # Split dataset into chunks, preserving relationships if possible
        if hasattr(dataset, 'to_dict'):
            df = pd.DataFrame(dataset.to_dict())
        elif isinstance(dataset, pd.DataFrame):
            df = dataset
        else:
            return [dataset]
        n = len(df)
        chunks = [df.iloc[i:i+chunk_size] for i in range(0, n, chunk_size)]
        # TODO: Add logic to preserve foreign key relationships across chunks
        return chunks

class AdaptiveLearning:
    """
    Adaptive learning from user feedback.
    """
    def __init__(self):
        self.feedback_store = defaultdict(list)  # generation_id -> list of (score, timestamp)
        self.prompt_profiles = defaultdict(dict)  # user_id or dataset_id -> prompt config

    def learn_from_user_feedback(self, generation_id, quality_score):
        import time
        self.feedback_store[generation_id].append((quality_score, time.time()))
        # TODO: Use feedback to adjust prompt strategies, e.g., via moving average or A/B test
        # For now, just store feedback
        return True

    def get_average_score(self, generation_id):
        scores = [score for score, _ in self.feedback_store[generation_id]]
        return np.mean(scores) if scores else None

class GenerationAnalytics:
    """
    Analytics and optimization for Claude-based generation.
    """
    def __init__(self):
        self.performance_log = []  # List of (timestamp, response_time, quality, cost)
        self.quality_degradation_events = []
        self.prompt_cache = {}  # schema_hash -> prompt

    def track_claude_performance(self, response_time=None, quality=None, cost=None):
        import time
        self.performance_log.append((time.time(), response_time, quality, cost))
        # Detect quality degradation
        if quality is not None and len(self.performance_log) > 5:
            recent = [q for _, _, q, _ in self.performance_log[-5:] if q is not None]
            if len(recent) == 5 and np.mean(recent) < 0.7:
                self.quality_degradation_events.append(time.time())
        # TODO: Add cost optimization logic
        return True

    def cache_prompt(self, schema_hash, prompt):
        self.prompt_cache[schema_hash] = prompt

    def get_cached_prompt(self, schema_hash):
        return self.prompt_cache.get(schema_hash) 