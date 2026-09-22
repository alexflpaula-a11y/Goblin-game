// ============================================================
// quests.js — Painel de Missões (etapa 1.7)
//
// Sempre há missões ativas pedindo itens (madeira, pedra, comidas…)
// em troca de OURO + XP DA VILA. Slots fixos (3 por padrão); ao
// entregar, o slot é substituído por uma missão nova depois de um
// tempo de renovação. A dificuldade escala com o nível da vila.
// ============================================================
const { BAL } = require('balance.js');

// Recursos que uma missão pode pedir, com peso e nível mínimo da vila.
const DEMANDS = [
  { key: 'wood', kind: 'res', weight: 30, minLevel: 1, qty: [5, 14], value: 2 },
  { key: 'stone', kind: 'res', weight: 26, minLevel: 1, qty: [4, 12], value: 2 },
  { key: 'food', kind: 'res', weight: 14, minLevel: 2, qty: [3, 10], value: 3 },
  { key: 'ore', kind: 'res', weight: 12, minLevel: 4, qty: [3, 8], value: 5 },
  { key: 'bread', kind: 'meal', weight: 10, minLevel: 3, qty: [1, 3], value: 12 },
  { key: 'soup', kind: 'meal', weight: 6, minLevel: 3, qty: [1, 2], value: 20 },
  { key: 'stew', kind: 'meal', weight: 4, minLevel: 4, qty: [1, 2], value: 34 },
];

function pickWeighted(list, rng) {
  const total = list.reduce((a, d) => a + d.weight, 0);
  let r = rng() * total;
  for (const d of list) {
    r -= d.weight;
    if (r <= 0) return d;
  }
  return list[list.length - 1];
}

let nextId = 1;

class Quest {
  constructor(data) {
    Object.assign(this, {
      id: nextId++, key: 'wood', kind: 'res', qty: 5,
      gold: 10, xp: 20, done: false,
    }, data);
    if (data?.id != null) nextId = Math.max(nextId, data.id + 1);
  }

  /** Sorteia uma missão adequada ao nível da vila. */
  static roll(villageLevel, rng = Math.random) {
    const pool = DEMANDS.filter((d) => d.minLevel <= villageLevel);
    const d = pickWeighted(pool, rng);

    // quantidade cresce ~12% por nível da vila
    const scale = 1 + (villageLevel - 1) * 0.12;
    const [lo, hi] = d.qty;
    const qty = Math.max(1, Math.round((lo + Math.floor(rng() * (hi - lo + 1))) * scale));

    // recompensa proporcional ao "valor" do que foi pedido
    const worth = qty * d.value;
    const goldMul = BAL.quests?.goldMul ?? 1.6;
    const xpMul = BAL.quests?.xpMul ?? 1.1;
    const gold = Math.round(worth * goldMul);
    const xp = Math.max(
      BAL.quests?.xpMin ?? 20,
      Math.min(BAL.quests?.xpMax ?? 100, Math.round(worth * xpMul)),
    );

    return new Quest({ key: d.key, kind: d.kind, qty, gold, xp });
  }

  /** Quanto o jogador já tem do que a missão pede. */
  have(village) {
    return this.kind === 'meal'
      ? (village.meals?.[this.key] || 0)
      : (village.res?.[this.key] || 0);
  }

  canDeliver(village) { return this.have(village) >= this.qty; }
}

class Quests {
  constructor(data) {
    this.list = (data?.list || []).map((q) => new Quest(q));
    // slots que estão em contagem para renovar: [{left}]
    this.pending = data?.pending || [];
    this.completed = data?.completed ?? 0;
    this.configure();
  }

  /**
   * Relê os números do balance.json. É chamado de novo depois do
   * loadBalance(), porque o painel é criado antes do JSON chegar.
   */
  configure() {
    this.slots = BAL.quests?.slots ?? 3;
    this.renewTime = BAL.quests?.renewSeconds ?? 45;
  }

  /** Garante que os slots vazios sejam preenchidos (no boot). */
  ensure(villageLevel) {
    while (this.list.length + this.pending.length < this.slots) {
      this.list.push(Quest.roll(villageLevel));
    }
  }

  /** Conta o tempo de renovação dos slots entregues. */
  update(dt, villageLevel) {
    for (let i = this.pending.length - 1; i >= 0; i--) {
      this.pending[i].left -= dt;
      if (this.pending[i].left <= 0) {
        this.pending.splice(i, 1);
        this.list.push(Quest.roll(villageLevel));
      }
    }
  }

  /**
   * Entrega a missão: consome os itens e paga ouro + XP da vila.
   * Retorna {gold, xp, levelUps} ou null se não deu.
   */
  deliver(quest, village) {
    if (!quest || !quest.canDeliver(village)) return null;

    if (quest.kind === 'meal') village.meals[quest.key] -= quest.qty;
    else village.res[quest.key] -= quest.qty;

    village.add('gold', quest.gold);
    const levelUps = village.gainXp(quest.xp);

    const idx = this.list.indexOf(quest);
    if (idx >= 0) this.list.splice(idx, 1);
    this.pending.push({ left: this.renewTime });
    this.completed += 1;

    return { gold: quest.gold, xp: quest.xp, levelUps };
  }

  serialize() {
    return {
      list: this.list.map((q) => ({
        id: q.id, key: q.key, kind: q.kind, qty: q.qty, gold: q.gold, xp: q.xp,
      })),
      pending: this.pending,
      completed: this.completed,
    };
  }
}

module.exports = { Quest, Quests, DEMANDS };
