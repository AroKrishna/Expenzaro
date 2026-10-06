import React, { useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useForm } from 'react-hook-form';
import { budgetsAPI, categoriesAPI, Budget, Category } from '../lib/api';
import { formatDateForInput } from '../utils/format';
import { XMarkIcon } from '@heroicons/react/24/outline';

interface BudgetModalProps {
  budget?: Budget | null;
  onClose: () => void;
}

interface FormData {
  category_id: number;
  amount: number;
  period: 'weekly' | 'monthly' | 'quarterly' | 'yearly';
  start_date: string;
  end_date?: string;
}

export default function BudgetModal({ budget, onClose }: BudgetModalProps) {
  const [isSubmitting, setIsSubmitting] = useState(false);
  const queryClient = useQueryClient();

  const { data: categories } = useQuery({
    queryKey: ['categories'],
    queryFn: () => categoriesAPI.getAll(),
  });

  const {
    register,
    handleSubmit,
    formState: { errors },
    watch,
  } = useForm<FormData>({
    defaultValues: {
      category_id: budget?.category_id || 0,
      amount: budget?.amount || 0,
      period: budget?.period || 'monthly',
      start_date: budget ? formatDateForInput(budget.start_date) : formatDateForInput(new Date()),
      end_date: budget?.end_date ? formatDateForInput(budget.end_date) : '',
    },
  });

  const period = watch('period');

  const createMutation = useMutation({
    mutationFn: budgetsAPI.create,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['budgets'] });
      queryClient.invalidateQueries({ queryKey: ['dashboard-overview'] });
      onClose();
    },
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: number; data: Partial<FormData> }) =>
      budgetsAPI.update(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['budgets'] });
      queryClient.invalidateQueries({ queryKey: ['dashboard-overview'] });
      onClose();
    },
  });

  const onSubmit = async (data: FormData) => {
    setIsSubmitting(true);
    try {
      const budgetData = {
        ...data,
        end_date: data.end_date || undefined,
      };

      if (budget?.id) {
        await updateMutation.mutateAsync({
          id: budget.id,
          data: budgetData,
        });
      } else {
        await createMutation.mutateAsync(budgetData);
      }
    } catch (error) {
      console.error('Error saving budget:', error);
    } finally {
      setIsSubmitting(false);
    }
  };

  const categoryData = categories?.data || [];
  const expenseCategories = categoryData.filter((category: Category) => category.type === 'expense');

  const errorMessage = 
    (createMutation.error as any)?.response?.data?.detail ||
    (updateMutation.error as any)?.response?.data?.detail ||
    null;

  return (
    <div className="fixed inset-0 bg-gray-600 bg-opacity-50 overflow-y-auto h-full w-full z-50">
      <div className="relative top-20 mx-auto p-5 border w-full max-w-md shadow-lg rounded-md bg-white">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-medium text-gray-900">
            {budget ? 'Edit Budget' : 'Create Budget'}
          </h3>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600"
          >
            <XMarkIcon className="h-6 w-6" />
          </button>
        </div>

        {errorMessage && (
          <div className="mb-4 bg-danger-50 border border-danger-200 text-danger-700 px-4 py-3 rounded">
            {errorMessage}
          </div>
        )}

        <form onSubmit={handleSubmit((data: FormData) => onSubmit(data))} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Category *
            </label>
            <select
              {...register('category_id', { 
                required: 'Category is required',
                min: { value: 1, message: 'Please select a category' }
              })}
              className="input-field"
            >
              <option value={0}>Select a category</option>
              {expenseCategories.map((category: Category) => (
                <option key={category.id} value={category.id}>
                  {category.name}
                </option>
              ))}
            </select>
            {errors.category_id && (
              <p className="mt-1 text-sm text-danger-600">{errors.category_id.message}</p>
            )}
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Budget Amount *
            </label>
            <input
              type="number"
              step="0.01"
              min="0.01"
              {...register('amount', { 
                required: 'Amount is required',
                min: { value: 0.01, message: 'Amount must be greater than 0' }
              })}
              className="input-field"
              placeholder="0.00"
            />
            {errors.amount && (
              <p className="mt-1 text-sm text-danger-600">{errors.amount.message}</p>
            )}
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Period *
            </label>
            <select
              {...register('period', { required: 'Period is required' })}
              className="input-field"
            >
              <option value="weekly">Weekly</option>
              <option value="monthly">Monthly</option>
              <option value="yearly">Yearly</option>
            </select>
            {errors.period && (
              <p className="mt-1 text-sm text-danger-600">{errors.period.message}</p>
            )}
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Start Date *
            </label>
            <input
              type="date"
              {...register('start_date', { required: 'Start date is required' })}
              className="input-field"
            />
            {errors.start_date && (
              <p className="mt-1 text-sm text-danger-600">{errors.start_date.message}</p>
            )}
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              End Date (Optional)
            </label>
            <input
              type="date"
              {...register('end_date')}
              className="input-field"
            />
            <p className="mt-1 text-xs text-gray-500">
              Leave empty for ongoing budget
            </p>
          </div>

          <div className="bg-gray-50 rounded-lg p-3 text-sm text-gray-600">
            <p className="font-medium mb-1">Budget Period Information:</p>
            <p>
              {period === 'weekly' && 'This budget will track your weekly spending for the selected category.'}
              {period === 'monthly' && 'This budget will track your monthly spending for the selected category.'}
              {period === 'yearly' && 'This budget will track your yearly spending for the selected category.'}
            </p>
          </div>

          <div className="flex justify-end space-x-3 pt-4">
            <button
              type="button"
              onClick={onClose}
              className="btn-secondary"
              disabled={isSubmitting}
            >
              Cancel
            </button>
            <button
              type="submit"
              className="btn-primary"
              disabled={isSubmitting}
            >
              {isSubmitting ? 'Saving...' : budget ? 'Update Budget' : 'Create Budget'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}