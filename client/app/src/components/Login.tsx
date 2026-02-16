import { useState, FormEvent } from 'react'
import { loginWithDevice, loginWithEmail, signUpWithEmail } from '../api/nakama'

type Props = { onSuccess: () => void }

type Mode = 'signin' | 'signup'

function getOrCreateDeviceId(): string {
  const key = 'device_id'
  let id = localStorage.getItem(key)
  if (!id) {
    id = `dev_${Math.random().toString(36).slice(2, 14)}`
    localStorage.setItem(key, id)
  }
  return id
}

const formStyle = {
  display: 'block' as const,
  width: '100%',
  marginTop: 4,
  padding: 8,
  border: '1px solid #ccc',
  borderRadius: 4,
}
const labelStyle = { display: 'block' as const, marginBottom: 8 }
const buttonStyle = {
  padding: '10px 20px',
  background: '#333',
  color: '#fff',
  border: 'none' as const,
  borderRadius: 4,
}
const secondaryButtonStyle = {
  ...buttonStyle,
  background: 'transparent',
  color: '#666',
  border: '1px solid #ccc',
  marginTop: 8,
}

export function Login({ onSuccess }: Props) {
  const [mode, setMode] = useState<Mode>('signin')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [username, setUsername] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  async function handleEmailSubmit(e: FormEvent) {
    e.preventDefault()
    setError(null)
    setLoading(true)
    try {
      if (mode === 'signup') {
        await signUpWithEmail(email.trim(), password, username.trim() || undefined)
      } else {
        await loginWithEmail(email.trim(), password)
      }
      onSuccess()
    } catch (err) {
      setError(err instanceof Error ? err.message : mode === 'signup' ? 'Sign up failed' : 'Sign in failed')
    } finally {
      setLoading(false)
    }
  }

  async function handleGuestClick() {
    setError(null)
    setLoading(true)
    try {
      await loginWithDevice(getOrCreateDeviceId())
      onSuccess()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Guest sign in failed')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div style={{ padding: 24, maxWidth: 360, margin: '40px auto' }}>
      <h1 style={{ marginTop: 0 }}>Card Game</h1>

      <form onSubmit={handleEmailSubmit}>
        <p style={{ color: '#666', marginBottom: 16 }}>
          {mode === 'signin' ? 'Sign in with your account.' : 'Create an account for cross-save.'}
        </p>
        <label style={labelStyle}>
          Email
          <input
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            disabled={loading}
            required
            style={formStyle}
            autoComplete={mode === 'signup' ? 'email' : 'email'}
          />
        </label>
        <label style={labelStyle}>
          Password
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            disabled={loading}
            required
            minLength={8}
            style={formStyle}
            autoComplete={mode === 'signup' ? 'new-password' : 'current-password'}
          />
        </label>
        {mode === 'signup' && (
          <label style={labelStyle}>
            Username <span style={{ color: '#888', fontWeight: 400 }}>(optional)</span>
            <input
              type="text"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              disabled={loading}
              style={formStyle}
              placeholder="Display name"
              autoComplete="username"
            />
          </label>
        )}
        {error && (
          <p style={{ color: '#c00', marginBottom: 12, fontSize: 14 }}>{error}</p>
        )}
        <button type="submit" disabled={loading} style={buttonStyle}>
          {loading ? 'Please wait…' : mode === 'signin' ? 'Sign in' : 'Create account'}
        </button>
        <button
          type="button"
          onClick={() => {
            setMode(mode === 'signin' ? 'signup' : 'signin')
            setError(null)
          }}
          disabled={loading}
          style={{ ...secondaryButtonStyle, marginLeft: 8 }}
        >
          {mode === 'signin' ? 'Create account' : 'Sign in instead'}
        </button>
      </form>

      <p style={{ color: '#888', marginTop: 24, marginBottom: 8 }}>Or</p>
      <button
        type="button"
        onClick={handleGuestClick}
        disabled={loading}
        style={secondaryButtonStyle}
      >
        Continue as guest
      </button>
      <p style={{ fontSize: 12, color: '#888', marginTop: 8 }}>
        Guest uses this device only; no cross-save.
      </p>
    </div>
  )
}
