import { useCallback, useEffect, useState } from 'react';
import { profileApi } from '../../services/endpoints';
import type { Commitment, Expense, Income, Profile } from '../../types';
import { Button, Card, ConfirmDialog, Input, Select, toast } from '../../components/ui';
import { ApiError } from '../../services/api';

const FREQUENCIES = [
  { value: 'monthly', label: 'Monthly' },
  { value: 'semimonthly', label: 'Twice a month' },
  { value: 'biweekly', label: 'Every 2 weeks' },
  { value: 'weekly', label: 'Weekly' },
];

const CATEGORIES = [
  { value: 'rent', label: 'Rent / housing' },
  { value: 'utilities', label: 'Utilities' },
  { value: 'insurance', label: 'Insurance' },
  { value: 'loan', label: 'Loan' },
  { value: 'subscription', label: 'Subscription' },
  { value: 'groceries', label: 'Groceries' },
  { value: 'other', label: 'Other' },
];

export function ProfilePage() {
  const [profile, setProfile] = useState<Profile | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    profileApi
      .get()
      .then((p) => setProfile(p))
      .catch(() => setProfile(null))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return null;
  if (!profile) return <ProfileSetup onSaved={setProfile} />;

  return (
    <div className="space-y-8 animate-fade-in">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Financial profile</h1>
        <p className="mt-1 text-sm text-ink-500">
          Everything the engine uses to forecast your next 90 days.
        </p>
      </div>
      <BalanceCard profile={profile} onSaved={setProfile} />
      <IncomeSection />
      <ExpenseSection />
      <CommitmentSection />
      <PendingSection />
    </div>
  );
}

// ---------------------------------------------------------------- balance
function BalanceCard({ profile, onSaved }: { profile: Profile; onSaved: (p: Profile) => void }) {
  const [currency, setCurrency] = useState(profile.currency);
  const [balance, setBalance] = useState(profile.current_balance);
  const [minimum, setMinimum] = useState(profile.minimum_safe_balance);
  const [partial, setPartial] = useState(profile.allows_partial_payment);
  const [maxMonths, setMaxMonths] = useState(profile.max_installment_months?.toString() ?? '');
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function save(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    if (parseFloat(minimum) > parseFloat(balance)) {
      setError('Minimum cannot exceed current balance');
      return;
    }
    setSaving(true);
    try {
      const saved = await profileApi.update({
        currency,
        current_balance: balance,
        minimum_safe_balance: minimum,
        allows_partial_payment: partial,
        max_installment_months: maxMonths ? parseInt(maxMonths, 10) : null,
      });
      onSaved(saved);
      toast('Profile saved');
    } catch (err) {
      toast(err instanceof ApiError ? err.message : 'Save failed', 'error');
    } finally {
      setSaving(false);
    }
  }

  return (
    <Card>
      <h2 className="text-base font-semibold">Balance & preferences</h2>
      <form onSubmit={save} className="mt-4 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        <Input label="Currency" name="currency" value={currency} maxLength={3}
          onChange={(e) => setCurrency(e.target.value.toUpperCase())} hint="3-letter ISO code" />
        <Input label="Current balance" name="current_balance" type="number" step="0.01" min="0"
          value={balance} onChange={(e) => setBalance(e.target.value)} />
        <Input label="Minimum safe balance" name="minimum_safe_balance" type="number" step="0.01" min="0"
          value={minimum} onChange={(e) => setMinimum(e.target.value)} hint="Never drop below this" />
        <Select label="Partial payments" name="allows_partial_payment"
          value={partial ? 'yes' : 'no'} onChange={(e) => setPartial(e.target.value === 'yes')}
          options={[{ value: 'yes', label: 'Allowed' }, { value: 'no', label: 'Not allowed' }]} />
        <Input label="Max installment months" name="max_installment_months" type="number"
          min="1" max="60" value={maxMonths} onChange={(e) => setMaxMonths(e.target.value)}
          hint="Empty = installments disabled" />
        <div className="flex items-end">
          <Button type="submit" loading={saving}>Save</Button>
        </div>
        {error && <p className="field-error sm:col-span-2 lg:col-span-3">{error}</p>}
      </form>
    </Card>
  );
}

