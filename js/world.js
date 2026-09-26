// ============================================================
// world.js — A grande ilha (geração procedural + terreno
// pré-renderizado) e os goblins que passeiam por ela.
// ============================================================
const { getSprite } = require('assetLoader.js');
const gear = require('gear.js');
const WORLD = {
  TILE: 16,
  COLS: 120,
  ROWS: 90,
  get W() { return this.COLS * this.TILE; },  // 1920
  get H() { return this.ROWS * this.TILE; },  // 1440
};

// Tipos de tile
const DEEP = 0, WATER = 1, SAND = 2, GRASS = 3, ROCK = 4;

const COLORS = {
  [DEEP]: '#143a5c',
  [WATER]: '#1d5c8f',
  [SAND]: '#e8d293',
  [ROCK]: '#7d8291',
  grassShades: ['#418f52', '#489a58', '#3b8449'],
  clearing: '#5aa463',
  wetSand: '#c9b57f',
  tuft: '#2f6b3c',
  flowers: ['#e86a6a', '#e8d06a', '#d98ae8'],
  rockDark: '#6a6f7d',
};

// ---------- RNG + noise ----------
function mulberry32(seed) {
  let a = seed >>> 0;
  return function () {
    a |= 0; a = (a + 0x6D2B79F5) | 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

function hash2(x, y, seed) {
  let h = seed ^ (x * 374761393) ^ (y * 668265263);
  h = (h ^ (h >>> 13)) * 1274126177;
  return ((h ^ (h >>> 16)) >>> 0) / 4294967296;
}

function makeNoise(seed, cell) {
  const rnd = mulberry32(seed);
  const gw = Math.ceil(WORLD.COLS / cell) + 3;
  const gh = Math.ceil(WORLD.ROWS / cell) + 3;
  const g = new Float32Array(gw * gh);
  for (let i = 0; i < g.length; i++) g[i] = rnd();
  const smooth = (t) => t * t * (3 - 2 * t);
  return (x, y) => {
    const fx = x / cell, fy = y / cell;
    const x0 = Math.floor(fx), y0 = Math.floor(fy);
    const tx = smooth(fx - x0), ty = smooth(fy - y0);
    const at = (gx, gy) => g[Math.max(0, Math.min(gh - 1, gy)) * gw + Math.max(0, Math.min(gw - 1, gx))];
    const a = at(x0, y0), b = at(x0 + 1, y0), c = at(x0, y0 + 1), d = at(x0 + 1, y0 + 1);
    return (a + (b - a) * tx) * (1 - ty) + (c + (d - c) * tx) * ty;
  };
}

// Quantos quadros cada animação realmente tem no atlas de sprites.
// Usado para nunca pedir um quadro que não existe (ex.: sair do 'walk'
// no quadro 7 e cair no 'idle', que só vai até 4) — o que fazia aparecer
// o placeholder "VAR" piscando entre uma ação e outra.
const ANIM_FRAMES = { idle: 5, walk: 8, attack: 17, hurt: 17, death: 15 };

// ---------- Goblin que passeia / trabalha ----------
class GoblinWalker {
  constructor(x, y, clearing) {
    this.x = x; this.y = y;
    this.i = 0;               // índice no roster da vila
    this.clearing = clearing; // {x, y, r}
    this.target = null;
    this.wait = Math.random() * 1.5;
    this.face = 1;
    this.anim = 'idle';
    this.frame = 0;
    this.animT = 0;
    this.speed = 26 + Math.random() * 10;
    this.job = null;          // {type:'goto'|'work', node}
    this.cycle = 0;
  }

  pickTarget() {
    const a = Math.random() * Math.PI * 2;
    const r = Math.sqrt(Math.random()) * this.clearing.r;
    this.target = { x: this.clearing.x + Math.cos(a) * r, y: this.clearing.y + Math.sin(a) * r * 0.7 };
  }

  update(dt, api = {}) {
    // qual goblin do roster este walker representa (p/ vestir o equip dele)
    this.goblin = api.village?.goblins?.[this.i] ?? this.goblin ?? null;

    // ----- construindo / melhorando uma estrutura -----
    if (this.job?.construction) {
      const structure = this.job.construction;
      const work = structure?.construction;
      // Se a obra já foi recolhida/concluída ou ganhou outro construtor,
      // este goblin volta a ficar disponível sem deixar referências órfãs.
      if (!work || work.status !== 'building' || work.worker !== this.i) {
        if (work?.worker === this.i) work.working = false;
        this.job = null; this.wait = 0.35;
      } else if (this.job.type === 'build-goto') {
        const target = { x: structure.x - 15, y: structure.y + 4 };
        const dx = target.x - this.x, dy = target.y - this.y;
        const dist = Math.hypot(dx, dy);
        if (dist < 3) {
          this.x = target.x; this.y = target.y;
          this.face = 1;
          this.job.type = 'build';
          work.working = true;
          this.anim = 'attack'; this.frame = 0; this.animT = 0;
        } else {
          this.x += (dx / Math.max(0.001, dist)) * this.speed * 1.25 * dt;
          this.y += (dy / Math.max(0.001, dist)) * this.speed * 1.25 * dt;
          this.face = dx >= 0 ? 1 : -1;
          this.anim = 'walk';
          this.animT += dt;
          if (this.animT > 0.10) { this.animT = 0; this.frame = (this.frame + 1) % 8; }
        }
        return;
      } else {
        // Martela na frente da lona; o controlador principal desconta o
        // relógio para que Village continue sendo a dona do estado da obra.
        this.x = structure.x - 15; this.y = structure.y + 4;
        this.face = 1;
        this.anim = 'attack';
        this.animT += dt;
        if (this.animT > 0.09) { this.animT = 0; this.frame = (this.frame + 1) % 10; }
        api.onBuild?.(structure, this.goblin, dt);
        if (structure.construction?.status !== 'building') {
          if (structure.construction) structure.construction.working = false;
          this.job = null; this.wait = 0.45;
        }
        return;
      }
    }

    // ----- louvando uma divindade (ativação manual) -----
    if (this.job?.deityType) {
      const target = this.job.target;
      if (this.job.type === 'worship-goto') {
        const dx = target.x - this.x, dy = target.y - this.y;
        const dist = Math.hypot(dx, dy);
        if (dist < 3) {
          this.x = target.x; this.y = target.y;
          this.face = target.face;
          this.job.type = 'worship';
          this.anim = 'idle'; this.frame = 0; this.animT = 0;
        } else {
          this.x += (dx / Math.max(0.001, dist)) * this.speed * 1.3 * dt;
          this.y += (dy / Math.max(0.001, dist)) * this.speed * 1.3 * dt;
          this.face = dx >= 0 ? 1 : -1;
          this.anim = 'walk';
          this.animT += dt;
          if (this.animT > 0.09) { this.animT = 0; this.frame = (this.frame + 1) % 8; }
        }
      } else {
        // Reverência em 12 poses por ciclo usando os quadros idle existentes.
        this.x = target.x; this.y = target.y; this.face = target.face;
        this.anim = 'idle';
        this.animT += dt;
        if (this.animT > 0.12) { this.animT = 0; this.frame = (this.frame + 1) % 12; }
      }
      return;
    }

    // ----- trabalhando -----
    if (this.job) {
      const node = this.job.node;
      if (!node || node.depleted) {
        if (node) node.worker = null;
        this.job = null; this.wait = 0.4;
      }
      else if (this.job.type === 'goto') {
        const dx = node.x - this.x, dy = (node.y + 6) - this.y;
        const dist = Math.hypot(dx, dy);
        if (dist < 3) { this.job.type = 'work'; this.cycle = 0; }
        else {
          this.x += (dx / dist) * this.speed * 1.3 * dt;
          this.y += (dy / dist) * this.speed * 1.3 * dt;
          this.face = dx >= 0 ? 1 : -1;
          this.anim = 'walk';
          this.animT += dt;
          if (this.animT > 0.11) { this.animT = 0; this.frame = (this.frame + 1) % 8; }
        }
        return;
      } else { // work
        this.anim = 'attack';
        this.face = node.x >= this.x ? 1 : -1;
        this.animT += dt;
        if (this.animT > 0.09) { this.animT = 0; this.frame = (this.frame + 1) % 10; }
        const g = api.village?.goblins?.[this.i];
        // velocidade e força aceleram o ciclo de trabalho
        const mul = g ? Math.max(0.4, 1 - (g.velocidade + g.poderDestrutivo) / 80) : 1;
        this.cycle += dt;
        const period = (api.workPeriod || 1.2) * mul;
        this.jobProgress = Math.min(1, this.cycle / period);
        if (this.cycle >= period) {
          this.cycle = 0;
          this.jobProgress = 0;
          api.onChop?.(node, g);
          if (node.depleted) { this.job = null; this.wait = 0.4; }
        }
        return;
      }
    }

    // ----- passeando -----
    if (this.wait > 0) {
      this.wait -= dt;
      this.anim = 'idle';
      this.animT += dt;
      if (this.animT > 0.22) { this.animT = 0; this.frame = (this.frame + 1) % 5; }
      if (this.wait <= 0) this.pickTarget();
      return;
    }
    if (!this.target) this.pickTarget();
    const dx = this.target.x - this.x, dy = this.target.y - this.y;
    const dist = Math.hypot(dx, dy);
    if (dist < 2) {
      this.target = null;
      this.wait = 0.6 + Math.random() * 2.2;
      return;
    }
    this.x += (dx / dist) * this.speed * dt;
    this.y += (dy / dist) * this.speed * dt;
    this.face = dx >= 0 ? 1 : -1;
    this.anim = 'walk';
    this.animT += dt;
    if (this.animT > 0.11) { this.animT = 0; this.frame = (this.frame + 1) % 8; }
  }

  draw(ctx) {
    // sombra
    ctx.fillStyle = 'rgba(0,0,0,0.28)';
    ctx.beginPath();
    ctx.ellipse(this.x, this.y + 1, 8, 3.5, 0, 0, Math.PI * 2);
    ctx.fill();
    // barra de progresso do ciclo de trabalho
    if (this.job?.type === 'work' && this.jobProgress != null) {
      ctx.fillStyle = 'rgba(0,0,0,0.55)';
      ctx.fillRect(this.x - 9, this.y - 40, 18, 3);
      ctx.fillStyle = '#e8b23a';
      ctx.fillRect(this.x - 9, this.y - 40, 18 * this.jobProgress, 3);
    }
    // sprite (ancorado pelos pés), espelhado quando olha p/ esquerda.
    // O quadro é limitado à quantidade real da animação atual, pois
    // this.frame é compartilhado entre animações de tamanhos diferentes.
    const frame = this.frame % (ANIM_FRAMES[this.anim] || 1);
    const spr = getSprite(gear.spriteForGoblin(this.goblin, this.anim, frame));
    const worship = this.job?.type === 'worship';
    const worshipPhase = (this.frame % 12) / 12 * Math.PI * 2;
    ctx.save();
    ctx.translate(this.x, this.y);
    const bow = worship ? 0.76 + Math.abs(Math.sin(worshipPhase)) * 0.10 : 1;
    ctx.scale(this.face, bow);
    ctx.rotate(worship ? Math.sin(worshipPhase) * 0.035 * this.face : 0);
    ctx.drawImage(spr, -16, -30, 32, 32);
    ctx.restore();
    if (worship) {
      ctx.save();
      ctx.globalAlpha = 0.58 + Math.sin(worshipPhase) * 0.22;
      ctx.fillStyle = this.job.deityType === 'grande_arvore' ? '#b7ef78' : '#f1c85a';
      ctx.font = 'bold 9px monospace';
      ctx.textAlign = 'center';
      ctx.fillText('✦', this.x, this.y - 34 - Math.abs(Math.sin(worshipPhase)) * 3);
      ctx.restore();
    }
  }
}

// ---------- Mundo ----------
class World {
  constructor(seed = 7) {
    this.seed = seed;
    this.tiles = new Uint8Array(WORLD.COLS * WORLD.ROWS);
    this.centerX = WORLD.W / 2;
    this.centerY = WORLD.H / 2;
    this.clearing = { x: this.centerX, y: this.centerY, r: 10 * WORLD.TILE };
    this.floats = [];
    this.generate();
    this.prerender();
    this.goblins = [];
    this.setGoblinCount(1);
  }

  // Mantém um walker por goblin da vila (sincronizado com o roster)
  setGoblinCount(n) {
    while (this.goblins.length < n) {
      const a = Math.random() * Math.PI * 2;
      this.goblins.push(new GoblinWalker(
        this.clearing.x + Math.cos(a) * 40,
        this.clearing.y + Math.sin(a) * 28,
        this.clearing
      ));
    }
    if (this.goblins.length > n) this.goblins.length = n;
    this.goblins.forEach((g, i) => { g.i = i; });
  }

  generate() {
    const n1 = makeNoise(this.seed, 18);
    const n2 = makeNoise(this.seed + 101, 9);
    const n3 = makeNoise(this.seed + 202, 4);
    const nr = makeNoise(this.seed + 303, 6);
    const cx = WORLD.COLS / 2, cy = WORLD.ROWS / 2;

    for (let y = 0; y < WORLD.ROWS; y++) {
      for (let x = 0; x < WORLD.COLS; x++) {
        const fbm = n1(x, y) * 0.55 + n2(x, y) * 0.3 + n3(x, y) * 0.15;
        const dx = (x - cx) / (WORLD.COLS * 0.46);
        const dy = (y - cy) / (WORLD.ROWS * 0.44);
        const d = Math.min(1, Math.hypot(dx, dy));
        const elev = fbm * 0.62 + (1 - d * d) * 0.62;

        let t;
        if (elev < 0.50) t = DEEP;
        else if (elev < 0.56) t = WATER;
        else if (elev < 0.62) t = SAND;
        else t = GRASS;
        if (t === GRASS && nr(x, y) > 0.74) t = ROCK;

        // clareira da vila: sempre grama limpa
        const px = x * WORLD.TILE + 8, py = y * WORLD.TILE + 8;
        if (Math.hypot(px - this.clearing.x, py - this.clearing.y) < this.clearing.r) t = GRASS;

        this.tiles[y * WORLD.COLS + x] = t;
      }
    }
  }

  tileAtPx(px, py) {
    const tx = Math.floor(px / WORLD.TILE), ty = Math.floor(py / WORLD.TILE);
    if (tx < 0 || ty < 0 || tx >= WORLD.COLS || ty >= WORLD.ROWS) return DEEP;
    return this.tiles[ty * WORLD.COLS + tx];
  }

  // Terreno estático desenhado 1x em canvas offscreen
  prerender() {
    const c = document.createElement('canvas');
    c.width = WORLD.W; c.height = WORLD.H;
    const g = c.getContext('2d');
    const T = WORLD.TILE;

    for (let y = 0; y < WORLD.ROWS; y++) {
      for (let x = 0; x < WORLD.COLS; x++) {
        const t = this.tiles[y * WORLD.COLS + x];
        const px = x * T, py = y * T;
        const h = hash2(x, y, this.seed);

        if (t === DEEP || t === WATER) {
          g.fillStyle = COLORS[t];
          g.fillRect(px, py, T, T);
          if (h > 0.86) { // variação sutil
            g.fillStyle = 'rgba(255,255,255,0.05)';
            g.fillRect(px, py, T, T);
          }
        } else if (t === SAND) {
          g.fillStyle = COLORS[SAND];
          g.fillRect(px, py, T, T);
          // beirada molhada onde encosta água
          const near = (xx, yy) => {
            const i = yy * WORLD.COLS + xx;
            return xx >= 0 && yy >= 0 && xx < WORLD.COLS && yy < WORLD.ROWS && this.tiles[i] <= WATER;
          };
          g.fillStyle = COLORS.wetSand;
          if (near(x, y - 1)) g.fillRect(px, py, T, 3);
          if (near(x, y + 1)) g.fillRect(px, py + T - 3, T, 3);
          if (near(x - 1, y)) g.fillRect(px, py, 3, T);
          if (near(x + 1, y)) g.fillRect(px + T - 3, py, 3, T);
          if (h > 0.9) { // conchas/pedrinhas
            g.fillStyle = '#cbb98a';
            g.fillRect(px + 4 + Math.floor(h * 7) % 6, py + 5 + Math.floor(h * 13) % 6, 2, 2);
          }
        } else if (t === ROCK) {
          g.fillStyle = COLORS[ROCK];
          g.fillRect(px, py, T, T);
          g.fillStyle = COLORS.rockDark;
          g.fillRect(px + 2, py + 3, 6, 4);
          g.fillRect(px + 9, py + 8, 5, 4);
          g.fillStyle = 'rgba(255,255,255,0.14)';
          g.fillRect(px + 3, py + 3, 3, 1);
        } else { // GRASS
          const inClearing = Math.hypot(px + 8 - this.clearing.x, py + 8 - this.clearing.y) < this.clearing.r;
          g.fillStyle = inClearing ? COLORS.clearing : COLORS.grassShades[Math.floor(h * 3) % 3];
          g.fillRect(px, py, T, T);
          if (!inClearing) {
            if (h > 0.88) { // tufo de grama
              g.fillStyle = COLORS.tuft;
              g.fillRect(px + 4, py + 8, 1, 4);
              g.fillRect(px + 7, py + 6, 1, 6);
              g.fillRect(px + 10, py + 9, 1, 3);
            } else if (h < 0.05) { // florzinha
              g.fillStyle = COLORS.flowers[Math.floor(h * 100) % 3];
              g.fillRect(px + 7, py + 7, 2, 2);
            }
          } else if (h > 0.93) {
            g.fillStyle = 'rgba(0,0,0,0.06)'; // pisado na clareira
            g.fillRect(px + 3, py + 6, 4, 2);
          }
        }
      }
    }
    this.terrain = c;

    // pontos de brilho na água (animados)
    this.shimmer = [];
    for (let y = 0; y < WORLD.ROWS; y++) {
      for (let x = 0; x < WORLD.COLS; x++) {
        const t = this.tiles[y * WORLD.COLS + x];
        if ((t === WATER || t === DEEP) && hash2(x, y, this.seed + 55) > 0.93) {
          this.shimmer.push({ x: x * T + 4, y: y * T + 7, phase: hash2(x, y, 9) * 6.28 });
        }
      }
    }
  }

  update(dt, api) {
    for (const gb of this.goblins) {
      gb.update(dt, api);
      // Tarefas automáticas só ocupam quem realmente está livre. Assim uma
      // construção recebe prioridade e um posto esgotado procura outro nó.
      if (!gb.job) api.onAutoTask?.(gb);
    }
    // textos flutuantes (+1 madeira etc.)
    for (const f of this.floats) { f.ttl -= dt; f.y -= 14 * dt; }
    this.floats = this.floats.filter((f) => f.ttl > 0);
  }

  draw(ctx, time, vis, extras = []) {
    // recorte visível do terreno pré-renderizado
    const sx = Math.max(0, Math.floor(vis.x0));
    const sy = Math.max(0, Math.floor(vis.y0));
    const sw = Math.min(WORLD.W - sx, Math.ceil(vis.x1 - vis.x0));
    const sh = Math.min(WORLD.H - sy, Math.ceil(vis.y1 - vis.y0));
    if (sw > 0 && sh > 0) ctx.drawImage(this.terrain, sx, sy, sw, sh, sx, sy, sw, sh);

    // brilho da água
    for (const s of this.shimmer) {
      if (s.x < vis.x0 - 8 || s.x > vis.x1 + 8 || s.y < vis.y0 - 8 || s.y > vis.y1 + 8) continue;
      const a = 0.10 + 0.10 * Math.sin(time * 2 + s.phase);
      if (a <= 0.02) continue;
      ctx.fillStyle = `rgba(255,255,255,${a.toFixed(3)})`;
      ctx.fillRect(s.x, s.y, 6, 2);
    }

    // entidades (prédios + nós + goblins) ordenadas por y p/ profundidade
    const drawables = [
      ...extras,
      ...this.goblins.map((gb) => ({ y: gb.y, draw: (c) => gb.draw(c) })),
    ].sort((a, b) => a.y - b.y);
    for (const d of drawables) d.draw(ctx);

    // textos flutuantes
    ctx.font = 'bold 9px monospace';
    ctx.textAlign = 'center';
    for (const f of this.floats) {
      ctx.globalAlpha = Math.max(0, Math.min(1, f.ttl));
      ctx.fillStyle = '#000';
      ctx.fillText(f.text, f.x + 1, f.y + 1);
      ctx.fillStyle = f.color;
      ctx.fillText(f.text, f.x, f.y);
    }
    ctx.globalAlpha = 1;
    ctx.textAlign = 'left';
  }
}

module.exports = { WORLD, World };
