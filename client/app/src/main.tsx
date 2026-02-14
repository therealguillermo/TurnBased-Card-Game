import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { restoreSession, setSession } from './api/nakama'
import App from './App'
import './index.css'

// Restore session on load so App can show login vs inventory
const saved = restoreSession()
if (saved) setSession(saved)

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <App />
  </StrictMode>
)
