// ============================================================
// goblin.js — Entidade Goblin: atributos, especialidade,
// raridade, nível/XP e geração de candidatos (escolha 1 de 3)
// com "sorte crescente" por gnomos→goblins já recrutados.
// ============================================================
const { BAL } = require('balance.js');
const NAMES = ['Grik', 'Snaga', 'Uzgul', 'Mog', 'Zub', 'Krash', 'Narzug', 'Gashbol',
  'Dush', 'Ugluk', 'Bolg', 'Shagrat', 'Gorbag', 'Muzgash', 'Lugburz', 'Radbug'];

const SPECS = ['warrior', 'mage', 'healer', 'cook', 'worker', 'runner', 'common'];
const RARITIES = ['common', 'uncommon', 'rare', 'epic', 'mythic', 'legendary', 'divine'];
const ATTRS = ['poderDestrutivo', 'potencialMagico', 'vitalidade',
  'velocidade', 'precisao', 'potencialEvolucao'];

// As 45 aparências fornecidas pelo autor, mantidas na ordem numérica dos GIFs.
// Cada uma possui os 59 quadros: idle 5, walk 8, attack 17, hurt 17, death 12.
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
  common:    [8, 5, 5, 6, 10, 6, 20],
  uncommon:  [12, 8, 8, 8, 12, 8, 10],
  rare:      [16, 12, 12, 10, 12, 12, 2],
  epic:      [22, 16, 16, 12, 12, 16, 0],
  mythic:    [26, 20, 20, 14, 12, 18, 0],
  legendary: [28, 22, 22, 15, 13, 20, 0],
  divine:    [30, 24, 24, 16, 14, 22, 0],
};

// Chance de cada faixa: 1/2 comum, 1/5 incomum, 1/10 raro, 1/50 épico,
// 1/100 mítico, 1/500 lendário e 1/5000 divino. Só o DENOMINADOR é fixo:
// o numerador começa em 1 e sobe um décimo a cada goblin já recrutado.
// Quando a fração chega a 1 inteiro, aquela faixa atingiu o máximo e
// para de aparecer (ex.: com 10 goblins o comum vira 2/2 e sai do sorteio).
// As faixas "especiais" ainda não existem e não entram aqui.
const RARITY_DENOMINATOR = Object.freeze({
  common: 2, uncommon: 5, rare: 10, epic: 50,
  mythic: 100, legendary: 500, divine: 5000,
});
const RARITY_LUCK_STEP = 0.1;

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
      // tarefa persistente escolhida na Área/prédios dos Goblins:
      // null | wood | stone | food | builder | cook
      assignment: null,
    }, data);
    this.equip = this.equip || {};
    // A interface não possui mais espaço de runa; saves antigos descartam
    // somente o vínculo equipado, sem deixar um slot invisível no boneco.
    delete this.equip.runa;
    this.skills = this.skills || [];
    if (!['wood', 'stone', 'food', 'builder', 'cook'].includes(this.assignment)) this.assignment = null;
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
  /**
   * Tabela de chances do momento. Cada faixa é `numerador/denominador`:
   * o numerador sobe 0,1 por goblin recrutado e, ao alcançar o
   * denominador, a faixa está no máximo e sai do sorteio.
   * Devolve também a chance real (peso normalizado) de cada faixa.
   */
  static rarityOdds(recruitedCount = 0) {
    const denominators = { ...RARITY_DENOMINATOR, ...(BAL.recruit?.rarityDenominator || {}) };
    const step = BAL.recruit?.luckStep ?? RARITY_LUCK_STEP;
    const raw = 1 + Math.max(0, recruitedCount) * step;
    const rows = RARITIES.map((rarity) => {
      const denominator = denominators[rarity];
      const maxed = raw >= denominator;
      return {
        rarity, denominator,
        numerator: Math.min(raw, denominator),
        weight: maxed ? 0 : raw / denominator,
        maxed,
      };
    });
    const total = rows.reduce((sum, row) => sum + row.weight, 0);
    const fallback = rows[rows.length - 1];
    for (const row of rows) {
      row.chance = total > 0 ? row.weight / total : (row === fallback ? 1 : 0);
    }
    return rows;
  }

  // Sorte crescente: cada goblin recrutado aproxima as faixas do seu teto,
  // e as que chegaram ao máximo deixam de ser sorteadas.
  static rollRarity(recruitedCount, rng = Math.random) {
    const rows = Goblin.rarityOdds(recruitedCount);
    const weights = rows.map((row) => row.weight);
    if (weights.reduce((a, b) => a + b, 0) <= 0) return rows[rows.length - 1].rarity;
    return rows[pickWeighted(weights, rng)].rarity;
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

module.exports = {
  SPECS, RARITIES, RARITY_DENOMINATOR, RARITY_LUCK_STEP, ATTRS, VARIATIONS, Goblin,
};
