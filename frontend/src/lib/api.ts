import axios from 'axios';

// Base API URL configuration
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api';

export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Control': 'no-cache',
    'Content-Type': 'application/json',
  },
});

// Request interceptor to attach JWT token
apiClient.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('access_token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// Response interceptor for unauthorized handling
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      // Don't auto-logout if we're on the login page
      if (!window.location.pathname.includes('/login')) {
        localStorage.removeItem('access_token');
      }
    }
    return Promise.reject(error);
  }
);

// -------------------------------------------------------------
// Interfaces
// -------------------------------------------------------------

export interface User {
  id: number;
  email: string;
  full_name?: string | null;
  is_active: boolean;
  role: string;
}

export interface Category {
  id: number;
  name: string;
  type: 'income' | 'expense';
  user_id?: number;
  description?: string;
}

export interface Transaction {
  id: number;
  user_id: number;
  category_id?: number | null;
  category?: Category;
  category_name?: string | null;
  category_type?: string | null;
  date: string;
  amount: number;
  description: string;
  merchant?: string | null;
  transaction_type: 'income' | 'expense';
  raw_description?: string | null;
  reference_id?: string | null;
  notes?: string | null;
  created_at?: string;
  updated_at?: string;
}

export interface TransactionCreate {
  amount: number;
  description: string;
  date: string;
  transaction_type: 'income' | 'expense';
  category_id?: number;
  merchant?: string;
  notes?: string;
  reference_id?: string;
}

export interface Budget {
  id: number;
  user_id: number;
  category_id: number;
  category_name?: string;
  category_type?: string;
  name: string;
  amount: number;
  limit_amount: number;
  spent_amount: number;
  remaining_amount?: number;
  percentage_used: number;
  period: 'weekly' | 'monthly' | 'quarterly' | 'yearly';
  start_date: string;
  end_date?: string;
  is_active: boolean;
  alert_threshold?: number;
  is_current?: boolean;
  created_at?: string;
  updated_at?: string;
}

export interface Alert {
  id: number;
  user_id: number;
  title: string;
  message: string;
  alert_type: string;
  status: 'unread' | 'read' | 'dismissed';
  priority: string;
  action_url?: string | null;
  transaction_id?: number | null;
  budget_id?: number | null;
  category_id?: number | null;
  is_read: boolean;
  created_at: string;
  read_at?: string | null;
  dismissed_at?: string | null;
}

export interface FinancialSummary {
  total_income: number;
  total_expenses: number;
  net_amount: number;
  savings_rate: number;
  currency?: string;
}

export interface SpendingByCategory {
  category_id: number;
  category_name: string;
  amount: number;
  percentage: number;
  transaction_count?: number;
}

export interface DashboardOverview {
  period: {
    start_date: string;
    end_date: string;
    days: number;
  };
  financial_summary: FinancialSummary;
  spending_by_category: SpendingByCategory[];
  recent_transactions: Transaction[];
  budget_summary?: any;
  alert_summary?: any;
}

// -------------------------------------------------------------
// APIs
// -------------------------------------------------------------

export const authAPI = {
  login: (data: { email: string; password: string }) =>
    apiClient.post<{ access_token: string; token_type: string }>('/auth/login', data),

  getCurrentUser: () =>
    apiClient.get<User>('/users/me'),
};

export const dashboardAPI = {
  getOverview: (params?: { period_days?: number }) =>
    apiClient.get<DashboardOverview>('/dashboard/overview', { params }),
};

