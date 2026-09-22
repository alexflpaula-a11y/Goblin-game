// ============================================================
// camera.js — Câmera livre do mundo (pan + zoom, estilo mobile)
// 1 dedo arrasta → pan | pinça (2 dedos) → zoom | roda do mouse → zoom
// ============================================================
const { CONFIG } = require('config.js');
const clamp = (v, a, b) => Math.max(a, Math.min(b, v));

class Camera {
  constructor(worldW, worldH, x, y, zoom = 1.6) {
    this.worldW = worldW;
    this.worldH = worldH;
    this.x = x;           // centro da visão, em coords de mundo
    this.y = y;
    this.zoom = zoom;     // 1 = 1px de mundo por px lógico
    this.minZoom = 0.7;
    this.maxZoom = 3.0;
    this.clamp();
  }

  get viewW() { return CONFIG.LOGICAL_WIDTH / this.zoom; }
  get viewH() { return CONFIG.LOGICAL_HEIGHT / this.zoom; }

  // dx/dy em pixels LÓGICOS de tela → desloca o mundo no sentido do dedo
  panByScreen(dx, dy) {
    this.x -= dx / this.zoom;
    this.y -= dy / this.zoom;
    this.clamp();
  }

  // Zoom mantendo fixo o ponto de tela (sx, sy)
  zoomAt(sx, sy, factor) {
    const before = this.screenToWorld(sx, sy);
    this.zoom = clamp(this.zoom * factor, this.minZoom, this.maxZoom);
    const after = this.screenToWorld(sx, sy);
    this.x += before.x - after.x;
    this.y += before.y - after.y;
    this.clamp();
  }

  screenToWorld(sx, sy) {
    return {
      x: this.x + (sx - CONFIG.LOGICAL_WIDTH / 2) / this.zoom,
      y: this.y + (sy - CONFIG.LOGICAL_HEIGHT / 2) / this.zoom,
    };
  }

  worldToScreen(wx, wy) {
    return {
      x: (wx - this.x) * this.zoom + CONFIG.LOGICAL_WIDTH / 2,
      y: (wy - this.y) * this.zoom + CONFIG.LOGICAL_HEIGHT / 2,
    };
  }

  // Não deixa a câmera sair da ilha
  clamp() {
    const vw = this.viewW, vh = this.viewH;
    this.x = vw >= this.worldW ? this.worldW / 2 : clamp(this.x, vw / 2, this.worldW - vw / 2);
    this.y = vh >= this.worldH ? this.worldH / 2 : clamp(this.y, vh / 2, this.worldH - vh / 2);
  }

  // Aplica a transformação de mundo no contexto 2D
  applyTransform(ctx, scaleFactor) {
    const s = scaleFactor * this.zoom;
    ctx.setTransform(
      s, 0, 0, s,
      scaleFactor * (CONFIG.LOGICAL_WIDTH / 2 - this.x * this.zoom),
      scaleFactor * (CONFIG.LOGICAL_HEIGHT / 2 - this.y * this.zoom)
    );
  }

  // Retângulo visível do mundo (para culling)
  visible() {
    return {
      x0: this.x - this.viewW / 2,
      y0: this.y - this.viewH / 2,
      x1: this.x + this.viewW / 2,
      y1: this.y + this.viewH / 2,
    };
  }
}

module.exports = { Camera };
