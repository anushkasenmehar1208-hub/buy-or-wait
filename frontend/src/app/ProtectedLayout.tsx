import { useEffect, useState } from 'react';
import { NavLink, Navigate, Outlet, useLocation } from 'react-router-dom';
import { useAuth } from '../features/auth/AuthContext';
import { PageLoader } from '../components/ui';
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
            <span className="hidden text-sm text-ink-500 sm:block">
              {user.full_name || user.email}
            </span>
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
            <button
              onClick={signout}
              className="rounded-lg px-3 py-2 text-sm font-medium text-ink-500 transition-colors
                hover:bg-ink-100 hover:text-ink-800"
            >
              Sign out
            </button>
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
