// ============================================================
// deities.js — Divindades ativadas manualmente por goblins.
//
// Nenhuma estrutura começa com acólito: o jogador toca na divindade e
// envia um goblin livre. O milagre só avança depois que ele chega e começa
// a louvar. Tocar outra vez (ou no goblin) interrompe o culto.
// ============================================================
const { getSprite } = require('assetLoader.js');
const { ISLAND_NODE_CAP } = require('nodes.js');

const DEITY_TYPES = ['grande_arvore', 'golem_pedra'];
const MAX_WORSHIPPERS = 3;
const MAX_DEITY_LEVEL = 3;
const ANIMATION_FRAMES = {
  treeChant: 24,
  golemForge: 28,
  projectileSpin: 20,
};

// Por enquanto, os santuários produzem apenas o material-base. Os outros
// graus permanecem reservados para o futuro sistema de runas/forja.
const DEITY_RESOURCES = {
  grande_arvore: { key: 'wood', amount: 2 },
  golem_pedra: { key: 'stone', amount: 2 },
};

const clamp01 = (n) => Math.max(0, Math.min(1, n));
const easeOut = (n) => 1 - Math.pow(1 - clamp01(n), 3);
const easeInOut = (n) => {
  const t = clamp01(n);
  return t < 0.5 ? 2 * t * t : 1 - Math.pow(-2 * t + 2, 2) / 2;
};
const stepped = (n, frames) => Math.floor(clamp01(n) * (frames - 1)) / Math.max(1, frames - 1);

class Deities {
  constructor(world, village, nodes, rng = Math.random) {
    this.world = world;
    this.village = village;
    this.nodes = nodes;
    this.rng = rng;
    this.clock = 0;
    this.projectiles = [];
    this.states = {
      grande_arvore: {
        active: false, worshippers: [], worshipper: null,
        mode: 'idle', time: 0, cooldown: 1.8,
        duration: 4.2, site: null,
      },
      golem_pedra: {
        active: false, worshippers: [], worshipper: null,
        mode: 'idle', time: 0, cooldown: 2.2,
        duration: 3.1, site: null, launched: false,
      },
    };
    this.sync();
  }

  /** Perfil persistente da divindade, migrado sem quebrar saves antigos. */
  profile(type) {
    const structure = this.village.get(type);
    if (!structure) return null;
    const profile = structure.deity || {};
    profile.level = Math.max(1, Math.min(MAX_DEITY_LEVEL, Math.round(profile.level || 1)));
    profile.xp = Math.max(0, Number(profile.xp) || 0);
    structure.deity = profile;
    return profile;
  }

  xpNext(type) {
    const level = this.profile(type)?.level || 1;
    // Um acólito leva minutos; com os três postos ocupados o primeiro nível
    // ainda pede um minuto inteiro de louvor contínuo.
    return 180 + (level - 1) * 150;
  }

  /** Duração de um ciclo completo com os acólitos presentes. */
  cycleSeconds(type) {
    const profile = this.profile(type) || { level: 1 };
    const power = Math.max(1, this.poweredCount(type));
    const base = type === 'grande_arvore' ? 12 : 9.5;
    // Acólitos e evolução aceleram a geração, sem liberar materiais novos.
    return Math.max(3, (base - (profile.level - 1) * 1.5) / power);
  }

  production(type) { return DEITY_RESOURCES[type] || null; }

  /** Valida acólitos sem jamais preencher uma estrutura automaticamente. */
  sync() {
    for (const type of DEITY_TYPES) {
      const state = this.states[type];
      if (!this.village.has(type)) {
        if (state.active) this.deactivate(type);
        continue;
      }
      // Migra o único acólito do formato antigo e remove referências que não
      // correspondem mais a um goblin realmente louvando esta divindade.
      if (!Array.isArray(state.worshippers)) state.worshippers = [];
      if (state.worshipper != null && !state.worshippers.includes(state.worshipper)) {
        state.worshippers.push(state.worshipper);
      }
      state.worshippers = state.worshippers.filter((idx) => {
        const walker = this.world.goblins[idx];
        return !!walker && walker.job?.deityType === type;
      }).slice(0, MAX_WORSHIPPERS);
      state.active = state.worshippers.length > 0;
      state.worshipper = state.worshippers[0] ?? null; // compatibilidade
      if (!state.active) {
        state.mode = 'idle';
        state.time = 0;
        state.site = null;
        state.launched = false;
      }
    }
  }

  worshipPosition(type, structure, slot = 0) {
    const side = type === 'grande_arvore' ? 1 : -1;
    const positions = [
      { x: 39, y: 12 }, { x: 18, y: 25 }, { x: 55, y: 27 },
    ];
    const p = positions[slot % MAX_WORSHIPPERS];
    return { x: structure.x + side * p.x, y: structure.y + p.y, face: -side };
  }

