import { useState } from 'react'
import { openDrop, ensureArt } from '../api/generation'
import { createUnit } from '../api/nakama'

type Props = { onOpened: () => void }

const DROP_TYPE = 'rare_unit_drop'

export function OpenDrop({ onOpened }: Props) {
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function handleOpen() {
    setError(null)
    setLoading(true)
    try {
      const result = await openDrop(DROP_TYPE)
      if (result.kind === 'unit' && result.stats) {
        await createUnit(result.suggestedTemplateId, result.rarity, result.stats as unknown as Record<string, number>)
        try {
          await ensureArt(result.suggestedTemplateId, result.name)
        } catch {
          // Art may already exist or generation can fail; don't block
        }
        onOpened()
      } else {
        setError('This drop type returns an item; only unit drops are supported for now.')
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Open drop failed')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div>
      <button
        onClick={handleOpen}
        disabled={loading}
        style={{
          padding: '10px 20px',
          background: '#333',
          color: '#fff',
          border: 'none',
          borderRadius: 4,
        }}
      >
        {loading ? 'Opening…' : `Open drop (${DROP_TYPE})`}
      </button>
      {error && (
        <p style={{ color: '#c00', marginTop: 8, fontSize: 14 }}>{error}</p>
      )}
    </div>
  )
}
