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

check('catálogo tem os equipamentos', inv.ITEMS.length === 14, `${inv.ITEMS.length} itens`);
check('todo item tem ícone e preço', inv.ITEMS.every((i) => i.icon && i.price > 0));
check('10 espaços no boneco', inv.EQUIP_SLOTS.length === 10);
check('espaços esperados',
  ['capacete', 'peitoral', 'botas', 'calca', 'anel1', 'anel2',
    'arma_primaria', 'arma_secundaria', 'runa', 'colar']
    .every((k) => inv.EQUIP_SLOTS.includes(k)));

const iv = new Village();
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
check('2 espaços por goblin', abilities.SKILL_SLOTS === 2);

const ag = Goblin.roll(0);
const specAb = abilities.ABILITIES.find((a) => a.spec === ag.specialty);
const otherAb = abilities.ABILITIES.find((a) => a.spec && a.spec !== ag.specialty);
const generic = abilities.byId('investida');
check('aceita habilidade da própria especialidade', abilities.canEquip(ag, specAb));
check('recusa habilidade de outra especialidade', !abilities.canEquip(ag, otherAb));
check('genérica serve p/ todos', abilities.canEquip(ag, generic));

check('equipa no espaço 0', abilities.equipAbility(ag, 0, specAb.id) === true);
check('equipa genérica no espaço 1', abilities.equipAbility(ag, 1, generic.id) === true);
check('re-equipar MOVE em vez de duplicar',
  abilities.equipAbility(ag, 1, specAb.id) === true
  && ag.skills.filter(Boolean).length === 1 && ag.skills[1] === specAb.id);
check('recusa classe errada', abilities.equipAbility(ag, 0, otherAb.id) === false);
check('remove habilidade', abilities.unequipAbility(ag, 1) === specAb.id);

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
