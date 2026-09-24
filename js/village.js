// ============================================================
// village.js — Estado da vila: recursos, estruturas, habitação,
// XP/nível da vila e desbloqueios.
//
// Regras do planejamento implementadas aqui:
//   • 1 Casa de Goblin abriga 1 goblin POR NÍVEL dela (cap = soma dos níveis)
//   • construir/melhorar casa → abre recrutamento (escolher 1 de 3)
//   • cada estrutura exige um nível da vila (BUILDINGS[].reqLevel)
//   • melhorar estrutura é limitado pelo nível da vila (§2.5)
//   • XP da vila vem de missões e batalhas → sobe de nível → desbloqueia
// ============================================================
const { getSprite } = require('assetLoader.js');
const { BAL } = require('balance.js');
const { Goblin } = require('goblin.js');

// ---------- Catálogo de estruturas ----------
// reqLevel  = nível da vila para desbloquear (planejamento §6)
// maxCount  = quantas podem existir (casas: várias; o resto: 1)
// maxLevel  = teto de melhoria da própria estrutura
const BUILDINGS = {
  construction: { sprite: 'building_construction_1', reqLevel: 1, maxCount: 1, maxLevel: 3, cost: null },
  quest: { sprite: 'building_questboard_1', reqLevel: 1, maxCount: 1, maxLevel: 3, cost: null },
  house: {
    sprite: 'building_house_1', reqLevel: 1, maxCount: 12, maxLevel: 3,
    cost: { wood: 15, stone: 10 },
  },
  serraria: {
    sprite: 'building_serraria_1', reqLevel: 2, maxCount: 1, maxLevel: 3,
    cost: { wood: 40, stone: 20 },
  },
  fazenda: {
    sprite: 'building_fazenda_1', reqLevel: 2, maxCount: 1, maxLevel: 3,
    cost: { wood: 35, stone: 15 },
  },
  armazem: {
    sprite: 'building_armazem_1', reqLevel: 2, maxCount: 1, maxLevel: 3,
    cost: { wood: 40, stone: 30 },
  },
  cozinha: {
    sprite: 'building_cozinha_1', reqLevel: 3, maxCount: 1, maxLevel: 3,
    cost: { wood: 50, stone: 40 },
  },
  mercado: {
    sprite: 'building_mercado_1', reqLevel: 3, maxCount: 1, maxLevel: 3,
    cost: { wood: 60, stone: 30, gold: 50 },
  },
  mina: {
    sprite: 'building_mina_1', reqLevel: 4, maxCount: 1, maxLevel: 3,
    cost: { wood: 70, stone: 60 },
  },
  estabulo: {
    sprite: 'building_estabulo_1', reqLevel: 4, maxCount: 1, maxLevel: 3,
    cost: { wood: 80, stone: 40, gold: 60 },
  },
  ferraria: {
    sprite: 'building_ferraria_1', reqLevel: 5, maxCount: 1, maxLevel: 3,
    cost: { wood: 90, stone: 80, ore: 20 },
  },
  altar: {
    sprite: 'building_altar_1', reqLevel: 6, maxCount: 1, maxLevel: 3,
    cost: { stone: 120, ore: 40, gold: 100 },
  },
  bazar: {
    sprite: 'building_bazar_1', reqLevel: 6, maxCount: 1, maxLevel: 3,
    cost: { wood: 100, stone: 60, gold: 150 },
  },
  porto: {
    sprite: 'building_porto_1', reqLevel: 7, maxCount: 1, maxLevel: 3,
    cost: { wood: 150, stone: 80, gold: 120 },
  },
  quartel: {
    sprite: 'building_quartel_1', reqLevel: 8, maxCount: 1, maxLevel: 3,
    cost: { wood: 120, stone: 150, ore: 60, gold: 200 },
  },
};

// Ordem de exibição no catálogo da Casa de Construção
const BUILD_ORDER = ['house', 'serraria', 'fazenda', 'armazem', 'cozinha', 'mercado', 'mina',
  'estabulo', 'ferraria', 'altar', 'bazar', 'porto', 'quartel'];

// Posições fixas (slots) para novas casas dentro da clareira
const HOUSE_SLOTS = [
  [1000, 706], [920, 750], [1000, 750], [850, 706], [1070, 706],
  [850, 750], [1070, 750], [880, 670], [1040, 670], [960, 790],
  [880, 790], [1040, 790],
];

// Slots das demais estruturas (anel externo da clareira)
const STRUCT_SLOTS = {
  serraria: [790, 660], fazenda: [1130, 660],
  cozinha: [790, 790], mercado: [1130, 790],
  mina: [760, 726], estabulo: [1160, 726],
  ferraria: [850, 620], altar: [1070, 620],
  bazar: [850, 830], porto: [1070, 830],
  quartel: [960, 590], armazem: [960, 858],
};

