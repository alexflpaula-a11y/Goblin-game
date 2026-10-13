// ============================================================
// battle.js — Combate por turnos (estilo Final Fantasy).
//
// Frente a frente: até 4 goblins da vila × o grupo inimigo (ou o
// Chefe). Por enquanto só existe o ataque normal — as 3 habilidades
// de cada goblin entram numa etapa seguinte.
//
// A lógica é pura (sem canvas). A tela em si é desenhada por
// drawBattle(), para o main.js só precisar encaminhar toques.
// ============================================================
const { getSprite } = require('assetLoader.js');
const gear = require('gear.js');
const inv = require('inventory.js');

const ANIM_FRAMES = { idle: 5, walk: 8, attack: 17, hurt: 17, death: 15 };

const ALLY_SPOTS = [
  { x: 205, y: 224 }, { x: 122, y: 248 },
  { x: 205, y: 288 }, { x: 122, y: 312 },
];
const FOE_SPOTS = [
  { x: 435, y: 224 }, { x: 518, y: 248 },
  { x: 435, y: 288 }, { x: 518, y: 312 },
];
const BOSS_SPOT = { x: 510, y: 236 };

function clamp(v, a, b) { return Math.max(a, Math.min(b, v)); }

function fighterFrom(src, side, index, isBoss) {
  const wolf = src.kind === 'wolf';
  const boss = !!(isBoss || src.isBoss);
  const spot = side === 'ally'
    ? ALLY_SPOTS[index] || ALLY_SPOTS[0]
    : (boss && wolf ? { x: 505, y: index === 0 ? 228 : 310 } : boss ? BOSS_SPOT : (FOE_SPOTS[index] || FOE_SPOTS[0]));
  const hp = src.hp == null ? src.maxHp : src.hp;
  return {
    src,
    side,
    name: src.name,
    kind: src.kind || 'goblin',
    spritePrefix: src.spritePrefix || (wolf ? 'wolf' : null),
    attackKind: src.attackKind || 'melee',
    isBoss: boss,
    poderDestrutivo: src.poderDestrutivo || 3,
    vitalidade: src.vitalidade || 3,
    velocidade: src.velocidade || 3,
    precisao: src.precisao || 3,
    level: src.level || 1,
    maxHp: src.maxHp || (20 + (src.vitalidade || 3) * 4 + (src.level || 1) * 6),
    hp: Math.max(0, hp),
    alive: hp > 0,
    x: spot.x,
    y: spot.y,
    homeX: spot.x,
    homeY: spot.y,
    face: side === 'ally' ? 1 : -1,
    scale: src.scale || (boss ? 2.05 : (wolf ? 1.9 : 1.9)),
    anim: hp > 0 ? 'idle' : 'death',
    frame: hp > 0 ? 0 : ANIM_FRAMES.death - 1,
    animT: 0,
    stun: 0,
    bleed: 0,
  };
}

function hitChance(atk, def) {
  return clamp(0.93 + atk.precisao * 0.006 - def.velocidade * 0.004, 0.88, 0.99);
}

function rollDamage(atk, def, rng) {
  const base = atk.poderDestrutivo * 2.3 + atk.level * 1.4 - def.vitalidade * 0.85;
  const spread = 0.85 + rng() * 0.3;
  const crit = rng() < clamp(atk.precisao * 0.025, 0.04, 0.22);
  const raw = Math.max(1, Math.round(base * spread * (crit ? 1.55 : 1)));
  return { dmg: raw, crit };
}

