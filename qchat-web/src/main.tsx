import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import QChat from './webparts/components/QChat.tsx'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <QChat />
  </StrictMode>,
)


