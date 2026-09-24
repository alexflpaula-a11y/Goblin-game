// ============================================================
// goblin.js — Entidade Goblin: atributos, especialidade,
// raridade, nível/XP e geração de candidatos (escolha 1 de 3)
// com "sorte crescente" por gnomos→goblins já recrutados.
// ============================================================
const { BAL } = require('balance.js');
const NAMES = ['Grik', 'Snaga', 'Uzgul', 'Mog', 'Zub', 'Krash', 'Narzug', 'Gashbol',
  'Dush', 'Ugluk', 'Bolg', 'Shagrat', 'Gorbag', 'Muzgash', 'Lugburz', 'Radbug'];

const SPECS = ['warrior', 'mage', 'healer', 'cook', 'worker', 'runner', 'common'];
const RARITIES = ['common', 'uncommon', 'rare', 'epic'];
const ATTRS = ['poderDestrutivo', 'potencialMagico', 'vitalidade',
  'velocidade', 'precisao', 'potencialEvolucao'];

const RARITY_SPEC_WEIGHTS = {
  common:   [8, 5, 5, 6, 10, 6, 20],
  uncommon: [12, 8, 8, 8, 12, 8, 10],
  rare:     [16, 12, 12, 10, 12, 12, 2],
  epic:     [22, 16, 16, 12, 12, 16, 0],
};

function pickWeighted(weights, rng) {
  const total = weights.reduce((a, b) => a + b, 0);
  let r = rng() * total;
  for (let i = 0; i < weights.length; i++) {
    r -= weights[i];
    if (r <= 0) return i;
  }
  return weights.length - 1;
}

class Goblin {
  constructor(data) {
    Object.assign(this, {
      name: '?', rarity: 'common', specialty: 'common',
      level: 1, xp: 0,
      poderDestrutivo: 1, potencialMagico: 1, vitalidade: 1,
      velocidade: 1, precisao: 1, potencialEvolucao: 1,
      hp: null, mp: null,
      equip: {},   // { capacete: 'capacete_ferro', anel1: 'anel_rubi', ... }
      skills: [],  // [ 'investida', 'golpe_brutal' ] (2 espaços)
    }, data);
    this.equip = this.equip || {};
    this.skills = this.skills || [];
    this.recalc();
  }

  recalc() {
    this.maxHp = 20 + this.vitalidade * 4 + this.level * 6;
    this.maxMp = 5 + this.potencialMagico * 3 + this.level * 2;
    if (this.hp == null) this.hp = this.maxHp;
    if (this.mp == null) this.mp = this.maxMp;
    this.hp = Math.min(this.hp, this.maxHp);
    this.mp = Math.min(this.mp, this.maxMp);
  }

  xpNext() { return 40 + this.level * 30; }

  // Ganha XP com bônus do potencialEvolucao; retorna níveis subidos
  gainXp(amount) {
    const gained = Math.round(amount * (1 + this.potencialEvolucao / 20));
    this.xp += gained;
    let ups = 0;
    while (this.xp >= this.xpNext()) {
      this.xp -= this.xpNext();
      this.level += 1;
      ups += 1;
      // sobe 2 atributos aleatórios (teto 10)
      for (let i = 0; i < 2; i++) {
        const a = ATTRS[Math.floor(Math.random() * ATTRS.length)];
        this[a] = Math.min(10, this[a] + 1);
      }
    }
    this.recalc();
    return ups;
  }

  // ---------- Geração ----------
  // Sorte crescente: quanto mais goblins já recrutados, maior a
  // chance de raridades altas.
  static rollRarity(recruitedCount, rng = Math.random) {
    const base = BAL.recruit?.rarityBase || { common: 0.68, uncommon: 0.22, rare: 0.08, epic: 0.02 };
    const luck = recruitedCount * (BAL.recruit?.luckPerRecruit ?? 0.005);
    const wRare = base.rare + luck;
    const wEpic = base.epic + luck * 0.5;
    const wUnc = base.uncommon + luck * 0.5;
    const wCom = Math.max(0.15, 1 - wRare - wEpic - wUnc);
    const i = pickWeighted([wCom, wUnc, wRare, wEpic], rng);
    return RARITIES[i];
  }

  static roll(recruitedCount, existingNames = [], rng = Math.random) {
    const rarity = Goblin.rollRarity(recruitedCount, rng);
    const [lo, hi] = (BAL.recruit?.attrRange || {})[rarity] || [1, 6];
    const attrs = {};
    for (const a of ATTRS) attrs[a] = lo + Math.floor(rng() * (hi - lo + 1));

    const spec = SPECS[pickWeighted(RARITY_SPEC_WEIGHTS[rarity], rng)];

    let name = NAMES[Math.floor(rng() * NAMES.length)];
    if (existingNames.includes(name)) {
      let n = 2;
      while (existingNames.includes(`${name} ·${n}`)) n++;
      name = `${name} ·${n}`;
    }

    return new Goblin({ name, rarity, specialty: spec, ...attrs });
  }

  // Os 3 candidatos da tela de recrutamento
  static candidates(recruitedCount, existingNames = []) {
    const out = [];
    const names = [...existingNames];
    for (let i = 0; i < 3; i++) {
      const g = Goblin.roll(recruitedCount, names);
      names.push(g.name);
      out.push(g);
    }
    return out;
  }
}

module.exports = { SPECS, RARITIES, ATTRS, Goblin };
