import * as React from 'react';
import styles from './AdminPanel.module.css';
import localSettings from '../../backend/local.settings.json';

const llm_base = localSettings.Values.SERVER_URL || 'http://localhost:7071';

export default function AdminPanel(props: { onClose: () => void }) {
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
    <div className={styles.overlay}>
      <div className={styles.panel}>
        <div className={styles.header}>
          <h2 className={styles.title}>Admin – QU docs URLs</h2>
          <button type="button" className={styles.closeButton} onClick={props.onClose} aria-label="Close">
            ×
          </button>
        </div>
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
                  <button type="button" className={styles.secondaryButton} onClick={() => { setAdding(false); setNewUrl(''); }}>
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
      </div>
    </div>
  );
}
