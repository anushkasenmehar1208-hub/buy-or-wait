import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { affordabilityApi } from '../../services/endpoints';
import type { DecisionList } from '../../types';
import { ConfirmDialog, DecisionBadge, EmptyState, Skeleton, toast } from '../../components/ui';
import { ApiError } from '../../services/api';
import { formatDate, formatMoney } from '../../utils/format';

export function HistoryPage() {
  const [data, setData] = useState<DecisionList | null>(null);
  const [loading, setLoading] = useState(true);
  const [deleting, setDeleting] = useState<string | null>(null);

  useEffect(() => {
    affordabilityApi
      .decisions()
      .then(setData)
      .catch((e) => toast(e.message, 'error'))
      .finally(() => setLoading(false));
  }, []);

  async function remove(id: string) {
    try {
      await affordabilityApi.deleteDecision(id);
      setData((d) =>
        d ? { items: d.items.filter((i) => i.id !== id), total: d.total - 1 } : d,
      );
      toast('Decision deleted');
    } catch (err) {
      toast(err instanceof ApiError ? err.message : 'Delete failed', 'error');
    } finally {
      setDeleting(null);
    }
  }

  if (loading) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-8 w-48" />
        {Array.from({ length: 4 }).map((_, i) => (
          <Skeleton key={i} className="h-16" />
        ))}
      </div>
    );
  }

  if (!data || data.items.length === 0) {
    return (
      <EmptyState
        title="No decisions yet"
        description="Run your first affordability check and it will show up here."
      />
    );
  }

  return (
    <div className="space-y-6 animate-fade-in">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">History</h1>
        <p className="mt-1 text-sm text-ink-500">
          {data.total} saved {data.total === 1 ? 'check' : 'checks'}
        </p>
      </div>
      <ul className="card divide-y divide-ink-100 overflow-hidden">
        {data.items.map((r) => (
          <li key={r.id} className="flex items-center justify-between gap-4 p-4 hover:bg-ink-50">
            <Link to={`/history/${r.id}`} className="min-w-0 flex-1">
              <div className="flex flex-wrap items-center gap-x-3 gap-y-1">
                <span className="truncate font-medium text-ink-900">{r.item_name}</span>
                {r.decision && <DecisionBadge status={r.decision.affordability_status} />}
              </div>
              <p className="mt-0.5 text-xs text-ink-400">
                {formatMoney(r.amount, r.currency)} · {formatDate(r.created_at)}
              </p>
            </Link>
            <div className="flex items-center gap-2">
              <Link
                to={`/history/${r.id}`}
                className="rounded-lg px-2.5 py-1.5 text-sm text-ink-500 hover:bg-ink-100"
              >
                Details
              </Link>
              <button
                onClick={() => setDeleting(r.id)}
                className="rounded-lg px-2.5 py-1.5 text-sm text-rose-600 hover:bg-rose-400/10"
              >
                Delete
              </button>
            </div>
          </li>
        ))}
      </ul>
      <ConfirmDialog
        open={!!deleting}
        title="Delete this check?"
        message="The request and its decision will be removed permanently."
        onCancel={() => setDeleting(null)}
        onConfirm={() => deleting && remove(deleting)}
      />
    </div>
  );
}