class Battle {
  constructor({ allies, foes, kind, difficulty, rewards, source, rng, instant, wave, waves, bgKey, twinsBg }) {
    this.kind = kind || 'patrol';
    this.difficulty = difficulty || 1;
    this.rewards = rewards || { gold: 14, goblin_gems: 2 };
    this.source = source || null;
    this.rng = rng || Math.random;
    this.instant = !!instant;
    this.bgKey = bgKey || null;
    this.twinsBg = twinsBg || null;
    this.pendingWaves = [];
    if (waves && waves.length) this.pendingWaves = waves.map((w) => (w || []).slice(0, 4));
    else if (wave && wave.length) this.pendingWaves = [wave.slice(0, 4)];
    this.pendingWave = this.pendingWaves[0] || [];
    this.waveNumber = 1;
    this.totalWaves = 1 + this.pendingWaves.length;
    this.caveDepth = 0;
    this.allies = (allies || []).slice(0, 4).map((g, i) => fighterFrom(g, 'ally', i, false));
    this.foes = (foes || []).slice(0, 4).map((g, i) => fighterFrom(g, 'foe', i, !!g.isBoss || kind === 'boss'));
    this.log = [];
    this.fx = [];
    this.weaponDrops = [];
    this.queue = [];
    this.qIndex = 0;
    this.phase = 'intro'; // intro | ready | anim | enemy | win | lose
    this.anim = null;
    this.wait = 0.55;
    this.current = null;
    this.target = null;
    this.finished = false;
    this.result = null;
    this._rebuildQueue();
    this.current = this.queue[0] || null;
    this._log('batalha');
  }

  living(side) {
    return (side === 'ally' ? this.allies : this.foes).filter((f) => f.alive);
  }

  /** Ordem fixa: GA1, GI1, GA2, GI2, GA3, GI3, GA4, GI4. Mortos/ausentes saem. */
  _slotList() {
    const out = [];
    for (let i = 0; i < 4; i++) {
      out.push(this.allies[i] || null);
      out.push(this.foes[i] || null);
    }
    return out;
  }

  _rebuildQueue() {
    this.queue = this._slotList().filter((f) => f?.alive);
    this.qIndex = Math.max(0, this.queue.indexOf(this.current));
    if (!this.current || !this.current.alive) this.current = this.queue[0] || null;
  }

  chooseTarget(index) {
    if (this.finished) return false;
    const living = this.living('foe');
    const target = living[index] || this.foes[index];
    if (!target?.alive) return false;
    this.target = target;
    return true;
  }

  commandAttack() {
    if (this.phase !== 'ready' || this.current?.side !== 'ally') return false;
    if (!this.target?.alive) return false;
    this._beginAttack(this.current, this.target);
    return true;
  }

  _beginAttack(atk, def) {
    this.phase = 'anim';
    this.anim = { kind: 'attack', atk, def, t: 0, resolved: false, hits: 0, strikes: 0,
      double: atk.src?.equip?.arma_primaria === 'manoplas_lobo' };
    atk.anim = this.instant ? 'attack' : 'walk'; atk.frame = 0; atk.animT = 0;
    if (this.instant) {
      this._strike();
      if (this.anim.double) this._strike();
    }
  }

  _bleedAfterAttack(f) {
    if (!f.alive || f.bleed <= 0) return;
    // Once per attack action (not per hit of the gauntlet combo), even on a miss.
    const dmg = Math.ceil(f.maxHp * 0.10);
    f.bleed -= 1;
    f.hp = Math.max(0, f.hp - dmg);
    if (f.src) f.src.hp = f.hp;
    this.fx.push({ kind: 'dmg', x: f.x, y: f.y - 34, text: String(dmg), ttl: 0.9 });
    this._log('bleed_tick', { name: f.name, dmg });
    if (!f.hp) {
      this._dropWeapons(f); f.alive = false; f.anim = 'death'; f.frame = 0; f.animT = 0;
      this._log('down', { name: f.name });
    }
  }

  _strike() {
    const a = this.anim;
    if (!a) return;
    a.strikes += 1;
    if (this._resolveAttack(a.atk, a.def)) a.hits += 1;
    if (a.double && a.strikes === 2 && a.hits === 2 && a.def.alive) {
      a.def.stun = Math.max(1, a.def.stun);
      this._log('stun', { name: a.def.name });
    }
  }

