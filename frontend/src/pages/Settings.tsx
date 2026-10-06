import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { authAPI } from '../lib/api';
import {
  CogIcon,
  CurrencyDollarIcon,
  BellIcon,
  ShieldCheckIcon,
  UserIcon,
  GlobeAltIcon,
  ChartBarIcon,
} from '@heroicons/react/24/outline';

interface UserSettings {
  currency: string;
  locale: string;
  timezone: string;
  dateFormat: string;
  numberFormat: string;
  budgetAlerts: boolean;
  transactionAlerts: boolean;
  monthlyReports: boolean;
  emailNotifications: boolean;
  theme: string;
  dashboardLayout: string;
}

const defaultSettings: UserSettings = {
  currency: 'INR',
  locale: 'en-IN',
  timezone: 'Asia/Kolkata',
  dateFormat: 'DD/MM/YYYY',
  numberFormat: 'Indian',
  budgetAlerts: true,
  transactionAlerts: true,
  monthlyReports: true,
  emailNotifications: true,
  theme: 'light',
  dashboardLayout: 'grid',
};

export default function Settings() {
  const [settings, setSettings] = useState<UserSettings>(defaultSettings);
  const [activeTab, setActiveTab] = useState('general');
  const queryClient = useQueryClient();

  // Fetch current user data
  const { data: user } = useQuery({
    queryKey: ['user'],
    queryFn: () => authAPI.getCurrentUser(),
  });

  const handleSettingChange = (key: keyof UserSettings, value: any) => {
    setSettings(prev => ({
      ...prev,
      [key]: value
    }));
  };

  const saveSettings = () => {
    // In a real implementation, this would save to backend
    console.log('Saving settings:', settings);
    alert('Settings saved successfully!');
  };

  const tabs = [
    { id: 'general', name: 'General', icon: CogIcon },
    { id: 'currency', name: 'Currency & Format', icon: CurrencyDollarIcon },
    { id: 'notifications', name: 'Notifications', icon: BellIcon },
    { id: 'security', name: 'Security', icon: ShieldCheckIcon },
    { id: 'profile', name: 'Profile', icon: UserIcon },
  ];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-900">Settings</h1>
        <button
          onClick={saveSettings}
          className="btn-primary"
        >
          Save Changes
        </button>
      </div>

      <div className="flex flex-col lg:flex-row gap-6">
        {/* Sidebar */}
        <div className="lg:w-64">
          <nav className="space-y-1">
            {tabs.map((tab) => {
              const Icon = tab.icon;
              return (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id)}
                  className={`w-full flex items-center px-3 py-2 text-sm font-medium rounded-md transition-colors ${
                    activeTab === tab.id
                      ? 'bg-primary-100 text-primary-700 border-r-2 border-primary-500'
                      : 'text-gray-600 hover:text-gray-900 hover:bg-gray-50'
                  }`}
                >
                  <Icon className="h-5 w-5 mr-3" />
                  {tab.name}
                </button>
              );
            })}
          </nav>
        </div>

        {/* Content */}
        <div className="flex-1">
          <div className="card">
            {/* General Settings */}
            {activeTab === 'general' && (
              <div className="space-y-6">
                <h2 className="text-lg font-medium text-gray-900 border-b border-gray-200 pb-2">
                  General Settings
                </h2>
                
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Theme
                    </label>
                    <select
                      value={settings.theme}
                      onChange={(e) => handleSettingChange('theme', e.target.value)}
                      className="input-field"
                    >
                      <option value="light">Light</option>
                      <option value="dark">Dark</option>
                      <option value="system">System</option>
                    </select>
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Dashboard Layout
                    </label>
                    <select
                      value={settings.dashboardLayout}
                      onChange={(e) => handleSettingChange('dashboardLayout', e.target.value)}
                      className="input-field"
                    >
                      <option value="grid">Grid View</option>
                      <option value="list">List View</option>
                      <option value="compact">Compact View</option>
                    </select>
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Timezone
                    </label>
                    <select
                      value={settings.timezone}
                      onChange={(e) => handleSettingChange('timezone', e.target.value)}
                      className="input-field"
                    >
                      <option value="Asia/Kolkata">Asia/Kolkata (IST)</option>
                      <option value="UTC">UTC</option>
                      <option value="America/New_York">America/New_York (EST)</option>
                      <option value="Europe/London">Europe/London (GMT)</option>
                    </select>
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Language
                    </label>
                    <select
                      value={settings.locale}
                      onChange={(e) => handleSettingChange('locale', e.target.value)}
                      className="input-field"
                    >
                      <option value="en-IN">English (India)</option>
                      <option value="hi-IN">हिन्दी (Hindi)</option>
                      <option value="en-US">English (US)</option>
                      <option value="en-GB">English (UK)</option>
                    </select>
                  </div>
                </div>
              </div>
            )}

            {/* Currency & Format Settings */}
            {activeTab === 'currency' && (
              <div className="space-y-6">
                <h2 className="text-lg font-medium text-gray-900 border-b border-gray-200 pb-2">
                  Currency & Format Settings
                </h2>
                
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      <CurrencyDollarIcon className="h-4 w-4 inline mr-1" />
                      Primary Currency
                    </label>
                    <select
                      value={settings.currency}
                      onChange={(e) => handleSettingChange('currency', e.target.value)}
                      className="input-field"
                    >
                      <option value="INR">₹ Indian Rupee (INR)</option>
                      <option value="USD">$ US Dollar (USD)</option>
                      <option value="EUR">€ Euro (EUR)</option>
                      <option value="GBP">£ British Pound (GBP)</option>
                      <option value="JPY">¥ Japanese Yen (JPY)</option>
                      <option value="AUD">A$ Australian Dollar (AUD)</option>
                      <option value="CAD">C$ Canadian Dollar (CAD)</option>
                    </select>
                    <p className="text-xs text-gray-500 mt-1">
                      All amounts will be displayed in this currency
                    </p>
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Number Format
                    </label>
                    <select
                      value={settings.numberFormat}
                      onChange={(e) => handleSettingChange('numberFormat', e.target.value)}
                      className="input-field"
                    >
                      <option value="Indian">Indian (1,23,45,678.90)</option>
                      <option value="International">International (1,234,567.90)</option>
                      <option value="European">European (1.234.567,90)</option>
                    </select>
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Date Format
                    </label>
                    <select
                      value={settings.dateFormat}
                      onChange={(e) => handleSettingChange('dateFormat', e.target.value)}
                      className="input-field"
                    >
                      <option value="DD/MM/YYYY">DD/MM/YYYY (31/12/2024)</option>
                      <option value="MM/DD/YYYY">MM/DD/YYYY (12/31/2024)</option>
                      <option value="YYYY-MM-DD">YYYY-MM-DD (2024-12-31)</option>
                      <option value="DD-MMM-YYYY">DD-MMM-YYYY (31-Dec-2024)</option>
                    </select>
                  </div>

                  <div className="md:col-span-2">
                    <h3 className="text-sm font-medium text-gray-700 mb-3">Currency Preview</h3>
                    <div className="bg-gray-50 p-4 rounded-lg">
                      <div className="grid grid-cols-2 gap-4 text-sm">
                        <div>
                          <span className="text-gray-600">Sample Amount:</span>
                          <div className="font-medium text-lg">
                            {settings.currency === 'INR' ? '₹1,23,456.78' : 
                             settings.currency === 'USD' ? '$12,345.67' :
                             settings.currency === 'EUR' ? '€12,345.67' : 
                             `${settings.currency} 12,345.67`}
                          </div>
                        </div>
                        <div>
                          <span className="text-gray-600">Date Format:</span>
                          <div className="font-medium">
                            {settings.dateFormat === 'DD/MM/YYYY' ? '31/12/2024' :
                             settings.dateFormat === 'MM/DD/YYYY' ? '12/31/2024' :
                             settings.dateFormat === 'YYYY-MM-DD' ? '2024-12-31' :
                             '31-Dec-2024'}
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            )}

            {/* Notification Settings */}
            {activeTab === 'notifications' && (
              <div className="space-y-6">
                <h2 className="text-lg font-medium text-gray-900 border-b border-gray-200 pb-2">
                  Notification Settings
                </h2>
                
                <div className="space-y-4">
                  <div className="flex items-center justify-between">
                    <div>
                      <h3 className="text-sm font-medium text-gray-900">Budget Alerts</h3>
                      <p className="text-sm text-gray-500">Get notified when approaching budget limits</p>
                    </div>
                    <label className="relative inline-flex items-center cursor-pointer">
                      <input
                        type="checkbox"
                        checked={settings.budgetAlerts}
                        onChange={(e) => handleSettingChange('budgetAlerts', e.target.checked)}
                        className="sr-only peer"
                      />
                      <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-primary-300 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-primary-600"></div>
                    </label>
                  </div>

                  <div className="flex items-center justify-between">
                    <div>
                      <h3 className="text-sm font-medium text-gray-900">Transaction Alerts</h3>
                      <p className="text-sm text-gray-500">Get notified about unusual spending patterns</p>
                    </div>
                    <label className="relative inline-flex items-center cursor-pointer">
                      <input
                        type="checkbox"
                        checked={settings.transactionAlerts}
                        onChange={(e) => handleSettingChange('transactionAlerts', e.target.checked)}
                        className="sr-only peer"
                      />
                      <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-primary-300 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-primary-600"></div>
                    </label>
                  </div>

                  <div className="flex items-center justify-between">
                    <div>
                      <h3 className="text-sm font-medium text-gray-900">Monthly Reports</h3>
                      <p className="text-sm text-gray-500">Receive monthly financial summary reports</p>
                    </div>
                    <label className="relative inline-flex items-center cursor-pointer">
                      <input
                        type="checkbox"
                        checked={settings.monthlyReports}
                        onChange={(e) => handleSettingChange('monthlyReports', e.target.checked)}
                        className="sr-only peer"
                      />
                      <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-primary-300 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-primary-600"></div>
                    </label>
                  </div>

                  <div className="flex items-center justify-between">
                    <div>
                      <h3 className="text-sm font-medium text-gray-900">Email Notifications</h3>
                      <p className="text-sm text-gray-500">Receive notifications via email</p>
                    </div>
                    <label className="relative inline-flex items-center cursor-pointer">
                      <input
                        type="checkbox"
                        checked={settings.emailNotifications}
                        onChange={(e) => handleSettingChange('emailNotifications', e.target.checked)}
                        className="sr-only peer"
                      />
                      <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-primary-300 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-primary-600"></div>
                    </label>
                  </div>
                </div>

                <div className="bg-blue-50 p-4 rounded-lg">
                  <h3 className="text-sm font-medium text-blue-900 mb-2">Notification Frequency</h3>
                  <div className="space-y-2">
                    <label className="flex items-center">
                      <input type="radio" name="frequency" value="instant" className="mr-2" defaultChecked />
                      <span className="text-sm text-blue-800">Instant (Real-time)</span>
                    </label>
                    <label className="flex items-center">
                      <input type="radio" name="frequency" value="daily" className="mr-2" />
                      <span className="text-sm text-blue-800">Daily Summary</span>
                    </label>
                    <label className="flex items-center">
                      <input type="radio" name="frequency" value="weekly" className="mr-2" />
                      <span className="text-sm text-blue-800">Weekly Summary</span>
                    </label>
                  </div>
                </div>
              </div>
            )}

            {/* Security Settings */}
            {activeTab === 'security' && (
              <div className="space-y-6">
                <h2 className="text-lg font-medium text-gray-900 border-b border-gray-200 pb-2">
                  Security Settings
                </h2>
                
                <div className="space-y-6">
                  <div className="bg-green-50 p-4 rounded-lg">
                    <div className="flex items-center">
                      <ShieldCheckIcon className="h-5 w-5 text-green-500 mr-2" />
                      <span className="text-sm font-medium text-green-800">Your account is secure</span>
                    </div>
                    <p className="text-sm text-green-700 mt-1">
                      Last login: Today at 10:30 AM from Mumbai, India
                    </p>
                  </div>

                  <div className="space-y-4">
                    <div>
                      <h3 className="text-sm font-medium text-gray-900 mb-3">Password Settings</h3>
                      <button className="btn-secondary">
                        Change Password
                      </button>
                    </div>

                    <div>
                      <h3 className="text-sm font-medium text-gray-900 mb-3">Two-Factor Authentication</h3>
                      <div className="flex items-center justify-between p-3 border border-gray-200 rounded-lg">
                        <div>
                          <span className="text-sm font-medium">SMS Authentication</span>
                          <p className="text-xs text-gray-500">Receive codes via SMS</p>
                        </div>
                        <button className="btn-secondary text-sm">
                          Enable
                        </button>
                      </div>
                    </div>

                    <div>
                      <h3 className="text-sm font-medium text-gray-900 mb-3">Active Sessions</h3>
                      <div className="space-y-2">
                        <div className="flex items-center justify-between p-3 border border-gray-200 rounded-lg">
                          <div>
                            <span className="text-sm font-medium">Current Device</span>
                            <p className="text-xs text-gray-500">Chrome on Windows • Mumbai, India</p>
                          </div>
                          <span className="text-xs text-green-600 font-medium">Active</span>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            )}

            {/* Profile Settings */}
            {activeTab === 'profile' && (
              <div className="space-y-6">
                <h2 className="text-lg font-medium text-gray-900 border-b border-gray-200 pb-2">
                  Profile Settings
                </h2>
                
                <div className="space-y-6">
                  <div className="flex items-center space-x-6">
                    <div className="flex-shrink-0">
                      <div className="h-20 w-20 rounded-full bg-gray-300 flex items-center justify-center">
                        <UserIcon className="h-8 w-8 text-gray-600" />
                      </div>
                    </div>
                    <div>
                      <button className="btn-secondary">
                        Change Photo
                      </button>
                      <p className="text-xs text-gray-500 mt-1">
                        JPG, GIF or PNG. Max size of 2MB.
                      </p>
                    </div>
                  </div>

                  <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-2">
                        Full Name
                      </label>
                      <input
                        type="text"
                        defaultValue={user?.data?.full_name || ''}
                        className="input-field"
                      />
                    </div>

                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-2">
                        Email Address
                      </label>
                      <input
                        type="email"
                        defaultValue={user?.data?.email || ''}
                        className="input-field"
                        disabled
                      />
                      <p className="text-xs text-gray-500 mt-1">
                        Contact support to change your email address
                      </p>
                    </div>

                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-2">
                        Phone Number
                      </label>
                      <input
                        type="tel"
                        placeholder="+91 98765 43210"
                        className="input-field"
                      />
                    </div>

                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-2">
                        Location
                      </label>
                      <input
                        type="text"
                        placeholder="Mumbai, India"
                        className="input-field"
                      />
                    </div>
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      About
                    </label>
                    <textarea
                      rows={3}
                      className="input-field"
                      placeholder="Tell us about yourself..."
                    />
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}