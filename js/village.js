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
//
// Tempo de obra: uma construção desbloqueada no nível N começa em
// 10 × N segundos e cada nível da estrutura acrescenta mais 10 s.
// Casa (req. 1) = 10/20/30 s; Serraria (req. 2) = 20/30/40 s;
// Cozinha (req. 3) = 30/40/50 s, e assim por diante.
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
  grande_arvore: {
    sprite: 'building_grande_arvore_1', reqLevel: 3, maxCount: 1, maxLevel: 3,
    deity: true, cost: { wood: 75, stone: 35, gold: 25 },
  },
  golem_pedra: {
    sprite: 'building_golem_pedra_1', reqLevel: 3, maxCount: 1, maxLevel: 3,
    deity: true, cost: { wood: 35, stone: 90, gold: 25 },
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
const BUILD_ORDER = ['house', 'serraria', 'fazenda', 'armazem', 'cozinha', 'mercado',
  'grande_arvore', 'golem_pedra', 'estabulo', 'ferraria', 'altar', 'bazar', 'porto', 'quartel'];

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
  grande_arvore: [760, 726], golem_pedra: [1160, 726],
  estabulo: [1205, 650], ferraria: [850, 620], altar: [1070, 620],
  bazar: [850, 830], porto: [1070, 830],
  quartel: [960, 590], armazem: [960, 858],
};