class Village {
  constructor(data) {
    this.res = data?.res || { ...(BAL.startResources || { wood: 50, stone: 30, gold: 100 }) };
    for (const k of ['wood', 'stone', 'ore', 'food', 'gold']) {
      if (this.res[k] == null) this.res[k] = 0;
    }
    this.structures = data?.structures || [
      { type: 'construction', level: 1, x: 920, y: 706 },
      { type: 'quest', level: 1, x: 960, y: 630 },
      { type: 'house', level: 1, x: 1000, y: 706, slot: 0 },
    ];
    this.goblins = (data?.goblins || []).map((d) => new Goblin(d));
    if (this.goblins.length === 0) this.goblins.push(Goblin.roll(0));
    this.recruitedCount = data?.recruitedCount ?? this.goblins.length;
    this.nextSlot = data?.nextSlot ?? 1;

    // ---------- XP / nível da vila (etapa 1.8) ----------
    this.level = data?.level ?? 1;
    this.xp = data?.xp ?? 0;
    // despensa de comidas cozinhadas: { bread: 3, soup: 1, ... }
    this.meals = data?.meals || {};
    // itens de equipamento guardados no Armazém: { espada_ferro: 2, ... }
    this.items = data?.items || {};
    // migração de saves antigos: `gear` era compra única da vila inteira;
    // agora cada peça é um item do inventário, equipável por goblin.
    if (!data?.items && data?.gear) {
      for (const [k, owned] of Object.entries(data.gear)) {
        if (owned) this.items[k] = (this.items[k] || 0) + 1;
      }
    }
  }

  // ---------- Consultas ----------
  get houses() { return this.structures.filter((s) => s.type === 'house'); }
  get capacity() { return this.houses.reduce((a, h) => a + h.level, 0); }

  /** Estruturas que não são casas (uma de cada, no máximo). */
  get facilities() {
    return this.structures.filter((s) => s.type !== 'house');
  }

  /** Retorna a estrutura desse tipo (ou null). Casas: use `houses`. */
  get(type) { return this.structures.find((s) => s.type === type) || null; }

  /** Nível de uma estrutura construída; 0 se ainda não existe. */
  levelOf(type) { return this.get(type)?.level || 0; }

  has(type) { return this.levelOf(type) > 0; }

  countOf(type) { return this.structures.filter((s) => s.type === type).length; }

  // ---------- XP e nível da vila ----------
  /** XP total para ir do nível N ao N+1 (planejamento §8: 100 × N^1.6). */
  xpNext() {
    const base = BAL.village?.xpBase ?? 100;
    const exp = BAL.village?.xpExp ?? 1.6;
    return Math.round(base * Math.pow(this.level, exp));
  }

  /** Dá XP à vila. Retorna quantos níveis subiu. */
  gainXp(amount) {
    const max = BAL.village?.maxLevel ?? 20;
    this.xp += Math.max(0, Math.round(amount));
    let ups = 0;
    while (this.level < max && this.xp >= this.xpNext()) {
      this.xp -= this.xpNext();
      this.level += 1;
      ups += 1;
    }
    if (this.level >= max) this.xp = Math.min(this.xp, this.xpNext());
    return ups;
  }

  /** Estruturas que este nível da vila acabou de liberar. */
  unlockedAt(level) {
    return BUILD_ORDER.filter((id) => BUILDINGS[id].reqLevel === level);
  }

  // ---------- Recursos ----------
  canAfford(cost) {
    return Object.entries(cost || {}).every(([k, v]) => (this.res[k] || 0) >= v);
  }

  pay(cost) {
    for (const [k, v] of Object.entries(cost || {})) this.res[k] -= v;
  }

  add(resource, amount) {
    this.res[resource] = (this.res[resource] || 0) + amount;
  }

  // ---------- Itens de equipamento (Armazém) ----------
  /** Espaços de item disponíveis (8 por nível do Armazém; 0 sem armazém). */
  itemCapacity() {
    return this.has('armazem') ? 8 * (1 + this.levelOf('armazem')) : 0;
  }

  /** Quantos itens estão guardados agora. */
  itemsCount() {
    return Object.values(this.items || {}).reduce((a, b) => a + b, 0);
  }

  addItem(itemId, n = 1) {
    this.items[itemId] = (this.items[itemId] || 0) + n;
  }

  takeItem(itemId, n = 1) {
    const left = (this.items[itemId] || 0) - n;
    if (left > 0) this.items[itemId] = left;
    else delete this.items[itemId];
  }

  costText(cost, t) {
    return Object.entries(cost || {}).map(([k, v]) => `${v} ${t(`res.${k}`)}`).join(' + ');
  }

  // ---------- Custos ----------
  /** Custo para construir uma estrutura nova desse tipo. */
  buildCost(type) {
    const def = BUILDINGS[type];
    if (!def?.cost) return null;
    if (type === 'house') return BAL.house?.buildCost || def.cost;
    // custo do balance.json vence o padrão, se existir
    return BAL.buildings?.[type]?.cost || def.cost;
  }

