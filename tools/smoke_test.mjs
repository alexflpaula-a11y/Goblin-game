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
const { Goblin, ATTRS, SPECS, RARITIES } = req('goblin.js');

const g = Goblin.roll(0);
check('goblin tem nome', typeof g.name === 'string' && g.name.length > 0);
check('goblin tem especialidade válida', SPECS.includes(g.specialty), g.specialty);
check('goblin tem raridade válida', RARITIES.includes(g.rarity), g.rarity);
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

// sorte crescente: com muitos recrutas, raridade média deve subir
const rarityScore = (r) => RARITIES.indexOf(r);
const avg = (n) => {
  let s = 0;
  for (let i = 0; i < 4000; i++) s += rarityScore(Goblin.rollRarity(n));
  return s / 4000;
};
const low = avg(0), high = avg(100);
check('sorte crescente aumenta raridade', high > low, `0 recrutas=${low.toFixed(3)} · 100=${high.toFixed(3)}`);

// ============================================================
section('Village — recursos, construção, habitação');
// ============================================================
const { Village } = req('village.js');
const v = new Village();

check('recursos iniciais do balance', v.res.wood === BALANCE.startResources.wood);
check('começa com 3 estruturas', v.structures.length === 3, String(v.structures.length));
check('começa com 1 casa', v.houses.length === 1);
check('começa com 1 goblin', v.goblins.length === 1);
check('capacidade = soma dos níveis das casas', v.capacity === 1);

const woodBefore = v.res.wood;
const built = v.buildHouse();
check('constrói casa com recursos', built === true);
check('pagou o custo em madeira', v.res.wood === woodBefore - BALANCE.house.buildCost.wood);
check('capacidade subiu p/ 2', v.capacity === 2);

v.res.wood = 0; v.res.stone = 0;
check('bloqueia construção sem recursos', v.buildHouse() === false);

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
let guard = 0;
while (v2.goblins.length < v2.capacity && guard++ < 50) v2.recruit(Goblin.roll(0));
check('não recruta acima da capacidade', v2.recruit(Goblin.roll(0)) === false);

// serialização
const round = new Village(JSON.parse(JSON.stringify(v.serialize())));
check('serialize/restore preserva recursos', round.res.wood === v.res.wood);
check('serialize/restore preserva casas', round.houses.length === v.houses.length);
check('serialize/restore reconstrói Goblins', round.goblins[0] instanceof Goblin);

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
v5.res = { wood: 9999, stone: 9999, ore: 9999, food: 9999, gold: 9999 };
v5.level = 1;
check('teto de melhoria = nível da vila', v5.maxUpgradeLevel('house') === 1);
check('não melhora além do nível da vila', v5.upgrade(v5.houses[0]) === false);
v5.level = 3;
check('teto sobe junto com a vila', v5.maxUpgradeLevel('house') === 3);
check('agora melhora', v5.upgrade(v5.houses[0]) === true);

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
section('Resultado');
// ============================================================
console.log(`  ${pass} passaram · ${fail} falharam`);
if (fail) {
  console.log('\n\x1b[31mFalhas:\x1b[0m');
  for (const f of failures) console.log('  ✗ ' + f);
  process.exit(1);
}
console.log('\x1b[32m  tudo certo\x1b[0m');