  _resolveAttack(atk, def) {
    if (this.anim) this.anim.resolved = true;
    if (!atk?.alive || !def?.alive) return false;
    const hit = this.rng() <= hitChance(atk, def);
    if (!hit) {
      this._log('miss', { name: atk.name, target: def.name });
      this.fx.push({ kind: 'miss', x: def.x, y: def.y - 36, ttl: 0.8 });
      return false;
    }
    const { dmg, crit } = rollDamage(atk, def, this.rng);
    def.hp = Math.max(0, def.hp - dmg);
    if (def.src) def.src.hp = def.hp;
    def.anim = 'hurt'; def.frame = 0; def.animT = 0;
    this.fx.push({
      kind: 'dmg', x: def.x, y: def.y - 34, text: String(dmg),
      crit, ttl: 0.9,
    });
    this._log(crit ? 'crit' : 'hit', { name: atk.name, target: def.name, dmg });
    if (atk.attackKind === 'bite') {
      def.bleed = Math.max(def.bleed || 0, 3);
      this._log('bleed', { name: def.name });
    } else if (atk.attackKind === 'slash') {
      def.stun = Math.max(def.stun || 0, 1);
      this._log('stun', { name: def.name });
    }
    if (def.hp <= 0) {
      this._dropWeapons(def);
      def.alive = false;
      def.hp = 0;
      if (def.src) def.src.hp = 0;
      def.anim = 'death'; def.frame = 0; def.animT = 0;
      this._log('down', { name: def.name });
      if (def.side === 'foe') this.lastDefeated = { x: def.homeX, y: def.homeY };
    }
    return true;
  }

  _dropWeapons(f) {
    if (f.weaponsDropped || f.side !== 'ally') return;
    f.weaponsDropped = true;
    const equip = f.src.equip || {};
    const ids = new Set(['arma_primaria', 'arma_secundaria'].map((k) => equip[k]).filter(Boolean));
    for (const id of ids) {
      const item = inv.byId(id);
      this.weaponDrops.push({ id, icon: item?.ground || item?.icon, x: f.homeX + 18, y: f.homeY + 8, claimed: false });
    }
    delete equip.arma_primaria; delete equip.arma_secundaria;
  }

  recoverWeapons(village) {
    for (const d of this.weaponDrops) if (!d.claimed) { village.addItem(d.id, 1); d.claimed = true; }
  }

  _syncHp() {
    for (const f of this.allies) {
      if (f.src) f.src.hp = Math.max(0, f.hp);
    }
  }

  _spawnPendingWave() {
    if (!this.pendingWaves?.length) return false;
    const members = this.pendingWaves.shift();
    this.pendingWave = this.pendingWaves[0] || [];
    this.waveNumber += 1;
    if (this.twinsBg && members.some((m) => m.attackKind === 'bite' || m.attackKind === 'slash' || (m.spritePrefix || '').startsWith('twin'))) {
      this.bgKey = this.twinsBg;
    }
    this.foes = members.slice(0, 4).map((g, i) => fighterFrom(g, 'foe', i, !!g.isBoss));
    this.target = null;
    this.anim = null;
    this.current = null;
    this._rebuildQueue();
    this.current = this.queue[0] || null;
    if (this.instant) {
      this.phase = 'intro';
      this.wait = 0;
      this._log('wave');
    } else {
      this.phase = 'advance';
      this.advanceT = 0;
      for (const f of this.foes) { f.x = f.homeX + 80; f.anim = 'walk'; }
    }
    return true;
  }

  _checkEnd() {
    if (!this.instant && (!this.living('ally').length || !this.living('foe').length)
      && [...this.allies, ...this.foes].some((f) => !f.alive && f.anim === 'death' && f.frame < ANIM_FRAMES.death - 1)) {
      this.phase = 'settling'; // Show the entire fall before a wave/chest replaces it.
      return true;
    }
    if (!this.living('ally').length) {
      this.phase = 'lose'; this.finished = true; this.result = 'lose';
      this._syncHp(); this._log('lose'); return true;
    }
    if (!this.living('foe').length) {
      if (this._spawnPendingWave()) return true;
      this.phase = 'win';
      this.finished = true;
      this.result = 'win';
      this._syncHp();
      this._log('win');
      return true;
    }
    if (!this.living('ally').length) {
      this.phase = 'lose';
      this.finished = true;
      this.result = 'lose';
      this._syncHp();
      this._log('lose');
      return true;
    }
    return false;
  }