// ---------------------------------------------------------------- income
function IncomeSection() {
  const [profile, setProfile] = useState<Profile | null>(null);
  const [deleting, setDeleting] = useState<Income | null>(null);
  const [editingId, setEditingId] = useState<string | null>(null);

  const refresh = useCallback(() => {
    profileApi.get().then((p) => p && setProfile(p)).catch(() => undefined);
  }, []);
  useEffect(refresh, [refresh]);

  const items = profile?.income ?? [];

  async function remove(item: Income) {
    try {
      await profileApi.deleteIncome(item.id);
      toast('Income removed');
      refresh();
    } catch (err) {
      toast(err instanceof ApiError ? err.message : 'Delete failed', 'error');
    } finally {
      setDeleting(null);
    }
  }

  async function saveEdit(id: string, data: Omit<Income, 'id'>) {
    try {
      await profileApi.updateIncome(id, data);
      toast('Income updated');
      setEditingId(null);
      refresh();
    } catch (err) {
      toast(err instanceof ApiError ? err.message : 'Update failed', 'error');
    }
  }

  return (
    <SectionCard title="Income sources" description="Salary, freelance, rental — anything recurring.">
      <IncomeForm
        onSubmit={async (data) => {
          await profileApi.addIncome(data);
          refresh();
        }}
      />
      <ItemList items={items} emptyText="No income added yet.">
        {(item) =>
          editingId === item.id ? (
            <li key={item.id} className="py-3">
              <IncomeForm initial={item} submitLabel="Save"
                onSubmit={(data) => saveEdit(item.id, data)}
                onCancel={() => setEditingId(null)} />
            </li>
          ) : (
            <ItemRow key={item.id} name={item.name} amount={item.amount}
              detail={`${item.frequency} · from ${item.next_date}`}
              onDelete={() => setDeleting(item)} onEdit={() => setEditingId(item.id)} />
          )
        }
      </ItemList>
      <ConfirmDialog open={!!deleting} title={`Remove “${deleting?.name}”?`}
        message="This will change future affordability results."
        onCancel={() => setDeleting(null)} onConfirm={() => deleting && remove(deleting)} />
    </SectionCard>
  );
}

function IncomeForm({
  initial, submitLabel = 'Add', onSubmit, onCancel,
}: {
  initial?: Income;
  submitLabel?: string;
  onSubmit: (data: Omit<Income, 'id'>) => Promise<void>;
  onCancel?: () => void;
}) {
  const [name, setName] = useState(initial?.name ?? '');
  const [amount, setAmount] = useState(initial?.amount ?? '');
  const [frequency, setFrequency] = useState<Income['frequency']>(initial?.frequency ?? 'monthly');
  const [nextDate, setNextDate] = useState(initial?.next_date ?? '');
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (!name.trim() || !amount || !nextDate) {
      setError('Name, amount, and next date are required');
      return;
    }
    setSaving(true);
    setError(null);
    try {
      await onSubmit({
        name: name.trim(), amount,
        frequency: frequency as Income['frequency'],
        next_date: nextDate, end_date: initial?.end_date ?? null,
      });
      if (!initial) {
        setName(''); setAmount(''); setNextDate('');
        toast('Income added');
      }
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Could not save income');
    } finally {
      setSaving(false);
    }
  }

  return (
    <form onSubmit={submit} className="grid gap-3 sm:grid-cols-[1fr_130px_150px_160px_auto]">
      <Input label="Name" name="income_name" placeholder="Salary" value={name}
        onChange={(e) => setName(e.target.value)} />
      <Input label="Amount" name="income_amount" type="number" step="0.01" min="0.01"
        placeholder="2500.00" value={amount} onChange={(e) => setAmount(e.target.value)} />
      <Select label="Frequency" name="income_frequency" value={frequency}
        onChange={(e) => setFrequency(e.target.value as Income['frequency'])} options={FREQUENCIES} />
      <Input label="Next date" name="income_next_date" type="date" value={nextDate}
        onChange={(e) => setNextDate(e.target.value)} />
      <div className="flex items-end gap-2">
        <Button type="submit" loading={saving}>{submitLabel}</Button>
        {onCancel && <Button type="button" variant="secondary" onClick={onCancel}>Cancel</Button>}
      </div>
      {error && <p className="field-error sm:col-span-5">{error}</p>}
    </form>
  );
}

