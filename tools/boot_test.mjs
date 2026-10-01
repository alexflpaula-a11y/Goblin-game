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
/** Gesto de arraste real em coordenadas lógicas do canvas. */
function dragPoints(start, end, pointerId = 9) {
  const h = elements.game._handlers;
  h.pointerdown({ pointerId, clientX: start.x * 2, clientY: start.y * 2 });
  step(1);
  h.pointermove({ pointerId, clientX: end.x * 2, clientY: end.y * 2 });
  step(1);
  h.pointerup({ pointerId, clientX: end.x * 2, clientY: end.y * 2 });
  step(2);
}
/** Arrasta um cartão/elemento até uma região de destino real da interface. */
function dragRegion(fromId, toId) {
  const from = region(fromId), to = region(toId);
  if (!from) throw new Error('região de origem não encontrada: ' + fromId);
  if (!to) throw new Error('região de destino não encontrada: ' + toId);
  dragPoints(
    { x: from.x + from.w / 2, y: from.y + from.h / 2 },
    { x: to.x + to.w / 2, y: to.y + to.h / 2 },
  );
}
async function hold(x, y, ms = 740) {
  const h = elements.game._handlers;
  const ev = { pointerId: 8, clientX: x * 2, clientY: y * 2 };
  h.pointerdown(ev);
  await new Promise((r) => setTimeout(r, ms));
  step(2);                 // frames com o dedo ainda pressionado: fecha o círculo
  h.pointerup(ev);
  step(1);
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
ok(appB.village.level === 1 && appB.village.goblins.length === 0,
  'vila NOVA (nível 1, ilha sem goblins) — save velho ignorado');
ok(!appB.village.has('armazem'), 'armazém do save velho não veio');
ok(globalThis.localStorage.getItem(SAVE_KEY) === null, 'chave do save velho foi descartada no boot');
ok(appB.state.screen === 'build' && has('bcard_construction'),
  'vila nova abre a navegação da fundação');
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
console.log('\x1b[1mBOOT E — fundação vazia, obras e recruta\x1b[0m');
const appE = await boot('');
ok(appE.village.structures.length === 0 && appE.state.screen === 'build',
  'novo jogo abre o terreno vazio no catálogo da fundação');
ok(has('bcard_construction') && !has('bcard_house'),
  'antes da Casa de Construção o catálogo só libera a fundação');
const starterWood = appE.village.res.wood;
ok(appE.village.goblins.length === 0 && appE.quests.list.length === 0,
  'ilha nova não tem goblins nem missões antes das fundações');
tapRegion('bcard_construction');
const constructionSpot = appE.camera.worldToScreen(920, 706);
tap(constructionSpot.x, constructionSpot.y);
const constructionHouse = appE.village.structures.find((s) => s.type === 'construction');
ok(constructionHouse?.construction?.status === 'ready' && constructionHouse.construction.total === 0
  && appE.village.res.wood === starterWood && !appE.village.has('construction'),
'Casa de Construção grátis vira lona brilhante de tempo zero');
tap(constructionSpot.x, constructionSpot.y);
ok(appE.village.has('construction') && appE.state.screen === 'world',
  'tocar na lona pronta conclui a Casa de Construção');

tapRegion('build_btn');
ok(has('bcard_quest') && has('bcard_house'), 'Casa de Construção concluída libera Painel e Casas grátis');
tapRegion('bcard_quest');
const questSpot = appE.camera.worldToScreen(960, 630);
tap(questSpot.x, questSpot.y);
const questWork = appE.village.structures.find((s) => s.type === 'quest');
ok(questWork?.construction?.status === 'building' && appE.village.res.wood === starterWood
  && appE.quests.list.length === 0,
  'Painel gratuito fica em obra e ainda não cria missões');

tapRegion('build_btn');
tapRegion('bcard_house');
ok(appE.state.placement?.mode === 'build', 'primeira Casa entra no modo de escolher posição');
const starterHouseSpot = appE.camera.worldToScreen(1000, 706);
tap(starterHouseSpot.x, starterHouseSpot.y);
const starterHouse = appE.village.structures.find((s) => s.type === 'house');
ok(starterHouse?.construction?.status === 'ready' && starterHouse.construction.total === 0
  && appE.village.capacity === 0 && appE.village.goblins.length === 0,
  'primeira Casa grátis também mostra lona brilhante sem cronômetro');
tap(starterHouseSpot.x, starterHouseSpot.y);
ok(['card_0', 'card_1', 'card_2'].every(has), 'primeira Casa concluída abre a escolha do primeiro goblin');
tapRegion('card_1');
ok(appE.village.goblins.length === 1, 'primeiro goblin só entra após a primeira Casa');

questWork.construction.remaining = 0; questWork.construction.status = 'ready'; questWork.construction.worker = null;
const questDoneSpot = appE.camera.worldToScreen(questWork.x, questWork.y - 20);
tap(questDoneSpot.x, questDoneSpot.y);
ok(appE.village.has('quest') && appE.quests.list.length > 0,
  'Painel concluído é que cria as missões');

tapRegion('build_btn');
tapRegion('bcard_house');
const houseSpot = appE.camera.worldToScreen(860, 760);
tap(houseSpot.x, houseSpot.y);
const houseWork = appE.village.structures.find((s) => s.type === 'house' && s.construction);
ok(houseWork?.construction?.total === 10 && appE.village.capacity === 1,
  'segunda Casa grátis cria obra de 10s e só dá capacidade quando for recolhida');
ok(houseWork?.construction?.status === 'building' && houseWork.construction.worker == null,
  'lona aguarda um Construtor nomeado; não captura goblin livre');
tapRegion('roster_btn');
tapRegion('jobs_tab_1');
ok(has('jobdrag_0') && has('jobdrop_builder'),
  'aba Trabalhos da Vila mostra goblins disponíveis para arrastar');
dragRegion('jobdrag_0', 'jobdrop_builder');
step(2);
ok(houseWork.construction.worker === 0,
  'goblin só vai até a lona depois de ser nomeado Construtor');
appE.state.screen = 'world';
// A lona em andamento alterna pausa/retomada sem arredondar nem consumir o
// relógio que já estava preenchido.
const houseWorkSpot = appE.camera.worldToScreen(houseWork.x, houseWork.y - 20);
houseWork.construction.remaining = 7.25;
tap(houseWorkSpot.x, houseWorkSpot.y);
const heldRemaining = houseWork.construction.remaining;
step(3);
ok(houseWork.construction.paused && heldRemaining === 7.25
  && houseWork.construction.remaining === heldRemaining && houseWork.construction.worker == null,
'pausar obra congela exatamente o tempo restante e libera o Construtor');
tap(houseWorkSpot.x, houseWorkSpot.y);
ok(!houseWork.construction.paused && houseWork.construction.remaining === heldRemaining,
  'retomar obra conserva exatamente o tempo que estava pausado');
appE.state.screen = 'world';
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
appE.village.level = 3;
appE.village.res.wood = 999; appE.village.res.stone = 999;
appE.village.upgrade(appE.village.houses[0]);
step(1);
ok(has('recruit_btn') && appE.village.goblins.length < appE.village.capacity,
  'Casa melhorada abre vaga e ela segue acessível pelo botão de recrutamento');
ok(!has('jobs_btn') && has('roster_btn'),
  'não há ícone separado de Trabalhos: a aba fica dentro da Vila');

// A aba Trabalhos dentro da Vila cria tarefas persistentes e ocupa
// automaticamente o goblin em uma árvore disponível.
tapRegion('roster_btn');
tapRegion('jobs_tab_1');
ok(has('jobdrag_1') && has('jobdrop_wood'), 'Vila mostra a aba Trabalhos');
dragRegion('jobdrag_1', 'jobdrop_wood');
ok(appE.village.goblins[1].assignment === 'wood' && !!appE.world.goblins[1].job?.node,
  'arrastar para Madeira manda o goblin coletar automaticamente');
tapRegion('jobdrop_wood');
ok(has('job_1_idle') && !has('job_0_wood'),
  'tocar Madeira mostra apenas quem está sendo usado nesse trabalho');
tapRegion('job_1_idle');
ok(appE.village.goblins[1].assignment === null && !appE.world.goblins[1].job,
  'retirar em Trabalhos remove a tarefa automática e chama o goblin de volta');
tapRegion('back_world');

// A aba Trabalhos reúne também a função de Construtor.
appE.world.goblins.forEach((w) => { w.job = null; });
appE.state.screen = 'roster'; appE.state.jobsTab = 1; appE.state.jobsRole = null; step(2);
ok(has('jobdrop_builder') && has('jobdrag_1'), 'Vila mostra o ofício Construtor');
dragRegion('jobdrag_1', 'jobdrop_builder');
ok(appE.village.goblins[1].assignment === 'builder', 'Vila designa um Construtor pelo arraste');

// A Cozinha possui uma escala própria e só inicia prato após nomear cozinheiro.
appE.village.level = 3;
appE.village.res = { wood: 999, stone: 999, ore: 999, food: 999, gold: 999 };
appE.village.build('cozinha');
appE.state.screen = 'kitchen'; appE.state.kitchenTab = 0; step(2);
ok(has('ktab_1') && has('cook_bread'), 'Cozinha mostra abas de receitas e cozinheiros');
// A escala agora só oferece goblins realmente disponíveis.
appE.world.goblins[0].job = null; appE.village.goblins[0].assignment = null;
tapRegion('ktab_1');
ok(has('cookrole_0_cook'), 'aba Cozinheiros permite escolher cada goblin');
tapRegion('cookrole_0_cook');
ok(appE.village.goblins[0].assignment === 'cook', 'Cozinha designa um Cozinheiro');
tapRegion('ktab_0');
tapRegion('cook_bread');
ok(appE.village.cookingJob?.recipeId === 'bread' && appE.village.cookingJob.remaining > 0
  && appE.village.cookingJob.total === 10 && !appE.village.meals.bread,
'ingredientes viram preparo de pão de 10s, não comida imediata');
tapRegion('cook_soup');
ok(appE.village.cookingQueue?.[0] === 'soup' && has('queue_remove_0'),
  'segunda receita entra na fila removível sem trocar o preparo atual');
tapRegion('queue_remove_0');
ok(appE.village.cookingQueue.length === 0, 'remover item da fila funciona');

// A aba Trabalhos reúne a designação por tipo e encaminha postos especiais.
tapRegion('back_world');
tapRegion('roster_btn');
tapRegion('jobs_tab_1');
ok(has('jobdrop_wood') && has('jobs_open_kitchen'),
  'aba Trabalhos lista ofícios e encaminha a Cozinha');
tapRegion('jobdrop_wood');
texts = drawnTexts();
ok(has('jobs_back_roles') && texts.includes('Nenhum goblin trabalhando'),
  'trabalho escolhido mostra somente sua equipe atual');
tapRegion('jobs_back_roles');
tapRegion('jobs_open_kitchen');
ok(appE.state.screen === 'kitchen' && appE.state.kitchenTab === 1,
  'posto Cozinha abre sua escala própria');

// Um coletor não aparece como livre no roster da Cozinha e não pode ser
// escolhido como cozinheiro enquanto seu trabalho atual está ativo.
const busyCook = appE.world.goblins[1];
busyCook.job = { type: 'goto', node: appE.nodes.list.find((n) => n.type === 'tree') };
appE.state.screen = 'kitchen'; appE.state.kitchenTab = 1; drawnTexts(); step(1);
texts = drawnTexts();
ok(!texts.includes('Madeira') && !has('cookrole_1_cook'),
  'Cozinha mostra somente goblins disponíveis, sem o coletor ocupado');

// A lista de todos os goblins continua rolável; trabalhos ficam na aba ao lado.
const { Goblin: BootGoblin } = req('goblin.js');
while (appE.village.goblins.length < 8) appE.village.goblins.push(BootGoblin.roll(appE.village.goblins.length));
appE.world.setGoblinCount(appE.village.goblins.length);
appE.state.screen = 'roster'; appE.state.jobsTab = 0; appE.state.rosterScroll = 0; step(2);
const firstCard = region('g_0');
dragPoints({ x: firstCard.x + 120, y: firstCard.y + firstCard.h / 2 },
  { x: firstCard.x + 120, y: firstCard.y + firstCard.h / 2 - 100 }, 14);
step(1);
ok(appE.state.rosterScroll > 0, 'lista da Vila rola ao arrastar');
appE.world.goblins[4].job = null; appE.village.goblins[4].assignment = null;
// Depois da rolagem, a aba ainda abre normalmente; o cartão disponível pode
// ser arrastado diretamente ao destino Comida.
appE.state.jobsTab = 1; appE.state.jobsRole = null; step(2);
dragRegion('jobdrag_4', 'jobdrop_food');
ok(appE.village.goblins[4].assignment === 'food',
  'aba Trabalhos atribui Comida sem sair da Vila');
// Mais dois goblins podem se juntar ao cozinheiro ativo, e o preparo mantém
// a escala persistente de três trabalhadores.
for (const i of [2, 3]) { appE.world.goblins[i].job = null; appE.village.goblins[i].assignment = null; }
appE.state.screen = 'kitchen'; appE.state.kitchenTab = 1; step(2);
tapRegion('cookrole_2_cook');
tapRegion('cookrole_3_cook');
step(2);
ok(appE.village.goblins.filter((g) => g.assignment === 'cook').length === 3
  && appE.village.cookingJob?.workers?.length === 3,
  'Cozinha agrega até três cozinheiros ao mesmo preparo');
appE.state.screen = 'world'; step(2);
// As verificações a seguir testam o salto desde o nível inicial.
appE.village.level = 1; appE.village.xp = 0;

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
appG.state.screen = 'build'; appG.state.buildTab = 1; drawnTexts(); step(1);
texts = drawnTexts();
ok(!texts.includes('Grande Árvore') && !texts.includes('Golem de Pedra'),
  'santuários não aparecem no fluxo de melhorias da construção');
appG.state.screen = 'world'; step(1);
// A ilha de demonstração já nasce lotada (200/200). Abrimos uma vaga de
// cada tipo para testar o ciclo divino que só repõe recursos colhidos.
appG.nodes.deplete(appG.nodes.list.find((n) => n.type === 'tree' && !n.depleted));
appG.nodes.deplete(appG.nodes.list.find((n) => n.type === 'rock' && !n.depleted));
// Um segundo goblin permite verificar que o painel não chama um coletor
// ocupado de livre. Ele é só uma semente de teste, fora da partida normal.
appG.village.goblins.push(BootGoblin.roll(1));
appG.world.setGoblinCount(appG.village.goblins.length);
// Um cozinheiro reservado não pode aparecer como disponível para louvar.
appG.village.goblins[1].assignment = 'cook';
const treePos = appG.camera.worldToScreen(appG.village.get('grande_arvore').x, appG.village.get('grande_arvore').y - 20);
tap(treePos.x, treePos.y);
ok(appG.state.screen === 'deity' && has('deity_worship_grande_arvore_0')
  && !has('deity_worship_grande_arvore_1'),
  'Santuário só lista o disponível; cozinheiro reservado fica fora');
appG.village.goblins[1].assignment = null;
const busyTree = appG.world.goblins[1];
busyTree.job = { type: 'goto', node: appG.nodes.list.find((n) => n.type === 'tree' && !n.depleted) };
drawnTexts(); step(1);
texts = drawnTexts();
ok(!texts.includes('Madeira') && !has('deity_worship_grande_arvore_1'),
  'Grande Árvore mostra somente goblins disponíveis, sem coletor ocupado');
busyTree.job = null;
tapRegion('deity_worship_grande_arvore_0');
ok(appG.deities.isActive('grande_arvore'), 'interface envia um goblin para a Grande Árvore');
for (let i = 0; i < 100; i++) appG.world.update(0.1, { village: appG.village });
ok(appG.world.goblins[0].job?.type === 'worship', 'goblin caminha até a árvore e começa a louvar');
let sawTreeChant = false;
for (let i = 0; i < 120 && !sawTreeChant; i++) {
  appG.nodes.update(0.1); appG.deities.update(0.1);
  sawTreeChant = appG.deities.states.grande_arvore.mode === 'chant';
}
ok(sawTreeChant, 'Grande Árvore canta após o goblin chegar');
appG.deities.deactivate('grande_arvore');
appG.state.screen = 'world';
const golemPos = appG.camera.worldToScreen(appG.village.get('golem_pedra').x, appG.village.get('golem_pedra').y - 20);
tap(golemPos.x, golemPos.y);
ok(appG.state.screen === 'deity' && has('deity_worship_golem_pedra_0'),
  'tocar no Golem abre sua interface de minério');
const busyGolem = appG.world.goblins[1];
busyGolem.job = { type: 'goto', node: appG.nodes.list.find((n) => n.type === 'rock' && !n.depleted) };
drawnTexts(); step(1);
texts = drawnTexts();
ok(texts.includes('Pedra') && !has('deity_worship_golem_pedra_1'),
  'Golem mostra somente goblins disponíveis, sem coletor ocupado');
busyGolem.job = null;
tapRegion('deity_worship_golem_pedra_0');
ok(appG.deities.isActive('golem_pedra'), 'interface envia o goblin livre ao Golem');
for (let i = 0; i < 120; i++) appG.world.update(0.1, { village: appG.village });
ok(appG.world.goblins[0].job?.type === 'worship', 'goblin caminha até o Golem e começa a louvar');
let sawGolemProjectile = false;
for (let i = 0; i < 240 && !sawGolemProjectile; i++) {
  appG.nodes.update(0.1); appG.deities.update(0.1);
  sawGolemProjectile = appG.deities.projectiles.length > 0;
}
ok(sawGolemProjectile, 'pedra divina está voando em arco');
ok(appG.deities.drawList(4).length >= 4, 'render inclui divindades, sombra e projétil polido');
step(2);
ok(true, 'frame animado desenha sem erro');

// ============================================================
console.log('\x1b[1mBOOT H — mover qualquer estrutura\x1b[0m');
appG.deities.deactivate('golem_pedra');
appG.state.screen = 'world';
step(1);
const oldTree = { x: appG.village.get('grande_arvore').x, y: appG.village.get('grande_arvore').y };
const oldTreeScreen = appG.camera.worldToScreen(oldTree.x, oldTree.y - 20);
await hold(oldTreeScreen.x, oldTreeScreen.y);
ok(appG.state.placement?.mode === 'move', 'toque longo completa o círculo e libera mover a estrutura');
const newTree = { x: 850, y: 780 };
const newTreeScreen = appG.camera.worldToScreen(newTree.x, newTree.y);
tap(newTreeScreen.x, newTreeScreen.y);
ok(appG.state.placement === null
  && appG.village.get('grande_arvore').x === newTree.x
  && appG.village.get('grande_arvore').y === newTree.y,
  'novo local escolhido é salvo na estrutura');

// ============================================================
console.log('\x1b[1mBOOT I — arrastar goblin no mundo\x1b[0m');
appG.state.screen = 'world';
const carried = appG.world.goblins[0];
carried.job = null; carried.target = null; carried.wait = 0;
appG.village.goblins[carried.i].assignment = null;
const fromGoblin = appG.camera.worldToScreen(carried.x, carried.y - 14);
const freePlace = { x: carried.x + 52, y: carried.y + 10 };
const freePlaceScreen = appG.camera.worldToScreen(freePlace.x, freePlace.y);
dragPoints(fromGoblin, freePlaceScreen, 10);
ok(!carried.dragged && Math.abs(carried.x - freePlace.x) < 2
  && Math.abs(carried.y - (freePlace.y + 8)) < 2,
  'arrastar goblin move-o pelo mundo e soltar o deixa no novo ponto');

// O demo de divindades não inclui a fundação; cria-se uma Casa pronta para
// validar o alvo real que a interação do mapa reconhece.
const constructionHome = appG.village.get('construction') || appG.village.build('construction');
ok(!!constructionHome, 'há uma Casa de Construção para receber o goblin');
const fromMovedGoblin = appG.camera.worldToScreen(carried.x, carried.y - 14);
const constructionScreen = appG.camera.worldToScreen(constructionHome.x, constructionHome.y - 20);
dragPoints(fromMovedGoblin, constructionScreen, 11);
ok(appG.village.goblins[carried.i].assignment === 'builder',
  'soltar o goblin sobre a Casa de Construção nomeia um Construtor');

console.log(`\n  ${passes} passaram · ${fails} falharam`);
process.exit(fails ? 1 : 0);