  /** Envia um goblin livre para um dos três postos de louvor. */
  activate(type, walkers = this.world.goblins, preferredIndex = null) {
    const structure = this.village.get(type);
    const state = this.states[type];
    if (!structure || !state) return { ok: false, reason: 'missing' };
    this.sync();
    if (state.worshippers.length >= MAX_WORSHIPPERS) return { ok: false, reason: 'full' };

    let best = preferredIndex == null ? null : walkers[preferredIndex];
    if (best?.job) return { ok: false, reason: 'busy' };
    if (!best) {
      const target = this.worshipPosition(type, structure, state.worshippers.length);
      let bestDistance = Infinity;
      for (const walker of walkers) {
        if (walker.job) continue;
        const d = Math.hypot(walker.x - target.x, walker.y - target.y);
        if (d < bestDistance) { best = walker; bestDistance = d; }
      }
    }
    if (!best) return { ok: false, reason: 'no_idle' };

    const target = this.worshipPosition(type, structure, state.worshippers.length);
    best.target = null;
    best.job = { type: 'worship-goto', deityType: type, target };
    state.worshippers.push(best.i);
    state.active = true;
    state.worshipper = state.worshippers[0];
    state.mode = 'idle';
    state.time = 0;
    state.site = null;
    state.cooldown = Math.min(state.cooldown, type === 'grande_arvore' ? 1.8 : 2.2);
    return { ok: true, walker: best };
  }

  /** Libera todos, ou apenas o acólito informado, sem apagar o XP acumulado. */
  deactivate(type, onlyIndex = null) {
    const state = this.states[type];
    if (!state) return false;
    const leaving = onlyIndex == null ? [...state.worshippers] : [onlyIndex];
    for (const index of leaving) {
      const walker = this.world.goblins[index];
      if (walker?.job?.deityType === type) {
        walker.job = null;
        walker.wait = 0.3;
        walker.target = null;
      }
    }
    state.worshippers = state.worshippers.filter((i) => !leaving.includes(i));
    state.active = state.worshippers.length > 0;
    state.worshipper = state.worshippers[0] ?? null;
    if (!state.active) {
      state.mode = 'idle';
      state.time = 0;
      state.site = null;
      state.launched = false;
    }
    return leaving.length > 0;
  }

  releaseByWalker(walker) {
    const type = walker?.job?.deityType;
    return type ? this.deactivate(type, walker.i) : false;
  }

  isActive(type) { return !!this.states[type]?.active; }

  poweredCount(type) {
    const state = this.states[type];
    if (!state) return 0;
    return state.worshippers.filter((idx) => {
      const walker = this.world.goblins[idx];
      return walker?.job?.deityType === type && walker.job.type === 'worship';
    }).length;
  }

  isPowered(type) { return this.poweredCount(type) > 0; }

  countFor(type) {
    const nodeType = type === 'grande_arvore' ? 'tree' : 'rock';
    return this.nodes.countActive(nodeType);
  }

  status(type) {
    const state = this.states[type];
    const profile = this.profile(type) || { level: 1, xp: 0 };
    const output = this.production(type);
    const powered = this.poweredCount(type);
    const seconds = this.cycleSeconds(type);
    const hasSpace = this.countFor(type) < ISLAND_NODE_CAP;
    return {
      count: this.countFor(type), max: ISLAND_NODE_CAP,
      active: !!state?.active, powered: powered > 0, poweredCount: powered,
      worshipper: state?.worshipper ?? null,
      worshippers: [...(state?.worshippers || [])], slots: MAX_WORSHIPPERS,
      level: profile.level, xp: profile.xp, xpNext: this.xpNext(type),
      output, hasSpace, perMinute: powered && hasSpace && output ? output.amount * 60 / seconds : 0,
    };
  }

  update(dt) {
    this.clock += dt;
    this.sync();
    this.updateWorshipXp(dt);
    this.updateTree(dt);
    this.updateGolem(dt);
    this.updateProjectiles(dt);
  }

  /** Cada goblin que chegou ao posto alimenta a barra de evolução. */
  updateWorshipXp(dt) {
    for (const type of DEITY_TYPES) {
      const profile = this.profile(type);
      const power = this.poweredCount(type);
      if (!profile || power <= 0 || profile.level >= MAX_DEITY_LEVEL) continue;
      profile.xp += dt * power;
      const needed = this.xpNext(type);
      if (profile.xp >= needed) {
        profile.xp -= needed;
        profile.level += 1;
        this.world.floats.push({
          x: this.village.get(type)?.x ?? 0, y: (this.village.get(type)?.y ?? 0) - 72,
          ttl: 2.2, text: `✦ LV ${profile.level}`, color: '#ffe27a',
        });
      }
    }
  }

