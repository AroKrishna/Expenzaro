import React, { useState } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { useForm } from 'react-hook-form';
import { categoriesAPI, Category } from '../lib/api';
import { XMarkIcon } from '@heroicons/react/24/outline';

interface CategoryModalProps {
  category?: Category | null;
  onClose: () => void;
}

interface FormData {
  name: string;
  type: 'income' | 'expense';
  description?: string;
}

export default function CategoryModal({ category, onClose }: CategoryModalProps) {
  const [isSubmitting, setIsSubmitting] = useState(false);
  const queryClient = useQueryClient();

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<FormData>({
    defaultValues: {
      name: category?.name || '',
      type: category?.type || 'expense',
      description: category?.description || '',
    },
  });

  const createMutation = useMutation({
    mutationFn: categoriesAPI.create,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['categories'] });
      onClose();
    },
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: number; data: Partial<FormData> }) =>
      categoriesAPI.update(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['categories'] });
      onClose();
    },
  });

  const onSubmit = async (data: FormData) => {
    setIsSubmitting(true);
    try {
      if (category?.id) {
        await updateMutation.mutateAsync({
          id: category.id,
          data: {
            name: data.name,
            description: data.description,
          },
        });
      } else {
        await createMutation.mutateAsync(data);
      }
    } catch (error) {
      console.error('Error saving category:', error);
    } finally {
      setIsSubmitting(false);
    }
  };

  const errorMessage = 
    (createMutation.error as any)?.response?.data?.detail ||
    (updateMutation.error as any)?.response?.data?.detail ||
    null;

  return (
    <div className="fixed inset-0 bg-gray-600 bg-opacity-50 overflow-y-auto h-full w-full z-50">
      <div className="relative top-20 mx-auto p-5 border w-full max-w-md shadow-lg rounded-md bg-white">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-medium text-gray-900">
            {category ? 'Edit Category' : 'Create Category'}
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
              Category Name *
            </label>
            <input
              type="text"
              {...register('name', { 
                required: 'Category name is required',
                minLength: { value: 2, message: 'Name must be at least 2 characters' },
                maxLength: { value: 50, message: 'Name must be less than 50 characters' }
              })}
              className="input-field"
              placeholder="Enter category name"
            />
            {errors.name && (
              <p className="mt-1 text-sm text-danger-600">{errors.name.message}</p>
            )}
          </div>

          {!category && (
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Category Type *
              </label>
              <select
                {...register('type', { required: 'Type is required' })}
                className="input-field"
              >
                <option value="expense">Expense</option>
                <option value="income">Income</option>
              </select>
              {errors.type && (
                <p className="mt-1 text-sm text-danger-600">{errors.type.message}</p>
              )}
            </div>
          )}

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Description (Optional)
            </label>
            <textarea
              {...register('description', {
                maxLength: { value: 200, message: 'Description must be less than 200 characters' }
              })}
              rows={3}
              className="input-field"
              placeholder="Enter category description"
            />
            {errors.description && (
              <p className="mt-1 text-sm text-danger-600">{errors.description.message}</p>
            )}
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
              {isSubmitting ? 'Saving...' : category ? 'Update' : 'Create'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}