// ---------------------------------------------------------------- expenses
function ExpenseSection() {
  const [profile, setProfile] = useState<Profile | null>(null);
  const [deleting, setDeleting] = useState<Expense | null>(null);
  const [editingId, setEditingId] = useState<string | null>(null);

  const refresh = useCallback(() => {
    profileApi.get().then((p) => p && setProfile(p)).catch(() => undefined);
  }, []);
  useEffect(refresh, [refresh]);

  const items = profile?.expenses ?? [];

  async function remove(item: Expense) {
    try {
      await profileApi.deleteExpense(item.id);
      toast('Expense removed');
      refresh();
    } catch (err) {
      toast(err instanceof ApiError ? err.message : 'Delete failed', 'error');
    } finally {
      setDeleting(null);
    }
  }

  async function saveEdit(id: string, data: Omit<Expense, 'id'>) {
    try {
      await profileApi.updateExpense(id, data);
      toast('Expense updated');
      setEditingId(null);
      refresh();
    } catch (err) {
      toast(err instanceof ApiError ? err.message : 'Update failed', 'error');
    }
  }

  return (
    <SectionCard title="Recurring expenses"
      description="Rent, utilities, subscriptions — regular outflows.">
      <ExpenseForm
        onSubmit={async (data) => {
          await profileApi.addExpense(data);
          refresh();
        }}
      />
      <ItemList items={items} emptyText="No expenses added yet.">
        {(item) =>
          editingId === item.id ? (
            <li key={item.id} className="py-3">
              <ExpenseForm initial={item} submitLabel="Save"
                onSubmit={(data) => saveEdit(item.id, data)}
                onCancel={() => setEditingId(null)} />
            </li>
          ) : (
            <ItemRow key={item.id} name={item.name} amount={item.amount}
              detail={`${item.category} · ${item.frequency} · from ${item.next_date}`}
              onDelete={() => setDeleting(item)} onEdit={() => setEditingId(item.id)} />
          )
        }
      </ItemList>
      <ConfirmDialog open={!!deleting} title={`Remove “${deleting?.name}”?`}
        message="This will change future affordability results."
        onCancel={() => setDeleting(null)} onConfirm={() => deleting && remove(deleting)} />
    </SectionCard>
  );
}

function ExpenseForm({
  initial, submitLabel = 'Add', onSubmit, onCancel,
}: {
  initial?: Expense;
  submitLabel?: string;
  onSubmit: (data: Omit<Expense, 'id'>) => Promise<void>;
  onCancel?: () => void;
}) {
  const [name, setName] = useState(initial?.name ?? '');
  const [category, setCategory] = useState(initial?.category ?? 'other');
  const [amount, setAmount] = useState(initial?.amount ?? '');
  const [frequency, setFrequency] = useState<Income['frequency']>(initial?.frequency ?? 'monthly');
  const [nextDate, setNextDate] = useState(initial?.next_date ?? '');
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (!name.trim() || !amount || !nextDate) {
      setError('Name, amount, and next date are required');
      return;
    }
    setSaving(true);
    setError(null);
    try {
      await onSubmit({
        name: name.trim(), category, amount,
        frequency: frequency as Expense['frequency'],
        next_date: nextDate,
        minimum_allowed_amount: initial?.minimum_allowed_amount ?? null,
        essential: initial?.essential ?? true,
      });
      if (!initial) {
        setName(''); setAmount(''); setNextDate('');
        toast('Expense added');
      }
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Could not save expense');
    } finally {
      setSaving(false);
    }
  }

  return (
    <form onSubmit={submit} className="grid gap-3 sm:grid-cols-[1fr_150px_130px_150px_160px_auto]">
      <Input label="Name" name="expense_name" placeholder="Rent" value={name}
        onChange={(e) => setName(e.target.value)} />
      <Select label="Category" name="expense_category" value={category}
        onChange={(e) => setCategory(e.target.value)} options={CATEGORIES} />
      <Input label="Amount" name="expense_amount" type="number" step="0.01" min="0.01"
        placeholder="1200.00" value={amount} onChange={(e) => setAmount(e.target.value)} />
      <Select label="Frequency" name="expense_frequency" value={frequency}
        onChange={(e) => setFrequency(e.target.value as Expense['frequency'])} options={FREQUENCIES} />
      <Input label="Next date" name="expense_next_date" type="date" value={nextDate}
        onChange={(e) => setNextDate(e.target.value)} />
      <div className="flex items-end gap-2">
        <Button type="submit" loading={saving}>{submitLabel}</Button>
        {onCancel && <Button type="button" variant="secondary" onClick={onCancel}>Cancel</Button>}
      </div>
      {error && <p className="field-error sm:col-span-6">{error}</p>}
    </form>
  );
}