  _nextTurn() {
    for (let guard = 0; guard < 12; guard++) {
      if (this._checkEnd()) return;
      const slots = this._slotList();
      let i = slots.indexOf(this.current);
      if (i < 0) i = this.current?.introSentinel ? 7 : 0;
      let next = null;
      for (let k = 1; k <= slots.length; k++) {
        const f = slots[(i + k) % slots.length];
        if (f?.alive) { next = f; break; }
      }
      this.current = next;
      if (this.target && !this.target.alive) this.target = null;
      this._rebuildQueue();
      if (!this.current) { this._checkEnd(); return; }

      if (this.current.stun > 0) {
        this.current.stun -= 1;
        this._log('stunned', { name: this.current.name });
        continue;
      }
      if (this.current.side === 'ally') {
        this.phase = 'ready';
      } else {
        this.phase = 'enemy';
        this.wait = this.instant ? 0 : 0.45;
        if (this.instant) this._enemyAttack();
      }
      return;
    }
  }

  _enemyAttack() {
    const atk = this.current;
    const living = this.living('ally');
    if (!atk?.alive || !living.length) { this._nextTurn(); return; }
    living.sort((a, b) => a.hp - b.hp);
    const def = this.rng() < 0.65 ? living[0] : living[Math.floor(this.rng() * living.length)];
    this._beginAttack(atk, def);
  }

  update(dt) {
    for (const f of [...this.allies, ...this.foes]) this._tickAnim(f, dt);
    for (const fx of this.fx) fx.ttl -= dt;
    this.fx = this.fx.filter((fx) => fx.ttl > 0);

    if (this.phase === 'settling') { this._nextTurn(); return; }

    if (this.phase === 'advance') {
      this.advanceT = (this.advanceT || 0) + dt;
      const k = Math.min(1, this.advanceT / 1.6);
      this.caveDepth = (this.waveNumber - 2 + k) * 80;
      for (const f of this.allies) {
        if (!f.alive) continue;
        f.anim = 'walk';
        f.x = f.homeX; // Camera tracks the marching party; cave scrolls left.
      }
      for (const f of this.foes) {
        f.x = f.homeX + 80 * (1 - k);
        f.anim = k < 1 ? 'walk' : 'idle';
      }
      if (k >= 1) {
        for (const f of this.allies) {
          f.x = f.homeX;
          if (f.alive) { f.anim = 'idle'; f.frame = 0; }
        }
        for (const f of this.foes) { f.x = f.homeX; f.anim = 'idle'; f.frame = 0; }
        this.phase = 'intro';
        this.wait = this.instant ? 0 : 0.3;
        this._log('wave');
      }
      return;
    }

    if (this.phase === 'intro') {
      this.wait -= dt;
      if (this.wait <= 0) {
        this.current = this._slotList()[7];
        // Start at GA1, applying stun just like any other turn.
        if (!this.current) this.current = { introSentinel: true };
        this._nextTurn();
      }
      return;
    }

    if (this.phase === 'enemy') {
      this.wait -= dt;
      if (this.wait <= 0) this._enemyAttack();
      return;
    }

    if (this.phase === 'anim' && this.anim) {
      const a = this.anim;
      a.t += dt;
      const atk = a.atk;
      const def = a.def;
      const gap = atk.kind === 'wolf' || def.kind === 'wolf' ? 52 : 30;
      const contactX = def.homeX - Math.sign(def.homeX - atk.homeX) * gap;
      const strikeAt = this.instant ? 0.42 : 0.54;
      const secondAt = this.instant ? 0.78 : 1.22;
      const contactEnd = this.instant ? (a.double ? 1.06 : 0.72) : (a.double ? 1.70 : 1.02);
      let mix = 0;
      if (a.t < 0.34) {
        mix = a.t / 0.34;
        if (atk.anim !== 'walk') { atk.anim = 'walk'; atk.frame = 0; }
      } else if (a.t < contactEnd) {
        mix = 1;
        if (atk.anim !== 'attack') { atk.anim = 'attack'; atk.frame = 0; atk.animT = 0; }
      } else {
        mix = Math.max(0, 1 - (a.t - contactEnd) / 0.28);
        if (atk.alive && atk.anim !== 'walk') { atk.anim = 'walk'; atk.frame = 0; }
      }
      if (!this.instant && atk.anim === 'attack') atk.frame = Math.min(16, Math.floor(((a.t - 0.34) % 0.68) / 0.04));
      atk.x = atk.homeX + (contactX - atk.homeX) * mix;
      atk.y = atk.homeY + (def.homeY - atk.homeY) * mix;
      if (a.strikes === 0 && a.t >= strikeAt) this._strike();
      if (a.double && a.strikes === 1 && a.t >= secondAt) {
        if (this.instant) { atk.frame = 0; atk.animT = 0; }
        this._strike();
      }
      if (a.t >= (this.instant ? 0.72 : contactEnd + 0.30)) {
        atk.x = atk.homeX; atk.y = atk.homeY;
        if (atk.alive) { atk.anim = 'idle'; atk.frame = 0; }
        this._bleedAfterAttack(atk);
        this.anim = null;
        this._nextTurn();
      }
    }
  }

