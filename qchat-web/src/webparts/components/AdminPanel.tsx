import * as React from 'react';
import styles from './AdminPanel.module.css';
import localSettings from '../../backend/local.settings.json';

const llm_base = localSettings.Values.SERVER_URL || 'http://localhost:7071';


type Tab = 'urls' | 'users' | 'backend';

interface User {
  _id: string;
  username: string;
  name?: string;
  role: 'student' | 'admin' | 'teacher';
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
  const [searchQuery, setSearchQuery] = React.useState('');

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

  // Filtered URLs
  const filteredUrls = React.useMemo(() => {
    if (!searchQuery.trim()) return urls;
    const query = searchQuery.toLowerCase();
    return urls.filter(url => url.toLowerCase().includes(query));
  }, [urls, searchQuery]);

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

          {/* SEARCH BAR */}
          <div className={styles.searchBar}>
            <input
              type="text"
              className={styles.searchInput}
              placeholder="Search URLs..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
            />
            {searchQuery && (
              <button
                type="button"
                className={styles.clearSearchButton}
                onClick={() => setSearchQuery('')}
              >
                ×
              </button>
            )}
          </div>

          <div className={styles.urlCount}>
            Showing {filteredUrls.length} of {urls.length} URLs
          </div>

          <ul className={styles.list}>
            {filteredUrls.map((url) => {
              const originalIndex = urls.indexOf(url);
              return (
                <li key={`${originalIndex}-${url}`} className={styles.row}>
                  <a href={url} target="_blank" rel="noopener noreferrer" className={styles.link}>
                    {url}
                  </a>
                  <button
                    type="button"
                    className={styles.removeButton}
                    onClick={() => removeUrl(originalIndex)}
                    disabled={saving}
                    aria-label="Remove"
                  >
                    Remove
                  </button>
                </li>
              );
            })}
          </ul>
          {filteredUrls.length === 0 && <div className={styles.empty}>No URLs found</div>}
        </>
      )}
    </>
  );
}


