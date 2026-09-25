// ============================================================
// gear.js — Aparência do goblin de acordo com o que ELE vestiu.
//
// ▸ COMO FUNCIONA (sistema de CAMADAS / layers)
//   Cada peça equipável (capacete, peitoral, calça, armas...) tem um
//   "overlay" próprio: um sprite que contém APENAS os pixels que aquela
//   peça acrescenta ao goblin base. Para montar o goblin vestido nós
//   empilhamos, na ordem certa, o corpo do goblin + cada overlay das
//   peças que ele está usando. Assim QUALQUER combinação funciona
//   automaticamente — inclusive misturar conjuntos (ex.: peitoral de
//   ferro + calça de avaritia), que antes fazia uma peça sumir.
//
// ▸ COMO ADICIONAR UMA PEÇA NOVA (o jeito fácil que você pediu)
//   1. Gere os overlays da peça em assets/sprites/goblin-gear-overlays
//      com o padrão:  overlay_<PREFIXO>_<anim>_<frame>.png
//      (anim = idle | walk | attack | hurt | death)
//   2. Registre a peça aqui em UMA linha, ligando o id do item ao
//      prefixo e à camada de desenho (z):
//         registerPiece('espada_ferro', 'wpn_espada', LAYER.arma_primaria);
//   Pronto. Ela já aparece equipada, sozinha ou combinada com qualquer
//   outra peça, em qualquer das 45 variações físicas de goblin.
//
// ▸ COMBOS (opcional, só estética)
//   Algumas combinações têm um sprite único desenhado à mão que fica
//   melhor do que empilhar as peças (ex.: o conjunto AVARITIA completo).
//   Quando TODAS as peças de um combo estão equipadas, usamos o overlay
//   do combo no lugar dos overlays individuais. É apenas um "atalho"
//   visual — remover um combo não quebra nada, só volta a empilhar.
//
// ▸ COMPOSIÇÃO EM TELA
//   Quando há variação física e/ou mistura de peças, devolvemos um id
//   `composite|base|camada1|camada2|...`; o assetLoader.js desenha tudo
//   num canvas cacheado (camadas sem PNG real são simplesmente puladas).
//   Quando é uma única peça sem variação e existe um sprite pronto
//   (ex.: av_full, ferro_pei), usamos direto esse sprite hand-made.
// ============================================================

// Camadas de desenho: quanto MENOR o z, mais embaixo a peça é desenhada.
// (calça embaixo, peitoral por cima, capacete acima, armas na frente.)
const LAYER = {
  calca: 10,
  botas: 15,
  peitoral: 20,
  colar: 25,
  capacete: 30,
  arma_secundaria: 40,
  arma_primaria: 50,
  runa: 55,
  anel: 60,
};

// Registro de peças: id do item → { overlay: <prefixo>, z: <camada> }.
// Só as peças que TÊM sprite entram aqui; as demais equipam normalmente,
// apenas não alteram a aparência (até ganharem seus overlays).
const PIECES = {};

// Combos hand-made: se TODAS as peças estiverem equipadas, usa o overlay
// do combo no lugar dos overlays individuais dessas peças.
const COMBOS = [];

// Prefixos que possuem um sprite COMPLETO pronto (goblin + peça já
// desenhados). Usado só para o atalho "uma peça, sem variação".
const FULL_SPRITE_PREFIXES = new Set();

/** Registra/atualiza uma peça equipável com aparência. */
function registerPiece(itemId, overlayPrefix, z, { hasFullSprite = false } = {}) {
  PIECES[itemId] = { overlay: overlayPrefix, z };
  if (hasFullSprite) FULL_SPRITE_PREFIXES.add(overlayPrefix);
  return PIECES[itemId];
}

/**
 * Registra um combo estético. `items` são os ids que precisam estar
 * TODOS equipados; `overlay` é o prefixo do sprite do combo. `z` define
 * a camada em que o combo é desenhado (padrão: a mais baixa das peças).
 */
function registerCombo(items, overlayPrefix, z, { hasFullSprite = true } = {}) {
  const zz = z ?? Math.min(...items.map((id) => PIECES[id]?.z ?? LAYER.peitoral));
  COMBOS.push({ items: items.slice(), overlay: overlayPrefix, z: zz });
  // combos maiores primeiro: assim o conjunto completo vence os parciais
  COMBOS.sort((a, b) => b.items.length - a.items.length);
  if (hasFullSprite) FULL_SPRITE_PREFIXES.add(overlayPrefix);
}

