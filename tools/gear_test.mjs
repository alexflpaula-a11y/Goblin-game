/**
 * gear_test.mjs — Equipamentos, Armazém e inventário.
 *
 * Exercita o ciclo completo da nova era dos itens:
 *   • prateleira do Mercado exige Armazém construído
 *   • compra em quantidade, limitada pelos espaços do Armazém
 *   • revenda de equipamento
 *   • equipar/desequipar por goblin (itens migram armazém ↔ corpo)
 *   • sprite de cada goblin conforme o que ELE vestiu
 *     (combos avaritia + peitoral de ferro sozinho)
 *   • migração de saves antigos (gear de compra única → itens)
 *   • persistência no save
 *
 * Uso:  node tools/gear_test.mjs
 */
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const ROOT = path.dirname(path.dirname(fileURLToPath(import.meta.url)));
const modules = {}, cache = {};
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

const market = req('market.js');
const gear = req('gear.js');
const inv = req('inventory.js');
const abilities = req('abilities.js');
const { Village } = req('village.js');
const { Goblin } = req('goblin.js');
const bal = req('balance.js');
Object.assign(bal.BAL, JSON.parse(fs.readFileSync(path.join(ROOT, 'assets/data/balance.json'), 'utf8')));

let fails = 0, passes = 0;
const ok = (cond, msg) => { console.log((cond ? '  ✓ ' : '  ✗ ') + msg); if (!cond) fails++; else passes++; };

console.log('ARMAZÉM & INVENTÁRIO — equipamentos');
const v = new Village(null);
// mercado + armazém construídos direto (custo/level irrelevantes p/ o teste)
v.structures.push({ type: 'mercado', level: 1, x: 500, y: 500 });
// um segundo goblin p/ provar que o equipamento é individual
v.goblins.push(new Goblin({ name: 'Zug', specialty: 'mage', raridade: 'common' }));
v.res.wood = 999; v.res.stone = 999;
v.res.gold = 2000;

// ---------- prateleira exige armazém ----------
let cat = market.catalog(v, 'buy');
ok(cat.filter(i => i.kind === 'gear').length === 0, 'sem Armazém: prateleira sem equipamentos');
cat = market.catalog(v, 'sell');
ok(cat.filter(i => i.kind === 'gear').length === 0, 'sem Armazém: nada de equipamento na venda');

v.structures.push({ type: 'armazem', level: 1, x: 520, y: 520 });
cat = market.catalog(v, 'buy');
const gears = cat.filter(i => i.kind === 'gear');
ok(gears.length === inv.ITEMS.length, `com Armazém: ${inv.ITEMS.length} equipamentos à venda`);
ok(market.catalog(v, 'sell').some(i => i.kind === 'gear'), 'equipamentos agora podem ser revendidos');
ok(!gears.some(i => i.price <= 0), 'todos com preço ok');
ok(inv.EQUIP_SLOTS.length === 10, 'boneco tem 10 espaços de equipamento');
ok(inv.SLOT_TYPES.includes('anel'), "anel é um tipo (serve nos dois dedos)");

// ---------- compra em quantidade + capacidade ----------
ok(v.itemCapacity() === 16, 'Armazém nv1 → 16 espaços');
const pEspada = market.buyPrice(v, 'gear', 'espada_ferro');
ok(market.buy(v, 'gear', 'espada_ferro', 2) === pEspada * 2, 'compra 2 espadas (multi-compra)');
ok(v.items.espada_ferro === 2, 'as 2 espadas estão no inventário');
ok(v.itemsCount() === 2, '2 espaços ocupados');

v.res.gold = 100000;
// lota o armazém: 16 espaços, 2 usados → cabem 14 anéis de cobre
const comprou = market.buy(v, 'gear', 'anel_cobre', 15);
ok(comprou === 0, 'compra além da capacidade falha');
ok(market.maxBuy(v, 'gear', 'anel_cobre') === 14, 'maxBuy respeita os espaços livres');
ok(market.buy(v, 'gear', 'anel_cobre', 14) > 0, 'lota o armazém com 14 anéis');
ok(v.itemsCount() === v.itemCapacity(), 'armazém cheio: 16/16');
ok(market.maxBuy(v, 'gear', 'espada_ferro') === 0, 'cheio: maxBuy 0');

// ---------- revenda ----------
const ouroAntes = v.res.gold;
const vendeu = market.sell(v, 'gear', 'anel_cobre', 4);
ok(vendeu > 0, 'revende 4 anéis de cobre');
ok(v.items.anel_cobre === 10, 'anéis saíram do armazém');
ok(v.res.gold === ouroAntes + vendeu, 'ouro da revenda entrou');

// ---------- equipar por goblin ----------
const g0 = v.goblins[0];
const g1 = v.goblins[1];
v.items = { espada_ferro: 1 };   // só UMA espada: ela vai pro corpo de g0
ok(inv.equip(v, g0, 'arma_primaria', 'espada_ferro'), 'g0 equipa espada');
ok(g0.equip.arma_primaria === 'espada_ferro', 'espada no espaço de arma primária');
ok(v.items.espada_ferro === undefined, 'espada saiu do armazém');
ok(inv.equip(v, g0, 'capacete', 'espada_ferro') === false, 'espaço errado recusa o item');
ok(inv.equip(v, g0, 'arma_primaria', 'clava_goblin') === false, 'item não comprado não equipa');
ok(inv.equip(v, g1, 'arma_primaria', 'espada_ferro') === false,
  'item no CORPO de g0 não equipa em g1');

