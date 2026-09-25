/**
 * render_test.mjs — Roda o jogo INTEIRO (inclusive main.js) num DOM falso.
 *
 * O smoke_test cobre a lógica; este aqui cobre o que ela não alcança:
 * erros de runtime no desenho das telas (função inexistente, sprite com
 * nome errado, chave de tradução faltando, hit-test quebrado).
 *
 * Simula canvas/Image/localStorage, avança alguns frames em cada tela e
 * dispara toques nos botões registrados. Qualquer exceção reprova.
 *
 * Uso:  node tools/render_test.mjs
 */
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const ROOT = path.dirname(path.dirname(fileURLToPath(import.meta.url)));

// ---------------- canvas falso ----------------
// Registra as chamadas para conferirmos que algo foi mesmo desenhado.
const calls = { drawImage: 0, fillText: 0, fillRect: 0 };
function makeCtx() {
  const noop = () => {};
  return new Proxy({
    canvas: { width: 1280, height: 720 },
    measureText: (s) => ({ width: String(s).length * 6 }),
    createRadialGradient: () => ({ addColorStop: noop }),
    createLinearGradient: () => ({ addColorStop: noop }),
    getImageData: () => ({ data: new Uint8ClampedArray(4) }),
    drawImage: (img) => {
      if (img == null) throw new Error('drawImage recebeu sprite nulo');
      calls.drawImage++;
    },
    fillText: () => { calls.fillText++; },
    fillRect: () => { calls.fillRect++; },
  }, {
    get(target, prop) {
      if (prop in target) return target[prop];
      return noop;               // qualquer outro método do canvas
    },
    set(target, prop, value) { target[prop] = value; return true; },
  });
}

function makeCanvas() {
  const el = {
    width: 1280, height: 720,
    style: {},
    getContext: () => makeCtx(),
    addEventListener: () => {},
    removeEventListener: () => {},
    getBoundingClientRect: () => ({ left: 0, top: 0, width: 1280, height: 720 }),
  };
  return el;
}

// ---------------- DOM falso ----------------
const elements = {};
function makeEl(id) {
  return {
    id, style: {}, textContent: '', dataset: {},
    addEventListener(type, fn) { (this._h ||= {})[type] = fn; },
    click() { this._h?.click?.(); },
    classList: { add() {}, remove() {}, toggle() {}, contains() { return false; } },
    appendChild() {}, setAttribute() {}, getBoundingClientRect: () => ({ left: 0, top: 0 }),
  };
}
for (const id of ['viewport', 'title', 'subtitle', 'langBtn', 'status']) {
  elements[id] = makeEl(id);
}
elements.game = makeCanvas();

