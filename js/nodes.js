// ============================================================
// nodes.js — Nós de recurso FINITOS espalhados pela ilha
// (árvores → madeira, pedras → pedra). Quando o estoque acaba,
// vira toco/entulho. Replantio/Mina entram em fases futuras.
// ============================================================
const { getSprite } = require('assetLoader.js');
const { BAL } = require('balance.js');
const { WORLD } = require('world.js');
function mulberry32(seed) {
  let a = seed >>> 0;
  return function () {
    a |= 0; a = (a + 0x6D2B79F5) | 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

class Nodes {
  constructor(world, data) {
    this.world = world;
    if (data && data.length) {
      this.list = data.map((d) => ({ worker: null, ...d }));
    } else {
      this.list = this.generate();
    }
  }

  generate() {
    const cfg = BAL.nodes || { treeCount: 90, rockCount: 55, treeStock: 15, rockStock: 12 };
    const rnd = mulberry32(42);
    const out = [];
    const clearing = this.world.clearing;

    const tryPlace = (type) => {
      for (let attempt = 0; attempt < 60; attempt++) {
        const tx = 2 + Math.floor(rnd() * (WORLD.COLS - 4));
        const ty = 2 + Math.floor(rnd() * (WORLD.ROWS - 4));
        if (this.world.tiles[ty * WORLD.COLS + tx] !== 3) continue; // só grama
        const x = tx * WORLD.TILE + 8 + Math.floor(rnd() * 8) - 4;
        const y = ty * WORLD.TILE + 8 + Math.floor(rnd() * 8) - 4;
        // longe da clareira da vila
        if (Math.hypot(x - clearing.x, y - clearing.y) < clearing.r + 24) continue;
        // distância mínima entre nós
        let ok = true;
        for (const n of out) {
          if (Math.hypot(n.x - x, n.y - y) < 26) { ok = false; break; }
        }
        if (!ok) continue;
        const stock = type === 'tree' ? cfg.treeStock : cfg.rockStock;
        out.push({ type, x, y, stock, max: stock, depleted: false, worker: null });
        return true;
      }
      return false;
    };

    for (let i = 0; i < cfg.treeCount; i++) tryPlace('tree');
    for (let i = 0; i < cfg.rockCount; i++) tryPlace('rock');
    return out;
  }

  alive() { return this.list.filter((n) => !n.depleted); }

  hitTest(wx, wy) {
    for (let i = this.list.length - 1; i >= 0; i--) {
      const n = this.list[i];
      if (n.depleted) continue;
      if (Math.abs(wx - n.x) <= 14 && wy <= n.y + 4 && wy >= n.y - 30) return n;
    }
    return null;
  }

  // Manda o walker livre mais próximo trabalhar no nó
  assign(node, walkers) {
    if (!node || node.depleted || node.worker != null) return null;
    let best = null, bestD = Infinity;
    for (const w of walkers) {
      if (w.job) continue;
      const d = Math.hypot(w.x - node.x, w.y - node.y);
      if (d < bestD) { bestD = d; best = w; }
    }
    if (!best) return null;
    best.job = { type: 'goto', node };
    node.worker = best.i;
    return best;
  }

  drawList() {
    return this.list.map((n) => ({
      y: n.y,
      draw: (ctx) => {
        const id = n.depleted
          ? (n.type === 'tree' ? 'node_tree_stump' : 'node_rock_rubble')
          : (n.type === 'tree' ? 'node_tree_0' : 'node_rock_0');
        ctx.drawImage(getSprite(id), n.x - 16, n.y - 30, 32, 32);
        // barra de estoque (quando já foi coletado ou tem trabalhador)
        if (!n.depleted && (n.stock < n.max || n.worker != null)) {
          ctx.fillStyle = 'rgba(0,0,0,0.55)';
          ctx.fillRect(n.x - 10, n.y - 36, 20, 3);
          ctx.fillStyle = n.type === 'tree' ? '#c9a24a' : '#9aa0ad';
          ctx.fillRect(n.x - 10, n.y - 36, 20 * (n.stock / n.max), 3);
        }
      },
    }));
  }

  serialize() {
    return this.list.map(({ type, x, y, stock, max, depleted }) =>
      ({ type, x, y, stock, max, depleted }));
  }
}

module.exports = { Nodes };
