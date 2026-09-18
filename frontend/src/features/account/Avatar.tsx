import { API_BASE_URL } from '../../services/api';
import type { User } from '../../types';

/**
 * Circular avatar: the user's picture when one exists, initials otherwise.
 * Used by the navbar, the menu header, the profile page, and settings.
 */

/** The API returns a path; resolve it against the backend origin. */
function avatarSrc(url: string): string {
  return url.startsWith('http') ? url : `${API_BASE_URL}${url}`;
}
export function initialsFor(user: Pick<User, 'full_name' | 'email'>): string {
  const source = user.full_name || user.email;
  const parts = source.split(/\s+/).filter(Boolean);
  if (parts.length >= 2) return (parts[0][0] + parts[1][0]).toUpperCase();
  const first = parts[0] ?? 'U';
  if (user.full_name) return first.slice(0, 2).toUpperCase();
  return first[0]!.toUpperCase();
}

export function Avatar({
  user,
  size = 'md',
  className = '',
}: {
  user: Pick<User, 'full_name' | 'email' | 'avatar_url'>;
  size?: 'sm' | 'md' | 'lg' | 'xl';
  className?: string;
}) {
  const sizeClass = {
    sm: 'h-7 w-7 text-[11px]',
    md: 'h-9 w-9 text-sm',
    lg: 'h-16 w-16 text-xl',
    xl: 'h-24 w-24 text-3xl',
  }[size];

  if (user.avatar_url) {
    return (
      <img
        src={avatarSrc(user.avatar_url)}
        alt=""
        className={`${sizeClass} shrink-0 rounded-full object-cover ${className}`}
      />
    );
  }
  return (
    <span
      aria-hidden="true"
      className={`${sizeClass} flex shrink-0 items-center justify-center rounded-full
        bg-sage-600 font-semibold text-ink-50 ${className}`}
    >
      {initialsFor(user)}
    </span>
  );
}
