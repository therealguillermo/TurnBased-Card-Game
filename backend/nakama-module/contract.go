package main

// Contract constants (locked game design).

const (
	CollectionProfile  = "player/profile"
	CollectionWallet   = "player/wallet"
	CollectionInventory = "player/inventory"
	StorageKeyProfile  = "profile"
	StorageKeyWallet   = "wallet"
	StorageKeyInventory = "inventory"
)

var (
	AllowedStats = [7]string{
		"hp_max", "stamina_max", "mana_max", "melee", "ranged", "magic", "maneuver",
	}
	AllowedRarities = [6]string{
		"Common", "Uncommon", "Rare", "Epic", "Legendary", "Mythic",
	}
	AllowedSlots = [3]string{"Weapon", "Armor", "Relic"}
	EquipmentSlotKeys = [3]string{"weapon", "armor", "relic"} // slot names for equipment map
)

func isAllowedStat(s string) bool {
	for _, a := range AllowedStats {
		if a == s { return true }
	}
	return false
}

func isAllowedRarity(s string) bool {
	for _, a := range AllowedRarities {
		if a == s { return true }
	}
	return false
}

func isAllowedItemSlot(s string) bool {
	for _, a := range AllowedSlots {
		if a == s { return true }
	}
	return false
}

func isAllowedEquipmentSlotName(s string) bool {
	for _, a := range EquipmentSlotKeys {
		if a == s { return true }
	}
	return false
}
