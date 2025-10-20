import * as React from 'react';
import QPage from './QPage';
import ChatHistoryPanel from './ChatHistoryPanel';
import HelpTab from './HelpTab';
import HelpBubbles from './HelpBubbles';
import styles from './QChat.module.scss';

type Msg = { role: 'user' | 'assistant'; text: string };
type Conversation = { id: string; title: string; messages: Msg[]; created: string };

export default function QChat() {
  const [msgs, setMsgs] = React.useState<Msg[]>([
    { role: 'assistant', text: 'Hi! Ask me about MyQ resources.' }
  ]);
  const [input, setInput] = React.useState('');
  const [showPage, setShowPage] = React.useState(false);
  const [showHelpTab, setShowHelpTab] = React.useState(false);
  const [showTips, setShowTips] = React.useState(true);
  const [historyOpen, setHistoryOpen] = React.useState(true);
  const [history, setHistory] = React.useState<Conversation[]>(() => {
    try {
      const raw = localStorage.getItem('qchat.conversations');
      return raw ? JSON.parse(raw) : [];
    } catch {
      return [];
    }
  });
  // current conversation id (null = new unsaved conv)
  const [currentConvId, setCurrentConvId] = React.useState<string | null>(null);

  async function onSend(e?: React.FormEvent) {
    e?.preventDefault();
    if (!input.trim()) return;

    const user = { role: 'user' as const, text: input.trim() };
    setMsgs(m => [...m, user]);

    // api calls to llm come here
    setInput('');
    // persist conversation: if this is the first user message in a new conversation, create a new Conversation
    try {
      if (!currentConvId) {
        const id = (Date.now() + Math.random()).toString(36);
        const title = user.text.slice(0, 60);
        const conv: Conversation = { id, title, messages: [...msgs, user], created: new Date().toISOString() };
        const newHist = [conv].concat(history).slice(0, 50);
        setHistory(newHist);
        localStorage.setItem('qchat.conversations', JSON.stringify(newHist));
        setCurrentConvId(id);
      } else {
        // update existing conversation messages
        const updated = history.map(h => h.id === currentConvId ? { ...h, messages: [...h.messages, user] } : h);
        setHistory(updated);
        localStorage.setItem('qchat.conversations', JSON.stringify(updated));
      }
    } catch { /* ignore */ }
  }

  function handleLoadConversation(conv: Conversation) {
    setMsgs(conv.messages);
    setCurrentConvId(conv.id);
  }

  if (showPage) {
    return <QPage onClose={() => setShowPage(false)} />;
  }

  return (
    <div style={{ fontFamily: 'Segoe UI, system-ui', maxWidth: 980 }}>
      {showHelpTab && <HelpTab onClose={() => setShowHelpTab(false)} />}
      <ChatHistoryPanel open={historyOpen} onClose={() => setHistoryOpen(false)} history={history} onLoad={handleLoadConversation} />
      <div style={{ background: '#012a5a', color: 'white', padding: '12px 16px', borderRadius: 6, display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 12 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <button onClick={() => setHistoryOpen(v => !v)} style={{ padding: '6px 10px', borderRadius: 8 }}>History</button>
          <div style={{ fontWeight: 700, fontSize: 18 }}>QCHAT</div>
        </div>
        <div>
          <button onClick={() => setShowHelpTab(true)} style={{ padding: '6px 10px', borderRadius: 8, background: '#0a58ca', color: 'white', border: 'none' }}>Help</button>
        </div>
      </div>

  <div className={styles.chatMain} style={{ padding: 12, borderRadius: 12, border: '1px solid #ddd', marginTop: 12, minHeight: 520 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <HelpBubbles open={showTips} />
          <button onClick={() => setShowTips(t => !t)} style={{ padding: '6px 10px', borderRadius: 8 }}>{showTips ? 'Hide Tips' : 'Show Tips'}</button>
        </div>

        <div style={{ maxHeight: 380, overflowY: 'auto', marginTop: 12 }}>
          {msgs.map((m, i) => (
            <div key={i} style={{
              background: m.role === 'assistant' ? '#f5f5f5' : '#e8f3ff',
              padding: 10, borderRadius: 10, margin: '6px 0'
            }}>
              <strong>{m.role === 'assistant' ? 'qChat' : 'You'}: </strong>{m.text}
            </div>
          ))}
        </div>
      </div>

      <form onSubmit={onSend} style={{ display: 'flex', gap: 8, marginTop: 10 }}>
        <input
          value={input}
          onChange={e => setInput(e.target.value)}
          placeholder="Type a question…"
          style={{ flex: 1, padding: 10, borderRadius: 10, border: '1px solid #ccc' }}
        />
        <button type="submit" style={{
          padding: '10px 16px', borderRadius: 10, border: '1px solid #0078D4', background: '#0078D4', color: 'white'
        }}>
          Send
        </button>
      </form>
    </div>
  );
}