// troca direta: a antiga volta pro armazém quando outra entra
v.addItem('espada_ferro', 1);
ok(inv.equip(v, g0, 'arma_primaria', 'espada_ferro'), 'troca a espada por outra espada');
ok(v.items.espada_ferro === 1, 'a antiga voltou ao armazém (troca direta)');

// anel serve nos dois dedos
v.addItem('anel_cobre', 2);
ok(inv.equip(v, g0, 'anel1', 'anel_cobre') && inv.equip(v, g0, 'anel2', 'anel_cobre'),
  'um anel em cada dedo');
ok(g0.equip.anel1 === 'anel_cobre' && g0.equip.anel2 === 'anel_cobre', 'anel I e anel II ocupados');

// ---------- sprites por goblin ----------
ok(gear.spriteForGoblin(g0, 'idle', 0) === 'goblin_idle_0',
  'sem peças com skin: sprite base (espada não muda sprite)');
v.addItem('peitoral_ferro', 1);
ok(inv.equip(v, g0, 'peitoral', 'peitoral_ferro'), 'g0 veste peitoral de ferro');
ok(gear.spriteForGoblin(g0, 'attack', 5) === 'ferro_pei_attack_5', 'peitoral de ferro sozinho → skin ferro_pei');
ok(gear.spriteForGoblin(g1, 'idle', 0) === 'goblin_idle_0', 'g1 continua de sprite base');

v.res.gold = 100000;
v.items = {};   // esvazia p/ caber o conjunto
market.buy(v, 'gear', 'peitoral_avaritia', 1);
market.buy(v, 'gear', 'capacete_avaritia', 1);
market.buy(v, 'gear', 'calca_avaritia', 1);
ok(inv.equip(v, g1, 'peitoral', 'peitoral_avaritia'), 'g1 veste peitoral avaritia');
ok(gear.spriteForGoblin(g1, 'walk', 3) === 'av_pei_walk_3', 'avaritia: av_pei');
inv.equip(v, g1, 'capacete', 'capacete_avaritia');
inv.equip(v, g1, 'calca', 'calca_avaritia');
ok(gear.spriteForGoblin(g1, 'death', 7) === 'av_full_death_7', 'conjunto completo → av_full');
ok(gear.spriteForGoblin(g1, 'idle', 2) === 'av_full_idle_2', 'g1 em idle com conjunto');

// ferro + avaritia: avaritia vence (não há skin mista)
v.addItem('peitoral_ferro', 1);
inv.equip(v, g1, 'peitoral', 'peitoral_ferro');
ok(gear.spriteForGoblin(g1, 'idle', 0) === 'av_cap_cal_idle_0',
  'mistura: avaritia vence sobre ferro');

// ---------- desequipar ----------
const volta = inv.unequip(v, g0, 'arma_primaria');
ok(volta === 'espada_ferro', 'desequipar devolve o item');
ok(v.items.espada_ferro === 1, 'item de volta ao armazém (o do corpo; o do estoque foi zerado)');
ok(!g0.equip.arma_primaria, 'espaço de arma vazio agora');

// ---------- habilidades ----------
ok(abilities.SKILL_SLOTS === 2, '2 espaços de habilidade por goblin');
const warrior = new Goblin({ name: 'Thrak', specialty: 'warrior' });
const mage = new Goblin({ name: 'Zuggut', specialty: 'mage' });
ok(abilities.canEquip(warrior, abilities.byId('golpe_brutal')), 'guerreiro usa Golpe Brutal');
ok(!abilities.canEquip(mage, abilities.byId('golpe_brutal')), 'mago NÃO usa Golpe Brutal');
ok(abilities.canEquip(mage, abilities.byId('investida')), 'genérica (investida) serve p/ todos');
ok(abilities.equipAbility(warrior, 0, 'golpe_brutal'), 'equipa no espaço 0');
ok(abilities.equipAbility(warrior, 1, 'investida'), 'equipa genérica no espaço 1');
ok(abilities.equipAbility(warrior, 0, 'bola_fogo') === false, 'habilidade de outra classe recusada');
ok(abilities.hasAbility(warrior, 'investida'), 'guerreiro sabe investida');
// re-equipar move de espaço em vez de duplicar
abilities.equipAbility(warrior, 1, 'golpe_brutal');
ok(warrior.skills.filter(Boolean).length === 1, 'mover não duplica a habilidade');
ok(abilities.unequipAbility(warrior, 1) === 'golpe_brutal', 'remove do espaço');
// g0 da vila aprende algo (p/ testar persistência)
ok(abilities.equipAbility(g0, 0, 'investida'), 'g0 aprende genérica');

// ---------- migração de save antigo ----------
const velho = new Village({ gear: { peitoral_avaritia: true, capacete_avaritia: true } });
ok(velho.items.peitoral_avaritia === 1 && velho.items.capacete_avaritia === 1,
  'save antigo: peças únicas viram itens do inventário');
ok(!velho.gear, 'campo antigo gear não é mais usado');

// ---------- persistência ----------
const snap = JSON.parse(JSON.stringify(v.serialize()));
const v2 = new Village(snap);
ok(v2.itemsCount() === v.itemsCount(), 'itens persistem no save');
ok(v2.goblins[0].equip?.capacete === v.goblins[0].equip?.capacete, 'equipamento do goblin persiste');
ok(JSON.stringify(v2.goblins[0].skills || []) === JSON.stringify(v.goblins[0].skills || []),
  'habilidades persistem');

console.log(`\n  ${passes} passaram · ${fails} falharam`);
if (fails) {
  console.log('\n\x1b[31mFalhas:\x1b[0m (veja ✗ acima)');
  process.exit(1);
}
console.log('\n\x1b[32m  tudo certo\x1b[0m');
process.exit(0);
