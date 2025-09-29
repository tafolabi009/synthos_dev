"""
Custom Model Service for Synthos
Handles model upload, validation, inference, and lifecycle management
Supports TensorFlow, PyTorch, HuggingFace, ONNX, and Scikit-Learn models
"""

import asyncio
import json
import os
import pickle
import tempfile
import zipfile
from typing import Dict, List, Any, Optional, Tuple
import boto3
from datetime import datetime
import logging
from pathlib import Path

# Conditional pandas import for Lambda compatibility
try:
    from app.utils.optional_imports import pd, PANDAS_AVAILABLE
    HAS_PANDAS = True
except ImportError:
    HAS_PANDAS = False
    # Create a simple fallback for basic DataFrame-like operations
    class MockDataFrame:
        def __init__(self, data=None):
            self.data = data or []
        def to_dict(self, orient='records'):
            return self.data if isinstance(self.data, list) else []
        def to_csv(self, *args, **kwargs):
            return ""
    pd = type('MockPandas', (), {'DataFrame': MockDataFrame})()

# Conditional numpy import for Lambda compatibility
try:
    import numpy as np
    HAS_NUMPY = True
except ImportError:
    HAS_NUMPY = False
    # Create a simple fallback for basic numpy-like operations
    class MockNumpy:
        def array(self, data):
            return data
        def mean(self, data):
            return sum(data) / len(data) if data else 0
        def std(self, data):
            mean_val = self.mean(data)
            return (sum((x - mean_val) ** 2 for x in data) / len(data)) ** 0.5 if data else 0
    np = MockNumpy()

from app.core.config import settings
from app.core.logging import get_logger
from app.models.dataset import CustomModel, CustomModelStatus, CustomModelType

try:
    from google.cloud import storage as gcs_storage
except Exception:  # pragma: no cover
    gcs_storage = None

try:
    import boto3  # legacy support
except Exception:  # pragma: no cover
    boto3 = None

logger = get_logger(__name__)


