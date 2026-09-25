// ============================================================
// nodes.js — Nós de trabalho espalhados pela ilha.
//
// Dois tipos:
//   • FINITOS (naturais): árvores → madeira, pedras → pedra.
//     Quando o estoque acaba, viram toco/entulho.
//   • INFINITOS (estruturas): a Fazenda produz comida e a Mina
//     produz pedra/minério sem acabar (§2.6). Eles nascem junto
//     com a estrutura e usam o mesmo sistema de trabalho.
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

  /**
   * Sincroniza os postos de trabalho INFINITOS com as estruturas
   * construídas: Fazenda → comida, Mina → pedra/minério (§2.6).
   * Chamado no boot e sempre que uma estrutura nova é erguida.
   */
  syncFacilities(village) {
    const FACILITY_NODES = [
      { struct: 'fazenda', type: 'farm', dx: 0, dy: 34 },
      { struct: 'mina', type: 'mineshaft', dx: 0, dy: 34 },
    ];
    for (const def of FACILITY_NODES) {
      const s = village.get(def.struct);
      const existing = this.list.find((n) => n.type === def.type);
      if (!s) {
        // estrutura não existe (ou foi removida) → tira o posto
        if (existing) this.list.splice(this.list.indexOf(existing), 1);
        continue;
      }
      if (existing) {
        existing.x = s.x + def.dx;
        existing.y = s.y + def.dy;
        existing.level = s.level;
      } else {
        this.list.push({
          type: def.type, x: s.x + def.dx, y: s.y + def.dy,
          infinite: true, level: s.level,
          stock: 1, max: 1, depleted: false, worker: null,
        });
      }
    }
  }

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
        // Postos infinitos não têm sprite próprio: são marcados por um
        // pequeno letreiro no chão, ao lado da estrutura que os criou.
        if (n.infinite) {
          const label = n.type === 'farm' ? '🌾' : '⛏';
          ctx.fillStyle = 'rgba(22,16,36,0.72)';
          ctx.fillRect(n.x - 13, n.y - 16, 26, 15);
          ctx.strokeStyle = 'rgba(255,233,168,0.5)';
          ctx.lineWidth = 1;
          ctx.strokeRect(n.x - 12.5, n.y - 15.5, 25, 14);
          ctx.font = '10px monospace';
          ctx.textAlign = 'center';
          ctx.textBaseline = 'middle';
          ctx.fillStyle = '#ffe9a8';
          ctx.fillText(label, n.x, n.y - 8);
          ctx.textAlign = 'left';
          return;
        }
        const id = n.depleted
          ? (n.type === 'tree' ? 'node_tree_stump' : 'node_rock_rubble')
          : (n.type === 'tree' ? 'node_tree_0' : 'node_rock_0');
        // Nós ativos usam a arte 64px (desenhada em 48px, ancorada pela base);
        // tocos/entulho continuam pequenos (32px).
        const size = n.depleted ? 24 : 48;
        ctx.drawImage(getSprite(id), n.x - size / 2, n.y + 2 - size, size, size);
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
    // Postos infinitos são recriados a partir das estruturas no boot,
    // então não precisam ser salvos.
    return this.list
      .filter((n) => !n.infinite)
      .map(({ type, x, y, stock, max, depleted }) =>
        ({ type, x, y, stock, max, depleted }));
  }
}

module.exports = { Nodes };
