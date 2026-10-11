/**
 * smoke_test.mjs — Testa a LÓGICA do jogo sem navegador.
 *
 * Carrega os módulos puros (os que não dependem de canvas/DOM) no Node
 * e exercita o ciclo da vila: recursos, construção, recrutamento,
 * nós finitos, missões, XP/nível da vila, cozinha e batalha.
 *
 * Uso:  node tools/smoke_test.mjs
 */
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const ROOT = path.dirname(path.dirname(fileURLToPath(import.meta.url)));

// ---------- mini loader (mesmo contrato do js/loader.js) ----------
const modules = {};
const cache = {};
const order = JSON.parse(fs.readFileSync(path.join(ROOT, 'js/_order.json'), 'utf8'));
for (const name of order) {
  const code = fs.readFileSync(path.join(ROOT, 'js', name), 'utf8');
  modules[name] = new Function('module', 'exports', 'require', code);
}
function req(name) {
  if (!cache[name]) {
    const m = { exports: {} };
    cache[name] = m;
    modules[name](m, m.exports, req);
  }
  return cache[name].exports;
}

// ---------- ambiente mínimo ----------
// Os módulos de lógica não tocam no DOM, mas o assetLoader referencia
// `document` no placeholder — damos um stub inofensivo.
globalThis.window = { EMBEDDED: null };
globalThis.document = {
  createElement: () => ({
    width: 0, height: 0,
    getContext: () => new Proxy({}, { get: () => () => {} }),
  }),
};
globalThis.performance = globalThis.performance || { now: () => Date.now() };

// ---------- helpers de teste ----------
let pass = 0, fail = 0;
const failures = [];
function check(label, cond, extra = '') {
  if (cond) { pass++; return; }
  fail++;
  failures.push(`${label}${extra ? ' — ' + extra : ''}`);
}
function section(name) { console.log(`\n\x1b[1m${name}\x1b[0m`); }

// ---------- carrega balance ----------
const BALANCE = JSON.parse(fs.readFileSync(path.join(ROOT, 'assets/data/balance.json'), 'utf8'));
const { BAL } = req('balance.js');
Object.assign(BAL, BALANCE);

// ============================================================
section('Goblin — atributos, XP, raridade');
// ============================================================
const { Goblin, ATTRS, SPECS, RARITIES, VARIATIONS } = req('goblin.js');

const g = Goblin.roll(0);
check('goblin tem nome', typeof g.name === 'string' && g.name.length > 0);
check('goblin tem especialidade válida', SPECS.includes(g.specialty), g.specialty);
check('goblin tem raridade válida', RARITIES.includes(g.rarity), g.rarity);
check('catálogo tem as 45 variações', VARIATIONS.length === 45 && new Set(VARIATIONS).size === 45);
check('goblin recebe uma variação válida', VARIATIONS.includes(g.variation), g.variation);
check('6 atributos presentes', ATTRS.every((a) => typeof g[a] === 'number'));
check('atributos entre 1 e 10', ATTRS.every((a) => g[a] >= 1 && g[a] <= 10));
check('HP derivado da vitalidade', g.maxHp === 20 + g.vitalidade * 4 + g.level * 6);
check('começa com HP cheio', g.hp === g.maxHp);

const before = g.level;
g.gainXp(10000);
check('sobe de nível com XP', g.level > before, `${before} → ${g.level}`);
check('atributos respeitam teto 10', ATTRS.every((a) => g[a] <= 10));
check('HP recalculado após subir', g.maxHp === 20 + g.vitalidade * 4 + g.level * 6);

const cands = Goblin.candidates(0, []);
check('recrutamento gera 3 candidatos', cands.length === 3);
check('candidatos têm nomes distintos', new Set(cands.map((c) => c.name)).size === 3);
check('candidatos têm variações distintas', new Set(cands.map((c) => c.variation)).size === 3);
const cookSave = new Goblin({ ...g, assignment: 'cook' });
const oldUnknownJob = new Goblin({ ...g, assignment: 'made_up_old_role' });
check('save preserva a função Cozinheiro', cookSave.assignment === 'cook');
check('função antiga/desconhecida ainda migra para Livre', oldUnknownJob.assignment === null);

// sorte crescente: com muitos recrutas, raridade média deve subir
const rarityScore = (r) => RARITIES.indexOf(r);
const avg = (n) => {
  let s = 0;
  for (let i = 0; i < 4000; i++) s += rarityScore(Goblin.rollRarity(n));
  return s / 4000;
};
const low = avg(0), high = avg(100);
check('sorte crescente aumenta raridade', high > low, `0 recrutas=${low.toFixed(3)} · 100=${high.toFixed(3)}`);

// Chances pedidas: 1/2 comum, 1/5 incomum, 1/10 raro, 1/50 épico, 1/100 mítico,
// 1/500 lendário e 1/5000 divino. O numerador sobe 0,1 por goblin recrutado e
// a faixa some do sorteio quando ele alcança o denominador.
const { RARITY_DENOMINATOR, RARITY_LUCK_STEP } = req('goblin.js');
check('as sete faixas existem, do comum ao divino',
  RARITIES.join(',') === 'common,uncommon,rare,epic,mythic,legendary,divine');
check('os denominadores são 2, 5, 10, 50, 100, 500 e 5000',
  JSON.stringify(RARITY_DENOMINATOR)
  === JSON.stringify({ common: 2, uncommon: 5, rare: 10, epic: 50, mythic: 100, legendary: 500, divine: 5000 }));
check('cada goblin recrutado soma um décimo ao numerador', RARITY_LUCK_STEP === 0.1);

const oddsAt = (n) => Object.fromEntries(Goblin.rarityOdds(n).map((row) => [row.rarity, row]));
const start0 = oddsAt(0);
check('sem recrutas, as frações começam em 1/denominador',
  Object.values(start0).every((row) => row.numerator === 1 && !row.maxed));
const nine = oddsAt(9);
check('com 9 goblins todas as faixas estão em 1,9/denominador',
  Math.abs(nine.common.numerator - 1.9) < 1e-9
  && Math.abs(nine.divine.numerator - 1.9) < 1e-9
  && Object.values(nine).every((row) => !row.maxed));
const ten = oddsAt(10);
check('com 10 goblins o comum chega a 2/2 e para de aparecer',
  ten.common.maxed && ten.common.chance === 0
  && Math.abs(ten.uncommon.numerator - 2) < 1e-9 && !ten.uncommon.maxed);
check('faixas restantes continuam proporcionais depois do corte',
  Math.abs(ten.uncommon.chance / ten.rare.chance - 2) < 1e-9
  && Math.abs(ten.rare.chance / ten.epic.chance - 5) < 1e-9);
check('incomum e raro também se esgotam no seu tempo (40 e 90 goblins)',
  oddsAt(39).uncommon.maxed === false && oddsAt(40).uncommon.maxed === true
  && oddsAt(89).rare.maxed === false && oddsAt(90).rare.maxed === true);
check('o divino nunca se esgota numa partida realista',
  !oddsAt(500).divine.maxed && oddsAt(500).divine.chance > 0);

let raritySeed = 20261001;
const rarityRng = () => {
  raritySeed = (raritySeed * 1103515245 + 12345) % 2147483648;
  return raritySeed / 2147483648;
};
const SAMPLES = 400000;
const rolls = Object.fromEntries(RARITIES.map((r) => [r, 0]));
for (let i = 0; i < SAMPLES; i++) rolls[Goblin.rollRarity(0, rarityRng)] += 1;
const offBy = RARITIES.map((r) => Math.abs(rolls[r] / SAMPLES - start0[r].chance));
check('o sorteio respeita as proporções 1/2 : 1/5 : 1/10 : 1/50 : 1/100 : 1/500 : 1/5000',
  Math.max(...offBy) < 0.01,
  RARITIES.map((r) => `${r} ${(100 * rolls[r] / SAMPLES).toFixed(2)}%`).join(' · '));
