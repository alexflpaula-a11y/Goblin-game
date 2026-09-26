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
 *   G. divindades começam vazias e só animam após toque do jogador
 *   H. estruturas podem ser movidas para um ponto escolhido no mapa
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
tap(30, 330);   // botão CONSTRUIR (ícone) — interage um pouco
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
// rola a prateleira (horizontal) até a espada ficar visível
{
  const buyItems = market.catalog(appD.village, 'buy');
  const eIdx = buyItems.findIndex((it) => it.kind === 'gear' && it.key === 'espada_ferro');
  appD.state.marketScroll = Math.max(0, 16 + eIdx * 153 - 200);
}
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
console.log('\x1b[1mBOOT E — obra de verdade (lona → concluir → recrutar)\x1b[0m');
const appE = await boot('');
tapRegion('build_btn');
ok(has('bcard_house'), 'catálogo mostra a Casa');
tapRegion('bcard_house');
ok(appE.state.placement?.mode === 'build', 'Casa entra no modo de escolher posição');
const houseSpot = appE.camera.worldToScreen(860, 760);
tap(houseSpot.x, houseSpot.y);
const houseWork = appE.village.structures.find((s) => s.type === 'house' && s.construction);
ok(houseWork?.construction?.total === 10 && appE.village.capacity === 1,
  'Casa cria uma obra de 10s e só dá capacidade quando for recolhida');
ok(houseWork?.construction?.status === 'building' && houseWork.construction.worker === 0,
  'lona recebeu o goblin livre como construtor');
// Simula o fim do cronômetro; o toque na lona, e não o término do tempo,
// é que libera a estrutura e a tela de recrutamento.
houseWork.construction.remaining = 0;
houseWork.construction.status = 'ready';
houseWork.construction.worker = null;
const finishedSpot = appE.camera.worldToScreen(houseWork.x, houseWork.y - 20);
tap(finishedSpot.x, finishedSpot.y);
ok(['card_0', 'card_1', 'card_2'].every(has), 'tocar na lona brilhante abre a escolha de 1 de 3');
const before = appE.village.goblins.length;
tapRegion('card_1');
ok(appE.village.goblins.length === before + 1, 'goblin recrutado entrou na vila');
ok(appE.state.screen === 'world', 'voltou para o mundo após recrutar');

// A Área dos Goblins cria tarefas persistentes e ocupa automaticamente o
// goblin em uma árvore disponível.
tapRegion('jobs_btn');
ok(has('job_0_wood') && has('job_1_wood'), 'Área dos Goblins lista tarefas para cada goblin');
tapRegion('job_1_wood');
ok(appE.village.goblins[1].assignment === 'wood' && !!appE.world.goblins[1].job?.node,
  'tarefa Madeira manda o goblin coletar automaticamente');
tapRegion('job_1_idle');
ok(appE.village.goblins[1].assignment === null && !appE.world.goblins[1].job,
  'Livre remove a tarefa automática e chama o goblin de volta');
tapRegion('close_jobs');

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

// ============================================================
console.log('\x1b[1mBOOT G — divindades exigem ativação manual\x1b[0m');
const appG = await boot('?demo=deities');
ok(appG.village.has('grande_arvore') && appG.village.has('golem_pedra'),
  'demo constrói as duas divindades de nível 3');
ok(!appG.deities.isActive('grande_arvore') && !appG.deities.isActive('golem_pedra')
  && appG.world.goblins.every((w) => !w.job),
  'nenhum goblin começa preso às estruturas');
const treePos = appG.camera.worldToScreen(appG.village.get('grande_arvore').x, appG.village.get('grande_arvore').y - 20);
tap(treePos.x, treePos.y);
ok(appG.deities.isActive('grande_arvore'), 'tocar na Grande Árvore envia um goblin');
for (let i = 0; i < 100; i++) appG.world.update(0.1, { village: appG.village });
ok(appG.world.goblins[0].job?.type === 'worship', 'goblin caminha até a árvore e começa a louvar');
for (let i = 0; i < 28; i++) { appG.nodes.update(0.1); appG.deities.update(0.1); }
ok(appG.deities.states.grande_arvore.mode === 'chant', 'Grande Árvore canta após o goblin chegar');
appG.deities.deactivate('grande_arvore');
const golemPos = appG.camera.worldToScreen(appG.village.get('golem_pedra').x, appG.village.get('golem_pedra').y - 20);
tap(golemPos.x, golemPos.y);
ok(appG.deities.isActive('golem_pedra'), 'tocar no Golem envia o goblin agora livre');
for (let i = 0; i < 120; i++) appG.world.update(0.1, { village: appG.village });
ok(appG.world.goblins[0].job?.type === 'worship', 'goblin caminha até o Golem e começa a louvar');
for (let i = 0; i < 40; i++) { appG.nodes.update(0.1); appG.deities.update(0.1); }
ok(appG.deities.projectiles.length > 0, 'pedra rúnica está voando em arco');
ok(appG.deities.drawList(4).length >= 4, 'render inclui divindades, sombra e projétil polido');
step(2);
ok(true, 'frame animado desenha sem erro');

// ============================================================
console.log('\x1b[1mBOOT H — mover qualquer estrutura\x1b[0m');
appG.deities.deactivate('golem_pedra');
step(1);
tapRegion('move_btn');
ok(appG.state.placement?.mode === 'pick', 'botão Mover pede uma estrutura');
const oldTree = { x: appG.village.get('grande_arvore').x, y: appG.village.get('grande_arvore').y };
const oldTreeScreen = appG.camera.worldToScreen(oldTree.x, oldTree.y - 20);
tap(oldTreeScreen.x, oldTreeScreen.y);
ok(appG.state.placement?.mode === 'move', 'estrutura escolhida vira um fantasma móvel');
const newTree = { x: 850, y: 780 };
const newTreeScreen = appG.camera.worldToScreen(newTree.x, newTree.y);
tap(newTreeScreen.x, newTreeScreen.y);
ok(appG.state.placement === null
  && appG.village.get('grande_arvore').x === newTree.x
  && appG.village.get('grande_arvore').y === newTree.y,
  'novo local escolhido é salvo na estrutura');

console.log(`\n  ${passes} passaram · ${fails} falharam`);
process.exit(fails ? 1 : 0);
