import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { categoriesAPI, Category } from '../lib/api';
import CategoryModal from '../components/CategoryModal';
import {
  PlusIcon,
  PencilIcon,
  TrashIcon,
  FolderIcon,
  ExclamationTriangleIcon,
} from '@heroicons/react/24/outline';

export default function Categories() {
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingCategory, setEditingCategory] = useState<Category | null>(null);

  const queryClient = useQueryClient();

  const { data: categories, isLoading, error } = useQuery({
    queryKey: ['categories'],
    queryFn: () => categoriesAPI.getAll(),
  });

  const deleteMutation = useMutation({
    mutationFn: categoriesAPI.delete,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['categories'] });
      queryClient.invalidateQueries({ queryKey: ['transactions'] });
    },
  });

  const handleEdit = (category: Category) => {
    setEditingCategory(category);
    setIsModalOpen(true);
  };

  const handleDelete = (id: number) => {
    if (confirm('Are you sure you want to delete this category? This action cannot be undone.')) {
      deleteMutation.mutate(id);
    }
  };

  const handleModalClose = () => {
    setIsModalOpen(false);
    setEditingCategory(null);
  };

  const categoryData = categories?.data || [];
  const incomeCategories = categoryData.filter((cat: Category) => cat.type === 'income');
  const expenseCategories = categoryData.filter((cat: Category) => cat.type === 'expense');

  if (error) {
    return (
      <div className="bg-danger-50 border border-danger-200 rounded-md p-4">
        <div className="flex">
          <ExclamationTriangleIcon className="h-5 w-5 text-danger-400" />
          <div className="ml-3">
            <h3 className="text-sm font-medium text-danger-800">
              Error loading categories
            </h3>
            <div className="mt-2 text-sm text-danger-700">
              Failed to load category data. Please try again.
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
        <h1 className="text-2xl font-bold text-gray-900">Categories</h1>
        <button
          onClick={() => setIsModalOpen(true)}
          className="btn-primary mt-4 sm:mt-0"
        >
          <PlusIcon className="h-5 w-5 mr-2" />
          Add Category
        </button>
      </div>

      {/* Categories Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Income Categories */}
        <CategorySection
          title="Income Categories"
          type="income"
          categories={incomeCategories}
          isLoading={isLoading}
          onEdit={handleEdit}
          onDelete={handleDelete}
          isDeleting={deleteMutation.isPending}
        />

        {/* Expense Categories */}
        <CategorySection
          title="Expense Categories"
          type="expense"
          categories={expenseCategories}
          isLoading={isLoading}
          onEdit={handleEdit}
          onDelete={handleDelete}
          isDeleting={deleteMutation.isPending}
        />
      </div>

      {/* Category Modal */}
      {isModalOpen && (
        <CategoryModal
          category={editingCategory}
          onClose={handleModalClose}
        />
      )}
    </div>
  );
}

interface CategorySectionProps {
  title: string;
  type: 'income' | 'expense';
  categories: Category[];
  isLoading: boolean;
  onEdit: (category: Category) => void;
  onDelete: (id: number) => void;
  isDeleting: boolean;
}

function CategorySection({
  title,
  type,
  categories,
  isLoading,
  onEdit,
  onDelete,
  isDeleting
}: CategorySectionProps) {
  const colorClass = type === 'income' ? 'text-success-600' : 'text-danger-600';

  return (
    <div className="card">
      <div className="flex items-center mb-4">
        <FolderIcon className={`h-6 w-6 mr-2 ${colorClass}`} />
        <h2 className="text-lg font-semibold text-gray-900">{title}</h2>
        <span className="ml-2 text-sm text-gray-500">({categories.length})</span>
      </div>

      {isLoading ? (
        <div className="space-y-3">
          {[...Array(3)].map((_, i) => (
            <div key={i} className="animate-pulse">
              <div className="h-12 bg-gray-200 rounded"></div>
            </div>
          ))}
        </div>
      ) : categories.length > 0 ? (
        <div className="space-y-2">
          {categories.map((category) => (
            <div
              key={category.id}
              className="flex items-center justify-between p-3 bg-gray-50 rounded-lg hover:bg-gray-100 transition-colors"
            >
              <div className="flex-1">
                <h3 className="font-medium text-gray-900">{category.name}</h3>
                {category.description && (
                  <p className="text-sm text-gray-500">{category.description}</p>
                )}
              </div>
              <div className="flex items-center space-x-1">
                <button
                  onClick={() => onEdit(category)}
                  className="p-1 text-gray-400 hover:text-gray-600 rounded"
                >
                  <PencilIcon className="h-4 w-4" />
                </button>
                <button
                  onClick={() => onDelete(category.id)}
                  className="p-1 text-gray-400 hover:text-danger-600 rounded"
                  disabled={isDeleting}
                >
                  <TrashIcon className="h-4 w-4" />
                </button>
              </div>
            </div>
          ))}
        </div>
      ) : (
        <div className="text-center py-8 text-gray-500">
          <FolderIcon className="h-8 w-8 mx-auto mb-2 text-gray-300" />
          <p>No {type} categories found</p>
          <p className="text-sm">Create your first {type} category to get started</p>
        </div>
      )}
    </div>
  );
}