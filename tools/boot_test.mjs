/**
 * boot_test.mjs — Boot REAL do jogo sem navegador, cobrindo:
 *
 *   A. save.js desativado  (não grava, não carrega, limpa o velho)
 *   B. boot com save antigo no localStorage → vila nova
 *   C. armazém: despensa (3 pratos ≠ "sem pratos"), estouro real
 *      17/16 por desequipar (regressão), grade sem itens escondidos
 *   D. mercado: compra respeita a capacidade do armazém (UI real)
 *   E. recrutamento de verdade: construir casa → escolher 1 de 3
 *   F. subir 2+ níveis de uma vez anuncia TODOS os desbloqueios
 *
 * Uso:  node tools/boot_test.mjs
 */
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const ROOT = path.dirname(path.dirname(fileURLToPath(import.meta.url)));

let fails = 0, passes = 0;
const ok = (cond, msg, extra) => {
  console.log((cond ? '  ✓ ' : '  ✗ ') + msg + (extra ? `  (${extra})` : ''));
  cond ? passes++ : fails++;
};

// ---------- canvas falso com listeners + gravação de fillText ----------
const textLog = [];
function makeCanvas(id) {
  const handlers = {};
  const el = {
    _id: id, width: 1280, height: 720, style: {},
    getContext: () => new Proxy({
      canvas: el,
      measureText: (s) => ({ width: String(s).length * 6 }),
      createRadialGradient: () => ({ addColorStop: () => {} }),
      createLinearGradient: () => ({ addColorStop: () => {} }),
      fillText: (s) => { textLog.push(String(s)); },
    }, { get: (t, p) => (p in t ? t[p] : () => {}), set: (t, p, v) => { t[p] = v; return true; } }),
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
  getElementById: (id) => elements[id],
  createElement: (tag) => (tag === 'canvas' ? makeCanvas('dyn') : makeEl(tag)),
  addEventListener() {}, body: makeEl('body'),
};
globalThis.localStorage = {
  _d: {},
  getItem(k) { return this._d[k] ?? null; },
  setItem(k, v) { this._d[k] = v; },
  removeItem(k) { delete this._d[k]; },
};
globalThis.location = { search: '' };
globalThis.screen = { orientation: { lock: () => Promise.resolve() } };
globalThis.setInterval = () => 0;
globalThis.requestAnimationFrame = (fn) => raf.push(fn);
globalThis.fetch = async (url) => {
  try {
    const data = fs.readFileSync(path.join(ROOT, url));
    return { ok: true, json: async () => JSON.parse(data), text: async () => String(data) };
  } catch {
    return { ok: false, json: async () => { throw new Error('404'); }, text: async () => { throw new Error('404'); } };
  }
};
globalThis.Image = class {
  set src(v) { this._src = v; queueMicrotask(() => this.onload?.()); }
  get src() { return this._src; }
};

// ---------- módulos ----------
const modules = {}, cache = {};
for (const nm of JSON.parse(fs.readFileSync(path.join(ROOT, 'js/_order.json'), 'utf8'))) {
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

// captura as regiões clicáveis do último frame (classe atual do ui.js)
let lastEls = [];
function patchUI() {
  const { UI } = req('ui.js');
  UI.prototype.begin = function () { this.els = []; lastEls = this.els; };
}
const regions = () => lastEls;
const region = (id) => regions().find((r) => r.id === id);
const has = (id) => !!region(id);
function tap(x, y) {
  const h = elements.game._handlers;
  const ev = { pointerId: 7, clientX: x * 2, clientY: y * 2 };
  h.pointerdown(ev);
  h.pointerup(ev);
  step(2);
}
function tapRegion(id) {
  const r = region(id);
  if (!r) throw new Error('região não encontrada: ' + id);
  tap(r.x + r.w / 2, r.y + r.h / 2);
}

const SAVE_KEY = 'gnome-village-save-v1';
const drawnTexts = () => textLog.splice(0, textLog.length).join(' | ');

/** Boota o jogo (limpa módulos, mata loops antigos, roda main.js). */
async function boot(search = '') {
  for (const k of Object.keys(cache)) delete cache[k];
  raf = [];                       // loops das boots anteriores morrem
  globalThis.location = { search };
  req('main.js');
  patchUI();
  await new Promise((r) => setTimeout(r, 250));
  step(3);
  return req('main.js');          // alça { state, village, quests }
}

// ============================================================
console.log('\x1b[1mBOOT A — save.js desativado (unidade)\x1b[0m');
const save = req('save.js');
ok(save.SAVE_ENABLED === false, 'SAVE_ENABLED === false (salvamento desligado)');
globalThis.localStorage.setItem(SAVE_KEY, '{"language":"en"}');
save.saveGame({ language: 'pt-BR', taps: 99 });
ok(globalThis.localStorage.getItem(SAVE_KEY) === '{"language":"en"}',
  'saveGame não grava nada com o salvamento desligado');
ok(save.loadGame() === null, 'loadGame devolve null mesmo com dado gravado');
save.clearGame();
ok(globalThis.localStorage.getItem(SAVE_KEY) === null, 'clearGame remove a chave');

// ============================================================
console.log('\x1b[1mBOOT B — save velho no localStorage é ignorado\x1b[0m');
globalThis.localStorage.setItem(SAVE_KEY, JSON.stringify({
  language: 'en',
  village: {
    level: 5, xp: 10,
    res: { wood: 999, stone: 999, gold: 999 },
    structures: [
      { type: 'construction', level: 1, x: 920, y: 706 },
      { type: 'quest', level: 1, x: 960, y: 630 },
      { type: 'house', level: 1, x: 1000, y: 706, slot: 0 },
      { type: 'armazem', level: 3, x: 960, y: 858 },
    ],
    goblins: [
      { name: 'Velho', specialty: 'mage', hp: 10 },
      { name: 'Velho2', specialty: 'cook' },
      { name: 'Velho3', specialty: 'worker' },
    ],
    items: { espada_ferro: 5 },
  },
}));
const appB = await boot('');
ok(appB.village.level === 1 && appB.village.goblins.length === 1,
  'vila NOVA (nível 1, 1 goblin) — save velho ignorado');
ok(!appB.village.has('armazem'), 'armazém do save velho não veio');
ok(globalThis.localStorage.getItem(SAVE_KEY) === null, 'chave do save velho foi descartada no boot');
tap(56, 334);   // botão CONSTRUIR — interage um pouco
ok(appB.state.screen === 'build', 'navegação funciona na vila nova');
ok(globalThis.localStorage.getItem(SAVE_KEY) === null, 'nada é gravado ao jogar');

// ============================================================
console.log('\x1b[1mBOOT C — armazém: despensa e estouro por desequipar\x1b[0m');
const NO_MEALS = JSON.parse(fs.readFileSync(path.join(ROOT, 'assets/data/i18n.pt-br.json'), 'utf8'))['ui.no_meals'];
const appC = await boot('?demo=armazem');
ok(appC.state.screen === 'armazem', 'demo abre direto na tela do armazém');
drawnTexts();                    // descarta textos do boot
// 4 pratos (kit do demo): nada de aviso de despensa vazia
step(1);
let texts = drawnTexts();
ok(!texts.includes(NO_MEALS), 'com 4 pratos guardados não aparece aviso de despensa vazia');
// exatamente 3 pratos: caso que desenhava o aviso por cima dos chips
appC.village.meals = { bread: 2, soup: 1, stew: 1 };
step(1);
texts = drawnTexts();
ok(!texts.includes(NO_MEALS), 'com 3 pratos também NÃO aparece o aviso (regressão do wrap)');
// 0 pratos: aviso legítimo
appC.village.meals = {};
step(1);
texts = drawnTexts();
ok(texts.includes(NO_MEALS), 'com despensa vazia o aviso aparece');

// estouro REAL: armazém 16/16 + espada equipada → desequipar = 17/16
appC.village.items = { espada_ferro: 16 };
appC.village.goblins[0].equip = { arma_primaria: 'espada_ferro' };
step(1);
tapRegion('inv_equip');
tapRegion('slot_arma_primaria');
ok(has('equn_arma_primaria'), 'espada equipada aparece com botão de remover');
tapRegion('equn_arma_primaria');
ok(appC.village.itemsCount() === 17, 'desequipar com armazém cheio deixa 17/16 (por design)');
tapRegion('back_eq');
const cells = regions().filter((r) => r.id === 'invs_espada_ferro');
ok(cells.length === 17, 'grade mostra TODOS os 17 itens (regressão do slice)', `${cells.length} células`);

const market = req('market.js');
ok(market.maxBuy(appC.village, 'gear', 'espada_ferro') === 0, 'compra bloqueada com 17/16');
// tirar 2 do armazém libera espaço p/ comprar 1 (com ouro suficiente)
appC.village.res.gold = 500;
appC.village.takeItem('espada_ferro', 2);
ok(appC.village.itemsCount() === 15, 'tirando 2 itens: 15/16');
ok(market.maxBuy(appC.village, 'gear', 'espada_ferro') === 1, 'espaço liberado → dá p/ comprar 1');

// ============================================================
console.log('\x1b[1mBOOT D — mercado: compra respeita a capacidade\x1b[0m');
const appD = await boot('?demo=market');
ok(appD.state.screen === 'market' && appD.village.has('armazem'), 'demo abre o Mercado com Armazém');
tapRegion('mtab_1');                       // aba COMPRAR
appD.state.marketPage = 4;                 // página com espada/clava/escudo/runa
step(1);
ok(has('mdo_gear:espada_ferro'), 'espada à venda na aba de compra');
tapRegion('mmax_gear:espada_ferro');       // quantidade = máximo
tapRegion('mdo_gear:espada_ferro');        // confirma
const bought = appD.village.itemsCount();
ok(bought > 2, `comprou equipamentos (2 → ${bought} itens)`);
// armazém cheio: botão de compra some (maxBuy = 0)
appD.village.res.gold = 5000;
appD.village.items = { espada_ferro: 16 };
step(1);
ok(!has('mdo_gear:espada_ferro'), 'com armazém cheio o botão de compra desaparece');
market.sell(appD.village, 'gear', 'espada_ferro', 1);
step(1);
ok(has('mdo_gear:espada_ferro'), 'vender 1 devolve o botão de compra');

// ============================================================
console.log('\x1b[1mBOOT E — recrutamento de verdade (construir casa → 1 de 3)\x1b[0m');
const appE = await boot('');
tapRegion('build_btn');
ok(has('bcard_house'), 'catálogo mostra a Casa');
tapRegion('bcard_house');
ok(['card_0', 'card_1', 'card_2'].every(has), 'construir casa abre a escolha de 1 de 3');
const before = appE.village.goblins.length;
tapRegion('card_1');
ok(appE.village.goblins.length === before + 1, 'goblin recrutado entrou na vila');
ok(appE.state.screen === 'world', 'voltou para o mundo após recrutar');

// ============================================================
console.log('\x1b[1mBOOT F — subir 2+ níveis anuncia todos os desbloqueios\x1b[0m');
const q = appE.quests.list[0];
q.kind = 'res'; q.key = 'wood'; q.qty = 1; q.xp = 4000; q.gold = 10;
appE.village.res.wood = 50;
tapRegion('quests_btn');
tapRegion('qdo_' + q.id);
ok(appE.village.level >= 3, `vila subiu vários níveis (agora nível ${appE.village.level})`);
const msg = appE.state.toast?.msg || '';
ok(msg.includes('Serraria') && msg.includes('Cozinha') && msg.includes('Ferraria'),
  'toast anuncia desbloqueios do nível 2, 3 E 5 (salto múltiplo)', msg);

console.log(`\n  ${passes} passaram · ${fails} falharam`);
process.exit(fails ? 1 : 0);
