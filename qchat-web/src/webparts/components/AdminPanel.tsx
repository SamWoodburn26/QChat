import * as React from 'react';
import styles from './AdminPanel.module.css';
import localSettings from '../../backend/local.settings.json';

const API_BASE = localSettings.Values?.SERVER_URL || 'http://localhost:7071';

type Props = { onClose?: () => void };

export default function AdminPanel(props: Props) {
  const [urls, setUrls] = React.useState<string[]>([]);
  const [loading, setLoading] = React.useState(true);
  const [error, setError] = React.useState<string | null>(null);

  React.useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    fetch(`${API_BASE}/api/qu_docs`)
      .then((res) => {
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return res.json();
      })
      .then((data: { urls?: string[] }) => {
        if (!cancelled && Array.isArray(data.urls)) setUrls(data.urls);
      })
      .catch((e) => {
        if (!cancelled) setError(e instanceof Error ? e.message : String(e));
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => { cancelled = true; };
  }, []);

  return (
    <div
      className={styles.overlay}
      onClick={(e) => {
        if (e.target === e.currentTarget && props.onClose) props.onClose();
      }}
      role="dialog"
      aria-labelledby="admin-panel-title"
      aria-modal="true"
    >
      <div className={styles.panel} onClick={(e) => e.stopPropagation()}>
        <div className={styles.header}>
          <h2 id="admin-panel-title" className={styles.title}>
            Admin — QChat document links
          </h2>
          {props.onClose && (
            <button
              type="button"
              className={styles.closeBtn}
              onClick={props.onClose}
              aria-label="Close admin panel"
            >
              Close
            </button>
          )}
        </div>
        <div className={styles.body}>
          <p className={styles.subtitle}>
            These URLs are used by QChat to answer questions. (Read-only list.)
          </p>
          {loading && <div className={styles.loading}>Loading links…</div>}
          {error && (
            <div className={styles.error}>
              Could not load links: {error}. Is the backend running?
            </div>
          )}
          {!loading && !error && urls.length === 0 && (
            <div className={styles.empty}>No document URLs found.</div>
          )}
          {!loading && !error && urls.length > 0 && (
            <ul className={styles.list}>
              {urls.map((url, i) => (
                <li key={i} className={styles.item}>
                  <a
                    href={url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className={styles.link}
                  >
                    {url}
                  </a>
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>
    </div>
  );
}