check('a ordem de raridade é respeitada e o divino aparece',
  rolls.divine > 0 && rolls.divine < rolls.legendary && rolls.legendary < rolls.mythic
  && rolls.mythic < rolls.epic && rolls.epic < rolls.rare
  && rolls.rare < rolls.uncommon && rolls.uncommon < rolls.common);
const cappedRolls = new Set();
for (let i = 0; i < 4000; i++) cappedRolls.add(Goblin.rollRarity(10, rarityRng));
check('faixa no máximo não é mais sorteada', !cappedRolls.has('common'));
for (const rarity of ['mythic', 'legendary', 'divine']) {
  const special = new Goblin({ rarity, name: 'Prova' });
  check(`um goblin ${rarity} é válido e persiste no save`,
    RARITIES.includes(special.rarity)
    && new Goblin(JSON.parse(JSON.stringify(special))).rarity === rarity);
}

// ============================================================
section('Village — recursos, construção, habitação');
// ============================================================
const { Village } = req('village.js');
const v = new Village();

check('recursos iniciais do balance', v.res.wood === BALANCE.startResources.wood);
check('começa sem estruturas no mapa', v.structures.length === 0, String(v.structures.length));
check('começa sem casas e sem capacidade', v.houses.length === 0 && v.capacity === 0);
check('começa sem goblins na ilha', v.goblins.length === 0);

const startWood = v.res.wood, startStone = v.res.stone;
const foundation = v.beginBuildAt('construction', 920, 706);
check('Casa de Construção grátis aparece como lona pronta sem cronômetro',
  foundation?.type === 'construction' && foundation.construction?.status === 'ready'
  && foundation.construction.total === 0 && !v.has('construction')
  && v.res.wood === startWood && v.res.stone === startStone);
check('recolher a lona da fundação é que libera a Casa de Construção',
  v.completeConstruction(foundation) && v.has('construction'));
const board = v.beginBuildAt('quest', 960, 650);
check('Painel gratuito ainda é uma obra cronometrada',
  board?.construction?.status === 'building' && board.construction.total === 10);
const firstHouse = v.beginBuildAt('house', 1000, 706);
check('primeira Casa grátis também nasce como lona brilhante sem tempo',
  firstHouse?.type === 'house' && firstHouse.construction?.status === 'ready'
  && firstHouse.construction.total === 0 && v.capacity === 0);
check('recolher a primeira lona libera a capacidade, não um goblin automático',
  v.completeConstruction(firstHouse) && v.capacity === 1 && v.goblins.length === 0);
check('primeira Casa não consumiu recursos', v.res.wood === startWood && v.res.stone === startStone);
check('recruta só cabe depois da primeira Casa', v.recruit(Goblin.roll(0)) && v.goblins.length === 1);
check('a segunda e a terceira Casa também são grátis', v.buildHouse() && v.buildHouse()
  && v.houses.length === 3 && v.res.wood === startWood && v.res.stone === startStone);

const woodBefore = v.res.wood;
const built = v.buildHouse();
check('quarta Casa passa a custar recursos', built === true);
check('pagou o custo em madeira depois das três grátis', v.res.wood === woodBefore - BALANCE.house.buildCost.wood);
check('capacidade cresce com as Casas', v.capacity === 4);

v.res.wood = 0; v.res.stone = 0;
check('bloqueia construção paga sem recursos', v.buildHouse() === false);

v.res.wood = 9999; v.res.stone = 9999;
// A partir da etapa 1.8 a melhoria é limitada pelo nível da vila (§2.5),
// então a vila precisa estar no nível 3 para a casa chegar ao nível 3.
v.level = 3;
const capBefore = v.capacity;
check('melhora casa (+1 nível)', v.upgradeHouse(0) === true);
check('capacidade cresce com melhoria', v.capacity === capBefore + 1);

// teto de nível da casa
for (let i = 0; i < 10; i++) v.upgradeHouse(0);
check('respeita maxLevel da casa', v.houses[0].level === BALANCE.house.maxLevel,
  `nível ${v.houses[0].level}`);

// recrutamento respeita capacidade
const v2 = new Village();
v2.buildHouse(); // primeira casa de fundação, instantânea e gratuita
let guard = 0;
while (v2.goblins.length < v2.capacity && guard++ < 50) v2.recruit(Goblin.roll(0));
check('não recruta acima da capacidade', v2.recruit(Goblin.roll(0)) === false);

// serialização
const round = new Village(JSON.parse(JSON.stringify(v.serialize())));
check('serialize/restore preserva recursos', round.res.wood === v.res.wood);
check('serialize/restore preserva casas', round.houses.length === v.houses.length);
check('serialize/restore reconstrói Goblins', round.goblins[0] instanceof Goblin);
check('serialize/restore preserva variação', round.goblins[0].variation === v.goblins[0].variation);

// ============================================================
section('World — chão uniforme e povoamento inicial');
// ============================================================
const { World } = req('world.js');
const visualWorld = new World(17);
check('mundo novo não cria walkers antes de haver goblins', visualWorld.goblins.length === 0);
check('terra da ilha não alterna para tiles de rocha', !Array.from(visualWorld.tiles).includes(4));

// ============================================================
section('Village — XP, nível e desbloqueios (etapa 1.8)');
// ============================================================
const v3 = new Village();
check('vila começa no nível 1', v3.level === 1);
check('vila começa com 0 XP', v3.xp === 0);
check('xpNext segue 100×N^1.6', v3.xpNext() === Math.round(100 * Math.pow(1, 1.6)));

v3.gainXp(v3.xpNext());
check('sobe para nível 2 com XP exato', v3.level === 2, `nível ${v3.level}`);
check('XP sobrando zera', v3.xp === 0, String(v3.xp));

const ups = v3.gainXp(100000);
check('XP grande sobe vários níveis', ups > 1, `+${ups} níveis`);
check('respeita o nível máximo', v3.level <= (BALANCE.village.maxLevel ?? 20), `nível ${v3.level}`);

const v4 = new Village();
check('nível 1 libera só as iniciais', v4.unlockedAt(1).includes('house'));
check('nível 2 libera serraria e fazenda',
  v4.unlockedAt(2).includes('serraria') && v4.unlockedAt(2).includes('fazenda'));
check('nível 5 libera ferraria', v4.unlockedAt(5).includes('ferraria'));

// ---------- gates de construção ----------
v4.res = { wood: 9999, stone: 9999, ore: 9999, food: 9999, gold: 9999 };
check('serraria bloqueada no nível 1', v4.blockedReason('serraria')?.reason === 'level');
check('build() recusa estrutura travada', v4.build('serraria') === null);

v4.level = 2;
check('serraria liberada no nível 2', v4.canBuild('serraria') === true);
const saw = v4.build('serraria');
check('constrói a serraria', saw !== null && saw.type === 'serraria');
check('serraria aparece no estado', v4.has('serraria'));
check('bloqueia duplicata (maxCount 1)', v4.blockedReason('serraria')?.reason === 'count');

v4.res = { wood: 0, stone: 0, ore: 0, food: 0, gold: 0 };
v4.level = 3;
check('sem recursos → motivo cost', v4.blockedReason('cozinha')?.reason === 'cost');

// ---------- melhoria limitada pelo nível da vila ----------
const v5 = new Village();
v5.buildHouse();
v5.res = { wood: 9999, stone: 9999, ore: 9999, food: 9999, gold: 9999 };
v5.level = 1;
check('teto de melhoria = nível da vila', v5.maxUpgradeLevel('house') === 1);
check('não melhora além do nível da vila', v5.upgrade(v5.houses[0]) === false);
v5.level = 3;
check('teto sobe junto com a vila', v5.maxUpgradeLevel('house') === 3);
check('agora melhora', v5.upgrade(v5.houses[0]) === true);
check('melhorar Casa aumenta a capacidade e libera nova vaga', v5.capacity === 2 && v5.goblins.length < v5.capacity);
const timedHouse = new Village();
timedHouse.buildHouse(); timedHouse.level = 3;
timedHouse.res = { wood: 999, stone: 999, ore: 999, food: 999, gold: 999 };
const timedHome = timedHouse.houses[0];
check('melhoria de Casa por obra só ganha vaga ao ser recolhida',
  timedHouse.beginUpgrade(timedHome) && timedHouse.capacity === 1
  && ((timedHome.construction.status = 'ready'), timedHouse.completeConstruction(timedHome))
  && timedHouse.capacity === 2);
