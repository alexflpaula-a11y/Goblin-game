/**
 * check_layout.mjs — Valida o LAYOUT das telas a partir do JSON do
 * render_preview.mjs: regiões dentro da tela, sem sobreposição
 * ambígua, e invariantes específicos (anel de espaços, grade etc.).
 *
 * Uso:  node tools/check_layout.mjs armazem equip market
 */
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const ROOT = path.dirname(path.dirname(fileURLToPath(import.meta.url)));
const [,, ...names] = process.argv;
const W = 640, H = 360;

let fails = 0, passes = 0;
const ok = (cond, msg) => { console.log((cond ? '  ✓ ' : '  ✗ ') + msg); cond ? passes++ : fails++; };

const overlap = (a, b) => Math.max(0, Math.min(a.x + a.w, b.x + b.w) - Math.max(a.x, b.x))
  * Math.max(0, Math.min(a.y + a.h, b.y + b.h) - Math.max(a.y, b.y));

for (const name of names) {
  const p = path.join(ROOT, 'tools/preview', name + '.json');
  if (!fs.existsSync(p)) { console.log(`  !! ${name}: sem JSON (rode o render_preview)`); fails++; continue; }
  const { regions } = JSON.parse(fs.readFileSync(p, 'utf8'));
  console.log(`\n[${name}] ${regions.length} regiões clicáveis`);

  // 1. dentro da tela lógica
  const out = regions.filter((r) => r.x < 0 || r.y < 0 || r.x + r.w > W || r.y + r.h > H);
  ok(out.length === 0, 'todas as regiões dentro da tela',
    out.map((r) => `${r.id}@${r.x},${r.y}`).join(' '));

  // 2. sobreposições (regiões diferentes brigando pelo mesmo toque)
  const clashes = [];
  for (let i = 0; i < regions.length; i++) {
    for (let j = i + 1; j < regions.length; j++) {
      const a = regions[i], b = regions[j];
      if (a.id === b.id) continue;                 // mesma ação (células duplicadas)
      const ov = overlap(a, b);
      if (ov > 0) clashes.push(`${a.id} × ${b.id} (${ov}px²)`);
    }
  }
  ok(clashes.length === 0, 'nenhuma região sobrepõe outra', clashes.slice(0, 6).join(' | '));

  // 3. invariantes por tela
  if (name === 'equip') {
    const slots = regions.filter((r) => r.id.startsWith('slot_'));
    ok(slots.length === 10, 'anel de equipamento completo (10 espaços)',
      slots.map((s) => s.id.slice(5)).join(','));
    const goblin = { x: 214, y: 152, w: 72, h: 72 };   // sprite do goblin no centro
    const onGoblin = slots.filter((s) => overlap(s, goblin) > 0);
    ok(onGoblin.length === 0, 'nenhum espaço cobre o goblin', onGoblin.map((s) => s.id).join(','));
    const panel = { x: 402, y: 100, w: 214, h: 226 };  // painel direito
    const onPanel = slots.filter((s) => overlap(s, panel) > 0);
    ok(onPanel.length === 0, 'nenhum espaço invade o painel de itens',
      onPanel.map((s) => s.id).join(','));
    const tabs = regions.filter((r) => /^eqtab_[012]$/.test(r.id));
    ok(tabs.length === 3, '3 abas presentes (equip./alimentos/hab.)');
    const nav = regions.filter((r) => r.id === 'eq_prev' || r.id === 'eq_next');
    ok(nav.length === 0 || nav.length === 2, 'navegação ‹ › presente (0 com 1 goblin)');
  }
  if (name === 'armazem') {
    const cells = regions.filter((r) => r.id.startsWith('invs_'));
    ok(cells.length >= 4, 'grade tem células clicáveis (itens da prévia)',
      `${cells.length} células`);
    ok(regions.some((r) => r.id === 'inv_upgrade'), 'botão de melhorar presente');
    ok(regions.some((r) => r.id === 'inv_equip'), 'botão de equipar goblins presente');
    const up = regions.find((r) => r.id === 'inv_upgrade');
    const eq = regions.find((r) => r.id === 'inv_equip');
    ok(!up || !eq || overlap(up, eq) === 0, 'melhorar e equipar não se sobrepõem');
  }
  if (name === 'market') {
    const gearCards = regions.filter((r) => r.id.startsWith('mdo_gear:'));
    ok(gearCards.length > 0, 'equipamento na prateleira (comprar/vender)', `${gearCards.length} botões`);
    const qty = regions.filter((r) => /^mq_[+-]_gear:/.test(r.id));
    ok(qty.length > 0, 'seletor de quantidade funciona p/ equipamento', `${qty.length} botões ±`);
  }
}

console.log(`\n  ${passes} passaram · ${fails} falharam`);
process.exit(fails ? 1 : 0);