// USERS TAB - WITH SEARCH AND TEACHER ROLE
function UsersTab() {
  const [users, setUsers] = React.useState<User[]>([]);
  const [loading, setLoading] = React.useState(true);
  const [error, setError] = React.useState<string | null>(null);
  const [updating, setUpdating] = React.useState<string | null>(null);
  const [searchQuery, setSearchQuery] = React.useState('');

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

  async function changeRole(userId: string, newRole: 'student' | 'admin' | 'teacher') {
    setUpdating(userId);
    setError(null);

    try {
      const res = await fetch(`${llm_base}/api/usersadmin/${userId}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ role: newRole }),
      });

      if (!res.ok) throw new Error('Failed to update role');

      setUsers((prev) =>
        prev.map((u) => (u._id === userId ? { ...u, role: newRole } : u))
      );
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to update role');
    } finally {
      setUpdating(null);
    }
  }

  // Filtered Users
  const filteredUsers = React.useMemo(() => {
    if (!searchQuery.trim()) return users;
    const query = searchQuery.toLowerCase();
    return users.filter(user => 
      user.username.toLowerCase().includes(query) ||
      user.name?.toLowerCase().includes(query) ||
      user.role.toLowerCase().includes(query)
    );
  }, [users, searchQuery]);

  if (loading) return <div className={styles.loading}>Loading users...</div>;

  return (
    <>
      {error && <div className={styles.error}>{error}</div>}

      {/* SEARCH BAR */}
      <div className={styles.searchBar}>
        <input
          type="text"
          className={styles.searchInput}
          placeholder="Search users (username, name, role)..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
        />
        {searchQuery && (
          <button
            type="button"
            className={styles.clearSearchButton}
            onClick={() => setSearchQuery('')}
          >
            ×
          </button>
        )}
      </div>

      <div className={styles.urlCount}>
        Showing {filteredUsers.length} of {users.length} users
      </div>

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
            {filteredUsers.map((user) => (
              <tr key={user._id}>
                <td>{user.username}</td>
                <td>{user.name || '-'}</td>
                <td>
                  <span 
                    className={
                      user.role === 'admin' 
                        ? styles.badgeAdmin 
                        : user.role === 'teacher' 
                          ? styles.badgeTeacher 
                          : styles.badgeStudent
                    }
                  >
                    {user.role}
                  </span>
                </td>
                <td>
                  <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
                    {user.role !== 'student' && (
                      <button
                        type="button"
                        className={styles.roleButton}
                        onClick={() => changeRole(user._id, 'student')}
                        disabled={updating === user._id}
                      >
                        Student
                      </button>
                    )}
                    {user.role !== 'admin' && (
                      <button
                        type="button"
                        className={styles.roleButton}
                        onClick={() => changeRole(user._id, 'admin')}
                        disabled={updating === user._id}
                      >
                        Admin
                      </button>
                    )}
                    {user.role !== 'teacher' && (
                      <button
                        type="button"
                        className={styles.roleButton}
                        onClick={() => changeRole(user._id, 'teacher')}
                        disabled={updating === user._id}
                      >
                        Teacher
                      </button>
                    )}
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {filteredUsers.length === 0 && <div className={styles.empty}>No users found</div>}
      </div>
    </>
  );
}


// BACKEND TAB - MAINTENANCE MODE CONTROL
function BackendTab() {
  const [status, setStatus] = React.useState<{ enabled: boolean; message: string; updated_at: string | null; updated_by: string | null } | null>(null);
  const [loading, setLoading] = React.useState(true);
  const [error, setError] = React.useState<string | null>(null);
  const [toggling, setToggling] = React.useState(false);

  React.useEffect(() => {
    loadStatus();
  }, []);

  async function loadStatus() {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`${llm_base}/api/maintenance`);
      if (!res.ok) throw new Error('Failed to load status');
      const data = await res.json();
      setStatus(data);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load status');
    } finally {
      setLoading(false);
    }
  }

  async function toggleMaintenance() {
    if (!status) return;
    
    const newEnabled = !status.enabled;
    const confirmMsg = newEnabled 
      ? 'WARNING: This will DISABLE chat for ALL users (including admins). Continue?'
      : 'Enable chat for all users?';
    
    if (!confirm(confirmMsg)) return;

    setToggling(true);
    setError(null);
    
    try {
      const username = localStorage.getItem('username') || 'admin';
      
      const res = await fetch(`${llm_base}/api/maintenance`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          enabled: newEnabled,
          updated_by: username
        })
      });

      if (!res.ok) throw new Error('Failed to toggle maintenance mode');
      
      const data = await res.json();
      setStatus(data);
      
      alert(newEnabled ? 'Maintenance mode ENABLED - Chat is now OFFLINE for everyone' : 'Maintenance mode DISABLED - Chat is now online');
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to toggle maintenance mode');
    } finally {
      setToggling(false);
    }
  }

  if (loading) return <div className={styles.loading}>Loading status...</div>;

  return (
    <div className={styles.backendControl}>
      {error && <div className={styles.error}>{error}</div>}

      <div className={styles.statusCard}>
        <h3>Emergency Maintenance Mode</h3>
        <div className={styles.statusRow}>
          <span>Status:</span>
          <span className={status?.enabled ? styles.statusStopped : styles.statusRunning}>
            {status?.enabled ? 'CHAT OFFLINE' : 'CHAT ONLINE'}
          </span>
        </div>
        
        {status?.enabled && status.updated_by && (
          <div style={{ marginTop: '12px', fontSize: '14px', color: '#666' }}>
            <div>Disabled by: {status.updated_by}</div>
            {status.updated_at && <div>At: {new Date(status.updated_at).toLocaleString()}</div>}
          </div>
        )}

        <button
          type="button"
          className={status?.enabled ? styles.primaryButton : styles.dangerButton}
          onClick={toggleMaintenance}
          disabled={toggling}
          style={{ width: '100%', marginTop: '16px' }}
        >
          {toggling 
            ? 'Processing...' 
            : status?.enabled 
              ? 'ENABLE CHAT (Turn ON)' 
              : 'DISABLE CHAT (Emergency Shutdown)'}
        </button>
      </div>

      <div className={styles.warningBox}>
        <strong>Warning:</strong> When maintenance mode is enabled, ALL users (including admins) cannot use chat. 
        Use this only in emergency situations (security breach, data leak, etc.).
      </div>
    </div>
  );
}