import { format, parseISO, isValid } from 'date-fns';

/**
 * Format currency amount in Indian Rupees (INR)
 */
export function formatCurrency(amount: number, currency = 'INR'): string {
  return new Intl.NumberFormat('en-IN', {
    style: 'currency',
    currency,
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(amount);
}

/**
 * Format percentage
 */
export function formatPercentage(value: number, decimals = 1): string {
  return `${value.toFixed(decimals)}%`;
}

/**
 * Format date for display
 */
export function formatDate(date: string | Date, formatStr = 'MMM dd, yyyy'): string {
  try {
    const dateObj = typeof date === 'string' ? parseISO(date) : date;
    if (!isValid(dateObj)) {
      return 'Invalid Date';
    }
    return format(dateObj, formatStr);
  } catch (error) {
    return 'Invalid Date';
  }
}

/**
 * Format date for input fields
 */
export function formatDateForInput(date: string | Date): string {
  try {
    const dateObj = typeof date === 'string' ? parseISO(date) : date;
    if (!isValid(dateObj)) {
      return '';
    }
    return format(dateObj, 'yyyy-MM-dd');
  } catch (error) {
    return '';
  }
}

/**
 * Format relative time (e.g., "2 hours ago")
 */
export function formatRelativeTime(date: string | Date): string {
  try {
    const dateObj = typeof date === 'string' ? parseISO(date) : date;
    if (!isValid(dateObj)) {
      return 'Invalid Date';
    }
    
    const now = new Date();
    const diffInMs = now.getTime() - dateObj.getTime();
    const diffInMinutes = Math.floor(diffInMs / (1000 * 60));
    const diffInHours = Math.floor(diffInMs / (1000 * 60 * 60));
    const diffInDays = Math.floor(diffInMs / (1000 * 60 * 60 * 24));

    if (diffInMinutes < 1) {
      return 'Just now';
    } else if (diffInMinutes < 60) {
      return `${diffInMinutes} minute${diffInMinutes > 1 ? 's' : ''} ago`;
    } else if (diffInHours < 24) {
      return `${diffInHours} hour${diffInHours > 1 ? 's' : ''} ago`;
    } else if (diffInDays < 7) {
      return `${diffInDays} day${diffInDays > 1 ? 's' : ''} ago`;
    } else {
      return formatDate(dateObj, 'MMM dd, yyyy');
    }
  } catch (error) {
    return 'Invalid Date';
  }
}

/**
 * Get color class for transaction type
 */
export function getTransactionTypeColor(type: 'income' | 'expense'): string {
  return type === 'income' ? 'text-success-600' : 'text-danger-600';
}

/**
 * Get color class for budget status
 */
export function getBudgetStatusColor(percentage: number): string {
  if (percentage >= 100) return 'text-danger-600';
  if (percentage >= 80) return 'text-warning-600';
  return 'text-success-600';
}

/**
 * Get alert priority color
 */
export function getAlertPriorityColor(priority: string): string {
  switch (priority.toLowerCase()) {
    case 'critical':
      return 'text-danger-600 bg-danger-50 border-danger-200';
    case 'high':
      return 'text-danger-600 bg-danger-50 border-danger-200';
    case 'medium':
      return 'text-warning-600 bg-warning-50 border-warning-200';
    case 'low':
      return 'text-primary-600 bg-primary-50 border-primary-200';
    default:
      return 'text-gray-600 bg-gray-50 border-gray-200';
  }
}

/**
 * Truncate text to specified length
 */
export function truncateText(text: string, length = 50): string {
  if (text.length <= length) return text;
  return text.substring(0, length) + '...';
}

/**
 * Capitalize first letter
 */
export function capitalize(text: string): string {
  if (!text) return text;
  return text.charAt(0).toUpperCase() + text.slice(1).toLowerCase();
}