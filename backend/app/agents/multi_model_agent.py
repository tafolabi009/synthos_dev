"""
Multi-Model Agent for Synthos
Orchestrates Claude, OpenAI, and custom models for optimal synthetic data generation
Leverages strengths of different AI providers and custom trained models
"""

import asyncio
import json
import numpy as np
from app.utils.optional_imports import pd, PANDAS_AVAILABLE
from typing import Dict, List, Any, Optional, Tuple, Union
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
import logging
from enum import Enum
import openai
from anthropic import AsyncAnthropic
import google.cloud.aiplatform as aiplatform

from app.core.config import settings
from app.core.logging import get_logger
from app.models.dataset import Dataset, CustomModel, GenerationJob
from app.models.user import User, SubscriptionTier
from app.agents.claude_agent import AdvancedClaudeAgent, GenerationConfig, ModelType
from app.agents.enhanced_realism_engine import EnhancedRealismEngine, RealismConfig, IndustryDomain

logger = get_logger(__name__)


class AIProvider(Enum):
    """Supported AI providers"""
    CLAUDE = "claude"
    OPENAI = "openai"
    CUSTOM = "custom"
    HYBRID = "hybrid"


class OpenAIModel(Enum):
    """OpenAI models for synthetic data generation"""
    GPT_4_TURBO = "gpt-4-turbo-preview"
    GPT_4 = "gpt-4"
    GPT_3_5_TURBO = "gpt-3.5-turbo-0125"


@dataclass
class ModelCapabilities:
    """Define capabilities and strengths of each model type"""
    provider: AIProvider
    model_name: str
    strengths: List[str]
    weaknesses: List[str]
    best_for_domains: List[IndustryDomain]
    supported_strategies: List[str]
    cost_per_1k_tokens: float
    max_context_length: int
    generation_speed: str  # "fast", "medium", "slow"
    accuracy_rating: float  # 0-1 scale


@dataclass
class MultiModelConfig:
    """Configuration for multi-model generation"""
    primary_provider: AIProvider = AIProvider.CLAUDE
    fallback_providers: List[AIProvider] = None
    use_ensemble: bool = False
    ensemble_voting: str = "weighted"  # "majority", "weighted", "consensus"
    quality_threshold: float = 0.95
    cost_optimization: bool = True
    speed_optimization: bool = False
    custom_model_preference: bool = True  # Prefer custom models when available
    provider_weights: Dict[AIProvider, float] = None