  _tickAnim(f, dt) {
    const frames = ANIM_FRAMES[f.anim] || 5;
    const step = f.anim === 'idle' ? 0.18 : f.anim === 'walk' ? 0.10 : 0.07;
    f.animT += dt;
    const advance = Math.floor(f.animT / step);
    if (!advance) return;
    f.animT -= advance * step;
    if (f.anim === 'death') {
      f.frame = Math.min(frames - 1, f.frame + advance);
      return;
    }
    const complete = f.frame + advance >= frames;
    f.frame = (f.frame + advance) % frames;
    if (f.anim === 'hurt' && complete) f.anim = f.alive ? 'idle' : 'death';
    if (f.anim === 'attack' && complete && this.phase !== 'anim') f.anim = 'idle';
  }

  _log(kind, params) {
    this.log.push({ kind, params: params || {}, t: 0 });
    if (this.log.length > 8) this.log.shift();
  }
}

function drawFighter(ctx, f, time, highlight) {
  const wolf = f.kind === 'wolf' || f.src?.kind === 'wolf';
  ctx.fillStyle = 'rgba(0,0,0,0.28)';
  ctx.beginPath(); ctx.ellipse(f.x, f.y + 2, (wolf ? 19 : 10) * f.scale, 4, 0, 0, Math.PI * 2); ctx.fill();
  ctx.save();
  ctx.translate(f.x, f.y);
  ctx.scale(f.face * f.scale, f.scale);
  ctx.imageSmoothingEnabled = false;
  if (wolf) {
    const prefix = f.spritePrefix || f.src?.spritePrefix || 'wolf';
    const n = ANIM_FRAMES[f.anim] || 5;
    const spr = getSprite(prefix + '_' + f.anim + '_' + (f.frame % n));
    const twin = prefix.startsWith('twin');
    const w = twin ? 56 : 48, h = twin ? 36 : 32;
    ctx.drawImage(spr, -w / 2, -h + 2, w, h);
  } else {
    const spr = getSprite(gear.spriteForGoblin(f.src, f.anim, f.frame % (ANIM_FRAMES[f.anim] || 1)));
    if (f.side === 'foe') {
      ctx.filter = f.isBoss ? 'hue-rotate(-10deg) saturate(1.25)' : 'hue-rotate(-20deg) saturate(1.15)';
    }
    ctx.drawImage(spr, -16, -30, 32, 32);
    ctx.filter = 'none';
  }
  ctx.restore();

  const bw = f.isBoss ? 42 : 28;
  ctx.fillStyle = 'rgba(0,0,0,0.55)';
  ctx.fillRect(f.x - bw / 2, f.y - 38 * f.scale, bw, 4);
  ctx.fillStyle = f.side === 'ally' ? '#4fa562' : '#d45b4a';
  ctx.fillRect(f.x - bw / 2, f.y - 38 * f.scale, bw * (f.hp / Math.max(1, f.maxHp)), 4);
  ctx.fillStyle = highlight ? '#ffe9a8' : '#efeafd';
  ctx.font = `bold ${f.isBoss ? 9 : 8}px monospace`;
  ctx.textAlign = 'center';
  ctx.fillText(f.name, f.x, f.y - 42 * f.scale);
  if (f.bleed > 0) {
    ctx.fillStyle = '#d4452f';
    ctx.fillText('+', f.x + 16, f.y - 48 * f.scale);
  }
  if (f.stun > 0) {
    ctx.fillStyle = '#ffe14a';
    ctx.fillText('*', f.x - 18, f.y - 48 * f.scale);
  }
  ctx.textAlign = 'left';
}

