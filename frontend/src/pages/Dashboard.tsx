import React, { useState, useEffect } from 'react';
import { useQuery } from '@tanstack/react-query';
import { dashboardAPI, DashboardOverview } from '../lib/api';
import { formatCurrency, formatPercentage, formatDate } from '../utils/format';
import {
  BanknotesIcon,
  ArrowTrendingUpIcon,
  ArrowTrendingDownIcon,
  ExclamationTriangleIcon,
} from '@heroicons/react/24/outline';
import { Chart as ChartJS, CategoryScale, LinearScale, BarElement, Title, Tooltip, Legend, ArcElement } from 'chart.js';
import { Bar, Doughnut } from 'react-chartjs-2';

// Register ChartJS components
ChartJS.register(CategoryScale, LinearScale, BarElement, Title, Tooltip, Legend, ArcElement);

export default function Dashboard() {
  const [periodDays, setPeriodDays] = useState(30);

  const { data: overview, isLoading, error, refetch } = useQuery({
    queryKey: ['dashboard-overview', periodDays],
    queryFn: () => dashboardAPI.getOverview({ period_days: periodDays }),
    retry: 2,
  });

  if (isLoading) {
    return (
      <div className="animate-pulse">
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
          {[...Array(4)].map((_, i) => (
            <div key={i} className="bg-white p-6 rounded-lg shadow-card">
              <div className="h-4 bg-gray-200 rounded mb-4"></div>
              <div className="h-8 bg-gray-200 rounded mb-2"></div>
              <div className="h-3 bg-gray-200 rounded w-1/2"></div>
            </div>
          ))}
        </div>
      </div>
    );
  }

  if (error) {
    console.error('Dashboard error details:', error);
    return (
      <div className="bg-danger-50 border border-danger-200 rounded-md p-4">
        <div className="flex">
          <ExclamationTriangleIcon className="h-5 w-5 text-danger-400" />
          <div className="ml-3">
            <h3 className="text-sm font-medium text-danger-800">
              Error loading dashboard
            </h3>
            <div className="mt-2 text-sm text-danger-700">
              Failed to load dashboard data. Please try again.
            </div>
            <div className="mt-3">
              <button
                onClick={() => refetch()}
                className="text-sm bg-danger-100 hover:bg-danger-200 text-danger-800 px-3 py-1 rounded"
              >
                Retry
              </button>
            </div>
          </div>
        </div>
      </div>
    );
  }

  const dashboardData = (overview as any)?.data;

  if (!dashboardData) {
    return <div className="text-center py-20 text-gray-500">No data available</div>;
  }

  // Chart data for spending by category
  const categoryChartData = {
    labels: (dashboardData?.spending_by_category || []).map((item: any) => item.category_name),
    datasets: [
      {
        data: (dashboardData?.spending_by_category || []).map((item: any) => item.amount),
        backgroundColor: [
          '#3B82F6',
          '#10B981',
          '#F59E0B',
          '#EF4444',
          '#8B5CF6',
          '#06B6D4',
          '#F97316',
          '#84CC16',
        ],
        borderWidth: 0,
      },
    ],
  };

  const chartOptions = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        position: 'bottom' as const,
      },
    },
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between">
        <h1 className="text-2xl font-bold text-gray-900">Dashboard</h1>
        <div className="mt-4 sm:mt-0">
          <select
            value={periodDays}
            onChange={(e) => setPeriodDays(Number(e.target.value))}
            className="input-field"
          >
            <option value={7}>Last 7 days</option>
            <option value={30}>Last 30 days</option>
            <option value={90}>Last 90 days</option>
            <option value={365}>Last year</option>
          </select>
        </div>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <SummaryCard
          title="Total Income"
          value={formatCurrency(dashboardData?.financial_summary?.total_income || 0)}
          icon={<ArrowTrendingUpIcon className="h-6 w-6" />}
          color="success"
        />
        <SummaryCard
          title="Total Expenses"
          value={formatCurrency(dashboardData?.financial_summary?.total_expenses || 0)}
          icon={<ArrowTrendingDownIcon className="h-6 w-6" />}
          color="danger"
        />
        <SummaryCard
          title="Net Amount"
          value={formatCurrency(dashboardData?.financial_summary?.net_amount || 0)}
          icon={<BanknotesIcon className="h-6 w-6" />}
          color={(dashboardData?.financial_summary?.net_amount || 0) >= 0 ? "success" : "danger"}
        />
        <SummaryCard
          title="Savings Rate"
          value={formatPercentage(dashboardData?.financial_summary?.savings_rate || 0)}
          icon={<ArrowTrendingUpIcon className="h-6 w-6" />}
          color="primary"
        />
      </div>

      {/* Charts and Recent Transactions */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Spending by Category Chart */}
        <div className="card">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">
            Spending by Category
          </h2>
          {(dashboardData?.spending_by_category || []).length > 0 ? (
            <div className="h-64">
              <Doughnut data={categoryChartData} options={chartOptions} />
            </div>
          ) : (
            <div className="h-64 flex items-center justify-center text-gray-500">
              No spending data available for this period
            </div>
          )}
        </div>

        {/* Recent Transactions */}
        <div className="card">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">
            Recent Transactions
          </h2>
          <div className="space-y-3">
            {(dashboardData?.recent_transactions || []).length > 0 ? (
              (dashboardData?.recent_transactions || []).slice(0, 5).map((transaction: any) => (
                <div
                  key={transaction.id}
                  className="flex items-center justify-between p-3 bg-gray-50 rounded-lg"
                >
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-gray-900 truncate">
                      {transaction.description}
                    </p>
                    <p className="text-xs text-gray-500">
                      {transaction.category_name || 'Uncategorized'} • {formatDate(transaction.date)}
                    </p>
                  </div>
                  <div className={`text-sm font-medium ${
                    transaction.transaction_type === 'income' 
                      ? 'text-success-600' 
                      : 'text-danger-600'
                  }`}>
                    {transaction.transaction_type === 'income' ? '+' : '-'}
                    {formatCurrency(Math.abs(transaction.amount))}
                  </div>
                </div>
              ))
            ) : (
              <div className="text-center text-gray-500 py-8">
                No recent transactions
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Budget Overview */}
      <div className="card">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">
          Budget Overview
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          <div className="text-center">
            <div className="text-2xl font-bold text-gray-900">
              {dashboardData?.budget_summary?.total_budgets || 0}
            </div>
            <div className="text-sm text-gray-500">Total Budgets</div>
          </div>
          <div className="text-center">
            <div className="text-2xl font-bold text-success-600">
              {dashboardData?.budget_summary?.active_budgets || 0}
            </div>
            <div className="text-sm text-gray-500">Active Budgets</div>
          </div>
          <div className="text-center">
            <div className="text-2xl font-bold text-warning-600">
              {dashboardData?.budget_summary?.warning_budgets || 0}
            </div>
            <div className="text-sm text-gray-500">Warning Budgets</div>
          </div>
          <div className="text-center">
            <div className="text-2xl font-bold text-danger-600">
              {dashboardData?.budget_summary?.exceeded_budgets || 0}
            </div>
            <div className="text-sm text-gray-500">Exceeded Budgets</div>
          </div>
        </div>
      </div>

      {/* Alerts Summary */}
      {(dashboardData?.alert_summary?.total_alerts || 0) > 0 && (
        <div className="card">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">
            Alert Summary
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="text-center">
              <div className="text-2xl font-bold text-gray-900">
                {dashboardData?.alert_summary?.total_alerts || 0}
              </div>
              <div className="text-sm text-gray-500">Total Alerts</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold text-primary-600">
                {dashboardData?.alert_summary?.unread_alerts || 0}
              </div>
              <div className="text-sm text-gray-500">Unread Alerts</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold text-danger-600">
                {dashboardData?.alert_summary?.critical_alerts || 0}
              </div>
              <div className="text-sm text-gray-500">Critical Alerts</div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

interface SummaryCardProps {
  title: string;
  value: string;
  icon: React.ReactNode;
  color: 'primary' | 'success' | 'danger' | 'warning';
}

function SummaryCard({ title, value, icon, color }: SummaryCardProps) {
  const colorClasses = {
    primary: 'text-primary-600 bg-primary-50',
    success: 'text-success-600 bg-success-50',
    danger: 'text-danger-600 bg-danger-50',
    warning: 'text-warning-600 bg-warning-50',
  };

  return (
    <div className="card">
      <div className="flex items-center">
        <div className={`p-2 rounded-lg ${colorClasses[color]}`}>
          {icon}
        </div>
        <div className="ml-4">
          <h3 className="text-sm font-medium text-gray-500">{title}</h3>
          <p className="text-2xl font-semibold text-gray-900">{value}</p>
        </div>
      </div>
    </div>
  );
}