// ---------------------------------------------------------------- commitments
function CommitmentSection() {
  const [profile, setProfile] = useState<Profile | null>(null);
  const [deleting, setDeleting] = useState<Commitment | null>(null);

  const refresh = useCallback(() => {
    profileApi.get().then((p) => p && setProfile(p)).catch(() => undefined);
  }, []);
  useEffect(refresh, [refresh]);

  const items = profile?.commitments ?? [];

  async function remove(item: Commitment) {
    try {
      await profileApi.deleteCommitment(item.id);
      toast('Commitment removed');
      refresh();
    } catch (err) {
      toast(err instanceof ApiError ? err.message : 'Delete failed', 'error');
    } finally {
      setDeleting(null);
    }
  }

  return (
    <SectionCard title="One-off commitments"
      description="Known future obligations: loan payoff, planned purchases.">
      <CommitmentForm
        onSubmit={async (data) => {
          await profileApi.addCommitment(data);
          refresh();
        }}
      />
      <ItemList items={items} emptyText="No commitments added.">
        {(item) => (
          <ItemRow key={item.id} name={item.name} amount={item.amount}
            detail={`due ${item.due_date}`}
            onDelete={() => setDeleting(item)} onEdit={() => undefined} />
        )}
      </ItemList>
      <ConfirmDialog open={!!deleting} title={`Remove “${deleting?.name}”?`}
        message="This will change future affordability results."
        onCancel={() => setDeleting(null)} onConfirm={() => deleting && remove(deleting)} />
    </SectionCard>
  );
}

function CommitmentForm({ onSubmit }: { onSubmit: (data: Omit<Commitment, 'id'>) => Promise<void> }) {
  const [name, setName] = useState('');
  const [amount, setAmount] = useState('');
  const [dueDate, setDueDate] = useState('');
  const [saving, setSaving] = useState(false);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (!name.trim() || !amount || !dueDate) return;
    setSaving(true);
    try {
      await onSubmit({
        name: name.trim(), amount, due_date: dueDate,
        is_installment: false, installment_total: 1,
      });
      setName(''); setAmount(''); setDueDate('');
      toast('Commitment added');
    } catch (err) {
      toast(err instanceof ApiError ? err.message : 'Could not add commitment', 'error');
    } finally {
      setSaving(false);
    }
  }

  return (
    <form onSubmit={submit} className="grid gap-3 sm:grid-cols-[1fr_130px_160px_auto]">
      <Input label="Name" name="commitment_name" placeholder="Loan payoff" value={name}
        onChange={(e) => setName(e.target.value)} />
      <Input label="Amount" name="commitment_amount" type="number" step="0.01" min="0.01"
        value={amount} onChange={(e) => setAmount(e.target.value)} />
      <Input label="Due date" name="commitment_due" type="date" value={dueDate}
        onChange={(e) => setDueDate(e.target.value)} />
      <div className="flex items-end">
        <Button type="submit" loading={saving}>Add</Button>
      </div>
    </form>
  );
}

// ---------------------------------------------------------------- pending
function PendingSection() {
  const [profile, setProfile] = useState<Profile | null>(null);
  const [deleting, setDeleting] = useState<{ id: string; name: string } | null>(null);

  const refresh = useCallback(() => {
    profileApi.get().then((p) => p && setProfile(p)).catch(() => undefined);
  }, []);
  useEffect(refresh, [refresh]);

  const items = profile?.pending ?? [];

  async function remove(item: { id: string; name: string }) {
    try {
      await profileApi.deletePending(item.id);
      toast('Pending payment removed');
      refresh();
    } catch (err) {
      toast(err instanceof ApiError ? err.message : 'Delete failed', 'error');
    } finally {
      setDeleting(null);
    }
  }

  return (
    <SectionCard title="Pending payments"
      description="Committed but unpaid amounts reserved from your balance.">
      <PendingForm
        onSubmit={async (data) => {
          await profileApi.addPending(data);
          refresh();
        }}
      />
      <ItemList items={items} emptyText="No pending payments.">
        {(item) => (
          <ItemRow key={item.id} name={item.name} amount={item.amount}
            detail={`due ${item.due_date}`}
            onDelete={() => setDeleting(item)} onEdit={() => undefined} />
        )}
      </ItemList>
      <ConfirmDialog open={!!deleting} title={`Remove “${deleting?.name}”?`}
        message="This will change future affordability results."
        onCancel={() => setDeleting(null)} onConfirm={() => deleting && remove(deleting)} />
    </SectionCard>
  );
}

