// ============================================================
// ui.js — UI imediata desenhada no canvas (painéis, botões,
// barras, textos). Os hit-tests ficam registrados por frame e
// o tap é roteado pelo main.js.
// ============================================================
class UI {
  constructor(ctx) {
    this.ctx = ctx;
    this.els = [];
  }

  begin() { this.els = []; }

  panel(x, y, w, h, title) {
    const c = this.ctx;
    // sombra suave
    c.fillStyle = 'rgba(0,0,0,0.35)';
    c.beginPath();
    if (c.roundRect) c.roundRect(x + 2, y + 4, w, h, 12); else c.rect(x + 2, y + 4, w, h);
    c.fill();
    // corpo com leve gradiente
    let g = null;
    if (c.createLinearGradient) {
      g = c.createLinearGradient(x, y, x, y + h);
      g.addColorStop(0, 'rgba(38,28,60,0.96)');
      g.addColorStop(1, 'rgba(20,14,34,0.96)');
    }
    c.fillStyle = g || 'rgba(22,16,36,0.94)';
    c.strokeStyle = 'rgba(167,139,250,0.45)';
    c.lineWidth = 1.5;
    c.beginPath();
    if (c.roundRect) c.roundRect(x, y, w, h, 12); else c.rect(x, y, w, h);
    c.fill(); c.stroke();
    // brilho no topo
    c.fillStyle = 'rgba(255,255,255,0.06)';
    c.fillRect(x + 8, y + 2, w - 16, 2);
    if (title) this.text(x + w / 2, y + 20, title, { align: 'center', size: 13, bold: true, color: '#efeafd' });
  }

  text(x, y, str, o = {}) {
    const c = this.ctx;
    c.font = `${o.bold ? 'bold ' : ''}${o.size || 11}px monospace`;
    c.fillStyle = o.color || '#efeafd';
    c.textAlign = o.align || 'left';
    c.textBaseline = 'middle';
    c.fillText(str, x, y);
    c.textAlign = 'left';
  }

  bar(x, y, w, h, frac, color) {
    const c = this.ctx;
    c.fillStyle = 'rgba(0,0,0,0.5)';
    c.fillRect(x, y, w, h);
    c.fillStyle = color;
    c.fillRect(x, y, Math.max(0, Math.min(1, frac)) * w, h);
  }

  button(id, x, y, w, h, label, enabled = true, accent = false) {
    const c = this.ctx;
    // sombra
    if (enabled) {
      c.fillStyle = 'rgba(0,0,0,0.25)';
      c.beginPath();
      if (c.roundRect) c.roundRect(x + 1, y + 2, w, h, 8); else c.rect(x + 1, y + 2, w, h);
      c.fill();
    }
    let fill;
    if (!enabled) {
      fill = 'rgba(120,120,140,0.22)';
    } else if (c.createLinearGradient) {
      fill = c.createLinearGradient(x, y, x, y + h);
      if (accent) { fill.addColorStop(0, '#b9a2ff'); fill.addColorStop(1, '#8b6cf0'); }
      else { fill.addColorStop(0, 'rgba(167,139,250,0.30)'); fill.addColorStop(1, 'rgba(167,139,250,0.12)'); }
    } else {
      fill = accent ? '#a78bfa' : 'rgba(167,139,250,0.18)';
    }
    c.fillStyle = fill;
    c.strokeStyle = enabled ? 'rgba(167,139,250,0.75)' : 'rgba(255,255,255,0.12)';
    c.lineWidth = 1.5;
    c.beginPath();
    if (c.roundRect) c.roundRect(x, y, w, h, 8); else c.rect(x, y, w, h);
    c.fill(); c.stroke();
    if (enabled) {
      c.fillStyle = 'rgba(255,255,255,0.16)';
      c.fillRect(x + 5, y + 3, w - 10, 1.5);
    }
    this.text(x + w / 2, y + h / 2, label, {
      align: 'center', size: 11, bold: true,
      color: !enabled ? '#8a8798' : accent ? '#1b1530' : '#e4dbff',
    });
    if (enabled) this.els.push({ id, x, y, w, h });
  }

