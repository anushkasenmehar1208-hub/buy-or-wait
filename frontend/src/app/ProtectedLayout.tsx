import { useCallback, useEffect, useRef, useState } from 'react';
import { NavLink, Navigate, Outlet, useLocation, useNavigate } from 'react-router-dom';
import { useAuth } from '../features/auth/AuthContext';
import { Avatar } from '../features/account/Avatar';
import { PageLoader } from '../components/ui';
import { getStoredTheme, setTheme, watchSystemTheme } from '../utils/theme';
import type { ThemePreference } from '../utils/theme';

const navItems = [
  { to: '/', label: 'Dashboard', end: true },
  { to: '/affordability', label: 'Can I afford it?' },
  { to: '/financial-profile', label: 'Financial profile' },
  { to: '/history', label: 'History' },
];

export function ProtectedLayout() {
  const { user, loading, signout } = useAuth();
  const location = useLocation();
  const [theme, setThemeState] = useState<ThemePreference>('system');

  useEffect(() => setThemeState(getStoredTheme()), []);
  useEffect(() => watchSystemTheme(), []);

  const cycleTheme = useCallback(() => {
    const order: ThemePreference[] = ['light', 'dark', 'system'];
    const next = order[(order.indexOf(getStoredTheme()) + 1) % order.length];
    setTheme(next);
    setThemeState(next);
  }, []);

  if (loading) return <PageLoader />;
  if (!user) return <Navigate to="/signin" replace state={{ from: location }} />;

  return (
    <div className="flex min-h-screen flex-col bg-ink-50 text-ink-900">
      <header className="sticky top-0 z-40 border-b border-ink-100 bg-surface/90 backdrop-blur">
        <div className="mx-auto flex h-16 max-w-6xl items-center justify-between px-4 sm:px-6">
          <div className="flex items-center gap-8">
            <NavLink to="/" className="text-lg font-semibold tracking-tight">
              Buy or Wait<span className="text-sage-600">?</span>
            </NavLink>
            <nav className="hidden gap-1 md:flex" aria-label="Primary">
              {navItems.map((item) => (
                <NavLink
                  key={item.to}
                  to={item.to}
                  end={item.end}
                  className={({ isActive }) =>
                    `rounded-lg px-3 py-2 text-sm font-medium transition-colors ${
                      isActive ? 'bg-ink-100 text-ink-900' : 'text-ink-500 hover:bg-ink-100 hover:text-ink-800'
                    }`
                  }
                >
                  {item.label}
                </NavLink>
              ))}
            </nav>
          </div>
          <div className="flex items-center gap-3">
            <ThemeToggleButton theme={theme} onCycle={cycleTheme} />
            <ProfileMenu user={user} theme={theme} onSignout={signout} />
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
      <main className="mx-auto w-full max-w-6xl flex-1 px-4 py-8 sm:px-6">
        <Outlet />
      </main>
      <footer className="mx-auto max-w-6xl px-4 pb-8 pt-4 text-center text-xs text-ink-400 sm:px-6">
        Buy or Wait? — educational financial planning tool. Not financial advice.
      </footer>
    </div>
  );
}

function ThemeToggleButton({ theme, onCycle }: { theme: ThemePreference; onCycle: () => void }) {
  const label =
    theme === 'dark'
      ? 'Theme: dark theme. Switch to light theme'
      : theme === 'light'
        ? 'Theme: light theme. Switch to system theme'
        : 'Theme: System theme. Switch to dark theme';
  return (
    <button
      type="button"
      onClick={onCycle}
      aria-label={label}
      title="Change theme"
      className="flex h-9 w-9 items-center justify-center rounded-full text-ink-500 transition-colors
        hover:bg-ink-100 hover:text-ink-800 focus-visible:outline-none focus-visible:ring-2
        focus-visible:ring-sage-500 focus-visible:ring-offset-2"
    >
      {theme === 'light' ? (
        <svg aria-hidden="true" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <circle cx="12" cy="12" r="4" />
          <path d="M12 2v2m0 16v2M4.93 4.93l1.41 1.41m11.32 11.32 1.41 1.41M2 12h2m16 0h2M4.93 19.07l1.41-1.41M17.66 6.34l1.41-1.41" />
        </svg>
      ) : theme === 'dark' ? (
        <svg aria-hidden="true" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z" />
        </svg>
      ) : (
        <svg aria-hidden="true" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <rect x="2" y="3" width="20" height="14" rx="2" />
          <path d="M8 21h8m-4-4v4" />
        </svg>
      )}
    </button>
  );
}

/**
 * Circular avatar button in the navbar with an anchored dropdown menu.
 *
 * Closes on: outside pointer-down, Escape, a second click on the avatar, or
 * activating any item. Arrow keys rove focus across menu items; Tab leaves.
 */