const constructionSpeedVillage = new Village();
constructionSpeedVillage.level = 3;
constructionSpeedVillage.res = { wood: 999, stone: 999, ore: 999, food: 999, gold: 999 };
constructionSpeedVillage.build('construction');
constructionSpeedVillage.upgrade(constructionSpeedVillage.get('construction'));
check('Casa de Construção melhorada acelera todas as obras', constructionSpeedVillage.constructionSpeed() === 1.25);

// ---------- Modo Teste: carteira infinita e moradia livre ----------
const testV = new Village();
testV.setUnlimited(true);
const testGoldBefore = testV.res.gold;
testV.pay({ wood: 40, stone: 30, gold: 25 });
check('modo Teste não desconta recursos ao pagar',
  testV.res.gold === testGoldBefore && testV.res.wood >= 999999);
check('modo Teste pode pagar qualquer custo', testV.canAfford({ wood: 1e9, gold: 1e9 }));
testV.level = 8;
check('modo Teste constrói o que quiser sem recursos', testV.build('quartel') !== null);
const { Goblin: TestGoblin } = req('goblin.js');
check('modo Teste recruta sem depender de casas',
  testV.capacity === 0 && testV.recruit(TestGoblin.roll(0)) === true);
check('modo Teste persiste no save', new Village(JSON.parse(JSON.stringify(testV.serialize()))).unlimited === true);
const normalV = new Village();
normalV.pay({ wood: 10 });
check('modo Normal segue descontando normalmente',
  normalV.res.wood === (new Village()).res.wood - 10 && !normalV.unlimited);

// ============================================================
section('Village — obras com tempo, lona e recolhimento');
// ============================================================
const buildV = new Village();
buildV.buildHouse(); // a segunda casa é a primeira obra cronometrada
buildV.level = 3;
buildV.res = { wood: 9999, stone: 9999, ore: 9999, food: 9999, gold: 9999 };
check('tempos seguem 10 × (nível da vila exigido + nível da estrutura - 1)',
  buildV.constructionSeconds('house', 1) === 10
  && buildV.constructionSeconds('house', 2) === 20
  && buildV.constructionSeconds('house', 3) === 30
  && buildV.constructionSeconds('serraria', 1) === 20
  && buildV.constructionSeconds('serraria', 3) === 40
  && buildV.constructionSeconds('cozinha', 1) === 30
  && buildV.constructionSeconds('cozinha', 3) === 50);
const pendingHouse = buildV.beginBuildAt('house', 840, 760);
check('construir pelo fluxo do jogo cria uma obra pendente',
  pendingHouse?.construction?.status === 'building' && pendingHouse.construction.total === 10);
check('obra pendente não aumenta capacidade nem fica funcional',
  buildV.capacity === 1 && buildV.countOf('house') === 2 && buildV.houses.length === 1);
check('não recolhe lona antes de terminar', buildV.completeConstruction(pendingHouse) === false);
pendingHouse.construction.status = 'ready'; pendingHouse.construction.remaining = 0;
check('recolher lona pronta finaliza estrutura e libera capacidade',
  buildV.completeConstruction(pendingHouse) && buildV.capacity === 2 && buildV.houses.length === 2);
const upgradingHouse = buildV.houses[0];
check('melhoria cria obra de 20 segundos sem subir o nível na hora',
  buildV.beginUpgrade(upgradingHouse) && upgradingHouse.level === 1
  && upgradingHouse.construction?.total === 20);
upgradingHouse.construction.status = 'ready';
check('recolher melhoria aplica o nível alvo',
  buildV.completeConstruction(upgradingHouse) && upgradingHouse.level === 2);

// ============================================================
section('Quests — painel de missões (etapa 1.7)');
// ============================================================
const { Quests, Quest } = req('quests.js');
const qv = new Village();
qv.res = { wood: 9999, stone: 9999, ore: 9999, food: 9999, gold: 0 };
const qs = new Quests();
qs.ensure(qv.level);

check('painel enche os 3 slots', qs.list.length === BALANCE.quests.slots, String(qs.list.length));
check('missões pedem algo', qs.list.every((q) => q.qty > 0));
check('missões dão ouro e XP', qs.list.every((q) => q.gold > 0 && q.xp > 0));
check('XP respeita o teto do balance',
  qs.list.every((q) => q.xp >= BALANCE.quests.xpMin && q.xp <= BALANCE.quests.xpMax));
check('nível 1 não pede minério (gate)',
  Array.from({ length: 200 }, () => Quest.roll(1).key).every((k) => k !== 'ore'));

const q0 = qs.list[0];
const goldBefore = qv.res.gold;
const xpBefore = qv.xp;
const result = qs.deliver(q0, qv);
check('entrega funciona com estoque', result !== null);
check('pagou ouro', qv.res.gold === goldBefore + q0.gold);
check('deu XP à vila', qv.xp > xpBefore || qv.level > 1);
check('slot entra em renovação', qs.pending.length === 1);
check('missão saiu da lista', !qs.list.includes(q0));
check('contador de concluídas subiu', qs.completed === 1);

qs.update(BALANCE.quests.renewSeconds + 1, qv.level);
check('slot renova após o tempo', qs.list.length === BALANCE.quests.slots - 0, String(qs.list.length));
check('pendência foi limpa', qs.pending.length === 0);

const poor = new Village();
poor.res = { wood: 0, stone: 0, ore: 0, food: 0, gold: 0 };
const qs2 = new Quests();
qs2.ensure(1);
check('não entrega sem os itens', qs2.deliver(qs2.list[0], poor) === null);

// ============================================================
section('Cooking — cozinha e cura (etapa 1.4)');
// ============================================================
const cooking = req('cooking.js');
const cv = new Village();
cv.buildHouse();
cv.recruit(Goblin.roll(0));
cv.res = { wood: 100, stone: 100, ore: 100, food: 100, gold: 100 };

check('sem cozinha, nada liberado', cooking.available(0).length === 0);
check('cozinha nv1 libera pão e sopa', cooking.available(1).length === 2);
check('cozinha nv3 libera tudo', cooking.available(3).length === cooking.RECIPES.length);

check('não cozinha sem cozinha construída', cooking.cook(cv, 'bread') === null);

cv.level = 3;
cv.build('cozinha');
check('cozinha foi construída', cv.has('cozinha'));

