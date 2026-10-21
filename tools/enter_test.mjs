/**
 * enter_test.mjs — o goblin entra nas estruturas para trabalhar.
 *
 * Cobre o caminho do pão: sai para o armazém, entra nele, pega o trigo,
 * vai para a cozinha, entra e cozinha lá dentro (invisível). Ao terminar,
 * reaparece na porta.
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

let fails = 0;
function ok(cond, msg) {
  if (cond) console.log('  ✓ ' + msg);
  else { console.log('  ✗ ' + msg); fails++; }
}

const { GoblinWalker } = req('world.js');
const kitchen = { type: 'cozinha', x: 120, y: 60 };
const warehouse = { type: 'armazem', x: -120, y: 60 };
const meal = { status: 'cooking', workers: [0], worker: 0, working: false };
const walker = new GoblinWalker(-120, 60, { x: 0, y: 0, r: 40 });
walker.i = 0;
walker.speed = 30;   // passo por frame menor que o raio de chegada (3 px)
walker.job = { type: 'fetch-goto', cooking: meal, kitchen, warehouse };

let sawWarehouse = false, sawKitchen = false, sawOutside = false;
const api = { onCook: () => {} };
for (let t = 0; t < 30; t += 0.05) {
  walker.update(0.05, api);
  if (walker.inside === warehouse) sawWarehouse = true;
  if (walker.inside === kitchen) sawKitchen = true;
  if (!walker.inside) sawOutside = true;
  if (sawWarehouse && sawKitchen) break;
}
ok(sawWarehouse, 'entra no armazém para pegar o trigo');
ok(sawKitchen, 'depois entra na cozinha para cozinhar');
ok(sawOutside, 'fica visível no caminho entre os prédios');

// enquanto está dentro, não desenha nada
// canvas falso: o desenho do goblin pede um sprite, que criaria um canvas
globalThis.document = {
  createElement: () => ({
    width: 0, height: 0,
    getContext: () => new Proxy({}, {
      get: (t, k) => (k in t ? t[k] : (typeof k === 'string' && k.startsWith('create') ? () => ({ addColorStop() {} }) : () => {})),
      set: () => true,
    }),
  }),
};
let drawn = 0;
const stub = new Proxy({}, { get: () => () => { drawn++; } });
walker.inside = kitchen;
walker.draw(stub, 0);
ok(drawn === 0, 'não é desenhado enquanto está dentro');
walker.inside = null;
walker.draw(stub, 0);
ok(drawn > 0, 'volta a ser desenhado quando sai');

// ao terminar a receita, ele reaparece na porta
meal.status = 'done';
walker.job = { type: 'cook', cooking: meal, kitchen };
walker.update(0.05, api);
ok(walker.inside === null, 'ao terminar, sai da cozinha');
ok(!walker.job, 'libera o goblin depois de cozinhar');

console.log(`\n  ${fails === 0 ? 'ok' : fails} — entrando/saindo das estruturas`);
process.exit(fails === 0 ? 1 * 0 : 1);
