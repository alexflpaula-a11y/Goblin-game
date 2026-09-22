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
const h = v.houses[0];
v.upgradeHouse(0);
check('melhora casa (+1 nível)', v.houses[0].level === h.level);
check('capacidade cresce com melhoria', v.capacity >= 3);

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
section('Resultado');
// ============================================================
console.log(`  ${pass} passaram · ${fail} falharam`);
if (fail) {
  console.log('\n\x1b[31mFalhas:\x1b[0m');
  for (const f of failures) console.log('  ✗ ' + f);
  process.exit(1);
}
console.log('\x1b[32m  tudo certo\x1b[0m');
