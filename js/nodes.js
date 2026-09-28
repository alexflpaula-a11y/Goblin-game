// ============================================================
// nodes.js — Nós de trabalho espalhados pela ilha.
//
// Tipos:
//   • FINITOS (naturais): árvores → madeira, pedras → pedra.
//     Quando o estoque acaba, viram toco/entulho.
//   • DIVINOS (renováveis): a Grande Árvore faz árvores brotarem e o
//     Golem arremessa novas rochas. A ilha inteira comporta no máximo
//     40 árvores e 40 pedras, sempre longe das estruturas.
//   • INFINITO (estrutura): a Fazenda produz comida sem acabar.
// ============================================================
const { getSprite } = require('assetLoader.js');
const { BAL } = require('balance.js');
const { WORLD } = require('world.js');
const ISLAND_NODE_CAP = 40;
const GROWTH_FRAMES = { tree: 24, rock: 16 };

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
      // Migração: saves antigos podiam conter o posto infinito da Mina.
      // Ele não existe mais. Nós divinos restaurados já voltam crescidos.
      this.list = data
        .filter((d) => d.type !== 'mineshaft')
        .map((d) => ({
          worker: null, age: d.divine ? 99 : 0,
          growth: d.divine ? 1 : undefined,
          ...d,
        }));
    } else {
      this.list = this.generate();
    }
    this.enforceIslandCaps();
  }

  generate() {
    // Começa abaixo do teto para as divindades terem espaço para repor
    // recursos assim que forem ativadas.
    const cfg = BAL.nodes || { treeCount: 24, rockCount: 24, treeStock: 15, rockStock: 12 };
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

  /** Migra saves antigos sem jamais deixar mais de 40 nós ativos por tipo. */
  enforceIslandCaps() {
    for (const type of ['tree', 'rock']) {
      let active = 0;
      this.list = this.list.filter((n) => {
        if (n.type !== type || n.depleted) return true;
        active += 1;
        return active <= ISLAND_NODE_CAP;
      });
    }
  }

  alive() { return this.list.filter((n) => !n.depleted); }

  /** Total coletável na ilha, natural + divino. */
  countActive(type) {
    return this.list.filter((n) => n.type === type && !n.depleted).length;
  }

  /** Quantidade criada por divindade ainda coletável. */
  countDivine(type) {
    return this.list.filter((n) => n.divine && n.type === type && !n.depleted).length;
  }

  /**
   * Procura grama segura para um milagre. O raio de 190 px em torno de
   * TODA estrutura é proibido, e os nós também mantêm espaço entre si.
   * A origem opcional limita o alcance do arremesso do Golem.
   */
  findDivineSite(type, structures, rng = Math.random, origin = null, range = {}) {
    const minFromStructures = 190;
    const minFromOrigin = range.minFromOrigin ?? 0;
    const maxFromOrigin = range.maxFromOrigin ?? Infinity;
    const clearing = this.world.clearing;

    for (let attempt = 0; attempt < 360; attempt++) {
      const tx = 2 + Math.floor(rng() * (WORLD.COLS - 4));
      const ty = 2 + Math.floor(rng() * (WORLD.ROWS - 4));
      if (this.world.tiles[ty * WORLD.COLS + tx] !== 3) continue;
      const x = tx * WORLD.TILE + 8 + Math.floor(rng() * 9) - 4;
      const y = ty * WORLD.TILE + 8 + Math.floor(rng() * 9) - 4;

      // Além de conferir cada prédio, preserva uma faixa larga em torno
      // da clareira, inclusive quando a vila ainda tem poucas estruturas.
      if (Math.hypot(x - clearing.x, y - clearing.y) < clearing.r + 72) continue;
      if ((structures || []).some((s) => Math.hypot(x - s.x, y - s.y) < minFromStructures)) continue;
      if (this.list.some((n) => !n.depleted && Math.hypot(x - n.x, y - n.y) < 38)) continue;
      if (origin) {
        const d = Math.hypot(x - origin.x, y - origin.y);
        if (d < minFromOrigin || d > maxFromOrigin) continue;
      }
      return { x, y, type };
    }
    return null;
  }

  /**
   * Materializa um nó divino sem ultrapassar o teto TOTAL da ilha.
   * Um toco/entulho divino antigo é limpo antes de sua reposição.
   */
  spawnDivine(type, site) {
    if (!site || (type !== 'tree' && type !== 'rock')) return null;
    if (this.countActive(type) >= ISLAND_NODE_CAP) return null;
    const divine = this.list.filter((n) => n.divine && n.type === type);
    if (divine.length >= ISLAND_NODE_CAP) {
      const spent = divine.find((n) => n.depleted);
      if (!spent) return null;
      const i = this.list.indexOf(spent);
      if (i >= 0) this.list.splice(i, 1);
    }

    const cfg = BAL.nodes || {};
    const stock = type === 'tree' ? (cfg.treeStock ?? 15) : (cfg.rockStock ?? 12);
    const node = {
      type, x: site.x, y: site.y,
      stock, max: stock, depleted: false, worker: null,
      divine: true, growth: 0, age: 0,
    };
    this.list.push(node);
    return node;
  }

  /** Faz árvores brotarem e pedras assentarem depois do impacto. */
  update(dt) {
    for (const n of this.list) {
      if (!n.divine) continue;
      n.age = (n.age || 0) + dt;
      if ((n.growth ?? 1) < 1) {
        const duration = n.type === 'tree' ? 2.2 : 0.65;
        n.growth = Math.min(1, n.growth + dt / duration);
      }
    }
  }

  /**
   * Sincroniza o único posto de trabalho infinito restante:
   * Fazenda → comida. Chamado no boot e após construir/melhorar.
   */
  syncFacilities(village) {
    // Remove qualquer resquício da Mina vindo de um save antigo.
    this.list = this.list.filter((n) => n.type !== 'mineshaft');
    const FACILITY_NODES = [
      { struct: 'fazenda', type: 'farm', dx: 0, dy: 34 },
    ];
    for (const def of FACILITY_NODES) {
      const s = village.get(def.struct);
      const existing = this.list.find((n) => n.type === def.type);
      if (!s) {
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
      if (n.depleted || (n.divine && (n.growth ?? 1) < 0.82)) continue;
      if (Math.abs(wx - n.x) <= 14 && wy <= n.y + 4 && wy >= n.y - 30) return n;
    }
    return null;
  }

  /** Próximo nó desocupado para uma tarefa automática da Área dos Goblins. */
  findAvailable(task, x, y) {
    const type = task === 'wood' ? 'tree' : task === 'stone' ? 'rock'
      : task === 'food' ? 'farm' : null;
    if (!type) return null;
    let best = null;
    let bestD = Infinity;
    for (const node of this.list) {
      if (node.type !== type || node.depleted || node.worker != null) continue;
      const d = Math.hypot((x ?? node.x) - node.x, (y ?? node.y) - node.y);
      if (d < bestD) { bestD = d; best = node; }
    }
    return best;
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
        const rawGrowth = n.divine && !n.depleted ? (n.growth ?? 1) : 1;
        const frameCount = GROWTH_FRAMES[n.type] || 1;
        const growth = Math.min(1, Math.floor(rawGrowth * (frameCount - 1)) / Math.max(1, frameCount - 1));

        if (n.divine && rawGrowth < 1) {
          // 24 quadros para o broto e 16 para o impacto da pedra.
          ctx.save();
          ctx.fillStyle = n.type === 'tree' ? 'rgba(69,48,25,0.68)' : 'rgba(120,112,94,0.58)';
          ctx.beginPath();
          ctx.ellipse(n.x, n.y + 1, 12 + growth * 5, 3 + growth * 2, 0, 0, Math.PI * 2);
          ctx.fill();
          ctx.translate(n.x, n.y + 2);
          if (n.type === 'tree') {
            const rise = 1 - Math.pow(1 - growth, 3);
            const overshoot = Math.sin(growth * Math.PI) * (1 - growth) * 0.16;
            const sway = Math.sin((n.age || 0) * 10) * (1 - growth) * 0.075;
            ctx.rotate(sway);
            ctx.scale(0.52 + rise * 0.48 + overshoot, Math.max(0.03, rise + overshoot));
          } else {
            const bounce = 0.58 + growth * 0.42 + Math.sin(growth * Math.PI * 4) * (1 - growth) * 0.22;
            ctx.rotate(Math.sin(growth * Math.PI * 3) * (1 - growth) * 0.12);
            ctx.scale(bounce, bounce);
          }
          ctx.drawImage(getSprite(id), -size / 2, -size, size, size);
          ctx.restore();

          // Mais partículas distribuídas por quadros deixam o nascimento suave.
          ctx.save();
          ctx.globalAlpha = Math.max(0, 1 - growth * 0.8);
          ctx.fillStyle = n.type === 'tree' ? '#8ed15c' : '#c4b995';
          for (let i = 0; i < 8; i++) {
            const a = (n.age || 0) * (2.2 + i * 0.17) + i * 0.83;
            const radius = 7 + growth * (10 + i % 3);
            const px = n.x + Math.cos(a) * radius;
            const py = n.y - 2 - Math.abs(Math.sin(a)) * (5 + growth * 12) - growth * 8;
            ctx.fillRect(px, py, i % 3 === 0 ? 3 : 2, 2);
          }
          ctx.restore();
        } else {
          ctx.drawImage(getSprite(id), n.x - size / 2, n.y + 2 - size, size, size);
        }
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
      .map(({ type, x, y, stock, max, depleted, divine }) =>
        ({ type, x, y, stock, max, depleted, ...(divine ? { divine: true } : {}) }));
  }
}

module.exports = { Nodes, ISLAND_NODE_CAP, GROWTH_FRAMES };
