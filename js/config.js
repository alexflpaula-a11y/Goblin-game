// ============================================================
// config.js — Constantes globais do jogo
// ============================================================
const CONFIG = {
  // Resolução lógica PAISAGEM (tudo é desenhado nessas coordenadas e escalado)
  LOGICAL_WIDTH: 640,
  LOGICAL_HEIGHT: 360,

  // 'fit'  → o jogo inteiro cabe na tela (com barras, se preciso)
  // 'cover'→ preenche a tela toda, cortando bordas
  SCALE_MODE: 'fit',

  // Limita o devicePixelRatio para não estourar memória em telas 3x+
  MAX_DPR: 3,

  // Visual de debug
  BACKGROUND: '#241d38',
  GRID_COLOR: 'rgba(255,255,255,0.05)',
  GRID_SIZE: 40,
  SPRITE_SIZE: 32,
};

module.exports = { CONFIG };
