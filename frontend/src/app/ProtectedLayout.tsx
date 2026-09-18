import { useEffect, useRef, useState } from 'react';
import { NavLink, Navigate, Outlet, useLocation, useNavigate } from 'react-router-dom';
import { useAuth } from '../features/auth/AuthContext';
import { PageLoader, toast } from '../components/ui';
import type { User } from '../types';
import { getStoredTheme, setTheme, watchSystemTheme } from '../utils/theme';
import type { ThemePreference } from '../utils/theme';

const navItems = [
  { to: '/', label: 'Dashboard', end: true },
  { to: '/affordability', label: 'Can I afford it?' },
  { to: '/profile', label: 'Financial profile' },
  { to: '/history', label: 'History' },
];

const nextTheme: Record<ThemePreference, ThemePreference> = {
  light: 'dark',
  dark: 'system',
  system: 'light',
};

const themeLabel: Record<ThemePreference, string> = {
  light: 'Light theme',
  dark: 'Dark theme',
  system: 'System theme',
};

export function ProtectedLayout() {
  const { user, loading, signout } = useAuth();
  const location = useLocation();
  const [theme, setThemeState] = useState<ThemePreference>('system');

  useEffect(() => {
    setThemeState(getStoredTheme());
    return watchSystemTheme();
  }, []);

  function cycleTheme() {
    const next = nextTheme[theme];
    setTheme(next);
    setThemeState(next);
  }

  if (loading) return <PageLoader />;
  if (!user) return <Navigate to="/signin" state={{ from: location }} replace />;

  return (
    <div className="min-h-screen bg-ink-50">
      <header className="sticky top-0 z-40 border-b border-ink-100 bg-surface/90 backdrop-blur-sm">
        <div className="mx-auto flex h-16 max-w-6xl items-center justify-between gap-4 px-4 sm:px-6">
          <div className="flex items-center gap-8">
            <NavLink to="/" className="text-lg font-semibold tracking-tight text-ink-900">
              Buy or Wait<span className="text-sage-600">?</span>
            </NavLink>
            <nav className="hidden items-center gap-1 md:flex" aria-label="Main">
              {navItems.map((item) => (
                <NavLink
                  key={item.to}
                  to={item.to}
                  end={item.end}
                  className={({ isActive }) =>
                    `rounded-lg px-3 py-2 text-sm font-medium transition-colors ${
                      isActive
                        ? 'bg-ink-100 text-ink-900'
                        : 'text-ink-500 hover:bg-ink-100 hover:text-ink-800'
                    }`
                  }
                >
                  {item.label}
                </NavLink>
              ))}
            </nav>
          </div>
          <div className="flex items-center gap-3">
            <button
              type="button"
              onClick={cycleTheme}
              aria-label={`Theme: ${themeLabel[theme]}. Switch to ${themeLabel[nextTheme[theme]].toLowerCase()}`}
              title={`Theme: ${themeLabel[theme]}`}
              className="flex h-9 w-9 items-center justify-center rounded-lg text-ink-500 transition-colors
                hover:bg-ink-100 hover:text-ink-800 focus-visible:outline-none focus-visible:ring-2
                focus-visible:ring-sage-500"
            >
              {theme === 'dark' ? (
                /* moon — currently dark */
                <svg aria-hidden="true" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z" />
                </svg>
              ) : theme === 'light' ? (
                /* sun — currently light */
                <svg aria-hidden="true" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <circle cx="12" cy="12" r="4" />
                  <path d="M12 2v2m0 16v2M4.93 4.93l1.41 1.41m11.32 11.32 1.41 1.41M2 12h2m16 0h2M4.93 19.07l1.41-1.41M17.66 6.34l1.41-1.41" />
                </svg>
              ) : (
                /* monitor — system */
                <svg aria-hidden="true" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <rect x="2" y="3" width="20" height="14" rx="2" />
                  <path d="M8 21h8m-4-4v4" />
                </svg>
              )}
            </button>
            <ProfileMenu user={user} theme={theme} onCycleTheme={cycleTheme} onSignout={signout} />
          </div>
        </div>
        {/* mobile nav */}
        <nav className="flex gap-1 overflow-x-auto border-t border-ink-100 px-4 py-2 md:hidden" aria-label="Mobile">
          {navItems.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.end}
              className={({ isActive }) =>
                `whitespace-nowrap rounded-lg px-3 py-1.5 text-sm font-medium ${
                  isActive ? 'bg-ink-100 text-ink-900' : 'text-ink-500'
                }`
              }
            >
              {item.label}
            </NavLink>
          ))}
        </nav>
      </header>
      <main className="mx-auto max-w-6xl px-4 py-8 sm:px-6">
        <Outlet />
      </main>
      <footer className="mx-auto max-w-6xl px-4 pb-8 pt-4 text-center text-xs text-ink-400 sm:px-6">
        Buy or Wait? — educational financial planning tool. Not financial advice.
      </footer>
    </div>
  );
}

