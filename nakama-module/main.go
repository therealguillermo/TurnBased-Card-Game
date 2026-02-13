package main

import (
	"context"
	"crypto/rand"
	"database/sql"
	"encoding/hex"
	"encoding/json"
	"errors"
	"fmt"
	"time"

	"github.com/heroiclabs/nakama-common/runtime"
)

// --- JSON types (match contract) ---

type Profile struct {
	Username  string `json:"username"`
	CreatedAt string `json:"createdAt"`
}

type Wallet struct {
	Gold float64 `json:"gold"`
}

type StatsMap map[string]int64

type ItemInstance struct {
	InstanceId string            `json:"instanceId"`
	TemplateId string            `json:"templateId"`
	Rarity     string            `json:"rarity"`
	Slot       string            `json:"slot"`
	Bonuses    map[string]int64   `json:"bonuses"`
	Passive    string            `json:"passive,omitempty"`
	CreatedAt  string            `json:"createdAt"`
}

type UnitInstance struct {
	InstanceId string            `json:"instanceId"`
	TemplateId string            `json:"templateId"`
	Rarity     string            `json:"rarity"`
	Stats      StatsMap          `json:"stats"`
	Equipment  map[string]string  `json:"equipment"` // weapon, armor, relic -> itemInstanceId or ""
}

type Inventory struct {
	Items map[string]*ItemInstance `json:"items"`
	Units map[string]*UnitInstance `json:"units"`
}

func initInventory() *Inventory {
	return &Inventory{
		Items: make(map[string]*ItemInstance),
		Units: make(map[string]*UnitInstance),
	}
}

// --- Error codes (returned to client) ---

const (
	CodeBadRequest    = 3
	CodeNotFound     = 5
	CodePermission   = 7
	CodeInvalidArg   = 3
)

func errResp(code int, msg string) (string, error) {
	return "", runtime.NewError(msg, code)
}

// --- Helpers ---

func generateInstanceId() string {
	b := make([]byte, 8)
	rand.Read(b)
	return hex.EncodeToString(b) + "-" + fmt.Sprintf("%d", time.Now().UnixNano())
}

func mustGetUserId(ctx context.Context) (string, error) {
	uid, ok := ctx.Value(runtime.RUNTIME_CTX_USER_ID).(string)
	if !ok || uid == "" {
		return "", errResp(CodePermission, "user_id_required")
	}
	return uid, nil
}

func readStorage(ctx context.Context, nk runtime.NakamaModule, userID, collection, key string) (string, error) {
	reads := []*runtime.StorageRead{
		{
			Collection: collection,
			Key:       key,
			UserID:    userID,
		},
	}
	objects, err := nk.StorageRead(ctx, reads)
	if err != nil {
		return "", err
	}
	if len(objects) == 0 {
		return "", nil
	}
	return objects[0].Value, nil
}

func writeStorage(ctx context.Context, nk runtime.NakamaModule, userID, collection, key, value string) error {
	writes := []*runtime.StorageWrite{
		{
			Collection:      collection,
			Key:             key,
			UserID:          userID,
			Value:           value,
			Version:         "*",
			PermissionRead:  runtime.STORAGE_PERMISSION_NO_READ,
			PermissionWrite: runtime.STORAGE_PERMISSION_NO_WRITE,
		},
	}
	_, err := nk.StorageWrite(ctx, writes)
	return err
}

func ensureProfileAndWallet(ctx context.Context, nk runtime.NakamaModule, userID, username string) (*Profile, *Wallet, *Inventory, error) {
	profileJSON, _ := readStorage(ctx, nk, userID, CollectionProfile, StorageKeyProfile)
	walletJSON, _ := readStorage(ctx, nk, userID, CollectionWallet, StorageKeyWallet)
	inventoryJSON, _ := readStorage(ctx, nk, userID, CollectionInventory, StorageKeyInventory)

	var profile Profile
	if profileJSON == "" {
		profile = Profile{Username: username, CreatedAt: time.Now().UTC().Format(time.RFC3339)}
		if profile.Username == "" {
			if len(userID) > 8 {
				profile.Username = userID[:8]
			} else {
				profile.Username = userID
			}
		}
		raw, _ := json.Marshal(profile)
		if err := writeStorage(ctx, nk, userID, CollectionProfile, StorageKeyProfile, string(raw)); err != nil {
			return nil, nil, nil, err
		}
	} else {
		if err := json.Unmarshal([]byte(profileJSON), &profile); err != nil {
			return nil, nil, nil, err
		}
	}

	var wallet Wallet
	if walletJSON == "" {
		wallet = Wallet{Gold: 0}
		raw, _ := json.Marshal(wallet)
		if err := writeStorage(ctx, nk, userID, CollectionWallet, StorageKeyWallet, string(raw)); err != nil {
			return nil, nil, nil, err
		}
	} else {
		if err := json.Unmarshal([]byte(walletJSON), &wallet); err != nil {
			return nil, nil, nil, err
		}
	}

	inv := initInventory()
	if inventoryJSON != "" {
		if err := json.Unmarshal([]byte(inventoryJSON), inv); err != nil {
			return nil, nil, nil, err
		}
		if inv.Items == nil {
			inv.Items = make(map[string]*ItemInstance)
		}
		if inv.Units == nil {
			inv.Units = make(map[string]*UnitInstance)
		}
	}
	return &profile, &wallet, inv, nil
}