export const transactionsAPI = {
  getAll: (params?: any) =>
    apiClient.get<Transaction[]>('/transactions/', { params }),

  getById: (id: number) =>
    apiClient.get<Transaction>(`/transactions/${id}`),

  create: (data: TransactionCreate) =>
    apiClient.post<Transaction>('/transactions/', data),

  update: (id: number, data: Partial<TransactionCreate>) =>
    apiClient.put<Transaction>(`/transactions/${id}`, data),

  delete: (id: number) =>
    apiClient.delete(`/transactions/${id}`),

  uploadCSV: (file: File) => {
    const formData = new FormData();
    formData.append('file', file);
    return apiClient.post('/transactions/upload-csv', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
  },
};

export const categoriesAPI = {
  getAll: () =>
    apiClient.get<Category[]>('/categories/'),

  getById: (id: number) =>
    apiClient.get<Category>(`/categories/${id}`),

  create: (data: Partial<Category>) =>
    apiClient.post<Category>('/categories/', data),

  update: (id: number, data: Partial<Category>) =>
    apiClient.put<Category>(`/categories/${id}`, data),

  delete: (id: number) =>
    apiClient.delete(`/categories/${id}`),
};

export const budgetsAPI = {
  getAll: async (params?: any) => {
    const response = await apiClient.get<Budget[]>('/budgets/', { params });
    // Transform fields so both amount & limit_amount exist
    const enriched = (response.data || []).map((b: any) => ({
      ...b,
      amount: Number(b.limit_amount ?? b.amount ?? 0),
      limit_amount: Number(b.limit_amount ?? b.amount ?? 0),
      spent_amount: Number(b.spent_amount ?? 0),
      percentage_used: Number(b.percentage_used ?? 0),
    }));
    return { ...response, data: enriched };
  },

  getById: async (id: number) => {
    const response = await apiClient.get<Budget>(`/budgets/${id}`);
    const b = response.data;
    const enriched = {
      ...b,
      amount: Number(b.limit_amount ?? b.amount ?? 0),
      limit_amount: Number(b.limit_amount ?? b.amount ?? 0),
      spent_amount: Number(b.spent_amount ?? 0),
      percentage_used: Number(b.percentage_used ?? 0),
    };
    return { ...response, data: enriched };
  },

  create: (data: any) => {
    // Ensure required backend fields (name, limit_amount, end_date)
    const startDate = data.start_date ? new Date(data.start_date) : new Date();
    let endDate = data.end_date ? new Date(data.end_date) : null;

    if (!endDate || isNaN(endDate.getTime())) {
      endDate = new Date(startDate);
      if (data.period === 'weekly') {
        endDate.setDate(startDate.getDate() + 7);
      } else if (data.period === 'yearly') {
        endDate.setFullYear(startDate.getFullYear() + 1);
      } else {
        endDate.setMonth(startDate.getMonth() + 1);
      }
    }

    const payload = {
      name: data.name || `${data.period || 'Monthly'} Budget`,
      category_id: Number(data.category_id),
      limit_amount: Number(data.amount ?? data.limit_amount),
      period: data.period || 'monthly',
      start_date: startDate.toISOString(),
      end_date: endDate.toISOString(),
      alert_threshold: data.alert_threshold ?? 80,
      is_active: data.is_active ?? true,
    };
    return apiClient.post<Budget>('/budgets/', payload);
  },

  update: (id: number, data: any) => {
    const payload: any = { ...data };
    if (data.amount !== undefined) {
      payload.limit_amount = Number(data.amount);
    }
    if (data.start_date) {
      payload.start_date = new Date(data.start_date).toISOString();
    }
    if (data.end_date) {
      payload.end_date = new Date(data.end_date).toISOString();
    }
    return apiClient.put<Budget>(`/budgets/${id}`, payload);
  },

  delete: (id: number) =>
    apiClient.delete(`/budgets/${id}`),

  getProgress: () =>
    apiClient.get('/budgets/progress'),

  getSummary: () =>
    apiClient.get('/budgets/summary'),
};

export const alertsAPI = {
  getAll: async (params?: any) => {
    const response = await apiClient.get<Alert[]>('/alerts/', { params });
    const enriched = (response.data || []).map((a: any) => ({
      ...a,
      is_read: a.status === 'read',
    }));
    return { ...response, data: enriched };
  },

  markAsRead: (id: number) =>
    apiClient.put(`/alerts/${id}`, { status: 'read' }),

  delete: (id: number) =>
    apiClient.delete(`/alerts/${id}`),
};