function drawBattleBackdrop(ctx, bg) {
  if (bg?.image) {
    ctx.imageSmoothingEnabled = false;
    try {
      const shift = (bg.depth || 0) % 640;
      const image = getSprite(bg.image);
      ctx.drawImage(image, -shift, 0, 640, 360);
      if (shift) ctx.drawImage(image, 640 - shift, 0, 640, 360);
    }
    catch (e) { ctx.fillStyle = '#1a1410'; ctx.fillRect(0, 0, 640, 360); }
    return;
  }
  if (bg?.terrain) {
    const zoom = 2.6;
    const vw = 640 / zoom, vh = 360 / zoom;
    const sx = Math.max(0, (bg.x || 320) - vw / 2);
    const sy = Math.max(0, (bg.y || 180) - vh / 2);
    try {
      ctx.drawImage(bg.terrain, sx, sy, vw, vh, 0, 0, 640, 360);
    } catch (e) {
      ctx.fillStyle = '#163528';
      ctx.fillRect(0, 0, 640, 360);
    }
    ctx.fillStyle = 'rgba(10, 18, 14, 0.28)';
    ctx.fillRect(0, 0, 640, 360);
    return;
  }
  const g = ctx.createLinearGradient?.(0, 0, 0, 360);
  if (g) { g.addColorStop(0, '#1a1630'); g.addColorStop(1, '#0c1c18'); ctx.fillStyle = g; }
  else ctx.fillStyle = '#141022';
  ctx.fillRect(0, 0, 640, 360);
  ctx.fillStyle = '#163528';
  ctx.beginPath();
  ctx.ellipse(320, 300, 280, 70, 0, 0, Math.PI * 2);
  ctx.fill();
}

function drawSlider(ui, ctx, id, x, y, w, value, label) {
  ui.text(x, y - 4, label, { size: 9, color: '#ffe9a8' });
  ctx.fillStyle = 'rgba(0,0,0,0.45)';
  ctx.fillRect(x, y, w, 10);
  ctx.fillStyle = '#4fa562';
  ctx.fillRect(x, y, w * Math.max(0, Math.min(1, value)), 10);
  ctx.strokeStyle = 'rgba(255,233,168,0.55)';
  ctx.strokeRect(x + 0.5, y + 0.5, w - 1, 9);
  const kx = x + w * Math.max(0, Math.min(1, value));
  ctx.fillStyle = '#ffe9a8';
  ctx.fillRect(kx - 3, y - 2, 6, 14);
  ui.region(id, x, y - 6, w, 22);
}

