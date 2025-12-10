import * as React from 'react';
import styles from './LoginDropdown.module.css';

export default function LoginDropdown(props: {
  open: boolean;
  onClose: () => void;
  currentUser: string | null;
  onLogin: (username: string, password: string) => void;
  onRegister: (username: string, password: string) => void;
  onMicrosoftLogin: () => void;
  onGoogleLogin: () => void;
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
          
          <button
            type="button"
            onClick={props.onGoogleLogin}
            className={styles.googleBtn}
          >
            <svg width="18" height="18" viewBox="0 0 18 18" fill="none">
              <path d="M17.64 9.2c0-.637-.057-1.251-.164-1.84H9v3.481h4.844c-.209 1.125-.843 2.078-1.796 2.717v2.258h2.908c1.702-1.567 2.684-3.874 2.684-6.615z" fill="#4285F4"/>
              <path d="M9.003 18c2.43 0 4.467-.806 5.956-2.18L12.05 13.56c-.806.54-1.837.86-3.047.86-2.344 0-4.328-1.584-5.036-3.711H.957v2.332C2.438 15.983 5.482 18 9.003 18z" fill="#34A853"/>
              <path d="M3.964 10.71c-.18-.54-.282-1.117-.282-1.71 0-.593.102-1.17.282-1.71V4.958H.957C.347 6.173 0 7.548 0 9c0 1.452.348 2.827.957 4.042l3.007-2.332z" fill="#FBBC05"/>
              <path d="M9.003 3.58c1.321 0 2.508.454 3.44 1.345l2.582-2.58C13.464.891 11.426 0 9.003 0 5.482 0 2.438 2.017.957 4.958L3.964 7.29c.708-2.127 2.692-3.71 5.039-3.71z" fill="#EA4335"/>
            </svg>
            Sign in with Google
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