  /** Material-base só é entregue junto de um novo nó dentro do teto da ilha. */
  grantProduction(type, nodeProduced = false) {
    const output = this.production(type);
    if (!output || !nodeProduced) return null;
    this.village.res[output.key] = (this.village.res[output.key] || 0) + output.amount;
    const deity = this.village.get(type);
    this.world.floats.push({
      x: deity?.x ?? 0, y: (deity?.y ?? 0) - 62, ttl: 1.8,
      text: `+${output.amount} ${output.key}`, color: type === 'grande_arvore' ? '#8fe06f' : '#f1c85a',
    });
    return output;
  }

  updateTree(dt) {
    const state = this.states.grande_arvore;
    if (!this.isPowered('grande_arvore')) return;

    if (state.mode === 'idle') {
      state.cooldown -= dt;
      if (state.cooldown > 0) return;

      // Cada milagre ocupa uma vaga real na ilha. Quando as 200 árvores
      // estão ativas, o culto aguarda alguém colher uma antes de gerar outra.
      if (this.countFor('grande_arvore') >= ISLAND_NODE_CAP) {
        state.cooldown = 2;
        return;
      }
      const deity = this.village.get('grande_arvore');
      const site = this.nodes.findDivineSite('tree', this.village.structures, this.rng, deity,
        { minFromOrigin: 210 });
      if (!site) { state.cooldown = 2; return; }
      state.mode = 'chant';
      state.time = 0;
      state.duration = this.cycleSeconds('grande_arvore');
      state.site = site;
      return;
    }

    state.time += dt;
    if (state.time < state.duration) return;

    const node = this.nodes.spawnDivine('tree', state.site);
    if (node) {
      this.grantProduction('grande_arvore', true);
      this.world.floats.push({
        x: node.x, y: node.y - 18, ttl: 1.8,
        text: '♬', color: '#8fe06f',
      });
    }
    state.mode = 'idle';
    state.time = 0;
    state.site = null;
    state.cooldown = Math.max(1.4, this.cycleSeconds('grande_arvore') * 0.22);
  }

  updateGolem(dt) {
    const state = this.states.golem_pedra;
    if (!this.isPowered('golem_pedra')) return;

    if (state.mode === 'idle') {
      state.cooldown -= dt;
      if (state.cooldown > 0) return;

      // O Golem também espera uma vaga real: não há pedra/produto extra
      // enquanto a ilha já estiver no teto de rochas ativas.
      if (this.countFor('golem_pedra') + this.projectiles.length >= ISLAND_NODE_CAP) {
        state.cooldown = 2;
        return;
      }
      const deity = this.village.get('golem_pedra');
      const site = this.nodes.findDivineSite('rock', this.village.structures, this.rng, deity,
        { minFromOrigin: 220, maxFromOrigin: 560 });
      if (!site) { state.cooldown = 2; return; }
      state.mode = 'forge';
      state.time = 0;
      state.duration = this.cycleSeconds('golem_pedra');
      state.site = site;
      state.launched = false;
      return;
    }

    state.time += dt;
    // 28 poses: condensação, levantamento, antecipação e soltura.
    if (!state.launched && state.time >= state.duration * 0.5) {
      const deity = this.village.get('golem_pedra');
      if (deity && state.site) {
        this.projectiles.push({
          type: 'rock',
          x0: deity.x + 25, y0: deity.y - 51,
          x1: state.site.x, y1: state.site.y,
          x: deity.x + 25, y: deity.y - 51,
          groundY: deity.y,
          time: 0, duration: 1.85, spin: 0, trail: [],
        });
      }
      state.launched = true;
    }

    if (state.time >= state.duration) {
      state.mode = 'idle';
      state.time = 0;
      state.site = null;
      state.cooldown = Math.max(1.7, this.cycleSeconds('golem_pedra') * 0.24);
    }
  }

