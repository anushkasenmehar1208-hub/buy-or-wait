import { useEffect, useRef, useState } from 'react';
import { useAuth } from '../auth/AuthContext';
import { useAccount } from './AccountContext';
import { Avatar } from './Avatar';
import { DangerZone } from './DangerZone';
import { Button, Card, Input, Skeleton, toast } from '../../components/ui';
import { ApiError } from '../../services/api';
import type { User } from '../../types';

const MAX_FILE_BYTES = 2 * 1024 * 1024;
const ACCEPTED = ['image/png', 'image/jpeg', 'image/webp'];

/**
 * Account profile page (/profile): profile photo + personal information.
 * Renders a skeleton instantly while /api/auth/me restores the session —
 * never a blank page (the loading-state rule from the financial profile fix).
 */
export function AccountProfilePage() {
  const { user, loading } = useAuth();

  if (loading) {
    return (
      <div className="mx-auto max-w-2xl space-y-8 animate-fade-in">
        <div>
          <Skeleton className="h-8 w-48" />
          <Skeleton className="mt-2 h-4 w-72" />
        </div>
        <Skeleton className="h-52" />
        <Skeleton className="h-64" />
      </div>
    );
  }
  if (!user) return null;

  return (
    <div className="mx-auto max-w-2xl space-y-8 animate-fade-in">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Profile</h1>
        <p className="mt-1 text-sm text-ink-500">
          How you appear across Buy or Wait?.
        </p>
      </div>
      <PhotoCard user={user} />
      <PersonalInfoCard user={user} />
      <DangerZone user={user} />
    </div>
  );
}

function PhotoCard({ user }: { user: User }) {
  const { uploadAvatar, removeAvatar } = useAccount();
  const [pending, setPending] = useState<File | null>(null);
  const [pendingUrl, setPendingUrl] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [removing, setRemoving] = useState(false);
  const fileRef = useRef<HTMLInputElement>(null);
  const pendingUrlRef = useRef<string | null>(null);

  // Object URLs must be revoked to avoid leaking the blob.
  useEffect(() => {
    pendingUrlRef.current = pendingUrl;
    return () => {
      if (pendingUrlRef.current) URL.revokeObjectURL(pendingUrlRef.current);
    };
  }, [pendingUrl]);

  if (!user) return null;

  function choose(file: File | undefined) {
    if (!file) return;
    if (!ACCEPTED.includes(file.type)) {
      toast('Unsupported image type. Use PNG, JPEG, or WebP.', 'error');
      return;
    }
    if (file.size > MAX_FILE_BYTES) {
      toast('Image is too large. Maximum size is 2 MB.', 'error');
      return;
    }
    if (pendingUrlRef.current) URL.revokeObjectURL(pendingUrlRef.current);
    setPending(file);
    setPendingUrl(URL.createObjectURL(file));
  }

  function discard() {
    if (pendingUrlRef.current) URL.revokeObjectURL(pendingUrlRef.current);
    setPending(null);
    setPendingUrl(null);
    if (fileRef.current) fileRef.current.value = '';
  }

  async function save() {
    if (!pending) return;
    setSaving(true);
    try {
      await uploadAvatar(pending);
      toast('Profile picture updated');
      discard();
    } catch (err) {
      toast(err instanceof ApiError ? err.message : 'Upload failed', 'error');
    } finally {
      setSaving(false);
    }
  }

  async function remove() {
    setRemoving(true);
    try {
      await removeAvatar();
      toast('Profile picture removed');
    } catch (err) {
      toast(err instanceof ApiError ? err.message : 'Could not remove picture', 'error');
    } finally {
      setRemoving(false);
    }
  }

  return (
    <Card>
      <h2 className="text-base font-semibold">Profile photo</h2>
      <p className="mt-0.5 text-sm text-ink-500">PNG, JPEG, or WebP — up to 2 MB.</p>
      <div className="mt-5 flex flex-col items-start gap-6 sm:flex-row sm:items-center">
        <div className="relative">
          <Avatar
            user={pendingUrl ? { ...user, avatar_url: null } : user}
            size="xl"
            className={pendingUrl ? 'hidden' : ''}
          />
          {pendingUrl && (
            <img
              src={pendingUrl}
              alt="Selected profile preview"
              className="h-24 w-24 rounded-full object-cover"
            />
          )}
          {saving && (
            <span className="absolute inset-0 flex items-center justify-center rounded-full
              bg-ink-950/50 text-ink-50" aria-label="Saving">
              <svg className="h-6 w-6 animate-spin" viewBox="0 0 24 24" fill="none" aria-hidden>
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
              </svg>
            </span>
          )}
        </div>
        <div className="flex flex-wrap items-center gap-3">
          <input
            ref={fileRef}
            type="file"
            accept={ACCEPTED.join(',')}
            className="hidden"
            onChange={(e) => choose(e.target.files?.[0])}
          />
          {!pending && (
            <Button variant="secondary" onClick={() => fileRef.current?.click()}>
              {user.avatar_url ? 'Change photo' : 'Upload photo'}
            </Button>
          )}
          {pending && (
            <>
              <Button onClick={save} loading={saving}>Save photo</Button>
              <Button variant="secondary" onClick={discard} disabled={saving}>Cancel</Button>
            </>
          )}
          {!pending && user.avatar_url && (
            <Button variant="secondary" onClick={remove} loading={removing}>
              Remove
            </Button>
          )}
        </div>
      </div>
      <p className="mt-4 text-xs text-ink-400">
        Your picture is private — only you can see it while signed in.
      </p>
    </Card>
  );
}

function PersonalInfoCard({ user }: { user: User }) {
  const { updateName } = useAccount();
  const [name, setName] = useState(user.full_name);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Keep the field in sync when the session/user changes (e.g. after save elsewhere).
  useEffect(() => setName(user.full_name), [user.full_name]);

  const changed = name !== user.full_name;

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    if (!name.trim()) {
      setError('Name cannot be blank');
      return;
    }
    setSaving(true);
    try {
      await updateName(name.trim());
      toast('Profile saved');
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Save failed');
    } finally {
      setSaving(false);
    }
  }

  return (
    <Card>
      <h2 className="text-base font-semibold">Personal information</h2>
      <form onSubmit={submit} className="mt-4 space-y-4">
        <Input
          label="Display name"
          name="full_name"
          value={name}
          maxLength={120}
          onChange={(e) => setName(e.target.value)}
          hint="Shown in the navbar menu and across your account."
        />
        <Input
          label="Email address"
          name="email_readonly"
          value={user.email}
          readOnly
          hint="Email changes are not supported yet."
          className="cursor-not-allowed opacity-70"
        />
        {error && <p className="field-error" role="alert">{error}</p>}
        <div className="flex items-center gap-3">
          <Button type="submit" loading={saving} disabled={!changed}>Save changes</Button>
          {changed && (
            <button
              type="button"
              onClick={() => { setName(user.full_name); setError(null); }}
              className="text-sm text-ink-500 hover:text-ink-800 hover:underline"
            >
              Discard
            </button>
          )}
        </div>
      </form>
    </Card>
  );
}
