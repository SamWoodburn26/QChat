import * as React from 'react';

export default function HelpTab(props: { onClose?: () => void }) {
  return (
    <div style={{ padding: 18 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <h2 style={{ margin: 0 }}>Help</h2>
        {props.onClose && (
          <button onClick={props.onClose} style={{ padding: '6px 10px', borderRadius: 8 }}>Close Tab</button>
        )}
      </div>

      <div style={{ marginTop: 18, padding: 12, border: '1px dashed #ccc', borderRadius: 8 }}>
        <p style={{ margin: 0, fontSize: 16 }}>Placeholder</p>
      </div>
    </div>
  );
}