// --- Validation ---

func validateUnitStats(stats map[string]int64) error {
	if len(stats) != 7 {
		return errors.New("stats must contain exactly the 7 allowed keys")
	}
	for k, v := range stats {
		if !isAllowedStat(k) {
			return fmt.Errorf("invalid stat key: %s", k)
		}
		_ = v
	}
	for _, k := range AllowedStats {
		if _, ok := stats[k]; !ok {
			return fmt.Errorf("missing required stat: %s", k)
		}
	}
	return nil
}

func validateBonuses(bonuses map[string]int64) error {
	for k := range bonuses {
		if !isAllowedStat(k) {
			return fmt.Errorf("invalid bonus key: %s", k)
		}
	}
	return nil
}

// --- RPC: rpc_get_state ---

func rpcGetState(ctx context.Context, logger runtime.Logger, db *sql.DB, nk runtime.NakamaModule, payload string) (string, error) {
	userID, err := mustGetUserId(ctx)
	if err != nil {
		return errResp(CodePermission, "user_id_required")
	}
	username, _ := ctx.Value(runtime.RUNTIME_CTX_USERNAME).(string)
	profile, wallet, inv, err := ensureProfileAndWallet(ctx, nk, userID, username)
	if err != nil {
		logger.Error("ensureProfileAndWallet: %v", err)
		return errResp(CodeBadRequest, "failed_to_load_state")
	}

	unitsList := make([]*UnitInstance, 0, len(inv.Units))
	for _, u := range inv.Units {
		unitsList = append(unitsList, u)
	}

	out := map[string]interface{}{
		"profile":   profile,
		"wallet":    wallet,
		"inventorySummary": map[string]interface{}{
			"itemsCount": len(inv.Items),
			"unitsCount": len(inv.Units),
		},
		"units": unitsList,
	}
	raw, _ := json.Marshal(out)
	return string(raw), nil
}

// --- RPC: rpc_create_unit ---

type CreateUnitPayload struct {
	TemplateId string            `json:"templateId"`
	Rarity    string            `json:"rarity"`
	Stats     map[string]int64   `json:"stats"`
}

func rpcCreateUnit(ctx context.Context, logger runtime.Logger, db *sql.DB, nk runtime.NakamaModule, payload string) (string, error) {
	userID, err := mustGetUserId(ctx)
	if err != nil {
		return errResp(CodePermission, "user_id_required")
	}
	if payload == "" {
		return errResp(CodeInvalidArg, "missing_payload")
	}
	var in CreateUnitPayload
	if err := json.Unmarshal([]byte(payload), &in); err != nil {
		return errResp(CodeInvalidArg, "invalid_json")
	}
	if in.TemplateId == "" {
		return errResp(CodeInvalidArg, "missing_templateId")
	}
	if !isAllowedRarity(in.Rarity) {
		return errResp(CodeInvalidArg, "invalid_rarity")
	}
	if err := validateUnitStats(in.Stats); err != nil {
		return errResp(CodeInvalidArg, err.Error())
	}

	_, _, inv, err := ensureProfileAndWallet(ctx, nk, userID, "")
	if err != nil {
		return errResp(CodeBadRequest, "failed_to_load_inventory")
	}

	instanceId := generateInstanceId()
	unit := &UnitInstance{
		InstanceId: instanceId,
		TemplateId: in.TemplateId,
		Rarity:     in.Rarity,
		Stats:      in.Stats,
		Equipment:  map[string]string{"weapon": "", "armor": "", "relic": ""},
	}
	inv.Units[instanceId] = unit

	invRaw, _ := json.Marshal(inv)
	if err := writeStorage(ctx, nk, userID, CollectionInventory, StorageKeyInventory, string(invRaw)); err != nil {
		return errResp(CodeBadRequest, "failed_to_save_unit")
	}

	out := map[string]interface{}{"unit": unit}
	raw, _ := json.Marshal(out)
	return string(raw), nil
}

