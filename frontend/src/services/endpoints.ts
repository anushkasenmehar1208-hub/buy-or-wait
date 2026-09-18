import { api } from './api';
import type {
  AuthResponse,
  Commitment,
  DashboardSummary,
  DecisionList,
  Expense,
  Income,
  PendingPayment,
  Profile,
  PurchaseRequestWithDecision,
  User,
} from '../types';

export const authApi = {
  signup: (data: { email: string; password: string; full_name?: string }) =>
    api.post<AuthResponse>('/api/auth/signup', data),
  signin: (data: { email: string; password: string }) =>
    api.post<AuthResponse>('/api/auth/signin', data),
  signout: () => api.post<{ detail: string }>('/api/auth/signout'),
  me: () => api.get<User>('/api/auth/me'),
};

export const accountApi = {
  updateProfile: (data: { full_name: string }) =>
    api.put<User>('/api/account/profile', data),
  uploadAvatar: (file: File) => {
    const form = new FormData();
    form.append('file', file);
    return api.put<User>('/api/account/avatar', form);
  },
  deleteAvatar: () => api.delete<User>('/api/account/avatar'),
  deleteAccount: () => api.delete<void>('/api/account'),
};

export interface ProfileUpsertPayload {
  currency: string;
  current_balance: string;
  minimum_safe_balance: string;
  allows_partial_payment: boolean;
  max_installment_months: number | null;
}

export const profileApi = {
  get: () => api.get<Profile | null>('/api/profile'),
  create: (data: ProfileUpsertPayload) => api.post<Profile>('/api/profile', data),
  update: (data: ProfileUpsertPayload) => api.put<Profile>('/api/profile', data),
  delete: () => api.delete<void>('/api/profile'),

  addIncome: (data: Omit<Income, 'id'>) => api.post<Income>('/api/profile/income', data),
  updateIncome: (id: string, data: Omit<Income, 'id'>) =>
    api.put<Income>(`/api/profile/income/${id}`, data),
  deleteIncome: (id: string) => api.delete<void>(`/api/profile/income/${id}`),

  addExpense: (data: Omit<Expense, 'id'>) => api.post<Expense>('/api/profile/expenses', data),
  updateExpense: (id: string, data: Omit<Expense, 'id'>) =>
    api.put<Expense>(`/api/profile/expenses/${id}`, data),
  deleteExpense: (id: string) => api.delete<void>(`/api/profile/expenses/${id}`),

  addCommitment: (data: Omit<Commitment, 'id'>) =>
    api.post<Commitment>('/api/profile/commitments', data),
  deleteCommitment: (id: string) => api.delete<void>(`/api/profile/commitments/${id}`),

  addPending: (data: Omit<PendingPayment, 'id'>) => api.post<PendingPayment>('/api/profile/pending', data),
  deletePending: (id: string) => api.delete<void>(`/api/profile/pending/${id}`),
};

export const affordabilityApi = {
  check: (data: { item_name: string; amount: string; currency?: string; deadline?: string }) =>
    api.post<PurchaseRequestWithDecision>('/api/affordability/check', data),
  decisions: (limit = 50, offset = 0) =>
    api.get<DecisionList>(`/api/affordability/decisions?limit=${limit}&offset=${offset}`),
  decision: (id: string) => api.get<PurchaseRequestWithDecision>(`/api/affordability/decisions/${id}`),
  deleteDecision: (id: string) => api.delete<void>(`/api/affordability/decisions/${id}`),
  summary: () => api.get<DashboardSummary>('/api/affordability/summary'),
};