class Village {
  constructor(data) {
    this.res = data?.res || { ...(BAL.startResources || { wood: 50, stone: 30, gold: 100 }) };
    for (const k of ['wood', 'stone', 'ore', 'food', 'gold']) {
      if (this.res[k] == null) this.res[k] = 0;
    }
    const initialStructures = data?.structures || [
      { type: 'construction', level: 1, x: 920, y: 706 },
      { type: 'quest', level: 1, x: 960, y: 630 },
      { type: 'house', level: 1, x: 1000, y: 706, slot: 0 },
    ];
    // Migração transparente: a Mina foi retirada do jogo.
    this.structures = initialStructures.filter((s) => s.type !== 'mina');
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
  /** Uma obra só passa a valer depois de o jogador recolhê-la na lona. */
  isReady(structure) { return !!structure && !structure.construction; }

  get houses() { return this.structures.filter((s) => s.type === 'house' && this.isReady(s)); }
  get capacity() { return this.houses.reduce((a, h) => a + h.level, 0); }

  /** Estruturas prontas que não são casas (uma de cada, no máximo). */
  get facilities() {
    return this.structures.filter((s) => s.type !== 'house' && this.isReady(s));
  }

  /** Retorna a estrutura pronta desse tipo (ou null). Casas: use `houses`. */
  get(type) { return this.structures.find((s) => s.type === type && this.isReady(s)) || null; }

  /** Nível de uma estrutura construída; 0 se ainda não existe. */
  levelOf(type) { return this.get(type)?.level || 0; }

  has(type) { return this.levelOf(type) > 0; }

  /** Conta também a obra pendente para não permitir duplicatas na construção. */
  countOf(type) { return this.structures.filter((s) => s.type === type).length; }

  /** Obras ainda aguardando trabalho ou prontas para serem recolhidas. */
  get constructionSites() { return this.structures.filter((s) => !!s.construction); }

  /** Segundos de trabalho para alcançar `targetLevel` nesta estrutura. */
  constructionSeconds(type, targetLevel = 1) {
    const req = BUILDINGS[type]?.reqLevel ?? 1;
    return 10 * Math.max(1, req + Math.max(1, targetLevel) - 1);
  }

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
   * Constrói uma estrutura. `position` permite ao jogador escolher o ponto;
   * sem ele, os slots antigos continuam servindo aos testes/demos e saves.
   */
  build(type, position = null) {
    if (!this.canBuild(type)) return null;
    const cost = this.buildCost(type);

    let x;
    let y;
    let slot;
    if (position && Number.isFinite(position.x) && Number.isFinite(position.y)) {
      x = Math.round(position.x);
      y = Math.round(position.y);
      if (type === 'house') {
        slot = this.nextSlot;
        this.nextSlot += 1;
      }
    } else if (type === 'house') {
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

  buildAt(type, x, y) { return this.build(type, { x, y }); }

  /**
   * Cria uma obra no mapa. `build()` continua instantâneo para preservar a
   * API de saves antigos, testes de lógica e prévias; a UI usa este método
   * para que toda construção ganhe lona, construtor e cronômetro.
   */
  beginBuildAt(type, x, y) {
    const structure = this.buildAt(type, x, y);
    if (!structure) return null;
    const seconds = this.constructionSeconds(type, 1);
    structure.construction = {
      kind: 'build', targetLevel: 1,
      total: seconds, remaining: seconds,
      status: 'building', worker: null, working: false,
    };
    return structure;
  }

  /** Move sem custo uma estrutura já construída. */
  move(structure, x, y) {
    if (!structure || !this.structures.includes(structure)) return false;
    if (!Number.isFinite(x) || !Number.isFinite(y)) return false;
    structure.x = Math.round(x);
    structure.y = Math.round(y);
    return true;
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

  /** Paga uma melhoria, mas só aplica o novo nível quando a obra terminar. */
  beginUpgrade(structure) {
    if (!structure || !this.isReady(structure)) return false;
    if (structure.level >= this.maxUpgradeLevel(structure.type)) return false;
    const cost = this.upgradeCost(structure);
    if (!this.canAfford(cost)) return false;
    this.pay(cost);
    const targetLevel = structure.level + 1;
    const seconds = this.constructionSeconds(structure.type, targetLevel);
    structure.construction = {
      kind: 'upgrade', targetLevel,
      total: seconds, remaining: seconds,
      status: 'building', worker: null, working: false,
    };
    return true;
  }

  /** Recolhe uma obra concluída: ela passa a funcionar na vila. */
  completeConstruction(structure) {
    if (!structure?.construction || structure.construction.status !== 'ready') return false;
    structure.level = structure.construction.targetLevel;
    delete structure.construction;
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
  drawList(time = 0) {
    // Divindades prontas são desenhadas pelo deities.js; uma divindade em
    // obra ainda precisa mostrar a lona nesta lista.
    return this.structures
      .filter((s) => !BUILDINGS[s.type]?.deity || s.construction)
      .map((s) => ({
        y: s.y,
        draw: (ctx) => {
          const work = s.construction;
          if (work) {
            // A lona branca cercada é um sprite próprio. Poeira e brilho são
            // animados aqui para reagirem ao trabalho e ao relógio da obra.
            ctx.drawImage(getSprite('building_construction_site'), s.x - 32, s.y - 60, 64, 64);

            if (work.status === 'building') {
              if (work.working) {
                ctx.save();
                for (let i = 0; i < 9; i++) {
                  const phase = time * (2.4 + i * 0.11) + i * 1.73;
                  const rise = (Math.sin(phase) + 1) * 0.5;
                  const px = s.x - 16 + ((i * 13) % 31) + Math.sin(phase * 1.7) * 3;
                  const py = s.y - 9 - rise * (9 + (i % 3) * 4);
                  ctx.globalAlpha = 0.18 + rise * 0.26;
                  ctx.fillStyle = i % 2 ? '#c8ae7b' : '#e4d0a0';
                  ctx.fillRect(Math.round(px), Math.round(py), i % 3 === 0 ? 3 : 2, i % 3 === 0 ? 3 : 2);
                }
                ctx.restore();
              }
              const seconds = Math.max(0, Math.ceil(work.remaining));
              ctx.fillStyle = 'rgba(20,14,27,0.82)';
              ctx.fillRect(s.x - 20, s.y - 73, 40, 11);
              ctx.strokeStyle = 'rgba(255,233,168,0.75)';
              ctx.lineWidth = 1;
              ctx.strokeRect(s.x - 19.5, s.y - 72.5, 39, 10);
              ctx.fillStyle = '#ffe9a8';
              ctx.font = 'bold 8px monospace';
              ctx.textAlign = 'center';
              ctx.fillText(`${seconds}s`, s.x, s.y - 65);
              const progress = 1 - work.remaining / Math.max(1, work.total);
              ctx.fillStyle = 'rgba(0,0,0,0.48)';
              ctx.fillRect(s.x - 17, s.y + 5, 34, 3);
              ctx.fillStyle = '#e8b23a';
              ctx.fillRect(s.x - 17, s.y + 5, 34 * Math.max(0, progress), 3);
              ctx.textAlign = 'left';
            } else {
              // Terminou: o cronômetro some e a lona chama o toque com brilho.
              const pulse = 0.45 + (Math.sin(time * 5) + 1) * 0.18;
              ctx.save();
              ctx.globalAlpha = pulse;
              ctx.strokeStyle = '#fff3a8';
              ctx.lineWidth = 1.5;
              ctx.beginPath();
              ctx.arc(s.x, s.y - 29, 28 + Math.sin(time * 4) * 2, 0, Math.PI * 2);
              ctx.stroke();
              ctx.fillStyle = '#fff7bf';
              for (let i = 0; i < 4; i++) {
                const a = time * 1.8 + i * Math.PI / 2;
                const px = s.x + Math.cos(a) * 25;
                const py = s.y - 29 + Math.sin(a) * 19;
                ctx.fillRect(Math.round(px) - 1, Math.round(py) - 1, 3, 3);
              }
              ctx.restore();
            }
            return;
          }

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