  /** Custo para melhorar a estrutura (cresce por nível). */
  upgradeCost(structure) {
    const type = structure.type;
    if (type === 'house') {
      const base = BAL.house?.upgradeBase || { wood: 25, stone: 15 };
      const mul = Math.pow(BAL.house?.upgradeMul ?? 1.6, structure.level - 1);
      const out = {};
      for (const [k, v] of Object.entries(base)) out[k] = Math.round(v * mul);
      return out;
    }
    const base = this.buildCost(type) || { wood: 40, stone: 20 };
    const mul = Math.pow(BAL.buildings?.upgradeMul ?? 1.8, structure.level - 1) * 0.8;
    const out = {};
    for (const [k, v] of Object.entries(base)) out[k] = Math.round(v * mul);
    return out;
  }

  /** Teto de melhoria: limitado pelo nível da vila (§2.5). */
  maxUpgradeLevel(type) {
    const def = BUILDINGS[type] || {};
    return Math.min(def.maxLevel ?? 3, Math.max(1, this.level));
  }

  // ---------- Por que não posso construir isto? ----------
  /**
   * Retorna null se pode construir, ou um motivo:
   *   {reason:'level', need}  {reason:'count'}  {reason:'cost'}
   */
  blockedReason(type) {
    const def = BUILDINGS[type];
    if (!def) return { reason: 'unknown' };
    if (this.level < def.reqLevel) return { reason: 'level', need: def.reqLevel };
    if (this.countOf(type) >= def.maxCount) return { reason: 'count' };
    if (!this.canAfford(this.buildCost(type))) return { reason: 'cost' };
    return null;
  }

  canBuild(type) { return this.blockedReason(type) === null; }

  // ---------- Construir ----------
  /**
   * Constrói uma estrutura. Retorna a estrutura criada ou null.
   * Casas usam HOUSE_SLOTS; as demais têm um ponto fixo na clareira.
   */
  build(type) {
    if (!this.canBuild(type)) return null;
    const cost = this.buildCost(type);

    let x;
    let y;
    let slot;
    if (type === 'house') {
      if (this.nextSlot >= HOUSE_SLOTS.length) return null;
      slot = this.nextSlot;
      [x, y] = HOUSE_SLOTS[slot];
      this.nextSlot += 1;
    } else {
      [x, y] = STRUCT_SLOTS[type] || [960, 726];
    }

    this.pay(cost);
    const s = { type, level: 1, x, y };
    if (slot != null) s.slot = slot;
    this.structures.push(s);
    return s;
  }

  /** Compatibilidade com o código antigo. */
  buildHouse() { return this.build('house') !== null; }

  houseBuildCost() { return this.buildCost('house'); }

  houseUpgradeCost(house) { return this.upgradeCost(house); }

  // ---------- Melhorar ----------
  /** Melhora uma estrutura pelo objeto. Retorna true se subiu de nível. */
  upgrade(structure) {
    if (!structure) return false;
    if (structure.level >= this.maxUpgradeLevel(structure.type)) return false;
    const cost = this.upgradeCost(structure);
    if (!this.canAfford(cost)) return false;
    this.pay(cost);
    structure.level += 1;
    return true;
  }

  /** Melhora a casa pelo índice (usado pela aba Melhorias). */
  upgradeHouse(index) { return this.upgrade(this.houses[index]); }

  // ---------- Goblins ----------
  recruit(goblin) {
    if (this.goblins.length >= this.capacity) return false;
    this.goblins.push(goblin);
    this.recruitedCount += 1;
    return true;
  }

  /** Remove um goblin (usado pelo Bazar). Retorna o removido. */
  removeGoblin(index) {
    if (index < 0 || index >= this.goblins.length) return null;
    return this.goblins.splice(index, 1)[0];
  }

  // ---------- Render / hit-test no mundo ----------
  drawList() {
    return this.structures.map((s) => ({
      y: s.y,
      draw: (ctx) => {
        const spr = getSprite(BUILDINGS[s.type]?.sprite || 'building_house_1');
        ctx.drawImage(spr, s.x - 32, s.y - 60, 64, 64);
        // pips de nível
        for (let i = 0; i < s.level; i++) {
          ctx.fillStyle = '#e8b23a';
          ctx.fillRect(s.x - 10 + i * 7, s.y - 66, 4, 4);
        }
      },
    }));
  }

  hitTest(wx, wy) {
    for (const s of this.structures) {
      if (wx >= s.x - 30 && wx <= s.x + 30 && wy >= s.y - 60 && wy <= s.y + 4) return s;
    }
    return null;
  }

  serialize() {
    return {
      res: this.res,
      structures: this.structures,
      goblins: this.goblins,
      recruitedCount: this.recruitedCount,
      nextSlot: this.nextSlot,
      level: this.level,
      xp: this.xp,
      meals: this.meals,
      items: this.items,
    };
  }
}

module.exports = { Village, BUILDINGS, BUILD_ORDER };
