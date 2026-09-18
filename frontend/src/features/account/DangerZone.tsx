import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAccount } from './AccountContext';
import { Avatar } from './Avatar';
import { ConfirmDialog, Button, Card, toast } from '../../components/ui';
import { ApiError } from '../../services/api';
import type { User } from '../../types';

/**
 * Danger zone at the bottom of the profile page. Deletion is handled here
 * (with confirmation) and linked from the navbar menu's Delete account item.
 */
export function DangerZone({ user }: { user: User }) {
  return (
    <Card className="border-rose-200 dark:border-rose-500/30">
      <h2 className="text-base font-semibold text-rose-600 dark:text-rose-400">Danger zone</h2>
      <div id="danger" className="mt-4 flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex items-center gap-4">
          <Avatar user={user} size="lg" />
          <div>
            <p className="text-sm font-medium text-ink-800">Delete account</p>
            <p className="mt-0.5 max-w-md text-sm text-ink-500">
              Permanently removes your account, financial profile, and decision history.
              This cannot be undone.
            </p>
          </div>
        </div>
        <DeleteAccountButton />
      </div>
    </Card>
  );
}

function DeleteAccountButton() {
  const { deleteAccount } = useAccount();
  const [confirming, setConfirming] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const navigate = useNavigate();

  async function confirm() {
    setDeleting(true);
    try {
      await deleteAccount();
      setConfirming(false);
      navigate('/signin', { replace: true });
      toast('Your account has been deleted');
    } catch (err) {
      setConfirming(false);
      toast(err instanceof ApiError ? err.message : 'Could not delete account', 'error');
    } finally {
      setDeleting(false);
    }
  }

  return (
    <>
      <Button variant="danger" onClick={() => setConfirming(true)}>
        Delete account…
      </Button>
      <ConfirmDialog
        open={confirming}
        title="Delete your account?"
        message="This permanently removes your account and associated data — your financial
          profile, income, expenses, and decision history. This action cannot be undone."
        confirmLabel={deleting ? 'Deleting…' : 'Delete forever'}
        onCancel={() => setConfirming(false)}
        onConfirm={confirm}
      />
    </>
  );
}
