import { useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { affordabilityApi } from '../../services/endpoints';
import type { PurchaseRequestWithDecision } from '../../types';
import { DecisionBadge, EmptyState, Skeleton } from '../../components/ui';
import { formatDate, formatMoney, todayISO } from '../../utils/format';

export function DecisionDetailPage() {
  const { id } = useParams<{ id: string }>();
  const [req, setReq] = useState<PurchaseRequestWithDecision | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!id) return;
    affordabilityApi
      .decision(id)
      .then(setReq)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [id]);

  if (loading) return <Skeleton className="h-64" />;
  if (error || !req) {
    return <EmptyState title="Not found" description={error ?? 'This decision does not exist.'} />;
  }

  const d = req.decision;

  return (
    <div className="mx-auto max-w-3xl space-y-6 animate-fade-in">
      <div>
        <Link to="/history" className="text-sm text-ink-500 hover:text-ink-800">
          ← History
        </Link>
        <div className="mt-3 flex flex-wrap items-center gap-3">
          <h1 className="text-2xl font-semibold tracking-tight">{req.item_name}</h1>
          {d && <DecisionBadge status={d.affordability_status} />}
        </div>
        <p className="mt-1 text-sm text-ink-500">
          {formatMoney(req.amount, req.currency)} · checked {formatDate(req.created_at)}
          {req.deadline ? ` · deadline ${formatDate(req.deadline)}` : ''}
        </p>
      </div>

      {d ? (
        <>
          <div className="card p-6">
            <dl className="grid grid-cols-2 gap-4 text-sm">
              <Fact label="Safe to pay today" value={formatMoney(d.amount_safe_to_pay, req.currency)} />
              <Fact label="Recommended method" value={d.recommended_payment_method.replaceAll('_', ' ')} />
              <Fact
                label="Earliest full payment"
                value={d.earliest_date_for_full_payment ? formatDate(d.earliest_date_for_full_payment) : '—'}
              />
              <Fact label="Spending changes" value={d.spending_changes_needed ?? 'none'} />
            </dl>
          </div>

          <div className="card p-6">
            <h2 className="text-base font-semibold">Why?</h2>
            <p className="mt-2 text-sm leading-relaxed text-ink-600">{d.decision_explanation}</p>
          </div>

          {d.payment_plan && d.payment_plan !== 'none' && (
            <div className="card p-6">
              <h2 className="text-base font-semibold">Payment plan</h2>
              <ul className="mt-3 divide-y divide-ink-100">
                {d.payment_plan.split('|').map((part, i) => {
                  const [date, amount] = part.split(':');
                  return (
                    <li key={i} className="flex justify-between py-2 text-sm">
                      <span className="text-ink-500">
                        {date === todayISO() ? 'Today' : formatDate(date)}
                      </span>
                      <span className="font-medium">{formatMoney(amount, req.currency)}</span>
                    </li>
                  );
                })}
              </ul>
            </div>
          )}
        </>
      ) : (
        <EmptyState title="No decision" description="This request has no stored decision." />
      )}
    </div>
  );
}

function Fact({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <dt className="text-ink-500">{label}</dt>
      <dd className="mt-0.5 font-medium text-ink-900">{value}</dd>
    </div>
  );
}
