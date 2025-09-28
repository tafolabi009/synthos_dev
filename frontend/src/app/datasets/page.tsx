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

interface Dataset {
  id: number;
  name: string;
  description?: string;
  file_name: string;
  file_size: number;
  row_count: number;
  column_count: number;
  status: string;
  privacy_level: string;
  created_at: string;
  updated_at: string;
  columns: DatasetColumn[];
}

interface DatasetColumn {
  id: number;
  name: string;
  data_type: string;
  nullable: boolean;
  unique_values?: number;
}

interface GenerationJob {
  id: number;
  dataset_id: number;
  rows_requested: number;
  rows_generated: number;
  status: string;
  progress_percentage: number;
  created_at: string;
  completed_at?: string;
}

export default function DatasetsPage() {
  const { user, isAuthenticated } = useAuth();
  const router = useRouter();
  const { toast } = useToast();
  const [datasets, setDatasets] = useState<Dataset[]>([]);
  const [selectedDataset, setSelectedDataset] = useState<Dataset | null>(null);
  const [generationJobs, setGenerationJobs] = useState<GenerationJob[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [uploadLoading, setUploadLoading] = useState(false);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [uploadForm, setUploadForm] = useState({
    name: '',
    description: '',
    privacy_level: 'medium'
  });

  useEffect(() => {
    if (!isAuthenticated) {
      router.push('/auth/signin');
      return;
    }

    fetchData();
  }, [isAuthenticated, router]);

  const fetchData = async () => {
    try {
      setLoading(true);
      const [datasetsResponse, jobsResponse] = await Promise.all([
        apiClient.getDatasets(),
        apiClient.getGenerationJobs()
      ]);

      setDatasets(datasetsResponse);
      setGenerationJobs(jobsResponse);
    } catch (err) {
      console.error('Error fetching data:', err);
      setError('Failed to load datasets');
    } finally {
      setLoading(false);
    }
  };

  const handleFileUpload = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!selectedFile) return;

    setUploadLoading(true);
    try {
      const newDataset = await apiClient.uploadDataset(selectedFile, uploadForm);
      setDatasets(prev => [...prev, newDataset]);
      setSelectedFile(null);
      setUploadForm({ name: '', description: '', privacy_level: 'medium' });
      
      toast({
        title: "Dataset uploaded!",
        description: "Your dataset has been uploaded and is being processed.",
        variant: "success",
      });
    } catch (err) {
      console.error('Error uploading dataset:', err);
      toast({
        title: "Upload failed",
        description: "Failed to upload dataset. Please try again.",
        variant: "destructive",
      });
    } finally {
      setUploadLoading(false);
    }
  };

  const handleDeleteDataset = async (datasetId: number) => {
    if (!confirm('Are you sure you want to delete this dataset?')) return;

    try {
      await apiClient.deleteDataset(datasetId);
      setDatasets(prev => prev.filter(d => d.id !== datasetId));
      if (selectedDataset?.id === datasetId) {
        setSelectedDataset(null);
      }
      
      toast({
        title: "Dataset deleted",
        description: "The dataset has been deleted successfully.",
        variant: "success",
      });
    } catch (err) {
      console.error('Error deleting dataset:', err);
      toast({
        title: "Delete failed",
        description: "Failed to delete dataset. Please try again.",
        variant: "destructive",
      });
    }
  };

  const handleDownloadDataset = async (datasetId: number) => {
    try {
      const blob = await apiClient.downloadDataset(datasetId);
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `dataset_${datasetId}.csv`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
      
      toast({
        title: "Download started",
        description: "Your dataset download has started.",
        variant: "success",
      });
    } catch (err) {
      console.error('Error downloading dataset:', err);
      toast({
        title: "Download failed",
        description: "Failed to download dataset. Please try again.",
        variant: "destructive",
      });
    }
  };

  const startGeneration = async (datasetId: number) => {
    try {
      const job = await apiClient.startGeneration({
        dataset_id: datasetId,
        rows: 1000,
        privacy_level: 'medium'
      });
      setGenerationJobs(prev => [...prev, job]);
      
      toast({
        title: "Generation started!",
        description: "Synthetic data generation has been started for this dataset.",
        variant: "success",
      });
    } catch (err) {
      console.error('Error starting generation:', err);
      toast({
        title: "Generation failed",
        description: "Failed to start generation. Please try again.",
        variant: "destructive",
      });
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'ready': return 'bg-green-100 text-green-800';
      case 'processing': return 'bg-yellow-100 text-yellow-800';
      case 'failed': return 'bg-red-100 text-red-800';
      default: return 'bg-gray-100 text-gray-800';
    }
  };

  const getPrivacyLevelColor = (level: string) => {
    switch (level) {
      case 'high': return 'bg-red-100 text-red-800';
      case 'medium': return 'bg-yellow-100 text-yellow-800';
      case 'low': return 'bg-green-100 text-green-800';
      default: return 'bg-gray-100 text-gray-800';
    }
  };

  const formatFileSize = (bytes: number) => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  const getDatasetJobs = (datasetId: number) => {
    return generationJobs.filter(job => job.dataset_id === datasetId);
  };

  if (loading) {
    return (
      <div className="flex flex-col min-h-screen">
        <Header />
        <div className="flex-1 flex items-center justify-center">
          <div className="animate-spin rounded-full h-32 w-32 border-b-2 border-primary" role="status" aria-live="polite" aria-busy="true" tabIndex={0}></div>
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col min-h-screen">
      <Header />
      <main className="flex-1 bg-gradient-to-br from-background via-background to-primary/5">
        <div className="container mx-auto px-4 py-8">
          <div className="mb-8">
            <h1 className="text-4xl font-bold mb-2">Dataset Management</h1>
            <p className="text-lg text-muted-foreground">
              Upload, manage, and analyze your datasets for synthetic data generation
            </p>
          </div>


          <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
            {/* Dataset List */}
            <div className="lg:col-span-2">
              {/* Upload Form */}
              <Card className="mb-6">
                <CardHeader>
                  <CardTitle>Upload New Dataset</CardTitle>
                  <CardDescription>
                    Upload a CSV, JSON, or Excel file to create a new dataset
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <form onSubmit={handleFileUpload} className="space-y-4">
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      <div>
                        <label className="block text-sm font-medium mb-2">Dataset Name</label>
                        <input
                          type="text"
                          value={uploadForm.name}
                          onChange={(e) => setUploadForm(prev => ({ ...prev, name: e.target.value }))}
                          className="w-full p-2 border rounded-md"
                          placeholder="Enter dataset name"
                          required
                        />
                      </div>
                      <div>
                        <label className="block text-sm font-medium mb-2">Privacy Level</label>
                        <select
                          value={uploadForm.privacy_level}
                          onChange={(e) => setUploadForm(prev => ({ ...prev, privacy_level: e.target.value }))}
                          className="w-full p-2 border rounded-md"
                        >
                          <option value="low">Low</option>
                          <option value="medium">Medium</option>
                          <option value="high">High</option>
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
                        placeholder="Optional description..."
                      />
                    </div>
                    <div>
                      <label className="block text-sm font-medium mb-2">File</label>
                      <input
                        type="file"
                        onChange={(e) => setSelectedFile(e.target.files?.[0] || null)}
                        className="w-full p-2 border rounded-md"
                        accept=".csv,.json,.xlsx,.xls"
                        required
                      />
                    </div>
                    <Button type="submit" disabled={uploadLoading || !selectedFile} className="touch-target">
                      {uploadLoading ? 'Uploading...' : 'Upload Dataset'}
                    </Button>
                  </form>
                </CardContent>
              </Card>

              {/* Datasets List */}
              <div className="space-y-4">
                {datasets.map(dataset => (
                  <motion.div
                    key={dataset.id}
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.3 }}
                  >
                    <Card className={`cursor-pointer transition-all ${
                      selectedDataset?.id === dataset.id ? 'ring-2 ring-primary' : 'hover:shadow-lg'
                    }`}>
                      <CardHeader onClick={() => setSelectedDataset(dataset)}>
                        <div className="flex items-center justify-between">
                          <div>
                            <CardTitle className="text-lg">{dataset.name}</CardTitle>
                            <CardDescription>{dataset.description || 'No description'}</CardDescription>
                          </div>
                          <div className="flex items-center gap-2">
                            <span className={`px-2 py-1 rounded text-xs ${getStatusColor(dataset.status)}`}>
                              {dataset.status}
                            </span>
                            <span className={`px-2 py-1 rounded text-xs ${getPrivacyLevelColor(dataset.privacy_level)}`}>
                              {dataset.privacy_level}
                            </span>
                          </div>
                        </div>
                      </CardHeader>
                      <CardContent>
                        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
                          <div>
                            <p className="text-muted-foreground">Rows</p>
                            <p className="font-medium">{dataset.row_count.toLocaleString()}</p>
                          </div>
                          <div>
                            <p className="text-muted-foreground">Columns</p>
                            <p className="font-medium">{dataset.column_count}</p>
                          </div>
                          <div>
                            <p className="text-muted-foreground">Size</p>
                            <p className="font-medium">{formatFileSize(dataset.file_size)}</p>
                          </div>
                          <div>
                            <p className="text-muted-foreground">Created</p>
                            <p className="font-medium">{new Date(dataset.created_at).toLocaleDateString()}</p>
                          </div>
                        </div>
                        <div className="mt-4 flex gap-2">
                          <Button 
                            size="sm" 
                            onClick={() => startGeneration(dataset.id)}
                            disabled={dataset.status !== 'ready'}
                            className="touch-target"
                          >
                            Generate
                          </Button>
                          <Button 
                            variant="outline" 
                            size="sm"
                            onClick={() => handleDownloadDataset(dataset.id)}
                            className="touch-target"
                          >
                            Download
                          </Button>
                          <Button 
                            variant="destructive" 
                            size="sm"
                            onClick={() => handleDeleteDataset(dataset.id)}
                            className="touch-target"
                          >
                            Delete
                          </Button>
                        </div>
                      </CardContent>
                    </Card>
                  </motion.div>
                ))}
              </div>

              {datasets.length === 0 && (
                <div className="text-center py-12">
                  <div className="text-6xl mb-4">📊</div>
                  <h3 className="text-xl font-semibold mb-2">No Datasets Yet</h3>
                  <p className="text-muted-foreground">
                    Upload your first dataset to start generating synthetic data
                  </p>
                </div>
              )}
            </div>

            {/* Dataset Details */}
            <div className="lg:col-span-1">
              {selectedDataset ? (
                <div className="space-y-6">
                  <Card>
                    <CardHeader>
                      <CardTitle>Dataset Details</CardTitle>
                      <CardDescription>{selectedDataset.name}</CardDescription>
                    </CardHeader>
                    <CardContent>
                      <div className="space-y-4">
                        <div>
                          <p className="text-sm font-medium">File Name</p>
                          <p className="text-sm text-muted-foreground">{selectedDataset.file_name}</p>
                        </div>
                        <div>
                          <p className="text-sm font-medium">Status</p>
                          <span className={`px-2 py-1 rounded text-xs ${getStatusColor(selectedDataset.status)}`}>
                            {selectedDataset.status}
                          </span>
                        </div>
                        <div>
                          <p className="text-sm font-medium">Privacy Level</p>
                          <span className={`px-2 py-1 rounded text-xs ${getPrivacyLevelColor(selectedDataset.privacy_level)}`}>
                            {selectedDataset.privacy_level}
                          </span>
                        </div>
                        <div>
                          <p className="text-sm font-medium">Description</p>
                          <p className="text-sm text-muted-foreground">
                            {selectedDataset.description || 'No description provided'}
                          </p>
                        </div>
                      </div>
                    </CardContent>
                  </Card>

                  <Card>
                    <CardHeader>
                      <CardTitle>Column Schema</CardTitle>
                    </CardHeader>
                    <CardContent>
                      <div className="space-y-2">
                        {selectedDataset.columns.map(column => (
                          <div key={column.id} className="flex items-center justify-between p-2 bg-muted rounded">
                            <div>
                              <p className="text-sm font-medium">{column.name}</p>
                              <p className="text-xs text-muted-foreground">{column.data_type}</p>
                            </div>
                            <div className="text-right">
                              {column.unique_values && (
                                <p className="text-xs text-muted-foreground">
                                  {column.unique_values} unique
                                </p>
                              )}
                              {column.nullable && (
                                <p className="text-xs text-muted-foreground">Nullable</p>
                              )}
                            </div>
                          </div>
                        ))}
                      </div>
                    </CardContent>
                  </Card>

                  <Card>
                    <CardHeader>
                      <CardTitle>Generation Jobs</CardTitle>
                    </CardHeader>
                    <CardContent>
                      <div className="space-y-2">
                        {getDatasetJobs(selectedDataset.id).map(job => (
                          <div key={job.id} className="p-3 bg-muted rounded">
                            <div className="flex items-center justify-between">
                              <div>
                                <p className="text-sm font-medium">{job.rows_requested} rows</p>
                                <p className="text-xs text-muted-foreground">
                                  {new Date(job.created_at).toLocaleDateString()}
                                </p>
                              </div>
                              <span className={`px-2 py-1 rounded text-xs ${getStatusColor(job.status)}`}>
                                {job.status}
                              </span>
                            </div>
                            {job.status === 'running' && (
                              <div className="mt-2">
                                <div className="flex justify-between text-xs mb-1">
                                  <span>Progress</span>
                                  <span>{job.progress_percentage}%</span>
                                </div>
                                <div className="w-full bg-gray-200 rounded-full h-2">
                                  <div 
                                    className="bg-primary h-2 rounded-full transition-all duration-300"
                                    style={{ width: `${job.progress_percentage}%` }}
                                  />
                                </div>
                              </div>
                            )}
                          </div>
                        ))}
                        {getDatasetJobs(selectedDataset.id).length === 0 && (
                          <p className="text-sm text-muted-foreground">No generation jobs yet</p>
                        )}
                      </div>
                    </CardContent>
                  </Card>
                </div>
              ) : (
                <Card>
                  <CardContent className="text-center py-8">
                    <div className="text-4xl mb-4">📋</div>
                    <h3 className="text-lg font-semibold mb-2">Select a Dataset</h3>
                    <p className="text-muted-foreground">
                      Click on a dataset to view its details and manage generation jobs
                    </p>
                  </CardContent>
                </Card>
              )}
            </div>
          </div>
        </div>
      </main>
    </div>
  );
} 