  // Botão quadrado rústico só com ícone (barra de ações do mundo)
  iconBtn(id, x, y, s, active = false) {
    const c = this.ctx;
    // sombra
    c.fillStyle = 'rgba(0,0,0,0.30)';
    c.beginPath();
    if (c.roundRect) c.roundRect(x + 1.5, y + 2.5, s, s, 10); else c.rect(x + 1.5, y + 2.5, s, s);
    c.fill();
    // corpo de madeira com gradiente
    let g = null;
    if (c.createLinearGradient) {
      g = c.createLinearGradient(x, y, x, y + s);
      if (active) { g.addColorStop(0, '#caa036'); g.addColorStop(1, '#8a5a18'); }
      else { g.addColorStop(0, '#6f4b2a'); g.addColorStop(1, '#48301a'); }
    }
    c.fillStyle = g || (active ? '#a5772a' : '#573a20');
    c.beginPath();
    if (c.roundRect) c.roundRect(x, y, s, s, 10); else c.rect(x, y, s, s);
    c.fill();
    // borda
    c.lineWidth = 2;
    c.strokeStyle = active ? '#ffe9a8' : '#2a1b0c';
    c.beginPath();
    if (c.roundRect) c.roundRect(x + 1, y + 1, s - 2, s - 2, 9); else c.rect(x + 1, y + 1, s - 2, s - 2);
    c.stroke();
    // brilho no topo
    c.fillStyle = 'rgba(255,255,255,0.16)';
    c.fillRect(x + 5, y + 4, s - 10, 2);
    this.els.push({ id, x, y, w: s, h: s });
  }

  // Selo/contador circular (badge) para cantos de botões
  badge(cx, cy, str, color = '#4fa562', ink = '#0f2a16') {
    const c = this.ctx;
    c.fillStyle = color;
    c.beginPath(); c.arc(cx, cy, 8, 0, Math.PI * 2); c.fill();
    c.strokeStyle = '#1b1530'; c.lineWidth = 1.5; c.stroke();
    this.text(cx, cy + 0.5, str, { align: 'center', size: 9, bold: true, color: ink });
  }

  // Região clicável sem visual (cards inteiros)
  region(id, x, y, w, h) { this.els.push({ id, x, y, w, h }); }

  card(x, y, w, h) {
    const c = this.ctx;
    c.fillStyle = 'rgba(255,255,255,0.06)';
    c.strokeStyle = 'rgba(255,255,255,0.14)';
    c.lineWidth = 1;
    c.beginPath();
    if (c.roundRect) c.roundRect(x, y, w, h, 8); else c.rect(x, y, w, h);
    c.fill(); c.stroke();
  }

  hit(tap) {
    if (!tap) return null;
    for (let i = this.els.length - 1; i >= 0; i--) {
      const e = this.els[i];
      if (tap.x >= e.x && tap.x <= e.x + e.w && tap.y >= e.y && tap.y <= e.y + e.h) return e.id;
    }
    return null;
  }

  // ---------- Visual rústico goblin ----------
  // Painel de pranchas de madeira gastas, com pregos e lascas
  rusticPanel(x, y, w, h) {
    const c = this.ctx;
    c.save();
    c.beginPath();
    if (c.roundRect) c.roundRect(x, y, w, h, 6); else c.rect(x, y, w, h);
    c.clip();
    const shades = ['#6e4626', '#7d5230', '#65411f', '#75492a'];
    let py = y, i = 0;
    while (py < y + h) {
      const ph = 14 + ((i * 7) % 5);
      c.fillStyle = shades[i % 4];
      c.fillRect(x, py, w, ph);
      c.fillStyle = 'rgba(0,0,0,0.28)';
      c.fillRect(x, py + ph - 1, w, 1);
      py += ph; i++;
    }
    // veios + rachaduras
    c.fillStyle = 'rgba(0,0,0,0.14)';
    for (let k = 0; k < 8; k++) {
      const gx = x + ((k * 53) % (w - 24)) + 8;
      const gy = y + ((k * 37) % (h - 10)) + 4;
      c.fillRect(gx, gy, 10 + (k % 3) * 5, 1);
    }
    c.fillStyle = 'rgba(0,0,0,0.2)';
    c.fillRect(x + w * 0.22, y + 8, 1, h * 0.3);
    c.fillRect(x + w * 0.78, y + h * 0.5, 1, h * 0.3);
    c.restore();
    // borda gasta
    c.strokeStyle = '#3c2712';
    c.lineWidth = 2;
    c.beginPath();
    if (c.roundRect) c.roundRect(x + 1, y + 1, w - 2, h - 2, 6); else c.rect(x + 1, y + 1, w - 2, h - 2);
    c.stroke();
    // pregos tortos
    c.fillStyle = '#9aa0ad';
    for (const [nx, ny] of [[x + 6, y + 6], [x + w - 7, y + 7], [x + 7, y + h - 7], [x + w - 6, y + h - 6]]) {
      c.fillRect(nx - 1, ny - 1, 3, 3);
      c.fillStyle = 'rgba(0,0,0,0.35)';
      c.fillRect(nx, ny, 1, 1);
      c.fillStyle = '#9aa0ad';
    }
    // lascas nas bordas
    c.fillStyle = '#3c2712';
    c.beginPath(); c.moveTo(x + w * 0.3, y); c.lineTo(x + w * 0.3 + 7, y); c.lineTo(x + w * 0.3 + 3, y + 5); c.closePath(); c.fill();
    c.beginPath(); c.moveTo(x + w * 0.7, y + h); c.lineTo(x + w * 0.7 - 7, y + h); c.lineTo(x + w * 0.7 - 3, y + h - 5); c.closePath(); c.fill();
  }

