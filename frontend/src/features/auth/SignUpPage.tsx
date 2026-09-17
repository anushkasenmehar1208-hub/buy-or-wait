import { useState } from 'react';
import type { FormEvent } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from './AuthContext';
import { Button, Input } from '../../components/ui';
import { ApiError } from '../../services/api';

export function SignUpPage() {
  const { signup } = useAuth();
  const navigate = useNavigate();
  const [fullName, setFullName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  function validate(): boolean {
    const errs: Record<string, string> = {};
    if (!email.includes('@')) errs.email = 'Enter a valid email address';
    if (password.length < 8) errs.password = 'At least 8 characters';
    else if (!/\d/.test(password)) errs.password = 'Include at least one digit';
    else if (!/[a-zA-Z]/.test(password)) errs.password = 'Include at least one letter';
    setFieldErrors(errs);
    return Object.keys(errs).length === 0;
  }

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    if (!validate()) return;
    setLoading(true);
    try {
      await signup(email, password, fullName);
      navigate('/profile', { replace: true });
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Sign up failed');
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center px-4">
      <div className="w-full max-w-md animate-fade-in">
        <h1 className="text-center text-2xl font-semibold tracking-tight">
          Create your account
        </h1>
        <p className="mt-2 text-center text-sm text-ink-500">
          Set up your finances once — ask "can I afford it?" anytime.
        </p>
        <form onSubmit={onSubmit} className="card mt-8 space-y-5 p-6" noValidate>
          <Input
            label="Full name"
            name="full_name"
            autoComplete="name"
            value={fullName}
            onChange={(e) => setFullName(e.target.value)}
          />
          <Input
            label="Email"
            name="email"
            type="email"
            autoComplete="email"
            required
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            error={fieldErrors.email}
          />
          <Input
            label="Password"
            name="password"
            type="password"
            autoComplete="new-password"
            required
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            error={fieldErrors.password ?? error}
            hint="At least 8 characters with a letter and a digit"
          />
          <Button type="submit" loading={loading} className="w-full">
            Create account
          </Button>
          <p className="text-center text-sm text-ink-500">
            Already have an account?{' '}
            <Link to="/signin" className="font-medium text-sage-700 hover:underline">
              Sign in
            </Link>
          </p>
        </form>
      </div>
    </div>
  );
}
