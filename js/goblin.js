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

// As 45 aparências fornecidas pelo autor, mantidas na ordem numérica dos GIFs.
// Cada uma possui os 62 quadros: idle, walk, attack, hurt e death.
const VARIATIONS = [
  '01_dente_dourado', '02_tapa_olho', '04_orelha_furada', '07_cicatriz', '08_albinismo',
  '09_queimaduras', '10_corsario', '13_sobrevivente', '14_anel', '15_marca_de_nascenca',
  '16_sem_orelha', '17_enfaixado', '18_ileso', '19_olho_cego', '20_verruga',
  '21_sardas', '22_tatuagem_facial', '23_presas_duplas', '24_olho_rubi', '26_veterano',
  '27_queimado_enfaixado', '28_albino_rubi', '29_guerreiro_marcado', '30_sobrevivente_ferido', '31_mistico',
  '32_brigao', '33_amaldicoado', '34_sardento', '35_cacador_marcado', '36_pirata_queimado',
  '37_albino_cicatrizado', '38_guerreiro_enfaixado', '39_oraculo_rubi', '40_presas_douradas', '41_veterano_enfaixado',
  '42_queimado_tatuado', '43_albino_sardento', '44_brigao_cego', '45_fanatico', '46_marcado_rubi',
  '47_sobrevivente_sujo', '48_corsario_tatuado', '49_guerreiro_dourado', '50_amaldicoado_enfaixado', '51_mutilado',
];
const VARIATION_SET = new Set(VARIATIONS);

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
      variation: null, // aparência física; null preserva goblins de saves antigos
      level: 1, xp: 0,
      poderDestrutivo: 1, potencialMagico: 1, vitalidade: 1,
      velocidade: 1, precisao: 1, potencialEvolucao: 1,
      hp: null, mp: null,
      equip: {},   // { capacete: 'capacete_ferro', anel1: 'anel_rubi', ... }
      skills: [],  // [ 'investida', 'golpe_brutal' ] (2 espaços)
    }, data);
    this.equip = this.equip || {};
    this.skills = this.skills || [];
    if (!VARIATION_SET.has(this.variation)) this.variation = null;
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

  static roll(recruitedCount, existingNames = [], rng = Math.random, excludedVariations = []) {
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

    // Evita repetir aparência entre os três candidatos quando possível.
    const blocked = new Set(excludedVariations);
    const available = VARIATIONS.filter((id) => !blocked.has(id));
    const pool = available.length ? available : VARIATIONS;
    const variation = pool[Math.floor(rng() * pool.length)];

    return new Goblin({ name, rarity, specialty: spec, variation, ...attrs });
  }

  // Os 3 candidatos da tela de recrutamento
  static candidates(recruitedCount, existingNames = [], rng = Math.random) {
    const out = [];
    const names = [...existingNames];
    const variations = [];
    for (let i = 0; i < 3; i++) {
      const g = Goblin.roll(recruitedCount, names, rng, variations);
      names.push(g.name);
      variations.push(g.variation);
      out.push(g);
    }
    return out;
  }
}

module.exports = { SPECS, RARITIES, ATTRS, VARIATIONS, Goblin };