  // Cartão de pergaminho velho (manchas e bordas gastas)
  parchment(x, y, w, h) {
    const c = this.ctx;
    c.fillStyle = '#d8c090';
    c.fillRect(x, y, w, h);
    c.fillStyle = '#c9b079';
    c.fillRect(x, y + h - 3, w, 3);
    c.fillRect(x + w - 3, y, 3, h);
    c.fillStyle = 'rgba(110,70,38,0.28)';
    c.fillRect(x + 4, y + 5, 2, 2);
    c.fillRect(x + w - 9, y + h - 10, 3, 2);
    c.fillRect(x + 7, y + h - 8, 2, 2);
    c.fillRect(x + w - 14, y + 6, 2, 2);
    c.strokeStyle = '#8a6b4a';
    c.lineWidth = 1;
    c.strokeRect(x + 0.5, y + 0.5, w - 1, h - 1);
  }

  // Brilho radial atrás do ícone (como na referência)
  glow(cx, cy, r) {
    const c = this.ctx;
    const g = c.createRadialGradient(cx, cy, 2, cx, cy, r);
    g.addColorStop(0, 'rgba(255,232,160,0.5)');
    g.addColorStop(1, 'rgba(255,232,160,0)');
    c.fillStyle = g;
    c.beginPath(); c.arc(cx, cy, r, 0, Math.PI * 2); c.fill();
  }

  // Placa de madeira com texto (título/banner)
  woodSign(x, y, w, h, label, size = 12) {
    const c = this.ctx;
    c.fillStyle = '#4a3018';
    c.fillRect(x, y, w, h);
    c.fillStyle = 'rgba(255,255,255,0.06)';
    c.fillRect(x, y, w, 2);
    c.strokeStyle = '#2a1b0c';
    c.lineWidth = 1.5;
    c.strokeRect(x + 0.5, y + 0.5, w - 1, h - 1);
    c.fillStyle = '#8a8798';
    c.fillRect(x + 3, y + 3, 2, 2);
    c.fillRect(x + w - 5, y + h - 5, 2, 2);
    this.text(x + w / 2, y + h / 2 + 1, label, { align: 'center', size, bold: true, color: '#e8d5a8' });
  }

  // Aba rústica (tab)
  tab(id, x, y, w, h, label, active) {
    const c = this.ctx;
    c.fillStyle = active ? '#8a6b4a' : '#54371c';
    c.beginPath();
    c.moveTo(x + 4, y + h); c.lineTo(x, y + 4); c.lineTo(x + 6, y);
    c.lineTo(x + w - 6, y); c.lineTo(x + w, y + 4); c.lineTo(x + w - 4, y + h);
    c.closePath(); c.fill();
    c.strokeStyle = '#2a1b0c'; c.lineWidth = 1.5; c.stroke();
    this.text(x + w / 2, y + h / 2 + 1, label, {
      align: 'center', size: 9, bold: true,
      color: active ? '#ffe9b8' : '#b99b6f',
    });
    this.els.push({ id, x, y, w, h });
  }

  // X de fechar rústico (maior e mais bonito)
  closeX(id, x, y, s = 30) {
    const c = this.ctx;
    // sombra
    c.fillStyle = 'rgba(0,0,0,0.3)';
    c.beginPath();
    if (c.roundRect) c.roundRect(x + 1, y + 2, s, s, 8); else c.rect(x + 1, y + 2, s, s);
    c.fill();
    // corpo vermelho com gradiente
    let g = null;
    if (c.createLinearGradient) {
      g = c.createLinearGradient(x, y, x, y + s);
      g.addColorStop(0, '#c8452f'); g.addColorStop(1, '#7e2416');
    }
    c.fillStyle = g || '#8c2f1f';
    c.beginPath();
    if (c.roundRect) c.roundRect(x, y, s, s, 8); else c.rect(x, y, s, s);
    c.fill();
    c.strokeStyle = '#2a1b0c'; c.lineWidth = 2;
    c.beginPath();
    if (c.roundRect) c.roundRect(x + 1, y + 1, s - 2, s - 2, 7); else c.rect(x + 1, y + 1, s - 2, s - 2);
    c.stroke();
    // brilho no topo
    c.fillStyle = 'rgba(255,255,255,0.18)';
    c.fillRect(x + 5, y + 3, s - 10, 2);
    // X
    const m = Math.round(s * 0.3);
    c.strokeStyle = '#ffe9b8'; c.lineWidth = 3; c.lineCap = 'round';
    c.beginPath();
    c.moveTo(x + m, y + m); c.lineTo(x + s - m, y + s - m);
    c.moveTo(x + s - m, y + m); c.lineTo(x + m, y + s - m);
    c.stroke();
    c.lineCap = 'butt';
    this.els.push({ id, x, y, w: s, h: s });
  }

