import * as React from 'react';
import styles from './ChatHistoryPanel.module.css';

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
        {/* Close button - calls parent onClose to toggle visibility */}
        <button onClick={props.onClose} aria-label="Close history">x</button>
      </div>

      <div className={styles.list}>
        {/* Empty state when there are no saved conversations */}
        {props.history.length === 0 && <div className={styles.empty}>No saved conversations</div>}

        {/* Render each conversation as a selectable item. The parent receives the
            full Conversation object and decides how to display or activate it. */}
        {props.history.map((conv) => (
          <div
            key={conv.id}
            className={styles.item}
            onClick={() => props.onLoad(conv)}
            tabIndex={0}
            role="button"
          >
            <div className={styles.preview}><strong>{conv.title || 'Conversation'}</strong></div>
            <div className={styles.count}>{conv.messages.length} msgs · {new Date(conv.created).toLocaleString()}</div>
          </div>
        ))}
      </div>
    </div>
  );
}
