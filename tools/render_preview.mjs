/**
 * render_preview.mjs — Gera uma PRÉVIA VISUAL das telas sem navegador.
 *
 * Roda o jogo inteiro (main.js incluído) num DOM falso, mas com um
 * canvas que REGISTRA cada chamada de desenho em JSON. O
 * tools/replay_preview.py reproduz essas chamadas numa imagem PNG
 * de verdade (com os sprites reais), para inspecionar o layout.
 *
 * Uso:  node tools/render_preview.mjs ?demo=armazem
 *       node tools/render_preview.mjs ?demo=equip
 *       node tools/render_preview.mjs            (mundo)
 * Saída: tools/preview/<demo>.json
 */
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const ROOT = path.dirname(path.dirname(fileURLToPath(import.meta.url)));
const query = process.argv[2] || '';
const name = (query.replace(/^\?demo=/, '') || 'world');

// ---------- canvas gravador ----------
const calls = [];
let cur = null;

function makeCtx(canvas, record = true) {
  if (!record) {
    // canvas offscreen (terreno etc.): só precisa existir, não grava
    const noop = () => {};
    return new Proxy({
      canvas,
      measureText: (s) => ({ width: String(s).length * 6 }),
      createRadialGradient: () => ({ addColorStop: noop }),
      createLinearGradient: () => ({ addColorStop: noop }),
      setLineDash: noop,
    }, {
      get(t, p) { if (p in t) return t[p]; return noop; },
      set(t, p, v) { t[p] = v; return true; },
    });
  }
  const state = {
    fillStyle: '#000', strokeStyle: '#000', lineWidth: 1, font: '10px monospace',
    textAlign: 'left', textBaseline: 'alphabetic', globalAlpha: 1,
    imageSmoothingEnabled: true, _dash: [],
  };
  const ctx = {
    canvas,
    ...state,
    setLineDash(d) { this._dash = d; calls.push({ op: 'setLineDash', args: [d] }); },
    measureText: (s) => ({ width: String(s).length * 6 }),
    createRadialGradient(cx, cy, r0, cx2, cy2, r1) {
      const g = { _grad: { cx: cx2, cy: cy2, r: r1 }, stops: [] };
      g.addColorStop = (o, c) => g.stops.push([o, c]);
      return g;
    },
    beginPath() { cur = { ops: [] }; },
    closePath() { cur?.ops.push(['close']); },
    moveTo(x, y) { (cur ||= { ops: [] }).ops.push(['M', x, y]); },
    lineTo(x, y) { (cur ||= { ops: [] }).ops.push(['L', x, y]); },
    arc(x, y, r, a0, a1) { (cur ||= { ops: [] }).ops.push(['arc', x, y, r, a0, a1]); },
    ellipse(x, y, rx, ry, rot, a0, a1) { (cur ||= { ops: [] }).ops.push(['ellipse', x, y, rx, ry]); },
    rect(x, y, w, h) { (cur ||= { ops: [] }).ops.push(['rect', x, y, w, h]); },
    roundRect(x, y, w, h, r) { (cur ||= { ops: [] }).ops.push(['roundrect', x, y, w, h, r]); },
    fill() {
      if (!cur) return;
      calls.push({ op: 'path', sub: 'fill', ops: cur.ops,
        style: this.fillStyle, alpha: this.globalAlpha });
      cur = null;
    },
    stroke() {
      if (!cur) return;
      calls.push({ op: 'path', sub: 'stroke', ops: cur.ops,
        style: this.strokeStyle, lw: this.lineWidth, alpha: this.globalAlpha });
      cur = null;
    },
    clip() {
      if (!cur) return;
      calls.push({ op: 'clip', ops: cur.ops });
      cur = null;
    },
    fillRect(x, y, w, h) {
      calls.push({ op: 'fillRect', args: [x, y, w, h],
        style: this.fillStyle, alpha: this.globalAlpha });
    },
    strokeRect(x, y, w, h) {
      calls.push({ op: 'strokeRect', args: [x, y, w, h],
        style: this.strokeStyle, lw: this.lineWidth, alpha: this.globalAlpha });
    },
    fillText(t, x, y) {
      calls.push({ op: 'fillText', args: [String(t), x, y], style: this.fillStyle,
        font: this.font, align: this.textAlign, base: this.textBaseline,
        alpha: this.globalAlpha });
    },
    drawImage(img, ...a) {
      calls.push({ op: 'drawImage', src: img._src || img._id || '?', args: a });
    },
    save() { calls.push({ op: 'save' }); },
    restore() { calls.push({ op: 'restore' }); },
    translate(x, y) { calls.push({ op: 'translate', args: [x, y] }); },
    scale(x, y) { calls.push({ op: 'scale', args: [x, y] }); },
    setTransform(a, b, c, d, e, f) { calls.push({ op: 'setTransform', args: [a, b, c, d, e, f] }); },
  };
  // propriedades de estilo gravadas por atribuição
  for (const k of ['fillStyle', 'strokeStyle', 'lineWidth', 'font', 'textAlign', 'textBaseline', 'globalAlpha']) {
    Object.defineProperty(ctx, k, {
      get() { return state[k]; },
      set(v) { state[k] = v; },
    });
  }
  return ctx;
}

