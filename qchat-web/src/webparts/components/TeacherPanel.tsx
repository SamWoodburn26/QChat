import * as React from 'react';
import styles from './TeacherPanel.module.css';

type Tab = 'email' | 'blackboard' | 'canvas';
const configuredServerUrl = import.meta.env.VITE_SERVER_URL || 'http://localhost:7071';
const llm_base = import.meta.env.DEV ? '' : configuredServerUrl;

export default function TeacherPanel(props: { onClose: () => void }) {
  const [activeTab, setActiveTab] = React.useState<Tab>('email');

  return (
    <div className={styles.overlay}>
      <div className={styles.panel}>
        <div className={styles.header}>
          <h2 className={styles.title}>Tools</h2>
          <button type="button" className={styles.closeButton} onClick={props.onClose} aria-label="Close">
            ×
          </button>
        </div>

        {/* Tabs Navigation */}
        <div className={styles.tabs}>
          <button
            type="button"
            className={`${styles.tab} ${activeTab === 'email' ? styles.tabActive : ''}`}
            onClick={() => setActiveTab('email')}
          >
            Email
          </button>
          <button
            type="button"
            className={`${styles.tab} ${activeTab === 'blackboard' ? styles.tabActive : ''}`}
            onClick={() => setActiveTab('blackboard')}
          >
            Blackboard
          </button>
          <button
            type="button"
            className={`${styles.tab} ${activeTab === 'canvas' ? styles.tabActive : ''}`}
            onClick={() => setActiveTab('canvas')}
          >
            Canvas
          </button>
        </div>

        {/* Tab Content */}
        <div className={styles.tabContent}>
          {activeTab === 'email' && <EmailTab />}
          {activeTab === 'blackboard' && <BlackboardTab />}
          {activeTab === 'canvas' && <CanvasTab />}
        </div>
      </div>
    </div>
  );
}

// EMAIL TAB
function EmailTab() {
  const [to, setTo] = React.useState('');
  const [subject, setSubject] = React.useState('');
  const [body, setBody] = React.useState('');
  const [copied, setCopied] = React.useState(false);
  const [sending, setSending] = React.useState(false);
  const [status, setStatus] = React.useState<string | null>(null);

  function copyEmail() {
    const emailText = `To: ${to}\nSubject: ${subject}\n\n${body}`;
    navigator.clipboard.writeText(emailText).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    });
  }

  function clearForm() {
    setTo('');
    setSubject('');
    setBody('');
    setStatus(null);
  }

  async function sendEmail() {
    setStatus(null);
    if (!to.trim() || !subject.trim() || !body.trim()) {
      setStatus('Please fill in To, Subject, and Message.');
      return;
    }

    setSending(true);
    try {
      const response = await fetch(`${llm_base}/api/send_mail`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          to,
          subject,
          body,
        }),
      });

      const data = await response.json();
      if (!response.ok || !data.success) {
        setStatus(data.error || data.details || `Email send failed (${response.status}).`);
        return;
      }

      setStatus('Email sent successfully.');
    } catch (error) {
      console.error('Send email error:', error);
      setStatus('Could not send email. Check backend and Microsoft app permissions.');
    } finally {
      setSending(false);
    }
  }

  function useTemplate(template: string) {
    switch (template) {
      case 'welcome':
        setSubject('Welcome to the Course!');
        setBody('Dear Students,\n\nWelcome to our course! I\'m excited to have you in class this semester.\n\nBest regards,\n[Your Name]');
        break;
      case 'reminder':
        setSubject('Assignment Reminder');
        setBody('Dear Students,\n\nThis is a friendly reminder that the assignment is due on [DATE].\n\nBest regards,\n[Your Name]');
        break;
      case 'announcement':
        setSubject('Class Announcement');
        setBody('Dear Students,\n\n[Your announcement here]\n\nBest regards,\n[Your Name]');
        break;
    }
  }

  return (
    <div className={styles.emailComposer}>
      <div className={styles.templates}>
        <span className={styles.templateLabel}>Quick Templates:</span>
        <button type="button" className={styles.templateButton} onClick={() => useTemplate('welcome')}>
          Welcome Email
        </button>
        <button type="button" className={styles.templateButton} onClick={() => useTemplate('reminder')}>
          Assignment Reminder
        </button>
        <button type="button" className={styles.templateButton} onClick={() => useTemplate('announcement')}>
          Announcement
        </button>
      </div>

      <div className={styles.formGroup}>
        <label className={styles.label}>To:</label>
        <input
          type="text"
          className={styles.input}
          value={to}
          onChange={(e) => setTo(e.target.value)}
          placeholder="student@example.com or class list"
        />
      </div>

      <div className={styles.formGroup}>
        <label className={styles.label}>Subject:</label>
        <input
          type="text"
          className={styles.input}
          value={subject}
          onChange={(e) => setSubject(e.target.value)}
          placeholder="Email subject"
        />
      </div>

      <div className={styles.formGroup}>
        <label className={styles.label}>Message:</label>
        <textarea
          className={styles.textarea}
          value={body}
          onChange={(e) => setBody(e.target.value)}
          placeholder="Email body"
          rows={12}
        />
      </div>

      <div className={styles.actions}>
        <button type="button" className={styles.primaryButton} onClick={sendEmail} disabled={sending}>
          {sending ? 'Sending...' : 'Send via Microsoft'}
        </button>
        <button type="button" className={styles.primaryButton} onClick={copyEmail}>
          {copied ? ' Copied!' : 'Copy to Clipboard'}
        </button>
        <button type="button" className={styles.secondaryButton} onClick={clearForm}>
          Clear
        </button>
      </div>

      {status && <div className={styles.note}>{status}</div>}

      <div className={styles.note}>
        Copy this email and paste it into your email client (Gmail, Outlook, etc.)
      </div>
    </div>
  );
}

