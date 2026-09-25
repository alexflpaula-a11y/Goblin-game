/**
 * tap_test.mjs — Interação REAL: toques atravessando o pipeline
 * input → update → routeTap → render, sem navegador.
 *
 * O canvas falso guarda os listeners de pointer; injetamos taps nas
 * coordenadas lógicas e conferimos o resultado pelo conjunto de
 * regiões clicáveis que a UI registra no frame seguinte.
 *
 * Uso:  node tools/tap_test.mjs        (TAP_DEBUG=1 p/ ver cada toque)
 */
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const ROOT = path.dirname(path.dirname(fileURLToPath(import.meta.url)));

let fails = 0, passes = 0;
const ok = (cond, msg) => { console.log((cond ? '  ✓ ' : '  ✗ ') + msg); cond ? passes++ : fails++; };

// ---------- canvas falso com listeners ----------
function makeCanvas(id) {
  const handlers = {};
  const el = {
    _id: id, width: 1280, height: 720, style: {},
    getContext: () => new Proxy({
      canvas: el,
      measureText: (s) => ({ width: String(s).length * 6 }),
      createRadialGradient: () => ({ addColorStop: () => {} }),
      createLinearGradient: () => ({ addColorStop: () => {} }),
    },
      { get: (t, p) => (p in t ? t[p] : () => {}), set: (t, p, v) => { t[p] = v; return true; } }),
    addEventListener(type, fn) { handlers[type] = fn; },
    removeEventListener() {},
    getBoundingClientRect: () => ({ left: 0, top: 0, width: 1280, height: 720 }),
    _handlers: handlers,
  };
  return el;
}

function makeEl(id) {
  return {
    id, style: {}, textContent: '', dataset: {},
    addEventListener() {}, appendChild() {}, setAttribute() {},
    classList: { add() {}, remove() {}, toggle() {}, contains() { return false; } },
    getBoundingClientRect: () => ({ left: 0, top: 0, width: 1280, height: 720 }),
  };
}

const elements = {};
for (const id of ['viewport', 'title', 'subtitle', 'langBtn', 'status']) elements[id] = makeEl(id);
elements.game = makeCanvas('game');

let raf = [];

function step(n = 2) {
  for (let i = 0; i < n; i++) {
    const q = raf.splice(0, raf.length);
    for (const fn of q) fn(performance.now());
  }
}

// ---------- ambiente ----------
globalThis.window = { EMBEDDED: null, innerWidth: 1280, innerHeight: 720, devicePixelRatio: 1, addEventListener() {} };
globalThis.document = {
  getElementById: (id) => elements[id] || makeEl(id),
  createElement: (tag) => (tag === 'canvas' ? makeCanvas('dyn') : makeEl(tag)),
  addEventListener() {},
  body: makeEl('body'),
};
globalThis.localStorage = { _d: {}, getItem(k) { return this._d[k] ?? null; }, setItem(k, v) { this._d[k] = v; }, removeItem(k) { delete this._d[k]; } };
globalThis.location = { search: '?demo=equip' };
globalThis.screen = { orientation: { lock: () => Promise.resolve() } };
globalThis.setInterval = () => 0;
globalThis.requestAnimationFrame = (fn) => raf.push(fn);
globalThis.fetch = async (url) => {
  const p = path.join(ROOT, url);
  try {
    const data = fs.readFileSync(p);
    return { ok: true, json: async () => JSON.parse(data), text: async () => String(data) };
  } catch {
    return { ok: false, json: async () => { throw new Error('404'); }, text: async () => { throw new Error('404'); } };
  }
};
globalThis.Image = class {
  set src(v) { this._src = v; queueMicrotask(() => this.onload?.()); }
  get src() { return this._src; }
};

// ---------- módulos (uma única sessão) ----------
const modules = {}, cache = {};
const order = JSON.parse(fs.readFileSync(path.join(ROOT, 'js/_order.json'), 'utf8'));
for (const nm of order) {
  modules[nm] = new Function('module', 'exports', 'require',
    fs.readFileSync(path.join(ROOT, 'js', nm), 'utf8'));
}
function req(nm) {
  if (!cache[nm]) {
    const m = { exports: {} };
    cache[nm] = m;
    modules[nm](m, m.exports, req);
  }
  return cache[nm].exports;
}

// captura as regiões do último frame
const { UI } = req('ui.js');
let lastEls = [];
UI.prototype.begin = function () { this.els = []; lastEls = this.els; };
if (process.env.TAP_DEBUG) {
  const origHit = UI.prototype.hit;
  UI.prototype.hit = function (t) {
    const r = origHit.call(this, t);
    console.log('    [hit]', JSON.stringify(t), '→', r);
    return r;
  };
}

const DEBUG = !!process.env.TAP_DEBUG;
const regions = () => lastEls;
const region = (id) => regions().find((r) => r.id === id);
const center = (r) => ({ x: r.x + r.w / 2, y: r.y + r.h / 2 });
const has = (id) => !!region(id);

