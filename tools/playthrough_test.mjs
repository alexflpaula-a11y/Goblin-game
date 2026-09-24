/**
 * playthrough_test.mjs — Simula uma PARTIDA de verdade.
 *
 * Os outros testes olham peça por peça. Este joga o ciclo completo do
 * planejamento (§2.1) e confere que ele fecha:
 *
 *   coletar → construir → missões → XP da vila → subir de nível
 *   → desbloquear estruturas → fazenda → cozinha → curar goblin
 *
 * É o teste que pega "o jogo trava no meio" — o problema que existia
 * antes, quando o nível da vila era fixo em 1.
 *
 * Uso:  node tools/playthrough_test.mjs
 */
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const ROOT = path.dirname(path.dirname(fileURLToPath(import.meta.url)));

const modules = {};
const cache = {};
const order = JSON.parse(fs.readFileSync(path.join(ROOT, 'js/_order.json'), 'utf8'));
for (const name of order) {
  if (name === 'main.js') continue;   // aqui não precisamos do loop/DOM
  modules[name] = new Function('module', 'exports', 'require',
    fs.readFileSync(path.join(ROOT, 'js', name), 'utf8'));
}
function req(name) {
  if (!cache[name]) {
    const m = { exports: {} };
    cache[name] = m;
    modules[name](m, m.exports, req);
  }
  return cache[name].exports;
}

globalThis.window = { EMBEDDED: null };
globalThis.document = {
  createElement: () => ({
    width: 0, height: 0,
    getContext: () => new Proxy({}, { get: () => () => {} }),
  }),
};

const { BAL } = req('balance.js');
Object.assign(BAL, JSON.parse(fs.readFileSync(path.join(ROOT, 'assets/data/balance.json'), 'utf8')));

const { Village } = req('village.js');
const { Quests } = req('quests.js');
const cooking = req('cooking.js');
const market = req('market.js');
const gear = req('gear.js');
const inv = req('inventory.js');
const abilities = req('abilities.js');

let pass = 0, fail = 0;
const failures = [];
function check(label, cond, extra = '') {
  if (cond) { pass++; console.log(`  \x1b[32m✓\x1b[0m ${label}${extra ? ' — ' + extra : ''}`); return; }
  fail++;
  failures.push(`${label}${extra ? ' — ' + extra : ''}`);
  console.log(`  \x1b[31m✗\x1b[0m ${label}${extra ? ' — ' + extra : ''}`);
}

console.log('\x1b[1mPartida simulada — o ciclo do jogo fecha?\x1b[0m\n');

const v = new Village();
const q = new Quests();
q.ensure(v.level);

console.log(`  início: vila nv${v.level} · ${v.goblins.length} goblin · ` +
  `${v.res.wood} madeira, ${v.res.stone} pedra, ${v.res.gold} ouro`);

// ---------- 1. o jogador começa travado? ----------
check('no começo só dá para construir casa',
  v.canBuild('house') && !v.canBuild('serraria'));

// ---------- 2. coletar recursos (trabalho nos nós) ----------
// Simula o que handleChop faz: cada ciclo rende 1 recurso.
for (let i = 0; i < 120; i++) v.add('wood', 1);
for (let i = 0; i < 90; i++) v.add('stone', 1);
check('coleta acumula recursos', v.res.wood > 150, `${v.res.wood} madeira`);

// ---------- 3. construir casas e recrutar ----------
const { Goblin } = req('goblin.js');
let built = 0;
while (v.canBuild('house') && built < 3) {
  v.build('house');
  built += 1;
  if (v.goblins.length < v.capacity) v.recruit(Goblin.roll(v.recruitedCount));
}
check('construiu casas novas', built === 3, `${built} casas`);
check('recrutou goblins', v.goblins.length > 1, `${v.goblins.length} goblins`);

