// Cave treasure: one immutable loot roll, one grant, skippable presentation.
const { getSprite } = require('assetLoader.js');
class Treasure {
  constructor(battle) {
    this.boss = battle.kind === 'lair';
    this.origin = battle.lastDefeated || { x: 500, y: 240 };
    this.time = 0;
    this.opened = false;
    this.claimed = false;
    const amounts = battle.repeat ? {} : this.boss
      ? { wood: 30, stone: 25, ore: 12, food: 15 }
      : { wood: 8, stone: 6, food: 4 };
    this.loot = Object.entries({ ...amounts, ...battle.rewards })
      .filter(([, amount]) => amount > 0)
      .map(([id, amount]) => ({ id, amount, icon: 'res_' + id, item: false }));
    if (this.boss && !battle.repeat) this.loot.push({ id: 'manoplas_lobo', amount: 1, icon: 'item_manoplas_lobo', item: true });
  }
  claim(village) {
    if (this.claimed) return false;
    this.claimed = true;
    for (const r of this.loot) {
      if (r.item) village.addItem(r.id, r.amount);
      else village.add(r.id, r.amount);
    }
    return true;
  }
  update(dt) { this.time += dt; }
  position() {
    const t = Math.min(1, this.time / 0.85);
    const k = 1 - (1 - t) ** 3;
    return { x: this.origin.x + (320 - this.origin.x) * k,
      y: this.origin.y + (180 - this.origin.y) * k - Math.sin(t * Math.PI) * 32 };
  }
  tap(x, y) {
    const p = this.position();
    if (!this.opened && Math.abs(x - p.x) <= 90 && Math.abs(y - p.y) <= 78) {
      this.opened = true;
      return 'open';
    }
    return 'skip';
  }
}
function drawTreasure(ctx, ui, treasure, i18n, time) {
  const t = treasure;
  if (!t.opened) {
    const p = t.position();
    const pulse = 0.8 + Math.sin(time * 4) * 0.12;
    const glow = ctx.createRadialGradient(p.x, p.y, 10, p.x, p.y, 136);
    glow.addColorStop(0, 'rgba(255,255,235,0.95)');
    glow.addColorStop(0.4, t.boss ? 'rgba(90,200,255,0.7)' : 'rgba(255,205,70,0.7)');
    glow.addColorStop(1, 'rgba(255,220,90,0)');
    ctx.fillStyle = glow; ctx.fillRect(p.x - 140, p.y - 140, 280, 280);
    ctx.save(); ctx.globalAlpha = pulse;
    ctx.imageSmoothingEnabled = true; // bau low-poly em alta resolucao
    ctx.drawImage(getSprite(t.boss ? 'reward_chest_bone' : 'reward_chest_wood'), p.x - 80, p.y - 70, 160, 140);
    ctx.restore();
    for (let i = 0; i < 14; i++) {
      const a = i * 2.4 + time * 0.35, r = 80 + Math.sin(time * 2 + i) * 22;
      const x = p.x + Math.cos(a) * r, y = p.y + Math.sin(a) * r * 0.7;
      ctx.fillStyle = '#fff4bd'; ctx.fillRect(x - 3, y, 7, 1); ctx.fillRect(x, y - 3, 1, 7);
    }
    ui.text(320, 285, i18n.t('ui.chest_open'), { align: 'center', size: 12, color: '#fff4bd' });
    ui.text(320, 310, i18n.t('ui.chest_skip'), { align: 'center', size: 9, color: '#d6eaff' });
    return;
  }
  // Full-width luminous band; the cave remains visible above and below.
  const band = ctx.createLinearGradient?.(0, 82, 0, 278);
  if (band) { band.addColorStop(0, '#47cfff'); band.addColorStop(0.08, '#1265ce');
  band.addColorStop(0.5, '#082d78'); band.addColorStop(0.92, '#1265ce'); band.addColorStop(1, '#65e6ff'); }
  ctx.fillStyle = band || '#1265ce'; ctx.fillRect(0, 82, 640, 196);
  ctx.fillStyle = '#c4faff'; ctx.fillRect(0, 82, 640, 3); ctx.fillRect(0, 275, 640, 3);
  ui.text(320, 110, i18n.t('ui.chest_loot'), { align: 'center', size: 14, color: '#ffffff' });
  const step = Math.min(92, 600 / t.loot.length);
  t.loot.forEach((r, i) => {
    const x = 320 + (i - (t.loot.length - 1) / 2) * step;
    ctx.fillStyle = 'rgba(104,210,255,0.25)'; ctx.fillRect(x - 29, 138, 58, 58);
    ctx.drawImage(getSprite(r.icon), x - 23, 143, 46, 46);
    ui.text(x, 210, '+' + r.amount, { align: 'center', size: 12, color: '#ffffff' });
    const label = i18n.t((r.item ? 'item.' : 'res.') + r.id);
    // Wrap names without pushing the row outside the band.
    const words = label.split(' '); let row = '', lines = [];
    for (const word of words) { if ((row + ' ' + word).trim().length > 12 && row) { lines.push(row); row = ''; } row = (row + ' ' + word).trim(); }
    if (row) lines.push(row);
    lines.slice(0, 3).forEach((line, j) => ui.text(x, 226 + j * 10, line, { align: 'center', size: 8, color: '#dbf6ff' }));
  });
  ui.text(320, 302, i18n.t('ui.chest_exit'), { align: 'center', size: 10, color: '#ffffff' });
}
module.exports = { Treasure, drawTreasure };
