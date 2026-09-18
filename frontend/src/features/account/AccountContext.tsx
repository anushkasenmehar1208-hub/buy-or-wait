import { createContext, useCallback, useContext, useMemo } from 'react';
import type { ReactNode } from 'react';
import { accountApi } from '../../services/endpoints';
import { setToken } from '../../services/api';
import { useAuth } from '../auth/AuthContext';
import type { User } from '../../types';

// signout is used by consumers via useSignout(); this context only mutates the user.

interface AccountState {
  /** Update display name; resolves with the saved user. */
  updateName: (fullName: string) => Promise<User>;
  /** Upload a profile picture; resolves with the updated user. */
  uploadAvatar: (file: File) => Promise<User>;
  /** Remove the profile picture; resolves with the updated user. */
  removeAvatar: () => Promise<User>;
  /** Permanently delete the account and clear local auth state. */
  deleteAccount: () => Promise<void>;
}

const AccountContext = createContext<AccountState | null>(null);

export function AccountProvider({ children }: { children: ReactNode }) {
  const { user, setUser } = useAuth();

  const applyUser = useCallback(
    (next: User) => {
      setUser(next);
      return next;
    },
    [setUser],
  );

  const updateName = useCallback(
    async (fullName: string) => {
      if (!user) throw new Error('Not signed in');
      return applyUser(await accountApi.updateProfile({ full_name: fullName }));
    },
    [user, applyUser],
  );

  const uploadAvatar = useCallback(
    async (file: File) => {
      if (!user) throw new Error('Not signed in');
      return applyUser(await accountApi.uploadAvatar(file));
    },
    [user, applyUser],
  );

  const removeAvatar = useCallback(async () => {
    if (!user) throw new Error('Not signed in');
    return applyUser(await accountApi.deleteAvatar());
  }, [user, applyUser]);

  const deleteAccount = useCallback(async () => {
    if (!user) throw new Error('Not signed in');
    try {
      await accountApi.deleteAccount();
    } finally {
      // Even on error, a 204 already destroyed the account server-side only on
      // success; clearing local state keeps the UI honest for success paths.
      setToken(null);
      setUser(null);
    }
  }, [user, setUser]);

  const value = useMemo(
    () => ({ updateName, uploadAvatar, removeAvatar, deleteAccount }),
    [updateName, uploadAvatar, removeAvatar, deleteAccount],
  );

  return <AccountContext.Provider value={value}>{children}</AccountContext.Provider>;
}

export function useAccount(): AccountState {
  const ctx = useContext(AccountContext);
  if (!ctx) throw new Error('useAccount must be used within AccountProvider');
  return ctx;
}

/** Convenience re-export so callers don't import two contexts for signout. */
export function useSignout() {
  const { signout } = useAuth();
  return signout;
}
