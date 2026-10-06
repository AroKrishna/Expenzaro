import React, { useState, useEffect } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useForm } from 'react-hook-form';
import { transactionsAPI, categoriesAPI, Transaction, TransactionCreate, Category } from '../lib/api';
import { formatDateForInput } from '../utils/format';
import { XMarkIcon } from '@heroicons/react/24/outline';

interface TransactionModalProps {
  transaction?: Transaction | null;
  onClose: () => void;
}

interface FormData extends TransactionCreate {
  amount: number;
}

export default function TransactionModal({ transaction, onClose }: TransactionModalProps) {
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
    reset,
    watch,
  } = useForm<FormData>({
    defaultValues: {
      description: transaction?.description || '',
      amount: transaction ? Math.abs(transaction.amount) : 0,
      date: transaction ? formatDateForInput(transaction.date) : formatDateForInput(new Date()),
      transaction_type: transaction?.transaction_type || 'expense',
      category_id: transaction?.category_id || undefined,
      merchant: transaction?.merchant || '',
      notes: transaction?.notes || '',
    },
  });

  const transactionType = watch('transaction_type');

  const createMutation = useMutation({
    mutationFn: transactionsAPI.create,
    onSuccess: (data) => {
      console.log('✅ Create mutation success callback triggered', data);
      try {
        queryClient.invalidateQueries({ queryKey: ['transactions'] });
        queryClient.invalidateQueries({ queryKey: ['dashboard-overview'] });
        console.log('🔄 Queries invalidated, closing modal...');
        onClose();
        console.log('🚪 Modal close callback called');
      } catch (error) {
        console.error('😱 Error in success callback:', error);
        // Still close the modal even if there's an error
        onClose();
      }
    },
    onError: (error) => {
      console.error('❌ Create mutation error:', error);
      // Don't close modal on error, let user see the error
    }
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: number; data: Partial<TransactionCreate> }) =>
      transactionsAPI.update(id, data),
    onSuccess: (data) => {
      console.log('✅ Update mutation success callback triggered', data);
      queryClient.invalidateQueries({ queryKey: ['transactions'] });
      queryClient.invalidateQueries({ queryKey: ['dashboard-overview'] });
      console.log('🔄 Queries invalidated, closing modal...');
      onClose();
      console.log('🚪 Modal close callback called');
    },
    onError: (error) => {
      console.error('❌ Update mutation error:', error);
    }
  });

  const onSubmit = async (data: FormData) => {
    setIsSubmitting(true);
    console.log('🎯 Starting transaction submission...', data);
    try {
      const transactionData: TransactionCreate = {
        ...data,
        amount: Math.abs(data.amount), // Always send positive amount
        category_id: data.category_id,
      };
      
      console.log('📊 Transaction data prepared:', transactionData);

      if (transaction?.id) {
        console.log('✏️ Updating existing transaction...');
        await updateMutation.mutateAsync({
          id: transaction.id,
          data: transactionData,
        });
        console.log('✅ Transaction updated successfully');
      } else {
        console.log('➕ Creating new transaction...');
        const result = await createMutation.mutateAsync(transactionData);
        console.log('✅ Transaction created successfully:', result);
      }
      
      console.log('🎉 Transaction operation completed successfully!');
    } catch (error: any) {
      console.error('❌ Error saving transaction:', error);
      console.error('Error details:', {
        message: error?.message,
        response: error?.response,
        status: error?.response?.status,
        data: error?.response?.data
      });
    } finally {
      setIsSubmitting(false);
    }
  };

  const categoryData = categories?.data || [];
  const filteredCategories = categoryData.filter(
    (category: Category) => category.type === transactionType
  );

  // Extract error message safely
  const getErrorMessage = () => {
    const createError = createMutation.error as any;
    const updateError = updateMutation.error as any;
    
    // Check for API response errors first
    if (createError?.response?.data?.detail) {
      if (Array.isArray(createError.response.data.detail)) {
        return createError.response.data.detail.map((err: any) => err.msg || err.message || err).join(', ');
      }
      return createError.response.data.detail;
    }
    
    if (updateError?.response?.data?.detail) {
      if (Array.isArray(updateError.response.data.detail)) {
        return updateError.response.data.detail.map((err: any) => err.msg || err.message || err).join(', ');
      }
      return updateError.response.data.detail;
    }
    
    // Check for general error messages
    if (createError?.message) return createError.message;
    if (updateError?.message) return updateError.message;
    
    // Default error messages
    if (createError) return 'Failed to save transaction';
    if (updateError) return 'Failed to update transaction';
    
    return null;
  };
  
  const errorMessage = getErrorMessage();

  return (
    <div className="fixed inset-0 bg-gray-600 bg-opacity-50 overflow-y-auto h-full w-full z-50">
      <div className="relative top-20 mx-auto p-5 border w-full max-w-md shadow-lg rounded-md bg-white">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-medium text-gray-900">
            {transaction ? 'Edit Transaction' : 'Add Transaction'}
          </h3>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600"
          >
            <XMarkIcon className="h-6 w-6" />
          </button>
        </div>

        {errorMessage && typeof errorMessage === 'string' && (
          <div className="mb-4 bg-danger-50 border border-danger-200 text-danger-700 px-4 py-3 rounded">
            {errorMessage}
          </div>
        )}

        <form onSubmit={handleSubmit((data: FormData) => onSubmit(data))} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Description *
            </label>
            <input
              type="text"
              {...register('description', { required: 'Description is required' })}
              className="input-field"
              placeholder="Enter transaction description"
            />
            {errors.description && (
              <p className="mt-1 text-sm text-danger-600">{errors.description.message}</p>
            )}
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Amount *
            </label>
            <input
              type="number"
              step="0.01"
              min="0"
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
              Date *
            </label>
            <input
              type="date"
              {...register('date', { required: 'Date is required' })}
              className="input-field"
            />
            {errors.date && (
              <p className="mt-1 text-sm text-danger-600">{errors.date.message}</p>
            )}
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Type *
            </label>
            <select
              {...register('transaction_type', { required: 'Type is required' })}
              className="input-field"
            >
              <option value="expense">Expense</option>
              <option value="income">Income</option>
            </select>
            {errors.transaction_type && (
              <p className="mt-1 text-sm text-danger-600">{errors.transaction_type.message}</p>
            )}
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Category
            </label>
            <select
              {...register('category_id', {
                setValueAs: (value) => value === '' || !value ? undefined : Number(value)
              })}
              className="input-field"
            >
              <option value="">Select a category</option>
              {filteredCategories.map((category: Category) => (
                <option key={category.id} value={category.id}>
                  {category.name}
                </option>
              ))}
            </select>
            {filteredCategories.length === 0 && (
              <p className="mt-1 text-sm text-amber-600">
                No {transactionType} categories available. Create one in the Categories page.
              </p>
            )}
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Merchant
            </label>
            <input
              type="text"
              {...register('merchant')}
              className="input-field"
              placeholder="Enter merchant name"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Notes
            </label>
            <textarea
              {...register('notes')}
              rows={3}
              className="input-field"
              placeholder="Additional notes (optional)"
            />
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
              {isSubmitting ? 'Saving...' : transaction ? 'Update' : 'Create'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}