  // Botão de seta (chevron) — usado para trocar de personagem no equipar
  arrowBtn(id, x, y, s, dir) {
    const c = this.ctx;
    // sombra
    c.fillStyle = 'rgba(0,0,0,0.3)';
    c.beginPath();
    if (c.roundRect) c.roundRect(x + 1, y + 2, s, s, 9); else c.rect(x + 1, y + 2, s, s);
    c.fill();
    // corpo madeira/acento
    let g = null;
    if (c.createLinearGradient) {
      g = c.createLinearGradient(x, y, x, y + s);
      g.addColorStop(0, '#b9a2ff'); g.addColorStop(1, '#8b6cf0');
    }
    c.fillStyle = g || '#a78bfa';
    c.beginPath();
    if (c.roundRect) c.roundRect(x, y, s, s, 9); else c.rect(x, y, s, s);
    c.fill();
    c.strokeStyle = '#2a1b0c'; c.lineWidth = 2;
    c.beginPath();
    if (c.roundRect) c.roundRect(x + 1, y + 1, s - 2, s - 2, 8); else c.rect(x + 1, y + 1, s - 2, s - 2);
    c.stroke();
    c.fillStyle = 'rgba(255,255,255,0.2)';
    c.fillRect(x + 5, y + 3, s - 10, 2);
    // chevron
    const cx = x + s / 2, cy = y + s / 2, r = s * 0.22;
    c.strokeStyle = '#1b1530'; c.lineWidth = 3; c.lineJoin = 'round'; c.lineCap = 'round';
    c.beginPath();
    if (dir < 0) {
      c.moveTo(cx + r * 0.6, cy - r); c.lineTo(cx - r * 0.6, cy); c.lineTo(cx + r * 0.6, cy + r);
    } else {
      c.moveTo(cx - r * 0.6, cy - r); c.lineTo(cx + r * 0.6, cy); c.lineTo(cx - r * 0.6, cy + r);
    }
    c.stroke();
    c.lineJoin = 'miter'; c.lineCap = 'butt';
    this.els.push({ id, x, y, w: s, h: s });
  }

  // Barra de rolagem vertical (trilho fino + polegar dourado)
  scrollbarV(x, y, h, scroll, maxScroll, viewH, contentH) {
    if (maxScroll <= 0) return;
    const c = this.ctx;
    c.fillStyle = 'rgba(0,0,0,0.28)';
    c.fillRect(x, y, 4, h);
    const thumbH = Math.max(20, h * (viewH / contentH));
    const t = (scroll / maxScroll) * (h - thumbH);
    c.fillStyle = 'rgba(255,233,168,0.65)';
    c.fillRect(x, y + t, 4, thumbH);
  }

  // Barra de rolagem horizontal
  scrollbarH(x, y, w, scroll, maxScroll, viewW, contentW) {
    if (maxScroll <= 0) return;
    const c = this.ctx;
    c.fillStyle = 'rgba(0,0,0,0.28)';
    c.fillRect(x, y, w, 4);
    const thumbW = Math.max(20, w * (viewW / contentW));
    const t = (scroll / maxScroll) * (w - thumbW);
    c.fillStyle = 'rgba(255,233,168,0.65)';
    c.fillRect(x + t, y, thumbW, 4);
  }

  // Indicador de páginas com pontinhos (o ativo é maior/dourado)
  pageDots(cx, cy, count, active) {
    const c = this.ctx;
    const gap = 11;
    const start = cx - ((count - 1) * gap) / 2;
    for (let i = 0; i < count; i++) {
      const on = i === active;
      c.fillStyle = on ? '#ffe9a8' : 'rgba(255,233,168,0.32)';
      c.beginPath();
      c.arc(start + i * gap, cy, on ? 3.4 : 2.4, 0, Math.PI * 2);
      c.fill();
    }
  }
}

module.exports = { UI };
