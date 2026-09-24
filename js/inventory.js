// ============================================================
// inventory.js — Armazém: catálogo de itens e o inventário da
// vila (etapa "armazém & inventário", antes da Parte 2).
//
// Os EQUIPAMENTOS ainda não têm status (isso vem com as batalhas);
// por enquanto eles vivem em espaços (slots):
//   • no ARMazém: cada item ocupado ocupa 1 espaço da grade
//     (capacidade sobe com o nível do Armazém);
//   • no GOBLIN: 10 espaços de equipamento em volta do boneco
//     (capacete, peitoral, botas, calça, 2 anéis, arma primária,
//     arma secundária, runa e colar).
//
// Onde cada item fica:
//   village.items            → { espada_ferro: 2, ... } (no armazém)
//   goblin.equip             → { capacete: 'capacete_ferro', ... } (no corpo)
// ============================================================
const { BAL } = require('balance.js');

// Tipos de espaço (o item só entra no espaço do próprio tipo).
// 'anel' serve para os DOIS espaços de anel do boneco.
const SLOT_TYPES = [
  'capacete', 'peitoral', 'botas', 'calca', 'anel',
  'arma_primaria', 'arma_secundaria', 'runa', 'colar',
];

// Os 10 espaços do boneco (anel duplicado: esquerdo e direito).
const EQUIP_SLOTS = [
  'capacete', 'peitoral', 'botas', 'calca', 'anel1', 'anel2',
  'arma_primaria', 'arma_secundaria', 'runa', 'colar',
];

// Catálogo de itens (à venda no Mercado, guardados no Armazém).
// `skin` = prefixo dos sprites do goblin vestindo a peça (gear.js).
const ITEMS = [
  // conjunto AVARITIA (peças raras — as únicas com skin completa em combos)
  { id: 'capacete_avaritia', slot: 'capacete', icon: 'av_cap_icon', price: 150 },
  { id: 'peitoral_avaritia', slot: 'peitoral', icon: 'av_pei_icon', price: 120 },
  { id: 'calca_avaritia', slot: 'calca', icon: 'av_cal_icon', price: 90 },
  // conjunto de FERRO (o básico honesto)
  { id: 'capacete_ferro', slot: 'capacete', icon: 'item_capacete_ferro', price: 45 },
  { id: 'peitoral_ferro', slot: 'peitoral', icon: 'item_peitoral_ferro', price: 60, skin: 'ferro_pei' },
  { id: 'calca_ferro', slot: 'calca', icon: 'item_calca_ferro', price: 40 },
  // couro & adornos
  { id: 'botas_couro', slot: 'botas', icon: 'item_botas_couro', price: 35 },
  { id: 'anel_cobre', slot: 'anel', icon: 'item_anel_cobre', price: 50 },
  { id: 'anel_rubi', slot: 'anel', icon: 'item_anel_rubi', price: 110 },
  { id: 'colar_presas', slot: 'colar', icon: 'item_colar_presas', price: 70 },
  // armas
  { id: 'espada_ferro', slot: 'arma_primaria', icon: 'item_espada_ferro', price: 80 },
  { id: 'clava_goblin', slot: 'arma_primaria', icon: 'item_clava_goblin', price: 30 },
  { id: 'escudo_madeira', slot: 'arma_secundaria', icon: 'item_escudo_madeira', price: 55 },
  // mística
  { id: 'runa_azul', slot: 'runa', icon: 'item_runa_azul', price: 130 },
];

const byId = (id) => ITEMS.find((i) => i.id === id) || null;

/** Preço-base (balance.json `inventory.prices` pode sobrescrever). */
function priceOf(id) {
  const it = byId(id);
  return BAL.inventory?.prices?.[id] ?? it?.price ?? 10;
}

/** Tipo de espaço que um espaço do boneco aceita ('anel1' → 'anel'). */
function slotTypeOf(slotKey) {
  return slotKey === 'anel1' || slotKey === 'anel2' ? 'anel' : slotKey;
}

/** O item serve nesse espaço do boneco? */
function accepts(slotKey, item) {
  return !!item && slotTypeOf(slotKey) === item.slot;
}

/** Nome traduzido do espaço ('anel1' → "Anel I"). */
function slotName(t, slotKey) {
  return t('slot.' + slotKey);
}

/**
 * Itens de um tipo presentes no armazém (ainda não equipados).
 * Retorna [{...item, have}] na ordem do catálogo.
 */
function itemsForSlot(village, slotKey) {
  return ITEMS
    .filter((i) => accepts(slotKey, i))
    .map((i) => ({ ...i, have: village.items?.[i.id] || 0 }))
    .filter((i) => i.have > 0);
}

/**
 * Equipa um item do armazém num espaço do goblin.
 * O que estava no espaço volta para o armazém. Retorna true se deu.
 */
function equip(village, goblin, slotKey, itemId) {
  const item = byId(itemId);
  if (!item || !accepts(slotKey, item)) return false;
  if ((village.items?.[itemId] || 0) <= 0) return false;

  goblin.equip = goblin.equip || {};
  const old = goblin.equip[slotKey];
  village.takeItem(itemId, 1);
  if (old) village.addItem(old, 1);   // troca direta: antigo volta pro armazém
  goblin.equip[slotKey] = itemId;
  return true;
}

/**
 * Remove o que estiver num espaço do goblin e devolve ao armazém.
 * (Pode estourar a capacidade — só a COMPRA é limitada pelo nível.)
 */
function unequip(village, goblin, slotKey) {
  const cur = goblin.equip?.[slotKey];
  if (!cur) return null;
  delete goblin.equip[slotKey];
  village.addItem(cur, 1);
  return cur;
}

/** Quantos espaços de equipamento o goblin está usando. */
function equippedCount(goblin) {
  return Object.keys(goblin.equip || {}).length;
}

module.exports = {
  SLOT_TYPES, EQUIP_SLOTS, ITEMS,
  byId, priceOf, slotTypeOf, accepts, slotName,
  itemsForSlot, equip, unequip, equippedCount,
};
