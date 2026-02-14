import type { UnitInstance } from '../types'
import { getArtUrl, getBorderUrl } from '../api/generation'

type Props = { unit: UnitInstance; size?: number }

const STAT_KEYS = [
  'hp_max',
  'stamina_max',
  'mana_max',
  'melee',
  'ranged',
  'magic',
  'maneuver',
] as const

export function Card({ unit, size = 144 }: Props) {
  const artUrl = getArtUrl(unit.templateId)
  const borderUrl = getBorderUrl(unit.rarity)
  const inner = Math.round((size * 32) / 36)

  return (
    <div
      style={{
        width: size,
        background: '#222',
        borderRadius: 6,
        overflow: 'hidden',
        boxShadow: '0 2px 8px rgba(0,0,0,0.2)',
      }}
    >
      <div
        style={{
          position: 'relative',
          width: size,
          height: size,
          backgroundImage: `url(${borderUrl})`,
          backgroundSize: '100% 100%',
          backgroundRepeat: 'no-repeat',
        }}
      >
        <div
          style={{
            position: 'absolute',
            left: '50%',
            top: '50%',
            transform: 'translate(-50%, -50%)',
            width: inner,
            height: inner,
            backgroundImage: `url(${artUrl})`,
            backgroundSize: 'cover',
            backgroundPosition: 'center',
          }}
        />
      </div>
      <div style={{ padding: 8 }}>
        <div style={{ fontWeight: 600, marginBottom: 4 }}>{unit.templateId}</div>
        <div style={{ fontSize: 12, color: '#aaa', marginBottom: 6 }}>
          {unit.rarity}
        </div>
        <div style={{ fontSize: 11, color: '#888', display: 'flex', flexWrap: 'wrap', gap: '4px 8px' }}>
          {STAT_KEYS.map((key) => (
            <span key={key}>
              {key}: {unit.stats[key]}
            </span>
          ))}
        </div>
      </div>
    </div>
  )
}
