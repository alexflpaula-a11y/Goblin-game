// Collection feedback aggregates the harvest of ONE source, never the inventory delta.
const { getSprite } = require('assetLoader.js');
class HarvestFeedback {
  constructor() { this.cards = []; }
  add(event) {
    const key = event.sourceId || event.kind;
    let card = this.cards.find((c) => c.key === key);
    if (!card) {
      card = { key, kind: event.kind, total: 0, ttl: 0, pulse: 0 };
      this.cards.unshift(card);
      this.cards = this.cards.slice(0, 3);
    }
    card.total = event.total ?? (card.total + event.amount);
    card.max = event.max || card.max;
    card.done = !!event.done;
    card.ttl = card.done ? 3.5 : 2.4;
    card.pulse = 0.2;
  }
  update(dt) {
    for (const c of this.cards) { c.ttl -= dt; c.pulse = Math.max(0, c.pulse - dt); }
    this.cards = this.cards.filter((c) => c.ttl > 0);
  }
}
function drawHarvestFeedback(ctx, ui, feedback, i18n) {
  feedback.cards.forEach((c, i) => {
    const x = 410, y = 86 + i * 61, w = 220;
    ctx.save();
    ctx.globalAlpha = Math.min(1, c.ttl * 2);
    ctx.fillStyle = 'rgba(4,13,23,0.8)'; ctx.fillRect(x + 3, y + 3, w, 54);
    ctx.fillStyle = '#172938'; ctx.fillRect(x, y, w, 54);
    ctx.strokeStyle = c.done ? '#85d995' : '#bda264'; ctx.lineWidth = 1;
    ctx.strokeRect(x + 0.5, y + 0.5, w - 1, 53);
    ctx.fillStyle = c.done ? '#85d995' : '#edc977'; ctx.fillRect(x, y, 3, 54);
    ctx.fillStyle = '#263e4e'; ctx.fillRect(x + 10, y + 9, 34, 34);
    ctx.imageSmoothingEnabled = false;
    const size = c.pulse > 0 ? 29 : 26;
    ctx.drawImage(getSprite('res_' + c.kind), x + 27 - size / 2, y + 26 - size / 2, size, size);
    ui.text(x + 54, y + 16, i18n.t(c.done ? 'ui.harvest_done' : 'ui.harvest_collecting'), { size: 8, color: '#b3d4df' });
    ui.text(x + 54, y + 34, '+' + c.total + ' ' + i18n.t('res.' + c.kind), { size: 12, bold: true, color: '#ffdf95' });
    if (c.max) {
      ctx.fillStyle = '#091923'; ctx.fillRect(x + 54, y + 43, 154, 3);
      ctx.fillStyle = '#7ecb9d'; ctx.fillRect(x + 54, y + 43, 154 * Math.min(1, c.total / c.max), 3);
    }
    ctx.restore();
  });
}
module.exports = { HarvestFeedback, drawHarvestFeedback };
