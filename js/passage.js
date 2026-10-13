// ============================================================
// passage.js — Passagem da caverna entre a ilha e a sala de batalha.
//
// Ao escolher os lutadores e entrar numa toca, o grupo caminha por um
// túnel antes de chegar à sala. A câmera avança (zoom em direção ao fundo
// do túnel) enquanto os goblins andam pelo chão. Um toque pula a passagem.
//
// Lógica pura + desenho em drawCavePassage(); não toca no estado do jogo.
// A batalha começa só quando passage.finished() ou o toque pula.
// ============================================================
const { getSprite } = require('assetLoader.js');
const { drawGoblinAt } = require('raid.js');

const PASSAGE_TIME = 3.4;
const SKIP_AFTER = 0.6;
// Ponto de fuga do túnel dentro da arte (640×360).
const VANISH = { x: 322, y: 172 };
// Pés do grupo, em faixas do chão (duas linhas, para o grupo não virar um bloco).
const LANE_Y = [300, 318, 308, 328];

class CavePassage {
  constructor({ allies, duration } = {}) {
    this.allies = (allies || []).filter(Boolean).slice(0, 4);
    this.dur = duration || PASSAGE_TIME;
    this.t = 0;
    this.frame = 0;
    this.frameT = 0;
  }

  update(dt) {
    this.t = Math.min(this.dur, this.t + dt);
    this.frameT += dt;
    if (this.frameT >= 0.1) {
      this.frameT = 0;
      this.frame = (this.frame + 1) % 8;
    }
  }

  progress() { return this.t / this.dur; }

  finished() { return this.t >= this.dur; }

  canSkip() { return this.t >= SKIP_AFTER; }
}

function smooth(k) { return k * k * (3 - 2 * k); }

function drawCavePassage(ctx, ui, pass, i18n, time) {
  const k = pass.progress();
  const e = smooth(k);
  const img = getSprite('bg_den_passage');

  // Avanço: o túnel cresce em torno do ponto de fuga.
  const z = 1 + 0.42 * e;
  const sway = Math.sin(time * 1.3) * 3 * (1 - e * 0.5);
  ctx.save();
  ctx.imageSmoothingEnabled = false;
  ctx.drawImage(img, VANISH.x - VANISH.x * z + sway, VANISH.y - VANISH.y * z, 640 * z, 360 * z);
  ctx.restore();

  // Poeira no ar do túnel.
  ctx.save();
  for (let i = 0; i < 14; i++) {
    const px = ((i * 97 + time * (18 + i)) % 660) - 10;
    const py = 60 + ((i * 53) % 220) + Math.sin(time * 2 + i) * 4;
    ctx.globalAlpha = 0.25 + 0.2 * Math.sin(time * 3 + i);
    ctx.fillStyle = '#e8cf9a';
    ctx.fillRect(px, py, 2, 2);
  }
  ctx.restore();

  // Grupo andando da entrada (esquerda) em direção ao fundo do túnel.
  const walk = pass.allies;
  walk.forEach((g, i) => {
    const x = -30 - i * 26 + e * 300;
    const y = LANE_Y[i % LANE_Y.length];
    ctx.save();
    ctx.fillStyle = 'rgba(0,0,0,0.3)';
    ctx.beginPath(); ctx.ellipse(x, y + 2, 12, 3.5, 0, 0, Math.PI * 2); ctx.fill();
    ctx.restore();
    drawGoblinAt(ctx, g, x, y, 1, 'walk', pass.frame + i * 2, 1.6);
  });

  // Vinheta: escurece as bordas e deixa o fundo mais profundo.
  const grad = ctx.createRadialGradient(320, 180, 110, 320, 180, 360);
  grad.addColorStop(0, 'rgba(0,0,0,0)');
  grad.addColorStop(1, 'rgba(0,0,0,0.6)');
  ctx.save();
  ctx.fillStyle = grad;
  ctx.fillRect(0, 0, 640, 360);
  ctx.restore();

  ui.woodSign(8, 8, 236, 22, i18n.t('ui.cave_passage'), 11);
  ui.text(320, 346, i18n.t('ui.cave_passage_skip'), { align: 'center', size: 8, color: '#cdbb94' });

  // Escurecimento final: a passagem termina em preto e a sala aparece.
  const fade = Math.max(0, (k - 0.9) / 0.1);
  if (fade > 0) {
    ctx.save();
    ctx.fillStyle = `rgba(0,0,0,${Math.min(1, fade)})`;
    ctx.fillRect(0, 0, 640, 360);
    ctx.restore();
  }
}

module.exports = { CavePassage, drawCavePassage, PASSAGE_TIME, SKIP_AFTER };
