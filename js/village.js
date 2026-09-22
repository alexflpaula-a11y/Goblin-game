// ============================================================
// village.js — Estado da vila: recursos, estruturas, habitação
// (1 casa = 1 gnomo→goblin por nível), construir/melhorar casa
// abre recrutamento (escolher 1 de 3).
// ============================================================
const { getSprite } = require('assetLoader.js');
const { BAL } = require('balance.js');
const { Goblin } = require('goblin.js');
const BUILDING_SPRITE = {
  construction: 'building_construction_1',
  house: 'building_house_1',
  quest: 'building_questboard_1',
};

// Posições fixas (slots) para novas casas dentro da clareira
const HOUSE_SLOTS = [
  [1000, 706], [920, 750], [1000, 750], [850, 706], [1070, 706],
  [850, 750], [1070, 750], [880, 670], [1040, 670], [960, 790],
  [880, 790], [1040, 790],
];

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
  }

  get houses() { return this.structures.filter((s) => s.type === 'house'); }
  get capacity() { return this.houses.reduce((a, h) => a + h.level, 0); }
  // Nível da vila (sistema completo chega na etapa 1.8)
  get level() { return this._level ?? 1; }

  canAfford(cost) {
    return Object.entries(cost).every(([k, v]) => (this.res[k] || 0) >= v);
  }
  pay(cost) {
    for (const [k, v] of Object.entries(cost)) this.res[k] -= v;
  }
  costText(cost, t) {
    return Object.entries(cost).map(([k, v]) => `${v} ${t(`res.${k}`)}`).join(' + ');
  }

  houseBuildCost() { return BAL.house?.buildCost || { wood: 15, stone: 10 }; }
  houseUpgradeCost(house) {
    const base = BAL.house?.upgradeBase || { wood: 25, stone: 15 };
    const mul = Math.pow(BAL.house?.upgradeMul ?? 1.6, house.level - 1);
    const out = {};
    for (const [k, v] of Object.entries(base)) out[k] = Math.round(v * mul);
    return out;
  }

  buildHouse() {
    if (this.nextSlot >= HOUSE_SLOTS.length) return false;
    const cost = this.houseBuildCost();
    if (!this.canAfford(cost)) return false;
    this.pay(cost);
    const [x, y] = HOUSE_SLOTS[this.nextSlot];
    this.structures.push({ type: 'house', level: 1, x, y, slot: this.nextSlot });
    this.nextSlot += 1;
    return true;
  }

  upgradeHouse(index) {
    const house = this.houses[index];
    if (!house || house.level >= (BAL.house?.maxLevel ?? 3)) return false;
    const cost = this.houseUpgradeCost(house);
    if (!this.canAfford(cost)) return false;
    this.pay(cost);
    house.level += 1;
    return true;
  }

  recruit(goblin) {
    if (this.goblins.length >= this.capacity) return false;
    this.goblins.push(goblin);
    this.recruitedCount += 1;
    return true;
  }

  // ---------- Render / hit-test no mundo ----------
  drawList() {
    return this.structures.map((s) => ({
      y: s.y,
      draw: (ctx) => {
        const spr = getSprite(BUILDING_SPRITE[s.type]);
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
    };
  }
}

module.exports = { Village };
