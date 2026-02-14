/** Game contract types (match backend). */

export type Rarity =
  | 'Common'
  | 'Uncommon'
  | 'Rare'
  | 'Epic'
  | 'Legendary'
  | 'Mythic'

export interface Stats {
  hp_max: number
  stamina_max: number
  mana_max: number
  melee: number
  ranged: number
  magic: number
  maneuver: number
}

export interface UnitInstance {
  instanceId: string
  templateId: string
  rarity: Rarity
  stats: Stats
  equipment: {
    weapon: string
    armor: string
    relic: string
  }
}

export interface ItemInstance {
  instanceId: string
  templateId: string
  rarity: Rarity
  slot: string
  bonuses: Partial<Stats>
  passive?: string
  createdAt?: string
}

export interface Profile {
  username: string
  createdAt: string
}

export interface Wallet {
  gold: number
}

export interface GameState {
  profile: Profile
  wallet: Wallet
  inventorySummary: { itemsCount: number; unitsCount: number }
  units: UnitInstance[]
}

/** Generation service: open drop response (unit or item). */
export interface DropResult {
  kind: 'unit' | 'item'
  dropTypeId: string
  name: string
  rarity: Rarity
  suggestedTemplateId: string
  stats?: Stats
  slot?: string
  bonuses?: Partial<Stats>
  modifier?: { id: string; params?: Record<string, unknown> } | null
}