function drawBattle(ctx, ui, battle, i18n, time, view) {
  view = view || {};
  drawBattleBackdrop(ctx, { ...(view.bg || {}), image: battle.bgKey || view.bg?.image, depth: battle.caveDepth });

  if (battle.bgKey) ui.text(320, 44, `${battle.foes.some((f) => f.isBoss && f.kind === 'wolf') ? i18n.t('ui.war_twins') : i18n.t('ui.den_title')} · ${battle.waveNumber}/${battle.totalWaves}`, { align: 'center', size: 11, color: '#ffe9a8' });
  for (const d of battle.weaponDrops) {
    if (d.claimed) continue;
    const y = d.y - 8 + Math.sin(time * 3) * 3;
    ctx.fillStyle = 'rgba(60,170,255,0.3)'; ctx.beginPath(); ctx.ellipse(d.x, y, 19, 12, 0, 0, Math.PI * 2); ctx.fill();
    ctx.fillStyle = '#9ceaff'; ctx.fillRect(d.x + 13, y - 13, 2, 2);
    ctx.drawImage(getSprite(d.icon), d.x - 12, y - 12, 24, 24);
  }
  const current = battle.current;
  const fighters = [...battle.foes, ...battle.allies].sort((a, b) => a.y - b.y);
  for (const f of fighters) {
    drawFighter(ctx, f, time, (current === f || battle.target === f) && !battle.finished);
  }

  if (!battle.finished && !view.menu) {
    battle.living('foe').forEach((f, i) => {
      const selected = battle.target === f;
      const pulse = 0.45 + Math.sin(time * 6) * 0.25;
      ctx.strokeStyle = selected
        ? `rgba(255, 210, 80, ${0.7 + pulse * 0.3})`
        : `rgba(255, 120, 90, ${pulse})`;
      ctx.lineWidth = selected ? 3 : 2;
      ctx.beginPath(); ctx.arc(f.x, f.y - 16, selected ? 24 : 22, 0, Math.PI * 2); ctx.stroke();
      const halfWidth = (f.kind === 'wolf' ? 26 : 16) * f.scale;
      const height = 34 * f.scale;
      ui.region('battle_tgt_' + i, f.x - halfWidth, f.y - height, halfWidth * 2, height + 8);
    });
  }

  for (const fx of battle.fx) {
    ctx.globalAlpha = Math.max(0, Math.min(1, fx.ttl * 1.4));
    ctx.textAlign = 'center';
    ctx.font = `bold ${fx.crit ? 14 : 11}px monospace`;
    ctx.fillStyle = fx.kind === 'miss' ? '#cdd3de' : (fx.crit ? '#ffe14a' : '#ffd0c8');
    ctx.fillText(fx.kind === 'miss' ? i18n.t('ui.battle_miss') : (fx.crit ? '★' + fx.text : fx.text), fx.x, fx.y - (0.9 - fx.ttl) * 18);
    ctx.globalAlpha = 1;
    ctx.textAlign = 'left';
  }

  ui.woodSign(8, 8, 210, 22, i18n.t('ui.battle_title'), 11);

  const last = battle.log[battle.log.length - 1];
  if (last && last.kind !== 'batalha') {
    let line = '';
    if (last.kind === 'hit' || last.kind === 'crit') {
      line = i18n.t('ui.battle_dmg', { name: last.params.name, target: last.params.target, dmg: last.params.dmg });
    } else if (last.kind === 'miss') line = i18n.t('ui.battle_miss_log', { name: last.params.name });
    else if (last.kind === 'down') line = i18n.t('ui.battle_down', { name: last.params.name });
    else if (last.kind === 'wave') line = i18n.t('ui.battle_wave');
    else if (last.kind === 'bleed') line = i18n.t('ui.battle_bleed', { name: last.params.name });
    else if (last.kind === 'stun') line = i18n.t('ui.battle_stun', { name: last.params.name });
    else if (last.kind === 'stunned') line = i18n.t('ui.battle_stunned', { name: last.params.name });
    else if (last.kind === 'bleed_tick') line = i18n.t('ui.battle_bleed_tick', { name: last.params.name, dmg: last.params.dmg });
    if (line) ui.text(228, 18, line, { size: 9, color: '#ffe9a8' });
  }

  // Engrenagem de configurações no topo.
  ctx.fillStyle = 'rgba(20,14,10,0.72)';
  ctx.fillRect(598, 6, 34, 26);
  ctx.strokeStyle = '#e8b23a';
  ctx.strokeRect(598.5, 6.5, 33, 25);
  ui.text(615, 20, '⚙', { align: 'center', size: 14, color: '#ffe9a8' });
  if (!view.menu) ui.region('battle_settings', 598, 6, 34, 26);

  const bri = view.brightness == null ? 1 : view.brightness;
  if (bri < 0.98) {
    ctx.fillStyle = `rgba(0,0,0,${Math.max(0, Math.min(0.72, 1 - bri))})`;
    ctx.fillRect(0, 0, 640, 360);
  } else if (bri > 1.02) {
    ctx.fillStyle = `rgba(255,245,210,${Math.min(0.28, (bri - 1) * 0.4)})`;
    ctx.fillRect(0, 0, 640, 360);
  }

  if (view.reward) return;
  if (battle.phase === 'win' || battle.phase === 'lose') {
    const win = battle.phase === 'win';
    ui.rusticPanel(170, 88, 300, 168);
    ui.woodSign(186, 100, 268, 24, i18n.t(win ? 'ui.battle_win' : 'ui.battle_lose'), 13);
    if (win) {
      ui.text(320, 148, `+${battle.rewards.gold} ${i18n.t('res.gold')}`, { align: 'center', size: 12, bold: true, color: '#ffe9a8' });
      ui.text(320, 168, `+${battle.rewards.goblin_gems} ${i18n.t('res.goblin_gems')}`, { align: 'center', size: 12, bold: true, color: '#7bd88f' });
    } else {
      ui.text(320, 158, i18n.t('ui.battle_lose_hint'), { align: 'center', size: 10, color: '#e8d5a8' });
    }
    ui.button('battle_continue', 230, 200, 180, 32, i18n.t('ui.battle_continue'), true, true);
    return;
  }

  // Botão de ataque: só dispara no alvo já escolhido.
  if (!view.menu && battle.phase === 'ready' && current?.side === 'ally') {
    ui.text(86, 318, i18n.t('ui.battle_turn', { name: current.name }),
      { align: 'center', size: 9, color: '#ffe9a8' });
    const canHit = !!battle.target?.alive;
    ctx.fillStyle = 'rgba(20,14,10,0.72)';
    ctx.fillRect(12, 268, 56, 56);
    ctx.strokeStyle = canHit ? '#e8b23a' : '#6a5a40';
    ctx.lineWidth = 2;
    ctx.strokeRect(13, 269, 54, 54);
    ctx.imageSmoothingEnabled = false;
    ctx.globalAlpha = canHit ? 1 : 0.45;
    ctx.drawImage(getSprite('ui_attack_sword'), 16, 272, 48, 48);
    ctx.globalAlpha = 1;
    ui.region('battle_attack', 12, 268, 56, 56);
    ui.text(40, 332, i18n.t('ui.battle_attack'), { align: 'center', size: 8, color: canHit ? '#ffe9a8' : '#8a8798' });
    ui.text(320, 336, i18n.t(canHit ? 'ui.battle_use' : 'ui.battle_pick'),
      { align: 'center', size: 10, bold: true, color: canHit ? '#9ff0a9' : '#ffcf5c' });
  }

  if (view.menu === 'settings') {
    ui.rusticPanel(150, 52, 340, 256);
    ui.woodSign(166, 64, 308, 24, i18n.t('ui.battle_settings'), 12);
    ui.closeX('battle_settings_close', 454, 62);
    drawSlider(ui, ctx, 'vol_bar', 186, 118, 268, view.volume ?? 0.7, i18n.t('ui.battle_volume'));
    drawSlider(ui, ctx, 'bri_bar', 186, 158, 268, ((view.brightness ?? 1) - 0.4) / 0.8, i18n.t('ui.battle_brightness'));
    ui.button('battle_menu', 186, 186, 268, 30, i18n.t('ui.battle_menu'), true);
    ui.button('battle_forfeit', 186, 224, 268, 30, i18n.t('ui.battle_forfeit'), true);
    ui.button('battle_settings_close', 230, 262, 180, 28, i18n.t('ui.close'), true);
  } else if (view.menu === 'confirm_menu' || view.menu === 'confirm_forfeit') {
    const forfeit = view.menu === 'confirm_forfeit';
    ui.rusticPanel(150, 88, 340, 176);
    ui.woodSign(166, 100, 308, 24, i18n.t(forfeit ? 'ui.battle_forfeit' : 'ui.battle_menu'), 12);
    ui.text(320, 148, i18n.t(forfeit ? 'ui.battle_confirm_forfeit' : 'ui.battle_confirm_menu'),
      { align: 'center', size: 10, color: '#e8d5a8' });
    ui.button(forfeit ? 'battle_forfeit_yes' : 'battle_menu_yes', 176, 188, 140, 32, i18n.t('ui.yes'), true, true);
    ui.button('battle_confirm_no', 324, 188, 140, 32, i18n.t('ui.no'), true);
  }
}

module.exports = {
  Battle, drawBattle, hitChance, rollDamage,
  ALLY_SPOTS, FOE_SPOTS,
};