function PendingForm({ onSubmit }: { onSubmit: (data: Omit<Commitment, 'id'>) => Promise<void> }) {
  const [name, setName] = useState('');
  const [amount, setAmount] = useState('');
  const [dueDate, setDueDate] = useState('');
  const [saving, setSaving] = useState(false);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (!name.trim() || !amount || !dueDate) return;
    setSaving(true);
    try {
      await onSubmit({ name: name.trim(), amount, due_date: dueDate } as Omit<Commitment, 'id'>);
      setName(''); setAmount(''); setDueDate('');
      toast('Pending payment added');
    } catch (err) {
      toast(err instanceof ApiError ? err.message : 'Could not add pending payment', 'error');
    } finally {
      setSaving(false);
    }
  }

  return (
    <form onSubmit={submit} className="grid gap-3 sm:grid-cols-[1fr_130px_160px_auto]">
      <Input label="Name" name="pending_name" placeholder="Utility bill" value={name}
        onChange={(e) => setName(e.target.value)} />
      <Input label="Amount" name="pending_amount" type="number" step="0.01" min="0.01"
        value={amount} onChange={(e) => setAmount(e.target.value)} />
      <Input label="Due date" name="pending_due" type="date" value={dueDate}
        onChange={(e) => setDueDate(e.target.value)} />
      <div className="flex items-end">
        <Button type="submit" loading={saving}>Add</Button>
      </div>
    </form>
  );
}

// ---------------------------------------------------------------- shared bits
function ProfileSetup({ onSaved }: { onSaved: (p: Profile) => void }) {
  const [currency, setCurrency] = useState('USD');
  const [balance, setBalance] = useState('');
  const [minimum, setMinimum] = useState('');
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    if (!balance || !minimum) {
      setError('Balance and minimum are required');
      return;
    }
    if (parseFloat(minimum) > parseFloat(balance)) {
      setError('Minimum cannot exceed current balance');
      return;
    }
    setSaving(true);
    try {
      const created = await profileApi.create({
        currency, current_balance: balance, minimum_safe_balance: minimum,
        allows_partial_payment: true, max_installment_months: null,
      });
      onSaved(created);
      toast('Profile created');
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Could not create profile');
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="mx-auto max-w-xl animate-fade-in">
      <h1 className="text-2xl font-semibold tracking-tight">Set up your financial profile</h1>
      <p className="mt-1 text-sm text-ink-500">
        Start with your balance — you can add income, expenses, and commitments next.
      </p>
      <Card className="mt-6">
        <form onSubmit={submit} className="space-y-4">
          <Input label="Currency" name="setup_currency" value={currency} maxLength={3}
            onChange={(e) => setCurrency(e.target.value.toUpperCase())} hint="3-letter ISO code" />
          <Input label="Current balance" name="setup_balance" type="number" step="0.01" min="0"
            value={balance} onChange={(e) => setBalance(e.target.value)} />
          <Input label="Minimum safe balance" name="setup_minimum" type="number" step="0.01" min="0"
            value={minimum} onChange={(e) => setMinimum(e.target.value)}
            hint="The floor your balance should never cross" />
          {error && <p className="field-error">{error}</p>}
          <Button type="submit" loading={saving} className="w-full">Create profile</Button>
        </form>
      </Card>
    </div>
  );
}

function SectionCard({
  title, description, children,
}: { title: string; description: string; children: React.ReactNode }) {
  return (
    <Card>
      <h2 className="text-base font-semibold">{title}</h2>
      <p className="mt-0.5 text-sm text-ink-500">{description}</p>
      <div className="mt-4">{children}</div>
    </Card>
  );
}

function ItemList<T extends { id: string }>({
  items, children, emptyText,
}: { items: T[]; emptyText: string; children: (item: T) => React.ReactNode }) {
  if (items.length === 0) {
    return <p className="mt-4 text-sm text-ink-400">{emptyText}</p>;
  }
  return <ul className="mt-4 divide-y divide-ink-100">{items.map((i) => children(i))}</ul>;
}

function ItemRow({
  name, amount, detail, onDelete, onEdit,
}: {
  name: string; amount: string; detail: string;
  onDelete: () => void; onEdit: () => void;
}) {
  return (
    <li className="flex items-center justify-between py-3">
      <div>
        <p className="text-sm font-medium text-ink-800">{name}</p>
        <p className="text-xs text-ink-400">{detail}</p>
      </div>
      <div className="flex items-center gap-2">
        <span className="text-sm text-ink-700">{amount}</span>
        {onEdit && (
          <button onClick={onEdit} className="text-sm text-sage-700 hover:underline">Edit</button>
        )}
        <button onClick={onDelete} className="text-sm text-rose-600 hover:underline">Remove</button>
      </div>
    </li>
  );
}