/** Injeta um toque (down+up rápidos, sem movimento) em coords lógicas. */
function tap(x, y) {
  const h = elements.game._handlers;
  const ev = { pointerId: 7, clientX: x * 2, clientY: y * 2 };
  h.pointerdown(ev);
  h.pointerup(ev);
  step(2);
  if (DEBUG) console.log('    [tap]', x.toFixed(0), y.toFixed(0), '→', regions().map((r) => r.id).join(','));
}
const tapRegion = (id) => {
  const r = region(id);
  if (!r) throw new Error('região não encontrada: ' + id);
  const c = center(r);
  tap(c.x, c.y);
};

// ============================================================
console.log('\x1b[1mTAP — equipar: anel de espaços em volta do goblin\x1b[0m');
req('main.js');
await new Promise((r) => setTimeout(r, 300));
step(3);

const slotIds = regions().filter((r) => r.id.startsWith('slot_')).map((r) => r.id.slice(5));
ok(slotIds.length === 10, 'anel completo: 10 espaços', slotIds.join(','));
ok(['capacete', 'peitoral', 'botas', 'calca', 'anel1', 'anel2',
  'arma_primaria', 'arma_secundaria', 'runa', 'colar']
  .every((k) => slotIds.includes(k)), 'todos os espaços esperados presentes');
ok(has('eqtab_0') && has('eqtab_1') && has('eqtab_2'), '3 abas: equipamento/alimentos/habilidades');

// ---- equipar peitoral de ferro ----
tapRegion('slot_peitoral');
ok(has('eqdo_peitoral_:_peitoral_ferro'), 'painel lista o peitoral de ferro');
ok(!has('eqdo_peitoral_:_espada_ferro'), 'espada não aparece no espaço de peitoral');

tapRegion('eqdo_peitoral_:_peitoral_ferro');
ok(has('equn_peitoral'), 'peitoral equipado (botão Remover apareceu)');
ok(!has('eqdo_peitoral_:_peitoral_ferro'), 'peitoral saiu do armazém');

// ---- desequipar devolve ----
tapRegion('equn_peitoral');
ok(has('eqdo_peitoral_:_peitoral_ferro'), 'desequipar devolve o peitoral ao armazém');

// ---- armas: primária e secundária ----
tapRegion('slot_arma_primaria');
ok(has('eqdo_arma_primaria_:_espada_ferro'), 'espada listada p/ arma primária');
ok(!has('eqdo_arma_primaria_:_escudo_madeira'), 'escudo NÃO serve de arma primária');
tapRegion('slot_arma_secundaria');
ok(has('eqdo_arma_secundaria_:_escudo_madeira'), 'escudo listado p/ arma secundária');

// ---- dois anéis ----
tapRegion('slot_anel1');
ok(has('eqdo_anel1_:_anel_cobre'), 'anel I aceita anel de cobre');
tapRegion('slot_anel2');
ok(has('eqdo_anel2_:_anel_cobre'), 'anel II também aceita');

// ============================================================
console.log('\x1b[1mTAP — aba habilidades\x1b[0m');
tapRegion('eqtab_2');
ok(regions().some((r) => r.id.startsWith('abeq_')), 'catálogo de habilidades listado');
ok(has('abslot_0') && has('abslot_1'), '2 espaços de habilidade');
ok(!regions().some((r) => r.id.startsWith('slot_')), 'anel de espaços sumiu nesta aba');

tapRegion('abeq_investida');
ok(has('abun_0'), 'habilidade equipada (botão de remover)');
tapRegion('abeq_investida');
ok(!has('abun_0'), 'tocar de novo remove a habilidade');

// ============================================================
console.log('\x1b[1mTAP — aba alimentos (dar comida ao goblin)\x1b[0m');
tapRegion('eqtab_1');
ok(has('pick_bread'), 'pratos guardados aparecem (pão)');
ok(regions().some((r) => r.id.startsWith('feed_')), 'goblins listados p/ alimentar');

tapRegion('pick_bread');       // escolhe o pão
tapRegion('feed_0');           // alimenta o goblin ferido
ok(!has('pick_bread'), 'pão consumido ao alimentar (despensa vazia)');

// ============================================================
console.log('\x1b[1mTAP — voltar p/ o armazém e o mundo\x1b[0m');
tapRegion('back_eq');
ok(has('inv_equip') && has('inv_upgrade'), 'voltou para a tela do armazém');
const cells = regions().filter((r) => r.id.startsWith('invs_'));
ok(cells.length === 7, 'grade do armazém com os 7 itens do kit', `${cells.length} células`);
ok(regions().filter((r) => r.id === 'invs_anel_cobre').length === 2, '2 anéis = 2 células');

tapRegion('back_world');
ok(regions().some((r) => r.id === 'armazem_btn'), 'botão ARMAZÉM aparece no mundo');

console.log(`\n  ${passes} passaram · ${fails} falharam`);
process.exit(fails ? 1 : 0);
