/**
 * Theme handling — light / dark / system.
 *
 * The dark palette itself lives in CSS variables (src/index.css, `html.dark`);
 * this module only persists the user's choice and toggles the class on <html>.
 * index.html runs a pre-hydration version of the same logic to avoid a
 * light-mode flash before React mounts.
 */
export type ThemePreference = 'light' | 'dark' | 'system';

const STORAGE_KEY = 'bow_theme';

function isDarkNow(pref: ThemePreference): boolean {
  if (pref === 'system') {
    return window.matchMedia('(prefers-color-scheme: dark)').matches;
  }
  return pref === 'dark';
}

export function getStoredTheme(): ThemePreference {
  const stored = localStorage.getItem(STORAGE_KEY);
  return stored === 'light' || stored === 'dark' || stored === 'system' ? stored : 'system';
}

function apply(pref: ThemePreference): void {
  document.documentElement.classList.toggle('dark', isDarkNow(pref));
}

/** Set the preference, persist it, and apply it immediately. */
export function setTheme(pref: ThemePreference): void {
  localStorage.setItem(STORAGE_KEY, pref);
  apply(pref);
}

/**
 * Follow system changes while the user is on "system".
 * Returns a cleanup function for the calling component's effect.
 */
export function watchSystemTheme(): () => void {
  const mq = window.matchMedia('(prefers-color-scheme: dark)');
  const onChange = () => {
    if (getStoredTheme() === 'system') apply('system');
  };
  mq.addEventListener('change', onChange);
  return () => mq.removeEventListener('change', onChange);
}

/** Apply the stored theme on app mount (idempotent with the index.html script). */
export function initTheme(): void {
  apply(getStoredTheme());
}
