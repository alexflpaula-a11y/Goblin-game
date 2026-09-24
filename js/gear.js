// ============================================================
// gear.js — Conjunto AVARITIA: peças de armadura vendidas no
// Mercado (etapa "loja de equipamentos").
//
// As peças são compras ÚNICAS da vila: compradas no Mercado,
// ficam com a vila para sempre (persistem no save) e TODOS os
// goblins passam a vestir a combinação adquirida — cada peça a
// mais muda o sprite (individual → pares → conjunto completo,
// gerados pixel a pixel em sprites/itens/, sem pixels novos).
//
// Os sprites seguem a mesma convenção do base:
//   av_pei_idle_0, av_cap_pei_walk_3, av_full_death_7, ...
// ============================================================
const { BAL } = require('balance.js');

// Peças à venda (ordem de exibição na prateleira do Mercado).
const GEAR = [
  { key: 'peitoral_avaritia', ver: 'pei', icon: 'av_pei_icon', price: 120 },
  { key: 'calca_avaritia',    ver: 'cal', icon: 'av_cal_icon', price: 90 },
  { key: 'capacete_avaritia', ver: 'cap', icon: 'av_cap_icon', price: 150 },
];

// combinação de peças → prefixo dos sprites da versão equipada
const VERSIONS = {
  'cap+cal+pei': 'av_full',
  'cap+pei': 'av_cap_pei',
  'cap+cal': 'av_cap_cal',
  'cal+pei': 'av_pei_cal',
  'cap': 'av_cap',
  'pei': 'av_pei',
  'cal': 'av_cal',
};

/** Preço fixo da peça (balance.json `gear.prices` pode sobrescrever). */
function priceOf(key) {
  const g = GEAR.find((x) => x.key === key);
  return BAL.gear?.prices?.[key] ?? g?.price ?? 100;
}

// ---------- Estado (espelho de village.gear) ----------
let owned = {};

function setOwned(gearObj) { owned = gearObj || {}; }

/** Prefixo da versão equipada agora (null = sem armadura, sprite base). */
function ownedVersion() {
  const pei = !!owned.peitoral_avaritia;
  const cal = !!owned.calca_avaritia;
  const cap = !!owned.capacete_avaritia;
  const k = [cap && 'cap', cal && 'cal', pei && 'pei'].filter(Boolean).join('+');
  return VERSIONS[k] || null;
}

/** Id do sprite do goblin vestindo a armadura da vila. */
function spriteFor(anim, frame) {
  const ver = ownedVersion();
  return ver ? `${ver}_${anim}_${frame}` : `goblin_${anim}_${frame}`;
}

module.exports = { GEAR, priceOf, setOwned, ownedVersion, spriteFor };
