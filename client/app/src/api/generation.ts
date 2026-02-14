import type { DropResult } from '../types'

const BASE = import.meta.env.VITE_GENERATION_URL ?? 'http://127.0.0.1:8000'

export function getArtUrl(templateId: string): string {
  return `${BASE}/assets/art/${templateId}.png`
}

export function getBorderUrl(rarity: string): string {
  return `${BASE}/assets/borders/${rarity}.png`
}

export async function openDrop(dropTypeId: string): Promise<DropResult> {
  const res = await fetch(`${BASE}/generate/drop`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ dropTypeId }),
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error((err as { detail?: string }).detail ?? 'Open drop failed')
  }
  return res.json() as Promise<DropResult>
}

export async function ensureArt(
  templateId: string,
  displayName?: string
): Promise<string> {
  const res = await fetch(`${BASE}/generate/${encodeURIComponent(templateId)}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(
      displayName ? { displayName, promptDescription: displayName } : {}
    ),
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error((err as { detail?: string }).detail ?? 'Generate art failed')
  }
  const data = (await res.json()) as { url: string }
  return `${BASE}${data.url}`
}
