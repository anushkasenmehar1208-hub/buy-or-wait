import { useEffect, useState } from 'react';
import type { FormEvent } from 'react';
import { Link } from 'react-router-dom';
import { affordabilityApi, profileApi } from '../../services/endpoints';
import type { Decision, Profile, PurchaseRequestWithDecision } from '../../types';
import { Button, Card, Input, toast } from '../../components/ui';
import { ApiError } from '../../services/api';
import { formatDate, formatMoney, todayISO } from '../../utils/format';
import { ForecastChart } from './ForecastChart';

export function AffordabilityPage() {
  const [profile, setProfile] = useState<Profile | null>(null);
  const [itemName, setItemName] = useState('');
  const [amount, setAmount] = useState('');
  const [deadline, setDeadline] = useState('');
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});
  const [submitting, setSubmitting] = useState(false);
  const [result, setResult] = useState<PurchaseRequestWithDecision | null>(null);

  useEffect(() => {
    profileApi
      .get()
      .then((p) => setProfile(p))
      .catch(() => setProfile(null));
  }, []);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    const errs: Record<string, string> = {};
    if (!itemName.trim()) errs.itemName = 'What do you want to buy?';
    const num = parseFloat(amount);
    if (!amount || Number.isNaN(num) || num <= 0) errs.amount = 'Enter a positive amount';
    if (deadline && deadline < todayISO()) errs.deadline = 'Deadline must be in the future';
    setFieldErrors(errs);
    if (Object.keys(errs).length > 0) return;

    setSubmitting(true);
    setResult(null);
    try {
      const res = await affordabilityApi.check({
        item_name: itemName.trim(),
        amount: amount,
        deadline: deadline || undefined,
      });
      setResult(res);
    } catch (err) {
      toast(err instanceof ApiError ? err.message : 'Check failed', 'error');
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="space-y-8 animate-fade-in">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Can I afford it?</h1>
        <p className="mt-1 text-sm text-ink-500">
          A deterministic 90-day cash-flow engine checks your request — no guessing.
        </p>
      </div>

      {!profile && (
        <Card className="border-amber-400/40 bg-amber-400/5">
          <p className="text-sm text-ink-700">
            You need a financial profile first.{' '}
            <Link to="/profile" className="font-medium text-sage-700 hover:underline">
              Create one now
            </Link>
            .
          </p>
        </Card>
      )}

      <Card>
        <form onSubmit={onSubmit} className="grid gap-4 sm:grid-cols-[1fr_200px_200px_auto]" noValidate>
          <Input
            label="What do you want to buy?"
            name="item_name"
            placeholder="MacBook Air"
            value={itemName}
            onChange={(e) => setItemName(e.target.value)}
            error={fieldErrors.itemName}
          />
          <Input
            label="Price"
            name="amount"
            type="number"
            min="0.01"
            step="0.01"
            inputMode="decimal"
            placeholder="1200.00"
            value={amount}
            onChange={(e) => setAmount(e.target.value)}
            error={fieldErrors.amount}
          />
          <Input
            label="Deadline (optional)"
            name="deadline"
            type="date"
            min={todayISO()}
            value={deadline}
            onChange={(e) => setDeadline(e.target.value)}
            error={fieldErrors.deadline}
          />
          <div className="flex items-end">
            <Button type="submit" loading={submitting} className="w-full sm:w-auto" disabled={!profile}>
              Check
            </Button>
          </div>
        </form>
      </Card>

      {submitting && <SkeletonResult />}

      {result?.decision && (
        <DecisionResult
          request={result}
          decision={result.decision}
          currency={result.currency}
          minBalance={parseFloat(profile?.minimum_safe_balance ?? '0')}
        />
      )}
    </div>
  );
}

function SkeletonResult() {
  return (
    <div className="card animate-pulse space-y-4 p-8">
      <div className="h-8 w-40 rounded bg-ink-100" />
      <div className="h-4 w-3/4 rounded bg-ink-100" />
      <div className="h-4 w-1/2 rounded bg-ink-100" />
      <div className="h-40 rounded bg-ink-100" />
    </div>
  );
}

