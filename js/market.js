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
// ============================================================
const { BAL } = require('balance.js');
const { RECIPES, byId } = require('cooking.js');

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
  const c = cfg();
  const desconto = 1 - c.levelBonus * Math.max(0, level(village) - 1);
  const min = sellPrice(village, kind, key) + 1;   // nunca vira moto-perpétuo
  return Math.max(min, Math.round(baseValue(kind, key) * c.buyMul * Math.max(0.4, desconto)));
}

/** Quanto o jogador tem desse item. */
function have(village, kind, key) {
  return kind === 'meal' ? (village.meals?.[key] || 0) : (village.res?.[key] || 0);
}

/**
 * O que está à venda / à compra, já com preço e quantidade.
 * `side` = 'sell' | 'buy'.
 */
function catalog(village, side) {
  const lv = level(village);
  const items = [
    ...TRADE_RES.map((k) => ({ kind: 'res', key: k, sprite: 'res_' + k })),
    ...RECIPES.map((r) => ({ kind: 'meal', key: r.id, sprite: r.sprite })),
  ];
  return items
    // pratos só entram na prateleira de COMPRA conforme o mercado cresce
    .filter((it) => (side === 'sell' || it.kind === 'res' || byId(it.key).reqKitchen <= lv))
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
  return Math.max(0, Math.floor((village.res.gold || 0) / p));
}

function addItem(village, kind, key, qty) {
  if (kind === 'meal') village.meals[key] = (village.meals[key] || 0) + qty;
  else village.add(key, qty);
}

function takeItem(village, kind, key, qty) {
  if (kind === 'meal') {
    village.meals[key] -= qty;
    if (village.meals[key] <= 0) delete village.meals[key];
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
