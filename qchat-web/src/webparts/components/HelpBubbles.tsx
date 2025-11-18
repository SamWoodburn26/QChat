import styles from './HelpBubbles.module.css';

export default function HelpBubbles(props: { open: boolean }) {
  const tips = [
    { id: 't1', title: 'Ask a question', body: 'Type a clear question in the input box and press Send. qChat will suggest resources.' },
    { id: 't2', title: 'Use keywords', body: 'Use specific keywords like "registration", "tuition", or "library" for better results.' },
    { id: 't3', title: 'View history', body: 'Open the History panel to load past conversations.' }
  ];

  if (!props.open) return null;

  return (
    <div className={styles.container} aria-hidden={!props.open}>
      {tips.map(t => (
        <div key={t.id} className={styles.tip}>
          <div className={styles.tipTitle}>{t.title}</div>
          <div className={styles.tipBody}>{t.body}</div>
        </div>
      ))}
    </div>
  );
}
