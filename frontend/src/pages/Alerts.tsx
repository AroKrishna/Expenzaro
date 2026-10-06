import React from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { alertsAPI, Alert } from '../lib/api';
import { formatRelativeTime, getAlertPriorityColor, capitalize } from '../utils/format';
import {
  BellIcon,
  CheckCircleIcon,
  TrashIcon,
  ExclamationTriangleIcon,
} from '@heroicons/react/24/outline';

export default function Alerts() {
  const queryClient = useQueryClient();

  const { data: alerts, isLoading, error } = useQuery({
    queryKey: ['alerts'],
    queryFn: () => alertsAPI.getAll({ limit: 50 }),
  });

  const markAsReadMutation = useMutation({
    mutationFn: alertsAPI.markAsRead,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['alerts'] });
    },
  });

  const deleteMutation = useMutation({
    mutationFn: alertsAPI.delete,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['alerts'] });
    },
  });

  const handleMarkAsRead = (id: number) => {
    markAsReadMutation.mutate(id);
  };

  const handleDelete = (id: number) => {
    if (confirm('Are you sure you want to delete this alert?')) {
      deleteMutation.mutate(id);
    }
  };

  const alertData = alerts?.data || [];
  const unreadAlerts = alertData.filter((alert: Alert) => !alert.is_read);
  const readAlerts = alertData.filter((alert: Alert) => alert.is_read);

  if (error) {
    return (
      <div className="bg-danger-50 border border-danger-200 rounded-md p-4">
        <div className="flex">
          <ExclamationTriangleIcon className="h-5 w-5 text-danger-400" />
          <div className="ml-3">
            <h3 className="text-sm font-medium text-danger-800">
              Error loading alerts
            </h3>
            <div className="mt-2 text-sm text-danger-700">
              Failed to load alert data. Please try again.
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center">
          <h1 className="text-2xl font-bold text-gray-900">Alerts</h1>
          {unreadAlerts.length > 0 && (
            <span className="ml-3 inline-flex items-center px-3 py-1 rounded-full text-sm font-medium bg-primary-100 text-primary-800">
              {unreadAlerts.length} unread
            </span>
          )}
        </div>
      </div>

      {isLoading ? (
        <div className="space-y-4">
          {[...Array(5)].map((_, i) => (
            <div key={i} className="card animate-pulse">
              <div className="flex items-start space-x-3">
                <div className="h-6 w-6 bg-gray-200 rounded-full"></div>
                <div className="flex-1">
                  <div className="h-4 bg-gray-200 rounded mb-2"></div>
                  <div className="h-3 bg-gray-200 rounded w-3/4"></div>
                </div>
              </div>
            </div>
          ))}
        </div>
      ) : alertData.length > 0 ? (
        <div className="space-y-6">
          {/* Unread Alerts */}
          {unreadAlerts.length > 0 && (
            <div>
              <h2 className="text-lg font-semibold text-gray-900 mb-4">Unread Alerts</h2>
              <div className="space-y-3">
                {unreadAlerts.map((alert: Alert) => (
                  <AlertCard
                    key={alert.id}
                    alert={alert}
                    onMarkAsRead={handleMarkAsRead}
                    onDelete={handleDelete}
                    isProcessing={markAsReadMutation.isPending || deleteMutation.isPending}
                  />
                ))}
              </div>
            </div>
          )}

          {/* Read Alerts */}
          {readAlerts.length > 0 && (
            <div>
              <h2 className="text-lg font-semibold text-gray-900 mb-4">
                Recent Alerts
                <span className="ml-2 text-sm font-normal text-gray-500">
                  ({readAlerts.length})
                </span>
              </h2>
              <div className="space-y-3">
                {readAlerts.slice(0, 10).map((alert: Alert) => (
                  <AlertCard
                    key={alert.id}
                    alert={alert}
                    onMarkAsRead={handleMarkAsRead}
                    onDelete={handleDelete}
                    isProcessing={markAsReadMutation.isPending || deleteMutation.isPending}
                  />
                ))}
              </div>
            </div>
          )}
        </div>
      ) : (
        <div className="card text-center py-12">
          <BellIcon className="h-12 w-12 mx-auto text-gray-300 mb-4" />
          <h3 className="text-lg font-medium text-gray-900 mb-2">No alerts</h3>
          <p className="text-gray-500">
            You're all caught up! Alerts will appear here when there are budget overruns or unusual spending patterns.
          </p>
        </div>
      )}
    </div>
  );
}

interface AlertCardProps {
  alert: Alert;
  onMarkAsRead: (id: number) => void;
  onDelete: (id: number) => void;
  isProcessing: boolean;
}

function AlertCard({ alert, onMarkAsRead, onDelete, isProcessing }: AlertCardProps) {
  const priorityClass = getAlertPriorityColor(alert.priority);

  return (
    <div className={`card border-l-4 ${alert.is_read ? 'opacity-75' : ''} ${
      alert.priority === 'critical' ? 'border-l-danger-500' :
      alert.priority === 'high' ? 'border-l-danger-400' :
      alert.priority === 'medium' ? 'border-l-warning-400' :
      'border-l-primary-400'
    }`}>
      <div className="flex items-start space-x-3">
        <div className="flex-shrink-0">
          <div className={`w-2 h-2 rounded-full mt-2 ${
            alert.is_read ? 'bg-gray-300' : 'bg-primary-500'
          }`} />
        </div>
        
        <div className="flex-1 min-w-0">
          <div className="flex items-start justify-between">
            <div className="flex-1">
              <div className="flex items-center space-x-2 mb-1">
                <h3 className={`font-medium ${alert.is_read ? 'text-gray-700' : 'text-gray-900'}`}>
                  {alert.title}
                </h3>
                <span className={`inline-flex px-2 py-1 text-xs font-semibold rounded-full ${priorityClass}`}>
                  {capitalize(alert.priority)}
                </span>
              </div>
              <p className={`text-sm ${alert.is_read ? 'text-gray-500' : 'text-gray-700'}`}>
                {alert.message}
              </p>
              <p className="text-xs text-gray-400 mt-1">
                {formatRelativeTime(alert.created_at)}
              </p>
            </div>

            <div className="flex items-center space-x-2 ml-4">
              {!alert.is_read && (
                <button
                  onClick={() => onMarkAsRead(alert.id)}
                  className="p-1 text-gray-400 hover:text-success-600 rounded"
                  disabled={isProcessing}
                  title="Mark as read"
                >
                  <CheckCircleIcon className="h-4 w-4" />
                </button>
              )}
              <button
                onClick={() => onDelete(alert.id)}
                className="p-1 text-gray-400 hover:text-danger-600 rounded"
                disabled={isProcessing}
                title="Delete alert"
              >
                <TrashIcon className="h-4 w-4" />
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}