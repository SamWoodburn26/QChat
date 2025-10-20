import * as React from 'react';
import styles from './ChatHistoryPanel.module.scss';

type Msg = { role: 'user' | 'assistant'; text: string };
type Conversation = { id: string; title: string; messages: Msg[]; created: string };

export default function ChatHistoryPanel(props: {
  open: boolean;
  onClose: () => void;
  history: Conversation[];
  onLoad: (conv: Conversation) => void;
}) {
  return (
    <div className={`${styles.panel} ${props.open ? styles.open : ''}`} role="dialog" aria-hidden={!props.open}>
      <div className={styles.header}>
        <h3>Chat history</h3>
        <button onClick={props.onClose} aria-label="Close history">×</button>
      </div>

      <div className={styles.list}>
        {props.history.length === 0 && <div className={styles.empty}>No saved conversations</div>}
        {props.history.map((conv) => (
          <div key={conv.id} className={styles.item} onClick={() => props.onLoad(conv)} tabIndex={0} role="button">
            <div className={styles.preview}><strong>{conv.title || 'Conversation'}</strong></div>
            <div className={styles.count}>{conv.messages.length} msgs · {new Date(conv.created).toLocaleString()}</div>
          </div>
        ))}
      </div>
    </div>
  );
}
