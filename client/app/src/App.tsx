import { useState, useCallback } from 'react'
import { getSession, clearSession } from './api/nakama'
import { Login } from './components/Login'
import { Inventory } from './components/Inventory'

export default function App() {
  const [session, setSessionState] = useState(getSession)

  const onLogin = useCallback(() => {
    setSessionState(getSession())
  }, [])

  const onLogout = useCallback(() => {
    clearSession()
    setSessionState(null)
  }, [])

  if (!session) {
    return <Login onSuccess={onLogin} />
  }

  return <Inventory onLogout={onLogout} />
}
