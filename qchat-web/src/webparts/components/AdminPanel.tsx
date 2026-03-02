import * as React from 'react';
import styles from './AdminPanel.module.css';
import localSettings from '../../backend/local.settings.json';

const llm_base = localSettings.Values.SERVER_URL || 'http://localhost:7071';


type Tab = 'urls' | 'users' | 'backend';

interface User {
  _id: string;
  username: string;
  name?: string;
  role: 'student' | 'admin';
  createdAt: string;
  lastLogin?: string;
}


export default function AdminPanel(props: { onClose: () => void }) {
  const [activeTab, setActiveTab] = React.useState<Tab>('urls');

  return (
    <div className={styles.overlay}>
      <div className={styles.panel}>
        <div className={styles.header}>
          <h2 className={styles.title}>Admin Panel</h2>
          <button type="button" className={styles.closeButton} onClick={props.onClose} aria-label="Close">
            ×
          </button>
        </div>

        {/* Tabs Navigation */}
        <div className={styles.tabs}>
          <button
            type="button"
            className={`${styles.tab} ${activeTab === 'urls' ? styles.tabActive : ''}`}
            onClick={() => setActiveTab('urls')}
          >
            URLs
          </button>
          <button
            type="button"
            className={`${styles.tab} ${activeTab === 'users' ? styles.tabActive : ''}`}
            onClick={() => setActiveTab('users')}
          >
            Users
          </button>
          <button
            type="button"
            className={`${styles.tab} ${activeTab === 'backend' ? styles.tabActive : ''}`}
            onClick={() => setActiveTab('backend')}
          >
            Backend
          </button>
        </div>

        {/* Tab Content */}
        <div className={styles.tabContent}>
          {activeTab === 'urls' && <URLsTab />}
          {activeTab === 'users' && <UsersTab />}
          {activeTab === 'backend' && <BackendTab />}
        </div>
      </div>
    </div>
  );
}

function URLsTab() {
  const [urls, setUrls] = React.useState<string[]>([]);
  const [loading, setLoading] = React.useState(true);
  const [saving, setSaving] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);
  const [adding, setAdding] = React.useState(false);
  const [newUrl, setNewUrl] = React.useState('');

  const loadUrls = React.useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`${llm_base}/api/qu_docs`);
      if (!res.ok) throw new Error('Failed to load URLs');
      const data = await res.json();
      setUrls(Array.isArray(data.urls) ? data.urls : []);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load URLs');
      setUrls([]);
    } finally {
      setLoading(false);
    }
  }, []);

  React.useEffect(() => {
    loadUrls();
  }, [loadUrls]);

  async function saveUrls(newList: string[]) {
    setSaving(true);
    setError(null);
    try {
      const res = await fetch(`${llm_base}/api/qu_docs`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ urls: newList }),
      });
      if (!res.ok) throw new Error('Failed to save URLs');
      const data = await res.json();
      setUrls(Array.isArray(data.urls) ? data.urls : newList);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to save URLs');
    } finally {
      setSaving(false);
    }
  }

  function removeUrl(index: number) {
    const next = urls.filter((_, i) => i !== index);
    saveUrls(next);
  }

  function addUrl() {
    const u = newUrl.trim();
    if (!u.startsWith('http://') && !u.startsWith('https://')) {
      setError('URL must start with http:// or https://');
      return;
    }
    setAdding(false);
    setNewUrl('');
    saveUrls([...urls, u]);
  }

  function removeDuplicates() {
    const seen = new Set<string>();
    const next = urls.filter((u) => {
      const key = u.toLowerCase().replace(/\/$/, '');
      if (seen.has(key)) return false;
      seen.add(key);
      return true;
    });
    if (next.length === urls.length) return;
    saveUrls(next);
  }

  return (
    <>
      {error && <div className={styles.error}>{error}</div>}
      {loading ? (
        <div className={styles.loading}>Loading…</div>
      ) : (
        <>
          <div className={styles.toolbar}>
            <button
              type="button"
              className={styles.secondaryButton}
              onClick={removeDuplicates}
              disabled={saving}
            >
              Remove duplicate links
            </button>
            {!adding ? (
              <button
                type="button"
                className={styles.primaryButton}
                onClick={() => setAdding(true)}
                disabled={saving}
              >
                Add URL
              </button>
            ) : (
              <div className={styles.addRow}>
                <input
                  type="url"
                  className={styles.input}
                  value={newUrl}
                  onChange={(e) => setNewUrl(e.target.value)}
                  placeholder="https://..."
                  autoFocus
                />
                <button type="button" className={styles.primaryButton} onClick={addUrl} disabled={saving}>
                  Add
                </button>
                <button
                  type="button"
                  className={styles.secondaryButton}
                  onClick={() => {
                    setAdding(false);
                    setNewUrl('');
                  }}
                >
                  Cancel
                </button>
              </div>
            )}
          </div>
          <ul className={styles.list}>
            {urls.map((url, i) => (
              <li key={`${i}-${url}`} className={styles.row}>
                <a href={url} target="_blank" rel="noopener noreferrer" className={styles.link}>
                  {url}
                </a>
                <button
                  type="button"
                  className={styles.removeButton}
                  onClick={() => removeUrl(i)}
                  disabled={saving}
                  aria-label="Remove"
                >
                  Remove
                </button>
              </li>
            ))}
          </ul>
        </>
      )}
    </>
  );
}


