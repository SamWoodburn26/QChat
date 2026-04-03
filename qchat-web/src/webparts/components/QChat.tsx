import * as React from 'react';
import ChatHistoryPanel from './ChatHistoryPanel.tsx';
import HelpTab from './HelpTab.tsx';
import HelpBubbles from './HelpBubbles.tsx';
import LoginDropdown from './LoginDropdown.tsx';
import styles from './QChat.module.css';
import TMImage from '../assets/TM.png';
import bobcatImage from '../assets/Bobcat.png';
import localSettings from '../../backend/local.settings.json';
import AdminPanel from './AdminPanel';
import TeacherPanel from './TeacherPanel';

type Msg = { role: 'user' | 'assistant'; text: string };
type Conversation = { id: string; title: string; messages: Msg[]; created: string };

const llm_base = localSettings.Values.SERVER_URL || 'http://localhost:7071';

function escapeHtml(text: string): string {
  return text
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

function extractHttpUrl(value: string): string | null {
  const match = value.match(/https?:\/\/[^\s<>"']+/i);
  return match ? match[0].replace(/[),.;:!?]+$/, '') : null;
}

function linkifyText(text: string): string {
  const urlRegex = /https?:\/\/[^\s<>"']+/g;
  const anchorRegex = /(<a\b[^>]*>.*?<\/a>)/gis;
  return text
    .split(anchorRegex)
    .map((segment) => {
      if (segment.toLowerCase().startsWith('<a')) {
        return segment;
      }

      return segment.replace(urlRegex, (url) => {
        const cleanUrl = url.replace(/[),.;:!?]+$/, '');
        return `<a href="${cleanUrl}" target="_blank" rel="noopener noreferrer" style="color: #0078D4; text-decoration: underline;">${cleanUrl}</a>`;
      });
    })
    .join('');
}

export default function QChat() {
  const [hasError, setHasError] = React.useState(false);
  const messagesEndRef = React.useRef<HTMLDivElement>(null);
  const [isLoading, setIsLoading] = React.useState(false);
  
  // Admin state
  const [isAdmin, setIsAdmin] = React.useState(false);
  const [showAdminPanel, setShowAdminPanel] = React.useState(false);
  
  // Teacher state
  const [isTeacher, setIsTeacher] = React.useState(false);
  const [showTeacherPanel, setShowTeacherPanel] = React.useState(false);
  
  React.useEffect(() => {
    console.log('QChat component mounted');
  }, []);

  if (hasError) {
    return <div style={{ padding: 20, color: 'red' }}>Error loading QChat</div>;
  }

  const [msgs, setMsgs] = React.useState<Msg[]>([
    { role: 'assistant', text: 'Hi! Ask me about MyQ resources.' }
  ]);

  React.useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [msgs]);

  const [input, setInput] = React.useState('');
  const [showPage, setShowPage] = React.useState(false);
  const [showHelpTab, setShowHelpTab] = React.useState(false);
  const [showTips, setShowTips] = React.useState(true);
  const [historyOpen, setHistoryOpen] = React.useState(false);
  const [loginOpen, setLoginOpen] = React.useState(false);
  const [currentUser, setCurrentUser] = React.useState<string | null>(null);
  const [history, setHistory] = React.useState<Conversation[]>([]);
  const [currentConvId, setCurrentConvId] = React.useState<string | null>(null);

  // Check admin/teacher status when user changes
  React.useEffect(() => {
    if (currentUser) {
      const role = localStorage.getItem('role');
      setIsAdmin(role === 'admin');
      setIsTeacher(role === 'teacher');
    } else {
      setIsAdmin(false);
      setIsTeacher(false);
    }
  }, [currentUser]);

  async function onSend(e?: React.FormEvent) {
    e?.preventDefault();
    if (!input.trim()) return;
    const msg = input.trim();

    const user = { role: 'user' as const, text: input.trim() };
    setMsgs(m => [...m, user]);
    setInput('');

    let sessionId = currentConvId;
    if (!sessionId) {
      sessionId = 'session_' + Date.now().toString(36) + Math.random().toString(36).substring(2);
      setCurrentConvId(sessionId);
    }

    setIsLoading(true); 

    try {
      const result = await fetch(`${llm_base}/api/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action: 'chat', userId: currentUser || 'anonymous', sessionId, message: msg }),
      });

      if (!result.ok) {
        throw new Error(`HTTP ${result.status}`);
      }

      const data = await result.json();
      const reply = data.reply || '(no reply)';
      const sources: string[] = Array.isArray(data.sources) ? data.sources : [];

      let text = reply;
      text = text.replace(/\n/g, '<br>');
      if (sources.length > 0) {
        const links = sources
          .map((src) => {
            const cleanedUrl = extractHttpUrl(src);
            if (cleanedUrl) {
              return `<li><a href="${cleanedUrl}" target="_blank" rel="noopener noreferrer">${cleanedUrl}</a></li>`;
            }
            return `<li>${escapeHtml(src)}</li>`;
          })
          .join('');
        text += '<br/><br/><strong>Sources:</strong><ul>' + links + '</ul>';
        /*const top_two = sources.slice(0, 2);
        const links = top_two.map(src => `<a g>${src}</a>`).join('<br>');
        text += '<br/><br/><strong>Sources:</strong><br/> ' + links; */
      }

      const assistant: Msg = { role: 'assistant', text };
      setMsgs(m => [...m, assistant]);

      if (!currentConvId) {
        const title = user.text.slice(0, 60);
        const conv: Conversation = {
          id: sessionId,
          title,
          messages: [{ role: 'assistant', text: 'Hi! Ask me about MyQ resources.' }, user, assistant],
          created: new Date().toISOString()
        };

        const newHist = [conv, ...history].slice(0, 50);
        setHistory(newHist);
        if (currentUser) {
          await saveConversationToDb(currentUser, conv);
        }
        setCurrentConvId(sessionId);
      } else {
        const updated = history.map(h =>
          h.id === sessionId
            ? { ...h, messages: [...h.messages, user, assistant] }
            : h
        );
        setHistory(updated);
        if (currentUser) {
          const updatedConv = updated.find(h => h.id === sessionId);
          if (updatedConv) {
            await saveConversationToDb(currentUser, updatedConv);
          }
        }
      }

    } catch (err) {
      console.error('Chat request error', err);
      const message = err instanceof Error
        ? (err.message.startsWith('HTTP ') ? `Backend returned ${err.message}. Check that the API and Ollama are running.` : `Could not reach backend: ${err.message}. Is the backend running at ${llm_base}?`)
        : "Could not access LLM. Please check that (1) the backend is running (e.g. func start) and (2) Ollama is running and reachable.";
      setMsgs(m => [...m, { role: 'assistant', text: message }]);
    }
    finally{
        setIsLoading(false);
    }
  }

  function handleLoadConversation(conv: Conversation) {
    setMsgs(conv.messages);
    setCurrentConvId(conv.id);
  }

  async function saveConversationToDb(username: string, conversation: Conversation) {
    try {
      await fetch(`${llm_base}/api/history`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          action: 'save',
          username,
          conversation
        })
      });
    } catch (err) {
      console.error('Failed to save conversation:', err);
    }
  }

  async function loadConversationsFromDb(username: string) {
    try {
      const response = await fetch(`${llm_base}/api/history?username=${encodeURIComponent(username)}`);
      if (response.ok) {
        const data = await response.json();
        setHistory(data.conversations || []);
      }
    } catch (err) {
      console.error('Failed to load conversations:', err);
    }
  }

  async function handleLogin(username: string, password: string) {
    try {
      const response = await fetch(`${llm_base}/api/auth`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          action: 'login',
          username,
          password
        })
      });

      const data = await response.json();
      
      if (data.success) {
        setCurrentUser(username);
        // Save to localStorage
        localStorage.setItem('username', data.username);
        localStorage.setItem('name', data.name || username);
        localStorage.setItem('role', data.role);
        setIsAdmin(data.role === 'admin');
        setIsTeacher(data.role === 'teacher');
        
        await loadConversationsFromDb(username);
        setLoginOpen(false);
      } else {
        alert(data.error || 'Login failed');
      }
    } catch (err) {
      console.error('Login error:', err);
      alert('Login failed. Please try again.');
    }
  }

  async function handleRegister(username: string, password: string) {
    try {
      const response = await fetch(`${llm_base}/api/auth`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          action: 'register',
          username,
          password
        })
      });

      const data = await response.json();
      
      if (data.success) {
        setCurrentUser(username);
        // Save to localStorage
        localStorage.setItem('username', data.username);
        localStorage.setItem('role', data.role);
        setIsAdmin(data.role === 'admin');
        setIsTeacher(data.role === 'teacher');
        
        await loadConversationsFromDb(username);
        setLoginOpen(false);
      } else {
        alert(data.error || 'Registration failed');
      }
    } catch (err) {
      console.error('Registration error:', err);
      alert('Registration failed. Please try again.');
    }
  }

  function handleLogout() {
    setCurrentUser(null);
    
    //  Clear localStorage
    localStorage.removeItem('username');
    localStorage.removeItem('name');
    localStorage.removeItem('role');
    setIsAdmin(false);
    setIsTeacher(false);
    
    setHistory([]);
    setCurrentConvId(null);
    setMsgs([{ role: 'assistant', text: 'Hi! Ask me about MyQ resources.' }]);
    
    setLoginOpen(false);
  }

  function handleMicrosoftLogin() {
    const clientId = 'YOUR_MICROSOFT_CLIENT_ID';
    const redirectUri = encodeURIComponent(window.location.origin);
    const scope = encodeURIComponent('openid profile email');
    const responseType = 'id_token';
    const nonce = Math.random().toString(36).substring(2);
    
    const authUrl = `https://login.microsoftonline.com/common/oauth2/v2.0/authorize?` +
      `client_id=${clientId}` +
      `&response_type=${responseType}` +
      `&redirect_uri=${redirectUri}` +
      `&scope=${scope}` +
      `&response_mode=fragment` +
      `&nonce=${nonce}`;
    
    const popup = window.open(authUrl, 'Microsoft Login', 'width=500,height=600');
    
    window.addEventListener('message', async (event) => {
      if (event.origin !== window.location.origin) return;
      
      if (event.data.type === 'microsoft-login') {
        popup?.close();
        
        const { email, name } = event.data;
        
        try {
          const response = await fetch(`${llm_base}/api/auth`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              action: 'microsoft_login',
              username: email,
              name: name
            })
          });

          const data = await response.json();
          
          if (data.success) {
            setCurrentUser(name || email);
            localStorage.setItem('username', data.username);
            localStorage.setItem('name', data.name);
            localStorage.setItem('role', data.role);
            setIsAdmin(data.role === 'admin');
            setIsTeacher(data.role === 'teacher');
            
            await loadConversationsFromDb(email);
            setLoginOpen(false);
          } else {
            alert(data.error || 'Microsoft login failed');
          }
        } catch (err) {
          console.error('Microsoft login error:', err);
          alert('Microsoft login failed. Please try again.');
        }
      }
    });
  }

  function handleGoogleLogin() {
    const clientId = '590552919397-6bp7ppthi11rgoiiehrj0jvi0apf3ltm.apps.googleusercontent.com';
    const redirectUri = encodeURIComponent(window.location.origin + '/google-callback.html');
    const scope = encodeURIComponent('openid profile email');
    const responseType = 'id_token';
    const nonce = Math.random().toString(36).substring(2);
    
    const authUrl = `https://accounts.google.com/o/oauth2/v2/auth?` +
      `client_id=${clientId}` +
      `&response_type=${responseType}` +
      `&redirect_uri=${redirectUri}` +
      `&scope=${scope}` +
      `&nonce=${nonce}`;
    
    const popup = window.open(authUrl, 'Google Login', 'width=500,height=600');
    
    const messageHandler = async (event: MessageEvent) => {
      if (event.origin !== window.location.origin) return;
      
      if (event.data.type === 'google-login') {
        popup?.close();
        window.removeEventListener('message', messageHandler);
        
        const { email, name } = event.data;
        
        try {
          const response = await fetch(`${llm_base}/api/auth`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              action: 'google_login',
              username: email,
              name: name
            })
          });

          const data = await response.json();
          
          if (data.success) {
            setCurrentUser(name || email);
            localStorage.setItem('username', data.username);
            localStorage.setItem('name', data.name);
            localStorage.setItem('role', data.role);
            setIsAdmin(data.role === 'admin');
            setIsTeacher(data.role === 'teacher');
            
            await loadConversationsFromDb(email);
            setLoginOpen(false);
          } else {
            alert(data.error || 'Google login failed');
          }
        } catch (err) {
          console.error('Google login error:', err);
          alert('Google login failed. Please try again.');
        }
      }
    };
    
    window.addEventListener('message', messageHandler);
  }

  // if (showPage) {
  //   return <QPage onClose={() => setShowPage(false)} />;
  // }

  return (
    <div className={`${styles.root} ${styles.qChat}`}>

      {showHelpTab && <HelpTab onClose={() => setShowHelpTab(false)} />}
      
      {/* Admin Panel */}
      {showAdminPanel && <AdminPanel onClose={() => setShowAdminPanel(false)} />}
      
      {/* Teacher Panel */}
      {showTeacherPanel && <TeacherPanel onClose={() => setShowTeacherPanel(false)} />}
      {/* History panel is controlled (open/close) by this component */}

      <ChatHistoryPanel
        open={historyOpen}
        onClose={() => setHistoryOpen(false)}
        history={history}
        onLoad={handleLoadConversation}
      />
      <LoginDropdown
        open={loginOpen}
        onClose={() => setLoginOpen(false)}
        currentUser={currentUser}
        onLogin={handleLogin}
        onRegister={handleRegister}
        onMicrosoftLogin={handleMicrosoftLogin}
        onGoogleLogin={handleGoogleLogin}
        onLogout={handleLogout}
      />
      <header className={styles.headerBar}>
        <div className={styles.headerActions}>
          <button
            className={styles.historyButton}
            onClick={() => setHistoryOpen(v => !v)}
          >
            History
          </button>
          <button
            className={styles.helpButton}
            onClick={() => setShowHelpTab(!showHelpTab)}
          >
            Help
          </button>
          
          <button
            className={styles.loginButton}
            onClick={() => setLoginOpen(v => !v)}
          >
            {currentUser ? `👤 ${currentUser}` : '👤 Login'}
          </button>
          
          {currentUser && isAdmin && (
            <button
              className={styles.loginButton}
              onClick={() => setShowAdminPanel(true)}
            >
              Admin Panel
            </button>
          )}
          
          {currentUser && isTeacher && (
            <button
              className={styles.loginButton}
              onClick={() => setShowTeacherPanel(true)}
            >
              Tools
            </button>
          )}
        </div>
        <div className={styles.titleLogo}>
          <img className={styles.bobcatImage} src={bobcatImage} alt="Bobcat mascot" />
          <div className={styles.brandTitle}>QCHAT</div>
          <img className={styles.tmImg} src={TMImage} alt="Trademark symbol" />
        </div>
      </header>

      <div className={styles.chatMain}>
        <div className={styles.tipsRow}>
          <HelpBubbles open={showTips} />
          <button
            className={styles.hideTipsButton}
            onClick={() => setShowTips(t => !t)}
          >
            {showTips ? 'Hide Tips' : 'Show Tips'}
          </button>
        </div>

        <div className={styles.messagesScroll}>
          {msgs.map((m, i) => (
            <div
              key={i}
              className={
                m.role === 'assistant' ? styles.messageAssistant : styles.messageUser
              }
            >
              <strong>{m.role === 'assistant' ? 'qChat' : 'You'}: </strong>
              <span dangerouslySetInnerHTML={{ __html: linkifyText(m.text) }} />
            </div>
          ))}

          {isLoading && (
            <div className={styles.loadingRow}>
              <strong>qChat:</strong>
              <span className={styles.spinner} />
              <span>Thinking…</span>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>
        <form className={styles.composer} onSubmit={onSend}>
          <input
            className={styles.textInput}
            value={input}
            onChange={e => setInput(e.target.value)}
            placeholder={isLoading ? "QChat is thinking..." : "Type a question…"}
            disabled={isLoading}
            enterKeyHint="send"
            autoComplete="off"
          />
          <button
            className={styles.sendButton}
            type="submit"
            disabled={isLoading}
          >
            Send
          </button>
        </form>
      </div>

      <footer className={styles.pageFooter}>
        Created By: Sam Woodburn, Thomas Rua, Tuana Turhan&emsp;&emsp;&emsp;&emsp; Advisors: Chetan Jaiswal & Lynn Byers
      </footer>

    </div>
  );
}