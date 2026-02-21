import { useState, useCallback } from 'react'
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

/** Convert templateId (e.g. frostbite_warden_3d33bc) to display name (e.g. Frostbite Warden). */
function toDisplayName(templateId: string): string {
  const withoutSuffix = templateId.replace(/_[a-z0-9]{6,}$/i, '')
  const withSpaces = (withoutSuffix || templateId).replace(/_/g, ' ')
  return withSpaces
    .split(' ')
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1).toLowerCase())
    .join(' ')
}

export function Card({ unit, size = 144 }: Props) {
  const artUrl = getArtUrl(unit.templateId)
  const borderUrl = getBorderUrl(unit.rarity)
  const inner = Math.round((size * 32) / 36)
  const displayName = toDisplayName(unit.templateId)

  const [hover, setHover] = useState(false)
  const [pos, setPos] = useState({ x: 0, y: 0 })

  const onMouseEnter = useCallback(() => setHover(true), [])
  const onMouseLeave = useCallback(() => setHover(false), [])
  const onMouseMove = useCallback((e: React.MouseEvent) => {
    setPos({ x: e.clientX, y: e.clientY })
  }, [])

  return (
    <>
      <div
        className="card-image-crisp"
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
            borderRadius: 6,
            overflow: 'hidden',
          }}
          onMouseEnter={onMouseEnter}
          onMouseLeave={onMouseLeave}
          onMouseMove={onMouseMove}
        >
          <img
            src={borderUrl}
            alt=""
            style={{
              position: 'absolute',
              inset: 0,
              display: 'block',
              width: '100%',
              height: '100%',
              objectFit: 'fill',
            }}
          />
          <div
            style={{
              position: 'absolute',
              left: '50%',
              top: '50%',
              transform: 'translate(-50%, -50%)',
              width: inner,
              height: inner,
              overflow: 'hidden',
              background: '#fff',
            }}
          >
            <img
              src={artUrl}
              alt=""
              style={{
                position: 'absolute',
                inset: 0,
                display: 'block',
                width: '100%',
                height: '100%',
                objectFit: 'cover',
                objectPosition: 'center',
              }}
            />
          </div>
        </div>
        <div
          style={{
            padding: '8px 6px',
            textAlign: 'center',
            fontWeight: 600,
            fontSize: 14,
            color: '#1a1a1a',
            background: '#fff',
            borderTop: '1px solid #e0e0e0',
          }}
        >
          {displayName}
        </div>
      </div>

      {hover && (
        <div
          role="tooltip"
          style={{
            position: 'fixed',
            left: pos.x,
            top: pos.y,
            zIndex: 9999,
            pointerEvents: 'none',
            background: '#fff',
            color: '#000',
            border: '1px solid #000',
            borderRadius: 4,
            padding: '10px 12px',
            fontSize: 13,
            lineHeight: 1.5,
            boxShadow: '0 2px 8px rgba(0,0,0,0.15)',
            minWidth: 140,
          }}
        >
          <div style={{ fontWeight: 600, marginBottom: 6 }}>{displayName}</div>
          <div style={{ fontSize: 12, color: '#000' }}>{unit.rarity}</div>
          <div style={{ marginTop: 6, display: 'flex', flexDirection: 'column', gap: 2 }}>
            {STAT_KEYS.map((key) => (
              <span key={key}>
                {key.replace(/_/g, ' ')}: {unit.stats[key]}
              </span>
            ))}
          </div>
        </div>
      )}
    </>
  )
}
