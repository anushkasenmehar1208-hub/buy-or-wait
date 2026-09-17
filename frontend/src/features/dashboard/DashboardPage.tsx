import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { affordabilityApi } from '../../services/endpoints';
import type { DashboardSummary } from '../../types';
import { Button, Card, DecisionBadge, EmptyState, Skeleton } from '../../components/ui';
import { formatDate, formatMoney } from '../../utils/format';

export function DashboardPage() {
  const [summary, setSummary] = useState<DashboardSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    affordabilityApi
      .summary()
      .then((s) => !cancelled && setSummary(s))
      .catch((e) => !cancelled && setError(e.message))
      .finally(() => !cancelled && setLoading(false));
    return () => {
      cancelled = true;
    };
  }, []);

  if (loading) {
    return (
      <div className="space-y-6">
        <Skeleton className="h-8 w-64" />
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {Array.from({ length: 4 }).map((_, i) => (
            <Skeleton key={i} className="h-28" />
          ))}
        </div>
        <Skeleton className="h-48" />
      </div>
    );
  }

  if (error) {
    return <EmptyState title="Something went wrong" description={error} />;
  }

  if (!summary?.profile_exists) {
    return (
      <EmptyState
        title="Set up your financial profile"
        description="Add your balance, income, and expenses so the engine can forecast your next 90 days."
        action={
          <Link to="/profile">
            <Button>Create profile</Button>
          </Link>
        }
      />
    );
  }

  const cur = summary.currency ?? 'USD';

  const stats = [
    { label: 'Current balance', value: formatMoney(summary.current_balance ?? 0, cur) },
    {
      label: 'Safe to spend today',
      value: formatMoney(summary.amount_safe_to_pay ?? 0, cur),
      hint: 'Keeps you above your minimum over 90 days',
    },
    { label: 'Monthly income', value: formatMoney(summary.monthly_income ?? 0, cur) },
    {
      label: 'Minimum safe balance',
      value: formatMoney(summary.minimum_safe_balance ?? 0, cur),
    },
  ];

  const recent = summary.recent_decisions ?? [];

  return (
    <div className="space-y-8 animate-fade-in">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Overview</h1>
          <p className="mt-1 text-sm text-ink-500">
            Your finances, forecast for the next 90 days.
          </p>
        </div>
        <Link to="/affordability">
          <Button>Can I afford it?</Button>
        </Link>
      </div>

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {stats.map((s) => (
          <Card key={s.label} className="p-5">
            <p className="text-sm text-ink-500">{s.label}</p>
            <p className="mt-2 text-2xl font-semibold tracking-tight text-ink-900">{s.value}</p>
            {s.hint && <p className="mt-1 text-xs text-ink-400">{s.hint}</p>}
          </Card>
        ))}
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <Card>
          <h2 className="text-base font-semibold">Upcoming commitments</h2>
          <UpcomingList items={summary.upcoming_commitments ?? []} currency={cur} />
        </Card>
        <Card>
          <h2 className="text-base font-semibold">Pending payments</h2>
          <UpcomingList items={summary.upcoming_pending ?? []} currency={cur} />
        </Card>
      </div>

      <Card>
        <div className="flex items-center justify-between">
          <h2 className="text-base font-semibold">Recent decisions</h2>
          <Link to="/history" className="text-sm font-medium text-sage-700 hover:underline">
            View all
          </Link>
        </div>
        {recent.length === 0 ? (
          <p className="mt-4 text-sm text-ink-500">
            No checks yet. Try “Can I afford it?” above.
          </p>
        ) : (
          <ul className="mt-4 divide-y divide-ink-100">
            {recent.map((r) => (
              <li key={r.id}>
                <Link
                  to={`/history/${r.id}`}
                  className="flex items-center justify-between gap-4 rounded-lg py-3 px-2 -mx-2 transition-colors hover:bg-ink-50"
                >
                  <div className="min-w-0">
                    <p className="truncate text-sm font-medium text-ink-800">{r.item_name}</p>
                    <p className="text-xs text-ink-400">{formatDate(r.created_at)}</p>
                  </div>
                  <div className="flex items-center gap-3">
                    <span className="text-sm text-ink-600">{formatMoney(r.amount, r.currency)}</span>
                    {r.decision && <DecisionBadge status={r.decision.affordability_status} />}
                  </div>
                </Link>
              </li>
            ))}
          </ul>
        )}
      </Card>
    </div>
  );
}

function UpcomingList({
  items,
  currency,
}: {
  items: { id: string; name: string; amount: string; due_date: string }[];
  currency: string;
}) {
  if (items.length === 0) {
    return <p className="mt-4 text-sm text-ink-400">Nothing scheduled.</p>;
  }
  return (
    <ul className="mt-4 space-y-3">
      {items.map((item) => (
        <li key={item.id} className="flex items-center justify-between text-sm">
          <span className="text-ink-700">{item.name}</span>
          <span className="flex items-baseline gap-3">
            <span className="text-ink-900">{formatMoney(item.amount, currency)}</span>
            <span className="text-xs text-ink-400">{formatDate(item.due_date)}</span>
          </span>
        </li>
      ))}
    </ul>
  );
}
