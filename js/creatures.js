// ============================================================
// creatures.js — Contagem de quadros dos lobos e da Mandíbula/Patas.
// GERADO por tools/expand_wolf_frames.py — não editar à mão.
// ============================================================
const CREATURE_FRAMES = {
  wolf: { idle: 5, walk: 16, attack: 11, hurt: 17, death: 7 },
  twin_jaw: { idle: 5, walk: 16, attack: 9, hurt: 3, death: 7 },
  twin_paw: { idle: 4, walk: 16, attack: 9, hurt: 3, death: 7 },
};

/** Duração total (s) de cada animação de criatura, mantida entre versões. */
const CREATURE_DURATION = { idle: 0.9, walk: 0.8, attack: 0.8, hurt: 0.5, death: 0.7 };

/** Quadros de uma animação de criatura (lobo/chefes); 1 se desconhecida. */
function creatureFrames(prefix, anim) {
  const row = CREATURE_FRAMES[prefix];
  return (row && row[anim]) || 1;
}

/** Segundos por quadro: mesma duração total, mais quadros = mais fluido. */
function creatureStep(prefix, anim) {
  return (CREATURE_DURATION[anim] || 0.07) / creatureFrames(prefix, anim);
}

module.exports = { CREATURE_FRAMES, CREATURE_DURATION, creatureFrames, creatureStep };
