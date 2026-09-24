/**
 * gear_test.mjs — Loja de armaduras Avaritia (Mercado, etapa "loja").
 *
 * Exercita o ciclo completo: prateleira, preços, compra única,
 * troca de sprite por combinação de peças e persistência no save.
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
const { Village } = req('village.js');
const { Goblin } = req('goblin.js');
const bal = req('balance.js');
// popula BAL como o jogo faz (window.EMBEDDED.balance)
Object.assign(bal.BAL, JSON.parse(fs.readFileSync(path.join(ROOT, 'assets/data/balance.json'), 'utf8')));

let fails = 0, passes = 0;
const ok = (cond, msg) => { console.log((cond ? '  ✓ ' : '  ✗ ') + msg); if (!cond) fails++; else passes++; };

console.log('LOJA AVARITIA — fluxo completo');
const v = new Village(null);
// mercado construído direto (custo/level irrelevantes p/ o teste)
v.structures.push({ type: 'mercado', level: 1, x: 500, y: 500 });
v.res.wood = 999; v.res.stone = 999;
v.res.gold = 500;

const cat = market.catalog(v, 'buy');
const gears = cat.filter(i => i.kind === 'gear');
ok(gears.length === 3, 'prateleira de COMPRA tem as 3 peças');
ok(market.catalog(v, 'sell').filter(i => i.kind === 'gear').length === 0, 'armaduras NÃO aparecem na venda');
ok(!gears.some(i => i.price <= 0), 'preços ok: ' + gears.map(g => g.key.split('_')[0] + '=' + g.price).join(' '));

// sem armadura -> sprite base
ok(gear.spriteFor('idle', 0) === 'goblin_idle_0', 'sem peças: sprite base');

// compra o peitoral (120)
const c1 = market.buy(v, 'gear', 'peitoral_avaritia', 1);
ok(c1 === 120 && v.res.gold === 380, 'compra peitoral: -120 ouro (restam 380)');
ok(gear.spriteFor('idle', 3) === 'av_pei_idle_3', 'sprite muda p/ av_pei');
ok(market.buy(v, 'gear', 'peitoral_avaritia', 1) === 0, 'peitoral é compra única (2ª tenta falha)');

// compra calça (90) -> par
market.buy(v, 'gear', 'calca_avaritia', 1);
ok(gear.spriteFor('walk', 2) === 'av_pei_cal_walk_2', 'peitoral+calça -> av_pei_cal');

// compra capacete (150) -> conjunto
market.buy(v, 'gear', 'capacete_avaritia', 1);
ok(gear.spriteFor('death', 7) === 'av_full_death_7', 'conjunto completo -> av_full');
ok(v.res.gold === 500 - 120 - 90 - 150, 'ouro total gasto: 360 (restam 140)');

// sem ouro não compra (já tem tudo — testa com item novo simulado)
v.gear = {}; gear.setOwned(v.gear); v.res.gold = 10;
ok(market.buy(v, 'gear', 'peitoral_avaritia', 1) === 0, 'sem ouro: compra falha');
ok(gear.spriteFor('idle', 0) === 'goblin_idle_0', 'nada comprado -> sprite base');

// persistência: serialize/load
v.res.gold = 200;
market.buy(v, 'gear', 'capacete_avaritia', 1);
const s = v.serialize();
ok(s.gear?.capacete_avaritia === true, 'serialize guarda gear');
const v2 = new Village(JSON.parse(JSON.stringify(s)));
gear.setOwned(v2.gear);
ok(gear.spriteFor('idle', 0) === 'av_cap_idle_0', 'save/load: capacete persiste');

// todos os 62 frames de cada versão existem no manifest
const man = JSON.parse(fs.readFileSync(path.join(ROOT, 'assets/manifest.json'), 'utf8'));
const ids = new Set(man.sprites.map(s => s.id));
const ANIMS = { idle: 5, walk: 8, attack: 17, hurt: 17, death: 15 };
let miss = 0;
for (const ver of ['av_pei','av_cal','av_cap','av_cap_pei','av_cap_cal','av_pei_cal','av_full'])
  for (const [a, n] of Object.entries(ANIMS))
    for (let i = 0; i < n; i++) if (!ids.has(`${ver}_${a}_${i}`)) miss++;
ok(miss === 0, 'manifest: 434 frames das 7 versões presentes');

console.log(`\n  ${passes} passaram · ${fails} falharam`);
process.exit(fails ? 1 : 0);