const foodBefore = cv.res.food;
const out = cooking.cook(cv, 'bread', () => 0.99);   // rng alto: sem bônus
check('cozinhou pão', out !== null && out.id === 'bread');
check('consumiu comida crua', cv.res.food === foodBefore - 3);
check('pão foi para a despensa', cv.meals.bread >= 1);

  check('receita travada pelo nível da cozinha', cooking.cook(cv, 'feast') === null);

  // A interface separa os ingredientes ao iniciar, mas o prato só entra na
  // despensa depois de o cozinheiro terminar seu cronômetro.
  const rawBefore = cv.res.food;
  const prep = cooking.beginCook(cv, 'soup');
  check('preparo cria trabalho de 10 segundos', prep?.total === 10 && prep.remaining === 10);
  check('preparo reserva ingredientes sem entregar prato',
    cv.res.food === rawBefore - 5 && !cv.meals.soup);
  check('não abre segundo preparo enquanto a panela está ocupada', cooking.beginCook(cv, 'bread') === null);
  const queueFoodBefore = cv.res.food;
  check('fila aceita receitas sem cobrar antes de iniciar',
    cooking.enqueue(cv, 'bread') === 1 && cooking.enqueue(cv, 'soup') === 2
    && cv.res.food === queueFoodBefore && cv.cookingQueue.join(',') === 'bread,soup');
  check('remover da fila preserva a ordem', cooking.dequeueAt(cv, 0) === 'bread' && cv.cookingQueue.join(',') === 'soup');
  while (cv.cookingQueue.length < cooking.MAX_QUEUE) cooking.enqueue(cv, 'bread');
  check('fila limita a 20 receitas', cv.cookingQueue.length === cooking.MAX_QUEUE && cooking.enqueue(cv, 'bread') === null);
  const restoredPrep = new Village(cv.serialize());
  check('preparo e fila pendentes persistem no save', restoredPrep.cookingJob?.recipeId === 'soup'
    && restoredPrep.cookingJob.remaining === 10 && restoredPrep.cookingQueue.length === cooking.MAX_QUEUE);
  prep.status = 'ready';
  const prepared = cooking.finishCook(cv, () => 0.99);
  check('prato só é entregue ao completar o preparo', prepared?.id === 'soup' && cv.meals.soup === 1 && !cv.cookingJob);
  check('tempos seguem 10/20/30 por nível de receita',
    cooking.cookingSeconds('bread') === 10 && cooking.cookingSeconds('stew') === 20 && cooking.cookingSeconds('feast') === 30);
  check('um, dois e três cozinheiros escalam a velocidade real',
    cooking.cookSpeed(1) === 1 && cooking.cookSpeed(2) === 2 && cooking.cookSpeed(3) === 3 && cooking.cookSpeed(4) === 3);
  const kitchenForRecipes = cv.get('cozinha');
  cv.level = 3;
  cv.upgrade(kitchenForRecipes);
  const stewJob = cooking.beginCook(cv, 'stew');
  check('cozinheiros aceitam ensopado com Cozinha nível 2', stewJob?.recipeId === 'stew' && stewJob.total === 20);
  stewJob.status = 'ready';
  check('ensopado termina e entra na despensa', cooking.finishCook(cv, () => 0.99)?.id === 'stew' && cv.meals.stew === 1);
  cv.res.wood = 999; cv.res.stone = 999; cv.res.gold = 999;
  cv.upgrade(kitchenForRecipes);
  const feastJob = cooking.beginCook(cv, 'feast');
  check('cozinheiros aceitam banquete com Cozinha nível 3', feastJob?.recipeId === 'feast' && feastJob.total === 30);
  feastJob.status = 'ready';
  check('banquete termina e entra na despensa', cooking.finishCook(cv, () => 0.99)?.id === 'feast' && cv.meals.feast === 1);

  const hurtGoblin = cv.goblins[0];
hurtGoblin.hp = 1;
const healed = cooking.feed(cv, hurtGoblin, 'bread');
check('comer cura HP', healed > 0, `curou ${healed}`);
check('consumiu o prato', (cv.meals.bread || 0) === 0);
check('não cura acima do máximo', hurtGoblin.hp <= hurtGoblin.maxHp);

hurtGoblin.hp = hurtGoblin.maxHp;
cv.meals.bread = 1;
check('não desperdiça em goblin cheio', cooking.feed(cv, hurtGoblin, 'bread') === 0);
check('prato continua guardado', cv.meals.bread === 1);

// ============================================================
section('Market — vender e comprar (etapa 1.6)');
// ============================================================
const market = req('market.js');

const mv = new Village();
mv.res = { wood: 100, stone: 50, ore: 10, food: 20, gold: 200 };
check('sem Mercado construído, não vende', market.sell(mv, 'res', 'wood', 10) === 0);
check('sem Mercado construído, não compra', market.buy(mv, 'res', 'stone', 1) === 0);
check('madeira intacta depois da tentativa', mv.res.wood === 100);

mv.level = 3;
mv.build('mercado');
check('Mercado construído no nível 3', mv.has('mercado'));

// ----- preços -----
const pSell = market.sellPrice(mv, 'res', 'wood');
const pBuy = market.buyPrice(mv, 'res', 'wood');
check('compra custa mais que a venda paga', pBuy > pSell, `${pSell} → ${pBuy}`);
check('minério vale mais que madeira',
  market.sellPrice(mv, 'res', 'ore') > market.sellPrice(mv, 'res', 'wood'));
check('prato vale mais que recurso cru',
  market.sellPrice(mv, 'meal', 'bread') > market.sellPrice(mv, 'res', 'food'));

// ----- venda -----
const mGoldBefore = mv.res.gold;
const mWoodBefore = mv.res.wood;
const mGot = market.sell(mv, 'res', 'wood', 10);
check('vender rende ouro', mGot === pSell * 10, `${mGot} ouro`);
check('ouro entrou no caixa', mv.res.gold === mGoldBefore + mGot);
check('madeira saiu do estoque', mv.res.wood === mWoodBefore - 10, `${mv.res.wood}`);
check('não vende mais do que tem', market.sell(mv, 'res', 'ore', 999) === 0);
check('não vende quantidade zero/negativa',
  market.sell(mv, 'res', 'wood', 0) === 0 && market.sell(mv, 'res', 'wood', -5) === 0);

// ----- compra -----
const g2 = mv.res.gold;
const stoneBefore = mv.res.stone;
const spent = market.buy(mv, 'res', 'stone', 3);
check('comprar gasta ouro', spent === market.buyPrice(mv, 'res', 'stone') * 3);
check('ouro saiu do caixa', mv.res.gold === g2 - spent);
check('pedra entrou no estoque', mv.res.stone === stoneBefore + 3, `${mv.res.stone}`);

const pobre = new Village();
pobre.level = 3; pobre.res = { wood: 0, stone: 0, ore: 0, food: 0, gold: 1 };
pobre.build('mercado');
check('sem ouro, não compra', market.buy(pobre, 'res', 'ore', 1) === 0);
check('maxBuy respeita o ouro', market.maxBuy(pobre, 'res', 'ore') === 0);

// ----- pratos -----
mv.meals = { bread: 4 };
const bg = market.sell(mv, 'meal', 'bread', 2);
check('vende pratos cozinhados', bg > 0, `${bg} ouro`);
check('despensa diminuiu', mv.meals.bread === 2);
mv.res.gold += 1000;
check('compra prato liberado pelo nível do Mercado',
  market.buy(mv, 'meal', 'bread', 1) > 0);
check('prato comprado entra na despensa', mv.meals.bread === 3);
check('prato acima do nível do Mercado não está à venda',
  market.buy(mv, 'meal', 'feast', 1) === 0);

// ----- catálogo e limites -----
const sellCat = market.catalog(mv, 'sell');
const buyCat = market.catalog(mv, 'buy');
check('catálogo de venda tem recursos e pratos',
  sellCat.some((i) => i.kind === 'res') && sellCat.some((i) => i.kind === 'meal'));
check('catálogo traz preço e quantidade',
  sellCat.every((i) => i.price > 0 && typeof i.have === 'number'));
check('catálogo de compra esconde prato travado',
  !buyCat.some((i) => i.kind === 'meal' && i.key === 'feast'));
check('maxSell é o que o jogador tem',
  market.maxSell(mv, 'res', 'wood') === mv.res.wood);

// ----- melhorar o Mercado melhora o negócio -----
const mercado = mv.get('mercado');
const antesVenda = market.sellPrice(mv, 'res', 'ore');
const antesCompra = market.buyPrice(mv, 'res', 'ore');
mv.res = { wood: 9999, stone: 9999, ore: 9999, food: 9999, gold: 9999 };
mv.level = 5;
mv.upgrade(mercado);
check('Mercado subiu de nível', mercado.level === 2);
check('mercado melhor paga mais na venda',
  market.sellPrice(mv, 'res', 'ore') >= antesVenda);
check('mercado melhor cobra menos na compra',
  market.buyPrice(mv, 'res', 'ore') <= antesCompra);
