// ============================================================
// cooking.js — Cozinha: comidas que curam (etapa 1.4)
//
// Receitas consomem comida crua (o recurso `food`, vindo da Fazenda)
// e produzem pratos que curam HP fora de batalha e valem ouro no
// Mercado. Melhorar a Cozinha desbloqueia pratos melhores (§2.5),
// e o goblin com especialidade `cook` aumenta o rendimento.
// ============================================================
const { BAL } = require('balance.js');

// reqKitchen = nível mínimo da Cozinha para liberar a receita
const RECIPES = [
  {
    id: 'bread', sprite: 'item_bread', reqKitchen: 1,
    cost: { food: 3 }, heal: 18, price: 12, time: 4,
  },
  {
    id: 'soup', sprite: 'item_soup', reqKitchen: 1,
    cost: { food: 5, wood: 2 }, heal: 34, price: 20, time: 6,
  },
  {
    id: 'stew', sprite: 'item_stew', reqKitchen: 2,
    cost: { food: 9, ore: 1 }, heal: 62, price: 34, time: 9,
  },
  {
    id: 'feast', sprite: 'item_feast', reqKitchen: 3,
    cost: { food: 16, gold: 10 }, heal: 120, price: 70, time: 14,
  },
];

const byId = (id) => RECIPES.find((r) => r.id === id) || null;

/** Receitas liberadas pelo nível atual da Cozinha. */
function available(kitchenLevel) {
  return RECIPES.filter((r) => r.reqKitchen <= kitchenLevel);
}

/** O melhor bônus de cozinheiro entre os goblins da vila. */
function cookBonus(village) {
  let best = 0;
  for (const g of village.goblins) {
    if (g.specialty !== 'cook') continue;
    // cozinheiro bom rende prato extra com mais frequência
    best = Math.max(best, 0.15 + g.potencialEvolucao * 0.02);
  }
  return Math.min(0.6, best);
}

/**
 * Cozinha um prato. Retorna {id, qty, healed} ou null se não deu.
 * O bônus de `cook` pode render 2 porções de uma vez.
 */
function cook(village, recipeId, rng = Math.random) {
  const r = byId(recipeId);
  if (!r) return null;
  const kitchen = village.levelOf('cozinha');
  if (kitchen < r.reqKitchen) return null;
  if (!village.canAfford(r.cost)) return null;

  village.pay(r.cost);
  let qty = 1;
  if (rng() < cookBonus(village)) qty += 1;

  village.meals[r.id] = (village.meals[r.id] || 0) + qty;
  return { id: r.id, qty };
}

/**
 * Usa um prato para curar um goblin. Retorna o HP curado, ou 0.
 * A cura extra vem da especialidade cook (§1.4).
 */
function feed(village, goblin, recipeId) {
  const r = byId(recipeId);
  if (!r || !goblin) return 0;
  if ((village.meals[r.id] || 0) <= 0) return 0;
  if (goblin.hp >= goblin.maxHp) return 0;

  const mul = 1 + (BAL.cooking?.healBonus ?? 0);
  const heal = Math.round(r.heal * mul);
  const before = goblin.hp;
  goblin.hp = Math.min(goblin.maxHp, goblin.hp + heal);
  village.meals[r.id] -= 1;
  if (village.meals[r.id] <= 0) delete village.meals[r.id];
  return goblin.hp - before;
}

/** Total de pratos guardados. */
function totalMeals(village) {
  return Object.values(village.meals || {}).reduce((a, b) => a + b, 0);
}

module.exports = { RECIPES, available, cook, feed, byId, totalMeals, cookBonus };
