export type AffordabilityStatus =
  | 'buy_now'
  | 'affordable_with_plan'
  | 'wait'
  | 'not_affordable';

export interface User {
  id: string;
  email: string;
  full_name: string;
}

export interface AuthResponse {
  access_token: string;
  token_type: string;
}

export interface Profile {
  id: string;
  user_id: string;
  currency: string;
  current_balance: string;
  minimum_safe_balance: string;
  allows_partial_payment: boolean;
  max_installment_months: number | null;
  has_income: boolean;
  has_expenses: boolean;
  income: Income[];
  expenses: Expense[];
  commitments: Commitment[];
  pending: PendingPayment[];
}

export interface Income {
  id: string;
  name: string;
  amount: string;
  frequency: 'weekly' | 'biweekly' | 'semimonthly' | 'monthly';
  next_date: string;
  end_date: string | null;
}

export interface Expense {
  id: string;
  name: string;
  category: string;
  amount: string;
  frequency: 'weekly' | 'biweekly' | 'semimonthly' | 'monthly';
  next_date: string;
  minimum_allowed_amount: string | null;
  essential: boolean;
}

export interface Commitment {
  id: string;
  name: string;
  amount: string;
  due_date: string;
  is_installment: boolean;
  installment_total: number;
}

export interface PendingPayment {
  id: string;
  name: string;
  amount: string;
  due_date: string;
}

export interface Decision {
  id: string;
  request_id: string;
  affordability_status: AffordabilityStatus;
  amount_safe_to_pay: string;
  recommended_payment_method: string;
  payment_plan: string | null;
  earliest_date_for_full_payment: string | null;
  spending_changes_needed: string | null;
  decision_explanation: string;
  created_at: string;
}

export interface PurchaseRequestWithDecision {
  id: string;
  item_name: string;
  amount: string;
  currency: string;
  deadline: string | null;
  created_at: string;
  decision: Decision | null;
}

export interface DecisionList {
  items: PurchaseRequestWithDecision[];
  total: number;
}

export interface UpcomingItem {
  id: string;
  name: string;
  amount: string;
  due_date: string;
}

export interface DashboardSummary {
  profile_exists: boolean;
  currency?: string;
  current_balance?: string;
  minimum_safe_balance?: string;
  amount_safe_to_pay?: string;
  monthly_income?: string;
  upcoming_commitments?: UpcomingItem[];
  upcoming_pending?: UpcomingItem[];
  recent_decisions?: PurchaseRequestWithDecision[];
  total_decisions?: number;
}

export interface ApiErrorShape {
  error: {
    code: string;
    message: string;
    details?: Record<string, unknown>;
  };
}
