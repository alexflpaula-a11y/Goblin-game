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
const ANIMATION_FRAMES = {
  treeChant: 24,
  golemForge: 28,
  projectileSpin: 20,
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
        active: false, worshipper: null,
        mode: 'idle', time: 0, cooldown: 1.8,
        duration: 4.2, site: null,
      },
      golem_pedra: {
        active: false, worshipper: null,
        mode: 'idle', time: 0, cooldown: 2.2,
        duration: 3.1, site: null, launched: false,
      },
    };
    this.sync();
  }

  /** Valida acólitos sem jamais preencher uma estrutura automaticamente. */
  sync() {
    for (const type of DEITY_TYPES) {
      const state = this.states[type];
      if (!this.village.has(type)) {
        if (state.active) this.deactivate(type);
        continue;
      }
      if (!state.active) continue;
      const walker = this.world.goblins[state.worshipper];
      if (!walker || walker.job?.deityType !== type) {
        state.active = false;
        state.worshipper = null;
        state.mode = 'idle';
        state.time = 0;
        state.site = null;
      }
    }
  }

  worshipPosition(type, structure) {
    return type === 'grande_arvore'
      ? { x: structure.x + 39, y: structure.y + 12, face: -1 }
      : { x: structure.x - 39, y: structure.y + 12, face: 1 };
  }

  /** Envia o goblin livre mais próximo para ativar a divindade. */
  activate(type, walkers = this.world.goblins) {
    const structure = this.village.get(type);
    const state = this.states[type];
    if (!structure || !state) return { ok: false, reason: 'missing' };
    if (state.active) return { ok: true, already: true, walker: walkers[state.worshipper] };

    const target = this.worshipPosition(type, structure);
    let best = null;
    let bestDistance = Infinity;
    for (const walker of walkers) {
      if (walker.job) continue;
      const d = Math.hypot(walker.x - target.x, walker.y - target.y);
      if (d < bestDistance) { best = walker; bestDistance = d; }
    }
    if (!best) return { ok: false, reason: 'no_idle' };

    best.target = null;
    best.job = { type: 'worship-goto', deityType: type, target };
    state.active = true;
    state.worshipper = best.i;
    state.mode = 'idle';
    state.time = 0;
    state.site = null;
    state.cooldown = type === 'grande_arvore' ? 1.8 : 2.2;
    return { ok: true, walker: best };
  }

  deactivate(type) {
    const state = this.states[type];
    if (!state) return false;
    const walker = this.world.goblins[state.worshipper];
    if (walker?.job?.deityType === type) {
      walker.job = null;
      walker.wait = 0.3;
      walker.target = null;
    }
    const wasActive = state.active;
    state.active = false;
    state.worshipper = null;
    state.mode = 'idle';
    state.time = 0;
    state.site = null;
    state.launched = false;
    return wasActive;
  }

  releaseByWalker(walker) {
    const type = walker?.job?.deityType;
    return type ? this.deactivate(type) : false;
  }

  isActive(type) { return !!this.states[type]?.active; }

  isPowered(type) {
    const state = this.states[type];
    const walker = state?.active ? this.world.goblins[state.worshipper] : null;
    return !!walker && walker.job?.deityType === type && walker.job.type === 'worship';
  }

  countFor(type) {
    const nodeType = type === 'grande_arvore' ? 'tree' : 'rock';
    return this.nodes.countActive(nodeType);
  }

  status(type) {
    const state = this.states[type];
    return {
      count: this.countFor(type), max: ISLAND_NODE_CAP,
      active: !!state?.active, powered: this.isPowered(type),
      worshipper: state?.worshipper ?? null,
    };
  }

  update(dt) {
    this.clock += dt;
    this.sync();
    this.updateTree(dt);
    this.updateGolem(dt);
    this.updateProjectiles(dt);
  }

  updateTree(dt) {
    const state = this.states.grande_arvore;
    if (!this.isPowered('grande_arvore')) return;

    if (state.mode === 'idle') {
      if (this.countFor('grande_arvore') >= ISLAND_NODE_CAP) return;
      state.cooldown -= dt;
      if (state.cooldown > 0) return;

      const deity = this.village.get('grande_arvore');
      const site = this.nodes.findDivineSite(
        'tree', this.village.structures, this.rng, deity, { minFromOrigin: 210 }
      );
      if (!site) { state.cooldown = 2; return; }
      state.mode = 'chant';
      state.time = 0;
      state.site = site;
      return;
    }

    state.time += dt;
    if (state.time < state.duration) return;

    if (this.countFor('grande_arvore') < ISLAND_NODE_CAP) {
      const node = this.nodes.spawnDivine('tree', state.site);
      if (node) {
        this.world.floats.push({
          x: node.x, y: node.y - 18, ttl: 1.8,
          text: '♬  +1', color: '#8fe06f',
        });
      }
    }
    state.mode = 'idle';
    state.time = 0;
    state.site = null;
    const level = this.village.levelOf('grande_arvore');
    state.cooldown = Math.max(5.2, 9.5 - level * 1.1);
  }

  updateGolem(dt) {
    const state = this.states.golem_pedra;
    if (!this.isPowered('golem_pedra')) return;

    if (state.mode === 'idle') {
      const inFlight = this.projectiles.length;
      if (this.countFor('golem_pedra') + inFlight >= ISLAND_NODE_CAP) return;
      state.cooldown -= dt;
      if (state.cooldown > 0) return;

      const deity = this.village.get('golem_pedra');
      const site = this.nodes.findDivineSite(
        'rock', this.village.structures, this.rng, deity,
        { minFromOrigin: 220, maxFromOrigin: 560 }
      );
      if (!site) { state.cooldown = 2; return; }
      state.mode = 'forge';
      state.time = 0;
      state.site = site;
      state.launched = false;
      return;
    }

    state.time += dt;
    // 28 poses: condensação, levantamento, antecipação e soltura.
    if (!state.launched && state.time >= 1.55) {
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
      const level = this.village.levelOf('golem_pedra');
      state.cooldown = Math.max(5.8, 10.5 - level * 1.2);
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

    for (let i = 0; i < s.level; i++) {
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

module.exports = { Deities, DEITY_TYPES, ISLAND_NODE_CAP, ANIMATION_FRAMES };