// ---------- 4. missões dão XP até a vila subir ----------
const lvBefore = v.level;
let delivered = 0;
for (let tick = 0; tick < 400 && v.level < 3; tick++) {
  for (const quest of [...q.list]) {
    if (!quest.canDeliver(v)) {
      // o jogador vai buscar o que falta (simula o trabalho dos goblins)
      const falta = quest.qty - quest.have(v);
      if (quest.kind === 'res' && falta > 0) v.add(quest.key, falta);
      else continue;
    }
    if (q.deliver(quest, v)) delivered += 1;
  }
  q.update(BAL.quests.renewSeconds + 1, v.level);
}
check('entregou missões', delivered > 0, `${delivered} entregas`);
check('missões fizeram a vila subir de nível', v.level > lvBefore,
  `nv${lvBefore} → nv${v.level}`);

// ---------- 5. subir de nível desbloqueou estruturas ----------
// O que importa aqui é o PORTÃO DE NÍVEL ter caído. Se falta recurso,
// o motivo vira 'cost' — e isso é o jogo funcionando, não um bug.
const gate = v.blockedReason('serraria');
check('nível 2 destravou a serraria (sem trava de nível)',
  v.level >= 2 && gate?.reason !== 'level',
  gate ? `motivo: ${gate.reason}` : 'liberada');

v.res = { wood: 9999, stone: 9999, ore: 9999, food: 0, gold: 9999 };
check('com recursos, a serraria pode ser construída', v.canBuild('serraria'));
check('constrói a serraria', v.build('serraria') !== null);
check('constrói a fazenda', v.build('fazenda') !== null);

// ---------- 6. fazenda alimenta a cozinha ----------
// A fazenda vira um posto de trabalho infinito que produz comida.
const { Nodes } = req('nodes.js');
const fakeWorld = {
  clearing: { x: 960, y: 726, r: 160 },
  tiles: new Uint8Array(120 * 90).fill(3),
};
const nodes = new Nodes(fakeWorld, []);
nodes.syncFacilities(v);
const farmNode = nodes.list.find((n) => n.type === 'farm');
check('fazenda criou posto de trabalho', !!farmNode);
check('posto da fazenda é infinito', farmNode?.infinite === true);

// goblins trabalham na fazenda
for (let i = 0; i < 40; i++) v.add('food', 1);
check('fazenda produz comida', v.res.food >= 40, `${v.res.food} comida`);

// ---------- 7. cozinha: precisa de nível 3 ----------
while (v.level < 3) v.gainXp(v.xpNext());
check('vila chegou ao nível 3', v.level >= 3);
check('cozinha liberada no nível 3', v.canBuild('cozinha'));
check('constrói a cozinha', v.build('cozinha') !== null);

const cooked = cooking.cook(v, 'bread');
check('cozinha produz comida curativa', cooked !== null, `${cooked?.qty}x pão`);

// ---------- 8. comida cura goblin ferido ----------
const g = v.goblins[0];
g.hp = 1;
const healed = cooking.feed(v, g, 'bread');
check('prato cura o goblin', healed > 0, `+${healed} HP`);

// ---------- 9. melhorar estrutura respeita o nível da vila ----------
const kitchen = v.get('cozinha');
v.res = { wood: 9999, stone: 9999, ore: 9999, food: 9999, gold: 9999 };
check('melhora a cozinha (vila nv3 permite nv3)', v.upgrade(kitchen) === true);
check('cozinha agora é nível 2', kitchen.level === 2);
check('receita melhor desbloqueada pela melhoria',
  cooking.available(kitchen.level).some((r) => r.id === 'stew'));

// ---------- 9.5. mercado: o excedente vira ouro e o que falta se compra ----------
// O Mercado abre junto com a Cozinha (vila nv3) e fecha a economia da Fase 1.
check('mercado liberado no nível 3', v.canBuild('mercado'));
check('constrói o mercado', v.build('mercado') !== null);

v.res = { wood: 300, stone: 100, ore: 0, food: 10, gold: 0 };
const ganho = market.sell(v, 'res', 'wood', 200);
check('vende o excedente de madeira', ganho > 0, `+${ganho} ouro`);
check('ouro entrou no caixa', v.res.gold === ganho);
check('madeira desceu para o que sobrou', v.res.wood === 100, `${v.res.wood}`);