// BLACKBOARD TAB
function BlackboardTab() {
  function openBlackboard() {
    window.open('https://login.microsoftonline.com/09409858-69fb-4de9-9879-90db22b52eaf/saml2?SAMLRequest=nZJPT%2BMwEMW%2FiuW788dNk8ZqirpbIZBAVCTsgcvKcZzibjIuHqdiv%2F2GtNXChQOXkSzPvPc8Py%2Bv3vqOHLVDY6GgcRBRokHZxsCuoE%2FVNVvQq9USZd%2Fxg1gP%2FgUe9eug0ZNxEFCcbgo6OBBWokEBstcovBLl%2Bv5O8CASB2e9VbajZI2onR%2BtflrAodeu1O5olH56vCvoi%2FcHFGH4OhgAczBSBXUn1Z%2FaStcEyvahHP3Zu2M4lbJ8oGQzZjEg%2FZT%2FItHZnYGgN8pZtK230BnQk0SUJ1G%2BmC9Ymrc1Sxqds3yRjSVqas7rOdeyndQ5JdfWKT29uaCt7FBTcrspqIxn2X4e51mTzHmmTLpP9km7T2W%2By%2Bp87MGtRDRH%2FX8KcdC3gF6CLyiPeMqiGYtnVZyKiAueBDyZPVOyPS%2Fqh4ETgK%2B2Wp%2BaUNxU1ZZtH8qKkl8XkGMDPWMTk7v7yOtrYXmBRFffQRJq8Mb%2FZaYJ3yV%2FrzfL8GOQ1fn4%2BTut%2FgE%3D&SigAlg=http%3A%2F%2Fwww.w3.org%2F2000%2F09%2Fxmldsig%23rsa-sha1&Signature=LD8xVhtabw5BiicKvG4wxQibMTeDhcM%2F66atPd4RhCQd2d4QwFZlvROblw9FEG7HtXGmHB9CYxYXcFcFBfuOTL8J7vt3IRFcVu5hE1iGn2cMjxjbCF7TAbZ6fSpH0uVd2FNek5qNz05Z1s2YVU1VZa9d3wFXoQ96BiDs5HdqRLZ%2BzzPsJtqQa0Xo46PfQ2uaMZJpRoS%2Fvl4xHKtWoL2JYnM5SVrPsqhiJTfA3P4XS0g8vml3K%2FSubN%2F%2FJNLWaYjMPa5yaF6GzntFv%2Ff3iiJvvM5o7TqN7cCmM%2BvUpRZRvElKUlzYx6yVJg4WxR%2FhucIEaD6eCVjzdA062QSRhE9q1Q%3D%3D', '_blank', 'noopener,noreferrer');
  }

  return (
    <div className={styles.quickAccess}>
      <div className={styles.hero}>
        <div className={styles.icon}>📚</div>
        <h3>Blackboard at Quinnipiac</h3>
        <p>Access your courses and manage your class content</p>
      </div>

      <button type="button" className={styles.largeButton} onClick={openBlackboard}>
        Open Blackboard
      </button>

      <div className={styles.info}>
        <h4>Quick Access to:</h4>
        <ul className={styles.linkList}>
          <li>Grade Center</li>
          <li>Course Content</li>
          <li>Discussion Boards</li>
          <li>Assignments</li>
        </ul>
      </div>
    </div>
  );
}

// CANVAS TAB
function CanvasTab() {
  function openCanvas() {
    window.open('https://quinnipiac.instructure.com/', '_blank', 'noopener,noreferrer');
  }

  return (
    <div className={styles.quickAccess}>
      <div className={styles.hero}>
        <div className={styles.icon}>📘</div>
        <h3>Canvas at Quinnipiac</h3>
        <p>Manage your courses and engage with students</p>
      </div>

      <button type="button" className={styles.largeButton} onClick={openCanvas}>
        Open Canvas
      </button>

      <div className={styles.info}>
        <h4>Quick Access to:</h4>
        <ul className={styles.linkList}>
          <li>Gradebook</li>
          <li>Course Files</li>
          <li>Discussions</li>
          <li>Assignments</li>
          <li>Announcements</li>
        </ul>
      </div>
    </div>
  );
}