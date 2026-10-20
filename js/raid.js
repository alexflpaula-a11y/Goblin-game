// ============================================================
// raid.js — Balão, mapa das ilhas e exploração da ilha inimiga.
//
// O balão nasce abandonado num canto da ilha da vila. Depois de
// consertado, o botão 🎈 abre o mapa: as ilhas ficam em linha no
// mar e o jogador arrasta para o lado. Ao descer, o grupo de até
// 8 goblins é representado pelo líder (toque = destino). Inimigos patrulham,
// ficam alertas a 6 blocos e, fora do alcance, se confundem e
// voltam. Encostar num grupo ou no Chefe abre a batalha por turnos.
// ============================================================
const { getSprite } = require('assetLoader.js');
const gear = require('gear.js');
const { WORLD } = require('world.js');
const { Goblin, VARIATIONS } = require('goblin.js');
const { BAL } = require('balance.js');
const { creatureFrames, creatureStep } = require('creatures.js');

const TILE = 16;
const RAID = {
  TILE,
  COLS: 128,
  ROWS: 96,
  get W() { return this.COLS * this.TILE; },
  get H() { return this.ROWS * this.TILE; },
};

const DEEP = 0, WATER = 1, SAND = 2, GRASS = 3;
const ALERT_TILES = 6;
const ALERT_RANGE = ALERT_TILES * TILE;
const SCREAM_TILES = 8;
const SCREAM_RANGE = SCREAM_TILES * TILE;
const CONTACT_RANGE = 26;
const PLAYER_SPEED = 72;
const ENEMY_SPEED = 38;
const BOSS_RUSH_SPEED = 120;
const CONFUSED_TIME = 1.2;
const ANIM_FRAMES = { idle: 5, walk: 8, attack: 17, hurt: 17, death: 15 };
// Quadros de caminhada dos animais de caça: 16 por animal, gerados sem IA por
// tools/make_walk_legs.py. O ciclo dura sempre 0,8 s.
const ANIMAL_WALK_FRAMES = { boar: 16, deer: 16, hare: 16 };
const ANIMAL_WALK_CYCLE = 0.8;
// Caça com histerese: o grupo para de correr ao chegar a HUNT_REACH e só volta
// a correr quando o animal passa de HUNT_CHASE. Entre as duas distâncias o estado
// anterior (correr ou golpear) é mantido, então não há ataque/andar piscando.
const HUNT_REACH = 22;
const HUNT_CHASE = 30;

const FORMATION = [
  { dx: -11, dy: -7 }, { dx: 11, dy: -7 },
  { dx: -11, dy: 9 }, { dx: 11, dy: 9 },
];

const BALLOON_REPAIR_COST = { wood: 30, stone: 20, gold: 15 };
const BALLOON_MAX_LEVEL = 3;
const PARTY_LIMIT = 8;
const BATTLE_LIMIT = 4;
const CITY_RADIUS = 170;
const LAIR_RADIUS = 110;

const ISLANDS = [
  { id: 'home', nameKey: 'ui.island_home', difficulty: 0, home: true, reqBalloon: 0, hue: 128, theme: 'home' },
  { id: 'fangs', nameKey: 'ui.island_fangs', difficulty: 1, reqBalloon: 1, hue: 22, theme: 'fangs' },
  { id: 'smoke', nameKey: 'ui.island_smoke', difficulty: 2, reqBalloon: 2, hue: 198, theme: 'smoke' },
  { id: 'iron', nameKey: 'ui.island_iron', difficulty: 3, reqBalloon: 3, hue: 8, theme: 'iron' },
];

const THEMES = {
  home: {
    ground: '#4e9458', tuft: '#2f6b3c', sand: '#e8d293', wetSand: '#c9b57f',
    deep: '#143a5c', water: '#1d5c8f', accent: '#e86a6a',
  },
  fangs: {
    ground: '#9a7a38', tuft: '#5c4a1c', sand: '#d8b56a', wetSand: '#b89450',
    deep: '#1a3e4a', water: '#2a6e7a', accent: '#5a3820',
  },
  smoke: {
    ground: '#4a534c', tuft: '#2c3630', sand: '#8c8070', wetSand: '#6e6658',
    deep: '#182028', water: '#2a3844', accent: '#6a6860',
  },
  iron: {
    ground: '#6e3c32', tuft: '#3e221c', sand: '#c49a68', wetSand: '#a0784c',
    deep: '#1c2432', water: '#2c4460', accent: '#8a4e30',
  },
};

function themeOf(def) {
  return THEMES[def?.theme || def?.id] || THEMES.home;
}

const CHEST_ITEMS = ['clava_goblin', 'botas_couro', 'anel_cobre', 'escudo_madeira', 'capacete_ferro'];
const ENEMY_NAMES = ['Snaga', 'Ugluk', 'Radbug', 'Muzgash', 'Gorbag', 'Shagrat', 'Bolg', 'Lug'];
const ENEMY_HUTS = [
  { type: 'house', sprite: 'building_house_1', hp: 10, dx: -96, dy: -70 },
  { type: 'house', sprite: 'building_house_1', hp: 10, dx: 4, dy: -82 },
  { type: 'serraria', sprite: 'building_serraria_1', hp: 12, dx: 100, dy: -64 },
  { type: 'fazenda', sprite: 'building_fazenda_1', hp: 12, dx: -100, dy: 62 },
  { type: 'cozinha', sprite: 'building_cozinha_1', hp: 10, dx: 8, dy: 78 },
  { type: 'mercado', sprite: 'building_mercado_1', hp: 12, dx: 104, dy: 58 },
];
const ITEM_ICON = (id) => 'item_' + id;

const COLORS = {
  [DEEP]: '#143a5c',
  [WATER]: '#1d5c8f',
  [SAND]: '#e8d293',
  ground: '#4e9458',
  wetSand: '#c9b57f',
  tuft: '#2f6b3c',
};

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

