import { Client, Session } from '@heroiclabs/nakama-js'
import type { GameState } from '../types'

const NAKAMA_URL = import.meta.env.VITE_NAKAMA_URL ?? 'http://127.0.0.1:7350'
const SERVER_KEY = import.meta.env.VITE_NAKAMA_SERVER_KEY ?? 'defaultkey'

let client: Client
let session: Session | null = null

export function getClient(): Client {
  if (!client) {
    client = new Client(SERVER_KEY, NAKAMA_URL)
  }
  return client
}

export function getSession(): Session | null {
  return session
}

export function setSession(s: Session | null): void {
  session = s
}

const SESSION_STORAGE_KEY = 'nakama_session'

export function persistSession(s: Session): void {
  const payload = {
    token: s.token,
    refresh: s.refresh_token,
    createdAt: Date.now(),
  }
  sessionStorage.setItem(SESSION_STORAGE_KEY, JSON.stringify(payload))
}

export function restoreSession(): Session | null {
  const raw = sessionStorage.getItem(SESSION_STORAGE_KEY)
  if (!raw) return null
  try {
    const payload = JSON.parse(raw) as {
      token: string
      refresh: string
      createdAt: number
    }
    const s = Session.restore(payload.token, payload.refresh)
    if (s.isexpired(Date.now() / 1000)) return null
    session = s
    return s
  } catch {
    return null
  }
}

export function clearSession(): void {
  session = null
  sessionStorage.removeItem(SESSION_STORAGE_KEY)
}

export async function loginWithDevice(deviceId: string): Promise<Session> {
  const c = getClient()
  const s = await c.authenticateDevice(deviceId, true)
  session = s
  persistSession(s)
  return s
}

export async function getState(): Promise<GameState> {
  const s = session ?? restoreSession()
  if (!s) throw new Error('Not logged in')
  const c = getClient()
  const res = await c.rpc(s, 'rpc_get_state', {})
  if (res.payload == null) throw new Error('Empty state response')
  return res.payload as GameState
}

export async function createUnit(
  templateId: string,
  rarity: string,
  stats: Record<string, number>
): Promise<{ unit: import('../types').UnitInstance }> {
  const s = session ?? restoreSession()
  if (!s) throw new Error('Not logged in')
  const c = getClient()
  const res = await c.rpc(s, 'rpc_create_unit', { templateId, rarity, stats })
  if (res.payload == null) throw new Error('Empty create unit response')
  return res.payload as { unit: import('../types').UnitInstance }
}
