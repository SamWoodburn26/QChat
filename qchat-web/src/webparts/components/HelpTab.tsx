import styles from './HelpTab.module.css';

export default function HelpTab(props: { onClose?: () => void }) {
  return (
    <div
      className={styles.overlay}
      onClick={(e) => {
        if (e.target === e.currentTarget && props.onClose) props.onClose();
      }}
      role="dialog"
      aria-labelledby="help-title"
      aria-modal="true"
    >
      <div className={styles.popup} onClick={(e) => e.stopPropagation()}>
        <div className={styles.header}>
          <h2 id="help-title" className={styles.title}>About QChat</h2>
          {props.onClose && (
            <button
              type="button"
              className={styles.closeBtn}
              onClick={props.onClose}
              aria-label="Close help"
            >
              Close
            </button>
          )}
        </div>
        <div className={styles.body}>
          <p>
            <strong>QChat</strong> is Quinnipiac University’s assistant. Use it to get quick answers about campus life, MyQ, dining, housing, events, and more.
          </p>
          <p className={styles.sectionTitle}>How to use it</p>
          <p>
            Type your question in the box at the bottom and press Send (or Enter). You can ask about upcoming events, today or next week, or things like “What’s for dinner?” or “How do I reset my password?”
          </p>
          <p>
            Use <strong>History</strong> to open past conversations and <strong>Show Tips</strong> for suggested questions.
          </p>
        </div>
      </div>
    </div>
  );
}