// ---------- terreno low-poly: cada azulejo vira 2 facetas triangulares ----
// A cor base do azulejo nao muda; cada triangulo ganha um tom flat proprio
// (hash do azulejo), como nas faces da arte low-poly dos animais.
const _shadeCache = new Map();
function shadeHex(hex, f) {
  if (!/^#[0-9a-f]{6}$/i.test(hex)) return hex;
  const key = hex + '|' + f.toFixed(3);
  let out = _shadeCache.get(key);
  if (!out) {
    const n = parseInt(hex.slice(1), 16);
    const c = (v) => Math.max(0, Math.min(255, Math.round(v * f)));
    out = `rgb(${c(n >> 16)},${c((n >> 8) & 255)},${c(n & 255)})`;
    _shadeCache.set(key, out);
  }
  return out;
}
function facetTri(g, x1, y1, x2, y2, x3, y3, fill) {
  g.fillStyle = fill;
  g.beginPath();
  g.moveTo(x1, y1); g.lineTo(x2, y2); g.lineTo(x3, y3);
  g.closePath(); g.fill();
}
function facetTile(g, px, py, T, hex, h1, h2) {
  const a = shadeHex(hex, 0.94 + h1 * 0.12);
  const b = shadeHex(hex, 0.94 + h2 * 0.12);
  if (h1 > 0.5) {
    facetTri(g, px, py, px + T, py, px, py + T, a);
    facetTri(g, px + T, py, px + T, py + T, px, py + T, b);
  } else {
    facetTri(g, px, py, px + T, py, px + T, py + T, a);
    facetTri(g, px, py, px + T, py + T, px, py + T, b);
  }
}

function makeNoise(seed, cell, cols, rows) {
  const rnd = mulberry32(seed);
  const gw = Math.ceil(cols / cell) + 3;
  const gh = Math.ceil(rows / cell) + 3;
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

function combatCfg() {
  return BAL.combat || {};
}

function balloonCost() {
  return combatCfg().balloonRepair || BALLOON_REPAIR_COST;
}

function balloonUpgradeCost(level) {
  const cfg = combatCfg();
  if (level <= 0) return cfg.balloonRepair || BALLOON_REPAIR_COST;
  if (level >= BALLOON_MAX_LEVEL) return null;
  const table = cfg.balloonUpgrade || [
    { wood: 55, stone: 40, gold: 45 },
    { wood: 90, stone: 70, gold: 80 },
  ];
  return table[level - 1] || null;
}

function islandUnlocked(def, balloonLevel) {
  if (!def || def.home) return true;
  return (balloonLevel || 0) >= (def.reqBalloon || 1);
}

function togglePartyMember(pick, index, limit = PARTY_LIMIT) {
  if (!Array.isArray(pick) || index == null || index < 0) return false;
  const at = pick.indexOf(index);
  if (at >= 0) { pick.splice(at, 1); return true; }
  if (pick.length >= limit) return false;
  pick.push(index);
  return true;
}

function raidRewards(difficulty, kind) {
  const d = Math.max(1, difficulty | 0);
  const cfg = combatCfg();
  const gold = cfg.gold ?? (12 + d * 4);
  const gems = cfg.gems ?? 2;
  if (kind === 'boss' || kind === 'lair') return { gold: gold * 2 + 10, goblin_gems: gems * 3 };
  return { gold, goblin_gems: gems };
}

function makeEnemyGoblin(name, difficulty, variation, isBoss, rng) {
  const d = Math.max(1, difficulty);
  const bonus = isBoss ? 4 : 0;
  const g = new Goblin({
    name,
    rarity: isBoss ? 'rare' : 'common',
    specialty: isBoss ? 'warrior' : 'common',
    variation,
    level: d + bonus,
    poderDestrutivo: Math.min(10, 3 + d + bonus),
    potencialMagico: 2,
    vitalidade: Math.min(10, 3 + d + bonus),
    velocidade: Math.min(10, (isBoss ? 6 : 2) + d),
    precisao: Math.min(10, 3 + d),
    potencialEvolucao: 3,
  });
  g.isBoss = !!isBoss;
  return g;
}

function patrolCount(difficulty, rng) {
  const d = Math.max(1, difficulty | 0);
  const lo = d;
  const hi = Math.min(4, d + 1);
  return lo + Math.floor((rng ? rng() : Math.random()) * (hi - lo + 1));
}

function makePatrolMembers(difficulty, rng, count) {
  const n = Math.max(1, Math.min(4, count != null ? count : patrolCount(difficulty, rng)));
  const out = [];
  for (let i = 0; i < n; i++) {
    const v = VARIATIONS[Math.floor(rng() * VARIATIONS.length)];
    out.push(makeEnemyGoblin(ENEMY_NAMES[i % ENEMY_NAMES.length], difficulty, v, false, rng));
  }
  return out;
}

function makeBossMember(difficulty, rng) {
  const v = VARIATIONS.includes('49_guerreiro_dourado') ? '49_guerreiro_dourado' : VARIATIONS[0];
  const g = makeEnemyGoblin('Chefe', difficulty, v, true, rng);
  return g;
}

const WOLF_NAMES = ['Presa', 'Uivo', 'Garra', 'Focinho'];

function makeWolfEnemy(name, difficulty, extra) {
  const d = Math.max(1, difficulty | 0);
  const hp = extra?.maxHp ?? (14 + d * 5);
  return {
    name,
    kind: 'wolf',
    spritePrefix: extra?.spritePrefix || 'wolf',
    attackKind: extra?.attackKind || 'melee',
    isBoss: !!extra?.isBoss,
    scale: extra?.scale,
    level: d,
    poderDestrutivo: extra?.poderDestrutivo ?? (2 + d),
    vitalidade: extra?.vitalidade ?? (2 + d),
    velocidade: extra?.velocidade ?? (3 + d),
    precisao: extra?.precisao ?? (3 + d),
    maxHp: hp,
    hp,
  };
}

function makeWolfPack(count, difficulty) {
  const n = Math.max(1, Math.min(4, count | 0));
  const out = [];
  for (let i = 0; i < n; i++) out.push(makeWolfEnemy(WOLF_NAMES[i % WOLF_NAMES.length], difficulty));
  return out;
}

function makeWarTwins(difficulty) {
  const d = Math.max(1, difficulty | 0);
  const hp = 48 + d * 10;
  return [
    makeWolfEnemy('Mandíbula', d, {
      isBoss: true, attackKind: 'bite', spritePrefix: 'twin_jaw', scale: 2,
      poderDestrutivo: 7 + d, vitalidade: 8, velocidade: 5, precisao: 6, maxHp: hp,
    }),
    makeWolfEnemy('Patas', d, {
      isBoss: true, attackKind: 'slash', spritePrefix: 'twin_paw', scale: 2,
      poderDestrutivo: 7 + d, vitalidade: 8, velocidade: 5, precisao: 6, maxHp: hp,
    }),
  ];
}

function denWaves(kind, difficulty) {
  if (kind === 'lair') {
    return {
      foes: makeWolfPack(4, difficulty),
      waves: [makeWolfPack(4, difficulty), makeWarTwins(difficulty)],
      bgKey: 'bg_den',
      twinsBg: 'bg_den_twins',
    };
  }
  return {
    foes: makeWolfPack(1, difficulty),
    waves: [makeWolfPack(2, difficulty), makeWolfPack(2, difficulty)],
    bgKey: 'bg_den',
  };
}

function raidWorkPeriod(party) {
  const base = BAL.nodes?.workPeriod ?? 1.2;
  const alive = (party?.goblins || []).filter((g) => g && g.hp > 0);
  // Sum each worker's home-island rate, including strength/speed bonuses.
  const rate = alive.reduce((sum, g) => sum + 1 / Math.max(0.4,
    1 - ((g.velocidade || 0) + (g.poderDestrutivo || 0)) / 80), 0);
  return rate > 0 ? base / rate : Infinity;
}

function findBalloonSpot(world) {
  const { TILE: T, COLS, ROWS } = WORLD;
  let best = null, bestScore = -1;
  for (let ty = Math.floor(ROWS * 0.52); ty < ROWS - 5; ty++) {
    for (let tx = 4; tx < Math.floor(COLS * 0.36); tx++) {
      const t = world.tiles[ty * COLS + tx];
      if (t !== 3) continue;
      let nearWater = 0, nearSand = 0;
      for (let dy = -2; dy <= 2; dy++) {
        for (let dx = -2; dx <= 2; dx++) {
          const nx = tx + dx, ny = ty + dy;
          if (nx < 0 || ny < 0 || nx >= COLS || ny >= ROWS) continue;
          const n = world.tiles[ny * COLS + nx];
          if (n <= WATER) nearWater = 1;
          if (n === SAND) nearSand = 1;
        }
      }
      if (!nearWater && !nearSand) continue;
      const x = tx * T + 8, y = ty * T + 8;
      const dClear = Math.hypot(x - world.clearing.x, y - world.clearing.y);
      if (dClear < world.clearing.r + 90) continue;
      const score = nearWater * 2 + nearSand + dClear / 140;
      if (score > bestScore) { bestScore = score; best = { x, y }; }
    }
  }
  return best || { x: world.clearing.x - 300, y: world.clearing.y + 230 };
}

function createBalloon(world, data) {
  const spot = data?.x != null ? { x: data.x, y: data.y } : findBalloonSpot(world);
  const level = data?.level ?? (data?.repaired ? 1 : 0);
  return { x: spot.x, y: spot.y, level, repaired: level >= 1 };
}

function balloonHit(balloon, wx, wy) {
  if (!balloon) return false;
  return Math.abs(wx - balloon.x) < 28 && wy < balloon.y + 10 && wy > balloon.y - 72;
}

function drawGoblinAt(ctx, goblin, x, y, face, anim, frame, scale = 1) {
  const frames = ANIM_FRAMES[anim] || 1;
  const spr = getSprite(gear.spriteForGoblin(goblin, anim, frame % frames));
  ctx.save();
  ctx.translate(x, y);
  ctx.scale((face || 1) * scale, scale);
  ctx.drawImage(spr, -16, -30, 32, 32);
  ctx.restore();
}

function drawBalloon(ctx, balloon, time, opts) {
  if (!balloon) return;
  const flying = !!(opts && opts.flying);
  const x = balloon.x, y = balloon.y;
  const bob = (balloon.repaired || flying) ? Math.sin((time || 0) * 2.2) * 2.5 : 0;
  const id = flying ? 'balloon_flying' : (balloon.repaired ? 'balloon_ready' : 'balloon_wrecked');
  const w = flying ? 46 : (balloon.repaired ? 42 : 56);
  const h = flying ? 58 : (balloon.repaired ? 54 : 38);
  ctx.save();
  ctx.imageSmoothingEnabled = true; // cenario low-poly: arte interna maior que o desenho
  ctx.drawImage(getSprite(id), x - w / 2, y - h + 8 + bob, w, h);
  ctx.restore();
}

function drawTree(ctx, x, y, hive, node) {
  ctx.save();
  ctx.imageSmoothingEnabled = true; // cenario low-poly: arte interna maior que o desenho
  ctx.drawImage(getSprite('node_tree_0'), x - 24, y - 46, 48, 48);
  if (node && !node.taken && node.max && node.stock < node.max) {
    drawHpBar(ctx, x, y - 50, 20, node.stock, node.max);
  }
  ctx.restore();
}

function drawRock(ctx, x, y, node) {
  ctx.save();
  ctx.imageSmoothingEnabled = true; // cenario low-poly: arte interna maior que o desenho
  ctx.drawImage(getSprite('node_rock_0'), x - 24, y - 46, 48, 48);
  if (node && !node.taken && node.max && node.stock < node.max) {
    drawHpBar(ctx, x, y - 50, 20, node.stock, node.max);
  }
  ctx.restore();
}

function drawChest(ctx, x, y, open) {
  ctx.save();
  ctx.imageSmoothingEnabled = true; // cenario low-poly: arte interna maior que o desenho
  ctx.drawImage(getSprite(open ? 'chest_open' : 'chest_closed'), x - 12, y - 20, 24, 24);
  ctx.restore();
}

function drawHpBar(ctx, x, y, w, hp, maxHp) {
  const h = 4;
  ctx.fillStyle = 'rgba(0,0,0,0.6)';
  ctx.fillRect(x - w / 2, y, w, h);
  const frac = Math.max(0, Math.min(1, hp / Math.max(1, maxHp)));
  ctx.fillStyle = frac > 0.45 ? '#4fa562' : '#c4452f';
  ctx.fillRect(x - w / 2, y, w * frac, h);
  ctx.strokeStyle = 'rgba(255,233,168,0.55)';
  ctx.lineWidth = 1;
  ctx.strokeRect(x - w / 2 - 0.5, y - 0.5, w + 1, h + 1);
}

function drawEnemyBuilding(ctx, b) {
  ctx.save();
  ctx.imageSmoothingEnabled = true; // cenario low-poly: arte interna maior que o desenho
  if (b.ruined) ctx.globalAlpha = 0.55;
  if (typeof ctx.filter === 'string') {
    ctx.filter = b.ruined
      ? 'grayscale(0.55) brightness(0.72)'
      : 'hue-rotate(-22deg) saturate(1.35) brightness(0.92)';
  }
  ctx.drawImage(getSprite(b.sprite || 'building_house_1'), b.x - 32, b.y - 60, 64, 64);
  ctx.filter = 'none';
  ctx.restore();
  if (!b.ruined) drawHpBar(ctx, b.x, b.y - 66, 28, b.hp, b.maxHp);
}

function drawGroundDrop(ctx, d, time) {
  if (d.taken) return;
  const bob = Math.sin(((time || 0) + (d.t || 0)) * 4.2) * 3.2;
  const glow = 0.38 + 0.28 * Math.sin(((time || 0) + (d.t || 0)) * 5);
  ctx.save();
  ctx.globalAlpha = 0.45 + glow;
  ctx.fillStyle = d.kind === 'item' ? '#4cbfff' : '#ffe9a8';
  ctx.beginPath();
  ctx.ellipse(d.x, d.y - 8 + bob, 11, 7, 0, 0, Math.PI * 2);
  ctx.fill();
  ctx.globalAlpha = 1;
  ctx.imageSmoothingEnabled = false;
  ctx.drawImage(getSprite(d.icon || 'res_gold'), d.x - 8, d.y - 22 + bob, 16, 16);
  ctx.restore();
}

function drawPawStamp(g, x, y, color) {
  g.fillStyle = color;
  g.fillRect(x + 3, y + 5, 4, 3);
  g.fillRect(x + 1, y + 1, 2, 2);
  g.fillRect(x + 4, y, 2, 2);
  g.fillRect(x + 7, y + 1, 2, 2);
  g.fillRect(x + 9, y + 4, 2, 2);
}

function drawDen(ctx, x, y) {
  ctx.save();
  ctx.fillStyle = 'rgba(0,0,0,0.28)';
  ctx.beginPath(); ctx.ellipse(x, y + 4, 18, 7, 0, 0, Math.PI * 2); ctx.fill();
  ctx.fillStyle = '#6a4a28';
  ctx.beginPath(); ctx.ellipse(x, y - 2, 20, 10, 0, 0, Math.PI * 2); ctx.fill();
  ctx.fillStyle = '#3a2814';
  ctx.beginPath(); ctx.ellipse(x - 1, y - 4, 16, 7, 0, 0, Math.PI * 2); ctx.fill();
  ctx.fillStyle = '#120c08';
  ctx.beginPath(); ctx.ellipse(x - 1, y - 3, 9, 5, 0, 0, Math.PI * 2); ctx.fill();
  ctx.fillStyle = '#e8d5a8';
  ctx.fillRect(x + 10, y - 8, 2, 8);
  ctx.fillRect(x + 8, y - 10, 6, 2);
  ctx.fillRect(x - 16, y - 6, 2, 7);
  ctx.restore();
}

function drawHive(ctx, x, y) {
  ctx.save();
  ctx.strokeStyle = '#5a3a18';
  ctx.lineWidth = 2;
  ctx.beginPath(); ctx.moveTo(x, y - 28); ctx.lineTo(x, y - 8); ctx.stroke();
  ctx.fillStyle = '#d4a030';
  ctx.beginPath(); ctx.ellipse(x, y - 2, 8, 12, 0, 0, Math.PI * 2); ctx.fill();
  ctx.strokeStyle = '#8a5a10';
  ctx.lineWidth = 1;
  ctx.beginPath(); ctx.ellipse(x, y - 6, 7, 3, 0, 0, Math.PI * 2); ctx.stroke();
  ctx.beginPath(); ctx.ellipse(x, y - 1, 7, 3, 0, 0, Math.PI * 2); ctx.stroke();
  ctx.beginPath(); ctx.ellipse(x, y + 4, 6, 2.5, 0, 0, Math.PI * 2); ctx.stroke();
  ctx.fillStyle = '#3a2208';
  ctx.beginPath(); ctx.ellipse(x, y + 2, 2, 1.5, 0, 0, Math.PI * 2); ctx.fill();
  ctx.restore();
}

function drawVent(ctx, x, y, time) {
  ctx.save();
  ctx.fillStyle = '#1a1c1a';
  ctx.beginPath(); ctx.ellipse(x, y, 8, 4, 0, 0, Math.PI * 2); ctx.fill();
  ctx.fillStyle = '#3a3e3a';
  ctx.beginPath(); ctx.ellipse(x, y - 1, 5, 2, 0, 0, Math.PI * 2); ctx.fill();
  const puff = 0.35 + 0.25 * Math.sin((time || 0) * 2.4 + x);
  ctx.globalAlpha = puff;
  ctx.fillStyle = '#9aa09a';
  ctx.beginPath(); ctx.ellipse(x, y - 10 - ((time || 0) * 8 + x) % 12, 5, 3, 0, 0, Math.PI * 2); ctx.fill();
  ctx.beginPath(); ctx.ellipse(x + 3, y - 18 - ((time || 0) * 6) % 10, 4, 3, 0, 0, Math.PI * 2); ctx.fill();
  ctx.restore();
}

function drawStump(ctx, x, y) {
  ctx.save();
  ctx.fillStyle = '#2a2218';
  ctx.fillRect(x - 7, y - 10, 14, 10);
  ctx.fillStyle = '#3a2a1c';
  ctx.beginPath(); ctx.ellipse(x, y - 10, 8, 4, 0, 0, Math.PI * 2); ctx.fill();
  ctx.fillStyle = '#1a1410';
  ctx.beginPath(); ctx.ellipse(x, y - 10, 4, 2, 0, 0, Math.PI * 2); ctx.fill();
  ctx.fillStyle = '#4a3a28';
  ctx.fillRect(x + 6, y - 6, 3, 5);
  ctx.restore();
}

function drawScrap(ctx, x, y) {
  ctx.save();
  ctx.fillStyle = '#6a3a28';
  ctx.fillRect(x - 10, y - 6, 14, 6);
  ctx.fillStyle = '#8a4e30';
  ctx.fillRect(x - 4, y - 12, 10, 8);
  ctx.fillStyle = '#c46a3a';
  ctx.fillRect(x + 2, y - 8, 8, 4);
  ctx.fillStyle = '#3a281c';
  ctx.fillRect(x - 8, y - 2, 6, 3);
  ctx.restore();
}

function drawOreSpike(ctx, x, y) {
  ctx.save();
  ctx.fillStyle = '#2a2428';
  ctx.beginPath();
  ctx.moveTo(x - 10, y); ctx.lineTo(x - 2, y - 16); ctx.lineTo(x + 6, y); ctx.closePath(); ctx.fill();
  ctx.fillStyle = '#c45a28';
  ctx.beginPath();
  ctx.moveTo(x - 2, y - 4); ctx.lineTo(x + 2, y - 18); ctx.lineTo(x + 6, y - 4); ctx.closePath(); ctx.fill();
  ctx.fillStyle = '#e8a050';
  ctx.fillRect(x, y - 14, 2, 6);
  ctx.restore();
}

/** Animal abatido cai de lado em 4 passos (pixel art), apoiado no chão, e some em fade. */
const ANIMAL_BASE_H = { boar: 28, deer: 40, hare: 24 };
/** Segundos que o animal fica parado no sprite de dano depois de um golpe. */
const HURT_HOLD_S = 2.5;
/** Duração do tremor e do clarão no início do dano. */
const HURT_FLASH_S = 0.18;
const FALL_TIME = 0.45;
const FADE_TIME = 0.35;

function drawAnimal(ctx, a, time) {
  if (!a || (!a.alive && !(a.corpseT > 0))) return;
  ctx.save();
  ctx.translate(a.x, a.y);
  ctx.scale(a.face || 1, 1);
  ctx.imageSmoothingEnabled = true; // arte original é maior que o desenho; suavizar evita chiado.
  if (a.kind === 'wolf') {
    ctx.fillStyle = 'rgba(0,0,0,0.28)';
    ctx.beginPath(); ctx.ellipse(0, 2, 9, 3, 0, 0, Math.PI * 2); ctx.fill();
    const anim = a.anim || 'idle';
    const n = creatureFrames('wolf', anim);
    const spr = getSprite('wolf_' + anim + '_' + ((a.frame || 0) % n));
    ctx.imageSmoothingEnabled = false;
    ctx.drawImage(spr, -24, -30, 48, 32);
    ctx.restore();
    return;
  }

  const fade = a.alive ? 1 : Math.max(0, Math.min(1, (a.corpseT || 0) / FADE_TIME));
  ctx.globalAlpha = fade;
  // A caixa de desenho é sempre a do sprite de repouso, para as variações ficarem no mesmo lugar.
  const idle = getSprite('animal_' + a.kind);
  const h = ANIMAL_BASE_H[a.kind] || 24;
  const w = h * ((idle.width || 1) / (idle.height || 1));
  let id;
  if (!a.alive) id = 'animal_' + a.kind + '_death';
  else if (a.hurtT > 0) id = 'animal_' + a.kind + '_hurt';
  else id = 'animal_' + a.kind + (a.anim === 'walk' ? '_walk_' + ((a.frame || 0) % (ANIMAL_WALK_FRAMES[a.kind] || 8)) : '');
  if (a.alive && a.hurtT > 0) {
    // Golpe: treme e clareia só nos primeiros HURT_FLASH_S; a arte de dano segue até hurtT zerar.
    const k = Math.max(0, 1 - (HURT_HOLD_S - a.hurtT) / HURT_FLASH_S);
    ctx.translate(Math.sin(k * 24) * 1.2 * k, 0);
    if (k > 0) ctx.filter = 'brightness(1.35)';
  }
  if (!a.alive) {
    // Queda: a carcaça desce do ar até o chão em FALL_TIME.
    const k = Math.min(1, (a.deathT || 0) / FALL_TIME);
    ctx.translate(0, -6 * (1 - k) * (1 - k));
  }
  ctx.fillStyle = 'rgba(0,0,0,0.28)';
  ctx.beginPath(); ctx.ellipse(0, 2, w * 0.36, 3, 0, 0, Math.PI * 2); ctx.fill();
  // Caminhada: o corpo sobe 1 px a cada passada (a arte pequena não mostra só as pernas).
  if (a.alive && a.anim === 'walk' && !(a.hurtT > 0)) {
    const half = (ANIMAL_WALK_FRAMES[a.kind] || 8) / 2;
    ctx.translate(0, -Math.abs(Math.sin(Math.PI * (a.frame || 0) / half)));
  }
  ctx.imageSmoothingEnabled = true;
  ctx.drawImage(getSprite(id), -w / 2, -h + 2, w, h);
  ctx.filter = 'none';
  ctx.globalAlpha = 1;
  if (a.alive) {
    ctx.restore();
    ctx.save();
    ctx.translate(a.x, a.y);
    drawHpBar(ctx, 0, -h - 4, 22, a.hp, a.maxHp);
  }
  ctx.restore();
}

function drawProp(ctx, p, time) {
  if (!p) return;
  ctx.save();
  ctx.imageSmoothingEnabled = true; // cenario low-poly: arte interna maior que o desenho
  if (p.type === 'den') ctx.drawImage(getSprite('prop_den'), p.x - 26, p.y - 34, 52, 34);
  else if (p.type === 'hive') ctx.drawImage(getSprite('prop_hive'), p.x - 16, p.y - 42, 32, 40);
  else if (p.type === 'vent') drawVent(ctx, p.x, p.y, time);
  else if (p.type === 'stump') drawStump(ctx, p.x, p.y);
  else if (p.type === 'scrap') drawScrap(ctx, p.x, p.y);
  else if (p.type === 'ore') drawOreSpike(ctx, p.x, p.y);
  ctx.restore();
}

class RaidIsland {
  constructor(def, goblins, seed) {
    this.def = def;
    this.difficulty = def?.difficulty || 1;
    this.seed = seed ?? (1000 + this.difficulty * 97);
    this.rng = mulberry32(this.seed);
    this.tiles = new Uint8Array(RAID.COLS * RAID.ROWS);
    this.W = RAID.W; this.H = RAID.H;
    this.events = [];
    this.busy = false;
    this.generate();
    this.prerender();
    const partyGoblins = (goblins || []).slice(0, PARTY_LIMIT);
    this.party = {
      x: this.landing.x,
      y: this.landing.y,
      target: null,
      goblins: partyGoblins,
      face: 1,
      anim: 'idle',
      frame: 0,
      animT: 0,
      job: null,
    };
    this.bossEnraged = false;
    this.cleared = false;
    this.showCityZone = false;
    this.landingGhost = null;
    this.drops = [];
    this.flyIn = null;
    this.leftBalloon = false;
  }

  beginFlyIn(duration = 2.1) {
    this.flyIn = { t: 0, dur: duration };
    this.leftBalloon = false;
    this.party.target = null;
    this.party.job = null;
    this.party.anim = 'idle';
  }

  flyingIn() {
    return !!(this.flyIn && this.flyIn.t < this.flyIn.dur);
  }

  _isFangs() {
    return (this.def?.theme || this.def?.id) === 'fangs';
  }

  inCity(x, y) {
    const r = this._isFangs() ? LAIR_RADIUS : CITY_RADIUS;
    return Math.hypot(x - this.center.x, y - this.center.y) < r;
  }

  canLand(x, y) {
    return this.walkable(x, y) && !this.inCity(x, y)
      && !this.dens.some((d) => Math.hypot(x - d.x, y - d.y) < 70);
  }

  setLanding(x, y) {
    if (!this.canLand(x, y)) return false;
    const p = this.clampWalkable(x, y);
    if (this.inCity(p.x, p.y)) return false;
    this.landing = p;
    this.party.x = p.x;
    this.party.y = p.y;
    this.party.target = null;
    this.party.job = null;
    this.party.anim = 'idle';
    return true;
  }

  generate() {
    const n1 = makeNoise(this.seed, 14, RAID.COLS, RAID.ROWS);
    const n2 = makeNoise(this.seed + 31, 7, RAID.COLS, RAID.ROWS);
    const cx = RAID.COLS / 2, cy = RAID.ROWS / 2;
    for (let y = 0; y < RAID.ROWS; y++) {
      for (let x = 0; x < RAID.COLS; x++) {
        const fbm = n1(x, y) * 0.6 + n2(x, y) * 0.4;
        const dx = (x - cx) / (RAID.COLS * 0.42);
        const dy = (y - cy) / (RAID.ROWS * 0.40);
        const d = Math.min(1, Math.hypot(dx, dy));
        const elev = fbm * 0.58 + (1 - d * d) * 0.66;
        let t;
        if (elev < 0.50) t = DEEP;
        else if (elev < 0.56) t = WATER;
        else if (elev < 0.62) t = SAND;
        else t = GRASS;
        this.tiles[y * RAID.COLS + x] = t;
      }
    }

    this.center = { x: RAID.W / 2, y: RAID.H / 2 };
    this.landing = this._findLanding();
    this.loot = [];
    this.buildings = [];
    this.patrols = [];
    this.dens = [];
    this.lair = null;
    this.props = [];
    this.animals = [];
    this._placeCenter();
    this._placePatrols();
    this._placeLoot();
    this._placeTheme();
  }

  tileAt(px, py) {
    const tx = Math.floor(px / TILE), ty = Math.floor(py / TILE);
    if (tx < 0 || ty < 0 || tx >= RAID.COLS || ty >= RAID.ROWS) return DEEP;
    return this.tiles[ty * RAID.COLS + tx];
  }

  walkable(px, py) { return this.tileAt(px, py) >= SAND; }

  _findLanding() {
    for (let tx = 4; tx < RAID.COLS / 2; tx++) {
      for (let ty = Math.floor(RAID.ROWS * 0.35); ty < Math.floor(RAID.ROWS * 0.7); ty++) {
        if (this.tiles[ty * RAID.COLS + tx] === SAND) {
          const x = tx * TILE + 8, y = ty * TILE + 8;
          if (this.walkable(x + 18, y)) return { x: x + 22, y };
        }
      }
    }
    return { x: 140, y: RAID.H / 2 };
  }

  _grassSpot(minCenter, maxCenter, avoid, minAvoid) {
    for (let i = 0; i < 400; i++) {
      const tx = 4 + Math.floor(this.rng() * (RAID.COLS - 8));
      const ty = 4 + Math.floor(this.rng() * (RAID.ROWS - 8));
      if (this.tiles[ty * RAID.COLS + tx] !== GRASS) continue;
      const x = tx * TILE + 8, y = ty * TILE + 8;
      const dc = Math.hypot(x - this.center.x, y - this.center.y);
      if (dc < minCenter || dc > maxCenter) continue;
      if (Math.hypot(x - this.landing.x, y - this.landing.y) < 96) continue;
      let ok = true;
      for (const a of avoid) {
        if (Math.hypot(a.x - x, a.y - y) < Math.max(minAvoid, a.kind === 'lair' ? 120 : a.kind === 'den' ? 58 : 0)) { ok = false; break; }
      }
      if (ok) return { x, y };
    }
    return null;
  }

  _placeCenter() {
    if (this._isFangs()) {
      this.buildings = [];
      this.boss = null;
      this.lair = {
        x: this.center.x, y: this.center.y,
        kind: 'lair', type: 'lair', cleared: false,
      };
      return;
    }
    ENEMY_HUTS.forEach((def, i) => {
      this.buildings.push({
        x: this.center.x + def.dx,
        y: this.center.y + def.dy,
        hp: def.hp,
        maxHp: def.hp,
        ruined: false,
        id: 'hut_' + i,
        type: def.type,
        sprite: def.sprite,
      });
    });
    this.boss = {
      x: this.center.x + 8,
      y: this.center.y - 6,
      goblin: makeBossMember(this.difficulty, this.rng),
      face: -1,
      anim: 'idle',
      frame: 0,
      animT: 0,
      alive: true,
    };
  }

  _ensureWaypoints(spot) {
    const wps = [spot];
    const angles = [0.5, 2.3, 3.9, 5.4];
    for (const a of angles) {
      const raw = { x: spot.x + Math.cos(a) * 56, y: spot.y + Math.sin(a) * 56 };
      const p = this.clampWalkable(raw.x, raw.y);
      if (Math.hypot(p.x - spot.x, p.y - spot.y) > 12) wps.push(p);
      if (wps.length >= 4) break;
    }
    return wps;
  }

  _placePatrols() {
    if (this._isFangs()) {
      const placed = [this.lair, this.landing].filter(Boolean);
      for (let i = 0; i < 6; i++) {
        const spot = this._grassSpot(200, 780, placed, 110);
        if (!spot) continue;
        const den = { id: 'den_' + i, x: spot.x, y: spot.y, kind: 'den', type: 'den', cleared: false };
        this.dens.push(den);
        placed.push(den);
      }
      return;
    }
    const placed = [this.boss, ...this.buildings];
    for (let i = 0; i < 5; i++) {
      const spot = this._grassSpot(200, 780, placed, 100);
      if (!spot) continue;
      const waypoints = this._ensureWaypoints(spot);
      const patrol = {
        x: spot.x, y: spot.y,
        waypoints,
        wi: 0,
        state: 'patrol', // patrol | chase | confused | return
        confusedT: 0,
        members: makePatrolMembers(this.difficulty, this.rng),
        face: 1,
        anim: 'walk',
        frame: 0,
        animT: 0,
        alive: true,
      };
      this.patrols.push(patrol);
      placed.push(patrol);
    }
  }

  _placeLoot() {
    const placed = [this.boss, this.lair, ...this.buildings, ...this.patrols, ...this.dens, this.landing].filter(Boolean);
    const cfg = BAL.nodes || {};
    const add = (type, n) => {
      for (let i = 0; i < n; i++) {
        const spot = this._grassSpot(80, 860, placed, 32);
        if (!spot) continue;
        const node = { type, x: spot.x, y: spot.y, taken: false };
        if (type === 'tree') { node.stock = cfg.treeStock ?? 30; node.max = node.stock; }
        if (type === 'rock') { node.stock = cfg.rockStock ?? 24; node.max = node.stock; }
        this.loot.push(node);
        placed.push(node);
      }
    };
    add('tree', 28);
    add('rock', 22);
    // Cave victories are now the only source of treasure chests.
  }

  _placeTheme() {
    const theme = this.def?.theme || this.def?.id;
    const placed = [this.boss, this.lair, ...this.buildings, ...this.patrols, ...this.dens, ...this.loot, this.landing].filter(Boolean);
    const addProp = (type, n) => {
      for (let i = 0; i < n; i++) {
        const spot = this._grassSpot(140, 820, placed, 40);
        if (!spot) continue;
        const p = { type, x: spot.x, y: spot.y };
        this.props.push(p);
        placed.push(p);
      }
    };
    const addAnimal = (kind, n) => {
      for (let i = 0; i < n; i++) {
        const spot = this._grassSpot(160, 800, placed, 52);
        if (!spot) continue;
        const a = {
          kind, x: spot.x, y: spot.y,
          homeX: spot.x, homeY: spot.y,
          wx: spot.x, wy: spot.y,
          hp: kind === 'boar' ? 18 : kind === 'deer' ? 12 : 8,
          maxHp: kind === 'boar' ? 18 : kind === 'deer' ? 12 : 8,
          alive: true, face: 1, anim: 'idle', animT: 0, frame: 0,
          wanderT: 0.4 + this.rng() * 2,
        };
        this.animals.push(a);
        placed.push(a);
      }
    };
    if (theme === 'fangs') {
      addAnimal('boar', 2);
      addAnimal('deer', 2);
      addAnimal('hare', 2);
    } else if (theme === 'smoke') {
      addProp('vent', 5);
      addProp('stump', 5);
      addAnimal('hare', 3);
      addAnimal('boar', 2);
    } else if (theme === 'iron') {
      addProp('scrap', 5);
      addProp('ore', 4);
      addAnimal('boar', 2);
      addAnimal('deer', 2);
    }
  }

  prerender() {
    const pal = themeOf(this.def);
    const theme = this.def?.theme || this.def?.id;
    const c = document.createElement('canvas');
    c.width = RAID.W; c.height = RAID.H;
    const g = c.getContext('2d');
    for (let y = 0; y < RAID.ROWS; y++) {
      for (let x = 0; x < RAID.COLS; x++) {
        const t = this.tiles[y * RAID.COLS + x];
        const px = x * TILE, py = y * TILE;
        const h = hash2(x, y, this.seed);
        if (t === DEEP || t === WATER) {
          facetTile(g, px, py, TILE, t === DEEP ? pal.deep : pal.water, h, hash2(x, y, this.seed + 7));
          if (h > 0.88) {
            g.fillStyle = 'rgba(255,255,255,0.05)';
            g.fillRect(px, py, TILE, TILE);
          }
        } else if (t === SAND) {
          facetTile(g, px, py, TILE, pal.sand, h, hash2(x, y, this.seed + 7));
          g.fillStyle = pal.wetSand;
          const near = (xx, yy) => {
            if (xx < 0 || yy < 0 || xx >= RAID.COLS || yy >= RAID.ROWS) return false;
            return this.tiles[yy * RAID.COLS + xx] <= WATER;
          };
          if (near(x, y - 1)) g.fillRect(px, py, TILE, 3);
          if (near(x, y + 1)) g.fillRect(px, py + TILE - 3, TILE, 3);
          if (near(x - 1, y)) g.fillRect(px, py, 3, TILE);
          if (near(x + 1, y)) g.fillRect(px + TILE - 3, py, 3, TILE);
        } else {
          facetTile(g, px, py, TILE, pal.ground, h, hash2(x, y, this.seed + 7));
          if (theme === 'fangs') {
            if (h > 0.91) {
              g.fillStyle = pal.tuft;
              g.fillRect(px + 6, py + 9, 1, 4);
              g.fillRect(px + 9, py + 8, 1, 5);
            } else if (h > 0.84) {
              drawPawStamp(g, px + (h * 5) % 4, py + (h * 9) % 4, pal.accent);
            } else if (h > 0.78) {
              g.fillStyle = '#7a5a28';
              g.fillRect(px + 5, py + 8, 4, 2);
            }
          } else if (theme === 'smoke') {
            if (h > 0.93) {
              g.fillStyle = '#2a2e2c';
              g.fillRect(px + 6, py + 6, 3, 3);
            } else if (h > 0.86) {
              g.fillStyle = pal.tuft;
              g.fillRect(px + 5, py + 8, 1, 5);
              g.fillRect(px + 9, py + 7, 1, 4);
            } else if (h > 0.78) {
              g.fillStyle = 'rgba(18,20,18,0.28)';
              g.fillRect(px, py, TILE, TILE);
            }
          } else if (theme === 'iron') {
            if (h > 0.93) {
              g.fillStyle = '#c46a3a';
              g.fillRect(px + 5, py + 6, 4, 2);
            } else if (h > 0.86) {
              g.fillStyle = pal.tuft;
              g.fillRect(px + 6, py + 9, 1, 4);
              g.fillRect(px + 10, py + 8, 1, 3);
            } else if (h > 0.80) {
              g.fillStyle = '#5a3028';
              g.fillRect(px + 3, py + 9, 7, 2);
            }
          } else if (h > 0.97) {
            g.fillStyle = pal.accent;
            g.fillRect(px + 7, py + 7, 2, 2);
          } else if (h > 0.94) {
            g.fillStyle = pal.tuft;
            g.fillRect(px + 6, py + 9, 1, 4);
            g.fillRect(px + 9, py + 8, 1, 5);
          }
        }
      }
    }
    this.terrain = c;
  }

  clampWalkable(x, y) {
    if (this.walkable(x, y)) return { x, y };
    for (let r = TILE; r <= 96; r += TILE) {
      for (let a = 0; a < 16; a++) {
        const px = x + Math.cos((a / 16) * Math.PI * 2) * r;
        const py = y + Math.sin((a / 16) * Math.PI * 2) * r;
        if (this.walkable(px, py)) return { x: px, y: py };
      }
    }
    return { x: this.landing.x, y: this.landing.y };
  }

  movePartyTo(x, y) {
    if (this.flyingIn() || this.busy) return;
    const p = this.clampWalkable(x, y);
    this.party.target = p;
    this.party.job = null;
  }

  interact(hit) {
    if (!hit || this.flyingIn()) return;
    if (hit.type === 'loot' && !hit.obj.taken) {
      this.party.target = { x: hit.obj.x, y: hit.obj.y + 10 };
      this.party.job = { type: 'loot', obj: hit.obj };
    } else if (hit.type === 'drop' && !hit.obj.taken) {
      this.party.target = { x: hit.obj.x, y: hit.obj.y };
      this.party.job = { type: 'drop', obj: hit.obj };
    } else if (hit.type === 'building' && !hit.obj.ruined) {
      this.party.target = { x: hit.obj.x - 16, y: hit.obj.y + 6 };
      this.party.job = { type: 'smash', obj: hit.obj };
    } else if (hit.type === 'animal' && hit.obj.alive) {
      this.party.target = { x: hit.obj.x, y: hit.obj.y + 8 };
      this.party.job = { type: 'hunt', obj: hit.obj };
    } else if ((hit.type === 'den' || hit.type === 'lair') && hit.obj && !hit.obj.cleared) {
      this.party.target = { x: hit.obj.x, y: hit.obj.y + 12 };
      this.party.job = { type: 'enter', obj: hit.obj };
    }
  }

  hitTest(wx, wy) {
    if (this.flyingIn()) return null;
    if (this.leftBalloon && Math.hypot(wx - (this.landing.x - 18), wy - this.landing.y) < 26) {
      return { type: 'balloon' };
    }
    let best = null, bestD = 28;
    if (this.lair && !this.lair.cleared) {
      const d = Math.hypot(wx - this.lair.x, wy - (this.lair.y - 20));
      if (d < 42) { bestD = d; best = { type: 'lair', obj: this.lair }; }
    }
    for (const den of this.dens) {
      if (den.cleared) continue;
      const d = Math.hypot(wx - den.x, wy - (den.y - 10));
      if (d < Math.min(bestD, 24)) { bestD = d; best = { type: 'den', obj: den }; }
    }
    for (const a of this.animals) {
      if (!a.alive) continue;
      const dist = Math.hypot(wx - a.x, wy - (a.y - 6));
      if (dist < Math.min(bestD, 20)) { bestD = dist; best = { type: 'animal', obj: a }; }
    }
    for (const d of this.drops) {
      if (d.taken) continue;
      const dist = Math.hypot(wx - d.x, wy - (d.y - 10));
      if (dist < Math.min(bestD, 18)) { bestD = dist; best = { type: 'drop', obj: d }; }
    }
    for (const b of this.buildings) {
      if (b.ruined) continue;
      const d = Math.hypot(wx - b.x, wy - (b.y - 16));
      if (d < bestD) { bestD = d; best = { type: 'building', obj: b }; }
    }
    for (const n of this.loot) {
      if (n.taken) continue;
      const d = Math.hypot(wx - n.x, wy - (n.y - 8));
      if (d < Math.min(bestD, 20)) { bestD = d; best = { type: 'loot', obj: n }; }
    }
    return best;
  }

  retreatToLanding() {
    this.party.x = this.landing.x;
    this.party.y = this.landing.y;
    this.party.target = null;
    this.party.job = null;
    this.party.anim = 'idle';
    for (const p of this.patrols) {
      if (p.state === 'chase' || p.state === 'confused') {
        p.state = 'return';
      }
    }
  }

  encounterProgress() {
    return { seed: this.seed, dens: this.dens.filter((d) => d.cleared).map((d) => d.id),
      lair: !!this.lair?.cleared };
  }

  restoreEncounters(progress) {
    if (!progress || progress.seed !== this.seed) return;
    const cleared = new Set(progress.dens || []);
    for (const den of this.dens) den.cleared = cleared.has(den.id);
    if (this.lair) this.lair.cleared = !!progress.lair;
    this.cleared = this.allEncountersCleared();
  }

  allEncountersCleared() {
    return this._isFangs() ? !!this.lair?.cleared && this.dens.length > 0 && this.dens.every((d) => d.cleared)
      : !this.boss?.alive && this.patrols.every((p) => !p.alive);
  }

  resolveEncounter(source) {
    if (!source) return;
    const refs = source.refs || (source.ref ? [source.ref] : []);
    if (source.kind === 'patrol') {
      for (const ref of refs) {
        if (ref) ref.alive = false;
      }
      this.patrols = this.patrols.filter((p) => p.alive);
    }
    if (source.kind === 'boss' && this.boss) {
      this.boss.alive = false;
      this.cleared = true;
    }
    if ((source.kind === 'den' || source.kind === 'lair') && source.ref) {
      source.ref.cleared = true;
      this.cleared = this.allEncountersCleared();
    }
  }

  takeEvent() {
    const out = this.events;
    this.events = [];
    return out;
  }

  update(dt) {
    if (this.flyIn) {
      this.flyIn.t += dt;
      if (this.flyIn.t >= this.flyIn.dur) this.flyIn = null;
      return this.takeEvent();
    }
    this._updateParty(dt);
    this._updateDrops(dt);
    this._updateAnimals(dt);
    this._updatePatrols(dt);
    this._updateBoss(dt);
    this._checkContact();
    this._checkReturnHome();
    return this.takeEvent();
  }

  _stepToward(g, tx, ty, speed, dt) {
    const dx = tx - g.x, dy = ty - g.y;
    const dist = Math.hypot(dx, dy);
    if (dist < 2) return true;
    const step = Math.min(dist, speed * dt);
    const ux = dx / dist, uy = dy / dist;
    const tries = [
      [g.x + ux * step, g.y + uy * step],
      [g.x + ux * step, g.y],
      [g.x, g.y + uy * step],
      [g.x + uy * step * 0.75, g.y - ux * step * 0.75],
      [g.x - uy * step * 0.75, g.y + ux * step * 0.75],
    ];
    for (const [nx, ny] of tries) {
      if (Math.hypot(nx - g.x, ny - g.y) > 0.0001 && this.walkable(nx, ny)) {
        g.x = nx; g.y = ny;
        g.face = dx >= 0 ? 1 : -1;
        g.anim = 'walk';
        return false;
      }
    }
    g.anim = 'idle';
    return false;
  }

  _updateParty(dt) {
    const p = this.party;
    const speed = Math.max(PLAYER_SPEED, combatCfg().playerSpeed || 0);
    if (p.job?.type === 'hunt' && p.job.obj?.alive) {
      const a = p.job.obj;
      const d = Math.hypot(p.x - a.x, p.y - a.y);
      if (d > HUNT_CHASE) p.target = { x: a.x, y: a.y + 4 };
      else if (d <= HUNT_REACH) p.target = null;
    }
    if (p.target) {
      const dx = p.target.x - p.x, dy = p.target.y - p.y;
      const dist = Math.hypot(dx, dy);
      if (dist < 3) {
        p.x = p.target.x; p.y = p.target.y;
        p.target = null;
        p.anim = p.job ? 'attack' : 'idle';
        p.frame = 0;
        this._arrive();
      } else {
        this._stepToward(p, p.target.x, p.target.y, speed, dt);
      }
    } else if (p.job?.type === 'chop') {
      const n = p.job.obj;
      if (!n || n.taken) {
        p.job = null;
        p.anim = 'idle';
      } else {
        p.anim = 'attack';
        const period = raidWorkPeriod(p);
        p.job.t = (p.job.t || 0) + dt;
        const kind = n.type === 'rock' ? 'stone' : 'wood';
        while (p.job && p.job.t + 1e-9 >= period && !n.taken) {
          p.job.t = Math.max(0, p.job.t - period);
          n.stock = Math.max(0, (n.stock || 1) - 1);
          this.events.push({ type: 'loot', kind, amount: 1,
            sourceId: 'node:' + n.x + ':' + n.y, total: n.max - n.stock, max: n.max, done: n.stock === 0 });
          if (n.stock <= 0) {
            n.taken = true;
            n.hive = false;
            p.job = null;
            p.anim = 'idle';
          }
        }
      }
    } else if (p.job?.type === 'smash') {
      p.anim = 'attack';
      p.job.t = (p.job.t || 0) + dt;
      if (p.job.t >= 0.55) {
        p.job.t = 0;
        const b = p.job.obj;
        if (!this.bossEnraged) {
          this.bossEnraged = true;
          this.events.push({ type: 'boss_alert' });
        }
        b.hp -= 1;
        if (b.hp <= 0) {
          b.ruined = true;
          p.job = null;
          p.anim = 'idle';
          this.events.push({ type: 'loot', kind: 'building', rewards: raidRewards(this.difficulty) });
        }
      }
    } else if (p.job?.type === 'hunt') {
      const a = p.job.obj;
      if (!a?.alive) {
        p.job = null;
        p.anim = 'idle';
      } else if (Math.hypot(p.x - a.x, p.y - a.y) > HUNT_CHASE) {
        p.target = { x: a.x, y: a.y + 8 };
      } else {
        p.anim = 'attack';
        p.job.t = (p.job.t || 0) + dt;
        if (p.job.t >= 0.5) {
          p.job.t = 0;
          a.hp = Math.max(0, a.hp - 4); a.hurtT = HURT_HOLD_S;
          if (!a.hp) this._killAnimal(a);
        }
      }
    } else if (!p.target) {
      p.anim = 'idle';
    }
    const step = p.anim === 'walk' ? 0.10 : p.anim === 'attack' ? 0.08 : 0.18;
    p.animT += dt;
    if (p.animT > step) {
      p.animT = 0;
      p.frame = (p.frame + 1) % (ANIM_FRAMES[p.anim] || 5);
    }
  }

  _arrive() {
    const job = this.party.job;
    if (!job) return;
    if (job.type === 'hunt') {
      const a = job.obj;
      if (!a?.alive) { this.party.job = null; return; }
      if (Math.hypot(this.party.x - a.x, this.party.y - a.y) > HUNT_CHASE) {
        this.party.target = { x: a.x, y: a.y + 8 };
      }
      return;
    }
    if (job.type === 'enter') {
      this._enterDen(job.obj);
      this.party.job = null;
      this.party.anim = 'idle';
      return;
    }
    if (job.type === 'loot') {
      const n = job.obj;
      if (n && (n.type === 'tree' || n.type === 'rock') && !n.taken) {
        this.party.job = { type: 'chop', obj: n, t: 0 };
        this.party.anim = 'attack';
        return;
      }
      if (!n.taken) {
        n.taken = true;
        if (n.type === 'chest') this.spawnChestDrops(n);
      }
      this.party.job = null;
      this.party.anim = 'idle';
    } else if (job.type === 'drop') {
      this._pickupDrop(job.obj);
      this.party.job = null;
      this.party.anim = 'idle';
    }
  }

  spawnChestDrops(chest) {
    const gold = 8 + Math.floor(this.rng() * 8);
    const bits = [{ kind: 'gold', amount: gold, icon: 'res_gold' }];
    if (this.rng() < 0.7) {
      const item = CHEST_ITEMS[Math.floor(this.rng() * CHEST_ITEMS.length)];
      bits.push({ kind: 'item', item, icon: ITEM_ICON(item) });
    }
    bits.forEach((b, i) => {
      const ang = -0.85 + i * 1.5;
      this.drops.push({
        ...b, taken: false, t: i * 0.18,
        x: chest.x + Math.cos(ang) * 16,
        y: chest.y + 10 + Math.sin(ang) * 8,
      });
    });
  }

  _pickupDrop(d) {
    if (!d || d.taken) return;
    d.taken = true;
    if (d.kind === 'gold') this.events.push({ type: 'loot', kind: 'gold', amount: d.amount });
    else if (d.kind === 'item') this.events.push({ type: 'loot', kind: 'item', item: d.item });
  }

  _updateDrops(dt) {
    const px = this.party.x, py = this.party.y;
    for (const d of this.drops) {
      if (d.taken) continue;
      d.t = (d.t || 0) + dt;
      if (Math.hypot(d.x - px, d.y - py) < 16) this._pickupDrop(d);
    }
  }

  _tickAnimalAnim(a, dt) {
    const wolf = a.kind === 'wolf';
    const walkN = ANIMAL_WALK_FRAMES[a.kind] || 8;
    const frames = wolf ? creatureFrames('wolf', a.anim)
      : a.anim === 'walk' ? walkN : (ANIM_FRAMES[a.anim] || 5);
    const step = wolf ? creatureStep('wolf', a.anim)
      : a.anim === 'walk' ? ANIMAL_WALK_CYCLE / walkN : a.anim === 'idle' ? 0.18 : 0.07;
    a.animT = (a.animT || 0) + dt;
    const advance = Math.floor(a.animT / step);
    if (!advance) return;
    a.animT -= advance * step;
    a.frame = a.anim === 'death' ? Math.min(frames - 1, (a.frame || 0) + advance)
      : ((a.frame || 0) + advance) % frames;
  }

  _animalRoute(a, away) {
    const angle = away ? Math.atan2(a.y - this.party.y, a.x - this.party.x) : this.rng() * Math.PI * 2;
    const clear = (dx, dy) => [0.25, 0.5, 0.75, 1].every((t) => this.walkable(a.x + dx * t, a.y + dy * t));
    // Search along a clear segment, not just a walkable end point across water.
    const distances = away ? [64, 40] : [26 + this.rng() * 28];
    for (const distance of distances) {
      for (const turn of [0, 0.5, -0.5, 1, -1, 1.6, -1.6, 2.4, -2.4, Math.PI]) {
        const dx = Math.cos(angle + turn) * distance, dy = Math.sin(angle + turn) * distance;
        if (!clear(dx, dy)) continue;
        a.wx = a.x + dx; a.wy = a.y + dy;
        return true;
      }
    }
    // Cornered: any clear short dash keeps it running instead of freezing on the spot.
    for (let k = 0; k < 16; k++) {
      const ang = (k / 16) * Math.PI * 2;
      const dx = Math.cos(ang) * 28, dy = Math.sin(ang) * 28;
      if (!clear(dx, dy)) continue;
      a.wx = a.x + dx; a.wy = a.y + dy;
      return true;
    }
    a.wx = a.x; a.wy = a.y;
    return false;
  }

  _updateAnimals(dt) {
    for (const a of this.animals) {
      if (!a.alive) {
        if ((a.corpseT || 0) > 0) {
          a.corpseT -= dt; a.deathT = (a.deathT || 0) + dt; a.anim = 'death'; this._tickAnimalAnim(a, dt);
        }
        continue;
      }
      a.hurtT = Math.max(0, (a.hurtT || 0) - dt);
      const dist = Math.hypot(a.x - this.party.x, a.y - this.party.y);
      if (dist < 110 && !a.fleeing) { a.fleeing = true; a.routeT = 0; }
      if (a.fleeing && dist > 170) {
        a.fleeing = false; a.wx = a.x; a.wy = a.y; a.wanderT = 0.8;
      }
      // Levou dano: fica parado no sprite de dano por HURT_HOLD_S antes de voltar a andar/fugir.
      if (a.hurtT > 0) { a.anim = 'idle'; a.frame = 0; a.animT = 0; continue; }
      a.routeT = (a.routeT || 0) - dt;
      a.wanderT -= dt;
      const arrived = Math.hypot(a.wx - a.x, a.wy - a.y) < 2;
      if (a.fleeing && (a.routeT <= 0 || arrived)) {
        this._animalRoute(a, true); a.routeT = 0.65;
      } else if (!a.fleeing && a.wanderT <= 0) {
        this._animalRoute(a, false); a.wanderT = 2.4 + this.rng() * 1.6;
      }
      const ox = a.x, oy = a.y;
      this._stepToward(a, a.wx, a.wy, a.fleeing ? 30 : 18, dt);
      const moving = Math.hypot(a.x - ox, a.y - oy) > 0.001;
      if (a.fleeing && !moving) {
        // Blocked by water/edge: after a beat, pick a new escape instead of standing still.
        a.stuckT = (a.stuckT || 0) + dt;
        if (a.stuckT > 0.2) { a.stuckT = 0; this._animalRoute(a, true); a.routeT = 0.4; }
      } else {
        a.stuckT = 0;
      }
      // A fleeing animal keeps its legs moving even when it is pinned, never a frozen pose.
      const anim = (moving || a.fleeing) ? 'walk' : 'idle';
      if (a.anim !== anim) { a.frame = 0; a.animT = 0; }
      a.anim = anim;
      this._tickAnimalAnim(a, dt);
    }
  }

  _killAnimal(a) {
    if (!a || !a.alive) return;
    a.alive = false; a.hp = 0;
    a.anim = 'death';
    a.frame = 0;
    a.corpseT = 1.4;
    a.deathT = 0;
    this.party.job = null;
    this.party.anim = 'idle';
    const amount = a.kind === 'wolf' ? 5 : a.kind === 'boar' ? 4 : a.kind === 'deer' ? 3 : 2;
    this.events.push({ type: 'loot', kind: 'meat', amount, sourceId: 'animal:' + a.homeX + ':' + a.homeY, total: amount, done: true });

  }

  _scream(origin) {
    if (this._isFangs()) return;
    this.events.push({ type: 'scream' });
    const ox = origin?.x ?? this.party.x;
    const oy = origin?.y ?? this.party.y;
    for (const g of this.patrols) {
      if (!g.alive) continue;
      if (Math.hypot(g.x - ox, g.y - oy) > SCREAM_RANGE) continue;
      g.heard = true;
      g.state = 'chase';
      g.confusedT = 0;
    }
  }

  _checkReturnHome() {
    if (this.busy || this.flyingIn()) return;
    const d = Math.hypot(this.party.x - this.landing.x, this.party.y - this.landing.y);
    if (d > 42) this.leftBalloon = true;
    if (this.leftBalloon && d < 18) {
      this.busy = true;
      this.events.push({ type: 'return_home' });
    }
  }

  _moveGroup(g, tx, ty, speed, dt) {
    return this._stepToward(g, tx, ty, speed, dt);
  }

  _tickGroupAnim(g, dt) {
    const step = g.anim === 'walk' ? 0.11 : 0.18;
    g.animT += dt;
    if (g.animT > step) {
      g.animT = 0;
      g.frame = (g.frame + 1) % (ANIM_FRAMES[g.anim] || 5);
    }
  }

  _updatePatrols(dt) {
    const speed = combatCfg().enemySpeed || ENEMY_SPEED;
    const px = this.party.x, py = this.party.y;
    for (const g of this.patrols) {
      if (!g.alive) continue;
      const dist = Math.hypot(g.x - px, g.y - py);
      if (dist <= ALERT_RANGE) {
        g.heard = false;
        g.state = 'chase';
        g.confusedT = 0;
        this._moveGroup(g, px, py, speed, dt);
      } else if (g.heard) {
        g.state = 'chase';
        g.confusedT = 0;
        this._moveGroup(g, px, py, speed, dt);
      } else if (g.state === 'chase') {
        g.state = 'confused';
        g.confusedT = CONFUSED_TIME;
        g.anim = 'idle';
      } else if (g.state === 'confused') {
        g.confusedT -= dt;
        g.anim = 'idle';
        if (g.confusedT <= 0) g.state = 'return';
      } else if (g.state === 'return') {
        const wp = g.waypoints[g.wi] || g.waypoints[0];
        if (this._moveGroup(g, wp.x, wp.y, speed, dt)) g.state = 'patrol';
      } else {
        const wp = g.waypoints[g.wi] || g.waypoints[0];
        if (this._moveGroup(g, wp.x, wp.y, speed * 0.85, dt)) {
          g.wi = (g.wi + 1) % g.waypoints.length;
        }
      }
      this._tickGroupAnim(g, dt);
    }
  }

  _updateBoss(dt) {
    const b = this.boss;
    if (!b?.alive) return;
    if (this.bossEnraged) {
      const rush = combatCfg().bossRushSpeed || BOSS_RUSH_SPEED;
      this._moveGroup(b, this.party.x, this.party.y, rush, dt);
    } else {
      b.anim = 'idle';
    }
    this._tickGroupAnim(b, dt);
  }

  _enterDen(den) {
    if (!den || den.cleared || this.busy) return;
    this.busy = true;
    this.party.target = null;
    this.party.job = null;
    const pack = denWaves(den.kind === 'lair' ? 'lair' : 'den', this.difficulty);
    this.events.push({
      type: 'battle',
      kind: den.kind === 'lair' ? 'lair' : 'den',
      foes: pack.foes,
      waves: pack.waves,
      bgKey: pack.bgKey,
      twinsBg: pack.twinsBg,
      source: { kind: den.kind === 'lair' ? 'lair' : 'den', ref: den },
      difficulty: this.difficulty,
    });
  }

  _checkContact() {
    if (this.busy) return;
    const px = this.party.x, py = this.party.y;
    if (this._isFangs()) {
      for (const den of this.dens) {
        if (den.cleared) continue;
        if (Math.hypot(den.x - px, den.y - py) < CONTACT_RANGE + 4) {
          this._enterDen(den);
          return;
        }
      }
      if (this.lair && !this.lair.cleared && Math.hypot(this.lair.x - px, this.lair.y - py) < CONTACT_RANGE + 16) {
        this._enterDen(this.lair);
      }
      return;
    }
    const touching = this.patrols.filter((g) => g.alive && Math.hypot(g.x - px, g.y - py) < CONTACT_RANGE);
    if (touching.length) {
      this.busy = true;
      this.party.target = null;
      const first = touching[0];
      const second = touching[1] || null;
      const ev = {
        type: 'battle',
        kind: 'patrol',
        foes: first.members,
        source: { kind: 'patrol', ref: first, refs: second ? [first, second] : [first] },
        difficulty: this.difficulty,
      };
      if (second) ev.wave = second.members;
      this.events.push(ev);
      return;
    }
    if (this.boss?.alive && Math.hypot(this.boss.x - px, this.boss.y - py) < CONTACT_RANGE + 6) {
      this.busy = true;
      this.party.target = null;
      this.events.push({
        type: 'battle',
        kind: 'boss',
        foes: [this.boss.goblin],
        source: { kind: 'boss', ref: this.boss },
        difficulty: this.difficulty,
      });
    }
  }

  draw(ctx, time, vis) {
    const sx = Math.max(0, Math.floor(vis.x0));
    const sy = Math.max(0, Math.floor(vis.y0));
    const sw = Math.min(RAID.W - sx, Math.ceil(vis.x1 - vis.x0));
    const sh = Math.min(RAID.H - sy, Math.ceil(vis.y1 - vis.y0));
    if (sw > 0 && sh > 0 && this.terrain) ctx.drawImage(this.terrain, sx, sy, sw, sh, sx, sy, sw, sh);

    if (this.showCityZone) {
      ctx.save();
      ctx.fillStyle = 'rgba(200, 40, 30, 0.22)';
      ctx.strokeStyle = 'rgba(255, 90, 70, 0.85)';
      ctx.lineWidth = 2;
      ctx.beginPath();
      ctx.ellipse(this.center.x, this.center.y, CITY_RADIUS, CITY_RADIUS * 0.72, 0, 0, Math.PI * 2);
      ctx.fill(); ctx.stroke();
      ctx.fillStyle = 'rgba(255, 210, 180, 0.92)';
      ctx.font = 'bold 10px monospace';
      ctx.textAlign = 'center';
      ctx.fillText('✕', this.center.x, this.center.y - CITY_RADIUS * 0.72 - 8);
      ctx.restore();
    }

    const drawables = [];
    if (this.flyIn) {
      const k = Math.min(1, this.flyIn.t / this.flyIn.dur);
      const ease = 1 - (1 - k) * (1 - k);
      const by = this.landing.y - 150 * (1 - ease);
      drawables.push({
        y: by,
        draw: (c) => drawBalloon(c, { x: this.landing.x - 18, y: by, repaired: true }, time, { flying: true }),
      });
    } else if (!this.showCityZone) {
      drawables.push({
        y: this.landing.y,
        draw: (c) => drawBalloon(c, { x: this.landing.x - 18, y: this.landing.y, repaired: true }, time),
      });
    }
    for (const n of this.loot) {
      if (n.taken && n.type !== 'chest') continue;
      drawables.push({
        y: n.y,
        draw: (c) => {
          if (n.type === 'tree' && !n.taken) drawTree(c, n.x, n.y, n.hive, n);
          else if (n.type === 'rock' && !n.taken) drawRock(c, n.x, n.y, n);
          else if (n.type === 'chest') drawChest(c, n.x, n.y, n.taken);
        },
      });
    }
    for (const p of this.props) {
      drawables.push({ y: p.y, draw: (c) => drawProp(c, p, time) });
    }
    for (const den of this.dens) {
      drawables.push({
        y: den.y,
        draw: (c) => {
          c.save();
          c.imageSmoothingEnabled = true; // cenario low-poly
          if (den.cleared) c.globalAlpha = 0.45;
          c.drawImage(getSprite('prop_den'), den.x - 26, den.y - 34, 52, 34);
          c.restore();
        },
      });
    }
    if (this.lair) {
      drawables.push({
        y: this.lair.y,
        draw: (c) => {
          c.save();
          c.imageSmoothingEnabled = true; // cenario low-poly
          if (this.lair.cleared) c.globalAlpha = 0.5;
          c.drawImage(getSprite('prop_den_lair'), this.lair.x - 80, this.lair.y - 78, 160, 87);
          c.restore();
        },
      });
    }
    for (const a of this.animals) {
      if (!a.alive && !(a.corpseT > 0)) continue;
      drawables.push({ y: a.y, draw: (c) => drawAnimal(c, a, time) });
    }
    for (const d of this.drops) {
      if (d.taken) continue;
      drawables.push({ y: d.y, draw: (c) => drawGroundDrop(c, d, time) });
    }
    for (const b of this.buildings) {
      drawables.push({ y: b.y, draw: (c) => drawEnemyBuilding(c, b) });
    }
    for (const g of this.patrols) {
      if (!g.alive) continue;
      drawables.push({
        y: g.y,
        draw: (c) => {
          g.members.forEach((m, i) => {
            const f = FORMATION[i] || FORMATION[0];
            drawGoblinAt(c, m, g.x + f.dx, g.y + f.dy, g.face, g.anim, g.frame);
          });
          if (g.state === 'chase') {
            c.fillStyle = '#ffcf5c';
            c.font = 'bold 16px monospace';
            c.textAlign = 'center';
            c.fillText('!', g.x, g.y - 38 + Math.sin(time * 8) * 2);
            c.textAlign = 'left';
          } else if (g.state === 'confused') {
            c.fillStyle = '#cdd3de';
            c.font = 'bold 16px monospace';
            c.textAlign = 'center';
            c.fillText('?', g.x, g.y - 38);
            c.textAlign = 'left';
          }
        },
      });
    }
    if (this.boss?.alive) {
      drawables.push({
        y: this.boss.y,
        draw: (c) => {
          drawGoblinAt(c, this.boss.goblin, this.boss.x, this.boss.y, this.boss.face, this.boss.anim, this.boss.frame, 1.65);
          c.fillStyle = '#ff8f3c';
          c.font = 'bold 9px monospace';
          c.textAlign = 'center';
          c.fillText('♛', this.boss.x, this.boss.y - 46);
          c.textAlign = 'left';
        },
      });
    }
    const ghost = this.landingGhost;
    if (ghost) {
      drawables.push({
        y: ghost.y,
        draw: (c) => {
          c.save();
          c.globalAlpha = 0.9;
          c.strokeStyle = ghost.valid ? '#75e083' : '#ff6b5e';
          c.lineWidth = 2;
          c.beginPath(); c.ellipse(ghost.x, ghost.y, 16, 10, 0, 0, Math.PI * 2); c.stroke();
          drawBalloon(c, { x: ghost.x, y: ghost.y, repaired: true }, time, { flying: true });
          c.fillStyle = ghost.valid ? '#9ff0a9' : '#ff9a90';
          c.font = 'bold 12px monospace';
          c.textAlign = 'center';
          c.fillText(ghost.valid ? '✓' : '✕', ghost.x, ghost.y - 62);
          c.restore();
        },
      });
    }
    const p = this.party;
    if (!this.showCityZone && !this.flyIn) {
      drawables.push({
        y: p.y,
        draw: (c) => {
          const lead = p.goblins.find((g) => g && g.hp > 0) || p.goblins[0];
          if (lead) drawGoblinAt(c, lead, p.x, p.y, p.face, p.anim, p.frame);
          if (p.target) {
            c.strokeStyle = 'rgba(255,233,168,0.7)';
            c.lineWidth = 1.5;
            c.beginPath(); c.arc(p.target.x, p.target.y, 7, 0, Math.PI * 2); c.stroke();
          }
        },
      });
    }
    drawables.sort((a, b) => a.y - b.y);
    for (const d of drawables) d.draw(ctx);
  }
}

const ISLAND_GAP = 230;

function islandChartWidth() {
  return 90 + ISLANDS.length * ISLAND_GAP;
}

function drawMiniIsland(ctx, def, x, y, selected, i18n, locked) {
  ctx.save();
  ctx.translate(x, y);
  ctx.imageSmoothingEnabled = true; // cenario low-poly: arte interna maior que o desenho
  const spr = getSprite('island_' + (def.id || 'home'));
  ctx.drawImage(spr, -78, -58, 156, 108);
  if (locked) {
    ctx.fillStyle = 'rgba(10, 16, 28, 0.55)';
    ctx.beginPath();
    ctx.ellipse(0, 8, 78, 48, 0, 0, Math.PI * 2);
    ctx.fill();
    ctx.fillStyle = '#ffe9a8';
    ctx.font = 'bold 18px monospace';
    ctx.textAlign = 'center';
    ctx.fillText('🔒', 0, 8);
  }
  if (selected) {
    ctx.strokeStyle = locked ? '#8a8798' : '#ffe9a8';
    ctx.lineWidth = 3;
    ctx.beginPath();
    ctx.ellipse(0, 10, 88, 54, 0, 0, Math.PI * 2);
    ctx.stroke();
    ctx.strokeStyle = 'rgba(255,233,168,0.35)';
    ctx.lineWidth = 6;
    ctx.stroke();
  }
  ctx.restore();
  ctx.fillStyle = 'rgba(20,14,10,0.72)';
  ctx.fillRect(x - 70, y + 52, 140, 18);
  ctx.strokeStyle = selected ? '#ffe9a8' : '#8a6b4a';
  ctx.strokeRect(x - 70.5, y + 51.5, 141, 19);
  ctx.fillStyle = selected ? '#ffe9a8' : '#e8d5a8';
  ctx.font = 'bold 11px monospace';
  ctx.textAlign = 'center';
  ctx.fillText(i18n.t(def.nameKey), x, y + 64);
  if (!def.home) {
    let stars = '';
    for (let i = 0; i < def.difficulty; i++) stars += '★';
    ctx.fillStyle = '#ffcf5c';
    ctx.font = '10px monospace';
    ctx.fillText(stars, x, y + 82);
    if (locked) {
      ctx.fillStyle = '#cdd3de';
      ctx.font = '8px monospace';
      ctx.fillText(i18n.t('ui.island_need_balloon', { n: def.reqBalloon }), x, y + 94);
    }
  }
  ctx.textAlign = 'left';
}

function drawIslandChart(ctx, ui, { scroll, selected, i18n, balloonLevel = 1, clearedIslands = {} }) {
  ctx.imageSmoothingEnabled = true;
  ctx.drawImage(getSprite('islands_sea'), 0, 0, 640, 360);
  ctx.fillStyle = 'rgba(6, 12, 22, 0.18)';
  ctx.fillRect(0, 0, 640, 360);

  ui.woodSign(16, 10, 280, 24, i18n.t('ui.islands_title'), 12);
  ui.closeX('close_islands', 598, 8);
  ui.text(320, 48, i18n.t('ui.islands_hint'), { align: 'center', size: 9, color: '#ffe9a8' });

  const origin = 110 - scroll;
  ISLANDS.forEach((def, i) => {
    const x = origin + i * ISLAND_GAP;
    if (x < -120 || x > 760) return;
    const locked = !islandUnlocked(def, balloonLevel);
    drawMiniIsland(ctx, def, x, 150, selected === i, i18n, locked);
    if (clearedIslands[def.id]) ui.text(x, 262, '✓ OK', { align: 'center', size: 13, color: '#8dffb3' });
    ui.region('island_' + i, x - 80, 88, 160, 150);
  });

  const def = ISLANDS[selected] || ISLANDS[0];
  const unlocked = islandUnlocked(def, balloonLevel);
  if (balloonLevel < BALLOON_MAX_LEVEL) {
    ui.button('balloon_upgrade', 16, 312, 170, 32, i18n.t('ui.balloon_upgrade'), true);
  }
  if (def.home) {
    ui.button('island_go', 220, 312, 200, 32, i18n.t('ui.island_return'), true, true);
  } else {
    ui.button('island_go', 220, 312, 200, 32,
      unlocked ? i18n.t('ui.island_travel') : i18n.t('ui.island_locked'), unlocked, unlocked);
  }
}

module.exports = {
  RAID, ISLANDS, THEMES, ALERT_RANGE, ALERT_TILES, CONTACT_RANGE,
  SCREAM_TILES, SCREAM_RANGE,
  PLAYER_SPEED, ENEMY_SPEED, BOSS_RUSH_SPEED,
  BALLOON_REPAIR_COST, BALLOON_MAX_LEVEL, PARTY_LIMIT, BATTLE_LIMIT, CITY_RADIUS, LAIR_RADIUS, FORMATION,
  balloonCost, balloonUpgradeCost, islandUnlocked, togglePartyMember, themeOf,
  patrolCount, raidRewards, raidWorkPeriod, findBalloonSpot, createBalloon, balloonHit,
  drawBalloon, drawGoblinAt, drawIslandChart, islandChartWidth,
  makePatrolMembers, makeBossMember, makeWolfPack, makeWarTwins, denWaves, RaidIsland,
};