check('mesmo melhorado, comprar continua mais caro que vender',
  market.buyPrice(mv, 'res', 'ore') > market.sellPrice(mv, 'res', 'ore'));

// ============================================================
section('Inventory — armazém, itens e espaços');
// ============================================================
const inv = req('inventory.js');

check('catálogo tem os equipamentos sem runa', inv.ITEMS.length === 13, `${inv.ITEMS.length} itens`);
check('todo item tem ícone e preço', inv.ITEMS.every((i) => i.icon && i.price > 0));
check('9 espaços no boneco', inv.EQUIP_SLOTS.length === 9);
check('espaços esperados sem runa',
  ['capacete', 'peitoral', 'botas', 'calca', 'anel1', 'anel2',
    'arma_primaria', 'arma_secundaria', 'colar']
    .every((k) => inv.EQUIP_SLOTS.includes(k)) && !inv.EQUIP_SLOTS.includes('runa'));

const iv = new Village();
iv.buildHouse();
iv.recruit(Goblin.roll(0));
check('sem armazém: 0 espaços de item', iv.itemCapacity() === 0);
iv.level = 2;
iv.res = { wood: 999, stone: 999, ore: 99, food: 99, gold: 999 };
check('armazém liberado no nível 2', iv.canBuild('armazem'));
check('constrói o armazém', iv.build('armazem') !== null);
check('armazém nv1 → 16 espaços', iv.itemCapacity() === 16);

iv.addItem('espada_ferro', 3);
iv.addItem('anel_rubi', 2);
check('conta itens guardados', iv.itemsCount() === 5);
check('capacidade sobe com o nível', (iv.upgrade(iv.get('armazem')), iv.itemCapacity() === 24));

const ig = iv.goblins[0];
check('equipa item', inv.equip(iv, ig, 'arma_primaria', 'espada_ferro') === true);
check('item sai do armazém', iv.itemsCount() === 4);
check('espaço ocupado', ig.equip.arma_primaria === 'espada_ferro');
check('tipo errado recusa', inv.equip(iv, ig, 'capacete', 'espada_ferro') === false);
check('anel serve nos dois espaços',
  inv.equip(iv, ig, 'anel1', 'anel_rubi') && inv.equip(iv, ig, 'anel2', 'anel_rubi'));
check('troca devolve a peça antiga',
  (iv.addItem('espada_ferro', 1), inv.equip(iv, ig, 'arma_primaria', 'espada_ferro'))
  && iv.items.espada_ferro === 3);
check('desequipar devolve ao armazém',
  inv.unequip(iv, ig, 'anel1') === 'anel_rubi' && iv.items.anel_rubi === 1);
check('conta peças equipadas', inv.equippedCount(ig) === 2);   // arma + anel II

// migração de save antigo (gear de compra única → itens)
const legacy = new Village({ gear: { peitoral_avaritia: true, calca_avaritia: false } });
check('save antigo migra peças p/ o inventário',
  legacy.items.peitoral_avaritia === 1 && !legacy.items.calca_avaritia);
const legacyRune = new Village({
  items: { espada_ferro: 1, runa_azul: 4 },
  goblins: [{ name: 'Gruk', equip: { runa: 'runa_azul', espada_ferro: 'espada_ferro' } }],
});
check('save antigo descarta runa guardada e equipada',
  !legacyRune.items.runa_azul && !legacyRune.goblins[0].equip.runa
  && legacyRune.goblins[0].equip.espada_ferro === 'espada_ferro');

// persistência
const iround = new Village(JSON.parse(JSON.stringify(iv.serialize())));
check('itens persistem no save', iround.itemsCount() === iv.itemsCount());
check('equipamento persiste no goblin', iround.goblins[0].equip.anel2 === 'anel_rubi');

// ============================================================
section('Abilities — habilidades por goblin');
// ============================================================
const abilities = req('abilities.js');
check('catálogo tem 10 habilidades', abilities.ABILITIES.length === 10);
check('toda habilidade tem ícone', abilities.ABILITIES.every((a) => a.icon));
check('3 espaços por goblin', abilities.SKILL_SLOTS === 3);

const ag = new Goblin({ name: 'Grak', specialty: 'warrior', variation: '01_dente_dourado' });
const specAb = abilities.ABILITIES.find((a) => a.spec === ag.specialty);
const otherAb = abilities.ABILITIES.find((a) => a.spec && a.spec !== ag.specialty);
const generic = abilities.byId('investida');
check('aceita habilidade da própria especialidade', abilities.canEquip(ag, specAb));
check('recusa habilidade de outra especialidade', !abilities.canEquip(ag, otherAb));
check('genérica serve p/ todos', abilities.canEquip(ag, generic));

check('equipa no espaço 0', abilities.equipAbility(ag, 0, specAb.id) === true);
check('equipa genérica no espaço 1', abilities.equipAbility(ag, 1, generic.id) === true);
check('terceiro espaço aceita a mesma regra', abilities.equipAbility(ag, 2, specAb.id) === true && ag.skills[2] === specAb.id);
check('re-equipar MOVE em vez de duplicar',
  abilities.equipAbility(ag, 1, specAb.id) === true
  && ag.skills.filter(Boolean).length === 1 && ag.skills[1] === specAb.id);
check('recusa classe errada', abilities.equipAbility(ag, 0, otherAb.id) === false);
check('remove habilidade', abilities.unequipAbility(ag, 1) === specAb.id);

// ============================================================
section('Divindades — canto, arremesso, distância e limite');
// ============================================================
const { Nodes, REMNANT_LIFETIME } = req('nodes.js');
const { Deities, ISLAND_NODE_CAP, ANIMATION_FRAMES, MAX_WORSHIPPERS } = req('deities.js');
const deityVillage = new Village();
deityVillage.level = 3;
deityVillage.res = { wood: 9999, stone: 9999, ore: 0, food: 0, gold: 9999 };
check('nível 3 libera a Grande Árvore', deityVillage.canBuild('grande_arvore'));
check('nível 3 libera o Golem de Pedra', deityVillage.canBuild('golem_pedra'));
check('Mina não existe mais no catálogo', !('mina' in req('village.js').BUILDINGS));
deityVillage.build('grande_arvore');
deityVillage.build('golem_pedra');
check('santuários não usam o fluxo comum de melhorias',
  deityVillage.maxUpgradeLevel('grande_arvore') === 1 && deityVillage.maxUpgradeLevel('golem_pedra') === 1);

const deityWorld = {
  clearing: { x: 960, y: 720, r: 160 },
  tiles: new Uint8Array(120 * 90).fill(3),
  floats: [],
  goblins: [
    { i: 0, x: 960, y: 720, job: null, target: null },
    { i: 1, x: 970, y: 720, job: null, target: null },
  ],
};
const deityNodes = new Nodes(deityWorld, [
  { type: 'tree', x: 80, y: 80, stock: 15, max: 15, depleted: false },
]);
let seed = 123456;
const deityRng = () => {
  seed = (Math.imul(seed, 1664525) + 1013904223) >>> 0;
  return seed / 4294967296;
};
const gods = new Deities(deityWorld, deityVillage, deityNodes, deityRng);
check('Golem entrega pedra-base, nunca minério', gods.production('golem_pedra')?.key === 'stone');
check('divindades começam sem goblins e desligadas',
  !gods.isActive('grande_arvore') && !gods.isActive('golem_pedra')
  && deityWorld.goblins.every((w) => !w.job));
const treeActivation = gods.activate('grande_arvore');
const golemActivation = gods.activate('golem_pedra');
check('jogador ativa cada divindade com um goblin livre', treeActivation.ok && golemActivation.ok);
// O world.js transforma worship-goto em worship ao chegar; aqui avançamos
// diretamente porque este é um teste puro sem GoblinWalker.
deityWorld.goblins.forEach((w) => { w.job.type = 'worship'; });
check('animações possuem mais quadros',
  ANIMATION_FRAMES.treeChant >= 24 && ANIMATION_FRAMES.golemForge >= 24);
