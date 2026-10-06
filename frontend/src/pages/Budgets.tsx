import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { budgetsAPI, Budget } from '../lib/api';
import { formatCurrency, formatPercentage, getBudgetStatusColor } from '../utils/format';
import BudgetModal from '../components/BudgetModal';
import {
  PlusIcon,
  PencilIcon,
  TrashIcon,
  ExclamationTriangleIcon,
  ChartBarIcon,
} from '@heroicons/react/24/outline';

export default function Budgets() {
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingBudget, setEditingBudget] = useState<Budget | null>(null);

  const queryClient = useQueryClient();

  const { data: budgets, isLoading, error } = useQuery({
    queryKey: ['budgets'],
    queryFn: () => budgetsAPI.getAll(),
  });

  const deleteMutation = useMutation({
    mutationFn: budgetsAPI.delete,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['budgets'] });
      queryClient.invalidateQueries({ queryKey: ['dashboard-overview'] });
    },
  });

  const handleEdit = (budget: Budget) => {
    setEditingBudget(budget);
    setIsModalOpen(true);
  };

  const handleDelete = (id: number) => {
    if (confirm('Are you sure you want to delete this budget?')) {
      deleteMutation.mutate(id);
    }
  };

  const handleModalClose = () => {
    setIsModalOpen(false);
    setEditingBudget(null);
  };

  const budgetData = budgets?.data || [];

  if (error) {
    return (
      <div className="bg-danger-50 border border-danger-200 rounded-md p-4">
        <div className="flex">
          <ExclamationTriangleIcon className="h-5 w-5 text-danger-400" />
          <div className="ml-3">
            <h3 className="text-sm font-medium text-danger-800">
              Error loading budgets
            </h3>
            <div className="mt-2 text-sm text-danger-700">
              Failed to load budget data. Please try again.
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between">
        <h1 className="text-2xl font-bold text-gray-900">Budgets</h1>
        <button
          onClick={() => setIsModalOpen(true)}
          className="btn-primary mt-4 sm:mt-0"
        >
          <PlusIcon className="h-5 w-5 mr-2" />
          Add Budget
        </button>
      </div>

      {/* Budget Cards */}
      {isLoading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {[...Array(6)].map((_, i) => (
            <div key={i} className="card animate-pulse">
              <div className="h-4 bg-gray-200 rounded mb-4"></div>
              <div className="h-8 bg-gray-200 rounded mb-2"></div>
              <div className="h-2 bg-gray-200 rounded mb-4"></div>
              <div className="h-4 bg-gray-200 rounded w-1/2"></div>
            </div>
          ))}
        </div>
      ) : budgetData.length > 0 ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {budgetData.map((budget: Budget) => (
            <BudgetCard
              key={budget.id}
              budget={budget}
              onEdit={handleEdit}
              onDelete={handleDelete}
              isDeleting={deleteMutation.isPending}
            />
          ))}
        </div>
      ) : (
        <div className="card text-center py-12">
          <div className="text-gray-500 mb-4">
            <ChartBarIcon className="h-12 w-12 mx-auto mb-4 text-gray-300" />
            <h3 className="text-lg font-medium text-gray-900 mb-2">No budgets found</h3>
            <p className="text-gray-500">
              Get started by creating your first budget to track your spending.
            </p>
          </div>
          <button
            onClick={() => setIsModalOpen(true)}
            className="btn-primary"
          >
            <PlusIcon className="h-5 w-5 mr-2" />
            Create Budget
          </button>
        </div>
      )}

      {/* Budget Modal */}
      {isModalOpen && (
        <BudgetModal
          budget={editingBudget}
          onClose={handleModalClose}
        />
      )}
    </div>
  );
}

interface BudgetCardProps {
  budget: Budget;
  onEdit: (budget: Budget) => void;
  onDelete: (id: number) => void;
  isDeleting: boolean;
}

function BudgetCard({ budget, onEdit, onDelete, isDeleting }: BudgetCardProps) {
  const getProgressBarColor = (percentage: number): string => {
    if (percentage >= 100) return 'bg-danger-600';
    if (percentage >= 80) return 'bg-warning-600';
    return 'bg-success-600';
  };

  const getStatusBadge = (budget: Budget) => {
    if (!budget.is_active) {
      return (
        <span className="inline-flex px-2 py-1 text-xs font-semibold rounded-full bg-gray-100 text-gray-800">
          Inactive
        </span>
      );
    }
    
    if (budget.percentage_used >= 100) {
      return (
        <span className="inline-flex px-2 py-1 text-xs font-semibold rounded-full bg-danger-100 text-danger-800">
          Exceeded
        </span>
      );
    }
    
    if (budget.percentage_used >= 80) {
      return (
        <span className="inline-flex px-2 py-1 text-xs font-semibold rounded-full bg-warning-100 text-warning-800">
          Warning
        </span>
      );
    }
    
    return (
      <span className="inline-flex px-2 py-1 text-xs font-semibold rounded-full bg-success-100 text-success-800">
        On Track
      </span>
    );
  };

  return (
    <div className="card">
      <div className="flex items-start justify-between mb-4">
        <div className="flex-1">
          <h3 className="text-lg font-semibold text-gray-900 mb-1">
            {budget.category_name}
          </h3>
          <div className="flex items-center space-x-2">
            {getStatusBadge(budget)}
            <span className="text-sm text-gray-500 capitalize">
              {budget.period}
            </span>
          </div>
        </div>
        <div className="flex items-center space-x-1">
          <button
            onClick={() => onEdit(budget)}
            className="p-1 text-gray-400 hover:text-gray-600"
          >
            <PencilIcon className="h-4 w-4" />
          </button>
          <button
            onClick={() => onDelete(budget.id)}
            className="p-1 text-gray-400 hover:text-danger-600"
            disabled={isDeleting}
          >
            <TrashIcon className="h-4 w-4" />
          </button>
        </div>
      </div>

      <div className="space-y-3">
        <div className="flex justify-between text-sm">
          <span className="text-gray-500">Spent</span>
          <span className="font-medium text-gray-900">
            {formatCurrency(budget.spent_amount)} of {formatCurrency(budget.amount)}
          </span>
        </div>

        <div className="w-full bg-gray-200 rounded-full h-2">
          <div
            className={`h-2 rounded-full transition-all duration-300 ${getProgressBarColor(budget.percentage_used)}`}
            style={{ width: `${Math.min(budget.percentage_used, 100)}%` }}
          />
        </div>

        <div className="flex justify-between items-center text-sm">
          <span className={`font-medium ${getBudgetStatusColor(budget.percentage_used)}`}>
            {formatPercentage(budget.percentage_used)} used
          </span>
          <span className="text-gray-500">
            {formatCurrency(budget.amount - budget.spent_amount)} remaining
          </span>
        </div>
      </div>
    </div>
  );
}