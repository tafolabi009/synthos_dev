'use client';

import React, { useState } from 'react';
import { motion } from 'framer-motion';
import { Header } from '@/components/layout/Header';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { useToast } from '@/components/ui/use-toast';

const SettingsPage = () => {
  const [activeTab, setActiveTab] = useState('account');
  const [isLoading, setIsLoading] = useState(false);
  const { toast } = useToast();

  const [accountData, setAccountData] = useState({
    full_name: 'John Doe',
    email: 'john@example.com',
    company: 'Acme Corp',
    timezone: 'UTC',
    language: 'English'
  });

  const [apiKeys, setApiKeys] = useState([
    {
      id: 1,
      name: 'Production API Key',
      key: 'sk_prod_**********************',
      created_at: '2024-01-15',
      last_used: '2024-01-20',
      permissions: ['read', 'write']
    },
    {
      id: 2,
      name: 'Development API Key',
      key: 'sk_dev_**********************',
      created_at: '2024-01-10',
      last_used: '2024-01-19',
      permissions: ['read']
    }
  ]);

  const [notifications, setNotifications] = useState({
    email_updates: true,
    generation_complete: true,
    usage_alerts: true,
    security_alerts: true,
    marketing_emails: false
  });

  const [privacy, setPrivacy] = useState({
    data_retention: '30_days',
    audit_logs: true,
    gdpr_compliance: true,
    encryption_level: 'high'
  });

  const tabs = [
    { id: 'account', label: 'Account', icon: '👤' },
    { id: 'api', label: 'API Keys', icon: '🔑' },
    { id: 'notifications', label: 'Notifications', icon: '🔔' },
    { id: 'privacy', label: 'Privacy', icon: '🔒' },
    { id: 'billing', label: 'Billing', icon: '💳' },
    { id: 'security', label: 'Security', icon: '🛡️' }
  ];

  const handleAccountUpdate = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    
    try {
      // Simulate API call
      await new Promise(resolve => setTimeout(resolve, 1000));
      toast({
        title: "Account updated!",
        description: "Your account settings have been updated successfully.",
        variant: "success",
      });
    } catch (error) {
      toast({
        title: "Update failed",
        description: "Failed to update account settings. Please try again.",
        variant: "destructive",
      });
    } finally {
      setIsLoading(false);
    }
  };

  const generateApiKey = async () => {
    setIsLoading(true);
    try {
      await new Promise(resolve => setTimeout(resolve, 1000));
      const newKey = {
        id: Date.now(),
        name: 'New API Key',
        key: 'sk_new_' + Math.random().toString(36).substring(2, 15),
        created_at: new Date().toISOString().split('T')[0],
        last_used: 'Never',
        permissions: ['read']
      };
      setApiKeys([...apiKeys, newKey]);
      toast({
        title: "API key generated!",
        description: "Your new API key has been generated successfully.",
        variant: "success",
      });
    } catch (error) {
      toast({
        title: "Generation failed",
        description: "Failed to generate API key. Please try again.",
        variant: "destructive",
      });
    } finally {
      setIsLoading(false);
    }
  };

  const revokeApiKey = (keyId: number) => {
    setApiKeys(apiKeys.filter(key => key.id !== keyId));
    toast({
      title: "API key revoked",
      description: "The API key has been revoked successfully.",
      variant: "success",
    });
  };

  const updateNotifications = async () => {
    setIsLoading(true);
    try {
      await new Promise(resolve => setTimeout(resolve, 1000));
      toast({
        title: "Notifications updated!",
        description: "Your notification preferences have been updated.",
        variant: "success",
      });
    } catch (error) {
      toast({
        title: "Update failed",
        description: "Failed to update notification preferences. Please try again.",
        variant: "destructive",
      });
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="flex flex-col min-h-screen">
      <Header />
      <main className="flex-1 bg-gray-50">
        <div className="container mx-auto px-4 py-8">
          {/* Header */}
          <div className="mb-8">
            <h1 className="text-4xl font-bold mb-2">Settings</h1>
            <p className="text-lg text-muted-foreground">
              Manage your account, API keys, and preferences
            </p>
          </div>


          <div className="grid grid-cols-1 lg:grid-cols-4 gap-8">
            {/* Sidebar */}
            <div className="lg:col-span-1">
              <nav className="space-y-2">
                {tabs.map((tab) => (
                  <button
                    key={tab.id}
                    onClick={() => setActiveTab(tab.id)}
                    className={`w-full flex items-center gap-3 px-4 py-3 rounded-lg text-left transition-colors ${
                      activeTab === tab.id
                        ? 'bg-primary text-primary-foreground'
                        : 'hover:bg-gray-100'
                    }`}
                  >
                    <span className="text-lg">{tab.icon}</span>
                    <span className="font-medium">{tab.label}</span>
                  </button>
                ))}
              </nav>
            </div>

            {/* Content */}
            <div className="lg:col-span-3">
              {activeTab === 'account' && (
                <Card>
                  <CardHeader>
                    <CardTitle>Account Information</CardTitle>
                    <CardDescription>
                      Update your personal information and preferences
                    </CardDescription>
                  </CardHeader>
                  <CardContent>
                    <form onSubmit={handleAccountUpdate} className="space-y-6">
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        <div>
                          <label className="block text-sm font-medium mb-2">Full Name</label>
                          <input
                            type="text"
                            value={accountData.full_name}
                            onChange={(e) => setAccountData({...accountData, full_name: e.target.value})}
                            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-primary"
                          />
                        </div>
                        <div>
                          <label className="block text-sm font-medium mb-2">Email</label>
                          <input
                            type="email"
                            value={accountData.email}
                            onChange={(e) => setAccountData({...accountData, email: e.target.value})}
                            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-primary"
                          />
                        </div>
                        <div>
                          <label className="block text-sm font-medium mb-2">Company</label>
                          <input
                            type="text"
                            value={accountData.company}
                            onChange={(e) => setAccountData({...accountData, company: e.target.value})}
                            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-primary"
                          />
                        </div>
                        <div>
                          <label className="block text-sm font-medium mb-2">Timezone</label>
                          <select
                            value={accountData.timezone}
                            onChange={(e) => setAccountData({...accountData, timezone: e.target.value})}
                            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-primary"
                          >
                            <option value="UTC">UTC</option>
                            <option value="America/New_York">Eastern Time</option>
                            <option value="America/Los_Angeles">Pacific Time</option>
                            <option value="Europe/London">London</option>
                            <option value="Asia/Tokyo">Tokyo</option>
                          </select>
                        </div>
                      </div>
                      <Button type="submit" disabled={isLoading}>
                        {isLoading ? 'Updating...' : 'Update Account'}
                      </Button>
                    </form>
                  </CardContent>
                </Card>
              )}

              {activeTab === 'api' && (
                <Card>
                  <CardHeader>
                    <div className="flex items-center justify-between">
                      <div>
                        <CardTitle>API Keys</CardTitle>
                        <CardDescription>
                          Manage your API keys for programmatic access
                        </CardDescription>
                      </div>
                      <Button onClick={generateApiKey} disabled={isLoading}>
                        Generate New Key
                      </Button>
                    </div>
                  </CardHeader>
                  <CardContent>
                    <div className="space-y-4">
                      {apiKeys.map((key) => (
                        <div key={key.id} className="flex items-center justify-between p-4 border rounded-lg">
                          <div>
                            <h3 className="font-medium">{key.name}</h3>
                            <p className="text-sm text-muted-foreground font-mono">{key.key}</p>
                            <div className="flex items-center gap-4 text-xs text-muted-foreground mt-2">
                              <span>Created: {key.created_at}</span>
                              <span>Last used: {key.last_used}</span>
                              <span>Permissions: {key.permissions.join(', ')}</span>
                            </div>
                          </div>
                          <Button
                            variant="destructive"
                            size="sm"
                            onClick={() => revokeApiKey(key.id)}
                          >
                            Revoke
                          </Button>
                        </div>
                      ))}
                    </div>
                  </CardContent>
                </Card>
              )}

              {activeTab === 'notifications' && (
                <Card>
                  <CardHeader>
                    <CardTitle>Notification Preferences</CardTitle>
                    <CardDescription>
                      Control what notifications you receive
                    </CardDescription>
                  </CardHeader>
                  <CardContent>
                    <div className="space-y-6">
                      {Object.entries(notifications).map(([key, value]) => (
                        <div key={key} className="flex items-center justify-between">
                          <div>
                            <h3 className="font-medium capitalize">
                              {key.replace('_', ' ')}
                            </h3>
                            <p className="text-sm text-muted-foreground">
                              {key === 'email_updates' && 'Receive product updates and announcements'}
                              {key === 'generation_complete' && 'Get notified when data generation is complete'}
                              {key === 'usage_alerts' && 'Alerts when approaching usage limits'}
                              {key === 'security_alerts' && 'Important security notifications'}
                              {key === 'marketing_emails' && 'Marketing and promotional emails'}
                            </p>
                          </div>
                          <label className="relative inline-flex items-center cursor-pointer">
                            <input
                              type="checkbox"
                              checked={value}
                              onChange={(e) => setNotifications({
                                ...notifications,
                                [key]: e.target.checked
                              })}
                              className="sr-only peer"
                            />
                            <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-primary/25 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-primary"></div>
                          </label>
                        </div>
                      ))}
                      <Button onClick={updateNotifications} disabled={isLoading}>
                        {isLoading ? 'Updating...' : 'Update Preferences'}
                      </Button>
                    </div>
                  </CardContent>
                </Card>
              )}

              {activeTab === 'privacy' && (
                <Card>
                  <CardHeader>
                    <CardTitle>Privacy & Security</CardTitle>
                    <CardDescription>
                      Control your data privacy and security settings
                    </CardDescription>
                  </CardHeader>
                  <CardContent>
                    <div className="space-y-6">
                      <div>
                        <label className="block text-sm font-medium mb-2">Data Retention Period</label>
                        <select
                          value={privacy.data_retention}
                          onChange={(e) => setPrivacy({...privacy, data_retention: e.target.value})}
                          className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-primary"
                        >
                          <option value="7_days">7 days</option>
                          <option value="30_days">30 days</option>
                          <option value="90_days">90 days</option>
                          <option value="1_year">1 year</option>
                        </select>
                      </div>
                      
                      <div>
                        <label className="block text-sm font-medium mb-2">Encryption Level</label>
                        <select
                          value={privacy.encryption_level}
                          onChange={(e) => setPrivacy({...privacy, encryption_level: e.target.value})}
                          className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-primary"
                        >
                          <option value="standard">Standard (AES-128)</option>
                          <option value="high">High (AES-256)</option>
                          <option value="enterprise">Enterprise (AES-256 + HSM)</option>
                        </select>
                      </div>

                      <div className="space-y-4">
                        <div className="flex items-center justify-between">
                          <div>
                            <h3 className="font-medium">Audit Logs</h3>
                            <p className="text-sm text-muted-foreground">Keep detailed logs of all activities</p>
                          </div>
                          <label className="relative inline-flex items-center cursor-pointer">
                            <input
                              type="checkbox"
                              checked={privacy.audit_logs}
                              onChange={(e) => setPrivacy({...privacy, audit_logs: e.target.checked})}
                              className="sr-only peer"
                            />
                            <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-primary/25 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-primary"></div>
                          </label>
                        </div>
                        
                        <div className="flex items-center justify-between">
                          <div>
                            <h3 className="font-medium">GDPR Compliance</h3>
                            <p className="text-sm text-muted-foreground">Enable GDPR compliance features</p>
                          </div>
                          <label className="relative inline-flex items-center cursor-pointer">
                            <input
                              type="checkbox"
                              checked={privacy.gdpr_compliance}
                              onChange={(e) => setPrivacy({...privacy, gdpr_compliance: e.target.checked})}
                              className="sr-only peer"
                            />
                            <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-primary/25 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-primary"></div>
                          </label>
                        </div>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              )}

              {activeTab === 'billing' && (
                <Card>
                  <CardHeader>
                    <CardTitle>Billing & Subscription</CardTitle>
                    <CardDescription>
                      Manage your subscription and billing information
                    </CardDescription>
                  </CardHeader>
                  <CardContent>
                    <div className="space-y-6">
                      <div className="p-6 bg-blue-50 border border-blue-200 rounded-lg">
                        <div className="flex items-center justify-between mb-4">
                          <h3 className="text-lg font-semibold">Free Plan</h3>
                          <span className="px-3 py-1 bg-blue-100 text-blue-700 rounded-full text-sm">Active</span>
                        </div>
                        <p className="text-sm text-muted-foreground mb-4">
                          10,000 rows per month • Basic support • Standard privacy
                        </p>
                        <Button>Upgrade Plan</Button>
                      </div>
                      
                      <div>
                        <h3 className="font-semibold mb-4">Usage This Month</h3>
                        <div className="space-y-3">
                          <div className="flex justify-between text-sm">
                            <span>Rows Generated</span>
                            <span>2,500 / 10,000</span>
                          </div>
                          <div className="w-full bg-gray-200 rounded-full h-2">
                            <div className="bg-primary h-2 rounded-full" style={{ width: '25%' }}></div>
                          </div>
                        </div>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              )}

              {activeTab === 'security' && (
                <Card>
                  <CardHeader>
                    <CardTitle>Security Settings</CardTitle>
                    <CardDescription>
                      Manage your account security and authentication
                    </CardDescription>
                  </CardHeader>
                  <CardContent>
                    <div className="space-y-6">
                      <div>
                        <h3 className="font-semibold mb-4">Password</h3>
                        <Button variant="outline">Change Password</Button>
                      </div>
                      
                      <div>
                        <h3 className="font-semibold mb-4">Two-Factor Authentication</h3>
                        <p className="text-sm text-muted-foreground mb-4">
                          Add an extra layer of security to your account
                        </p>
                        <Button variant="outline">Enable 2FA</Button>
                      </div>
                      
                      <div>
                        <h3 className="font-semibold mb-4">Active Sessions</h3>
                        <div className="space-y-3">
                          <div className="flex items-center justify-between p-3 border rounded-lg">
                            <div>
                              <p className="font-medium">Current Session</p>
                              <p className="text-sm text-muted-foreground">Chrome on MacOS • San Francisco, CA</p>
                            </div>
                            <span className="text-sm text-green-600">Active</span>
                          </div>
                        </div>
                      </div>
                      
                      <div>
                        <h3 className="font-semibold mb-4">Danger Zone</h3>
                        <div className="p-4 border border-red-200 rounded-lg">
                          <h4 className="font-medium text-red-600 mb-2">Delete Account</h4>
                          <p className="text-sm text-muted-foreground mb-4">
                            This action is irreversible. All your data will be permanently deleted.
                          </p>
                          <Button variant="destructive">Delete Account</Button>
                        </div>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              )}
            </div>
          </div>
        </div>
      </main>
    </div>
  );
};

export default SettingsPage; 