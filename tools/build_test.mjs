/**
 * build_test.mjs — Confere o BUILD de arquivo único.
 *
 * O build usa um caminho de carregamento diferente do modo dev
 * (sprites em base64 + módulos embutidos, sem fetch), então ele
 * precisa do seu próprio teste: já aconteceu de o dev funcionar e
 * o arquivo distribuído quebrar.
 *
 * Executa o HTML num DOM falso e confere que o jogo sobe.
 *
 * Uso:  node tools/build_test.mjs
 */
import fs from 'node:fs';
import path from 'node:path';
import vm from 'node:vm';
import { fileURLToPath } from 'node:url';

const ROOT = path.dirname(path.dirname(fileURLToPath(import.meta.url)));
const FILE = path.join(ROOT, 'vila-de-goblins-jogavel.html');

let pass = 0, fail = 0;
const failures = [];
function check(label, cond, extra = '') {
  if (cond) { pass++; return; }
  fail++;
  failures.push(`${label}${extra ? ' — ' + extra : ''}`);
}

console.log('\x1b[1mBuild — o arquivo único funciona sozinho\x1b[0m');

const html = fs.readFileSync(FILE, 'utf8');

// ---------- o HTML está inteiro? ----------
check('tem o EMBEDDED com os dados', html.includes('window.EMBEDDED = '));
check('tem o loader', html.includes('function __require'));
check('chama o main no fim', html.includes("__require('main.js');"));
check('não sobrou referência a arquivo externo',
  !/<script src=|<link rel="stylesheet"/.test(html));

// ---------- os dados embutidos estão completos? ----------
const i = html.indexOf('window.EMBEDDED = ') + 'window.EMBEDDED = '.length;
const embedded = JSON.parse(html.slice(i, html.indexOf('\n</script>', i)).replace(/;$/, ''));
check('sprites embutidos', Object.keys(embedded.sprites).length > 80,
  `${Object.keys(embedded.sprites).length} sprites`);
check('todo sprite é data URI',
  Object.values(embedded.sprites).every((s) => s.startsWith('data:image/png;base64,')));
check('i18n embutido nos 2 idiomas',
  embedded.i18n['pt-BR'] && embedded.i18n.en);
check('balance embutido', !!embedded.balance.village);

// ---------- o jogo executa? ----------
const calls = { drawImage: 0 };
function makeCtx() {
  const noop = () => {};
  return new Proxy({
    canvas: { width: 1280, height: 720 },
    measureText: (s) => ({ width: String(s).length * 6 }),
    createRadialGradient: () => ({ addColorStop: noop }),
    createLinearGradient: () => ({ addColorStop: noop }),
    drawImage: (img) => {
      if (img == null) throw new Error('drawImage com sprite nulo');
      calls.drawImage++;
    },
  }, { get: (t, p) => (p in t ? t[p] : noop), set: (t, p, v) => { t[p] = v; return true; } });
}
const makeEl = (id) => ({
  id, style: {}, textContent: '', dataset: {},
  addEventListener() {}, appendChild() {}, setAttribute() {},
  getContext: () => makeCtx(),
  getBoundingClientRect: () => ({ left: 0, top: 0, width: 1280, height: 720 }),
  width: 1280, height: 720,
});

const raf = [];
const logs = [];
const sandbox = {
  console: { log: (...a) => logs.push(a.join(' ')), warn: (...a) => logs.push(a.join(' ')), error: (...a) => logs.push(a.join(' ')) },
  window: { innerWidth: 1280, innerHeight: 720, devicePixelRatio: 2, addEventListener() {} },
  document: {
    getElementById: makeEl,
    createElement: makeEl,
    addEventListener() {},
    body: makeEl('body'),
  },
  screen: { orientation: { lock: () => Promise.resolve() } },
  localStorage: { _d: {}, getItem(k) { return this._d[k] ?? null; }, setItem(k, v) { this._d[k] = v; }, removeItem(k) { delete this._d[k]; } },
  location: { search: '' },
  performance: { now: () => Date.now() },
  requestAnimationFrame: (fn) => raf.push(fn),
  setTimeout, clearTimeout, setInterval: () => 0, clearInterval,
  Image: class { set src(v) { this._s = v; queueMicrotask(() => this.onload?.()); } get src() { return this._s; } },
  URLSearchParams,
  Math, JSON, Date, Object, Array, String, Number, Boolean, Error, Promise, Map, Set,
  Uint8Array, Float32Array, Uint8ClampedArray, isNaN, parseInt, parseFloat,
};
sandbox.window.EMBEDDED = null;
sandbox.globalThis = sandbox;

// extrai e roda os dois <script> do build
const scripts = [...html.matchAll(/<script>([\s\S]*?)<\/script>/g)].map((m) => m[1]);
check('o build tem os 2 blocos de script', scripts.length === 2, `${scripts.length}`);

let bootError = null;
try {
  const ctx = vm.createContext(sandbox);
  for (const code of scripts) vm.runInContext(code, ctx, { timeout: 15000 });
} catch (e) {
  bootError = e;
}
check('o jogo carrega sem erro', bootError === null, bootError?.message);

await new Promise((r) => setTimeout(r, 300));

check('sprites embutidos carregaram',
  logs.some((l) => /sprites embutidos prontos/.test(l)), logs.join(' | ').slice(0, 120));
check('o loop foi agendado', raf.length > 0);

// roda alguns frames
let err = null;
try {
  for (let k = 0; k < 3; k++) {
    const q = raf.splice(0, raf.length);
    for (const fn of q) fn(Date.now());
  }
} catch (e) { err = e; }
check('os frames desenham sem erro', err === null, err?.message);
check('desenhou sprites de verdade', calls.drawImage > 0, `${calls.drawImage} drawImage`);

console.log(`\n  ${pass} passaram · ${fail} falharam`);
if (fail) {
  console.log('\n\x1b[31mFalhas:\x1b[0m');
  for (const f of failures) console.log('  ✗ ' + f);
  process.exit(1);
}
console.log('\x1b[32m  o arquivo jogável está íntegro\x1b[0m');
process.exit(0);