  updateProjectiles(dt) {
    for (const p of this.projectiles) {
      p.trail.unshift({ x: p.x, y: p.y, spin: p.spin });
      if (p.trail.length > 7) p.trail.length = 7;
      p.time += dt;
      const t = clamp01(p.time / p.duration);
      const travel = easeInOut(t);
      p.x = p.x0 + (p.x1 - p.x0) * travel;
      p.groundY = p.y0 + (p.y1 - p.y0) * travel;
      const arc = Math.sin(t * Math.PI) * Math.min(175, 82 + Math.abs(p.x1 - p.x0) * 0.16);
      p.y = p.groundY - arc;
      p.spin = stepped(t, ANIMATION_FRAMES.projectileSpin) * Math.PI * 6;
      p.progress = t;
      p.done = t >= 1;
    }

    const landed = this.projectiles.filter((p) => p.done);
    this.projectiles = this.projectiles.filter((p) => !p.done);
    for (const p of landed) {
      if (this.countFor('golem_pedra') >= ISLAND_NODE_CAP) continue;
      const node = this.nodes.spawnDivine('rock', { x: p.x1, y: p.y1 });
      if (node) {
        this.grantProduction('golem_pedra', true);
        this.world.floats.push({
          x: node.x, y: node.y - 18, ttl: 1.5,
          text: '◆  +1', color: '#f1c85a',
        });
      }
    }
  }

  /** Entidades animadas inseridas na ordenação por profundidade do mundo. */
  drawList(time = this.clock) {
    const out = [];
    for (const type of DEITY_TYPES) {
      const structure = this.village.get(type);
      if (!structure) continue;
      out.push({
        y: structure.y,
        draw: (ctx) => this.drawDeity(ctx, type, structure, time),
      });
    }
    for (const projectile of this.projectiles) {
      out.push({
        y: projectile.groundY,
        draw: (ctx) => this.drawProjectileShadow(ctx, projectile),
      });
      out.push({
        // Ordena pela projeção no chão para a pedra não sumir atrás de
        // prédios enquanto está alta no arco.
        y: projectile.groundY + 0.1,
        draw: (ctx) => this.drawProjectile(ctx, projectile),
      });
    }
    return out;
  }

  drawDeity(ctx, type, s, time) {
    const state = this.states[type];
    const spriteId = type === 'grande_arvore'
      ? 'building_grande_arvore_1' : 'building_golem_pedra_1';
    const powered = this.isPowered(type);
    const animating = powered && state.mode !== 'idle';

    // Halo em camadas: apagado sem acólito, vivo durante o milagre.
    ctx.save();
    ctx.globalAlpha = animating ? 0.36 + Math.sin(time * 8) * 0.08 : (powered ? 0.24 : 0.10);
    ctx.fillStyle = type === 'grande_arvore' ? '#76d96a' : '#e3b94f';
    ctx.beginPath();
    ctx.ellipse(s.x, s.y + 1, 31 + Math.sin(time * 2) * 2, 8, 0, 0, Math.PI * 2);
    ctx.fill();
    ctx.restore();

    let bob = powered ? Math.sin(time * 2.3) * 0.65 : 0;
    let lean = 0;
    let sx = 1;
    let sy = 1;
    if (type === 'grande_arvore' && state.mode === 'chant') {
      const frame = Math.floor(state.time * 12) % ANIMATION_FRAMES.treeChant;
      const phase = frame / ANIMATION_FRAMES.treeChant * Math.PI * 2;
      const envelope = Math.sin(clamp01(state.time / state.duration) * Math.PI);
      lean = Math.sin(phase) * 0.045 * envelope;
      sx = 1 + Math.sin(phase * 2) * 0.042;
      sy = 1 - Math.sin(phase * 2) * 0.032;
      bob -= Math.abs(Math.sin(phase)) * 2;
    } else if (type === 'golem_pedra' && state.mode === 'forge') {
      const p = stepped(state.time / state.duration, ANIMATION_FRAMES.golemForge);
      const anticipation = Math.sin(clamp01(p / 0.58) * Math.PI);
      const release = p > 0.48 ? Math.sin(clamp01((p - 0.48) / 0.35) * Math.PI) : 0;
      lean = anticipation * -0.035 + release * 0.075;
      sx = 1 + anticipation * 0.035 - release * 0.025;
      sy = 1 - anticipation * 0.045 + release * 0.055;
      bob += anticipation * 2 - release * 4;
    }

    ctx.save();
    ctx.translate(s.x, s.y + bob);
    ctx.rotate(lean);
    ctx.scale(sx, sy);
    ctx.drawImage(getSprite(spriteId), -36, -72, 72, 72);
    ctx.restore();

    const deityLevel = this.profile(type)?.level || 1;
    for (let i = 0; i < deityLevel; i++) {
      ctx.fillStyle = '#f2c94c';
      ctx.fillRect(s.x - 10 + i * 7, s.y - 76, 4, 4);
    }

    if (!state.active) this.drawActivationHint(ctx, s, time);
    if (type === 'grande_arvore' && state.mode === 'chant' && powered) {
      this.drawSong(ctx, s, state.time);
    } else if (type === 'golem_pedra' && state.mode === 'forge' && !state.launched && powered) {
      this.drawForgedRock(ctx, s, state.time);
    }
  }

