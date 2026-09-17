import { forwardRef, useEffect, useRef, useState } from 'react';
import type { ButtonHTMLAttributes, InputHTMLAttributes, ReactNode, SelectHTMLAttributes } from 'react';

type ButtonVariant = 'primary' | 'secondary' | 'danger';

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant;
  loading?: boolean;
}

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(function Button(
  { variant = 'primary', loading, disabled, className = '', children, ...rest },
  ref,
) {
  const variantClass =
    variant === 'primary' ? 'btn-primary' : variant === 'danger' ? 'btn-danger' : 'btn-secondary';
  return (
    <button
      ref={ref}
      className={`${variantClass} ${className}`}
      disabled={disabled || loading}
      {...rest}
    >
      {loading && <Spinner className="h-4 w-4" />}
      {children}
    </button>
  );
});

interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  error?: string | null;
  hint?: string;
}

export function Input({ label, error, hint, id, className = '', ...rest }: InputProps) {
  const inputId = id ?? rest.name;
  return (
    <div>
      {label && (
        <label htmlFor={inputId} className="label">
          {label}
        </label>
      )}
      <input
        id={inputId}
        className={`input ${error ? 'border-rose-400 focus:border-rose-500 focus:ring-rose-500/20' : ''} ${className}`}
        aria-invalid={!!error}
        {...rest}
      />
      {error ? (
        <p className="field-error" role="alert">
          {error}
        </p>
      ) : hint ? (
        <p className="mt-1.5 text-sm text-ink-400">{hint}</p>
      ) : null}
    </div>
  );
}

interface SelectProps extends SelectHTMLAttributes<HTMLSelectElement> {
  label?: string;
  error?: string | null;
  options: { value: string; label: string }[];
}

export function Select({ label, error, options, id, className = '', ...rest }: SelectProps) {
  const selectId = id ?? rest.name;
  return (
    <div>
      {label && (
        <label htmlFor={selectId} className="label">
          {label}
        </label>
      )}
      <select id={selectId} className={`input ${className}`} {...rest}>
        {options.map((o) => (
          <option key={o.value} value={o.value}>
            {o.label}
          </option>
        ))}
      </select>
      {error && (
        <p className="field-error" role="alert">
          {error}
        </p>
      )}
    </div>
  );
}

export function Card({ children, className = '' }: { children: ReactNode; className?: string }) {
  return <div className={`card p-6 ${className}`}>{children}</div>;
}

export function Spinner({ className = 'h-5 w-5' }: { className?: string }) {
  return (
    <svg className={`animate-spin ${className}`} viewBox="0 0 24 24" fill="none" aria-hidden>
      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
      <path
        className="opacity-75"
        fill="currentColor"
        d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"
      />
    </svg>
  );
}

export function PageLoader() {
  return (
    <div className="flex min-h-[50vh] items-center justify-center text-ink-400">
      <Spinner className="h-8 w-8" />
    </div>
  );
}

export function Skeleton({ className = '' }: { className?: string }) {
  return (
    <div className={`relative overflow-hidden rounded-lg bg-ink-100 ${className}`}>
      <div
        className="absolute inset-0 -translate-x-full animate-[shimmer_1.5s_infinite]
          bg-gradient-to-r from-transparent via-white/60 to-transparent"
      />
    </div>
  );
}

const badgeStyles: Record<string, string> = {
  buy_now: 'bg-sage-100 text-sage-700',
  affordable_with_plan: 'bg-ink-100 text-ink-700',
  wait: 'bg-amber-400/15 text-amber-600',
  not_affordable: 'bg-rose-400/10 text-rose-600',
};

const badgeLabels: Record<string, string> = {
  buy_now: 'Buy now',
  affordable_with_plan: 'With plan',
  wait: 'Wait',
  not_affordable: 'Not affordable',
};

export function DecisionBadge({ status }: { status: string }) {
  return (
    <span
      className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium
        ${badgeStyles[status] ?? 'bg-ink-100 text-ink-600'}`}
    >
      {badgeLabels[status] ?? status}
    </span>
  );
}

export function EmptyState({
  title,
  description,
  action,
}: {
  title: string;
  description: string;
  action?: ReactNode;
}) {
  return (
    <div className="flex flex-col items-center justify-center rounded-xl border border-dashed
      border-ink-200 bg-white/50 px-6 py-14 text-center animate-fade-in">
      <h3 className="text-base font-semibold text-ink-800">{title}</h3>
      <p className="mt-1 max-w-sm text-sm text-ink-500">{description}</p>
      {action && <div className="mt-5">{action}</div>}
    </div>
  );
}

export function ConfirmDialog({
  open,
  title,
  message,
  confirmLabel = 'Delete',
  onConfirm,
  onCancel,
}: {
  open: boolean;
  title: string;
  message: string;
  confirmLabel?: string;
  onConfirm: () => void;
  onCancel: () => void;
}) {
  const cancelRef = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    if (!open) return;
    // Escape closes; focus lands on the safe (cancel) button; page scroll locks.
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        e.stopPropagation();
        onCancel();
      }
    };
    document.addEventListener('keydown', onKey);
    cancelRef.current?.focus();
    const prevOverflow = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    return () => {
      document.removeEventListener('keydown', onKey);
      document.body.style.overflow = prevOverflow;
    };
  }, [open, onCancel]);

  if (!open) return null;
  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-ink-950/40 p-4"
      role="dialog"
      aria-modal="true"
      aria-label={title}
      onClick={onCancel}
    >
      <div
        className="card w-full max-w-md animate-fade-in"
        onClick={(e) => e.stopPropagation()}
      >
        <h2 className="text-lg font-semibold">{title}</h2>
        <p className="mt-2 text-sm text-ink-600">{message}</p>
        <div className="mt-6 flex justify-end gap-3">
          <Button ref={cancelRef} variant="secondary" onClick={onCancel}>
            Cancel
          </Button>
          <Button variant="danger" onClick={onConfirm}>
            {confirmLabel}
          </Button>
        </div>
      </div>
    </div>
  );
}

// ------------------------------------------------------------------ toasts
interface Toast {
  id: number;
  message: string;
  kind: 'success' | 'error';
}

let toastId = 0;
const listeners = new Set<(toasts: Toast[]) => void>();
let toasts: Toast[] = [];

export function toast(message: string, kind: Toast['kind'] = 'success') {
  const t = { id: ++toastId, message, kind };
  toasts = [...toasts, t];
  listeners.forEach((l) => l(toasts));
  setTimeout(() => {
    toasts = toasts.filter((x) => x.id !== t.id);
    listeners.forEach((l) => l(toasts));
  }, 3500);
}

export function Toaster() {
  const [items, setItems] = useState<Toast[]>([]);
  useEffect(() => {
    listeners.add(setItems);
    return () => {
      listeners.delete(setItems);
    };
  }, []);
  return (
    <div className="fixed bottom-5 right-5 z-50 flex flex-col gap-2" aria-live="polite">
      {items.map((t) => (
        <div
          key={t.id}
          className={`rounded-lg px-4 py-3 text-sm shadow-raised animate-fade-in ${
            t.kind === 'success' ? 'bg-ink-900 text-white' : 'bg-rose-600 text-white'
          }`}
        >
          {t.message}
        </div>
      ))}
    </div>
  );
}
