import * as React from 'react';
import styles from './LoginDropdown.module.css';

export default function LoginDropdown(props: {
  open: boolean;
  onClose: () => void;
  currentUser: string | null;
  onLogin: (username: string, password: string) => void;
  onRegister: (username: string, password: string) => void;
  onMicrosoftLogin: () => void;
  onLogout: () => void;
}) {
  const [username, setUsername] = React.useState('');
  const [password, setPassword] = React.useState('');
  const [isRegistering, setIsRegistering] = React.useState(false);

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (username.trim() && password.trim()) {
      if (isRegistering) {
        props.onRegister(username.trim(), password.trim());
      } else {
        props.onLogin(username.trim(), password.trim());
      }
      setUsername('');
      setPassword('');
    }
  }

  if (!props.open) return null;

  return (
    <div className={styles.dropdown}>
      <div className={styles.header}>
        <h3>{isRegistering ? 'Register' : 'Login'}</h3>
        <button onClick={props.onClose} aria-label="Close login">×</button>
      </div>

      {props.currentUser ? (
        <div className={styles.content}>
          <p className={styles.loggedIn}>
            Logged in as: <strong>{props.currentUser}</strong>
          </p>
          <button onClick={props.onLogout} className={styles.logoutBtn}>
            Logout
          </button>
        </div>
      ) : (
        <form onSubmit={handleSubmit} className={styles.content}>
          <button
            type="button"
            onClick={props.onMicrosoftLogin}
            className={styles.microsoftBtn}
          >
            <svg width="21" height="21" viewBox="0 0 21 21" fill="none">
              <rect width="10" height="10" fill="#F25022"/>
              <rect x="11" width="10" height="10" fill="#7FBA00"/>
              <rect y="11" width="10" height="10" fill="#00A4EF"/>
              <rect x="11" y="11" width="10" height="10" fill="#FFB900"/>
            </svg>
            Sign in with Microsoft
          </button>
          
          <div className={styles.divider}>
            <span>OR</span>
          </div>

          <input
            type="text"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            placeholder="Enter username"
            className={styles.input}
          />
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="Enter password"
            className={styles.input}
          />
          <button type="submit" className={styles.loginBtn}>
            {isRegistering ? 'Register' : 'Login'}
          </button>
          <button
            type="button"
            onClick={() => setIsRegistering(!isRegistering)}
            className={styles.toggleBtn}
          >
            {isRegistering ? 'Already have an account? Login' : 'Need an account? Register'}
          </button>
        </form>
      )}
    </div>
  );
}