// ============================================================
// market.js — Mercado: vender e comprar (etapa 1.6)
//
// Fecha a economia da Fase 1: o jogador transforma o excedente
// (madeira, pedra, minério, comida crua e pratos) em OURO, e usa
// o ouro para comprar o que está faltando — inclusive pratos
// prontos, que funcionam como "poções" fora de batalha.
//
// Preços-base vêm do balance.json (`market.prices`); os pratos
// usam o `price` da própria receita (cooking.js). Melhorar o
// Mercado aproxima os dois lados: paga mais na venda e cobra
// menos na compra (§2.5 — melhorar estrutura melhora o serviço).
//
// Equipamentos (inventory.js) são negociados aqui também — mas
// só com o Armazém construído, e a compra respeita a capacidade
// de espaços dele.
// ============================================================
const { BAL } = require('balance.js');
const { RECIPES, byId } = require('cooking.js');
const inv = require('inventory.js');

// Recursos negociáveis, na ordem em que aparecem na tela.
const TRADE_RES = ['wood', 'stone', 'ore', 'food'];

// Valores de referência caso o balance.json não traga `market`.
const DEFAULT_PRICES = { wood: 2, stone: 3, ore: 7, food: 4 };

function cfg() {
  return {
    sellMul: BAL.market?.sellMul ?? 0.75,
    buyMul: BAL.market?.buyMul ?? 1.6,
    levelBonus: BAL.market?.levelBonus ?? 0.06,
    prices: { ...DEFAULT_PRICES, ...(BAL.market?.prices || {}) },
  };
}

/** Nível do Mercado construído (0 = não existe). */
function level(village) { return village.levelOf('mercado'); }

/** Valor-base de uma unidade do item (antes das margens). */
function baseValue(kind, key) {
  if (kind === 'gear') return inv.priceOf(key);
  if (kind === 'meal') return byId(key)?.price ?? 10;
  return cfg().prices[key] ?? 1;
}

/** Quanto o mercado PAGA por unidade. */
function sellPrice(village, kind, key) {
  const c = cfg();
  const bonus = 1 + c.levelBonus * Math.max(0, level(village) - 1);
  return Math.max(1, Math.round(baseValue(kind, key) * c.sellMul * bonus));
}

/** Quanto o mercado COBRA por unidade. */
function buyPrice(village, kind, key) {
  if (kind === 'gear') return baseValue(kind, key);
  const c = cfg();
  const desconto = 1 - c.levelBonus * Math.max(0, level(village) - 1);
  const min = sellPrice(village, kind, key) + 1;   // nunca vira moto-perpétuo
  return Math.max(min, Math.round(baseValue(kind, key) * c.buyMul * Math.max(0.4, desconto)));
}

/** Quanto o jogador tem desse item. */
function have(village, kind, key) {
  if (kind === 'gear') return village.items?.[key] || 0;
  return kind === 'meal' ? (village.meals?.[key] || 0) : (village.res?.[key] || 0);
}

/**
 * O que está à venda / à compra, já com preço e quantidade.
 * `side` = 'sell' | 'buy'. Equipamentos só entram com Armazém.
 */
function catalog(village, side) {
  const lv = level(village);
  const items = [
    ...TRADE_RES.map((k) => ({ kind: 'res', key: k, sprite: 'res_' + k })),
    ...RECIPES.map((r) => ({ kind: 'meal', key: r.id, sprite: r.sprite })),
    // equipamentos do Armazém (compra e revenda) — precisa do Armazém
    ...(village.has('armazem')
      ? inv.ITEMS.map((i) => ({ kind: 'gear', key: i.id, sprite: i.icon }))
      : []),
  ];
  return items
    // pratos só entram na prateleira conforme o mercado cresce
    .filter((it) => (side === 'sell' || it.kind !== 'meal' || byId(it.key).reqKitchen <= lv))
    .map((it) => ({
      ...it,
      price: side === 'sell'
        ? sellPrice(village, it.kind, it.key)
        : buyPrice(village, it.kind, it.key),
      have: have(village, it.kind, it.key),
    }));
}

/** Máximo que dá para vender (o que o jogador tem). */
function maxSell(village, kind, key) { return have(village, kind, key); }

/** Máximo que dá para comprar com o ouro atual. */
function maxBuy(village, kind, key) {
  const p = buyPrice(village, kind, key);
  if (kind === 'gear') {
    // limitado pelo ouro E pelos espaços livres do Armazém
    const livre = village.itemCapacity() - village.itemsCount();
    return Math.max(0, Math.min(Math.floor((village.res.gold || 0) / p), livre));
  }
  return Math.max(0, Math.floor((village.res.gold || 0) / p));
}

function addItem(village, kind, key, qty) {
  if (kind === 'meal') village.meals[key] = (village.meals[key] || 0) + qty;
  else if (kind === 'gear') village.addItem(key, qty);
  else village.add(key, qty);
}

function takeItem(village, kind, key, qty) {
  if (kind === 'meal') {
    village.meals[key] -= qty;
    if (village.meals[key] <= 0) delete village.meals[key];
  } else if (kind === 'gear') {
    village.takeItem(key, qty);
  } else {
    village.res[key] -= qty;
  }
}

/**
 * Vende `qty` unidades. Retorna o ouro recebido, ou 0 se não deu.
 */
function sell(village, kind, key, qty) {
  const n = Math.floor(qty);
  if (!village.has('mercado') || n <= 0) return 0;
  if (have(village, kind, key) < n) return 0;
  const gold = sellPrice(village, kind, key) * n;
  takeItem(village, kind, key, n);
  village.add('gold', gold);
  return gold;
}

/**
 * Compra `qty` unidades. Retorna o ouro gasto, ou 0 se não deu.
 */
function buy(village, kind, key, qty) {
  const n = Math.floor(qty);
  if (!village.has('mercado') || n <= 0) return 0;
  if (kind === 'meal' && byId(key)?.reqKitchen > level(village)) return 0;
  if (kind === 'gear') {                      // equipamento: precisa de Armazém
    if (!village.has('armazem')) return 0;
    if (village.itemsCount() + n > village.itemCapacity()) return 0;
  }
  const cost = buyPrice(village, kind, key) * n;
  if ((village.res.gold || 0) < cost) return 0;
  village.res.gold -= cost;
  addItem(village, kind, key, n);
  return cost;
}

module.exports = {
  TRADE_RES, catalog, sellPrice, buyPrice, sell, buy,
  maxSell, maxBuy, have, level,
};
