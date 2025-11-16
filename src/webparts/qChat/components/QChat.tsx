import * as React from 'react';
import QPage from './QPage';
import ChatHistoryPanel from './ChatHistoryPanel';
import HelpTab from './HelpTab';
import HelpBubbles from './HelpBubbles';
import styles from './QChat.module.scss';

type Msg = { role: 'user' | 'assistant'; text: string };
type Conversation = { id: string; title: string; messages: Msg[]; created: string };

// local host for the llm- connects to backend
//const llm_base = 'http://localhost:7071';
const llm_base = 'https://ropier-subtetanical-isla.ngrok-free.dev';
//const llm_base = 'https://subcollegiate-jaelynn-punningly.ngrok-free.dev';

export default function QChat() {
  // Visible messages in the active conversation (or in-progress messages before save)
  const [msgs, setMsgs] = React.useState<Msg[]>([
    { role: 'assistant', text: 'Hi! Ask me about MyQ resources.' }
  ]);

  const [input, setInput] = React.useState('');
  const [showPage, setShowPage] = React.useState(false);
  const [showHelpTab, setShowHelpTab] = React.useState(false);
  const [showTips, setShowTips] = React.useState(true);
  const [historyOpen, setHistoryOpen] = React.useState(false);

  // Generate persistent user id (in-memory, no localStorage)
  const [userId] = React.useState<string>(() => {
    return 'user_' + Date.now().toString(36) + Math.random().toString(36).substring(2);
  });

  // Keep conversations in memory only (no localStorage)
  const [history, setHistory] = React.useState<Conversation[]>([]);

  // current conversation id (null = in-progress new conversation)
  const [currentConvId, setCurrentConvId] = React.useState<string | null>(null);

  /*
    onSend: called when user submits the input form.

    - Adds the message to the visible `msgs`.
    - If no `currentConvId` exists, we create a new Conversation entry and persist it.
    - Otherwise we append the new message to the matching Conversation in `history` and persist.
  */
  async function onSend(e?: React.FormEvent) {
    e?.preventDefault();
    if (!input.trim()) return;
    const msg = input.trim();

    const user = { role: 'user' as const, text: input.trim() };
    // Add to the UI immediately (optimistic update). Replies from the assistant would be appended later.
    setMsgs(m => [...m, user]);
    setInput(''); // Reset textbox immediately

    // Ensure there is a session id for this conversation before calling backend
    let sessionId = currentConvId;
    if (!sessionId) {
      sessionId = 'session_' + Date.now().toString(36) + Math.random().toString(36).substring(2);
      setCurrentConvId(sessionId);
    }

    try {
      const result = await fetch(`${llm_base}/api/chat`, {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({ action: 'chat', userId, sessionId, message: msg }),
      });
      
      if (!result.ok) {
        throw new Error(`HTTP ${result.status}`);
      }
      
      // const data = await result.json();
      // const assistantText = data.response ?? '(no reply)';
      // const assistant: Msg = {role: 'assistant', text: assistantText};
      const data = await result.json();
      const reply = data.reply || '(no reply)';
      const sources = Array.isArray(data.sources) ? data.sources : [];

      let text = reply;
      if (sources.length > 0) {
        text += `\n\nSources: ${sources.slice(0, 3).join(', ')}${sources.length > 3 ? '...' : ''}`;
      }

      const assistant: Msg = { role: 'assistant', text };
      setMsgs(m => [...m, assistant]);

      // Persist conversation state to history (in-memory only)
      if (!currentConvId) {
        // First user message in a new conversation -> create a new Conversation object.
        const title = user.text.slice(0, 60);
        const conv: Conversation = { 
          id: sessionId, 
          title, 
          messages: [...msgs, user, assistant], 
          created: new Date().toISOString() 
        };

        // Prepend to history (newest first) and cap to 50 items
        const newHist = [conv, ...history].slice(0, 50);
        setHistory(newHist);
      } else {
        // Append to an existing conversation object in history
        const updated = history.map(h => 
          h.id === sessionId 
            ? { ...h, messages: [...h.messages, user, assistant] } 
            : h
        );
        setHistory(updated);
      }

    } catch (err) {
      console.error('Chat request error', err);
      setMsgs(m => [...m, {role: 'assistant', text: "Could not access LLM. Please check if backend is running."}]);
    }
  }

  // Parent handler passed to the ChatHistoryPanel: replace visible messages with the selected conversation's messages.
  function handleLoadConversation(conv: Conversation) {
    setMsgs(conv.messages);
    // Mark this conversation as the current one so subsequent sends append to it.
    setCurrentConvId(conv.id);
  }

  if (showPage) {
    return <QPage onClose={() => setShowPage(false)} />;
  }

  return (
    <div style={{ fontFamily: 'Segoe UI, system-ui', maxWidth: 980 }}>
      {showHelpTab && <HelpTab onClose={() => setShowHelpTab(false)} />}
      {/* History panel is controlled (open/close) by this component */}
      <ChatHistoryPanel 
        open={historyOpen} 
        onClose={() => setHistoryOpen(false)} 
        history={history} 
        onLoad={handleLoadConversation} 
      />
      <div style={{ 
        background: '#012a5a', 
        color: 'white', 
        padding: '12px 16px', 
        borderRadius: 6, 
        display: 'flex', 
        alignItems: 'center', 
        justifyContent: 'space-between', 
        marginBottom: 12 
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          {/* Toggle history panel */}
          <button 
            onClick={() => setHistoryOpen(v => !v)} 
            style={{ padding: '6px 10px', borderRadius: 8 }}
          >
            History
          </button>
          <div style={{ fontWeight: 700, fontSize: 18 }}>QCHAT</div>
        </div>
        <div>
          <button 
            onClick={() => setShowHelpTab(true)} 
            style={{ 
              padding: '6px 10px', 
              borderRadius: 8, 
              background: '#0a58ca', 
              color: 'white', 
              border: 'none' 
            }}
          >
            Help
          </button>
        </div>
      </div>

      <div className={styles.chatMain} style={{ 
        padding: 12, 
        borderRadius: 12, 
        border: '1px solid #ddd', 
        marginTop: 12, 
        minHeight: 520 
      }}>
        <div style={{ 
          display: 'flex', 
          justifyContent: 'space-between', 
          alignItems: 'center' 
        }}>
          <HelpBubbles open={showTips} />
          <button 
            onClick={() => setShowTips(t => !t)} 
            style={{ padding: '6px 10px', borderRadius: 8 }}
          >
            {showTips ? 'Hide Tips' : 'Show Tips'}
          </button>
        </div>

        <div style={{ maxHeight: 380, overflowY: 'auto', marginTop: 12 }}>
          {msgs.map((m, i) => (
            <div key={i} style={{
              background: m.role === 'assistant' ? '#f5f5f5' : '#e8f3ff',
              padding: 10, 
              borderRadius: 10, 
              margin: '6px 0'
            }}>
              <strong>{m.role === 'assistant' ? 'qChat' : 'You'}: </strong>
              {m.text}
            </div>
          ))}
        </div>
      </div>

      <form onSubmit={onSend} style={{ display: 'flex', gap: 8, marginTop: 10 }}>
        <input
          value={input}
          onChange={e => setInput(e.target.value)}
          placeholder="Type a question…"
          style={{ 
            flex: 1, 
            padding: 10, 
            borderRadius: 10, 
            border: '1px solid #ccc' 
          }}
        />
        <button 
          type="submit" 
          style={{
            padding: '10px 16px', 
            borderRadius: 10, 
            border: '1px solid #0078D4', 
            background: '#0078D4', 
            color: 'white'
          }}
        >
          Send
        </button>
      </form>
    </div>
  );
}