import { useEffect, useState } from 'react';
import { useAuth } from '../auth/AuthContext';
import { useAccount } from './AccountContext';
import { Avatar } from './Avatar';
import { Button, Card, Input, Skeleton, toast } from '../../components/ui';
import { ApiError } from '../../services/api';
import { getStoredTheme, setTheme, watchSystemTheme } from '../../utils/theme';
import type { ThemePreference } from '../../utils/theme';

const THEME_OPTIONS: { value: ThemePreference; label: string; description: string }[] = [
  { value: 'light', label: 'Light', description: 'Bright and clean' },
  { value: 'dark', label: 'Dark', description: 'Low-light friendly' },
  { value: 'system', label: 'System', description: 'Match your device' },
];

/**
 * /settings — Account + Appearance. Preferences stay honest: only settings
 * that already work end-to-end appear here (no fake toggles).
 */
export function SettingsPage() {
  const { user, loading } = useAuth();

  if (loading) {
    return (
      <div className="mx-auto max-w-2xl space-y-8 animate-fade-in">
        <div>
          <Skeleton className="h-8 w-40" />
          <Skeleton className="mt-2 h-4 w-64" />
        </div>
        <Skeleton className="h-64" />
        <Skeleton className="h-44" />
      </div>
    );
  }
  if (!user) return null;

  return (
    <div className="mx-auto max-w-2xl space-y-8 animate-fade-in">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Settings</h1>
        <p className="mt-1 text-sm text-ink-500">Account details and how the app looks.</p>
      </div>
      <AccountSection />
      <AppearanceSection />
    </div>
  );
}

function AccountSection() {
  const { user } = useAuth();
  if (!user) return null;
  const { updateName } = useAccount();
  const [name, setName] = useState(user.full_name);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => setName(user.full_name), [user.full_name]);
  const changed = name !== user.full_name;

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    if (!name.trim()) {
      setError('Name cannot be blank');
      return;
    }
    setSaving(true);
    try {
      await updateName(name.trim());
      toast('Settings saved');
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Save failed');
    } finally {
      setSaving(false);
    }
  }

  return (
    <Card>
      <h2 className="text-base font-semibold">Account</h2>
      <div className="mt-4 flex items-center gap-4">
        <Avatar user={user} size="lg" />
        <div>
          <p className="text-sm font-medium text-ink-800">{user.full_name || 'Account'}</p>
          <p className="text-xs text-ink-500">{user.email}</p>
          <p className="mt-1 text-xs text-ink-400">
            Edit your photo on the{' '}
            <a href="/profile" className="text-sage-700 hover:underline">profile page</a>.
          </p>
        </div>
      </div>
      <form onSubmit={submit} className="mt-5 space-y-4">
        <Input
          label="Display name"
          name="settings_full_name"
          value={name}
          maxLength={120}
          onChange={(e) => setName(e.target.value)}
        />
        <Input
          label="Email address"
          name="settings_email"
          value={user.email}
          readOnly
          hint="Email changes are not supported yet."
          className="cursor-not-allowed opacity-70"
        />
        {error && <p className="field-error" role="alert">{error}</p>}
        <Button type="submit" loading={saving} disabled={!changed}>Save changes</Button>
      </form>
    </Card>
  );
}

function AppearanceSection() {
  const [pref, setPref] = useState<ThemePreference>(getStoredTheme());

  useEffect(() => watchSystemTheme(), []);

  function choose(next: ThemePreference) {
    setTheme(next); // single source of truth: utils/theme.ts (same as the navbar cycle)
    setPref(next);
  }

  return (
    <Card>
      <div id="appearance" className="scroll-mt-24">
        <h2 className="text-base font-semibold">Appearance</h2>
        <p className="mt-0.5 text-sm text-ink-500">Choose how Buy or Wait? looks on this device.</p>
        <div role="radiogroup" aria-label="Theme" className="mt-4 grid gap-3 sm:grid-cols-3">
          {THEME_OPTIONS.map((opt) => (
            <button
              key={opt.value}
              type="button"
              role="radio"
              aria-checked={pref === opt.value}
              onClick={() => choose(opt.value)}
              className={`rounded-xl border p-4 text-left transition-colors focus-visible:outline-none
                focus-visible:ring-2 focus-visible:ring-sage-500 ${
                  pref === opt.value
                    ? 'border-sage-500 bg-sage-500/5'
                    : 'border-ink-200 hover:border-ink-300 hover:bg-ink-100/50'
                }`}
            >
              <div className="flex items-center justify-between">
                <span className="text-sm font-medium text-ink-800">{opt.label}</span>
                {pref === opt.value && (
                  <svg aria-hidden="true" width="16" height="16" viewBox="0 0 24 24" fill="none"
                    stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"
                    className="text-sage-600">
                    <path d="M20 6 9 17l-5-5" />
                  </svg>
                )}
              </div>
              <p className="mt-1 text-xs text-ink-500">{opt.description}</p>
            </button>
          ))}
        </div>
      </div>
    </Card>
  );
}