// USERS TAB 
function UsersTab() {
  const [users, setUsers] = React.useState<User[]>([]);
  const [loading, setLoading] = React.useState(true);
  const [error, setError] = React.useState<string | null>(null);
  const [updating, setUpdating] = React.useState<string | null>(null);

  React.useEffect(() => {
    loadUsers();
  }, []);

  async function loadUsers() {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`${llm_base}/api/usersadmin`);
      if (!res.ok) throw new Error('Failed to load users');
      const data = await res.json();
      setUsers(data.users || []);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load users');
    } finally {
      setLoading(false);
    }
  }

  async function toggleRole(userId: string, currentRole: string) {
    setUpdating(userId);
    setError(null);
    const newRole = currentRole === 'admin' ? 'student' : 'admin';

    try {
      const res = await fetch(`${llm_base}/api/usersadmin/${userId}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ role: newRole }),
      });

      if (!res.ok) throw new Error('Failed to update role');

      setUsers((prev) =>
        prev.map((u) => (u._id === userId ? { ...u, role: newRole as 'student' | 'admin' } : u))
      );
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to update role');
    } finally {
      setUpdating(null);
    }
  }

  if (loading) return <div className={styles.loading}>Loading users...</div>;

  return (
    <>
      {error && <div className={styles.error}>{error}</div>}
      <div className={styles.tableWrapper}>
        <table className={styles.table}>
          <thead>
            <tr>
              <th>Username</th>
              <th>Name</th>
              <th>Role</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {users.map((user) => (
              <tr key={user._id}>
                <td>{user.username}</td>
                <td>{user.name || '-'}</td>
                <td>
                  <span className={user.role === 'admin' ? styles.badgeAdmin : styles.badgeStudent}>
                    {user.role}
                  </span>
                </td>
                <td>
                  <button
                    type="button"
                    className={styles.roleButton}
                    onClick={() => toggleRole(user._id, user.role)}
                    disabled={updating === user._id}
                  >
                    {updating === user._id
                      ? '...'
                      : user.role === 'admin'
                      ? 'Make Student'
                      : 'Make Admin'}
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {users.length === 0 && <div className={styles.empty}>No users found</div>}
      </div>
    </>
  );
}


// BACKEND TAB 
function BackendTab() {
  const [status, setStatus] = React.useState<'checking' | 'running' | 'stopped'>('checking');
  const [error, setError] = React.useState<string | null>(null);
  const [action, setAction] = React.useState<'idle' | 'restarting'>('idle');

  React.useEffect(() => {
    checkStatus();
  }, []);

  async function checkStatus() {
    setStatus('checking');
    setError(null);
    try {
      const res = await fetch(`${llm_base}/api/health`, { signal: AbortSignal.timeout(3000) });
      setStatus(res.ok ? 'running' : 'stopped');
    } catch {
      setStatus('stopped');
    }
  }

  async function restartBackend() {
    setAction('restarting');
    setError(null);
    try {
      const res = await fetch(`${llm_base}/api/adminrestart`, { method: 'POST' });
      if (!res.ok) throw new Error('Failed to restart backend');
      setTimeout(checkStatus, 2000);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to restart');
    } finally {
      setAction('idle');
    }
  }

  return (
    <div className={styles.backendControl}>
      {error && <div className={styles.error}>{error}</div>}

      <div className={styles.statusCard}>
        <h3>Backend Status</h3>
        <div className={styles.statusRow}>
          <span>Status:</span>
          <span
            className={
              status === 'running'
                ? styles.statusRunning
                : status === 'stopped'
                ? styles.statusStopped
                : styles.statusChecking
            }
          >
            {status === 'running' ? 'Running' : status === 'stopped' ? 'Stopped' : 'Checking...'}
          </span>
        </div>
        <button
          type="button"
          className={styles.secondaryButton}
          onClick={checkStatus}
          disabled={action !== 'idle'}
        >
          Refresh Status
        </button>
      </div>

      <div className={styles.actionsCard}>
        <h3>Actions</h3>
        <button
          type="button"
          className={styles.primaryButton}
          onClick={restartBackend}
          disabled={action !== 'idle'}
          style={{ width: '100%', marginBottom: '12px' }}
        >
          {action === 'restarting' ? 'Restarting...' : ' Restart Backend'}
        </button>
        <p className={styles.warning}> Warning: This will restart the backend and may affect all users.</p>
      </div>
    </div>
  );
}