let sawChant = false, sawForge = false, sawProjectile = false;
let sawTreeRise = false, sawRockLand = false;
// Tempo para observar ciclos, crescimento e o projétil sem depender do teto.
for (let i = 0; i < 12000; i++) {
  deityNodes.update(0.1);
  gods.update(0.1);
  sawChant ||= gods.states.grande_arvore.mode === 'chant';
  sawForge ||= gods.states.golem_pedra.mode === 'forge';
  sawProjectile ||= gods.projectiles.length > 0;
  sawTreeRise ||= deityNodes.list.some((n) => n.divine && n.type === 'tree' && n.growth < 1);
  sawRockLand ||= deityNodes.list.some((n) => n.divine && n.type === 'rock');
}
check('Grande Árvore entra na animação de canto', sawChant);
check('Golem entra na animação de criação/arremesso', sawForge && sawProjectile);
check('árvore divina surge do chão', sawTreeRise);
check('pedra arremessada cai e permanece como nó', sawRockLand);
let deityDrawError = null;
try {
  gods.states.grande_arvore.mode = 'chant'; gods.states.grande_arvore.time = 1.1;
  gods.states.golem_pedra.mode = 'forge'; gods.states.golem_pedra.time = 0.5;
  gods.states.golem_pedra.launched = false;
  gods.projectiles.push({
    type: 'rock', x: 900, y: 500, groundY: 620, spin: 1.2,
    trail: [{ x: 895, y: 505, spin: 1 }], progress: 0.5,
  });
  const noop = () => {};
  const drawCtx = new Proxy({ globalAlpha: 1 }, {
    get: (target, key) => (key in target ? target[key] : noop),
    set: (target, key, value) => { target[key] = value; return true; },
  });
  for (const drawable of gods.drawList(123)) drawable.draw(drawCtx);
  for (const drawable of deityNodes.drawList()) drawable.draw(drawCtx);
} catch (error) { deityDrawError = error; }
check('divindades, acólitos e nós animados desenham sem erro',
  deityDrawError === null, deityDrawError?.message);
check('teto por tipo da ilha é 200', ISLAND_NODE_CAP === 200, String(ISLAND_NODE_CAP));
const freshNodes = new Nodes(visualWorld);
check('ilha real nova começa com 200 árvores e 200 pedras',
  freshNodes.countActive('tree') === 200 && freshNodes.countActive('rock') === 200,
  `${freshNodes.countActive('tree')} árvores, ${freshNodes.countActive('rock')} pedras`);
const cappedNodes = new Nodes(deityWorld, [
  ...Array.from({ length: 205 }, (_, i) => ({ type: 'tree', x: i * 3, y: 10, stock: 1, max: 1, depleted: false })),
  ...Array.from({ length: 205 }, (_, i) => ({ type: 'rock', x: i * 3, y: 50, stock: 1, max: 1, depleted: false })),
]);
check('save acima do teto é limitado a 200 árvores e 200 pedras',
  cappedNodes.countActive('tree') === ISLAND_NODE_CAP && cappedNodes.countActive('rock') === ISLAND_NODE_CAP);
const spawned = deityNodes.list.filter((n) => n.divine);
check('todos os milagres ficam a pelo menos 190px das estruturas',
  spawned.every((n) => deityVillage.structures.every((s) => Math.hypot(n.x - s.x, n.y - s.y) >= 190)));
const divineRound = new Nodes(deityWorld, JSON.parse(JSON.stringify(deityNodes.serialize())));
check('árvores e pedras persistem no save sem ultrapassar 200',
  divineRound.countActive('tree') <= ISLAND_NODE_CAP && divineRound.countActive('rock') <= ISLAND_NODE_CAP);
// A produção respeita a lotação da ilha: em 200 árvores ativas, ela espera.
// Quando uma é coletada, a vaga gera outra árvore e novo material-base, sem
// um limite vitalício de reposições.
deityNodes.list = cappedNodes.list;
gods.states.grande_arvore.mode = 'idle'; gods.states.grande_arvore.cooldown = 0;
const cappedWood = deityVillage.res.wood || 0;
for (let i = 0; i < 300; i++) gods.update(0.1);
check('Grande Árvore não produz enquanto a ilha está no teto',
  (deityVillage.res.wood || 0) === cappedWood && deityNodes.countActive('tree') === ISLAND_NODE_CAP);
const freedTree = deityNodes.list.find((n) => n.type === 'tree' && !n.depleted);
deityNodes.deplete(freedTree);
for (let i = 0; i < 300; i++) gods.update(0.1);
check('vaga colhida permite produção divina ilimitada e reposição',
  (deityVillage.res.wood || 0) > cappedWood && deityNodes.countActive('tree') === ISLAND_NODE_CAP);

// Até três acólitos dividem o santuário, aceleram a produção e enchem o XP
// persistente da divindade (não do nível físico do prédio).
const shrineVillage = new Village();
shrineVillage.level = 3;
shrineVillage.res = { wood: 9999, stone: 9999, ore: 0, food: 0, gold: 9999 };
shrineVillage.build('grande_arvore');
const shrineWorld = {
  clearing: { x: 960, y: 720, r: 160 }, tiles: new Uint8Array(120 * 90).fill(3), floats: [],
  goblins: [0, 1, 2].map((i) => ({ i, x: 940 + i * 15, y: 720, job: null, target: null })),
};
const shrineNodes = new Nodes(shrineWorld, [
  { type: 'tree', x: 20, y: 20, stock: 0, max: 1, depleted: true },
]);
const shrine = new Deities(shrineWorld, shrineVillage, shrineNodes, deityRng);
shrineVillage.goblins = [{ assignment: 'cook' }];
check('culto recusa um cozinheiro reservado, mesmo entre receitas',
  shrine.activate('grande_arvore', shrineWorld.goblins, 0).reason === 'busy');
shrineVillage.goblins[0].assignment = null;
const sent = [0, 1, 2].map((i) => shrine.activate('grande_arvore', shrineWorld.goblins, i));
shrineWorld.goblins.forEach((w) => { w.job.type = 'worship'; });
check('santuário aceita até três acólitos',
  sent.every((r) => r.ok) && shrine.status('grande_arvore').worshippers.length === MAX_WORSHIPPERS);
check('quarto acólito é recusado', shrine.activate('grande_arvore', shrineWorld.goblins).reason === 'full');
const materialsBefore = { wood: shrineVillage.res.wood || 0, hardwood: shrineVillage.res.hardwood || 0,
  ancient: shrineVillage.res.ancient_wood || 0 };
const levelOneCycle = shrine.cycleSeconds('grande_arvore');
const levelOneRate = shrine.status('grande_arvore').perMinute;
for (let i = 0; i < 500; i++) shrine.update(0.1);
check('nível 1 produz só madeira; graus futuros seguem indisponíveis',
  shrineVillage.res.wood > materialsBefore.wood
  && (shrineVillage.res.hardwood || 0) === materialsBefore.hardwood
  && (shrineVillage.res.ancient_wood || 0) === materialsBefore.ancient);
check('três acólitos multiplicam o XP de louvor (50s × 3 = 150)',
  shrine.status('grande_arvore').level === 1 && Math.round(shrine.status('grande_arvore').xp) === 150,
  `${shrine.status('grande_arvore').xp.toFixed(1)} XP`);
for (let i = 0; i < 110; i++) shrine.update(0.1);
check('três acólitos evoluem após um minuto de louvor contínuo', shrine.status('grande_arvore').level >= 2);
check('nível divino acelera a produção-base sem liberar materiais',
  shrine.cycleSeconds('grande_arvore') < levelOneCycle && shrine.status('grande_arvore').perMinute > levelOneRate);

