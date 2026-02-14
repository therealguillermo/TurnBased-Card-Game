import { useState, useEffect, useCallback } from 'react'
import { getState } from '../api/nakama'
import type { GameState } from '../types'
import { Card } from './Card'
import { OpenDrop } from './OpenDrop'

type Props = { onLogout: () => void }

export function Inventory({ onLogout }: Props) {
  const [state, setState] = useState<GameState | null>(null)
  const [error, setError] = useState<string | null>(null)

  const refresh = useCallback(async () => {
    setError(null)
    try {
      const s = await getState()
      setState(s)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load state')
    }
  }, [])

  useEffect(() => {
    refresh()
  }, [refresh])

  if (error && !state) {
    return (
      <div style={{ padding: 24 }}>
        <p style={{ color: '#c00' }}>{error}</p>
        <button onClick={refresh}>Retry</button>
        <button onClick={onLogout} style={{ marginLeft: 8 }}>Log out</button>
      </div>
    )
  }

  if (!state) {
    return <div style={{ padding: 24 }}>Loading…</div>
  }

  const { profile, wallet, inventorySummary, units } = state

  return (
    <div style={{ padding: 24, maxWidth: 900, margin: '0 auto' }}>
      <header style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 24 }}>
        <h1 style={{ margin: 0 }}>Inventory</h1>
        <div>
          <span style={{ marginRight: 16 }}>{profile.username}</span>
          <span style={{ marginRight: 16 }}>Gold: {wallet.gold}</span>
          <button onClick={onLogout}>Log out</button>
        </div>
      </header>

      <section style={{ marginBottom: 24 }}>
        <h2 style={{ marginTop: 0 }}>Summary</h2>
        <p>Units: {inventorySummary.unitsCount} · Items: {inventorySummary.itemsCount}</p>
      </section>

      <section style={{ marginBottom: 24 }}>
        <h2 style={{ marginTop: 0 }}>Open drop</h2>
        <OpenDrop onOpened={refresh} />
      </section>

      <section>
        <h2 style={{ marginTop: 0 }}>Units</h2>
        {units.length === 0 ? (
          <p style={{ color: '#666' }}>No units yet. Open a drop to get one.</p>
        ) : (
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 16 }}>
            {units.map((u) => (
              <Card key={u.instanceId} unit={u} />
            ))}
          </div>
        )}
      </section>
    </div>
  )
}