/**
 * Circular avatar button in the navbar with an anchored dropdown menu.
 *
 * Closes on: outside pointer-down, Escape, a second click on the avatar, or
 * activating any item. Entries with no page yet (Settings, Delete account)
 * say so honestly via toast instead of pretending.
 */
function ProfileMenu({ user, theme, onCycleTheme, onSignout }: {
  user: User;
  theme: ThemePreference;
  onCycleTheme: () => void;
  onSignout: () => void;
}) {
  const [open, setOpen] = useState(false);
  const navigate = useNavigate();
  const wrapRef = useRef<HTMLDivElement>(null);

  // Close on any pointer-down outside the avatar + menu, and on Escape.
  useEffect(() => {
    if (!open) return;
    const onPointerDown = (e: PointerEvent) => {
      if (wrapRef.current && !wrapRef.current.contains(e.target as Node)) setOpen(false);
    };
    const onKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setOpen(false);
    };
    document.addEventListener('pointerdown', onPointerDown);
    document.addEventListener('keydown', onKeyDown);
    return () => {
      document.removeEventListener('pointerdown', onPointerDown);
      document.removeEventListener('keydown', onKeyDown);
    };
  }, [open]);

  const initials = (user.full_name || user.email)
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0]!.toUpperCase())
    .join('');

  const themeLabel = theme === 'dark' ? 'Dark' : theme === 'light' ? 'Light' : 'System';

  return (
    <div ref={wrapRef} className="relative">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        aria-haspopup="menu"
        aria-expanded={open}
        aria-label="Account menu"
        title="Account"
        className={`flex h-9 w-9 items-center justify-center rounded-full bg-sage-600
          text-sm font-semibold text-ink-50 transition-colors hover:bg-sage-700
          focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-sage-500
          focus-visible:ring-offset-2 ${open ? 'ring-2 ring-sage-500 ring-offset-2' : ''}`}
      >
        {/* initials avatar — profile-picture upload comes later */}
        <span aria-hidden="true">{initials || 'U'}</span>
      </button>

      {open && (
        <div
          role="menu"
          aria-label="Account"
          className="absolute right-0 top-11 z-50 w-56 overflow-hidden rounded-xl
            border border-ink-100 bg-surface shadow-card"
        >
          <div className="border-b border-ink-100 px-4 py-3">
            <p className="truncate text-sm font-medium text-ink-900">
              {user.full_name || 'Account'}
            </p>
            <p className="truncate text-xs text-ink-500">{user.email}</p>
          </div>
          <div className="p-1.5">
            <MenuItem
              label="Profile"
              onClick={() => {
                setOpen(false);
                navigate('/profile');
              }}
            />
            <MenuItem label={`Appearance · ${themeLabel}`} onClick={onCycleTheme} />
            <MenuItem label="Settings" onClick={() => toast('Settings is not available yet.')} />
          </div>
          <div className="border-t border-ink-100 p-1.5">
            <MenuItem
              label="Sign out"
              onClick={() => {
                setOpen(false);
                onSignout();
              }}
            />
          </div>
          <div className="border-t border-ink-100 p-1.5">
            <MenuItem
              label="Delete account"
              destructive
              onClick={() => toast('Account deletion is not available yet.')}
            />
          </div>
        </div>
      )}
    </div>
  );
}

function MenuItem({ label, onClick, destructive = false }: {
  label: string;
  onClick: () => void;
  destructive?: boolean;
}) {
  return (
    <button
      type="button"
      role="menuitem"
      onClick={onClick}
      className={`w-full rounded-lg px-3 py-2 text-left text-sm transition-colors
        ${destructive
          ? 'text-rose-600 hover:bg-rose-50 dark:text-rose-400 dark:hover:bg-rose-500/10'
          : 'text-ink-700 hover:bg-ink-100'}`}
    >
      {label}
    </button>
  );
}
