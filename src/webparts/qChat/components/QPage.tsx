import * as React from 'react';
import styles from './QPage.module.scss';

export default function QPage(props: { onClose?: () => void }) {
  return (
    <div className={styles.page}>
      <header className={styles.header}>
        <h1>qChat — Student Help Center</h1>
        <p className={styles.lead}>Find quick answers, resources, and contact points for university services.</p>
        {props.onClose && (
          <button className={styles.close} onClick={props.onClose} aria-label="Close page">Close</button>
        )}
      </header>

      <main className={styles.content}>
        <section className={styles.card}>
          <h2>Academics</h2>
          <p>Registration, course planning, deadlines, and academic advising.</p>
          <a href="#" className={styles.cta}>Go to Academics</a>
        </section>

        <section className={styles.card}>
          <h2>Financial Aid</h2>
          <p>Tuition deadlines, payment plans, scholarships and grants.</p>
          <a href="#" className={styles.cta}>View Financial Aid</a>
        </section>

        <section className={styles.card}>
          <h2>Campus Life</h2>
          <p>Dining, housing, events, and student services.</p>
          <a href="#" className={styles.cta}>Explore Campus Life</a>
        </section>

        <section className={styles.cardFull}>
          <h2>Search the Knowledge Base</h2>
          <p>Type a question and qChat will suggest relevant articles and contacts.</p>
          <div className={styles.searchRow}>
            <input className={styles.searchInput} placeholder="Search help…" />
            <button className={styles.searchBtn}>Search</button>
          </div>
        </section>
      </main>

      <footer className={styles.footer}>
        <small>© {new Date().getFullYear()} Quinnipiac University — qChat</small>
      </footer>
    </div>
  );
}