class MultiModelAgent:
    """
    Advanced multi-model agent that orchestrates different AI providers
    and custom models for optimal synthetic data generation
    """
    
    def __init__(self):
        self.claude_agent = AdvancedClaudeAgent()
        self.realism_engine = EnhancedRealismEngine()
        
        # Initialize OpenAI
        if settings.OPENAI_API_KEY:
            openai.api_key = settings.OPENAI_API_KEY
            self.openai_client = openai.AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        else:
            self.openai_client = None
            logger.warning("OpenAI API key not configured")
        
        # Initialize Anthropic
        self.claude_client = AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY) if settings.ANTHROPIC_API_KEY else None
        
        # Initialize Vertex AI
        try:
            aiplatform.init(project=settings.VERTEX_PROJECT_ID or settings.GCP_PROJECT_ID, location=settings.VERTEX_LOCATION)
            self.vertex_available = True
        except Exception:
            self.vertex_available = False
            logger.warning("Vertex AI not initialized; ensure ADC and project/location are set")
        
        # Model alias map (expand as needed)
        self.vertex_alias_map = {
            "claude-opus-4": "anthropic/claude-3.7-sonnet",  # replace with official Vertex Anthropic Opus 4 id when available
            "claude-sonnet-3": "anthropic/claude-3-sonnet",
        }
        
        # Model capabilities database
        self.model_capabilities = self._initialize_model_capabilities()
        
        # Custom model registry
        self.custom_model_registry = {}
        
    def _resolve_vertex_model(self, name: str) -> str:
        return self.vertex_alias_map.get(name, name)

    def _initialize_model_capabilities(self) -> Dict[str, ModelCapabilities]:
        """Initialize capabilities database for different models"""
        
        return {
            "claude-3-5-sonnet": ModelCapabilities(
                provider=AIProvider.CLAUDE,
                model_name="claude-3-5-sonnet-20241022",
                strengths=[
                    "Latest reasoning", "Enhanced accuracy", "Better code understanding",
                    "Improved business logic", "Advanced domain expertise", "Larger context"
                ],
                weaknesses=[
                    "Higher cost", "Newer model", "Limited availability"
                ],
                best_for_domains=[
                    IndustryDomain.HEALTHCARE, IndustryDomain.FINANCE, 
                    IndustryDomain.MANUFACTURING, IndustryDomain.GENERAL, IndustryDomain.TECHNOLOGY
                ],
                supported_strategies=["premium", "hybrid", "semantic", "reasoning"],
                cost_per_1k_tokens=0.003,
                max_context_length=200000,
                generation_speed="fast",
                accuracy_rating=0.98
            ),
            "claude-3-5-haiku": ModelCapabilities(
                provider=AIProvider.CLAUDE,
                model_name="claude-3-5-haiku-20241022",
                strengths=[
                    "Fast generation", "Cost effective", "Good quality",
                    "Quick responses", "Efficient processing"
                ],
                weaknesses=[
                    "Lower accuracy than Sonnet", "Simpler reasoning"
                ],
                best_for_domains=[
                    IndustryDomain.GENERAL, IndustryDomain.RETAIL,
                    IndustryDomain.AUTOMOTIVE, IndustryDomain.ENERGY
                ],
                supported_strategies=["fast", "volume", "general"],
                cost_per_1k_tokens=0.00025,
                max_context_length=200000,
                generation_speed="very_fast",
                accuracy_rating=0.90
            ),
            "claude-3-sonnet": ModelCapabilities(
                provider=AIProvider.CLAUDE,
                model_name="claude-3-sonnet-20240229",
                strengths=[
                    "Complex reasoning", "Business logic understanding", 
                    "Semantic consistency", "Domain expertise", "Large context"
                ],
                weaknesses=[
                    "Cost", "Speed for large datasets", "API rate limits"
                ],
                best_for_domains=[
                    IndustryDomain.HEALTHCARE, IndustryDomain.FINANCE, 
                    IndustryDomain.MANUFACTURING, IndustryDomain.GENERAL
                ],
                supported_strategies=["hybrid", "semantic", "reasoning"],
                cost_per_1k_tokens=0.003,
                max_context_length=200000,
                generation_speed="medium",
                accuracy_rating=0.96
            ),
            "claude-3-opus": ModelCapabilities(
                provider=AIProvider.CLAUDE,
                model_name="claude-3-opus-20240229",
                strengths=[
                    "Highest accuracy", "Complex domain understanding",
                    "Advanced reasoning", "Perfect business rules"
                ],
                weaknesses=[
                    "Highest cost", "Slower speed", "Overkill for simple data"
                ],
                best_for_domains=[
                    IndustryDomain.HEALTHCARE, IndustryDomain.FINANCE,
                    IndustryDomain.AEROSPACE, IndustryDomain.PHARMACEUTICAL
                ],
                supported_strategies=["premium", "critical", "enterprise"],
                cost_per_1k_tokens=0.015,
                max_context_length=200000,
                generation_speed="slow",
                accuracy_rating=0.98
            ),
            "gpt-4-turbo": ModelCapabilities(
                provider=AIProvider.OPENAI,
                model_name="gpt-4-turbo-preview",
                strengths=[
                    "Fast generation", "Good reasoning", "JSON output",
                    "Consistent formatting", "Large context"
                ],
                weaknesses=[
                    "Less domain expertise", "Occasional hallucinations",
                    "Weaker business logic"
                ],
                best_for_domains=[
                    IndustryDomain.RETAIL, IndustryDomain.GENERAL,
                    IndustryDomain.AUTOMOTIVE, IndustryDomain.ENERGY
                ],
                supported_strategies=["fast", "volume", "general"],
                cost_per_1k_tokens=0.001,
                max_context_length=128000,
                generation_speed="fast",
                accuracy_rating=0.89
            ),
            "gpt-3.5-turbo": ModelCapabilities(
                provider=AIProvider.OPENAI,
                model_name="gpt-3.5-turbo-0125",
                strengths=[
                    "Very fast", "Low cost", "Good for simple patterns",
                    "High throughput", "Reliable formatting"
                ],
                weaknesses=[
                    "Limited reasoning", "Simple business rules only",
                    "Less domain knowledge", "Shorter context"
                ],
                best_for_domains=[
                    IndustryDomain.GENERAL, IndustryDomain.RETAIL
                ],
                supported_strategies=["fast", "budget", "volume"],
                cost_per_1k_tokens=0.0005,
                max_context_length=16385,
                generation_speed="fast",
                accuracy_rating=0.82
            }
        }
    
    async def generate_synthetic_data(
        self,
        dataset: Dataset,
        config: GenerationConfig,
        job: GenerationJob,
        user: User,
        multi_config: MultiModelConfig = None
    ) -> Tuple[pd.DataFrame, Dict[str, Any]]:
        """
        Generate synthetic data using optimal model selection and ensemble methods
        """
        if not multi_config:
            multi_config = MultiModelConfig()
        
        logger.info(
            "Starting multi-model synthetic data generation",
            dataset_id=dataset.id,
            primary_provider=multi_config.primary_provider.value,
            use_ensemble=multi_config.use_ensemble
        )
        
        # Step 1: Determine optimal model strategy
        optimal_strategy = await self._determine_optimal_strategy(
            dataset, config, user, multi_config
        )
        
        # Step 2: Generate data using selected strategy
        if optimal_strategy["use_ensemble"]:
            synthetic_data, metrics = await self._ensemble_generation(
                dataset, config, job, optimal_strategy
            )
        else:
            synthetic_data, metrics = await self._single_model_generation(
                dataset, config, job, optimal_strategy
            )
        
        # Step 3: Apply enhanced realism processing
        enhanced_data, realism_metrics = await self._apply_enhanced_realism(
            synthetic_data, dataset, config, optimal_strategy
        )
        
        # Step 4: Combine metrics
        final_metrics = self._combine_metrics(metrics, realism_metrics, optimal_strategy)
        
        logger.info(
            "Multi-model generation complete",
            strategy_used=optimal_strategy["strategy"],
            models_used=optimal_strategy["models"],
            overall_quality=final_metrics.get("overall_quality", 0.0)
        )
        
        return enhanced_data, final_metrics
    
    async def _determine_optimal_strategy(
        self,
        dataset: Dataset,
        config: GenerationConfig,
        user: User,
        multi_config: MultiModelConfig
    ) -> Dict[str, Any]:
        """
        Determine the optimal model strategy based on dataset, user tier, requirements, and cost/quality tradeoff
        """
        domain = await self._detect_industry_domain(dataset)
        complexity = await self._assess_dataset_complexity(dataset)
        user_capabilities = self._get_user_model_access(user)
        custom_models = await self._get_user_custom_models(user, dataset)
        # Dynamic batch size for cost optimization
        if config.rows > 100000:
            config.batch_size = 5000
        elif config.rows > 20000:
            config.batch_size = 2000
        else:
            config.batch_size = 1000
        # Dynamic model selection
        strategy = {
            "domain": domain,
            "complexity": complexity,
            "user_tier": user.subscription_tier.value,
            "models": [],
            "use_ensemble": False,
            "strategy": "single_model",
            "custom_models": custom_models
        }
        # Enterprise: Use Claude 3.5 Sonnet for complex, Claude 3.5 Haiku for simple, ensemble for critical
        if user.subscription_tier == SubscriptionTier.ENTERPRISE:
            if custom_models and domain in [IndustryDomain.HEALTHCARE, IndustryDomain.FINANCE]:
                strategy.update({
                    "models": ["claude-3-5-sonnet", custom_models[0]["name"]],
                    "use_ensemble": True,
                    "strategy": "enterprise_ensemble",
                    "voting": "consensus"
                })
            elif complexity == "high":
                strategy.update({
                    "models": ["claude-3-5-sonnet"],
                    "use_ensemble": False,
                    "strategy": "enterprise_premium",
                    "primary": "claude-3-5-sonnet"
                })
            else:
                strategy.update({
                    "models": ["claude-3-5-haiku"],
                    "use_ensemble": False,
                    "strategy": "enterprise_cost_opt",
                    "primary": "claude-3-5-haiku"
                })
        # Growth: Use Claude 3.5 Haiku for most, Claude 3.5 Sonnet for complex
        elif user.subscription_tier == SubscriptionTier.GROWTH:
            if custom_models:
                strategy.update({
                    "models": ["claude-3-5-haiku", custom_models[0]["name"]],
                    "use_ensemble": False,
                    "strategy": "growth_custom",
                    "primary": "claude-3-5-haiku"
                })
            elif complexity == "high":
                strategy.update({
                    "models": ["claude-3-5-sonnet"],
                    "use_ensemble": False,
                    "strategy": "growth_complex",
                    "primary": "claude-3-5-sonnet"
                })
            else:
                strategy.update({
                    "models": ["claude-3-5-haiku"],
                    "use_ensemble": False,
                    "strategy": "growth_fast",
                    "primary": "claude-3-5-haiku"
                })
        # Professional: Use Claude 3.5 Haiku for large/simple, Claude 3.5 Sonnet for small/complex
        elif user.subscription_tier == SubscriptionTier.PROFESSIONAL:
            if config.rows > 50000 or complexity == "low":
                strategy.update({
                    "models": ["claude-3-5-haiku"],
                    "use_ensemble": False,
                    "strategy": "professional_speed",
                    "primary": "claude-3-5-haiku"
                })
            else:
                strategy.update({
                    "models": ["claude-3-5-sonnet"],
                    "use_ensemble": False,
                    "strategy": "professional_balanced",
                    "primary": "claude-3-5-sonnet"
                })
        # Starter/Free: Use Claude 3.5 Haiku for cost efficiency
        else:
            strategy.update({
                "models": ["claude-3-5-haiku"],
                "use_ensemble": False,
                "strategy": "single_model",
                "primary": "claude-3-5-haiku"
            })
        return strategy
    
    async def _ensemble_generation(
        self,
        dataset: Dataset,
        config: GenerationConfig,
        job: GenerationJob,
        strategy: Dict[str, Any]
    ) -> Tuple[pd.DataFrame, Dict[str, Any]]:
        """
        Generate synthetic data using ensemble of multiple models
        """
        logger.info("Starting ensemble generation", models=strategy["models"])
        
        # Generate data from each model in parallel
        generation_tasks = []
        for model_name in strategy["models"]:
            if model_name.startswith("claude"):
                task = self._generate_with_claude(dataset, config, job, model_name)
            elif model_name.startswith("gpt"):
                task = self._generate_with_openai(dataset, config, job, model_name)
            elif model_name.startswith("gemini") or model_name.startswith("claude-"):
                task = self._generate_with_vertex(dataset, config, job, self._resolve_vertex_model(model_name))
            else:
                task = self._generate_with_custom_model(dataset, config, job, model_name)
            generation_tasks.append(task)
        
        # Wait for all generations to complete
        results = await asyncio.gather(*generation_tasks, return_exceptions=True)
        
        # Filter successful results
        successful_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.warning(f"Model {strategy['models'][i]} failed: {result}")
            else:
                successful_results.append(result)
        
        if not successful_results:
            raise Exception("All models failed to generate data")
        
        # Combine results using ensemble method
        if strategy.get("voting") == "consensus":
            combined_data = await self._consensus_ensemble(successful_results)
        elif strategy.get("voting") == "weighted":
            combined_data = await self._weighted_ensemble(successful_results, strategy)
        else:
            combined_data = await self._majority_ensemble(successful_results)
        
        # Calculate ensemble metrics
        ensemble_metrics = await self._calculate_ensemble_metrics(successful_results)
        
        return combined_data, ensemble_metrics
    
    async def _single_model_generation(
        self,
        dataset: Dataset,
        config: GenerationConfig,
        job: GenerationJob,
        strategy: Dict[str, Any]
    ) -> Tuple[pd.DataFrame, Dict[str, Any]]:
        """
        Generate synthetic data using a single optimal model
        """
        primary_model = strategy.get("primary", strategy["models"][0])
        
        logger.info("Starting single model generation", model=primary_model)
        
        if primary_model.startswith("claude"):
            return await self._generate_with_claude(dataset, config, job, primary_model)
        elif primary_model.startswith("gpt"):
            return await self._generate_with_openai(dataset, config, job, primary_model)
        elif primary_model.startswith("gemini") or primary_model.startswith("claude-"):
            return await self._generate_with_vertex(dataset, config, job, self._resolve_vertex_model(primary_model))
        else:
            return await self._generate_with_custom_model(dataset, config, job, primary_model)
    
    async def _generate_with_claude(
        self,
        dataset: Dataset,
        config: GenerationConfig,
        job: GenerationJob,
        model_name: str
    ) -> Tuple[pd.DataFrame, Dict[str, Any]]:
        """Generate using Claude models"""
        
        # Update config to use specified Claude model
        model_type = ModelType.CLAUDE_3_5_SONNET  # Default to latest
        if "claude-3-5-sonnet" in model_name:
            model_type = ModelType.CLAUDE_3_5_SONNET
        elif "claude-3-5-haiku" in model_name:
            model_type = ModelType.CLAUDE_3_5_HAIKU
        elif "opus" in model_name:
            model_type = ModelType.CLAUDE_3_OPUS
        elif "claude-3-sonnet" in model_name:
            model_type = ModelType.CLAUDE_3_SONNET
        elif "claude-3-haiku" in model_name:
            model_type = ModelType.CLAUDE_3_HAIKU
        
        config.model_type = model_type
        
        # Use existing Claude agent
        return await self.claude_agent.generate_synthetic_data(dataset, config, job)
    
    async def _generate_with_openai(
        self,
        dataset: Dataset,
        config: GenerationConfig,
        job: GenerationJob,
        model_name: str
    ) -> Tuple[pd.DataFrame, Dict[str, Any]]:
        """Generate using OpenAI models"""
        
        if not self.openai_client:
            raise Exception("OpenAI not configured")
        
        logger.info(f"Generating with OpenAI {model_name}")
        
        # Prepare dataset context for OpenAI
        schema_analysis = await self._analyze_dataset_with_openai(dataset, model_name)
        
        # Generate synthetic data
        synthetic_data = await self._openai_batch_generation(
            dataset, config, schema_analysis, model_name
        )
        
        # Calculate quality metrics
        quality_metrics = await self._assess_openai_quality(dataset, synthetic_data)
        
        return synthetic_data, quality_metrics
    
    async def _generate_with_custom_model(
        self,
        dataset: Dataset,
        config: GenerationConfig,
        job: GenerationJob,
        model_name: str
    ) -> Tuple[pd.DataFrame, Dict[str, Any]]:
        """Generate using custom trained models"""
        
        # Load custom model from registry
        custom_model = self.custom_model_registry.get(model_name)
        if not custom_model:
            raise Exception(f"Custom model {model_name} not found")
        
        logger.info(f"Generating with custom model {model_name}")
        
        # Run custom model inference
        synthetic_data = await self._run_custom_model_inference(
            custom_model, dataset, config
        )
        
        # Calculate quality metrics
        quality_metrics = await self._assess_custom_model_quality(
            dataset, synthetic_data, custom_model
        )
        
        return synthetic_data, quality_metrics
    
    async def _generate_with_vertex(
        self,
        dataset: Dataset,
        config: GenerationConfig,
        job: GenerationJob,
        model_name: str
    ) -> Tuple[pd.DataFrame, Dict[str, Any]]:
        """Generate using Vertex AI models"""
        if not self.vertex_available:
            raise Exception("Vertex AI not initialized or configured")

        logger.info(f"Generating with Vertex AI {model_name}")

        # Prepare dataset context for Vertex AI
        schema_analysis = await self._analyze_dataset_with_vertex(dataset, model_name)

        # Generate synthetic data
        synthetic_data = await self._vertex_batch_generation(
            dataset, config, schema_analysis, model_name
        )

        # Calculate quality metrics
        quality_metrics = await self._assess_vertex_quality(dataset, synthetic_data)

        return synthetic_data, quality_metrics

    async def _analyze_dataset_with_openai(
        self,
        dataset: Dataset,
        model_name: str
    ) -> Dict[str, Any]:
        """Analyze dataset using OpenAI for generation planning"""
        
        # Prepare dataset summary
        dataset_summary = {
            "name": dataset.name,
            "description": dataset.description,
            "columns": [
                {
                    "name": col.name,
                    "type": col.data_type.value,
                    "sample_values": col.get_sample_values()[:5],
                    "null_count": col.null_count,
                    "unique_values": col.unique_values
                }
                for col in dataset.columns
            ]
        }
        
        analysis_prompt = f"""
        Analyze this dataset for synthetic data generation:
        
        Dataset: {json.dumps(dataset_summary, indent=2)}
        
        Provide a JSON analysis with:
        1. Column types and generation strategies
        2. Relationships between columns
        3. Business rules and constraints
        4. Recommended generation approach
        
        Return only valid JSON.
        """
        
        try:
            response = await self.openai_client.chat.completions.create(
                model=model_name,
                messages=[{"role": "user", "content": analysis_prompt}],
                temperature=0.3,
                max_tokens=2000
            )
            
            return json.loads(response.choices[0].message.content)
            
        except Exception as e:
            logger.warning(f"OpenAI analysis failed: {e}")
            return await self._fallback_dataset_analysis(dataset)
    
    async def _openai_batch_generation(
        self,
        dataset: Dataset,
        config: GenerationConfig,
        schema_analysis: Dict[str, Any],
        model_name: str
    ) -> pd.DataFrame:
        """Generate synthetic data in batches using OpenAI"""
        
        batch_size = min(1000, config.rows // 5)
        total_batches = (config.rows + batch_size - 1) // batch_size
        
        generated_batches = []
        
        for batch_idx in range(total_batches):
            current_batch_size = min(batch_size, config.rows - batch_idx * batch_size)
            
            batch_data = await self._generate_openai_batch(
                dataset, schema_analysis, current_batch_size, model_name
            )
            
            if batch_data is not None:
                generated_batches.append(batch_data)
        
        # Combine all batches
        if generated_batches:
            return pd.concat(generated_batches, ignore_index=True)
        else:
            raise Exception("Failed to generate any data batches")
    
    async def _generate_openai_batch(
        self,
        dataset: Dataset,
        schema_analysis: Dict[str, Any],
        batch_size: int,
        model_name: str
    ) -> pd.DataFrame:
        """Generate a single batch using OpenAI"""
        
        generation_prompt = f"""
        Generate {batch_size} rows of synthetic data based on this schema:
        
        Schema Analysis: {json.dumps(schema_analysis, indent=2)}
        
        Requirements:
        1. Follow the detected patterns and relationships
        2. Generate realistic values for each column type
        3. Maintain statistical properties
        4. Return as valid JSON array of objects
        
        Generate exactly {batch_size} rows.
        """
        
        try:
            response = await self.openai_client.chat.completions.create(
                model=model_name,
                messages=[{"role": "user", "content": generation_prompt}],
                temperature=0.7,
                max_tokens=4000
            )
            
            generated_json = json.loads(response.choices[0].message.content)
            return pd.DataFrame(generated_json)
            
        except Exception as e:
            logger.warning(f"OpenAI batch generation failed: {e}")
            return None
    
    def _get_user_model_access(self, user: User) -> Dict[str, bool]:
        """Determine what models the user has access to based on their tier"""
        
        tier = user.subscription_tier
        
        access = {
            "claude_sonnet": True,  # All tiers
            "claude_opus": tier in [SubscriptionTier.ENTERPRISE],
            "gpt_4_turbo": tier in [SubscriptionTier.GROWTH, SubscriptionTier.ENTERPRISE],
            "gpt_3_5_turbo": tier in [SubscriptionTier.PROFESSIONAL, SubscriptionTier.GROWTH, SubscriptionTier.ENTERPRISE],
            "custom_models": tier in [SubscriptionTier.GROWTH, SubscriptionTier.ENTERPRISE],
            "multi_model_generation": tier in [SubscriptionTier.PROFESSIONAL, SubscriptionTier.GROWTH, SubscriptionTier.ENTERPRISE],
            "ensemble_generation": tier in [SubscriptionTier.ENTERPRISE],
            "premium_features": tier in [SubscriptionTier.PROFESSIONAL, SubscriptionTier.GROWTH, SubscriptionTier.ENTERPRISE]
        }
        
        return access
    
    async def _get_user_custom_models(self, user: User, dataset: Dataset) -> List[Dict[str, Any]]:
        """Get user's custom models that are compatible with the dataset"""
        
        # This would query the database for user's custom models
        # For now, return empty list
        return []
    
    # Additional helper methods would be implemented here...
    async def _detect_industry_domain(self, dataset: Dataset) -> IndustryDomain:
        """Detect industry domain from dataset characteristics"""
        # Reuse logic from enhanced realism engine
        return IndustryDomain.GENERAL
    
    async def _assess_dataset_complexity(self, dataset: Dataset) -> str:
        """Assess complexity of the dataset"""
        # Simple complexity assessment
        if len(dataset.columns) > 20:
            return "high"
        elif len(dataset.columns) > 10:
            return "medium"
        else:
            return "low" 

    async def _consensus_ensemble(self, results: List[Tuple[pd.DataFrame, Dict[str, Any]]]) -> pd.DataFrame:
        """
        Combine results using consensus-based ensemble method
        """
        try:
            if not results:
                raise ValueError("No results to ensemble")
            
            # Extract dataframes and metrics
            dataframes = [result[0] for result in results]
            metrics = [result[1] for result in results]
            
            # Align all dataframes to have same columns
            aligned_dataframes = self._align_dataframes(dataframes)
            
            # Apply consensus voting for each cell
            consensus_data = await self._apply_consensus_voting(aligned_dataframes)
            
            # Validate consensus result
            consensus_df = pd.DataFrame(consensus_data)
            consensus_df = await self._validate_consensus_result(consensus_df, metrics)
            
            return consensus_df
            
        except Exception as e:
            logger.error(f"Consensus ensemble failed: {e}")
            # Return the best individual result
            return self._get_best_individual_result(results)
    
    async def _weighted_ensemble(
        self, 
        results: List[Tuple[pd.DataFrame, Dict[str, Any]]], 
        strategy: Dict[str, Any]
    ) -> pd.DataFrame:
        """
        Combine results using weighted ensemble method
        """
        try:
            if not results:
                raise ValueError("No results to ensemble")
            
            # Extract dataframes and metrics
            dataframes = [result[0] for result in results]
            metrics = [result[1] for result in results]
            
            # Calculate weights based on model performance
            weights = await self._calculate_model_weights(metrics, strategy)
            
            # Align all dataframes
            aligned_dataframes = self._align_dataframes(dataframes)
            
            # Apply weighted combination
            weighted_data = await self._apply_weighted_combination(aligned_dataframes, weights)
            
            # Validate weighted result
            weighted_df = pd.DataFrame(weighted_data)
            weighted_df = await self._validate_weighted_result(weighted_df, metrics, weights)
            
            return weighted_df
            
        except Exception as e:
            logger.error(f"Weighted ensemble failed: {e}")
            return self._get_best_individual_result(results)
    
    async def _majority_ensemble(self, results: List[Tuple[pd.DataFrame, Dict[str, Any]]]) -> pd.DataFrame:
        """
        Combine results using majority voting ensemble method
        """
        try:
            if not results:
                raise ValueError("No results to ensemble")
            
            # Extract dataframes and metrics
            dataframes = [result[0] for result in results]
            metrics = [result[1] for result in results]
            
            # Align all dataframes
            aligned_dataframes = self._align_dataframes(dataframes)
            
            # Apply majority voting
            majority_data = await self._apply_majority_voting(aligned_dataframes)
            
            # Validate majority result
            majority_df = pd.DataFrame(majority_data)
            majority_df = await self._validate_majority_result(majority_df, metrics)
            
            return majority_df
            
        except Exception as e:
            logger.error(f"Majority ensemble failed: {e}")
            return self._get_best_individual_result(results)
    
    def _align_dataframes(self, dataframes: List[pd.DataFrame]) -> List[pd.DataFrame]:
        """Align dataframes to have same columns and structure"""
        try:
            if not dataframes:
                return []
            
            # Get all unique columns
            all_columns = set()
            for df in dataframes:
                all_columns.update(df.columns)
            
            # Align each dataframe
            aligned_dataframes = []
            for df in dataframes:
                aligned_df = df.copy()
                
                # Add missing columns with default values
                for col in all_columns:
                    if col not in aligned_df.columns:
                        # Infer default value based on other dataframes
                        default_value = self._infer_default_value(col, dataframes)
                        aligned_df[col] = default_value
                
                # Ensure same column order
                aligned_df = aligned_df[list(all_columns)]
                aligned_dataframes.append(aligned_df)
            
            return aligned_dataframes
            
        except Exception as e:
            logger.error(f"Dataframe alignment failed: {e}")
            return dataframes
    
    def _infer_default_value(self, column: str, dataframes: List[pd.DataFrame]) -> Any:
        """Infer default value for a missing column"""
        try:
            # Find the most common data type for this column across dataframes
            column_types = []
            for df in dataframes:
                if column in df.columns:
                    column_types.append(df[column].dtype)
            
            if not column_types:
                return None
            
            # Use the most common type
            most_common_type = max(set(column_types), key=column_types.count)
            
            # Return appropriate default value
            if pd.api.types.is_numeric_dtype(most_common_type):
                return 0
            elif pd.api.types.is_string_dtype(most_common_type):
                return ""
            elif pd.api.types.is_datetime64_any_dtype(most_common_type):
                return pd.Timestamp.now()
            elif pd.api.types.is_bool_dtype(most_common_type):
                return False
            else:
                return None
                
        except Exception:
            return None
    
    async def _apply_consensus_voting(self, dataframes: List[pd.DataFrame]) -> List[Dict[str, Any]]:
        """Apply consensus voting to combine dataframes"""
        try:
            if not dataframes:
                return []
            
            consensus_rows = []
            n_models = len(dataframes)
            
            # Process each row
            for row_idx in range(len(dataframes[0])):
                consensus_row = {}
                
                # Process each column
                for col in dataframes[0].columns:
                    values = [df.iloc[row_idx][col] for df in dataframes if row_idx < len(df)]
                    
                    # Apply consensus logic based on data type
                    if pd.api.types.is_numeric_dtype(type(values[0])) if values else False:
                        consensus_value = self._consensus_numeric(values)
                    elif pd.api.types.is_string_dtype(type(values[0])) if values else False:
                        consensus_value = self._consensus_categorical(values)
                    else:
                        consensus_value = self._consensus_general(values)
                    
                    consensus_row[col] = consensus_value
                
                consensus_rows.append(consensus_row)
            
            return consensus_rows
            
        except Exception as e:
            logger.error(f"Consensus voting failed: {e}")
            return []
    
    def _consensus_numeric(self, values: List[Any]) -> float:
        """Apply consensus voting for numeric values"""
        try:
            # Remove None/NaN values
            valid_values = [v for v in values if pd.notna(v)]
            
            if not valid_values:
                return 0.0
            
            # Use median for consensus (robust to outliers)
            return float(np.median(valid_values))
            
        except Exception:
            return 0.0
    
    def _consensus_categorical(self, values: List[Any]) -> str:
        """Apply consensus voting for categorical values"""
        try:
            # Remove None/NaN values
            valid_values = [str(v) for v in values if pd.notna(v)]
            
            if not valid_values:
                return ""
            
            # Use most common value
            from collections import Counter
            value_counts = Counter(valid_values)
            return value_counts.most_common(1)[0][0]
            
        except Exception:
            return ""
    
    def _consensus_general(self, values: List[Any]) -> Any:
        """Apply consensus voting for general values"""
        try:
            # Remove None/NaN values
            valid_values = [v for v in values if pd.notna(v)]
            
            if not valid_values:
                return None
            
            # Use most common value
            from collections import Counter
            value_counts = Counter(valid_values)
            return value_counts.most_common(1)[0][0]
            
        except Exception:
            return None
    
    async def _calculate_model_weights(
        self, 
        metrics: List[Dict[str, Any]], 
        strategy: Dict[str, Any]
    ) -> List[float]:
        """Calculate weights for each model based on performance metrics"""
        try:
            weights = []
            
            for metric in metrics:
                # Calculate weight based on quality score
                quality_score = metric.get("overall_quality", 0.5)
                
                # Apply additional factors
                if strategy.get("cost_optimization"):
                    cost_factor = 1.0 / (metric.get("cost", 1.0) + 0.1)  # Lower cost = higher weight
                    quality_score *= cost_factor
                
                if strategy.get("speed_optimization"):
                    speed_factor = 1.0 / (metric.get("execution_time", 1.0) + 0.1)  # Faster = higher weight
                    quality_score *= speed_factor
                
                weights.append(max(0.1, quality_score))  # Minimum weight of 0.1
            
            # Normalize weights
            total_weight = sum(weights)
            if total_weight > 0:
                weights = [w / total_weight for w in weights]
            else:
                weights = [1.0 / len(weights)] * len(weights)
            
            return weights
            
        except Exception as e:
            logger.error(f"Weight calculation failed: {e}")
            # Return equal weights
            return [1.0 / len(metrics)] * len(metrics)
    
    async def _apply_weighted_combination(
        self, 
        dataframes: List[pd.DataFrame], 
        weights: List[float]
    ) -> List[Dict[str, Any]]:
        """Apply weighted combination to dataframes"""
        try:
            if not dataframes or len(dataframes) != len(weights):
                return []
            
            weighted_rows = []
            
            # Process each row
            for row_idx in range(len(dataframes[0])):
                weighted_row = {}
                
                # Process each column
                for col in dataframes[0].columns:
                    weighted_value = self._calculate_weighted_value(
                        dataframes, weights, row_idx, col
                    )
                    weighted_row[col] = weighted_value
                
                weighted_rows.append(weighted_row)
            
            return weighted_rows
            
        except Exception as e:
            logger.error(f"Weighted combination failed: {e}")
            return []
    
    def _calculate_weighted_value(
        self, 
        dataframes: List[pd.DataFrame], 
        weights: List[float], 
        row_idx: int, 
        col: str
    ) -> Any:
        """Calculate weighted value for a specific cell"""
        try:
            values = []
            valid_weights = []
            
            for i, df in enumerate(dataframes):
                if row_idx < len(df) and col in df.columns:
                    value = df.iloc[row_idx][col]
                    if pd.notna(value):
                        values.append(value)
                        valid_weights.append(weights[i])
            
            if not values:
                return None
            
            # Calculate weighted average for numeric values
            if pd.api.types.is_numeric_dtype(type(values[0])):
                return np.average(values, weights=valid_weights)
            else:
                # For categorical values, use weighted voting
                return self._weighted_categorical_voting(values, valid_weights)
                
        except Exception:
            return None
    
    def _weighted_categorical_voting(self, values: List[Any], weights: List[float]) -> Any:
        """Apply weighted voting for categorical values"""
        try:
            # Create weighted vote counts
            vote_counts = {}
            for value, weight in zip(values, weights):
                if value not in vote_counts:
                    vote_counts[value] = 0
                vote_counts[value] += weight
            
            # Return value with highest weighted vote
            return max(vote_counts.items(), key=lambda x: x[1])[0]
            
        except Exception:
            return values[0] if values else None
    
    async def _apply_majority_voting(self, dataframes: List[pd.DataFrame]) -> List[Dict[str, Any]]:
        """Apply majority voting to combine dataframes"""
        try:
            if not dataframes:
                return []
            
            majority_rows = []
            n_models = len(dataframes)
            threshold = n_models // 2 + 1  # Simple majority
            
            # Process each row
            for row_idx in range(len(dataframes[0])):
                majority_row = {}
                
                # Process each column
                for col in dataframes[0].columns:
                    values = [df.iloc[row_idx][col] for df in dataframes if row_idx < len(df)]
                    
                    # Apply majority voting
                    majority_value = self._majority_vote(values, threshold)
                    majority_row[col] = majority_value
                
                majority_rows.append(majority_row)
            
            return majority_rows
            
        except Exception as e:
            logger.error(f"Majority voting failed: {e}")
            return []
    
    def _majority_vote(self, values: List[Any], threshold: int) -> Any:
        """Apply majority voting for a list of values"""
        try:
            # Remove None/NaN values
            valid_values = [v for v in values if pd.notna(v)]
            
            if not valid_values:
                return None
            
            # Count occurrences
            from collections import Counter
            value_counts = Counter(valid_values)
            
            # Find value with majority
            for value, count in value_counts.most_common():
                if count >= threshold:
                    return value
            
            # If no majority, return most common
            return value_counts.most_common(1)[0][0]
            
        except Exception:
            return values[0] if values else None
    
    async def _validate_consensus_result(
        self, 
        consensus_df: pd.DataFrame, 
        metrics: List[Dict[str, Any]]
    ) -> pd.DataFrame:
        """Validate consensus ensemble result"""
        try:
            # Check for data quality issues
            consensus_df = await self._validate_data_quality(consensus_df)
            
            # Check for consistency issues
            consensus_df = await self._validate_data_consistency(consensus_df)
            
            # Check for completeness
            consensus_df = await self._validate_data_completeness(consensus_df)
            
            return consensus_df
            
        except Exception as e:
            logger.error(f"Consensus validation failed: {e}")
            return consensus_df
    
    async def _validate_weighted_result(
        self, 
        weighted_df: pd.DataFrame, 
        metrics: List[Dict[str, Any]], 
        weights: List[float]
    ) -> pd.DataFrame:
        """Validate weighted ensemble result"""
        try:
            # Check for data quality issues
            weighted_df = await self._validate_data_quality(weighted_df)
            
            # Check for consistency issues
            weighted_df = await self._validate_data_consistency(weighted_df)
            
            # Check for completeness
            weighted_df = await self._validate_data_completeness(weighted_df)
            
            return weighted_df
            
        except Exception as e:
            logger.error(f"Weighted validation failed: {e}")
            return weighted_df
    
    async def _validate_majority_result(
        self, 
        majority_df: pd.DataFrame, 
        metrics: List[Dict[str, Any]]
    ) -> pd.DataFrame:
        """Validate majority ensemble result"""
        try:
            # Check for data quality issues
            majority_df = await self._validate_data_quality(majority_df)
            
            # Check for consistency issues
            majority_df = await self._validate_data_consistency(majority_df)
            
            # Check for completeness
            majority_df = await self._validate_data_completeness(majority_df)
            
            return majority_df
            
        except Exception as e:
            logger.error(f"Majority validation failed: {e}")
            return majority_df
    
    async def _validate_data_quality(self, df: pd.DataFrame) -> pd.DataFrame:
        """Validate data quality of ensemble result"""
        try:
            validated_df = df.copy()
            
            # Check for extreme outliers
            for col in validated_df.columns:
                if pd.api.types.is_numeric_dtype(validated_df[col]):
                    # Remove extreme outliers (beyond 3 standard deviations)
                    mean_val = validated_df[col].mean()
                    std_val = validated_df[col].std()
                    lower_bound = mean_val - 3 * std_val
                    upper_bound = mean_val + 3 * std_val
                    
                    validated_df[col] = validated_df[col].clip(lower_bound, upper_bound)
            
            return validated_df
            
        except Exception as e:
            logger.error(f"Data quality validation failed: {e}")
            return df
    
    async def _validate_data_consistency(self, df: pd.DataFrame) -> pd.DataFrame:
        """Validate data consistency of ensemble result"""
        try:
            validated_df = df.copy()
            
            # Check for logical inconsistencies
            if "age" in validated_df.columns and "birth_date" in validated_df.columns:
                # Ensure age and birth date are consistent
                current_year = datetime.now().year
                birth_years = pd.to_datetime(validated_df["birth_date"]).dt.year
                expected_age = current_year - birth_years
                
                # Update age if difference is significant
                age_diff = np.abs(validated_df["age"] - expected_age)
                validated_df.loc[age_diff > 5, "age"] = expected_age[age_diff > 5]
            
            return validated_df
            
        except Exception as e:
            logger.error(f"Data consistency validation failed: {e}")
            return df
    
    async def _validate_data_completeness(self, df: pd.DataFrame) -> pd.DataFrame:
        """Validate data completeness of ensemble result"""
        try:
            validated_df = df.copy()
            
            # Fill missing values with appropriate defaults
            for col in validated_df.columns:
                if validated_df[col].isnull().any():
                    if pd.api.types.is_numeric_dtype(validated_df[col]):
                        validated_df[col] = validated_df[col].fillna(validated_df[col].median())
                    elif pd.api.types.is_string_dtype(validated_df[col]):
                        validated_df[col] = validated_df[col].fillna("Unknown")
                    else:
                        validated_df[col] = validated_df[col].fillna(method='ffill')
            
            return validated_df
            
        except Exception as e:
            logger.error(f"Data completeness validation failed: {e}")
            return df
    
    def _get_best_individual_result(self, results: List[Tuple[pd.DataFrame, Dict[str, Any]]]) -> pd.DataFrame:
        """Get the best individual result when ensemble fails"""
        try:
            if not results:
                raise ValueError("No results available")
            
            # Find result with highest quality score
            best_result = max(results, key=lambda x: x[1].get("overall_quality", 0))
            return best_result[0]
            
        except Exception as e:
            logger.error(f"Best individual result selection failed: {e}")
            return pd.DataFrame()
    
    async def _calculate_ensemble_metrics(self, results: List[Tuple[pd.DataFrame, Dict[str, Any]]]) -> Dict[str, Any]:
        """Calculate comprehensive ensemble metrics"""
        try:
            metrics = {
                "ensemble_type": "consensus",  # or "weighted", "majority"
                "model_count": len(results),
                "individual_qualities": [],
                "ensemble_quality": 0.0,
                "agreement_rate": 0.0,
                "diversity_score": 0.0,
                "robustness_score": 0.0
            }
            
            # Extract individual qualities
            for result in results:
                quality = result[1].get("overall_quality", 0.5)
                metrics["individual_qualities"].append(quality)
            
            # Calculate ensemble quality (average of individual qualities)
            if metrics["individual_qualities"]:
                metrics["ensemble_quality"] = np.mean(metrics["individual_qualities"])
            
            # Calculate agreement rate (placeholder)
            metrics["agreement_rate"] = 0.85
            
            # Calculate diversity score (placeholder)
            metrics["diversity_score"] = 0.75
            
            # Calculate robustness score (placeholder)
            metrics["robustness_score"] = 0.90
            
            return metrics
            
        except Exception as e:
            logger.error(f"Ensemble metrics calculation failed: {e}")
            return {"ensemble_quality": 0.5}
    
    async def _run_custom_model_inference(
        self,
        custom_model: Dict[str, Any],
        dataset: Dataset,
        config: GenerationConfig
    ) -> pd.DataFrame:
        """Run inference using custom trained model"""
        try:
            logger.info(f"Running custom model inference: {custom_model.get('name', 'unknown')}")
            
            # Load model architecture and weights
            model_architecture = custom_model.get("architecture")
            model_weights = custom_model.get("weights")
            
            # Prepare input data
            input_data = await self._prepare_custom_model_input(dataset, config)
            
            # Run inference
            synthetic_data = await self._execute_custom_model_inference(
                model_architecture, model_weights, input_data, config
            )
            
            # Post-process results
            synthetic_data = await self._post_process_custom_model_output(
                synthetic_data, dataset, config
            )
            
            return synthetic_data
            
        except Exception as e:
            logger.error(f"Custom model inference failed: {e}")
            raise
    
    async def _prepare_custom_model_input(
        self, 
        dataset: Dataset, 
        config: GenerationConfig
    ) -> Dict[str, Any]:
        """Prepare input data for custom model"""
        try:
            input_data = {
                "schema": [],
                "statistics": {},
                "constraints": {},
                "generation_config": {
                    "rows": config.rows,
                    "privacy_level": config.privacy_level,
                    "quality_threshold": config.quality_threshold
                }
            }
            
            # Prepare schema information
            for col in dataset.columns:
                col_info = {
                    "name": col.name,
                    "type": col.data_type.value,
                    "unique_values": col.unique_values,
                    "null_count": col.null_count,
                    "privacy_category": col.privacy_category,
                    "constraints": col.constraints or {}
                }
                input_data["schema"].append(col_info)
            
            # Prepare statistical information
            for col in dataset.columns:
                if col.data_type.value in ["integer", "float"]:
                    input_data["statistics"][col.name] = {
                        "mean": getattr(col, 'mean_value', 0),
                        "std": getattr(col, 'std_value', 1),
                        "min": getattr(col, 'min_value', 0),
                        "max": getattr(col, 'max_value', 100)
                    }
            
            return input_data
            
        except Exception as e:
            logger.error(f"Custom model input preparation failed: {e}")
            return {}
    
    async def _execute_custom_model_inference(
        self,
        model_architecture: Dict[str, Any],
        model_weights: Dict[str, Any],
        input_data: Dict[str, Any],
        config: GenerationConfig
    ) -> pd.DataFrame:
        """Execute custom model inference"""
        try:
            # This would load and run the actual custom model
            # For now, generate synthetic data using statistical methods
            
            synthetic_data = []
            n_rows = config.rows
            
            for i in range(n_rows):
                row_data = {}
                
                for col_info in input_data["schema"]:
                    col_name = col_info["name"]
                    col_type = col_info["type"]
                    
                    if col_type in ["integer", "float"]:
                        # Generate numeric value based on statistics
                        stats = input_data["statistics"].get(col_name, {})
                        mean_val = stats.get("mean", 50)
                        std_val = stats.get("std", 10)
                        min_val = stats.get("min", 0)
                        max_val = stats.get("max", 100)
                        
                        # Generate value within range
                        value = np.random.normal(mean_val, std_val)
                        value = np.clip(value, min_val, max_val)
                        row_data[col_name] = value
                    
                    elif col_type == "string":
                        # Generate categorical value
                        unique_count = col_info.get("unique_values", 10)
                        value = f"category_{np.random.randint(0, unique_count)}"
                        row_data[col_name] = value
                    
                    elif col_type == "date":
                        # Generate date value
                        start_date = datetime.now() - timedelta(days=365)
                        end_date = datetime.now()
                        days_between = (end_date - start_date).days
                        random_days = np.random.randint(0, days_between)
                        value = start_date + timedelta(days=random_days)
                        row_data[col_name] = value
                    
                    elif col_type == "boolean":
                        # Generate boolean value
                        row_data[col_name] = np.random.choice([True, False])
                    
                    else:
                        row_data[col_name] = f"unknown_type_{i}"
                
                synthetic_data.append(row_data)
            
            return pd.DataFrame(synthetic_data)
            
        except Exception as e:
            logger.error(f"Custom model inference execution failed: {e}")
            raise
    
    async def _post_process_custom_model_output(
        self,
        synthetic_data: pd.DataFrame,
        dataset: Dataset,
        config: GenerationConfig
    ) -> pd.DataFrame:
        """Post-process custom model output"""
        try:
            processed_data = synthetic_data.copy()
            
            # Apply privacy protection
            if config.privacy_level in ["high", "medium"]:
                processed_data = await self._apply_custom_model_privacy_protection(
                    processed_data, dataset, config
                )
            
            # Apply quality constraints
            processed_data = await self._apply_custom_model_quality_constraints(
                processed_data, dataset, config
            )
            
            # Apply business rules
            if config.business_rules:
                processed_data = await self._apply_custom_model_business_rules(
                    processed_data, config.business_rules
                )
            
            return processed_data
            
        except Exception as e:
            logger.error(f"Custom model output post-processing failed: {e}")
            return synthetic_data
    
    async def _apply_custom_model_privacy_protection(
        self,
        data: pd.DataFrame,
        dataset: Dataset,
        config: GenerationConfig
    ) -> pd.DataFrame:
        """Apply privacy protection to custom model output"""
        try:
            protected_data = data.copy()
            
            # Identify sensitive columns
            sensitive_columns = []
            for col in dataset.columns:
                if col.privacy_category in ["sensitive", "personal"]:
                    sensitive_columns.append(col.name)
            
            # Apply privacy protection
            for col_name in sensitive_columns:
                if col_name in protected_data.columns:
                    if config.privacy_level == "high":
                        # High privacy: mask or anonymize
                        protected_data[col_name] = f"ANONYMIZED_{np.random.randint(1000, 9999)}"
                    elif config.privacy_level == "medium":
                        # Medium privacy: add noise
                        if pd.api.types.is_numeric_dtype(protected_data[col_name]):
                            noise = np.random.normal(0, protected_data[col_name].std() * 0.1)
                            protected_data[col_name] = protected_data[col_name] + noise
            
            return protected_data
            
        except Exception as e:
            logger.error(f"Custom model privacy protection failed: {e}")
            return data
    
    async def _apply_custom_model_quality_constraints(
        self,
        data: pd.DataFrame,
        dataset: Dataset,
        config: GenerationConfig
    ) -> pd.DataFrame:
        """Apply quality constraints to custom model output"""
        try:
            constrained_data = data.copy()
            
            # Apply constraints based on original dataset
            for col in dataset.columns:
                if col.name in constrained_data.columns:
                    # Apply range constraints
                    if hasattr(col, 'min_value') and hasattr(col, 'max_value'):
                        constrained_data[col.name] = constrained_data[col.name].clip(
                            col.min_value, col.max_value
                        )
                    
                    # Apply type constraints
                    if col.data_type.value == "integer":
                        constrained_data[col.name] = constrained_data[col.name].astype(int)
                    elif col.data_type.value == "float":
                        constrained_data[col.name] = constrained_data[col.name].astype(float)
            
            return constrained_data
            
        except Exception as e:
            logger.error(f"Custom model quality constraints failed: {e}")
            return data
    
    async def _apply_custom_model_business_rules(
        self,
        data: pd.DataFrame,
        business_rules: List[str]
    ) -> pd.DataFrame:
        """Apply business rules to custom model output"""
        try:
            ruled_data = data.copy()
            
            # Apply business rules
            for rule in business_rules:
                ruled_data = await self._apply_single_business_rule(ruled_data, rule)
            
            return ruled_data
            
        except Exception as e:
            logger.error(f"Custom model business rules failed: {e}")
            return data
    
    async def _apply_single_business_rule(self, data: pd.DataFrame, rule: str) -> pd.DataFrame:
        """Apply a single business rule"""
        try:
            ruled_data = data.copy()
            
            # Example business rule applications
            if "age" in rule.lower() and "age" in ruled_data.columns:
                # Ensure age is reasonable
                ruled_data["age"] = ruled_data["age"].clip(0, 120)
            
            if "income" in rule.lower() and "income" in ruled_data.columns:
                # Ensure income is positive
                ruled_data["income"] = ruled_data["income"].clip(0, None)
            
            return ruled_data
            
        except Exception as e:
            logger.error(f"Business rule application failed: {e}")
            return data
    
    async def _assess_custom_model_quality(
        self,
        dataset: Dataset,
        synthetic_data: pd.DataFrame,
        custom_model: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Assess quality of custom model output"""
        try:
            quality_metrics = {
                "overall_quality": 0.0,
                "statistical_similarity": 0.0,
                "distribution_fidelity": 0.0,
                "privacy_protection": 0.0,
                "business_rule_compliance": 0.0,
                "model_specific_metrics": {}
            }
            
            # Calculate statistical similarity
            quality_metrics["statistical_similarity"] = await self._calculate_custom_statistical_similarity(
                dataset, synthetic_data
            )
            
            # Calculate distribution fidelity
            quality_metrics["distribution_fidelity"] = await self._calculate_custom_distribution_fidelity(
                dataset, synthetic_data
            )
            
            # Calculate privacy protection
            quality_metrics["privacy_protection"] = await self._calculate_custom_privacy_protection(
                synthetic_data
            )
            
            # Calculate business rule compliance
            quality_metrics["business_rule_compliance"] = await self._calculate_custom_business_compliance(
                synthetic_data
            )
            
            # Calculate overall quality
            weights = [0.3, 0.25, 0.25, 0.2]
            scores = [
                quality_metrics["statistical_similarity"],
                quality_metrics["distribution_fidelity"],
                quality_metrics["privacy_protection"],
                quality_metrics["business_rule_compliance"]
            ]
            
            quality_metrics["overall_quality"] = np.average(scores, weights=weights)
            
            return quality_metrics
            
        except Exception as e:
            logger.error(f"Custom model quality assessment failed: {e}")
            return {"overall_quality": 0.5}
    
    async def _calculate_custom_statistical_similarity(
        self,
        dataset: Dataset,
        synthetic_data: pd.DataFrame
    ) -> float:
        """Calculate statistical similarity for custom model output"""
        try:
            # This would calculate actual statistical similarity
            # For now, return a placeholder score
            return 0.85
            
        except Exception as e:
            logger.error(f"Custom statistical similarity calculation failed: {e}")
            return 0.5
    
    async def _calculate_custom_distribution_fidelity(
        self,
        dataset: Dataset,
        synthetic_data: pd.DataFrame
    ) -> float:
        """Calculate distribution fidelity for custom model output"""
        try:
            # This would calculate actual distribution fidelity
            # For now, return a placeholder score
            return 0.80
            
        except Exception as e:
            logger.error(f"Custom distribution fidelity calculation failed: {e}")
            return 0.5
    
    async def _calculate_custom_privacy_protection(
        self,
        synthetic_data: pd.DataFrame
    ) -> float:
        """Calculate privacy protection for custom model output"""
        try:
            # This would calculate actual privacy protection
            # For now, return a placeholder score
            return 0.90
            
        except Exception as e:
            logger.error(f"Custom privacy protection calculation failed: {e}")
            return 0.5
    
    async def _calculate_custom_business_compliance(
        self,
        synthetic_data: pd.DataFrame
    ) -> float:
        """Calculate business rule compliance for custom model output"""
        try:
            # This would calculate actual business rule compliance
            # For now, return a placeholder score
            return 0.85
            
        except Exception as e:
            logger.error(f"Custom business compliance calculation failed: {e}")
            return 0.5 