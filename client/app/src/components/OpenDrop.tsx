import { useState } from 'react'
import { openDrop, ensureArt } from '../api/generation'
import { createUnit } from '../api/nakama'

const RARITIES = [
  'Common',
  'Uncommon',
  'Rare',
  'Epic',
  'Legendary',
  'Mythic',
] as const

type Props = {
  onOpened: () => void
  dropTypeId: string
  label?: string
}

export function OpenDrop({ onOpened, dropTypeId, label }: Props) {
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const displayLabel = label ?? `Open (${dropTypeId})`

  async function handleOpen() {
    setError(null)
    setLoading(true)
    try {
      const result = await openDrop(dropTypeId)
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
        {loading ? 'Opening…' : displayLabel}
      </button>
      {error && (
        <p style={{ color: '#c00', marginTop: 8, fontSize: 14 }}>{error}</p>
      )}
    </div>
  )
}

/** Unit drop type id for a given rarity. */
export function unitDropTypeId(rarity: string): string {
  const slug = rarity.toLowerCase().replace(/\s+/, '_')
  return `${slug}_unit_drop`
}

/** Item drop type id for a given rarity. */
export function itemDropTypeId(rarity: string): string {
  const slug = rarity.toLowerCase().replace(/\s+/, '_')
  return `${slug}_item_drop`
}

export { RARITIES }