// --- RPC: rpc_grant_item (admin only) ---

type GrantItemPayload struct {
	AdminSecret string            `json:"adminSecret"`
	TemplateId  string            `json:"templateId"`
	Rarity      string            `json:"rarity"`
	Slot        string            `json:"slot"`
	Bonuses     map[string]int64   `json:"bonuses"`
	Passive     string            `json:"passive,omitempty"`
	TargetUserId string           `json:"targetUserId,omitempty"`
}

func rpcGrantItem(ctx context.Context, logger runtime.Logger, db *sql.DB, nk runtime.NakamaModule, payload string) (string, error) {
	if payload == "" {
		return errResp(CodeInvalidArg, "missing_payload")
	}
	var in GrantItemPayload
	if err := json.Unmarshal([]byte(payload), &in); err != nil {
		return errResp(CodeInvalidArg, "invalid_json")
	}
	env, _ := ctx.Value(runtime.RUNTIME_CTX_ENV).(map[string]string)
	secret := ""
	if env != nil {
		secret = env["ADMIN_SECRET"]
	}
	if secret == "" || in.AdminSecret != secret {
		return errResp(CodePermission, "admin_only")
	}
	targetUserID := in.TargetUserId
	if targetUserID == "" {
		var err error
		targetUserID, err = mustGetUserId(ctx)
		if err != nil {
			return errResp(CodeInvalidArg, "targetUserId_required_when_not_authenticated")
		}
	}
	if in.TemplateId == "" || !isAllowedRarity(in.Rarity) || !isAllowedItemSlot(in.Slot) {
		return errResp(CodeInvalidArg, "missing_or_invalid_templateId_rarity_or_slot")
	}
	if err := validateBonuses(in.Bonuses); err != nil {
		return errResp(CodeInvalidArg, err.Error())
	}

	_, _, inv, err := ensureProfileAndWallet(ctx, nk, targetUserID, "")
	if err != nil {
		return errResp(CodeBadRequest, "failed_to_load_inventory")
	}

	instanceId := generateInstanceId()
	item := &ItemInstance{
		InstanceId: instanceId,
		TemplateId: in.TemplateId,
		Rarity:     in.Rarity,
		Slot:       in.Slot,
		Bonuses:    in.Bonuses,
		Passive:    in.Passive,
		CreatedAt:  time.Now().UTC().Format(time.RFC3339),
	}
	if item.Bonuses == nil {
		item.Bonuses = make(map[string]int64)
	}
	inv.Items[instanceId] = item

	invRaw, _ := json.Marshal(inv)
	if err := writeStorage(ctx, nk, targetUserID, CollectionInventory, StorageKeyInventory, string(invRaw)); err != nil {
		return errResp(CodeBadRequest, "failed_to_save_item")
	}

	out := map[string]interface{}{"item": item}
	raw, _ := json.Marshal(out)
	return string(raw), nil
}

// --- RPC: rpc_equip_item ---

type EquipItemPayload struct {
	UnitInstanceId  string `json:"unitInstanceId"`
	SlotName        string `json:"slotName"`   // weapon | armor | relic
	ItemInstanceId  *string `json:"itemInstanceId"` // null = unequip
}