// com o ouro na mão, compra o minério que os goblins ainda não mineraram
const podeComprar = market.maxBuy(v, 'res', 'ore');
check('dá para comprar minério com o ouro da venda', podeComprar > 0, `${podeComprar} un`);
const gasto = market.buy(v, 'res', 'ore', Math.min(3, podeComprar));
check('compra minério', gasto > 0 && v.res.ore > 0, `${v.res.ore} minério por ${gasto} ouro`);
check('o mercado não imprime dinheiro (compra > venda)',
  market.buyPrice(v, 'res', 'ore') > market.sellPrice(v, 'res', 'ore'));

// o ensopado precisa de minério: a compra destravou a receita na prática
v.res.food = 99;
const ensopado = cooking.cook(v, 'stew');
check('minério comprado alimenta a receita melhor', ensopado !== null);

// ---------- 9.6. armazém: inventário + equipar goblin ----------
check('armazém liberado no nível 2', v.canBuild('armazem'));
v.res = { wood: 999, stone: 999, ore: 99, food: 99, gold: v.res.gold };
check('constrói o armazém', v.build('armazem') !== null);
check('armazém nv1 dá 16 espaços de item', v.itemCapacity() === 16);

v.res.gold = 1000;
check('compra espada no mercado', market.buy(v, 'gear', 'espada_ferro', 1) > 0);
check('compra capacete no mercado', market.buy(v, 'gear', 'capacete_ferro', 1) > 0);
check('itens estão no inventário', v.itemsCount() === 2);

const lutador = v.goblins[0];
check('equipa espada no goblin', inv.equip(v, lutador, 'arma_primaria', 'espada_ferro'));
check('equipa capacete no goblin', inv.equip(v, lutador, 'capacete', 'capacete_ferro'));
check('itens saíram do armazém', v.itemsCount() === 0);
check('goblin veste 2 peças', inv.equippedCount(lutador) === 2);
check('capacete de ferro não tem skin própria (sprite base)',
  gear.spriteForGoblin(lutador, 'idle', 0) === 'goblin_idle_0');
check('outro goblin segue sem nada',
  gear.spriteForGoblin(v.goblins[1], 'idle', 0) === 'goblin_idle_0');

check('aprimora o armazém p/ mais espaços', v.upgrade(v.get('armazem')) === true);
check('armazém nv2 → 24 espaços', v.itemCapacity() === 24);

const habilidoso = v.goblins[1];
const abGenerica = abilities.byId('investida');
check('habilidade genérica serve p/ qualquer goblin', abilities.canEquip(habilidoso, abGenerica));
check('goblin aprende habilidade', abilities.equipAbility(habilidoso, 0, 'investida'));

// ---------- 10. o save aguenta tudo isso ----------
const snapshot = JSON.parse(JSON.stringify({ village: v.serialize(), quests: q.serialize() }));
const v2 = new Village(snapshot.village);
const q2 = new Quests(snapshot.quests);
check('save preserva o nível da vila', v2.level === v.level);
check('save preserva as estruturas', v2.has('cozinha') && v2.has('fazenda') && v2.has('mercado'));
check('save preserva os goblins', v2.goblins.length === v.goblins.length);
check('save preserva as missões', q2.list.length === q.list.length);
check('save preserva o armazém', v2.has('armazem') && v2.itemCapacity() === v.itemCapacity());
check('save preserva o equipamento do goblin',
  v2.goblins[0].equip?.arma_primaria === 'espada_ferro');
check('save preserva a habilidade do goblin', v2.goblins[1].skills?.[0] === 'investida');

console.log(`\n  vila nv${v.level} · ${v.goblins.length} goblins · ` +
  `${v.structures.length} estruturas · ${q.completed} missões concluídas`);
console.log(`\n  ${pass} passaram · ${fail} falharam`);
if (fail) {
  console.log('\n\x1b[31mFalhas:\x1b[0m');
  for (const f of failures) console.log('  ✗ ' + f);
  process.exit(1);
}
console.log('\x1b[32m  o ciclo do jogo fecha do início ao fim\x1b[0m');