function ProfileMenu({ user, theme, onSignout }: {
  user: { full_name: string; email: string; avatar_url: string | null };
  theme: ThemePreference;
  onSignout: () => void;
}) {
  const [open, setOpen] = useState(false);
  const navigate = useNavigate();
  const wrapRef = useRef<HTMLDivElement>(null);
  const avatarRef = useRef<HTMLButtonElement>(null);
  const menuRef = useRef<HTMLDivElement>(null);

  // Close on any pointer-down outside the avatar + menu, and on Escape.
  useEffect(() => {
    if (!open) return;
    const onPointerDown = (e: PointerEvent) => {
      if (wrapRef.current && !wrapRef.current.contains(e.target as Node)) setOpen(false);
    };
    const onKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        setOpen(false);
        avatarRef.current?.focus();
      }
    };
    document.addEventListener('pointerdown', onPointerDown);
    document.addEventListener('keydown', onKeyDown);
    return () => {
      document.removeEventListener('pointerdown', onPointerDown);
      document.removeEventListener('keydown', onKeyDown);
    };
  }, [open]);

  // Roving focus: ArrowUp/Down/Home/End move between menu items.
  const onMenuKeyDown = (e: React.KeyboardEvent) => {
    if (!menuRef.current) return;
    const items = [...menuRef.current.querySelectorAll<HTMLButtonElement>('[role=menuitem]')];
    const idx = items.indexOf(document.activeElement as HTMLButtonElement);
    let next = -1;
    if (e.key === 'ArrowDown') next = idx < 0 ? 0 : (idx + 1) % items.length;
    else if (e.key === 'ArrowUp') next = idx < 0 ? items.length - 1 : (idx - 1 + items.length) % items.length;
    else if (e.key === 'Home') next = 0;
    else if (e.key === 'End') next = items.length - 1;
    if (next >= 0) {
      e.preventDefault();
      items[next]!.focus();
    }
  };

  return (
    <div ref={wrapRef} className="relative">
      <button
        ref={avatarRef}
        type="button"
        onClick={() => setOpen((v) => !v)}
        onKeyDown={(e) => {
          if (open && e.key === 'ArrowDown') {
            e.preventDefault();
            menuRef.current?.querySelector<HTMLButtonElement>('[role=menuitem]')?.focus();
          }
        }}
        aria-haspopup="menu"
        aria-expanded={open}
        aria-label="Account menu"
        title="Account"
        className={`rounded-full transition-opacity focus-visible:outline-none focus-visible:ring-2
          focus-visible:ring-sage-500 focus-visible:ring-offset-2 ${open ? 'ring-2 ring-sage-500 ring-offset-2' : 'hover:opacity-85'}`}
      >
        <Avatar user={user} size="md" />
      </button>

      {open && (
        <div
          ref={menuRef}
          role="menu"
          aria-label="Account"
          onKeyDown={onMenuKeyDown}
          className="absolute right-0 top-11 z-50 w-60 overflow-hidden rounded-xl
            border border-ink-100 bg-surface shadow-card animate-fade-in"
        >
          <div className="flex items-center gap-3 border-b border-ink-100 px-4 py-3">
            <Avatar user={user} size="md" />
            <div className="min-w-0">
              <p className="truncate text-sm font-medium text-ink-900">
                {user.full_name || 'Account'}
              </p>
              <p className="truncate text-xs text-ink-500">{user.email}</p>
            </div>
          </div>
          <div className="p-1.5">
            <MenuItem
              label="Profile"
              onClick={() => {
                setOpen(false);
                navigate('/profile');
              }}
            />
            <MenuItem
              label="Appearance"
              hint={themeLabel(theme)}
              onClick={() => {
                setOpen(false);
                navigate('/settings#appearance');
              }}
            />
            <MenuItem
              label="Settings"
              onClick={() => {
                setOpen(false);
                navigate('/settings');
              }}
            />
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
              onClick={() => {
                setOpen(false);
                navigate('/profile#danger');
              }}
            />
          </div>
        </div>
      )}
    </div>
  );
}

function themeLabel(theme: ThemePreference): string {
  return theme === 'dark' ? 'Dark' : theme === 'light' ? 'Light' : 'System';
}

function MenuItem({
  label, hint, onClick, destructive = false,
}: {
  label: string;
  hint?: string;
  onClick: () => void;
  destructive?: boolean;
}) {
  return (
    <button
      type="button"
      role="menuitem"
      tabIndex={-1}
      onClick={onClick}
      className={`flex w-full items-center justify-between rounded-lg px-3 py-2 text-left text-sm transition-colors
        focus-visible:bg-ink-100 focus-visible:outline-none
        ${destructive
          ? 'text-rose-600 hover:bg-rose-50 dark:text-rose-400 dark:hover:bg-rose-500/10'
          : 'text-ink-700 hover:bg-ink-100'}`}
    >
      {label}
      {hint && <span className="text-xs text-ink-400">{hint}</span>}
    </button>
  );
}
