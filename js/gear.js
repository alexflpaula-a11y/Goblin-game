// ============================================================
// gear.js — Sprites do goblin de acordo com o que ELE vestiu.
//
// Antes a armadura era da vila inteira (compra única); agora cada
// goblin tem seu próprio `equip` (inventory.js) e o sprite sai
// daqui: as peças AVARITIA (capacete/peitoral/calça) têm skins
// para todas as combinações, e o peitoral de FERRO tem a própria
// skin quando usado sozinho (sem peças avaritia por cima).
//
// Os sprites seguem a mesma convenção do base:
//   av_pei_idle_0, av_cap_pei_walk_3, av_full_death_7, ferro_pei_attack_5...
// ============================================================

// combinação de peças avaritia → prefixo dos sprites da versão equipada
const VERSIONS = {
  'cap+cal+pei': 'av_full',
  'cap+pei': 'av_cap_pei',
  'cap+cal': 'av_cap_cal',
  'cal+pei': 'av_pei_cal',
  'cap': 'av_cap',
  'pei': 'av_pei',
  'cal': 'av_cal',
};

/**
 * Prefixo da versão vestida por esse `equip` (null = sprite base).
 * Avaritia vence; peitoral de ferro só aparece sem peças avaritia.
 */
function versionForEquip(equip) {
  const cap = equip?.capacete === 'capacete_avaritia';
  const cal = equip?.calca === 'calca_avaritia';
  const pei = equip?.peitoral === 'peitoral_avaritia';
  const k = [cap && 'cap', cal && 'cal', pei && 'pei'].filter(Boolean).join('+');
  if (VERSIONS[k]) return VERSIONS[k];
  if (!cap && !cal && equip?.peitoral === 'peitoral_ferro') return 'ferro_pei';
  return null;
}

/** Id do sprite DESTE goblin vestindo o que ele equipou. */
function spriteForGoblin(goblin, anim, frame) {
  const ver = goblin?.equip ? versionForEquip(goblin.equip) : null;
  return ver ? `${ver}_${anim}_${frame}` : `goblin_${anim}_${frame}`;
}

module.exports = { VERSIONS, versionForEquip, spriteForGoblin };