  drawActivationHint(ctx, s, time) {
    const pulse = 0.65 + Math.sin(time * 5) * 0.25;
    ctx.save();
    ctx.globalAlpha = pulse;
    ctx.fillStyle = '#ffe27a';
    ctx.font = 'bold 12px monospace';
    ctx.textAlign = 'center';
    ctx.fillText('!', s.x, s.y - 82 - Math.sin(time * 4) * 2);
    ctx.restore();
  }

  drawSong(ctx, s, t) {
    const notes = ['♪', '♫', '♪', '♬', '♪', '♫'];
    ctx.save();
    ctx.font = 'bold 11px monospace';
    ctx.textAlign = 'center';
    for (let i = 0; i < notes.length; i++) {
      const phase = (t * 0.48 + i / notes.length) % 1;
      const side = i % 2 ? 1 : -1;
      ctx.globalAlpha = Math.sin(phase * Math.PI) * 0.95;
      ctx.fillStyle = i % 3 === 1 ? '#ffe27a' : '#a8ef79';
      ctx.fillText(notes[i], s.x + side * (22 + phase * 22), s.y - 38 - phase * 46);
      // Folhinhas em dois pixels acompanham cada nota.
      ctx.fillRect(s.x - side * (12 + phase * 25), s.y - 50 - phase * 28, 3, 2);
    }
    ctx.restore();
  }

  drawForgedRock(ctx, s, t) {
    const p = stepped(t / 1.55, 18);
    const grow = easeOut(p);
    const size = 6 + grow * 22;
    const x = s.x + 25 - Math.sin(p * Math.PI) * 5;
    const y = s.y - 48 - Math.sin(p * Math.PI) * 12;
    ctx.save();
    ctx.globalAlpha = 0.16 + grow * 0.28;
    ctx.fillStyle = '#ffd75a';
    ctx.beginPath();
    ctx.arc(x, y, size * 0.72, 0, Math.PI * 2);
    ctx.fill();
    ctx.globalAlpha = 1;
    ctx.translate(x, y);
    ctx.rotate(p * Math.PI * 2);
    ctx.drawImage(getSprite('fx_pedra_divina'), -size / 2, -size / 2, size, size);
    ctx.restore();
  }

  drawProjectileShadow(ctx, p) {
    const height = Math.max(0, p.groundY - p.y);
    const scale = Math.max(0.25, 1 - height / 220);
    ctx.save();
    ctx.globalAlpha = 0.34 * scale;
    ctx.fillStyle = '#17131c';
    ctx.beginPath();
    ctx.ellipse(p.x, p.groundY + 2, 12 * scale, 4 * scale, 0, 0, Math.PI * 2);
    ctx.fill();
    ctx.restore();
  }

  drawProjectile(ctx, p) {
    const sprite = getSprite('fx_pedra_divina');
    ctx.save();
    // Rastro dourado com sete ecos suaves.
    for (let i = p.trail.length - 1; i >= 0; i--) {
      const trail = p.trail[i];
      const a = (1 - i / Math.max(1, p.trail.length)) * 0.16;
      const size = 13 + (p.trail.length - i) * 0.7;
      ctx.save();
      ctx.globalAlpha = a;
      ctx.translate(trail.x, trail.y);
      ctx.rotate(trail.spin || 0);
      ctx.drawImage(sprite, -size / 2, -size / 2, size, size);
      ctx.restore();
    }
    ctx.translate(p.x, p.y);
    ctx.rotate(p.spin || 0);
    ctx.globalAlpha = 0.22;
    ctx.fillStyle = '#ffd75a';
    ctx.beginPath();
    ctx.arc(0, 0, 16, 0, Math.PI * 2);
    ctx.fill();
    ctx.globalAlpha = 1;
    ctx.drawImage(sprite, -13, -13, 26, 26);
    // Faíscas rúnicas giram em sentido contrário.
    ctx.rotate(-(p.spin || 0) * 1.4);
    ctx.fillStyle = '#ffe68a';
    for (let i = 0; i < 4; i++) {
      const a = i * Math.PI / 2;
      ctx.fillRect(Math.cos(a) * 17 - 1, Math.sin(a) * 17 - 1, 2, 2);
    }
    ctx.restore();
  }
}

module.exports = {
  Deities, DEITY_TYPES, ISLAND_NODE_CAP, ANIMATION_FRAMES,
  MAX_WORSHIPPERS, MAX_DEITY_LEVEL, DEITY_RESOURCES,
};
