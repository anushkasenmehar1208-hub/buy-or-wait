import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react';
import type { ReactNode } from 'react';
import { authApi } from '../../services/endpoints';
import { getToken, setToken } from '../../services/api';
import type { User } from '../../types';

interface AuthState {
  user: User | null;
  loading: boolean;
  signin: (email: string, password: string) => Promise<void>;
  signup: (email: string, password: string, fullName: string) => Promise<void>;
  signout: () => void;
  /** Replace the stored user object (used by account mutations). */
  setUser: (user: User | null) => void;
}

const AuthContext = createContext<AuthState | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    async function restore() {
      if (!getToken()) {
        setLoading(false);
        return;
      }
      try {
        const me = await authApi.me();
        if (!cancelled) setUser(me);
      } catch {
        setToken(null);
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    restore();
    return () => {
      cancelled = true;
    };
  }, []);

  const signin = useCallback(async (email: string, password: string) => {
    const res = await authApi.signin({ email, password });
    setToken(res.access_token);
    setUser(await authApi.me());
  }, []);

  const signup = useCallback(async (email: string, password: string, fullName: string) => {
    const res = await authApi.signup({ email, password, full_name: fullName });
    setToken(res.access_token);
    setUser(await authApi.me());
  }, []);

  const signout = useCallback(() => {
    authApi.signout().catch(() => undefined);
    setToken(null);
    setUser(null);
  }, []);

  const value = useMemo(
    () => ({ user, loading, signin, signup, signout, setUser }),
    [user, loading, signin, signup, signout, setUser],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthState {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used within AuthProvider');
  return ctx;
}
