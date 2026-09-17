import { useState } from 'react';
import type { FormEvent } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import type { Location } from 'react-router-dom';
import { useAuth } from './AuthContext';
import { Button, Input } from '../../components/ui';
import { ApiError } from '../../services/api';

export function SignInPage() {
  const { signin } = useAuth();
  const navigate = useNavigate();
  const location = useLocation() as Location & {
    state?: { from?: { pathname: string } };
    search: string;
  };
  const sessionExpired = new URLSearchParams(location.search).get('expired') === '1';
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      await signin(email, password);
      navigate(location.state?.from?.pathname ?? '/', { replace: true });
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Sign in failed');
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center px-4">
      <div className="w-full max-w-md animate-fade-in">
        <h1 className="text-center text-2xl font-semibold tracking-tight">
          Buy or Wait<span className="text-sage-600">?</span>
        </h1>
        <p className="mt-2 text-center text-sm text-ink-500">
          Know whether a purchase is safe — before you make it.
        </p>
        {sessionExpired && (
          <p
            className="mt-3 rounded-lg border border-amber-400/40 bg-amber-400/10 px-3 py-2 text-center text-sm text-amber-700"
            role="status"
          >
            Your session expired. Please sign in again.
          </p>
        )}
        <form onSubmit={onSubmit} className="card mt-8 space-y-5 p-6" noValidate>
          <Input
            label="Email"
            name="email"
            type="email"
            autoComplete="email"
            required
            value={email}
            onChange={(e) => setEmail(e.target.value)}
          />
          <Input
            label="Password"
            name="password"
            type="password"
            autoComplete="current-password"
            required
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            error={error}
          />
          <Button type="submit" loading={loading} className="w-full">
            Sign in
          </Button>
          <p className="text-center text-sm text-ink-500">
            New here?{' '}
            <Link to="/signup" className="font-medium text-sage-700 hover:underline">
              Create an account
            </Link>
          </p>
        </form>
      </div>
    </div>
  );
}