function makeCanvas(id, record = true) {
  const el = {
    _id: id, width: 1280, height: 720, style: {},
    getContext: () => makeCtx(el, record),
    addEventListener() {}, removeEventListener() {},
    getBoundingClientRect: () => ({ left: 0, top: 0, width: 1280, height: 720 }),
  };
  return el;
}

// ---------- DOM falso ----------
const elements = {};
function makeEl(id) {
  return {
    id, style: {}, textContent: '', dataset: {},
    addEventListener() {}, appendChild() {}, setAttribute() {},
    getBoundingClientRect: () => ({ left: 0, top: 0, width: 1280, height: 720 }),
  };
}
for (const id of ['viewport', 'title', 'subtitle', 'langBtn', 'status']) elements[id] = makeEl(id);
elements.game = makeCanvas('game');

globalThis.window = { EMBEDDED: null, innerWidth: 1280, innerHeight: 720, devicePixelRatio: 1, addEventListener() {} };
globalThis.document = {
  getElementById: (id) => elements[id],
  createElement: (tag) => (tag === 'canvas' ? makeCanvas('dyn-' + Math.random(), false) : makeEl(tag)),
  addEventListener() {},
  body: makeEl('body'),
};
globalThis.localStorage = { _d: {}, getItem(k) { return this._d[k] ?? null; }, setItem(k, v) { this._d[k] = v; }, removeItem(k) { delete this._d[k]; } };
globalThis.location = { search: query };
globalThis.screen = { orientation: { lock: () => Promise.resolve() } };
globalThis.setInterval = () => 0;
const raf = [];
globalThis.requestAnimationFrame = (fn) => raf.push(fn);

// fetch: serve arquivos do disco (manifest, i18n, balance)
globalThis.fetch = async (url) => {
  const p = path.join(ROOT, url.replace(/^\.\//, ''));
  try {
    const data = fs.readFileSync(p);
    return { ok: true, json: async () => JSON.parse(data), text: async () => String(data) };
  } catch {
    return { ok: false, json: async () => { throw new Error('404 ' + url); }, text: async () => { throw new Error('404'); } };
  }
};

// Image: carrega na hora e guarda o src (o replay resolve o PNG)
let imgSeq = 0;
globalThis.Image = class {
  constructor() { this._id = 'img' + (imgSeq++); }
  set src(v) {
    this._src = v;
    queueMicrotask(() => this.onload?.());
  }
  get src() { return this._src; }
};

// ---------- módulos ----------
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

// o mundo fica fora da prévia (só as telas de UI interessam aqui)
const { World } = req('world.js');
World.prototype.draw = function () {};

// captura as regiões clicáveis do último frame (p/ checar layout)
const { UI } = req('ui.js');
let lastEls = null;
UI.prototype.begin = function () { this.els = []; lastEls = this.els; };

// ---------- roda ----------
req('main.js');
await new Promise((r) => setTimeout(r, 400));   // init() assíncrono

function step(n = 3) {
  for (let i = 0; i < n; i++) {
    const q = raf.splice(0, raf.length);
    for (const fn of q) fn(performance.now());
  }
}
step(4);

const out = path.join(ROOT, 'tools/preview');
fs.mkdirSync(out, { recursive: true });
fs.writeFileSync(path.join(out, name + '.json'), JSON.stringify({
  width: 1280, height: 720, logical: [640, 360], calls,
  regions: lastEls || [],
}));
console.log(`OK → tools/preview/${name}.json  (${calls.length} chamadas, ${lastEls?.length || 0} regiões)`);
process.exit(0);