// ---------------- Catálogo atual de aparências ----------------

// Conjunto AVARITIA — cada peça tem overlay próprio E sprite completo.
registerPiece('capacete_avaritia', 'av_cap', LAYER.capacete, { hasFullSprite: true });
registerPiece('peitoral_avaritia', 'av_pei', LAYER.peitoral, { hasFullSprite: true });
registerPiece('calca_avaritia', 'av_cal', LAYER.calca, { hasFullSprite: true });

// Peitoral de FERRO — overlay + sprite completo.
registerPiece('peitoral_ferro', 'ferro_pei', LAYER.peitoral, { hasFullSprite: true });

// Conjunto de FERRO restante — overlays gerados por tools/gen_gear_overlays.py.
registerPiece('capacete_ferro', 'ferro_cap', LAYER.capacete);
registerPiece('calca_ferro', 'ferro_cal', LAYER.calca);

// Armas — únicas peças de arma que aparecem no goblin (primária e secundária).
registerPiece('espada_ferro', 'wpn_espada', LAYER.arma_primaria);
registerPiece('clava_goblin', 'wpn_clava', LAYER.arma_primaria);
registerPiece('escudo_madeira', 'wpn_escudo', LAYER.arma_secundaria);

// Combos hand-made do conjunto avaritia.
registerCombo(['capacete_avaritia', 'peitoral_avaritia', 'calca_avaritia'], 'av_full');
registerCombo(['capacete_avaritia', 'peitoral_avaritia'], 'av_cap_pei');
registerCombo(['capacete_avaritia', 'calca_avaritia'], 'av_cap_cal');
registerCombo(['peitoral_avaritia', 'calca_avaritia'], 'av_pei_cal');

// ---------------- Cálculo das camadas equipadas ----------------

/**
 * Lista de prefixos de overlay que ESTE `equip` produz, já na ordem de
 * desenho (de baixo para cima). Aplica os combos primeiro (estética) e
 * depois as peças individuais restantes.
 */
function layersForEquip(equip) {
  if (!equip) return [];
  const equipped = new Set(Object.values(equip).filter(Boolean));
  const used = new Set();
  const layers = []; // { overlay, z }

  // 1) combos: se todas as peças do combo estiverem equipadas, agrupa.
  for (const combo of COMBOS) {
    if (combo.items.every((id) => equipped.has(id) && !used.has(id))) {
      combo.items.forEach((id) => used.add(id));
      layers.push({ overlay: combo.overlay, z: combo.z });
    }
  }

  // 2) peças individuais que sobraram (mistura entre conjuntos etc.).
  for (const id of equipped) {
    if (used.has(id)) continue;
    const p = PIECES[id];
    if (p) {
      layers.push({ overlay: p.overlay, z: p.z });
      used.add(id);
    }
  }

  layers.sort((a, b) => a.z - b.z);
  return layers.map((l) => l.overlay);
}

/**
 * COMPATIBILIDADE: prefixo "principal" da versão vestida (o mais alto na
 * pilha, ou null). Mantido porque código/saves antigos podem consultar.
 */
function versionForEquip(equip) {
  const layers = layersForEquip(equip);
  return layers.length ? layers[layers.length - 1] : null;
}

/** Id do sprite DESTE goblin, combinando aparência física e equipamento. */
function spriteForGoblin(goblin, anim, frame) {
  const base = goblin?.variation
    ? `variant_${goblin.variation}_${anim}_${frame}`
    : `goblin_${anim}_${frame}`;

  const overlays = goblin?.equip ? layersForEquip(goblin.equip) : [];
  if (!overlays.length) return base;

  // Atalho: uma única peça, goblin sem variação e existe sprite completo
  // pronto → usa direto o sprite hand-made (ex.: av_full, ferro_pei).
  if (!goblin.variation && overlays.length === 1 && FULL_SPRITE_PREFIXES.has(overlays[0])) {
    return `${overlays[0]}_${anim}_${frame}`;
  }

  // Caso geral: empilha o corpo do goblin + cada overlay de peça.
  const layerIds = overlays.map((prefix) => `overlay_${prefix}_${anim}_${frame}`);
  return `composite|${base}|${layerIds.join('|')}`;
}

module.exports = {
  LAYER, PIECES, COMBOS,
  registerPiece, registerCombo,
  layersForEquip, versionForEquip, spriteForGoblin,
};
