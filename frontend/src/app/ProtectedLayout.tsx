import { NavLink, Navigate, Outlet, useLocation } from 'react-router-dom';
import { useAuth } from '../features/auth/AuthContext';
import { PageLoader } from '../components/ui';

const navItems = [
  { to: '/', label: 'Dashboard', end: true },
  { to: '/affordability', label: 'Can I afford it?' },
  { to: '/profile', label: 'Financial profile' },
  { to: '/history', label: 'History' },
];

export function ProtectedLayout() {
  const { user, loading, signout } = useAuth();
  const location = useLocation();

  if (loading) return <PageLoader />;
  if (!user) return <Navigate to="/signin" state={{ from: location }} replace />;

  return (
    <div className="min-h-screen bg-ink-50">
      <header className="sticky top-0 z-40 border-b border-ink-100 bg-white/90 backdrop-blur-sm">
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
                        : 'text-ink-500 hover:bg-ink-50 hover:text-ink-800'
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
              onClick={signout}
              className="rounded-lg px-3 py-2 text-sm font-medium text-ink-500 transition-colors
                hover:bg-ink-50 hover:text-ink-800"
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
