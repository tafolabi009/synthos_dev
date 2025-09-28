'use client';

import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { Header } from '@/components/layout/Header';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { useAuth } from '@/contexts/AuthContext';
import { useRouter } from 'next/navigation';
import { apiClient } from '@/lib/api';
import { useToast } from '@/components/ui/use-toast';

interface CustomModel {
  id: number;
  name: string;
  description: string;
  model_type: string;
  status: string;
  accuracy_score: number;
  version: string;
  framework_version: string;
  supported_column_types: string[];
  max_columns: number;
  max_rows: number;
  requires_gpu: boolean;
  usage_count: number;
  last_used_at: string;
  tags: string[];
  created_at: string;
  updated_at: string;
}

interface TierLimits {
  subscription_tier: string;
  limits: {
    max_models: number;
    max_file_size_mb: number;
    gpu_support: boolean;
    features: string[];
  };
  current_usage: {
    models_used: number;
    models_remaining: number;
  };
}

export default function CustomModelsPage() {
  const { user, isAuthenticated } = useAuth();
  const router = useRouter();
  const { toast } = useToast();
  const [models, setModels] = useState<CustomModel[]>([]);
  const [tierLimits, setTierLimits] = useState<TierLimits | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [uploadLoading, setUploadLoading] = useState(false);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [uploadForm, setUploadForm] = useState({
    name: '',
    description: '',
    model_type: 'tensorflow'
  });

  useEffect(() => {
    if (!isAuthenticated) {
      router.push('/auth/signin');
      return;
    }

    // Check if user has access to custom models
    if (user?.subscription_tier === 'free' || user?.subscription_tier === 'starter') {
      setError('Custom models require Professional or Enterprise subscription');
      setLoading(false);
      return;
    }

    fetchCustomModels();
    fetchTierLimits();
  }, [isAuthenticated, user, router]);

  const fetchCustomModels = async () => {
    try {
      const response = await apiClient.getCustomModels();
      setModels(response);
    } catch (err) {
      console.error('Error fetching custom models:', err);
      setError('Failed to load custom models');
    }
  };

  const fetchTierLimits = async () => {
    try {
      const response = await fetch('/api/v1/custom-models/tier-limits', {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        }
      });
      if (response.ok) {
        const data = await response.json();
        setTierLimits(data);
      }
    } catch (err) {
      console.error('Error fetching tier limits:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleFileUpload = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!selectedFile) return;

    setUploadLoading(true);
    try {
      const response = await apiClient.uploadCustomModel(selectedFile, uploadForm);
      setModels(prev => [...prev, response]);
      setSelectedFile(null);
      setUploadForm({ name: '', description: '', model_type: 'tensorflow' });
      
      toast({
        title: "Model uploaded!",
        description: "Your custom model has been uploaded and is being processed.",
        variant: "success",
      });
    } catch (err) {
      console.error('Error uploading model:', err);
      toast({
        title: "Upload failed",
        description: "Failed to upload model. Please try again.",
        variant: "destructive",
      });
    } finally {
      setUploadLoading(false);
    }
  };

  const handleDeleteModel = async (modelId: number) => {
    try {
      await apiClient.deleteCustomModel(modelId);
      setModels(prev => prev.filter(m => m.id !== modelId));
      
      toast({
        title: "Model deleted",
        description: "The custom model has been deleted successfully.",
        variant: "success",
      });
    } catch (err) {
      console.error('Error deleting model:', err);
      toast({
        title: "Delete failed",
        description: "Failed to delete model. Please try again.",
        variant: "destructive",
      });
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'active': return 'bg-green-100 text-green-800';
      case 'training': return 'bg-yellow-100 text-yellow-800';
      case 'failed': return 'bg-red-100 text-red-800';
      default: return 'bg-gray-100 text-gray-800';
    }
  };

  const getModelTypeIcon = (type: string) => {
    switch (type) {
      case 'tensorflow': return '🧠';
      case 'pytorch': return '🔥';
      case 'huggingface': return '🤗';
      default: return '🤖';
    }
  };

  if (loading) {
    return (
      <div className="flex flex-col min-h-screen">
        <Header />
        <div className="flex-1 flex items-center justify-center">
          <div className="animate-spin rounded-full h-32 w-32 border-b-2 border-primary"></div>
        </div>
      </div>
    );
  }

  if (error && !tierLimits) {
    return (
      <div className="flex flex-col min-h-screen">
        <Header />
        <div className="flex-1 flex items-center justify-center">
          <Card className="max-w-md">
            <CardHeader>
              <CardTitle className="text-center">⚠️ Access Restricted</CardTitle>
            </CardHeader>
            <CardContent className="text-center">
              <p className="text-muted-foreground mb-4">{error}</p>
              <Button onClick={() => router.push('/pricing')}>
                Upgrade Subscription
              </Button>
            </CardContent>
          </Card>
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col min-h-screen">
      <Header />
      <main className="flex-1 bg-gradient-to-br from-background via-background to-primary/5">
        <div className="container mx-auto px-4 py-8">
          {/* Header */}
          <div className="mb-8">
            <h1 className="text-4xl font-bold mb-2">Custom Models</h1>
            <p className="text-lg text-muted-foreground">
              Upload and manage your custom AI models for synthetic data generation
            </p>
          </div>


          {/* Tier Limits */}
          {tierLimits && (
            <Card className="mb-8">
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  🎯 Subscription Limits
                  <span className="text-sm bg-primary/10 text-primary px-2 py-1 rounded">
                    {tierLimits.subscription_tier}
                  </span>
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  <div className="text-center">
                    <p className="text-2xl font-bold text-primary">
                      {tierLimits.current_usage.models_used}/{tierLimits.limits.max_models}
                    </p>
                    <p className="text-sm text-muted-foreground">Models Used</p>
                  </div>
                  <div className="text-center">
                    <p className="text-2xl font-bold text-primary">
                      {tierLimits.limits.max_file_size_mb}MB
                    </p>
                    <p className="text-sm text-muted-foreground">Max File Size</p>
                  </div>
                  <div className="text-center">
                    <p className="text-2xl font-bold text-primary">
                      {tierLimits.limits.gpu_support ? '✅' : '❌'}
                    </p>
                    <p className="text-sm text-muted-foreground">GPU Support</p>
                  </div>
                </div>
              </CardContent>
            </Card>
          )}

          {/* Upload Form */}
          <Card className="mb-8">
            <CardHeader>
              <CardTitle>Upload New Model</CardTitle>
              <CardDescription>
                Upload your custom trained model for synthetic data generation
              </CardDescription>
            </CardHeader>
            <CardContent>
              <form onSubmit={handleFileUpload} className="space-y-4">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium mb-2">Model Name</label>
                    <input
                      type="text"
                      value={uploadForm.name}
                      onChange={(e) => setUploadForm(prev => ({ ...prev, name: e.target.value }))}
                      className="w-full p-2 border rounded-md"
                      required
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium mb-2">Model Type</label>
                    <select
                      value={uploadForm.model_type}
                      onChange={(e) => setUploadForm(prev => ({ ...prev, model_type: e.target.value }))}
                      className="w-full p-2 border rounded-md"
                    >
                      <option value="tensorflow">TensorFlow</option>
                      <option value="pytorch">PyTorch</option>
                      <option value="huggingface">HuggingFace</option>
                    </select>
                  </div>
                </div>
                <div>
                  <label className="block text-sm font-medium mb-2">Description</label>
                  <textarea
                    value={uploadForm.description}
                    onChange={(e) => setUploadForm(prev => ({ ...prev, description: e.target.value }))}
                    className="w-full p-2 border rounded-md"
                    rows={3}
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium mb-2">Model File</label>
                  <input
                    type="file"
                    onChange={(e) => setSelectedFile(e.target.files?.[0] || null)}
                    className="w-full p-2 border rounded-md"
                    accept=".pb,.h5,.tf,.pt,.pth,.pkl,.json,.bin,.safetensors"
                    required
                  />
                </div>
                <Button type="submit" disabled={uploadLoading || !selectedFile}>
                  {uploadLoading ? 'Uploading...' : 'Upload Model'}
                </Button>
              </form>
            </CardContent>
          </Card>

          {/* Models List */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {models.map(model => (
              <motion.div
                key={model.id}
                initial={{ opacity: 0, scale: 0.95 }}
                animate={{ opacity: 1, scale: 1 }}
                transition={{ duration: 0.3 }}
              >
                <Card className="h-full">
                  <CardHeader>
                    <div className="flex items-center justify-between">
                      <CardTitle className="flex items-center gap-2">
                        {getModelTypeIcon(model.model_type)}
                        {model.name}
                      </CardTitle>
                      <span className={`px-2 py-1 rounded text-xs ${getStatusColor(model.status)}`}>
                        {model.status}
                      </span>
                    </div>
                    <CardDescription>{model.description}</CardDescription>
                  </CardHeader>
                  <CardContent>
                    <div className="space-y-3">
                      <div className="flex justify-between text-sm">
                        <span>Accuracy</span>
                        <span className="font-medium">{model.accuracy_score}%</span>
                      </div>
                      <div className="flex justify-between text-sm">
                        <span>Usage Count</span>
                        <span className="font-medium">{model.usage_count}</span>
                      </div>
                      <div className="flex justify-between text-sm">
                        <span>Max Columns</span>
                        <span className="font-medium">{model.max_columns}</span>
                      </div>
                      <div className="flex justify-between text-sm">
                        <span>GPU Required</span>
                        <span className="font-medium">{model.requires_gpu ? '✅' : '❌'}</span>
                      </div>
                      <div className="flex justify-between text-sm">
                        <span>Version</span>
                        <span className="font-medium">{model.version}</span>
                      </div>
                      <div className="flex justify-between text-sm">
                        <span>Created</span>
                        <span className="font-medium">
                          {new Date(model.created_at).toLocaleDateString()}
                        </span>
                      </div>
                      <div className="flex flex-wrap gap-1">
                        {model.tags.map(tag => (
                          <span key={tag} className="px-2 py-1 bg-blue-100 text-blue-800 rounded text-xs">
                            {tag}
                          </span>
                        ))}
                      </div>
                    </div>
                    <div className="mt-4 flex gap-2">
                      <Button 
                        variant="outline" 
                        size="sm"
                        onClick={() => handleDeleteModel(model.id)}
                      >
                        Delete
                      </Button>
                      <Button size="sm">Use Model</Button>
                    </div>
                  </CardContent>
                </Card>
              </motion.div>
            ))}
          </div>

          {models.length === 0 && (
            <div className="text-center py-12">
              <div className="text-6xl mb-4">🤖</div>
              <h3 className="text-xl font-semibold mb-2">No Custom Models Yet</h3>
              <p className="text-muted-foreground">
                Upload your first custom model to get started with personalized synthetic data generation
              </p>
            </div>
          )}
        </div>
      </main>
    </div>
  );
} 