const remnants = new Nodes(deityWorld, [
  { type: 'tree', x: 100, y: 100, stock: 1, max: 1, depleted: false },
  { type: 'rock', x: 140, y: 100, stock: 1, max: 1, depleted: false },
]);
remnants.deplete(remnants.list[0]);
remnants.deplete(remnants.list[1]);
remnants.update(REMNANT_LIFETIME - 0.1);
check('toco e entulho permanecem pelos primeiros 10 segundos', remnants.list.length === 2);
const remnantSave = remnants.serialize();
check('relógio de sumiço do resquício persiste no save', remnantSave.every((n) => n.depleted && n.decay > 0));
remnants.update(0.11);
check('toco e entulho somem após 10 segundos', remnants.list.length === 0);
check('desativar libera o goblin novamente',
  gods.deactivate('grande_arvore') && deityWorld.goblins[0].job === null);
const migratedVillage = new Village({ structures: [
  { type: 'mina', level: 2, x: 700, y: 700 },
  { type: 'house', level: 1, x: 1000, y: 706, slot: 0 },
] });
check('save antigo remove a Mina automaticamente', !migratedVillage.has('mina'));

// ============================================================
section('Save — o progresso novo persiste');
// ============================================================
const sv = new Village();
sv.level = 4; sv.xp = 77; sv.meals = { soup: 2 };
sv.res = { wood: 999, stone: 999, ore: 999, food: 999, gold: 999 };
sv.build('serraria');
const reload = new Village(JSON.parse(JSON.stringify(sv.serialize())));
check('nível da vila persiste', reload.level === 4);
check('XP da vila persiste', reload.xp === 77);
check('pratos persistem', reload.meals.soup === 2);
check('estruturas persistem', reload.has('serraria'));

const qsave = new Quests();
qsave.ensure(3);
const qreload = new Quests(JSON.parse(JSON.stringify(qsave.serialize())));
check('missões persistem', qreload.list.length === qsave.list.length);
check('missões recarregam com os mesmos pedidos',
  qreload.list[0].key === qsave.list[0].key && qreload.list[0].qty === qsave.list[0].qty);

// ============================================================
section('Combate — balão, ilha inimiga e turnos');
// ============================================================
const raid = req('raid.js');
const { Battle } = req('battle.js');
check('mapa tem a ilha da vila e 3 ilhas inimigas',
  raid.ISLANDS[0].home && raid.ISLANDS.filter((i) => !i.home).length === 3);
check('ilha 1 abre com o balão consertado', raid.islandUnlocked(raid.ISLANDS[1], 1));
check('ilha 2 exige balão nível 2', !raid.islandUnlocked(raid.ISLANDS[2], 1) && raid.islandUnlocked(raid.ISLANDS[2], 2));
check('ilha 3 exige balão nível 3', !raid.islandUnlocked(raid.ISLANDS[3], 2) && raid.islandUnlocked(raid.ISLANDS[3], 3));
const pick = [];
check('escolhe goblin pro grupo', raid.togglePartyMember(pick, 0) && pick.length === 1);
raid.togglePartyMember(pick, 1);
raid.togglePartyMember(pick, 2);
raid.togglePartyMember(pick, 3);
check('grupo para em 4', raid.togglePartyMember(pick, 4) === false && pick.length === 4);
check('desmarcar libera vaga', raid.togglePartyMember(pick, 0) && pick.length === 3);
check('melhoria do balão tem custo', !!raid.balloonUpgradeCost(1) && !raid.balloonUpgradeCost(3));
check('alcance de alerta é 6 blocos', raid.ALERT_TILES === 6 && raid.ALERT_RANGE === 6 * 16);
check('grupo do jogador é mais rápido que a patrulha', raid.PLAYER_SPEED > raid.ENEMY_SPEED);
check('chefe corre mais que o grupo', raid.BOSS_RUSH_SPEED > raid.PLAYER_SPEED);
check('consertar o balão custa madeira, pedra e ouro',
  raid.balloonCost().wood > 0 && raid.balloonCost().stone > 0 && raid.balloonCost().gold > 0);
const rw = raid.raidRewards(1);
check('recompensa de patrulha/estrutura é ouro + gemas goblinéias',
  rw.gold > 0 && rw.goblin_gems > 0);

const party = [0, 1, 2, 3].map((i) => new Goblin({
  name: 'G' + i, specialty: 'warrior', variation: '01_dente_dourado',
  poderDestrutivo: 8, vitalidade: 8, velocidade: 7, precisao: 8, level: 3,
}));
const island = new raid.RaidIsland(raid.ISLANDS[1], party, 7);
check('ilha gera o terreno', island.tiles.length === raid.RAID.COLS * raid.RAID.ROWS);
check('5 grupos de patrulha', island.patrols.length === 5);
check('ilha fácil tem 1 ou 2 inimigos por grupo',
  island.patrols.every((p) => p.members.length >= 1 && p.members.length <= 2));
check('grito do animal alcança 8 blocos', raid.SCREAM_TILES === 8 && raid.SCREAM_RANGE === 8 * 16);
check('grupo do jogador tem até 4 goblins', island.party.goblins.length === 4);
check('há árvores, pedras e baús', 
  island.loot.some((n) => n.type === 'tree')
  && island.loot.some((n) => n.type === 'rock')
  && island.loot.some((n) => n.type === 'chest'));
check('centro tem estruturas inimigas', island.buildings.length >= 3);
check('estruturas inimigas usam sprites da vila e têm vida',
  island.buildings.every((b) => b.sprite && b.maxHp >= 8));
check('patrulhas têm rota com mais de um ponto',
  island.patrols.every((p) => p.waypoints.length >= 2));
check('chefe está no centro', !!island.boss?.alive);
check('chão da Presa não é o do Fumo nem o do Ferro',
  raid.themeOf(raid.ISLANDS[1]).ground !== raid.themeOf(raid.ISLANDS[2]).ground
  && raid.themeOf(raid.ISLANDS[1]).ground !== raid.themeOf(raid.ISLANDS[3]).ground);
check('ilha das Presas tem tocas e colmeias',
  island.props.some((p) => p.type === 'den')
  && island.loot.some((n) => n.type === 'tree' && n.hive));
check('colmeia fica grudada numa árvore',
  island.loot.filter((n) => n.type === 'tree' && n.hive).length >= 1);
check('ilha das Presas tem lobos animados',
  island.animals.some((a) => a.kind === 'wolf' && a.alive));
check('ilha das Presas tem animais de caça', island.animals.filter((a) => a.alive).length >= 4);
const smokeIsle = new raid.RaidIsland(raid.ISLANDS[2], party, 11);
check('ilha do Fumo tem fumarolas e tocos',
  smokeIsle.props.some((p) => p.type === 'vent') && smokeIsle.props.some((p) => p.type === 'stump'));
check('ilha média tem 2 ou 3 inimigos por grupo',
  smokeIsle.patrols.every((p) => p.members.length >= 2 && p.members.length <= 3));
const ironIsle = new raid.RaidIsland(raid.ISLANDS[3], party, 13);
check('ilha do Ferro tem sucata e minério',
  ironIsle.props.some((p) => p.type === 'scrap') && ironIsle.props.some((p) => p.type === 'ore'));
check('ilha difícil tem 3 ou 4 inimigos por grupo',
  ironIsle.patrols.every((p) => p.members.length >= 3 && p.members.length <= 4));
const prey = island.animals.find((a) => a.alive);
const nearHunt = island.patrols[0];
const farHunt = island.patrols[1];
nearHunt.x = prey.x + 40; nearHunt.y = prey.y;
farHunt.x = prey.x + 400; farHunt.y = prey.y + 400;
island._killAnimal(prey);
check('matar animal dá comida', island.takeEvent().some((e) => e.type === 'loot' && e.kind === 'food'));
check('o grito só chama patrulha a 8 blocos, nunca o Chefe',
  nearHunt.heard === true && nearHunt.state === 'chase'
  && farHunt.heard !== true
  && island.boss.alive && island.bossEnraged === false);
