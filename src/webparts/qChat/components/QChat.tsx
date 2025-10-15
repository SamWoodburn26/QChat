import * as React from 'react';

type Msg = { role: 'user' | 'assistant'; text: string };

export default function QChat() {
  const [msgs, setMsgs] = React.useState<Msg[]>([
    { role: 'assistant', text: 'Hi! Ask me about MyQ resources.' }
  ]);
  const [input, setInput] = React.useState('');

  async function onSend(e?: React.FormEvent) {
    e?.preventDefault();
    if (!input.trim()) return;

    const user = { role: 'user' as const, text: input.trim() };
    setMsgs(m => [...m, user]);

    // api calls to llm come here
  }

  return (
    <div style={{ fontFamily: 'Segoe UI, system-ui', maxWidth: 700 }}>
      <div style={{ padding: 12, borderRadius: 12, border: '1px solid #ddd' }}>
        {msgs.map((m, i) => (
          <div key={i} style={{
            background: m.role === 'assistant' ? '#f5f5f5' : '#e8f3ff',
            padding: 10, borderRadius: 10, margin: '6px 0'
          }}>
            <strong>{m.role === 'assistant' ? 'qChat' : 'You'}: </strong>{m.text}
          </div>
        ))}
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