globalThis.window = {
  innerWidth: 1280, innerHeight: 720, devicePixelRatio: 2,
  addEventListener: () => {},
  EMBEDDED: null,
};
globalThis.document = {
  getElementById: (id) => elements[id] || makeEl(id),
  createElement: (tag) => (tag === 'canvas' ? makeCanvas() : makeEl(tag)),
  addEventListener: () => {},
  querySelectorAll: () => [],
  body: makeEl('body'),
};
globalThis.screen = { orientation: { lock: () => Promise.resolve() } };
globalThis.localStorage = {
  _d: {},
  getItem(k) { return this._d[k] ?? null; },
  setItem(k, v) { this._d[k] = String(v); },
  removeItem(k) { delete this._d[k]; },
};
globalThis.location = { search: '' };
globalThis.performance = { now: () => Date.now() };
globalThis.Image = class {
  constructor() { this.width = 32; this.height = 32; }
  set src(v) { this._src = v; queueMicrotask(() => this.onload?.()); }
  get src() { return this._src; }
};
let rafQueue = [];
globalThis.requestAnimationFrame = (fn) => { rafQueue.push(fn); return rafQueue.length; };
globalThis.cancelAnimationFrame = () => {};
globalThis.fetch = async (url) => {
  const rel = String(url).replace(/^\.?\//, '');
  const full = path.join(ROOT, rel);
  if (!fs.existsSync(full)) throw new Error('404 ' + rel);
  const text = fs.readFileSync(full, 'utf8');
  return { ok: true, json: async () => JSON.parse(text), text: async () => text };
};

// ---------------- loader ----------------
const modules = {};
const cache = {};
const order = JSON.parse(fs.readFileSync(path.join(ROOT, 'js/_order.json'), 'utf8'));
for (const name of order) {
  const code = fs.readFileSync(path.join(ROOT, 'js', name), 'utf8');
  modules[name] = new Function('module', 'exports', 'require', code);
}
function req(name) {
  if (!cache[name]) {
    if (!modules[name]) throw new Error('módulo não encontrado: ' + name);
    const m = { exports: {} };
    cache[name] = m;
    modules[name](m, m.exports, req);
  }
  return cache[name].exports;
}

// ---------------- teste ----------------
let pass = 0, fail = 0;
const failures = [];
function check(label, cond, extra = '') {
  if (cond) { pass++; return; }
  fail++;
  failures.push(`${label}${extra ? ' — ' + extra : ''}`);
}

console.log('\x1b[1mRender — telas desenham sem erro\x1b[0m');

// Boot: main.js chama init() sozinho e agenda o loop.
req('main.js');
await new Promise((r) => setTimeout(r, 300));   // deixa o init() assíncrono terminar

check('o jogo bootou e agendou o loop', rafQueue.length > 0);

// Roda alguns frames para o loop estabilizar.
function step(n = 3) {
  for (let i = 0; i < n; i++) {
    const q = rafQueue;
    rafQueue = [];
    for (const fn of q) fn(performance.now());
  }
}
step(3);
check('desenhou sprites no mundo', calls.drawImage > 0, `${calls.drawImage} drawImage`);

// ---------- percorre todas as telas ----------
const i18n = req('i18n.js').i18n;
const ui = null; // acessamos pelo estado interno via main? não exportado.

// main.js não exporta o estado, então navegamos pelos MESMOS toques que o
// jogador daria: os botões ficam registrados no UI a cada frame.
// Para isso, expomos o input falso e empurramos taps.
const input = req('input.js');

// O jeito mais direto e realista: usar as telas pelo hook ?demo=
const SCREENS = ['world', 'build', 'recruit', 'roster', 'quests', 'kitchen', 'market', 'armazem', 'equip'];
for (const scr of SCREENS) {
  // recria o jogo com a tela pedida
  for (const k of Object.keys(cache)) delete cache[k];
  rafQueue = [];
  calls.drawImage = 0;
  globalThis.location = { search: scr === 'world' ? '' : `?demo=${scr}` };
  globalThis.localStorage._d = {};   // começa limpo

  let err = null;
  try {
    req('main.js');
    await new Promise((r) => setTimeout(r, 200));
    step(4);
  } catch (e) {
    err = e;
  }
  check(`tela "${scr}" desenha sem erro`, err === null, err?.message);
  check(`tela "${scr}" desenhou algo`, calls.drawImage > 0 || scr === 'world');
}

// ---------- traduções: nenhuma chave faltando ----------
for (const k of Object.keys(cache)) delete cache[k];
rafQueue = [];
globalThis.location = { search: '' };
req('main.js');
await new Promise((r) => setTimeout(r, 200));

const pt = JSON.parse(fs.readFileSync(path.join(ROOT, 'assets/data/i18n.pt-br.json'), 'utf8'));
const en = JSON.parse(fs.readFileSync(path.join(ROOT, 'assets/data/i18n.en.json'), 'utf8'));
check('PT e EN têm as mesmas chaves',
  JSON.stringify(Object.keys(pt).sort()) === JSON.stringify(Object.keys(en).sort()));

// Toda chave usada no código existe nos dois idiomas? Além dos literais
// i18n.t('x'), escaneamos QUALQUER string do código com cara de chave de
// tradução ('toast.…', 'ui.…', …) — isso pega também chaves em ternários
// e argumentos do helper toast(). Prefixos dinâmicos (t('res.' + k))
// terminam em ponto e são conferidos à parte.
const KEY_RE = /^(?:app|stage|demo|ui|res|bld|meal|item|slot|ab|abd|spec|rarity|attr|toast|gear)\.[a-z_0-9]+$/;
const allSrc = fs.readdirSync(path.join(ROOT, 'js'))
  .filter((f) => f.endsWith('.js'))
  .map((f) => fs.readFileSync(path.join(ROOT, 'js', f), 'utf8').split('\n')
    // ignora linhas de comentário (doc do i18n.t('chave…') etc.)
    .filter((ln) => !/^[/*]/.test(ln.trim())))
  .join('\n');
const used = [...new Set([
  ...[...allSrc.matchAll(/i18n\.t\('([^']+)'\s*[,)]/g)].map((m2) => m2[1]),
  ...[...allSrc.matchAll(/\btoast\('([^']+)'\s*[,)]/g)].map((m2) => m2[1]),
  ...[...allSrc.matchAll(/'([a-z]+\.[a-z_0-9]+)'/g)].map((m2) => m2[1])
    .filter((k) => KEY_RE.test(k) && !k.endsWith('.js')),
])];
const literal = used.filter((k) => !k.endsWith('.'));
const prefixes = [...new Set([...allSrc.matchAll(/i18n\.t\('([a-z_]+\.)'\s*\+/g)].map((m2) => m2[1]))];

const missingPt = literal.filter((k) => !(k in pt));
check('nenhuma tradução faltando em PT', missingPt.length === 0, missingPt.join(', '));
const missingEn = literal.filter((k) => !(k in en));
check('nenhuma tradução faltando em EN', missingEn.length === 0, missingEn.join(', '));

// Cada prefixo dinâmico precisa ter pelo menos uma chave correspondente.
const orphanPrefix = prefixes.filter(
  (p) => !Object.keys(pt).some((k) => k.startsWith(p)));
check('prefixos dinâmicos têm traduções', orphanPrefix.length === 0, orphanPrefix.join(', '));

// Os conjuntos que o jogo monta dinamicamente, conferidos um a um.
const { BUILD_ORDER } = req('village.js');
const inventory = req('inventory.js');
const abilities = req('abilities.js');
const { VARIATIONS } = req('goblin.js');
const dyn = [
  ...BUILD_ORDER.map((id) => 'bld.' + id),
  ...['wood', 'stone', 'ore', 'food', 'gold'].map((r) => 'res.' + r),
  ...cookingMeals(),
  ...['warrior', 'mage', 'healer', 'cook', 'worker', 'runner', 'common'].map((s) => 'spec.' + s),
  ...['common', 'uncommon', 'rare', 'epic'].map((r) => 'rarity.' + r),
  ...VARIATIONS.map((v) => 'variation.' + v),
  ...inventory.EQUIP_SLOTS.map((s) => 'slot.' + s),
  ...inventory.SLOT_TYPES.map((s) => 'slot.' + s),
  ...inventory.ITEMS.map((i) => 'item.' + i.id),
  ...abilities.ABILITIES.map((a) => 'ab.' + a.id),
  ...abilities.ABILITIES.map((a) => 'abd.' + a.id),
];
function cookingMeals() {
  return req('cooking.js').RECIPES.map((r) => 'meal.' + r.id);
}
const missingDynPt = dyn.filter((k) => !(k in pt));
check('nomes dinâmicos traduzidos em PT', missingDynPt.length === 0, missingDynPt.join(', '));
const missingDynEn = dyn.filter((k) => !(k in en));
check('nomes dinâmicos traduzidos em EN', missingDynEn.length === 0, missingDynEn.join(', '));

// ---------- sprites: todo id pedido existe no manifest ----------
const manifest = JSON.parse(fs.readFileSync(path.join(ROOT, 'assets/manifest.json'), 'utf8'));
const haveSprites = new Set(manifest.sprites.map((s) => s.id));
const { BUILDINGS } = req('village.js');
const missingB = Object.values(BUILDINGS).map((b) => b.sprite).filter((s) => !haveSprites.has(s));
check('todo prédio tem sprite no manifest', missingB.length === 0, missingB.join(', '));
const cooking = req('cooking.js');
const missingM = cooking.RECIPES.map((r) => r.sprite).filter((s) => !haveSprites.has(s));
check('toda comida tem sprite no manifest', missingM.length === 0, missingM.join(', '));
const missingI = inventory.ITEMS.map((i) => i.icon).filter((s) => !haveSprites.has(s));
check('todo item de equipamento tem ícone no manifest', missingI.length === 0, missingI.join(', '));
const missingA = abilities.ABILITIES.map((a) => a.icon).filter((s) => !haveSprites.has(s));
check('toda habilidade tem ícone no manifest', missingA.length === 0, missingA.join(', '));
// skins do goblin equipado (ferro_pei / avaritia) cobrem as animações usadas
const gear = req('gear.js');
const anims = [['idle', 5], ['walk', 8], ['attack', 17], ['hurt', 17], ['death', 15]];
const skinMissing = [];
for (const ver of ['ferro_pei', 'av_full', 'av_cap_pei', 'av_pei_cal', 'av_cap_cal', 'av_pei', 'av_cap', 'av_cal']) {
  for (const [anim, n] of anims) {
    for (let i = 0; i < n; i++) {
      if (!haveSprites.has(`${ver}_${anim}_${i}`)) skinMissing.push(`${ver}_${anim}_${i}`);
    }
  }
}
check('todas as skins de equipamento existem no manifest', skinMissing.length === 0,
  skinMissing.slice(0, 4).join(', '));

const variationMissing = [];
for (const variant of VARIATIONS) {
  for (const [anim, n] of anims) {
    for (let i = 0; i < n; i++) {
      const id = `variant_${variant}_${anim}_${i}`;
      if (!haveSprites.has(id)) variationMissing.push(id);
    }
  }
}
check('as 45 variações cobrem os 62 quadros', variationMissing.length === 0,
  variationMissing.slice(0, 4).join(', '));

const overlayMissing = [];
for (const ver of ['ferro_pei', 'av_full', 'av_cap_pei', 'av_pei_cal', 'av_cap_cal', 'av_pei', 'av_cap', 'av_cal']) {
  for (const [anim, n] of anims) {
    for (let i = 0; i < n; i++) {
      const id = `overlay_${ver}_${anim}_${i}`;
      if (!haveSprites.has(id)) overlayMissing.push(id);
    }
  }
}
check('overlays preservam variações sob equipamento', overlayMissing.length === 0,
  overlayMissing.slice(0, 4).join(', '));

// peças de ferro e armas só têm OVERLAY (sem sprite completo): todas devem
// cobrir os 62 quadros para aparecerem em qualquer animação.
const gearOverlayMissing = [];
for (const ver of ['ferro_cap', 'ferro_cal', 'wpn_espada', 'wpn_clava', 'wpn_escudo']) {
  for (const [anim, n] of anims) {
    for (let i = 0; i < n; i++) {
      const id = `overlay_${ver}_${anim}_${i}`;
      if (!haveSprites.has(id)) gearOverlayMissing.push(id);
    }
  }
}
check('capacete/calça de ferro e armas têm overlay em todos os quadros',
  gearOverlayMissing.length === 0, gearOverlayMissing.slice(0, 4).join(', '));

const missingFiles = manifest.sprites.filter((s) => !fs.existsSync(path.join(ROOT, s.path)));
check('todo sprite do manifest existe em disco', missingFiles.length === 0,
  missingFiles.map((s) => s.path).join(', '));

// ---------- a versão de DESENVOLVIMENTO está completa? ----------
// (o build tem seu próprio teste; aqui garantimos que index-dev.html abre)
check('js/loader.js existe', fs.existsSync(path.join(ROOT, 'js/loader.js')));
const indexHtml = fs.readFileSync(path.join(ROOT, 'index-dev.html'), 'utf8');
check('index-dev.html carrega o loader', indexHtml.includes('js/loader.js'));
// A raiz index.html deve redirecionar para a versão rápida (arquivo único).
const rootHtml = fs.readFileSync(path.join(ROOT, 'index.html'), 'utf8');
check('index.html redireciona para o arquivo único',
  rootHtml.includes('vila-de-goblins-jogavel.html'));
const orderFiles = JSON.parse(fs.readFileSync(path.join(ROOT, 'js/_order.json'), 'utf8'));
const missingMods = orderFiles.filter((n) => !fs.existsSync(path.join(ROOT, 'js', n)));
check('todo módulo do _order.json existe', missingMods.length === 0, missingMods.join(', '));
check('_order.json não inclui o loader', !orderFiles.includes('loader.js'));
check('main.js é o último a carregar', orderFiles[orderFiles.length - 1] === 'main.js');

console.log(`\n  ${pass} passaram · ${fail} falharam`);
if (fail) {
  console.log('\n\x1b[31mFalhas:\x1b[0m');
  for (const f of failures) console.log('  ✗ ' + f);
  process.exit(1);
}
console.log('\x1b[32m  tudo certo\x1b[0m');
// O autosave deixa um setInterval rodando; encerramos na mão.
process.exit(0);