island.patrols.forEach((p) => { p.heard = false; p.state = 'patrol'; });
check('não pousa no centro da cidade', island.canLand(island.center.x, island.center.y) === false);
check('pousa fora da cidade na praia', island.canLand(island.landing.x, island.landing.y) === true);
const moved = island.setLanding(island.center.x, island.center.y);
check('setLanding recusa a cidade', moved === false);
check('setLanding aceita a praia', island.setLanding(island.landing.x, island.landing.y) === true);
island.movePartyTo(island.party.x + 40, island.party.y);
island.update(0.5);
check('toque move o grupo em formação', island.party.anim === 'walk' || island.party.target == null);

const chest = island.loot.find((n) => n.type === 'chest');
island.party.x = chest.x; island.party.y = chest.y + 10;
island.party.target = null;
island.party.job = { type: 'loot', obj: chest };
island._arrive();
check('abrir baú deixa o item no chão brilhando',
  chest.taken === true && island.drops.some((d) => !d.taken));
const drop = island.drops.find((d) => !d.taken);
const remaining = island.drops.filter((d) => !d.taken).length;
island.party.x = drop.x; island.party.y = drop.y;
island._updateDrops(0.05);
check('encostar no loot do chão recolhe',
  island.drops.filter((d) => !d.taken).length < remaining);
island.takeEvent();

island.beginFlyIn(1);
check('pouso esconde o grupo no balão voando', island.flyingIn() === true);
island.update(0.2);
check('durante a descida o grupo não anda', island.party.target == null);
island.update(1);
check('depois do pouso o grupo aparece', island.flyingIn() === false);

island.busy = false;
island.leftBalloon = true;
island.party.x = island.landing.x;
island.party.y = island.landing.y;
island._checkReturnHome();
check('voltar ao balão pede a ilha da vila', island.takeEvent().some((e) => e.type === 'return_home'));
island.busy = false;

island.busy = false;
const gA = island.patrols[0], gB = island.patrols[1], gC = island.patrols[2];
gA.x = island.party.x; gA.y = island.party.y; gA.state = 'chase';
gB.x = island.party.x; gB.y = island.party.y; gB.state = 'chase';
gC.x = island.party.x + 80; gC.y = island.party.y; gC.state = 'chase';
island._checkContact();
const dual = island.takeEvent().find((e) => e.type === 'battle');
check('dois grupos encostando entram na mesma luta em duas rodas',
  !!dual?.wave && dual.wave.length >= 1 && dual.source.refs.length === 2 && dual.foes.length >= 1);
island.busy = false;
gA.x = island.party.x; gA.y = island.party.y; gA.alive = true; gA.state = 'chase';
gB.x = island.party.x + 90; gB.y = island.party.y; gB.alive = true; gB.state = 'chase';
island._checkContact();
const single = island.takeEvent().find((e) => e.type === 'battle');
check('um grupo encosta e o outro continua perseguindo',
  !!single && !single.wave && gB.state === 'chase' && gB.alive);
island.resolveEncounter(single.source);
check('depois da primeira luta o segundo grupo segue no mapa',
  gB.alive && island.patrols.includes(gB));
island.busy = false;

const near = island.patrols.find((p) => p.alive && p !== gB) || island.patrols[0];
near.x = island.party.x + 40; near.y = island.party.y;
island.update(0.2);
check('inimigo a 6 blocos fica em alerta/persegue', near.state === 'chase');
near.x = island.party.x + 400; near.y = island.party.y + 400;
island.update(0.05);
check('sair do alcance deixa o grupo confuso', near.state === 'confused');
island.update(1.5);
check('depois da confusão a patrulha retoma', near.state === 'return' || near.state === 'patrol');

const smash = island.buildings[0];
island.interact({ type: 'building', obj: smash });
island.party.x = smash.x - 16; island.party.y = smash.y + 6;
island.party.target = null;
island.party.job = { type: 'smash', obj: smash };
island.update(0.6);
check('quebrar estrutura enfurece o chefe', island.bossEnraged === true);

const foes = raid.makePatrolMembers(1, () => 0.4, 4);
const btl = new Battle({
  allies: party, foes, kind: 'patrol', difficulty: 1,
  rewards: rw, instant: true, rng: () => 0,
});
check('batalha começa com 4×4', btl.allies.length === 4 && btl.foes.length === 4);
check('aliados ficam à esquerda', btl.allies.every((f) => f.x < 320));
check('inimigos ficam à direita', btl.foes.every((f) => f.x > 320));
check('turnos intercalam GA e GI',
  btl.queue[0] === btl.allies[0] && btl.queue[1] === btl.foes[0]
  && btl.queue[2] === btl.allies[1] && btl.queue[3] === btl.foes[1]);
btl.instant = false;
btl.allies[0].alive = false; btl.allies[0].hp = 0;
btl.current = btl.foes[3];
btl._nextTurn();
check('goblin morto ou ausente é pulado', btl.current === btl.foes[0]);
btl.allies[0].alive = true; btl.allies[0].hp = btl.allies[0].maxHp;
btl._rebuildQueue();
btl.instant = true;
btl.current = btl.allies[0];
btl.phase = 'ready';
check('escolhe o alvo antes da habilidade', btl.chooseTarget(0) === true && btl.target === btl.living('foe')[0]);
check('ataque sem alvo não dispara', (btl.target = null, btl.commandAttack() === false));
btl.chooseTarget(0);
check('habilidade usa o alvo na hora', btl.commandAttack() === true);
let turns = 80;
while (!btl.finished && turns--) {
  if (btl.phase === 'ready' && btl.current?.side === 'ally') {
    if (!btl.target?.alive) btl.chooseTarget(0);
    btl.commandAttack();
  }
  btl.update(1);
}
check('batalha termina', btl.finished === true, `fase=${btl.phase} left=${turns}`);
check('vitória dá as mesmas recompensas da destruição',
  btl.result === 'win' && btl.rewards.gold === rw.gold && btl.rewards.goblin_gems === rw.goblin_gems);

const waveFoes = raid.makePatrolMembers(1, () => 0.2, 4);
const btlW = new Battle({
  allies: party, foes, wave: waveFoes, kind: 'patrol', difficulty: 1,
  rewards: rw, instant: true, rng: () => 0,
});
check('luta com dois grupos guarda a segunda roda', btlW.pendingWave.length === 4);
btlW.foes.forEach((f) => { f.alive = false; f.hp = 0; });
btlW._checkEnd();
check('acabar a primeira roda traz o segundo grupo',
  btlW.finished === false && btlW.foes.every((f) => f.alive) && btlW.pendingWave.length === 0
  && btlW.log.some((l) => l.kind === 'wave'));
let waveTurns = 80;
while (!btlW.finished && waveTurns--) {
  if (btlW.phase === 'intro') btlW.wait = 0;
  if (btlW.phase === 'ready' && btlW.current?.side === 'ally') {
    if (!btlW.target?.alive) btlW.chooseTarget(0);
    btlW.commandAttack();
  }
  btlW.update(1);
}
check('as duas rodas terminam em vitória', btlW.finished === true && btlW.result === 'win',
  `fase=${btlW.phase} left=${waveTurns}`);

const gemV = new Village();
gemV.add('goblin_gems', 4);
check('gemas goblinéias entram no estoque sem função extra', gemV.res.goblin_gems === 4);

const gearBag = new Village();
gearBag.addItem('espada_ferro', 1);
gearBag.addItem('peitoral_ferro', 2);
check('armazém lista todos os itens guardados',
  inv.storedItems(gearBag).length === 2 && inv.storedItems(gearBag).some((i) => i.id === 'espada_ferro'));

// ============================================================
section('Resultado');
// ============================================================
console.log(`  ${pass} passaram · ${fail} falharam`);
if (fail) {
  console.log('\n\x1b[31mFalhas:\x1b[0m');
  for (const f of failures) console.log('  ✗ ' + f);
  process.exit(1);
}
console.log('\x1b[32m  tudo certo\x1b[0m');