func rpcEquipItem(ctx context.Context, logger runtime.Logger, db *sql.DB, nk runtime.NakamaModule, payload string) (string, error) {
	userID, err := mustGetUserId(ctx)
	if err != nil {
		return errResp(CodePermission, "user_id_required")
	}
	if payload == "" {
		return errResp(CodeInvalidArg, "missing_payload")
	}
	var in EquipItemPayload
	if err := json.Unmarshal([]byte(payload), &in); err != nil {
		return errResp(CodeInvalidArg, "invalid_json")
	}
	if in.UnitInstanceId == "" || in.SlotName == "" {
		return errResp(CodeInvalidArg, "missing_unitInstanceId_or_slotName")
	}
	if !isAllowedEquipmentSlotName(in.SlotName) {
		return errResp(CodeInvalidArg, "slotName must be weapon, armor, or relic")
	}

	_, _, inv, err := ensureProfileAndWallet(ctx, nk, userID, "")
	if err != nil {
		return errResp(CodeBadRequest, "failed_to_load_inventory")
	}

	unit, ok := inv.Units[in.UnitInstanceId]
	if !ok {
		return errResp(CodeNotFound, "unit_not_found")
	}

	var itemInstanceId string
	if in.ItemInstanceId != nil {
		itemInstanceId = *in.ItemInstanceId
	}
	if itemInstanceId != "" {
		item, ok := inv.Items[itemInstanceId]
		if !ok {
			return errResp(CodeNotFound, "item_not_found")
		}
		// Contract: slotName is weapon|armor|relic; item.Slot is Weapon|Armor|Relic
		slotMatch := (in.SlotName == "weapon" && item.Slot == "Weapon") ||
			(in.SlotName == "armor" && item.Slot == "Armor") ||
			(in.SlotName == "relic" && item.Slot == "Relic")
		if !slotMatch {
			return errResp(CodeInvalidArg, "item_slot_mismatch")
		}
		unit.Equipment[in.SlotName] = itemInstanceId
	} else {
		unit.Equipment[in.SlotName] = ""
	}

	invRaw, _ := json.Marshal(inv)
	if err := writeStorage(ctx, nk, userID, CollectionInventory, StorageKeyInventory, string(invRaw)); err != nil {
		return errResp(CodeBadRequest, "failed_to_save_equipment")
	}

	out := map[string]interface{}{"unit": unit}
	raw, _ := json.Marshal(out)
	return string(raw), nil
}

// --- RPC: rpc_compute_final_stats ---

type ComputeFinalStatsPayload struct {
	UnitInstanceId string `json:"unitInstanceId"`
}

func rpcComputeFinalStats(ctx context.Context, logger runtime.Logger, db *sql.DB, nk runtime.NakamaModule, payload string) (string, error) {
	userID, err := mustGetUserId(ctx)
	if err != nil {
		return errResp(CodePermission, "user_id_required")
	}
	if payload == "" {
		return errResp(CodeInvalidArg, "missing_payload")
	}
	var in ComputeFinalStatsPayload
	if err := json.Unmarshal([]byte(payload), &in); err != nil {
		return errResp(CodeInvalidArg, "invalid_json")
	}
	if in.UnitInstanceId == "" {
		return errResp(CodeInvalidArg, "missing_unitInstanceId")
	}

	_, _, inv, err := ensureProfileAndWallet(ctx, nk, userID, "")
	if err != nil {
		return errResp(CodeBadRequest, "failed_to_load_inventory")
	}

	unit, ok := inv.Units[in.UnitInstanceId]
	if !ok {
		return errResp(CodeNotFound, "unit_not_found")
	}

	// base + sum of equipped item bonuses
	final := make(StatsMap)
	for _, k := range AllowedStats {
		final[k] = unit.Stats[k]
	}
	for _, itemId := range unit.Equipment {
		if itemId == "" {
			continue
		}
		item, ok := inv.Items[itemId]
		if !ok {
			continue
		}
		for k, v := range item.Bonuses {
			if isAllowedStat(k) {
				final[k] += v
			}
		}
	}

	out := map[string]interface{}{
		"unitInstanceId": in.UnitInstanceId,
		"baseStats":      unit.Stats,
		"finalStats":     final,
	}
	raw, _ := json.Marshal(out)
	return string(raw), nil
}

// --- InitModule ---

func InitModule(ctx context.Context, logger runtime.Logger, db *sql.DB, nk runtime.NakamaModule, initializer runtime.Initializer) error {
	if err := initializer.RegisterRpc("rpc_get_state", rpcGetState); err != nil {
		return err
	}
	if err := initializer.RegisterRpc("rpc_create_unit", rpcCreateUnit); err != nil {
		return err
	}
	if err := initializer.RegisterRpc("rpc_grant_item", rpcGrantItem); err != nil {
		return err
	}
	if err := initializer.RegisterRpc("rpc_equip_item", rpcEquipItem); err != nil {
		return err
	}
	if err := initializer.RegisterRpc("rpc_compute_final_stats", rpcComputeFinalStats); err != nil {
		return err
	}
	logger.Info("game module loaded")
	return nil
}
