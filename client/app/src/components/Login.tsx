import { useState, FormEvent } from 'react'
import { loginWithDevice } from '../api/nakama'

type Props = { onSuccess: () => void }

function getOrCreateDeviceId(): string {
  const key = 'device_id'
  let id = localStorage.getItem(key)
  if (!id) {
    id = `dev_${Math.random().toString(36).slice(2, 14)}`
    localStorage.setItem(key, id)
  }
  return id
}

export function Login({ onSuccess }: Props) {
  const [deviceId, setDeviceId] = useState(getOrCreateDeviceId)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  async function handleSubmit(e: FormEvent) {
    e.preventDefault()
    setError(null)
    setLoading(true)
    try {
      await loginWithDevice(deviceId.trim())
      onSuccess()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Login failed')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div style={{ padding: 24, maxWidth: 360, margin: '40px auto' }}>
      <h1 style={{ marginTop: 0 }}>Card Game</h1>
      <p style={{ color: '#666' }}>Sign in with your device ID.</p>
      <form onSubmit={handleSubmit}>
        <label style={{ display: 'block', marginBottom: 8 }}>
          Device ID
          <input
            type="text"
            value={deviceId}
            onChange={(e) => setDeviceId(e.target.value)}
            disabled={loading}
            style={{
              display: 'block',
              width: '100%',
              marginTop: 4,
              padding: 8,
              border: '1px solid #ccc',
              borderRadius: 4,
            }}
          />
        </label>
        {error && (
          <p style={{ color: '#c00', marginBottom: 12, fontSize: 14 }}>{error}</p>
        )}
        <button
          type="submit"
          disabled={loading}
          style={{
            padding: '10px 20px',
            background: '#333',
            color: '#fff',
            border: 'none',
            borderRadius: 4,
          }}
        >
          {loading ? 'Signing in…' : 'Sign in'}
        </button>
      </form>
    </div>
  )
}