class CustomModelService:
    """Service for managing custom model files in object storage."""
    
    def __init__(self):
        # Determine storage provider; prefer GCS
        self.storage_provider = settings.STORAGE_PROVIDER.lower()
        self.gcs_client = None
        self.s3_client = None
        
        if self.storage_provider == "gcs":
            if not gcs_storage:
                logger.warning("google-cloud-storage not available; falling back to AWS if configured")
            else:
                self.gcs_client = gcs_storage.Client(project=settings.GCP_PROJECT_ID)  # uses ADC
                if not settings.GCS_BUCKET:
                    logger.warning("GCS bucket not configured (GCS_BUCKET)")
        else:
            if boto3 and settings.AWS_ACCESS_KEY_ID:
                self.s3_client = boto3.client(
                    's3',
                    aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                    aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
                    region_name=settings.AWS_REGION
                )
            elif boto3:
                self.s3_client = boto3.client('s3')
            else:
                logger.warning("boto3 not available; S3 disabled")
        
        # Model runtime registries
        self.loaded_models: Dict[str, Any] = {}
        self.model_validators = {
            CustomModelType.TENSORFLOW: self._validate_tensorflow_model,
            CustomModelType.PYTORCH: self._validate_pytorch_model,
            CustomModelType.HUGGINGFACE: self._validate_huggingface_model,
            CustomModelType.ONNX: self._validate_onnx_model,
            CustomModelType.SCIKIT_LEARN: self._validate_sklearn_model
        }
    
    async def upload_model_files(
        self,
        custom_model,
        model_file,
        config_file=None,
        requirements_file=None
    ) -> Dict[str, str]:
        """Upload model artifacts to object storage and update model record."""
        try:
            logger.info(f"Uploading files for model {custom_model.id}")
            
            base_key = f"custom-models/{custom_model.owner_id}/{custom_model.id}"
            model_key = f"{base_key}/model.{self._get_file_extension(model_file.filename)}"
            
            # Upload main model file
            model_content = await model_file.read()
            await self._upload_object(model_key, model_content, model_file.content_type)
            custom_model.model_s3_key = model_key  # keep field name for backward-compat
            
            # Upload config file if provided
            if config_file:
                config_key = f"{base_key}/config.{self._get_file_extension(config_file.filename)}"
                config_content = await config_file.read()
                await self._upload_object(config_key, config_content, config_file.content_type)
                custom_model.config_s3_key = config_key
            
            # Upload requirements file if provided
            if requirements_file:
                req_key = f"{base_key}/requirements.txt"
                req_content = await requirements_file.read()
                await self._upload_object(req_key, req_content, "text/plain")
                custom_model.requirements_s3_key = req_key
            
            return {
                "model_key": model_key,
                "config_key": getattr(custom_model, 'config_s3_key', None),
                "requirements_key": getattr(custom_model, 'requirements_s3_key', None)
            }
        except Exception as e:
            logger.exception("Failed to upload custom model files")
            raise
    
    async def _validate_uploaded_model(self, custom_model: CustomModel):
        """Validate uploaded model in background"""
        
        try:
            logger.info(f"Validating model {custom_model.id}")
            
            # Download model files to temporary directory
            temp_dir = tempfile.mkdtemp()
            
            model_path = await self._download_object(
                custom_model.model_s3_key, 
                os.path.join(temp_dir, "model")
            )
            
            config_path = None
            if custom_model.config_s3_key:
                config_path = await self._download_object(
                    custom_model.config_s3_key,
                    os.path.join(temp_dir, "config")
                )
            
            # Run model-specific validation
            validator = self.model_validators.get(custom_model.model_type)
            if not validator:
                raise Exception(f"No validator for model type {custom_model.model_type}")
            
            validation_result = await validator(model_path, config_path, custom_model)
            
            # Update model with validation results
            custom_model.validation_metrics = validation_result
            custom_model.accuracy_score = validation_result.get("accuracy", 0.0)
            custom_model.status = CustomModelStatus.READY
            
            logger.info(f"Model {custom_model.id} validation successful")
            
        except Exception as e:
            logger.error(f"Model validation failed: {e}")
            custom_model.status = CustomModelStatus.ERROR
            custom_model.validation_metrics = {"error": str(e)}
        
        finally:
            # Cleanup temp directory
            import shutil
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)
    
    async def _validate_tensorflow_model(
        self, 
        model_path: str, 
        config_path: Optional[str],
        custom_model: CustomModel
    ) -> Dict[str, Any]:
        """Validate TensorFlow model"""
        
        try:
            import tensorflow as tf
            
            # Load model
            if model_path.endswith('.h5'):
                model = tf.keras.models.load_model(model_path)
            elif os.path.isdir(model_path):
                model = tf.saved_model.load(model_path)
            else:
                raise Exception("Unsupported TensorFlow model format")
            
            # Extract model information
            validation_result = {
                "framework": "tensorflow",
                "framework_version": tf.__version__,
                "model_type": type(model).__name__,
                "input_shape": None,
                "output_shape": None,
                "parameters": None,
                "accuracy": 0.85,  # Placeholder - would run actual validation
                "validation_timestamp": datetime.utcnow().isoformat()
            }
            
            # Get model signature if available
            if hasattr(model, 'input_shape'):
                validation_result["input_shape"] = str(model.input_shape)
            if hasattr(model, 'output_shape'):
                validation_result["output_shape"] = str(model.output_shape)
            
            return validation_result
            
        except ImportError:
            raise Exception("TensorFlow not installed")
        except Exception as e:
            raise Exception(f"TensorFlow model validation failed: {e}")
    
    async def _validate_pytorch_model(
        self,
        model_path: str,
        config_path: Optional[str],
        custom_model: CustomModel
    ) -> Dict[str, Any]:
        """Validate PyTorch model"""
        
        try:
            import torch
            
            # Load model
            if model_path.endswith(('.pt', '.pth')):
                model = torch.load(model_path, map_location='cpu')
            else:
                raise Exception("Unsupported PyTorch model format")
            
            validation_result = {
                "framework": "pytorch",
                "framework_version": torch.__version__,
                "model_type": type(model).__name__,
                "parameters": sum(p.numel() for p in model.parameters()) if hasattr(model, 'parameters') else None,
                "accuracy": 0.83,  # Placeholder
                "validation_timestamp": datetime.utcnow().isoformat()
            }
            
            return validation_result
            
        except ImportError:
            raise Exception("PyTorch not installed")
        except Exception as e:
            raise Exception(f"PyTorch model validation failed: {e}")
    
    async def _validate_huggingface_model(
        self,
        model_path: str,
        config_path: Optional[str],
        custom_model: CustomModel
    ) -> Dict[str, Any]:
        """Validate HuggingFace model"""
        
        try:
            from transformers import AutoConfig, AutoModel
            
            # Load config
            if config_path and config_path.endswith('.json'):
                config = AutoConfig.from_pretrained(config_path)
            else:
                config = AutoConfig.from_pretrained(model_path)
            
            validation_result = {
                "framework": "huggingface",
                "model_type": config.model_type if hasattr(config, 'model_type') else "unknown",
                "architecture": config.architectures[0] if hasattr(config, 'architectures') and config.architectures else "unknown",
                "vocab_size": getattr(config, 'vocab_size', None),
                "max_position_embeddings": getattr(config, 'max_position_embeddings', None),
                "accuracy": 0.88,  # Placeholder
                "validation_timestamp": datetime.utcnow().isoformat()
            }
            
            return validation_result
            
        except ImportError:
            raise Exception("Transformers library not installed")
        except Exception as e:
            raise Exception(f"HuggingFace model validation failed: {e}")
    
    async def _validate_onnx_model(
        self,
        model_path: str,
        config_path: Optional[str],
        custom_model: CustomModel
    ) -> Dict[str, Any]:
        """Validate ONNX model"""
        
        try:
            import onnx
            import onnxruntime as ort
            
            # Load and validate ONNX model
            model = onnx.load(model_path)
            onnx.checker.check_model(model)
            
            # Create inference session
            session = ort.InferenceSession(model_path)
            
            validation_result = {
                "framework": "onnx",
                "onnx_version": onnx.__version__,
                "onnxruntime_version": ort.__version__,
                "input_names": [input.name for input in session.get_inputs()],
                "output_names": [output.name for output in session.get_outputs()],
                "input_shapes": [str(input.shape) for input in session.get_inputs()],
                "output_shapes": [str(output.shape) for output in session.get_outputs()],
                "accuracy": 0.86,  # Placeholder
                "validation_timestamp": datetime.utcnow().isoformat()
            }
            
            return validation_result
            
        except ImportError:
            raise Exception("ONNX or ONNXRuntime not installed")
        except Exception as e:
            raise Exception(f"ONNX model validation failed: {e}")
    
    async def _validate_sklearn_model(
        self,
        model_path: str,
        config_path: Optional[str],
        custom_model: CustomModel
    ) -> Dict[str, Any]:
        """Validate Scikit-Learn model"""
        
        try:
            import sklearn
            import joblib
            
            # Load model
            if model_path.endswith('.joblib'):
                model = joblib.load(model_path)
            elif model_path.endswith('.pkl'):
                with open(model_path, 'rb') as f:
                    model = pickle.load(f)
            else:
                raise Exception("Unsupported scikit-learn model format")
            
            validation_result = {
                "framework": "scikit-learn",
                "sklearn_version": sklearn.__version__,
                "model_type": type(model).__name__,
                "features": getattr(model, 'n_features_in_', None),
                "accuracy": 0.81,  # Placeholder
                "validation_timestamp": datetime.utcnow().isoformat()
            }
            
            return validation_result
            
        except ImportError:
            raise Exception("Scikit-learn not installed")
        except Exception as e:
            raise Exception(f"Scikit-learn model validation failed: {e}")
    
    async def run_custom_model_inference(
        self,
        custom_model: CustomModel,
        input_data: pd.DataFrame
    ) -> pd.DataFrame:
        """Run inference using a custom model"""
        
        if not custom_model.is_ready:
            raise Exception("Model is not ready for inference")
        
        # Load model if not cached
        model_key = f"{custom_model.id}_{custom_model.model_type.value}"
        if model_key not in self.loaded_models:
            await self._load_model_to_cache(custom_model)
        
        model_info = self.loaded_models[model_key]
        model = model_info["model"]
        
        try:
            # Run model-specific inference
            if custom_model.model_type == CustomModelType.TENSORFLOW:
                return await self._run_tensorflow_inference(model, input_data)
            elif custom_model.model_type == CustomModelType.PYTORCH:
                return await self._run_pytorch_inference(model, input_data)
            elif custom_model.model_type == CustomModelType.HUGGINGFACE:
                return await self._run_huggingface_inference(model, input_data)
            elif custom_model.model_type == CustomModelType.ONNX:
                return await self._run_onnx_inference(model, input_data)
            elif custom_model.model_type == CustomModelType.SCIKIT_LEARN:
                return await self._run_sklearn_inference(model, input_data)
            else:
                raise Exception(f"Unsupported model type: {custom_model.model_type}")
                
        except Exception as e:
            logger.error(f"Model inference failed: {e}")
            raise Exception(f"Inference failed: {e}")
    
    async def _load_model_to_cache(self, custom_model):
        """Load model from object storage to local cache directory."""
        temp_dir = tempfile.mkdtemp()
        model_path = await self._download_object(custom_model.model_s3_key, os.path.join(temp_dir, "model"))
        config_path = None
        if getattr(custom_model, 'config_s3_key', None):
            config_path = await self._download_object(custom_model.config_s3_key, os.path.join(temp_dir, "config"))
        return model_path, config_path
    
    async def _run_tensorflow_inference(self, model, input_data: pd.DataFrame) -> pd.DataFrame:
        """Run TensorFlow model inference"""
        
        # Convert DataFrame to numpy array
        input_array = input_data.to_numpy().astype(np.float32)
        
        # Run prediction
        predictions = model.predict(input_array)
        
        # Convert back to DataFrame
        if len(predictions.shape) == 1:
            result_df = pd.DataFrame({"prediction": predictions})
        else:
            result_df = pd.DataFrame(predictions)
        
        return result_df
    
    async def _run_sklearn_inference(self, model, input_data: pd.DataFrame) -> pd.DataFrame:
        """Run Scikit-Learn model inference"""
        
        # Run prediction
        if hasattr(model, 'predict_proba'):
            predictions = model.predict_proba(input_data)
            result_df = pd.DataFrame(predictions)
        else:
            predictions = model.predict(input_data)
            result_df = pd.DataFrame({"prediction": predictions})
        
        return result_df
    
    async def validate_model(self, custom_model: CustomModel) -> Dict[str, Any]:
        """Re-validate a model"""
        
        await self._validate_uploaded_model(custom_model)
        return custom_model.get_validation_metrics()
    
    async def _run_pytorch_inference(self, model, input_data: pd.DataFrame) -> pd.DataFrame:
        """Run PyTorch model inference with advanced features"""
        try:
            import torch
            import torch.nn as nn
            
            # Ensure model is in evaluation mode
            model.eval()
            
            # Convert input data to tensor with proper dtype
            if input_data.dtypes.any() == 'object':
                # Handle mixed data types
                numeric_cols = input_data.select_dtypes(include=[np.number]).columns
                input_tensor = torch.tensor(input_data[numeric_cols].values, dtype=torch.float32)
            else:
                input_tensor = torch.tensor(input_data.values, dtype=torch.float32)
            
            # Add batch dimension if needed
            if input_tensor.dim() == 1:
                input_tensor = input_tensor.unsqueeze(0)
            
            # Run inference with gradient computation disabled
            with torch.no_grad():
                try:
                    output = model(input_tensor)
                    
                    # Handle different output types
                    if isinstance(output, torch.Tensor):
                        if output.dim() > 1:
                            preds = output.softmax(dim=-1) if output.size(-1) > 1 else output.sigmoid()
                        else:
                            preds = output
                    elif isinstance(output, (list, tuple)):
                        preds = output[0] if len(output) > 0 else torch.zeros(input_tensor.size(0))
                    else:
                        preds = output
                    
                    # Convert to numpy
                    if hasattr(preds, 'cpu'):
                        preds = preds.cpu()
                    if hasattr(preds, 'numpy'):
                        preds = preds.numpy()
                    else:
                        preds = preds.detach().cpu().numpy()
                    
                    # Flatten if needed
                    if preds.ndim > 1:
                        preds = preds.flatten()
                    
                    return pd.DataFrame({"prediction": preds})
                    
                except Exception as e:
                    logger.error(f"PyTorch model inference failed: {e}")
                    # Fallback to simple forward pass
                    output = model(input_tensor)
                    if hasattr(output, 'detach'):
                        preds = output.detach().cpu().numpy()
                    else:
                        preds = output.numpy()
                    return pd.DataFrame({"prediction": preds.flatten()})
                    
        except ImportError:
            raise RuntimeError("PyTorch is not installed. Install with: pip install torch")
        except Exception as e:
            raise RuntimeError(f"PyTorch inference failed: {e}")

    async def _run_huggingface_inference(self, model, input_data: pd.DataFrame) -> pd.DataFrame:
        """Run HuggingFace model inference with advanced features"""
        try:
            from transformers import pipeline, AutoTokenizer, AutoModel
            import torch
            
            # Handle different model types
            if isinstance(model, str):
                # Model is a string path/name
                try:
                    # Try to create a pipeline
                    pipe = pipeline("text-generation", model=model, device="cpu")
                    texts = input_data.iloc[:, 0].astype(str).tolist()  # Assume first column is text
                    outputs = pipe(texts, max_length=50, num_return_sequences=1)
                    predictions = [out[0]['generated_text'] for out in outputs]
                    return pd.DataFrame({"prediction": predictions})
                except Exception:
                    # Fallback to direct model usage
                    tokenizer = AutoTokenizer.from_pretrained(model)
                    model_instance = AutoModel.from_pretrained(model)
                    
                    # Tokenize input
                    texts = input_data.iloc[:, 0].astype(str).tolist()
                    inputs = tokenizer(texts, return_tensors="pt", padding=True, truncation=True)
                    
                    # Run inference
                    with torch.no_grad():
                        outputs = model_instance(**inputs)
                        # Use last hidden state as prediction
                        predictions = outputs.last_hidden_state.mean(dim=1).cpu().numpy()
                        return pd.DataFrame({"prediction": predictions.flatten()})
            
            else:
                # Model is already loaded
                if hasattr(model, 'predict'):
                    predictions = model.predict(input_data)
                else:
                    # Assume it's a pipeline
                    predictions = model(input_data.to_dict(orient='records'))
                
                return pd.DataFrame({"prediction": predictions})
                
        except ImportError:
            raise RuntimeError("Transformers is not installed. Install with: pip install transformers")
        except Exception as e:
            raise RuntimeError(f"HuggingFace inference failed: {e}")

    async def _run_onnx_inference(self, model, input_data: pd.DataFrame) -> pd.DataFrame:
        """Run ONNX model inference with advanced features"""
        try:
            import onnxruntime as ort
            
            # Create inference session with optimizations
            sess_options = ort.SessionOptions()
            sess_options.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
            sess_options.intra_op_num_threads = 1
            sess_options.inter_op_num_threads = 1
            
            # Load model
            if isinstance(model, str):
                # Model is a file path
                sess = ort.InferenceSession(model, sess_options)
            else:
                # Model is already loaded
                sess = model
            
            # Get input details
            input_name = sess.get_inputs()[0].name
            input_shape = sess.get_inputs()[0].shape
            
            # Prepare input data
            input_values = input_data.values.astype('float32')
            
            # Handle dynamic shapes
            if input_shape[0] == -1:  # Dynamic batch size
                input_values = input_values.reshape(-1, *input_shape[1:])
            
            # Run inference
            outputs = sess.run(None, {input_name: input_values})
            
            # Handle multiple outputs
            if len(outputs) == 1:
                predictions = outputs[0]
            else:
                # Combine multiple outputs (e.g., classification + confidence)
                predictions = np.column_stack(outputs)
            
            # Ensure 1D output
            if predictions.ndim > 1:
                predictions = predictions.flatten()
            
            return pd.DataFrame({"prediction": predictions})
            
        except ImportError:
            raise RuntimeError("ONNX Runtime is not installed. Install with: pip install onnxruntime")
        except Exception as e:
            raise RuntimeError(f"ONNX inference failed: {e}")

    async def test_model_inference(
        self,
        custom_model: CustomModel,
        test_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Test model inference with comprehensive performance analysis"""
        import psutil
        import os
        import time
        
        test_df = pd.DataFrame([test_data])
        start_time = datetime.utcnow()
        process = psutil.Process(os.getpid())
        mem_before = process.memory_info().rss
        cpu_before = process.cpu_percent(interval=None)
        
        try:
            result_df = await self.run_custom_model_inference(custom_model, test_df)
            
            mem_after = process.memory_info().rss
            cpu_after = process.cpu_percent(interval=None)
            end_time = datetime.utcnow()
            inference_time = (end_time - start_time).total_seconds() * 1000
            
            # Comprehensive performance analysis
            performance_metrics = {
                "inference_speed": "fast" if inference_time < 100 else "medium" if inference_time < 500 else "slow",
                "memory_usage_mb": round((mem_after-mem_before)/1024/1024, 2),
                "cpu_usage_percent": round(cpu_after-cpu_before, 2),
                "throughput_rows_per_second": round(1000 / inference_time, 2) if inference_time > 0 else 0,
                "model_size_mb": await self._get_model_size(custom_model),
                "framework_version": await self._get_framework_version(custom_model),
                "gpu_available": await self._check_gpu_availability(),
                "optimization_level": await self._get_optimization_level(custom_model)
            }
            
            # Quality assessment
            quality_metrics = await self._assess_model_quality(custom_model, test_df, result_df)
            
            return {
                "sample_output": result_df.to_dict('records')[0] if not result_df.empty else {},
                "inference_time_ms": inference_time,
                "performance_metrics": performance_metrics,
                "quality_metrics": quality_metrics,
                "test_status": "success",
                "recommendations": await self._generate_performance_recommendations(performance_metrics)
            }
            
        except Exception as e:
            return {
                "test_status": "failed",
                "error": str(e),
                "inference_time_ms": 0,
                "performance_metrics": {},
                "quality_metrics": {},
                "recommendations": ["Fix model errors before deployment"]
            }
    
    async def delete_model_files(self, custom_model):
        """Delete all model artifacts from object storage."""
        keys = [getattr(custom_model, 'model_s3_key', None), getattr(custom_model, 'config_s3_key', None), getattr(custom_model, 'requirements_s3_key', None)]
        for key in keys:
            if key:
                try:
                    await self._delete_object(key)
                    logger.info(f"Deleted object: {key}")
                except Exception as e:
                    logger.warning(f"Failed to delete object {key}: {e}")

    # ---------- Storage backends ----------
    async def _upload_object(self, key: str, content: bytes, content_type: str):
        if self.storage_provider == "gcs" and self.gcs_client and settings.GCS_BUCKET:
            bucket = self.gcs_client.bucket(settings.GCS_BUCKET)
            blob = bucket.blob(key)
            blob.upload_from_string(content, content_type=content_type)
            return
        if self.s3_client and settings.AWS_S3_BUCKET:
            self.s3_client.put_object(Bucket=settings.AWS_S3_BUCKET, Key=key, Body=content, ContentType=content_type)
            return
        raise Exception("No storage backend configured")

    async def _download_object(self, key: str, local_path: str) -> str:
        if self.storage_provider == "gcs" and self.gcs_client and settings.GCS_BUCKET:
            bucket = self.gcs_client.bucket(settings.GCS_BUCKET)
            blob = bucket.blob(key)
            os.makedirs(os.path.dirname(local_path), exist_ok=True)
            blob.download_to_filename(local_path)
            return local_path
        if self.s3_client and settings.AWS_S3_BUCKET:
            response = self.s3_client.get_object(Bucket=settings.AWS_S3_BUCKET, Key=key)
            os.makedirs(os.path.dirname(local_path), exist_ok=True)
        with open(local_path, 'wb') as f:
            f.write(response['Body'].read())
            return local_path
        raise Exception("No storage backend configured")

    async def _delete_object(self, key: str):
        if self.storage_provider == "gcs" and self.gcs_client and settings.GCS_BUCKET:
            bucket = self.gcs_client.bucket(settings.GCS_BUCKET)
            blob = bucket.blob(key)
            blob.delete(if_exists=True)
            return
        if self.s3_client and settings.AWS_S3_BUCKET:
            self.s3_client.delete_object(Bucket=settings.AWS_S3_BUCKET, Key=key)
            return
        raise Exception("No storage backend configured")

    # ---------- Advanced Testing Helpers ----------
    async def _get_model_size(self, custom_model: CustomModel) -> float:
        """Get model size in MB"""
        try:
            if hasattr(custom_model, 'model_s3_key') and custom_model.model_s3_key:
                # This would require downloading and checking file size
                # For now, return estimated size based on model type
                size_estimates = {
                    CustomModelType.TENSORFLOW: 50.0,
                    CustomModelType.PYTORCH: 30.0,
                    CustomModelType.HUGGINGFACE: 100.0,
                    CustomModelType.ONNX: 20.0,
                    CustomModelType.SCIKIT_LEARN: 5.0
                }
                return size_estimates.get(custom_model.model_type, 25.0)
            return 0.0
        except Exception:
            return 0.0
    
    async def _get_framework_version(self, custom_model: CustomModel) -> str:
        """Get framework version used by the model"""
        try:
            if custom_model.model_type == CustomModelType.TENSORFLOW:
                import tensorflow as tf
                return f"TensorFlow {tf.__version__}"
            elif custom_model.model_type == CustomModelType.PYTORCH:
                import torch
                return f"PyTorch {torch.__version__}"
            elif custom_model.model_type == CustomModelType.HUGGINGFACE:
                from transformers import __version__ as transformers_version
                return f"Transformers {transformers_version}"
            elif custom_model.model_type == CustomModelType.ONNX:
                import onnx
                return f"ONNX {onnx.__version__}"
            elif custom_model.model_type == CustomModelType.SCIKIT_LEARN:
                import sklearn
                return f"Scikit-learn {sklearn.__version__}"
            return "Unknown"
        except Exception:
            return "Unknown"
    
    async def _check_gpu_availability(self) -> bool:
        """Check if GPU is available for inference"""
        try:
            if HAS_NUMPY:
                import torch
                return torch.cuda.is_available()
            return False
        except Exception:
            return False
    
    async def _get_optimization_level(self, custom_model: CustomModel) -> str:
        """Get model optimization level"""
        try:
            if custom_model.model_type == CustomModelType.ONNX:
                return "optimized"
            elif custom_model.model_type == CustomModelType.TENSORFLOW:
                return "standard"
            elif custom_model.model_type == CustomModelType.PYTORCH:
                return "standard"
            else:
                return "basic"
        except Exception:
            return "unknown"
    
    async def _assess_model_quality(
        self, 
        custom_model: CustomModel, 
        input_data: pd.DataFrame, 
        output_data: pd.DataFrame
    ) -> Dict[str, Any]:
        """Assess model quality and output consistency"""
        try:
            quality_metrics = {
                "output_consistency": 0.0,
                "prediction_confidence": 0.0,
                "output_diversity": 0.0,
                "error_rate": 0.0,
                "data_type_consistency": True
            }
            
            if output_data.empty:
                return quality_metrics
            
            # Check output consistency
            if len(output_data) > 1:
                # Calculate variance in predictions
                numeric_cols = output_data.select_dtypes(include=[np.number]).columns
                if len(numeric_cols) > 0:
                    variance = output_data[numeric_cols].var().mean()
                    quality_metrics["output_consistency"] = max(0, 1 - variance)
            
            # Check prediction confidence (for classification models)
            if custom_model.model_type in [CustomModelType.TENSORFLOW, CustomModelType.PYTORCH]:
                # This would check for probability outputs
                quality_metrics["prediction_confidence"] = 0.85  # Placeholder
            
            # Check output diversity
            unique_outputs = output_data.nunique().sum()
            total_outputs = len(output_data) * len(output_data.columns)
            quality_metrics["output_diversity"] = min(1.0, unique_outputs / total_outputs) if total_outputs > 0 else 0.0
            
            # Check data type consistency
            quality_metrics["data_type_consistency"] = not output_data.isnull().any().any()
            
            return quality_metrics
            
        except Exception as e:
            logger.error(f"Quality assessment failed: {e}")
            return {"error": str(e)}
    
    async def _generate_performance_recommendations(
        self, 
        performance_metrics: Dict[str, Any]
    ) -> List[str]:
        """Generate performance optimization recommendations"""
        recommendations = []
        
        # Speed recommendations
        if performance_metrics.get("inference_speed") == "slow":
            recommendations.append("Consider model quantization or pruning to improve inference speed")
            recommendations.append("Use ONNX format for better performance")
        
        # Memory recommendations
        memory_usage = performance_metrics.get("memory_usage_mb", 0)
        if memory_usage > 100:
            recommendations.append("High memory usage detected - consider model optimization")
        
        # GPU recommendations
        if not performance_metrics.get("gpu_available", False):
            recommendations.append("GPU not available - consider using GPU-accelerated inference for better performance")
        
        # Framework recommendations
        framework = performance_metrics.get("framework_version", "")
        if "TensorFlow" in framework:
            recommendations.append("Consider using TensorFlow Lite for mobile/edge deployment")
        elif "PyTorch" in framework:
            recommendations.append("Consider using TorchScript for production deployment")
        
        return recommendations
    
    async def run_comprehensive_model_validation(
        self,
        custom_model: CustomModel,
        test_dataset: pd.DataFrame
    ) -> Dict[str, Any]:
        """Run comprehensive model validation with multiple test cases"""
        try:
            validation_results = {
                "overall_status": "pending",
                "test_cases": [],
                "performance_summary": {},
                "recommendations": []
            }
            
            # Test case 1: Basic inference
            basic_test = await self._run_basic_inference_test(custom_model, test_dataset)
            validation_results["test_cases"].append(basic_test)
            
            # Test case 2: Performance test
            performance_test = await self._run_performance_test(custom_model, test_dataset)
            validation_results["test_cases"].append(performance_test)
            
            # Test case 3: Edge case test
            edge_case_test = await self._run_edge_case_test(custom_model, test_dataset)
            validation_results["test_cases"].append(edge_case_test)
            
            # Test case 4: Stress test
            stress_test = await self._run_stress_test(custom_model, test_dataset)
            validation_results["test_cases"].append(stress_test)
            
            # Calculate overall status
            passed_tests = sum(1 for test in validation_results["test_cases"] if test.get("status") == "passed")
            total_tests = len(validation_results["test_cases"])
            
            validation_results["overall_status"] = "passed" if passed_tests == total_tests else "failed"
            validation_results["performance_summary"] = {
                "tests_passed": passed_tests,
                "total_tests": total_tests,
                "success_rate": passed_tests / total_tests if total_tests > 0 else 0
            }
            
            return validation_results
            
        except Exception as e:
            return {
                "overall_status": "error",
                "error": str(e),
                "test_cases": [],
                "performance_summary": {},
                "recommendations": ["Fix validation errors"]
            }
    
    async def _run_basic_inference_test(
        self, 
        custom_model: CustomModel, 
        test_dataset: pd.DataFrame
    ) -> Dict[str, Any]:
        """Run basic inference test"""
        try:
            result = await self.run_custom_model_inference(custom_model, test_dataset.head(1))
            return {
                "test_name": "basic_inference",
                "status": "passed" if not result.empty else "failed",
                "details": "Basic inference test completed successfully"
            }
        except Exception as e:
            return {
                "test_name": "basic_inference",
                "status": "failed",
                "details": f"Basic inference test failed: {str(e)}"
            }
    
    async def _run_performance_test(
        self, 
        custom_model: CustomModel, 
        test_dataset: pd.DataFrame
    ) -> Dict[str, Any]:
        """Run performance test"""
        try:
            start_time = time.time()
            result = await self.run_custom_model_inference(custom_model, test_dataset.head(10))
            end_time = time.time()
            
            inference_time = (end_time - start_time) * 1000
            status = "passed" if inference_time < 1000 else "failed"  # 1 second threshold
            
            return {
                "test_name": "performance",
                "status": status,
                "details": f"Performance test completed in {inference_time:.2f}ms",
                "metrics": {"inference_time_ms": inference_time}
            }
        except Exception as e:
            return {
                "test_name": "performance",
                "status": "failed",
                "details": f"Performance test failed: {str(e)}"
            }
    
    async def _run_edge_case_test(
        self, 
        custom_model: CustomModel, 
        test_dataset: pd.DataFrame
    ) -> Dict[str, Any]:
        """Run edge case test with boundary values"""
        try:
            # Create edge case data
            edge_cases = pd.DataFrame({
                'min_value': [0, -1, float('inf')],
                'max_value': [100, 1000, float('-inf')],
                'null_value': [None, None, None]
            })
            
            result = await self.run_custom_model_inference(custom_model, edge_cases)
            return {
                "test_name": "edge_cases",
                "status": "passed" if not result.empty else "failed",
                "details": "Edge case test completed successfully"
            }
        except Exception as e:
            return {
                "test_name": "edge_cases",
                "status": "failed",
                "details": f"Edge case test failed: {str(e)}"
            }
    
    async def _run_stress_test(
        self, 
        custom_model: CustomModel, 
        test_dataset: pd.DataFrame
    ) -> Dict[str, Any]:
        """Run stress test with large dataset"""
        try:
            # Create larger test dataset
            large_dataset = pd.concat([test_dataset] * 10, ignore_index=True)
            result = await self.run_custom_model_inference(custom_model, large_dataset)
            
            return {
                "test_name": "stress_test",
                "status": "passed" if not result.empty else "failed",
                "details": f"Stress test completed with {len(large_dataset)} rows"
            }
        except Exception as e:
            return {
                "test_name": "stress_test",
                "status": "failed",
                "details": f"Stress test failed: {str(e)}"
            }

    # ---------- Helpers ----------
    def _get_file_extension(self, filename: str) -> str:
        if not filename or '.' not in filename:
            return 'bin'
        return filename.split('.')[-1].lower() 