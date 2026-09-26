// ============================================================
// input.js — Gestos mobile multi-toque + mouse
//   1 dedo arrastando  → pan (mover a câmera)
//   2 dedos (pinça)    → zoom no ponto médio + pan pelo meio
//   toque rápido       → tap (seleção)
//   roda do mouse      → zoom no cursor
// Tudo é agregado por frame e consumido com consume().
// Coordenadas sempre no espaço lógico (0..360, 0..640).
// ============================================================
const { CONFIG } = require('config.js');
class Input {
  constructor(canvas) {
    this.canvas = canvas;
    this.pointers = new Map(); // id → {x, y, x0, y0, t0, moved}
    this.pinchActive = false;
    this.prevDist = 0;

    // agregados do frame atual
    this.pan = { dx: 0, dy: 0 };
    this.pinch = null;   // {factor, mx, my}
    this.tap = null;     // {x, y}
    this.wheel = null;   // {factor, x, y}
    this.swipe = null;   // {dir: -1|+1} — arrasto horizontal (paginar)
    this.cursor = null;  // último ponto lógico (prévia de posicionamento)
    this.cursorSeq = 0;  // muda a cada down/move

    this._bind();
  }

  _toLogical(clientX, clientY) {
    const rect = this.canvas.getBoundingClientRect();
    return {
      x: ((clientX - rect.left) / rect.width) * CONFIG.LOGICAL_WIDTH,
      y: ((clientY - rect.top) / rect.height) * CONFIG.LOGICAL_HEIGHT,
    };
  }

  _bind() {
    this.canvas.addEventListener('pointerdown', (e) => {
      const p = this._toLogical(e.clientX, e.clientY);
      this.cursor = p; this.cursorSeq += 1;
      this.pointers.set(e.pointerId, { x: p.x, y: p.y, x0: p.x, y0: p.y, t0: performance.now(), moved: false });
      if (this.pointers.size === 2) {
        this.pinchActive = true;
        this.tap = null;
        this.prevDist = this._dist();
      }
    }, { passive: true });

    this.canvas.addEventListener('pointermove', (e) => {
      const ptr = this.pointers.get(e.pointerId);
      if (!ptr) return;
      const p = this._toLogical(e.clientX, e.clientY);
      this.cursor = p; this.cursorSeq += 1;

      if (this.pointers.size === 1) {
        // pan com 1 dedo
        this.pan.dx += p.x - ptr.x;
        this.pan.dy += p.y - ptr.y;
      }

      ptr.x = p.x; ptr.y = p.y;
      if (Math.hypot(p.x - ptr.x0, p.y - ptr.y0) > 10) ptr.moved = true;

      if (this.pointers.size === 2) {
        // pinça: zoom pela razão das distâncias + pan pelo ponto médio
        const d = this._dist();
        const mid = this._mid();
        if (this.prevDist > 0 && d > 0) {
          const factor = d / this.prevDist;
          if (!this.pinch) this.pinch = { factor: 1, mx: mid.x, my: mid.y };
          this.pinch.factor *= factor;
          this.pinch.mx = mid.x;
          this.pinch.my = mid.y;
        }
        this.prevDist = d;
      }
    }, { passive: true });

    const up = (e) => {
      const ptr = this.pointers.get(e.pointerId);
      this.pointers.delete(e.pointerId);
      if (this.pointers.size < 2) { this.pinchActive = false; this.prevDist = 0; }
      if (ptr && !this.pinchActive && !ptr.moved && performance.now() - ptr.t0 < 350) {
        this.tap = { x: ptr.x, y: ptr.y };
      }
      // arrasto horizontal rápido → swipe (usado para paginar telas)
      if (ptr && !this.pinchActive && ptr.moved) {
        const dx = ptr.x - ptr.x0;
        const dy = ptr.y - ptr.y0;
        if (Math.abs(dx) > 45 && Math.abs(dx) > Math.abs(dy) * 1.3) {
          this.swipe = { dir: dx < 0 ? 1 : -1 };
        }
      }
    };
    this.canvas.addEventListener('pointerup', up, { passive: true });
    this.canvas.addEventListener('pointercancel', up, { passive: true });

    this.canvas.addEventListener('wheel', (e) => {
      e.preventDefault();
      const p = this._toLogical(e.clientX, e.clientY);
      this.wheel = { factor: e.deltaY < 0 ? 1.15 : 1 / 1.15, x: p.x, y: p.y };
    }, { passive: false });
  }

  _dist() {
    const [a, b] = [...this.pointers.values()];
    return Math.hypot(a.x - b.x, a.y - b.y);
  }

  _mid() {
    const [a, b] = [...this.pointers.values()];
    return { x: (a.x + b.x) / 2, y: (a.y + b.y) / 2 };
  }

  // O loop chama 1x por frame e limpa os agregados
  consume() {
    const out = {
      pan: (this.pan.dx || this.pan.dy) ? { ...this.pan } : null,
      pinch: this.pinch,
      tap: this.tap,
      wheel: this.wheel,
      swipe: this.swipe,
    };
    this.pan = { dx: 0, dy: 0 };
    this.pinch = null;
    this.tap = null;
    this.wheel = null;
    this.swipe = null;
    return out;
  }
}

module.exports = { Input };