const verdictCopy: Record<string, { title: string; sub: string; tone: string }> = {
  buy_now: {
    title: 'Buy now',
    sub: 'You can safely afford this.',
    tone: 'bg-sage-600',
  },
  affordable_with_plan: {
    title: 'Affordable with a plan',
    sub: 'You can afford this with the plan below.',
    tone: 'bg-ink-800',
  },
  wait: {
    title: 'Wait',
    sub: 'Not safe today — but reachable later.',
    tone: 'bg-amber-500',
  },
  not_affordable: {
    title: 'Not affordable',
    sub: 'No safe way to make this purchase within your horizon.',
    tone: 'bg-rose-500',
  },
};

function DecisionResult({
  request,
  decision,
  currency,
  minBalance,
}: {
  request: PurchaseRequestWithDecision;
  decision: Decision;
  currency: string;
  minBalance: number;
}) {
  const copy = verdictCopy[decision.affordability_status] ?? verdictCopy.not_affordable;
  const plan = parsePlan(decision.payment_plan, currency);

  return (
    <div className="grid gap-6 lg:grid-cols-5">
      <Card className="lg:col-span-3 animate-fade-in">
        <div className={`inline-flex items-center gap-2 rounded-full px-3 py-1 text-white ${copy.tone}`}>
          <span className="text-sm font-semibold">{copy.title}</span>
        </div>
        <p className="mt-3 text-lg text-ink-800">{copy.sub}</p>

        <dl className="mt-6 grid grid-cols-2 gap-4 text-sm">
          <Fact label="Safe to pay today" value={formatMoney(decision.amount_safe_to_pay, currency)} />
          <Fact
            label="Recommended method"
            value={decision.recommended_payment_method.replaceAll('_', ' ')}
          />
          {decision.earliest_date_for_full_payment && (
            <Fact
              label="Earliest full payment"
              value={formatDate(decision.earliest_date_for_full_payment)}
            />
          )}
          {request.deadline && <Fact label="Your deadline" value={formatDate(request.deadline)} />}
        </dl>

        {plan.length > 0 && (
          <div className="mt-6 rounded-lg border border-ink-100 bg-ink-50 p-4">
            <p className="text-sm font-medium text-ink-700">Payment plan</p>
            <ul className="mt-2 space-y-1.5">
              {plan.map((p, i) => (
                <li key={i} className="flex justify-between text-sm">
                  <span className="text-ink-500">
                    {p.date === todayISO() ? 'Today' : formatDate(p.date)}
                  </span>
                  <span className="font-medium text-ink-800">{p.amount}</span>
                </li>
              ))}
            </ul>
          </div>
        )}

        <div className="mt-6 border-t border-ink-100 pt-4">
          <p className="text-sm font-medium text-ink-700">Why?</p>
          <p className="mt-2 text-sm leading-relaxed text-ink-600">
            {decision.decision_explanation}
          </p>
        </div>
      </Card>

      <Card className="lg:col-span-2">
        <h3 className="text-base font-semibold">Payment timeline</h3>
        <p className="mt-1 text-xs text-ink-400">
          When each payment happens over the next 90 days.
        </p>
        <ForecastChart
          minBalance={minBalance}
          plan={plan}
        />
        <p className="mt-3 text-xs leading-relaxed text-ink-400">
          The engine checks this schedule against your full 90-day forecast — income,
          recurring expenses, commitments, and pending payments — so your balance never
          drops below your {formatMoney(minBalance.toFixed(2), currency)} minimum.
        </p>
      </Card>
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

function parsePlan(plan: string | null, currency: string): { date: string; amount: string }[] {
  if (!plan || plan === 'none') return [];
  return plan
    .split('|')
    .map((part) => {
      const [d, amt] = part.split(':');
      if (!d || !amt) return null;
      return { date: d, amount: formatMoney(amt, currency) };
    })
    .filter((x): x is { date: string; amount: string } => x !== null);
}
